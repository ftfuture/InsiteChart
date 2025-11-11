"""
Kafka 기반 이벤트 버스 모듈
실시간 데이터 동기화 및 이벤트 기반 아키텍처 지원
"""

import asyncio
import json
import uuid
from typing import Dict, List, Callable, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaConnectionError
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class EventType(Enum):
    """이벤트 타입 열거형"""
    STOCK_PRICE_UPDATE = "stock_price_update"
    STOCK_SENTIMENT_UPDATE = "stock_sentiment_update"
    MARKET_DATA_UPDATE = "market_data_update"
    USER_ACTION = "user_action"
    SYSTEM_ALERT = "system_alert"
    DATA_SYNC_COMPLETE = "data_sync_complete"
    ERROR_OCCURRED = "error_occurred"

class EventPriority(Enum):
    """이벤트 우선순위 열거형"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class DataEvent:
    """데이터 이벤트 모델"""
    event_id: str
    event_type: str
    timestamp: str
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    priority: str = "normal"
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())

@dataclass
class EventSubscription:
    """이벤트 구독 정보 모델"""
    subscription_id: str
    event_type: str
    callback: Callable
    filter_criteria: Optional[Dict[str, Any]] = None
    active: bool = True
    created_at: str = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

class KafkaEventBus:
    """Kafka 기반 이벤트 버스 클래스"""
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_prefix: str = "insitechart",
        consumer_group: str = "insitechart-consumer",
        redis_url: str = "redis://localhost:6379"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.consumer_group = consumer_group
        self.redis_url = redis_url
        
        # Kafka 클라이언트
        self.producer = None
        self.consumer = None
        
        # 이벤트 구독 관리
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.subscription_callbacks: Dict[str, Callable] = {}
        
        # 상태 관리
        self.running = False
        self.connected = False
        
        # Redis 클라이언트 (이벤트 저장 및 재처리용)
        self.redis_client = None
        
        # 이벤트 처리 통계
        self.event_stats = {
            "published": 0,
            "consumed": 0,
            "failed": 0,
            "retried": 0
        }
        
        # 토픽 이름
        self.topics = {
            "events": f"{topic_prefix}-events",
            "high_priority": f"{topic_prefix}-high-priority",
            "dead_letter": f"{topic_prefix}-dead-letter"
        }
    
    async def initialize(self):
        """이벤트 버스 초기화"""
        try:
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # Kafka 프로듀서 초기화
            await self._initialize_producer()
            
            # Kafka 컨슈머 초기화
            await self._initialize_consumer()
            
            self.connected = True
            logger.info("Kafka Event Bus initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Event Bus: {str(e)}")
            raise
    
    async def start(self):
        """이벤트 버스 시작"""
        if not self.connected:
            await self.initialize()
        
        self.running = True
        
        # 메시지 처리 시작
        asyncio.create_task(self._process_messages())
        
        # 실패한 이벤트 재처리 시작
        asyncio.create_task(self._retry_failed_events())
        
        logger.info("Kafka Event Bus started")
    
    async def stop(self):
        """이벤트 버스 중지"""
        self.running = False
        
        # 프로듀서 종료
        if self.producer:
            await self.producer.stop()
        
        # 컨슈머 종료
        if self.consumer:
            await self.consumer.stop()
        
        # Redis 클라이언트 종료
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Kafka Event Bus stopped")
    
    async def publish(self, event: DataEvent) -> bool:
        """
        이벤트 발행
        
        Args:
            event: 발행할 이벤트
            
        Returns:
            성공 여부
        """
        try:
            if not self.connected or not self.producer:
                logger.error("Event bus not connected")
                return False
            
            # 이벤트 직렬화
            event_data = asdict(event)
            
            # 우선순위에 따른 토픽 선택
            topic = self._select_topic_by_priority(event.priority)
            
            # 이벤트 발행
            await self.producer.send_and_wait(
                topic=topic,
                value=event_data,
                key=event.event_id.encode()
            )
            
            # 통계 업데이트
            self.event_stats["published"] += 1
            
            # 이벤트 저장 (재처리용)
            await self._store_event_for_retry(event)
            
            logger.debug(f"Published event {event.event_id} to topic {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {str(e)}")
            self.event_stats["failed"] += 1
            return False
    
    async def subscribe(
        self,
        event_type: str,
        callback: Callable,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        이벤트 구독
        
        Args:
            event_type: 구독할 이벤트 타입
            callback: 이벤트 처리 콜백 함수
            filter_criteria: 이벤트 필터 조건
            
        Returns:
            구독 ID
        """
        subscription_id = str(uuid.uuid4())
        
        subscription = EventSubscription(
            subscription_id=subscription_id,
            event_type=event_type,
            callback=callback,
            filter_criteria=filter_criteria
        )
        
        # 구독 정보 저장
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        
        self.subscriptions[event_type].append(subscription)
        self.subscription_callbacks[subscription_id] = callback
        
        logger.info(f"Subscribed to event type {event_type} with ID {subscription_id}")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        이벤트 구독 해지
        
        Args:
            subscription_id: 구독 ID
            
        Returns:
            성공 여부
        """
        try:
            # 구독 정보 찾기 및 비활성화
            for event_type, subscriptions in self.subscriptions.items():
                for subscription in subscriptions:
                    if subscription.subscription_id == subscription_id:
                        subscription.active = False
                        break
            
            # 콜백 제거
            if subscription_id in self.subscription_callbacks:
                del self.subscription_callbacks[subscription_id]
            
            logger.info(f"Unsubscribed from event with ID {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {subscription_id}: {str(e)}")
            return False
    
    async def publish_stock_price_update(
        self,
        symbol: str,
        price: float,
        change: float,
        change_percent: float,
        source: str = "yahoo_finance"
    ) -> bool:
        """
        주식 가격 업데이트 이벤트 발행
        
        Args:
            symbol: 주식 심볼
            price: 현재 가격
            change: 가격 변화
            change_percent: 가격 변화율
            source: 데이터 소스
            
        Returns:
            성공 여부
        """
        event = DataEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.STOCK_PRICE_UPDATE.value,
            timestamp=datetime.utcnow().isoformat(),
            source=source,
            data={
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent
            },
            metadata={
                "category": "financial_data",
                "priority": "high"
            },
            priority="high"
        )
        
        return await self.publish(event)
    
    async def publish_sentiment_update(
        self,
        symbol: str,
        sentiment_score: float,
        mention_count: int,
        source: str = "social_media"
    ) -> bool:
        """
        감성 분석 업데이트 이벤트 발행
        
        Args:
            symbol: 주식 심볼
            sentiment_score: 감성 점수
            mention_count: 언급 횟수
            source: 데이터 소스
            
        Returns:
            성공 여부
        """
        event = DataEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.STOCK_SENTIMENT_UPDATE.value,
            timestamp=datetime.utcnow().isoformat(),
            source=source,
            data={
                "symbol": symbol,
                "sentiment_score": sentiment_score,
                "mention_count": mention_count
            },
            metadata={
                "category": "sentiment_data",
                "priority": "normal"
            },
            priority="normal"
        )
        
        return await self.publish(event)
    
    async def publish_system_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning",
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        시스템 알림 이벤트 발행
        
        Args:
            alert_type: 알림 타입
            message: 알림 메시지
            severity: 심각도 (info, warning, error, critical)
            details: 추가 정보
            
        Returns:
            성공 여부
        """
        event = DataEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SYSTEM_ALERT.value,
            timestamp=datetime.utcnow().isoformat(),
            source="system",
            data={
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "details": details or {}
            },
            metadata={
                "category": "system_monitoring",
                "priority": severity
            },
            priority=severity
        )
        
        return await self.publish(event)
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """
        이벤트 통계 정보 조회
        
        Returns:
            이벤트 통계
        """
        return {
            "published": self.event_stats["published"],
            "consumed": self.event_stats["consumed"],
            "failed": self.event_stats["failed"],
            "retried": self.event_stats["retried"],
            "active_subscriptions": sum(
                len([s for s in subs if s.active])
                for subs in self.subscriptions.values()
            ),
            "connected": self.connected,
            "running": self.running
        }
    
    async def _initialize_producer(self):
        """Kafka 프로듀서 초기화"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # 모든 복제본 확인
            retries=3,
            retry_backoff_ms=100,
            request_timeout_ms=30000,
            compression_type='gzip'
        )
        
        await self.producer.start()
        logger.info("Kafka producer initialized")
    
    async def _initialize_consumer(self):
        """Kafka 컨슈머 초기화"""
        topics = list(self.topics.values())
        
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.consumer_group,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            session_timeout_ms=30000,
            heartbeat_interval_ms=3000,
            max_poll_records=100
        )
        
        await self.consumer.start()
        logger.info("Kafka consumer initialized")
    
    async def _process_messages(self):
        """메시지 처리 루프"""
        try:
            while self.running:
                # 메시지 수신 대기
                message_pack = await self.consumer.getmany(timeout_ms=1000)
                
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        await self._handle_message(message)
                
                # 짧은 대시간으로 CPU 사용량 감소
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in message processing loop: {str(e)}")
            # 재시작 로직
            if self.running:
                await asyncio.sleep(5)
                asyncio.create_task(self._process_messages())
    
    async def _handle_message(self, message):
        """수신된 메시지 처리"""
        try:
            # 메시지 데이터 파싱
            event_data = message.value
            event_type = event_data.get("event_type")
            
            if not event_type:
                logger.warning(f"Received message without event_type: {message.key}")
                return
            
            # 이벤트 필터링 및 구독자에게 전달
            await self._notify_subscribers(event_type, event_data)
            
            # 통계 업데이트
            self.event_stats["consumed"] += 1
            
            logger.debug(f"Processed event {event_data.get('event_id')} of type {event_type}")
            
        except Exception as e:
            logger.error(f"Error handling message {message.key}: {str(e)}")
            self.event_stats["failed"] += 1
            
            # 실패한 이벤트 저장
            await self._store_failed_event(message.value)
    
    async def _notify_subscribers(self, event_type: str, event_data: Dict[str, Any]):
        """구독자에게 이벤트 알림"""
        if event_type not in self.subscriptions:
            return
        
        for subscription in self.subscriptions[event_type]:
            if not subscription.active:
                continue
            
            # 필터 조건 확인
            if subscription.filter_criteria:
                if not self._matches_filter(event_data, subscription.filter_criteria):
                    continue
            
            try:
                # 비동기 콜백 호출
                if asyncio.iscoroutinefunction(subscription.callback):
                    await subscription.callback(event_data)
                else:
                    # 동기 함수는 스레드 풀에서 실행
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, subscription.callback, event_data)
                    
            except Exception as e:
                logger.error(f"Error in subscription callback {subscription.subscription_id}: {str(e)}")
    
    def _matches_filter(self, event_data: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
        """이벤트 필터 조건 확인"""
        for key, value in filter_criteria.items():
            if key not in event_data or event_data[key] != value:
                return False
        return True
    
    def _select_topic_by_priority(self, priority: str) -> str:
        """우선순위에 따른 토픽 선택"""
        if priority in ["high", "critical"]:
            return self.topics["high_priority"]
        else:
            return self.topics["events"]
    
    async def _store_event_for_retry(self, event: DataEvent):
        """재처리를 위한 이벤트 저장"""
        try:
            if not self.redis_client:
                return
            
            # 재시도 횟수가 남은 경우에만 저장
            if event.retry_count < event.max_retries:
                retry_key = f"events:retry:{event.event_id}"
                await self.redis_client.setex(
                    retry_key,
                    3600,  # 1시간 후 만료
                    json.dumps(asdict(event))
                )
                
        except Exception as e:
            logger.error(f"Error storing event for retry: {str(e)}")
    
    async def _store_failed_event(self, event_data: Dict[str, Any]):
        """실패한 이벤트 저장"""
        try:
            if not self.redis_client:
                return
            
            failed_key = f"events:failed:{event_data.get('event_id')}"
            await self.redis_client.setex(
                failed_key,
                86400,  # 24시간 후 만료
                json.dumps(event_data)
            )
            
        except Exception as e:
            logger.error(f"Error storing failed event: {str(e)}")
    
    async def _retry_failed_events(self):
        """실패한 이벤트 재처리"""
        while self.running:
            try:
                if not self.redis_client:
                    await asyncio.sleep(60)
                    continue
                
                # 재시도 대기 이벤트 조회
                retry_keys = await self.redis_client.keys("events:retry:*")
                
                for key in retry_keys:
                    event_data_str = await self.redis_client.get(key)
                    if not event_data_str:
                        continue
                    
                    try:
                        event_data = json.loads(event_data_str)
                        event = DataEvent(**event_data)
                        
                        # 재시도 횟수 증가
                        event.retry_count += 1
                        
                        # 이벤트 재발행
                        if await self.publish(event):
                            # 성공 시 재시도 큐에서 제거
                            await self.redis_client.delete(key)
                            self.event_stats["retried"] += 1
                        else:
                            # 실패 시 재시도 횟수 확인
                            if event.retry_count >= event.max_retries:
                                # 최대 재시도 횟수 초과 시 실패 큐로 이동
                                await self._store_failed_event(event_data)
                                await self.redis_client.delete(key)
                            else:
                                # 재시도 정보 업데이트
                                await self.redis_client.setex(
                                    key,
                                    3600,
                                    json.dumps(asdict(event))
                                )
                    
                    except Exception as e:
                        logger.error(f"Error retrying event {key}: {str(e)}")
                
                # 1분마다 재시도 확인
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in retry loop: {str(e)}")
                await asyncio.sleep(60)

# 전역 이벤트 버스 인스턴스
kafka_event_bus = KafkaEventBus()


# 별칭으로 Event 클래스 제공
Event = DataEvent