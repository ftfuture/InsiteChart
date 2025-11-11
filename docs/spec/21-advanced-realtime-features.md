# 고급 실시간 기능 확장

## 1. 실시간 데이터 동기화 강화

### 1.1 웹소켓 기반 실시간 데이터 스트리밍

#### 1.1.1 실시간 데이터 관리자
```python
# realtime/websocket_manager.py
import asyncio
import json
from typing import Dict, List, Any, Set
from datetime import datetime, timedelta
import logging
from fastapi import WebSocket, WebSocketDisconnect
from app.services.data_collection import DataCollectionManager
from app.core.config import settings

class RealtimeDataManager:
    def __init__(self, websocket_manager, data_collection_manager):
        self.websocket_manager = websocket_manager
        self.data_collection_manager = data_collection_manager
        self.logger = logging.getLogger(__name__)
        
        # 실시간 데이터 처리 큐
        self.processing_queue = asyncio.Queue()
        
        # 실시간 데이터 구독자
        self.subscribers = {}
        
        # 데이터 수집 주기 (초)
        self.collection_intervals = {
            'stock_prices': 15,      # 15초
            'sentiment_data': 300,    # 5분
            'trending_stocks': 600    # 10분
        }
        
    async def start_realtime_processing(self):
        """실시간 데이터 처리 시작"""
        self.logger.info("Starting real-time data processing")
        
        # 데이터 수집 작업자 실행
        asyncio.create_task(self._data_collection_worker())
        
        # 실시간 처리 작업자 실행
        asyncio.create_task(self._realtime_processor())
        
        # 주기적 데이터 수집 작업자 실행
        asyncio.create_task(self._periodic_data_collector())
        
    async def _data_collection_worker(self):
        """데이터 수집 작업자"""
        while True:
            try:
                # 데이터 수집 대기
                data_task = await self.processing_queue.get()
                if data_task is None:
                    await asyncio.sleep(1)
                    continue
                
                await self.data_collection_manager.process_data_task(data_task)
                
            except Exception as e:
                self.logger.error(f"Data collection error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _realtime_processor(self):
        """실시간 데이터 처리 작업자"""
        while True:
            try:
                # 처리 대기
                data_task = await self.processing_queue.get()
                if data_task is None:
                    await asyncio.sleep(1)
                    continue
                
                await self._process_realtime_data(data_task)
                
            except Exception as e:
                self.logger.error(f"Realtime processing error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _periodic_data_collector(self):
        """주기적 데이터 수집 작업자"""
        while True:
            try:
                # 주식 가격 데이터 수집
                await self._collect_stock_prices()
                
                # 센티먼트 데이터 수집
                await self._collect_sentiment_data()
                
                # 트렌딩 주식 감지
                await self._detect_trending_stocks()
                
                # 다음 수집 대기
                await asyncio.sleep(60)  # 1분마다 확인
                
            except Exception as e:
                self.logger.error(f"Periodic data collection error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _collect_stock_prices(self):
        """주식 가격 데이터 수집"""
        # 관심종목 목록 조회
        watchlist_symbols = await self._get_watchlist_symbols()
        
        for symbol in watchlist_symbols:
            # 주식 가격 데이터 수집
            price_data = await self.data_collection_manager.get_stock_price(symbol)
            
            if price_data:
                # 실시간 처리 큐에 추가
                await self.processing_queue.put({
                    'type': 'stock_update',
                    'payload': price_data
                })
    
    async def _collect_sentiment_data(self):
        """센티먼트 데이터 수집"""
        # 관심종목 목록 조회
        watchlist_symbols = await self._get_watchlist_symbols()
        
        for symbol in watchlist_symbols:
            # 센티먼트 데이터 수집
            sentiment_data = await self.data_collection_manager.get_sentiment_data(symbol)
            
            if sentiment_data:
                # 실시간 처리 큐에 추가
                await self.processing_queue.put({
                    'type': 'sentiment_update',
                    'payload': sentiment_data
                })
    
    async def _detect_trending_stocks(self):
        """트렌딩 주식 감지"""
        # 트렌딩 주식 감지
        trending_stocks = await self.data_collection_manager.detect_trending_stocks()
        
        if trending_stocks:
            # 실시간 처리 큐에 추가
            await self.processing_queue.put({
                'type': 'trending_update',
                'payload': {'trending_stocks': trending_stocks}
            })
    
    async def _get_watchlist_symbols(self) -> List[str]:
        """관심종목 심볼 목록 조회"""
        # 실제 구현에서는 데이터베이스 조회
        # 여기서는 예시 데이터 반환
        return ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN']
    
    async def _process_realtime_data(self, data_task: Dict[str, Any]):
        """실시간 데이터 처리"""
        try:
            data_type = data_task.get('type')
            data_payload = data_task.get('payload')
            
            if data_type == 'stock_update':
                await self._handle_stock_update(data_payload)
            elif data_type == 'sentiment_update':
                await self._handle_sentiment_update(data_payload)
            elif data_type == 'trending_update':
                await self._handle_trending_update(data_payload)
                
        except Exception as e:
            self.logger.error(f"Realtime data processing error: {str(e)}")
    
    async def _handle_stock_update(self, stock_data: Dict[str, Any]):
        """주식 업데이트 실시간 처리"""
        symbol = stock_data.get('symbol')
        new_price = stock_data.get('current_price')
        old_price = stock_data.get('previous_close')
        
        # 실시간 구독자에게 브로드캐스트
        await self.websocket_manager.broadcast_to_topic('stock_updates', {
            'symbol': symbol,
            'new_price': new_price,
            'old_price': old_price,
            'timestamp': datetime.now().isoformat(),
            'source': 'real_time'
        })
        
        # 관심종목 사용자에게 알림
        await self._notify_watchlist_users(symbol, {
            'type': 'price_alert',
            'symbol': symbol,
            'old_price': old_price,
            'new_price': new_price,
            'change_percent': ((new_price - old_price) / old_price * 100) if old_price > 0 else 0,
            'timestamp': datetime.now().isoformat()
        })
    
    async def _handle_sentiment_update(self, sentiment_data: Dict[str, Any]):
        """센티먼트 데이터 실시간 처리"""
        symbol = sentiment_data.get('symbol')
        new_sentiment = sentiment_data.get('overall_sentiment')
        old_sentiment = sentiment_data.get('previous_sentiment', 0)
        
        # 실시간 구독자에게 브로드캐스트
        await self.websocket_manager.broadcast_to_topic('sentiment_updates', {
            'symbol': symbol,
            'new_sentiment': new_sentiment,
            'old_sentiment': old_sentiment,
            'timestamp': datetime.now().isoformat(),
            'source': 'real_time'
        })
        
        await self._notify_watchlist_users(symbol, {
            'type': 'sentiment_alert',
            'symbol': symbol,
            'sentiment_change': new_sentiment - old_sentiment,
            'timestamp': datetime.now().isoformat()
        })
    
    async def _handle_trending_update(self, trending_data: Dict[str, Any]):
        """트렌딩 주식 실시간 감지"""
        trending_stocks = trending_data.get('trending_stocks', [])
        
        # 실시간 구독자에게 브로드캐스트
        await self.websocket_manager.broadcast_to_topic('trending_updates', {
            'trending_stocks': trending_stocks,
            'timestamp': datetime.now().isoformat(),
            'source': 'real_time'
        })
    
    async def _notify_watchlist_users(self, alert_data: Dict[str, Any]):
        """관심종목 사용자 알림"""
        # 실제 구현에서는 데이터베이스 조회 후 알림
        await self.websocket_manager.broadcast_to_topic('user_alerts', alert_data)

# WebSocket 엔드포인트 확장
class EnhancedWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscription_topics = {
            'stock_updates': {},
            'sentiment_updates': {},
            'trending_updates': {},
            'user_alerts': {}
        }
        self.logger = logging.getLogger(__name__)
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """WebSocket 연결"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.logger.info(f"WebSocket connected: {client_id}")
        
        # 연결 환영 메시지
        await self._send_message(websocket, {
            'type': 'connection',
            'message': 'Connected to real-time data stream',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def disconnect(self, client_id: str):
        """WebSocket 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # 구독 정보 정리
        for topic, subscribers in self.subscription_topics.items():
            if client_id in subscribers:
                del subscribers[client_id]
                
        self.logger.info(f"WebSocket disconnected: {client_id}")
    
    async def subscribe_to_topic(self, client_id: str, topic: str, symbol: str = None):
        """특정 토픽 구독"""
        if client_id not in self.active_connections:
            return False
            
        if topic not in self.subscription_topics:
            return False
            
        # 구독 정보 추가
        self.subscription_topics[topic][client_id] = {
            'symbol': symbol,
            'subscribed_at': datetime.now()
        }
        
        # 구독 확인 메시지
        websocket = self.active_connections[client_id]
        await self._send_message(websocket, {
            'type': 'subscription',
            'topic': topic,
            'symbol': symbol,
            'message': f"Subscribed to {topic}" + (f" for {symbol}" if symbol else ""),
            'timestamp': datetime.now().isoformat()
        })
        
        return True
    
    async def unsubscribe_from_topic(self, client_id: str, topic: str):
        """특정 토픽 구독 해제"""
        if client_id in self.subscription_topics.get(topic, {}):
            del self.subscription_topics[topic][client_id]
            
            # 구독 해제 확인 메시지
            websocket = self.active_connections.get(client_id)
            if websocket:
                await self._send_message(websocket, {
                    'type': 'unsubscription',
                    'topic': topic,
                    'message': f"Unsubscribed from {topic}",
                    'timestamp': datetime.now().isoformat()
                })
    
    async def broadcast_to_topic(self, topic: str, message: Dict):
        """특정 토픽에 메시지 브로드캐스트"""
        if topic not in self.subscription_topics:
            return
            
        for client_id, subscription in self.subscription_topics[topic].items():
            if client_id not in self.active_connections:
                continue
                
            # 심볼 필터링 (있는 경우)
            symbol = subscription.get('symbol')
            if symbol and message.get('symbol') and message['symbol'] != symbol:
                continue
                
            websocket = self.active_connections[client_id]
            try:
                await self._send_message(websocket, {
                    'type': 'broadcast',
                    'topic': topic,
                    'message': message
                })
            except Exception as e:
                self.logger.error(f"WebSocket broadcast error to {client_id}: {str(e)}")
    
    async def _send_message(self, websocket: WebSocket, message: Dict):
        """WebSocket 메시지 전송"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.error(f"WebSocket send error: {str(e)}")
```

#### 1.1.2 실시간 알림 시스템
```python
# notifications/realtime_notifications.py
import asyncio
import smtplib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

class AlertType(Enum):
    PRICE_ALERT = "price_alert"
    SENTIMENT_ALERT = "sentiment_alert"
    TRENDING_ALERT = "trending_alert"
    VOLUME_ALERT = "volume_alert"

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Alert:
    type: AlertType
    symbol: str
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    recipients: List[str]
    priority: AlertPriority = AlertPriority.MEDIUM
    is_read: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'symbol': self.symbol,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'recipients': self.recipients,
            'priority': self.priority.value,
            'is_read': self.is_read
        }

class RealtimeNotificationSystem:
    def __init__(self, websocket_manager, db_session):
        self.websocket_manager = websocket_manager
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        
        # 알림 큐
        self.alert_queue = asyncio.Queue()
        
        # 알림 설정
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_username': settings.SMTP_USERNAME,
            'smtp_password': settings.SMTP_PASSWORD
        }
        
        # 알림 임계값
        self.alert_thresholds = {
            'price_change_percent': 5.0,  # 5% 이상 변동
            'sentiment_change': 0.3,      # 센티먼트 0.3 이상 변동
            'volume_spike': 2.0,          # 거래량 2배 이상 증가
            'trending_score': 0.8          # 트렌딩 점수 0.8 이상
        }
    
    async def start_notification_processing(self):
        """알림 처리 시작"""
        self.logger.info("Starting real-time notification processing")
        
        # 알림 처리 작업자 실행
        asyncio.create_task(self._notification_processor())
    
    async def _notification_processor(self):
        """알림 처리 작업자"""
        while True:
            try:
                # 알림 대기
                alert = await self.alert_queue.get()
                if alert is None:
                    await asyncio.sleep(1)
                    continue
                
                # 알림 처리
                await self._process_alert(alert)
                
            except Exception as e:
                self.logger.error(f"Notification processing error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_alert(self, alert: Alert):
        """알림 처리"""
        try:
            # 알림 저장
            await self._save_alert(alert)
            
            # 실시간 알림 전송
            await self._send_realtime_notification(alert)
            
            # 이메일 알림 전송 (중요도 높음)
            if alert.priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]:
                await self._send_email_alert(alert)
            
            # SMS 알림 전송 (긴급)
            if alert.priority == AlertPriority.CRITICAL:
                await self._send_sms_alert(alert)
                
        except Exception as e:
            self.logger.error(f"Alert processing error: {str(e)}")
    
    async def create_price_alert(self, symbol: str, old_price: float, new_price: float):
        """가격 알림 생성"""
        change_percent = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
        
        # 임계값 확인
        if abs(change_percent) < self.alert_thresholds['price_change_percent']:
            return
        
        # 알림 우선순위 결정
        if abs(change_percent) > 10:
            priority = AlertPriority.CRITICAL
        elif abs(change_percent) > 7:
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.MEDIUM
        
        # 알림 생성
        alert = Alert(
            type=AlertType.PRICE_ALERT,
            symbol=symbol,
            title=f"Price Alert: {symbol}",
            message=f"{symbol} price changed by {change_percent:.2f}%",
            data={
                'old_price': old_price,
                'new_price': new_price,
                'change_percent': change_percent
            },
            timestamp=datetime.now(),
            recipients=await self._get_alert_recipients(symbol),
            priority=priority
        )
        
        # 알림 큐에 추가
        await self.alert_queue.put(alert)
    
    async def create_sentiment_alert(self, symbol: str, old_sentiment: float, new_sentiment: float):
        """센티먼트 알림 생성"""
        sentiment_change = abs(new_sentiment - old_sentiment)
        
        # 임계값 확인
        if sentiment_change < self.alert_thresholds['sentiment_change']:
            return
        
        # 알림 우선순위 결정
        if sentiment_change > 0.5:
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.MEDIUM
        
        # 알림 생성
        alert = Alert(
            type=AlertType.SENTIMENT_ALERT,
            symbol=symbol,
            title=f"Sentiment Alert: {symbol}",
            message=f"{symbol} sentiment changed by {sentiment_change:.2f}",
            data={
                'old_sentiment': old_sentiment,
                'new_sentiment': new_sentiment,
                'sentiment_change': sentiment_change
            },
            timestamp=datetime.now(),
            recipients=await self._get_alert_recipients(symbol),
            priority=priority
        )
        
        # 알림 큐에 추가
        await self.alert_queue.put(alert)
    
    async def create_trending_alert(self, symbol: str, trend_score: float):
        """트렌딩 알림 생성"""
        # 임계값 확인
        if trend_score < self.alert_thresholds['trending_score']:
            return
        
        # 알림 생성
        alert = Alert(
            type=AlertType.TRENDING_ALERT,
            symbol=symbol,
            title=f"Trending Alert: {symbol}",
            message=f"{symbol} is trending with score {trend_score:.2f}",
            data={
                'trend_score': trend_score
            },
            timestamp=datetime.now(),
            recipients=await self._get_alert_recipients(symbol),
            priority=AlertPriority.MEDIUM
        )
        
        # 알림 큐에 추가
        await self.alert_queue.put(alert)
    
    async def _get_alert_recipients(self, symbol: str) -> List[str]:
        """알림 수신자 목록 조회"""
        # 실제 구현에서는 데이터베이스에서 해당 주식을 관심종목으로 등록한 사용자 조회
        # 여기서는 예시 데이터 반환
        return ['user1@example.com', 'user2@example.com']
    
    async def _save_alert(self, alert: Alert):
        """알림 저장"""
        # 실제 구현에서는 데이터베이스에 알림 저장
        pass
    
    async def _send_realtime_notification(self, alert: Alert):
        """실시간 알림 전송"""
        # WebSocket을 통해 실시간 알림 전송
        await self.websocket_manager.broadcast_to_topic('user_alerts', alert.to_dict())
    
    async def _send_email_alert(self, alert: Alert):
        """이메일 알림 전송"""
        try:
            # 이메일 내용 생성
            subject = f"[InsiteChart] {alert.title}"
            body = f"""
            <h2>{alert.title}</h2>
            <p>{alert.message}</p>
            <p><strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Priority:</strong> {alert.priority.value}</p>
            
            <h3>Details:</h3>
            <pre>{json.dumps(alert.data, indent=2)}</pre>
            
            <p>Best regards,<br>InsiteChart Team</p>
            """
            
            # 이메일 전송
            await self._send_email_smtp(alert.recipients, subject, body)
            
        except Exception as e:
            self.logger.error(f"Email alert failed: {str(e)}")
    
    async def _send_email_smtp(self, recipients: List[str], subject: str, body: str):
        """SMTP를 통한 이메일 전송"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # 이메일 생성
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_config['smtp_username']
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(body, _subtype='html'))
        
        # SMTP 전송
        with smtplib.SMTP(
            self.email_config['smtp_server'],
            self.email_config['smtp_port']
        ) as server:
            server.starttls()
            server.login(
                self.email_config['smtp_username'],
                self.email_config['smtp_password']
            )
            server.send_message(msg)
    
    async def _send_sms_alert(self, alert: Alert):
        """SMS 알림 전송"""
        # 실제 구현에서는 Twilio 등 SMS 서비스 사용
        pass
```

### 1.2 트렌딩 감지 고도화

#### 1.2.1 고급 트렌딩 감지 알고리즘
```python
# trending/advanced_trending_detector.py
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import logging

class AdvancedTrendingDetector:
    def __init__(self, data_collection_manager):
        self.data_collection_manager = data_collection_manager
        self.logger = logging.getLogger(__name__)
        
        # 트렌딩 감지 파라미터
        self.trending_thresholds = {
            'mention_count': 100,        # 최소 언급 수
            'mention_growth_rate': 2.0,  # 언급 증가율
            'sentiment_change': 0.3,     # 센티먼트 변화량
            'price_change': 0.05,        # 가격 변화율
            'volume_spike': 2.0          # 거래량 증가율
        }
        
        # 트렌딩 점수 가중치
        self.trending_weights = {
            'mention_growth': 0.4,
            'sentiment_change': 0.2,
            'price_change': 0.2,
            'volume_spike': 0.2
        }
        
    async def detect_trending_stocks(self) -> List[Dict[str, Any]]:
        """고급 트렌딩 주식 감지"""
        trending_stocks = []
        
        try:
            # 최근 24시간 언급 데이터 조회
            recent_mentions = await self.data_collection_manager.get_recent_mentions(24)
            
            # 심볼별 언급 집계
            symbol_mentions = self._group_mentions_by_symbol(recent_mentions)
            
            # 각 심볼별 트렌딩 분석
            for symbol, mentions in symbol_mentions.items():
                # 기준선 계산 (최근 7일간 평균)
                baseline = await self._calculate_baseline(symbol)
                
                # 현재 언급
                current_mentions = len(mentions)
                
                # 트렌딩 점수 계산
                trend_score = await self._calculate_advanced_trend_score(symbol, mentions, baseline)
                
                # 트렌딩 임계값 확인
                if trend_score > 0.7:  # 트렌딩 임계값
                    trending_stocks.append({
                        'symbol': symbol,
                        'trend_score': trend_score,
                        'current_mentions': current_mentions,
                        'baseline': baseline,
                        'mention_growth_rate': current_mentions / baseline if baseline > 0 else 0,
                        'timestamp': datetime.now().isoformat(),
                        'trend_factors': await self._get_trend_factors(symbol, mentions, baseline)
                    })
        
        except Exception as e:
            self.logger.error(f"Advanced trending detection error: {str(e)}")
        
        # 트렌딩 점수로 정렬
        trending_stocks.sort(key=lambda x: x['trend_score'], reverse=True)
        
        return trending_stocks
    
    def _group_mentions_by_symbol(self, mentions: List[Dict]) -> Dict[str, List[Dict]]:
        """심볼별 언급 그룹화"""
        symbol_mentions = {}
        
        for mention in mentions:
            symbol = mention.get('symbol')
            if symbol not in symbol_mentions:
                symbol_mentions[symbol] = []
            symbol_mentions[symbol].append(mention)
        
        return symbol_mentions
    
    async def _calculate_baseline(self, symbol: str) -> float:
        """기준선 언급 계산"""
        try:
            # 최근 7일간 언급 데이터 조회
            baseline_mentions = await self.data_collection_manager.get_recent_mentions(
                symbol, hours=168  # 7일
            )
            
            # 일별 평균 언급 수 계산
            daily_mentions = {}
            for mention in baseline_mentions:
                date = mention.get('timestamp', datetime.now()).date()
                if date not in daily_mentions:
                    daily_mentions[date] = 0
                daily_mentions[date] += 1
            
            # 평균 계산
            if daily_mentions:
                return sum(daily_mentions.values()) / len(daily_mentions)
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Baseline calculation error for {symbol}: {str(e)}")
            return 0.0
    
    async def _calculate_advanced_trend_score(self, symbol: str, mentions: List[Dict], baseline: float) -> float:
        """고급 트렌딩 점수 계산"""
        try:
            # 언급 증가율 점수
            mention_growth_score = await self._calculate_mention_growth_score(mentions, baseline)
            
            # 센티먼트 변화 점수
            sentiment_change_score = await self._calculate_sentiment_change_score(symbol)
            
            # 가격 변화 점수
            price_change_score = await self._calculate_price_change_score(symbol)
            
            # 거래량 증가 점수
            volume_spike_score = await self._calculate_volume_spike_score(symbol)
            
            # 가중치 적용 종합 점수
            total_score = (
                mention_growth_score * self.trending_weights['mention_growth'] +
                sentiment_change_score * self.trending_weights['sentiment_change'] +
                price_change_score * self.trending_weights['price_change'] +
                volume_spike_score * self.trending_weights['volume_spike']
            )
            
            return min(total_score, 1.0)  # 최대 1.0으로 제한
            
        except Exception as e:
            self.logger.error(f"Trend score calculation error for {symbol}: {str(e)}")
            return 0.0
    
    async def _calculate_mention_growth_score(self, mentions: List[Dict], baseline: float) -> float:
        """언급 증가율 점수 계산"""
        if baseline == 0:
            return 0.0
        
        current_mentions = len(mentions)
        growth_rate = current_mentions / baseline
        
        # 증가율에 따른 점수 (0~1)
        if growth_rate >= self.trending_thresholds['mention_growth_rate']:
            return min(growth_rate / 5.0, 1.0)  # 5배 증가 시 1.0
        else:
            return growth_rate / self.trending_thresholds['mention_growth_rate']
    
    async def _calculate_sentiment_change_score(self, symbol: str) -> float:
        """센티먼트 변화 점수 계산"""
        try:
            # 최근 24시간 센티먼트 데이터
            recent_sentiment = await self.data_collection_manager.get_sentiment_data(symbol, hours=24)
            
            # 이전 24시간 센티먼트 데이터
            previous_sentiment = await self.data_collection_manager.get_sentiment_data(
                symbol, hours_start=48, hours_end=24
            )
            
            if not recent_sentiment or not previous_sentiment:
                return 0.0
            
            # 평균 센티먼트 계산
            recent_avg = np.mean([s.get('overall_sentiment', 0) for s in recent_sentiment])
            previous_avg = np.mean([s.get('overall_sentiment', 0) for s in previous_sentiment])
            
            # 센티먼트 변화량
            sentiment_change = abs(recent_avg - previous_avg)
            
            # 변화량에 따른 점수 (0~1)
            return min(sentiment_change / self.trending_thresholds['sentiment_change'], 1.0)
            
        except Exception as e:
            self.logger.error(f"Sentiment change score calculation error for {symbol}: {str(e)}")
            return 0.0
    
    async def _calculate_price_change_score(self, symbol: str) -> float:
        """가격 변화 점수 계산"""
        try:
            # 최신 주식 가격 데이터
            current_price_data = await self.data_collection_manager.get_latest_stock_price(symbol)
            
            # 24시간 전 주식 가격 데이터
            previous_price_data = await self.data_collection_manager.get_stock_price_24h_ago(symbol)
            
            if not current_price_data or not previous_price_data:
                return 0.0
            
            current_price = current_price_data.get('close_price', 0)
            previous_price = previous_price_data.get('close_price', 0)
            
            if previous_price == 0:
                return 0.0
            
            # 가격 변화율
            price_change = abs(current_price - previous_price) / previous_price
            
            # 변화율에 따른 점수 (0~1)
            return min(price_change / self.trending_thresholds['price_change'], 1.0)
            
        except Exception as e:
            self.logger.error(f"Price change score calculation error for {symbol}: {str(e)}")
            return 0.0
    
    async def _calculate_volume_spike_score(self, symbol: str) -> float:
        """거래량 증가 점수 계산"""
        try:
            # 최신 거래량 데이터
            current_volume_data = await self.data_collection_manager.get_latest_stock_price(symbol)
            
            # 24시간 전 거래량 데이터
            previous_volume_data = await self.data_collection_manager.get_stock_price_24h_ago(symbol)
            
            if not current_volume_data or not previous_volume_data:
                return 0.0
            
            current_volume = current_volume_data.get('volume', 0)
            previous_volume = previous_volume_data.get('volume', 0)
            
            if previous_volume == 0:
                return 0.0
            
            # 거래량 증가율
            volume_spike = current_volume / previous_volume
            
            # 증가율에 따른 점수 (0~1)
            return min(volume_spike / self.trending_thresholds['volume_spike'], 1.0)
            
        except Exception as e:
            self.logger.error(f"Volume spike score calculation error for {symbol}: {str(e)}")
            return 0.0
    
    async def _get_trend_factors(self, symbol: str, mentions: List[Dict], baseline: float) -> Dict[str, Any]:
        """트렌딩 요인 상세 정보"""
        try:
            return {
                'mention_growth': {
                    'current': len(mentions),
                    'baseline': baseline,
                    'growth_rate': len(mentions) / baseline if baseline > 0 else 0,
                    'score': await self._calculate_mention_growth_score(mentions, baseline)
                },
                'sentiment_change': {
                    'score': await self._calculate_sentiment_change_score(symbol)
                },
                'price_change': {
                    'score': await self._calculate_price_change_score(symbol)
                },
                'volume_spike': {
                    'score': await self._calculate_volume_spike_score(symbol)
                }
            }
        except Exception as e:
            self.logger.error(f"Trend factors calculation error for {symbol}: {str(e)}")
            return {}
```

### 1.3 실시간 데이터 API 엔드포인트

#### 1.3.1 WebSocket API 엔드포인트
```python
# api/websocket_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional, List
import json
import logging

from app.services.realtime.websocket_manager import EnhancedWebSocketManager
from app.services.realtime.realtime_notifications import RealtimeNotificationSystem
from app.api.deps import get_current_user, get_db_session

router = APIRouter()
logger = logging.getLogger(__name__)

# WebSocket 관리자 인스턴스
websocket_manager = EnhancedWebSocketManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 엔드포인트"""
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 처리
            await handle_websocket_message(websocket, client_id, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(f"WebSocket disconnected: {client_id}")

async def handle_websocket_message(websocket: WebSocket, client_id: str, message: dict):
    """WebSocket 메시지 처리"""
    try:
        message_type = message.get('type')
        
        if message_type == 'subscribe':
            # 토픽 구독
            topic = message.get('topic')
            symbol = message.get('symbol')
            
            if await websocket_manager.subscribe_to_topic(client_id, topic, symbol):
                await websocket.send_text(json.dumps({
                    'type': 'subscription_success',
                    'topic': topic,
                    'symbol': symbol,
                    'message': f"Successfully subscribed to {topic}" + (f" for {symbol}" if symbol else "")
                }))
            else:
                await websocket.send_text(json.dumps({
                    'type': 'subscription_error',
                    'topic': topic,
                    'message': f"Failed to subscribe to {topic}"
                }))
        
        elif message_type == 'unsubscribe':
            # 토픽 구독 해제
            topic = message.get('topic')
            
            await websocket_manager.unsubscribe_from_topic(client_id, topic)
            
        elif message_type == 'ping':
            # 핑퐁 확인
            await websocket.send_text(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
        
        else:
            # 알 수 없는 메시지 타입
            await websocket.send_text(json.dumps({
                'type': 'error',
                'message': f"Unknown message type: {message_type}"
            }))
            
    except Exception as e:
        logger.error(f"WebSocket message handling error: {str(e)}")
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': "Internal server error"
        }))

@router.get("/ws/topics")
async def get_available_topics():
    """사용 가능한 토픽 목록 조회"""
    return {
        'topics': [
            {
                'name': 'stock_updates',
                'description': 'Real-time stock price updates',
                'supports_symbol_filter': True
            },
            {
                'name': 'sentiment_updates',
                'description': 'Real-time sentiment analysis updates',
                'supports_symbol_filter': True
            },
            {
                'name': 'trending_updates',
                'description': 'Real-time trending stocks updates',
                'supports_symbol_filter': False
            },
            {
                'name': 'user_alerts',
                'description': 'Personalized user alerts',
                'supports_symbol_filter': False
            }
        ]
    }

@router.get("/ws/connections")
async def get_active_connections():
    """활성 WebSocket 연결 목록 조회"""
    return {
        'active_connections': len(websocket_manager.active_connections),
        'subscriptions': {
            topic: len(subscribers)
            for topic, subscribers in websocket_manager.subscription_topics.items()
        }
    }
```

## 2. 고급 분석 기능 확장

### 2.1 BERT 기반 센티먼트 분석

#### 2.1.1 고급 센티먼트 분석기
```python
# sentiment/advanced_sentiment_analyzer.py
import asyncio
import torch
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import logging
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    pipeline
)

class AdvancedSentimentAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 모델 설정
        self.models = {
            'bert': {
                'name': 'ProsusAI/finbert',
                'tokenizer': None,
                'model': None,
                'pipeline': None
            },
            'roberta': {
                'name': 'cardiffnlp/twitter-roberta-base-sentiment-latest',
                'tokenizer': None,
                'model': None,
                'pipeline': None
            },
            'distilbert': {
                'name': 'distilbert-base-uncased-finetuned-sst-2-english',
                'tokenizer': None,
                'model': None,
                'pipeline': None
            }
        }
        
        # 가중치 설정
        self.model_weights = {
            'bert': 0.5,
            'roberta': 0.3,
            'distilbert': 0.2
        }
        
        # 금융 용어 사전
        self.financial_terms = {
            'bullish': ['bull', 'bullish', 'buy', 'long', 'moon', 'rocket', 'diamond hands'],
            'bearish': ['bear', 'bearish', 'sell', 'short', 'paper hands', 'dump'],
            'neutral': ['hold', 'hodl', 'wait', 'sideways']
        }
    
    async def initialize_models(self):
        """모델 초기화"""
        self.logger.info("Initializing sentiment analysis models...")
        
        for model_name, model_config in self.models.items():
            try:
                # 토크나이저 로드
                model_config['tokenizer'] = AutoTokenizer.from_pretrained(
                    model_config['name']
                )
                
                # 모델 로드
                model_config['model'] = AutoModelForSequenceClassification.from_pretrained(
                    model_config['name']
                )
                
                # 파이프라인 생성
                model_config['pipeline'] = pipeline(
                    "sentiment-analysis",
                    model=model_config['model'],
                    tokenizer=model_config['tokenizer'],
                    device=0 if torch.cuda.is_available() else -1
                )
                
                self.logger.info(f"Model {model_name} loaded successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to load model {model_name}: {str(e)}")
                model_config['pipeline'] = None
    
    async def analyze_sentiment_multi_model(self, texts: List[str], context: str = "general") -> Dict[str, Any]:
        """다중 모델을 활용한 센티먼트 분석"""
        if not any(model['pipeline'] for model in self.models.values()):
            await self.initialize_models()
        
        results = {
            'texts': texts,
            'context': context,
            'model_results': {},
            'combined_result': None,
            'financial_context': None
        }
        
        # 각 모델로 분석 실행
        model_tasks = []
        for model_name, model_config in self.models.items():
            if model_config['pipeline']:
                task = asyncio.create_task(
                    self._analyze_with_model(model_name, texts)
                )
                model_tasks.append(task)
        
        # 모든 모델 결과 기다리기
        model_results = await asyncio.gather(*model_tasks, return_exceptions=True)
        
        # 결과 저장
        for i, result in enumerate(model_results):
            model_name = list(self.models.keys())[i]
            if not isinstance(result, Exception):
                results['model_results'][model_name] = result
            else:
                self.logger.error(f"Model {model_name} analysis failed: {str(result)}")
                results['model_results'][model_name] = None
        
        # 결과 통합
        results['combined_result'] = self._combine_model_results(results['model_results'])
        
        # 금융 컨텍스트 적용
        results['financial_context'] = self._apply_financial_context(texts, results['combined_result'])
        
        return results
    
    async def _analyze_with_model(self, model_name: str, texts: List[str]) -> Dict[str, Any]:
        """특정 모델로 센티먼트 분석"""
        try:
            model_config = self.models[model_name]
            pipeline = model_config['pipeline']
            
            if not pipeline:
                return None
            
            # 배치 처리
            batch_size = 16
            all_results = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_results = pipeline(batch_texts)
                all_results.extend(batch_results)
            
            # 결과 정리
            processed_results = []
            for i, result in enumerate(all_results):
                label = result['label'].lower()
                score = result['score']
                
                # 레이블 정규화
                if label in ['positive', 'pos', 'label_2']:
                    normalized_label = 'positive'
                elif label in ['negative', 'neg', 'label_0']:
                    normalized_label = 'negative'
                else:
                    normalized_label = 'neutral'
                
                # 점수 변환 (-1 ~ 1)
                if normalized_label == 'positive':
                    normalized_score = score
                elif normalized_label == 'negative':
                    normalized_score = -score
                else:
                    normalized_score = 0
                
                processed_results.append({
                    'text': texts[i],
                    'label': normalized_label,
                    'score': normalized_score,
                    'confidence': score
                })
            
            return {
                'model': model_name,
                'results': processed_results,
                'average_sentiment': np.mean([r['score'] for r in processed_results])
            }
            
        except Exception as e:
            self.logger.error(f"Model {model_name} analysis error: {str(e)}")
            return None
    
    def _combine_model_results(self, model_results: Dict[str, Any]) -> Dict[str, Any]:
        """다중 모델 결과 통합"""
        if not model_results:
            return None
        
        # 유효한 모델 결과 필터링
        valid_results = {
            model_name: result 
            for model_name, result in model_results.items() 
            if result is not None
        }
        
        if not valid_results:
            return None
        
        # 가중치 적용 평균 계산
        weighted_scores = []
        total_weight = 0
        
        for model_name, result in valid_results.items():
            weight = self.model_weights.get(model_name, 0)
            avg_sentiment = result.get('average_sentiment', 0)
            
            weighted_scores.append(avg_sentiment * weight)
            total_weight += weight
        
        # 가중 평균 계산
        combined_sentiment = sum(weighted_scores) / total_weight if total_weight > 0 else 0
        
        # 레이블 결정
        if combined_sentiment > 0.1:
            combined_label = 'positive'
        elif combined_sentiment < -0.1:
            combined_label = 'negative'
        else:
            combined_label = 'neutral'
        
        # 신뢰도 계산
        confidence = min(abs(combined_sentiment) + 0.5, 1.0)
        
        return {
            'label': combined_label,
            'score': combined_sentiment,
            'confidence': confidence,
            'model_count': len(valid_results),
            'models_used': list(valid_results.keys())
        }
    
    def _apply_financial_context(self, texts: List[str], sentiment_result: Dict[str, Any]) -> Dict[str, Any]:
        """금융 컨텍스트 적용"""
        if not sentiment_result:
            return None
        
        # 금융 용어 카운트
        financial_term_counts = {
            'bullish': 0,
            'bearish': 0,
            'neutral': 0
        }
        
        # 텍스트에서 금융 용어 추출
        for text in texts:
            text_lower = text.lower()
            
            for sentiment_type, terms in self.financial_terms.items():
                for term in terms:
                    if term in text_lower:
                        financial_term_counts[sentiment_type] += 1
        
        # 금융 컨텍스트 점수 계산
        total_financial_terms = sum(financial_term_counts.values())
        
        if total_financial_terms > 0:
            # 금융 용어 기반 센티먼트 조정
            financial_sentiment = (
                financial_term_counts['bullish'] - financial_term_counts['bearish']
            ) / total_financial_terms
            
            # 원래 센티먼트와 금융 컨텍스트 결합
            original_sentiment = sentiment_result.get('score', 0)
            adjusted_sentiment = (original_sentiment * 0.7) + (financial_sentiment * 0.3)
            
            # 조정된 레이블 결정
            if adjusted_sentiment > 0.1:
                adjusted_label = 'positive'
            elif adjusted_sentiment < -0.1:
                adjusted_label = 'negative'
            else:
                adjusted_label = 'neutral'
            
            return {
                'original_sentiment': sentiment_result,
                'financial_context': {
                    'term_counts': financial_term_counts,
                    'financial_sentiment': financial_sentiment
                },
                'adjusted_sentiment': {
                    'label': adjusted_label,
                    'score': adjusted_sentiment,
                    'confidence': sentiment_result.get('confidence', 0.5)
                }
            }
        else:
            return {
                'original_sentiment': sentiment_result,
                'financial_context': None,
                'adjusted_sentiment': sentiment_result
            }
    
    async def analyze_stock_sentiment(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """주식 센티먼트 분석"""
        try:
            # 주식 관련 텍스트 수집
            texts = await self._collect_stock_texts(symbol, hours)
            
            if not texts:
                return {
                    'symbol': symbol,
                    'error': 'No texts found for analysis',
                    'sentiment': None
                }
            
            # 다중 모델 센티먼트 분석
            sentiment_result = await self.analyze_sentiment_multi_model(texts, context="stock")
            
            # 결과에 심볼 정보 추가
            sentiment_result['symbol'] = symbol
            sentiment_result['analysis_time'] = datetime.now().isoformat()
            sentiment_result['text_count'] = len(texts)
            
            return sentiment_result
            
        except Exception as e:
            self.logger.error(f"Stock sentiment analysis error for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'error': str(e),
                'sentiment': None
            }
    
    async def _collect_stock_texts(self, symbol: str, hours: int) -> List[str]:
        """주식 관련 텍스트 수집"""
        # 실제 구현에서는 Reddit, Twitter 등에서 텍스트 수집
        # 여기서는 예시 데이터 반환
        return [
            f"I think {symbol} is going to the moon! 🚀",
            f"{symbol} stock is looking bearish, might sell",
            f"HODL {symbol} for the long term!",
            f"{symbol} earnings report was better than expected",
            f"Concerned about {symbol} short term prospects"
        ]
```

### 2.2 상관관계 분석 고도화

#### 2.2.1 고급 상관관계 분석기
```python
# correlation/advanced_correlation_analyzer.py
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

class AdvancedCorrelationAnalyzer:
    def __init__(self, data_collection_manager):
        self.data_collection_manager = data_collection_manager
        self.logger = logging.getLogger(__name__)
        
        # 분석 파라미터
        self.analysis_windows = {
            'short_term': 7,    # 7일
            'medium_term': 30,   # 30일
            'long_term': 90      # 90일
        }
        
        # 상관관계 임계값
        self.correlation_thresholds = {
            'weak': 0.3,
            'moderate': 0.5,
            'strong': 0.7
        }
    
    async def analyze_stock_sentiment_correlation(self, symbol: str, window: str = 'medium_term') -> Dict[str, Any]:
        """주식-센티먼트 상관관계 분석"""
        try:
            # 분석 기간 설정
            days = self.analysis_windows.get(window, 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 주식 가격 데이터 조회
            price_data = await self.data_collection_manager.get_stock_price_history(
                symbol, start_date, end_date
            )
            
            # 센티먼트 데이터 조회
            sentiment_data = await self.data_collection_manager.get_sentiment_history(
                symbol, start_date, end_date
            )
            
            if not price_data or not sentiment_data:
                return {
                    'symbol': symbol,
                    'window': window,
                    'error': 'Insufficient data for analysis',
                    'correlation': None
                }
            
            # 데이터 정렬 및 병합
            merged_data = self._merge_price_sentiment_data(price_data, sentiment_data)
            
            if len(merged_data) < 10:  # 최소 10개 데이터 포인트 필요
                return {
                    'symbol': symbol,
                    'window': window,
                    'error': 'Insufficient merged data points',
                    'correlation': None
                }
            
            # 상관관계 분석
            correlation_results = self._calculate_correlation(merged_data)
            
            # 지연 상관관계 분석
            lag_correlation_results = self._calculate_lag_correlation(merged_data)
            
            # 결과 조합
            return {
                'symbol': symbol,
                'window': window,
                'data_points': len(merged_data),
                'analysis_date': datetime.now().isoformat(),
                'correlation': correlation_results,
                'lag_correlation': lag_correlation_results,
                'interpretation': self._interpret_correlation(correlation_results)
            }
            
        except Exception as e:
            self.logger.error(f"Correlation analysis error for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'window': window,
                'error': str(e),
                'correlation': None
            }
    
    def _merge_price_sentiment_data(self, price_data: List[Dict], sentiment_data: List[Dict]) -> pd.DataFrame:
        """주식 가격과 센티먼트 데이터 병합"""
        # 데이터프레임 변환
        price_df = pd.DataFrame(price_data)
        sentiment_df = pd.DataFrame(sentiment_data)
        
        # 날짜 컬럼 변환
        price_df['date'] = pd.to_datetime(price_df['date'])
        sentiment_df['date'] = pd.to_datetime(sentiment_df['date'])
        
        # 날짜 기준 병합
        merged_df = pd.merge(
            price_df[['date', 'close_price']],
            sentiment_df[['date', 'overall_sentiment']],
            on='date',
            how='inner'
        )
        
        return merged_df
    
    def _calculate_correlation(self, data: pd.DataFrame) -> Dict[str, Any]:
        """상관관계 계산"""
        # 피어슨 상관계수
        pearson_corr, pearson_p = stats.pearsonr(
            data['close_price'], 
            data['overall_sentiment']
        )
        
        # 스피어먼 상관계수
        spearman_corr, spearman_p = stats.spearmanr(
            data['close_price'], 
            data['overall_sentiment']
        )
        
        # 켄달의 타우 상관계수
        kendall_corr, kendall_p = stats.kendalltau(
            data['close_price'], 
            data['overall_sentiment']
        )
        
        return {
            'pearson': {
                'correlation': pearson_corr,
                'p_value': pearson_p,
                'significant': pearson_p < 0.05,
                'strength': self._get_correlation_strength(abs(pearson_corr))
            },
            'spearman': {
                'correlation': spearman_corr,
                'p_value': spearman_p,
                'significant': spearman_p < 0.05,
                'strength': self._get_correlation_strength(abs(spearman_corr))
            },
            'kendall': {
                'correlation': kendall_corr,
                'p_value': kendall_p,
                'significant': kendall_p < 0.05,
                'strength': self._get_correlation_strength(abs(kendall_corr))
            }
        }
    
    def _calculate_lag_correlation(self, data: pd.DataFrame, max_lag: int = 5) -> Dict[str, Any]:
        """지연 상관관계 계산"""
        lag_results = {}
        
        for lag in range(0, max_lag + 1):
            if lag == 0:
                # 지연 없는 상관관계
                corr, p = stats.pearsonr(
                    data['close_price'], 
                    data['overall_sentiment']
                )
            else:
                # 지연 상관관계 (센티먼트가 주식 가격에 선행)
                if len(data) > lag:
                    corr, p = stats.pearsonr(
                        data['close_price'].iloc[lag:], 
                        data['overall_sentiment'].iloc[:-lag]
                    )
                else:
                    corr, p = 0, 1
            
            lag_results[f'lag_{lag}'] = {
                'correlation': corr,
                'p_value': p,
                'significant': p < 0.05
            }
        
        # 최적 지연 찾기
        best_lag = max(
            lag_results.keys(),
            key=lambda x: abs(lag_results[x]['correlation']) if lag_results[x]['significant'] else 0
        )
        
        return {
            'lag_results': lag_results,
            'best_lag': best_lag,
            'best_correlation': lag_results[best_lag]['correlation']
        }
    
    def _get_correlation_strength(self, correlation: float) -> str:
        """상관관계 강도 분류"""
        abs_corr = abs(correlation)
        
        if abs_corr >= self.correlation_thresholds['strong']:
            return 'strong'
        elif abs_corr >= self.correlation_thresholds['moderate']:
            return 'moderate'
        elif abs_corr >= self.correlation_thresholds['weak']:
            return 'weak'
        else:
            return 'very_weak'
    
    def _interpret_correlation(self, correlation_results: Dict[str, Any]) -> Dict[str, Any]:
        """상관관계 결과 해석"""
        pearson_result = correlation_results.get('pearson', {})
        correlation = pearson_result.get('correlation', 0)
        p_value = pearson_result.get('p_value', 1)
        strength = pearson_result.get('strength', 'very_weak')
        
        interpretation = {
            'summary': '',
            'relationship': '',
            'significance': '',
            'trading_implication': ''
        }
        
        # 관계 방향
        if correlation > 0:
            interpretation['relationship'] = 'positive'
            interpretation['summary'] = f"Stock price and sentiment have a positive {strength} correlation"
        elif correlation < 0:
            interpretation['relationship'] = 'negative'
            interpretation['summary'] = f"Stock price and sentiment have a negative {strength} correlation"
        else:
            interpretation['relationship'] = 'no_correlation'
            interpretation['summary'] = "No significant correlation between stock price and sentiment"
        
        # 통계적 유의성
        if p_value < 0.05:
            interpretation['significance'] = 'statistically_significant'
        else:
            interpretation['significance'] = 'not_statistically_significant'
        
        # 트레이딩 시사점
        if strength in ['strong', 'moderate'] and p_value < 0.05:
            if correlation > 0:
                interpretation['trading_implication'] = (
                    "Positive sentiment may precede price increases. "
                    "Consider buying when sentiment turns positive."
                )
            else:
                interpretation['trading_implication'] = (
                    "Negative sentiment may precede price decreases. "
                    "Consider selling when sentiment turns negative."
                )
        else:
            interpretation['trading_implication'] = (
                "Weak or no correlation. Sentiment may not be a reliable price predictor."
            )
        
        return interpretation
    
    async def analyze_multi_stock_correlation(self, symbols: List[str]) -> Dict[str, Any]:
        """다중 주식 상관관계 분석"""
        try:
            # 각 주식별 센티먼트 데이터 조회
            sentiment_data = {}
            for symbol in symbols:
                symbol_sentiment = await self.data_collection_manager.get_sentiment_history(
                    symbol, 
                    datetime.now() - timedelta(days=30),
                    datetime.now()
                )
                if symbol_sentiment:
                    sentiment_data[symbol] = symbol_sentiment
            
            if len(sentiment_data) < 2:
                return {
                    'error': 'Insufficient symbols with sentiment data',
                    'correlation_matrix': None
                }
            
            # 상관관계 행렬 계산
            correlation_matrix = self._calculate_sentiment_correlation_matrix(sentiment_data)
            
            # 클러스터링 분석
            cluster_results = self._perform_sentiment_clustering(correlation_matrix, symbols)
            
            return {
                'symbols': symbols,
                'analysis_date': datetime.now().isoformat(),
                'correlation_matrix': correlation_matrix,
                'clusters': cluster_results,
                'interpretation': self._interpret_multi_stock_correlation(correlation_matrix, symbols)
            }
            
        except Exception as e:
            self.logger.error(f"Multi-stock correlation analysis error: {str(e)}")
            return {
                'error': str(e),
                'correlation_matrix': None
            }
    
    def _calculate_sentiment_correlation_matrix(self, sentiment_data: Dict[str, List[Dict]], symbols: List[str]) -> np.ndarray:
        """센티먼트 상관관계 행렬 계산"""
        # 데이터프레임 생성
        df_data = {}
        
        for symbol in symbols:
            if symbol in sentiment_data:
                # 일별 평균 센티먼트 계산
                symbol_df = pd.DataFrame(sentiment_data[symbol])
                symbol_df['date'] = pd.to_datetime(symbol_df['date'])
                
                # 일별 평균
                daily_sentiment = symbol_df.groupby('date')['overall_sentiment'].mean()
                df_data[symbol] = daily_sentiment
        
        # 공통 날짜 기준 병합
        merged_df = pd.DataFrame(df_data)
        merged_df = merged_df.dropna()
        
        # 상관관계 행렬 계산
        correlation_matrix = merged_df.corr()
        
        return correlation_matrix.values
    
    def _perform_sentiment_clustering(self, correlation_matrix: np.ndarray, symbols: List[str]) -> Dict[str, Any]:
        """센티먼트 기반 클러스터링"""
        # 거리 행렬 계산 (1 - 상관관계)
        distance_matrix = 1 - np.abs(correlation_matrix)
        
        # 계층적 클러스터링
        from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
        
        # 링키지 생성
        linkage_matrix = linkage(distance_matrix, method='average')
        
        # 클러스터 할당 (3개 클러스터)
        clusters = fcluster(linkage_matrix, t=3, criterion='maxclust')
        
        # 클러스터 결과 정리
        cluster_results = {}
        for i, cluster_id in enumerate(clusters):
            if cluster_id not in cluster_results:
                cluster_results[cluster_id] = []
            cluster_results[cluster_id].append(symbols[i])
        
        return {
            'linkage_matrix': linkage_matrix.tolist(),
            'clusters': {f'cluster_{k}': v for k, v in cluster_results.items()},
            'cluster_count': len(cluster_results)
        }
    
    def _interpret_multi_stock_correlation(self, correlation_matrix: np.ndarray, symbols: List[str]) -> Dict[str, Any]:
        """다중 주식 상관관계 해석"""
        # 가장 높은 상관관계 쌍 찾기
        max_corr = 0
        max_corr_pair = None
        
        n = len(symbols)
        for i in range(n):
            for j in range(i+1, n):
                corr = abs(correlation_matrix[i][j])
                if corr > max_corr:
                    max_corr = corr
                    max_corr_pair = (symbols[i], symbols[j])
        
        # 가장 낮은 상관관계 쌍 찾기
        min_corr = 1
        min_corr_pair = None
        
        for i in range(n):
            for j in range(i+1, n):
                corr = abs(correlation_matrix[i][j])
                if corr < min_corr:
                    min_corr = corr
                    min_corr_pair = (symbols[i], symbols[j])
        
        return {
            'highest_correlation': {
                'pair': max_corr_pair,
                'correlation': max_corr,
                'strength': self._get_correlation_strength(max_corr)
            },
            'lowest_correlation': {
                'pair': min_corr_pair,
                'correlation': min_corr,
                'strength': self._get_correlation_strength(min_corr)
            },
            'average_correlation': np.mean(np.abs(correlation_matrix[np.triu_indices(n, k=1)]))
        }
```

## 3. 실시간 대시보드 고도화

### 3.1 통합 실시간 대시보드
```python
# dashboard/realtime_dashboard.py
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

class RealtimeDashboard:
    def __init__(self, websocket_manager, data_collection_manager):
        self.websocket_manager = websocket_manager
        self.data_collection_manager = data_collection_manager
        self.logger = logging.getLogger(__name__)
        
        # 대시보드 데이터 캐시
        self.dashboard_cache = {}
        self.cache_ttl = 60  # 60초
        
        # 대시보드 구성
        self.dashboard_config = {
            'refresh_interval': 30,  # 30초
            'max_trending_stocks': 10,
            'max_watchlist_items': 20,
            'chart_data_points': 100
        }
    
    async def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """대시보드 데이터 조회"""
        try:
            # 캐시 확인
            cache_key = f"dashboard_{user_id}"
            if cache_key in self.dashboard_cache:
                cached_data, timestamp = self.dashboard_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self.cache_ttl:
                    return cached_data
            
            # 데이터 수집
            dashboard_data = await self._collect_dashboard_data(user_id)
            
            # 캐시 저장
            self.dashboard_cache[cache_key] = (dashboard_data, datetime.now())
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Dashboard data collection error: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _collect_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """대시보드 데이터 수집"""
        # 병렬로 데이터 수집
        tasks = [
            self._get_user_watchlist(user_id),
            self._get_trending_stocks(),
            self._get_market_overview(),
            self._get_sentiment_summary(),
            self._get_price_alerts(user_id)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 정리
        watchlist = results[0] if not isinstance(results[0], Exception) else []
        trending_stocks = results[1] if not isinstance(results[1], Exception) else []
        market_overview = results[2] if not isinstance(results[2], Exception) else {}
        sentiment_summary = results[3] if not isinstance(results[3], Exception) else {}
        price_alerts = results[4] if not isinstance(results[4], Exception) else []
        
        return {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'watchlist': watchlist,
            'trending_stocks': trending_stocks,
            'market_overview': market_overview,
            'sentiment_summary': sentiment_summary,
            'price_alerts': price_alerts,
            'last_updated': datetime.now().isoformat()
        }
    
    async def _get_user_watchlist(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자 관심종목 조회"""
        # 실제 구현에서는 데이터베이스에서 사용자 관심종목 조회
        # 여기서는 예시 데이터 반환
        watchlist_symbols = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN']
        
        watchlist_data = []
        for symbol in watchlist_symbols:
            # 주식 정보 조회
            stock_info = await self.data_collection_manager.get_stock_info(symbol)
            
            if stock_info:
                # 센티먼트 정보 조회
                sentiment_info = await self.data_collection_manager.get_latest_sentiment(symbol)
                
                watchlist_data.append({
                    'symbol': symbol,
                    'company_name': stock_info.get('company_name', ''),
                    'current_price': stock_info.get('current_price', 0),
                    'change_percent': stock_info.get('change_percent', 0),
                    'sentiment': sentiment_info.get('overall_sentiment', 0) if sentiment_info else 0,
                    'sentiment_label': self._get_sentiment_label(
                        sentiment_info.get('overall_sentiment', 0) if sentiment_info else 0
                    ),
                    'last_updated': stock_info.get('last_updated', datetime.now().isoformat())
                })
        
        return watchlist_data
    
    async def _get_trending_stocks(self) -> List[Dict[str, Any]]:
        """트렌딩 주식 조회"""
        # 트렌딩 감지기 호출
        from app.services.trending.advanced_trending_detector import AdvancedTrendingDetector
        
        trending_detector = AdvancedTrendingDetector(self.data_collection_manager)
        trending_stocks = await trending_detector.detect_trending_stocks()
        
        # 상위 N개만 반환
        return trending_stocks[:self.dashboard_config['max_trending_stocks']]
    
    async def _get_market_overview(self) -> Dict[str, Any]:
        """시장 개요 조회"""
        try:
            # 주요 지수 데이터 조회
            market_indices = ['^GSPC', '^DJI', '^IXIC']  # S&P 500, Dow Jones, NASDAQ
            
            indices_data = []
            for index_symbol in market_indices:
                index_info = await self.data_collection_manager.get_stock_info(index_symbol)
                
                if index_info:
                    indices_data.append({
                        'symbol': index_symbol,
                        'name': self._get_index_name(index_symbol),
                        'current_price': index_info.get('current_price', 0),
                        'change_percent': index_info.get('change_percent', 0),
                        'last_updated': index_info.get('last_updated', datetime.now().isoformat())
                    })
            
            # 시장 센티먼트 요약
            market_sentiment = await self._get_market_sentiment_summary()
            
            return {
                'indices': indices_data,
                'market_sentiment': market_sentiment,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Market overview error: {str(e)}")
            return {}
    
    async def _get_sentiment_summary(self) -> Dict[str, Any]:
        """센티먼트 요약 조회"""
        try:
            # 전체 시장 센티먼트 분석
            market_sentiment = await self.data_collection_manager.get_market_sentiment_summary()
            
            # 센티먼트 분포
            sentiment_distribution = {
                'positive': 0,
                'neutral': 0,
                'negative': 0
            }
            
            if market_sentiment:
                for sentiment_data in market_sentiment:
                    sentiment_score = sentiment_data.get('overall_sentiment', 0)
                    label = self._get_sentiment_label(sentiment_score)
                    sentiment_distribution[label] += 1
            
            return {
                'distribution': sentiment_distribution,
                'average_sentiment': np.mean([
                    s.get('overall_sentiment', 0) for s in market_sentiment
                ]) if market_sentiment else 0,
                'total_analyzed': len(market_sentiment),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Sentiment summary error: {str(e)}")
            return {}
    
    async def _get_price_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """가격 알림 조회"""
        # 실제 구현에서는 데이터베이스에서 사용자 알림 조회
        # 여기서는 예시 데이터 반환
        return [
            {
                'id': 'alert_1',
                'symbol': 'AAPL',
                'type': 'price_above',
                'threshold': 150.0,
                'current_price': 152.3,
                'triggered': True,
                'message': 'AAPL crossed above $150.00',
                'created_at': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'id': 'alert_2',
                'symbol': 'TSLA',
                'type': 'sentiment_change',
                'threshold': 0.5,
                'current_sentiment': 0.7,
                'triggered': True,
                'message': 'TSLA sentiment increased significantly',
                'created_at': (datetime.now() - timedelta(hours=4)).isoformat()
            }
        ]
    
    def _get_sentiment_label(self, sentiment_score: float) -> str:
        """센티먼트 레이블 반환"""
        if sentiment_score > 0.1:
            return 'positive'
        elif sentiment_score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def _get_index_name(self, index_symbol: str) -> str:
        """지수 이름 반환"""
        index_names = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ'
        }
        return index_names.get(index_symbol, index_symbol)
    
    async def start_dashboard_updates(self):
        """대시보드 실시간 업데이트 시작"""
        self.logger.info("Starting dashboard real-time updates")
        
        # 주기적 업데이트 작업자 실행
        asyncio.create_task(self._dashboard_update_worker())
    
    async def _dashboard_update_worker(self):
        """대시보드 업데이트 작업자"""
        while True:
            try:
                # 모든 활성 사용자에게 대시보드 업데이트 전송
                await self._broadcast_dashboard_updates()
                
                # 다음 업데이트 대기
                await asyncio.sleep(self.dashboard_config['refresh_interval'])
                
            except Exception as e:
                self.logger.error(f"Dashboard update error: {str(e)}")
                await asyncio.sleep(self.dashboard_config['refresh_interval'])
    
    async def _broadcast_dashboard_updates(self):
        """대시보드 업데이트 브로드캐스트"""
        # 실제 구현에서는 활성 사용자 목록 조회
        # 여기서는 예시로 모든 사용자에게 업데이트
        active_users = ['user1', 'user2', 'user3']
        
        for user_id in active_users:
            try:
                # 대시보드 데이터 조회
                dashboard_data = await self.get_dashboard_data(user_id)
                
                # WebSocket으로 전송
                await self.websocket_manager.broadcast_to_topic('dashboard_updates', {
                    'user_id': user_id,
                    'dashboard_data': dashboard_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Dashboard update error for user {user_id}: {str(e)}")
```

## 4. 결론

이 문서에서는 InsiteChart 시스템의 고급 실시간 기능 확장을 위한 상세한 구현 방안을 제시했습니다. 주요 개선 사항은 다음과 같습니다:

1. **실시간 데이터 동기화 강화**: 웹소켓 기반의 실시간 데이터 스트리밍 시스템을 구현하여 사용자에게 즉각적인 정보를 제공합니다.

2. **고급 센티먼트 분석**: BERT, RoBERTa, DistilBERT 등 다중 모델을 활용한 정교한 센티먼트 분석 시스템을 구축합니다.

3. **상관관계 분석 고도화**: 주식 가격과 소셜 센티먼트 간의 복잡한 상관관계를 분석하여 투자 결정에 유용한 인사이트를 제공합니다.

4. **실시간 대시보드**: 통합된 실시간 대시보드를 통해 사용자가 시장 상황을 한눈에 파악할 수 있도록 합니다.

이러한 고급 기능들을 통해 InsiteChart는 단순한 주식 검색 도구를 넘어, 실시간 시장 분석과 예측을 제공하는 종합적인 투자 플랫폼으로 발전할 수 있을 것입니다.