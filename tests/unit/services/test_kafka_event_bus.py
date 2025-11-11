"""
KafkaEventBus 단위 테스트

Kafka 이벤트 버스의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from backend.services.kafka_event_bus import (
    KafkaEventBus,
    DataEvent as Event,
    EventType,
    EventPriority,
    EventSubscription
)


class TestEvent:
    """Event 모델 테스트 클래스"""
    
    def test_event_creation(self):
        """Event 생성 테스트"""
        event = Event(
            event_id="test-event-123",
            event_type="stock_price_update",
            source="yahoo_finance",
            data={"symbol": "AAPL", "price": 150.25},
            timestamp=datetime.utcnow().isoformat(),
            priority="high"
        )
        
        assert event.event_id == "test-event-123"
        assert event.event_type == "stock_price_update"
        assert event.source == "yahoo_finance"
        assert event.data["symbol"] == "AAPL"
        assert event.data["price"] == 150.25
        assert event.priority == "high"
    
    def test_event_to_dict(self):
        """Event 딕셔너리 변환 테스트"""
        timestamp = datetime.utcnow()
        event = Event(
            event_id="test-event-123",
            event_type="stock_price_update",
            source="yahoo_finance",
            data={"symbol": "AAPL", "price": 150.25},
            timestamp=timestamp.isoformat(),
            priority="high"
        )
        
        from dataclasses import asdict
        event_dict = asdict(event)
        
        assert event_dict["event_id"] == "test-event-123"
        assert event_dict["event_type"] == "stock_price_update"
        assert event_dict["source"] == "yahoo_finance"
        assert event_dict["data"]["symbol"] == "AAPL"
        assert event_dict["data"]["price"] == 150.25
        assert event_dict["priority"] == "high"
    
    def test_event_from_dict(self):
        """딕셔너리로부터 Event 생성 테스트"""
        timestamp = datetime.utcnow()
        event_dict = {
            "event_id": "test-event-123",
            "event_type": "stock_price_update",
            "source": "yahoo_finance",
            "data": {"symbol": "AAPL", "price": 150.25},
            "timestamp": timestamp.isoformat(),
            "priority": "high"
        }
        
        event = Event(**event_dict)
        
        assert event.event_id == "test-event-123"
        assert event.event_type == "stock_price_update"
        assert event.source == "yahoo_finance"
        assert event.data["symbol"] == "AAPL"
        assert event.data["price"] == 150.25
        assert event.priority == "high"


class TestEventSubscription:
    """EventSubscription 테스트 클래스"""
    
    def test_event_subscription_creation(self):
        """EventSubscription 생성 테스트"""
        def dummy_callback(event_data):
            pass
        
        subscription = EventSubscription(
            subscription_id="test-sub-123",
            event_type="stock_price_update",
            callback=dummy_callback,
            filter_criteria={"source": "yahoo_finance"}
        )
        
        assert subscription.subscription_id == "test-sub-123"
        assert subscription.event_type == "stock_price_update"
        assert subscription.callback == dummy_callback
        assert subscription.filter_criteria["source"] == "yahoo_finance"
        assert subscription.active is True


class TestKafkaEventBus:
    """KafkaEventBus 테스트 클래스"""
    
    @pytest.fixture
    def mock_producer(self):
        """모의 Kafka 프로듀서"""
        producer = AsyncMock()
        producer.send_and_wait.return_value = AsyncMock()
        producer.stop.return_value = None
        return producer
    
    @pytest.fixture
    def mock_consumer(self):
        """모의 Kafka 컨슈머"""
        consumer = AsyncMock()
        # 모의 메시지 생성
        mock_message = MagicMock()
        mock_message.value = {
            "event_id": "test-event-123",
            "event_type": "stock_price_update",
            "source": "yahoo_finance",
            "data": {"symbol": "AAPL", "price": 150.25},
            "timestamp": datetime.utcnow().isoformat(),
            "priority": "high"
        }
        mock_message.key = "test-event-123"
        
        consumer.getmany.return_value = {MagicMock(): [mock_message]}
        return consumer
    
    @pytest.fixture
    def event_bus(self):
        """KafkaEventBus 인스턴스"""
        return KafkaEventBus(
            bootstrap_servers="localhost:9092",
            topic_prefix="test",
            consumer_group="test-consumer-group"
        )
    
    @pytest.mark.asyncio
    async def test_publish_event_success(self, event_bus, mock_producer):
        """이벤트 발행 성공 테스트"""
        # 설정
        event = Event(
            event_id="test-event-123",
            event_type="stock_price_update",
            source="yahoo_finance",
            data={"symbol": "AAPL", "price": 150.25},
            timestamp=datetime.utcnow().isoformat(),
            priority="high"
        )
        
        # 테스트 실행
        result = await event_bus.publish(event)
        
        # 결과 검증
        assert result is True
        
        # 모의 호출 검증
        mock_producer.send_and_wait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_event_failure(self, event_bus, mock_producer):
        """이벤트 발행 실패 테스트"""
        # 설정
        mock_producer.send_and_wait.side_effect = Exception("Kafka connection failed")
        
        event = Event(
            event_id="test-event-123",
            event_type="stock_price_update",
            source="yahoo_finance",
            data={"symbol": "AAPL", "price": 150.25},
            timestamp=datetime.utcnow().isoformat()
        )
        
        # 테스트 실행
        result = await event_bus.publish(event)
        
        # 결과 검증
        assert result is False
    
    @pytest.mark.asyncio
    async def test_subscribe_to_topic(self, event_bus):
        """토픽 구독 테스트"""
        # 설정
        def event_handler(event_data):
            pass
        
        # 테스트 실행
        subscription_id = await event_bus.subscribe("stock_price_update", event_handler)
        
        # 결과 검증
        assert subscription_id is not None
        assert "stock_price_update" in event_bus.subscriptions
        assert len(event_bus.subscriptions["stock_price_update"]) == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic(self, event_bus):
        """토픽 구독 해지 테스트"""
        # 설정
        def event_handler(event_data):
            pass
        
        subscription_id = await event_bus.subscribe("stock_price_update", event_handler)
        
        # 테스트 실행
        result = await event_bus.unsubscribe(subscription_id)
        
        # 결과 검증
        assert result is True
    
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler(self, event_bus):
        """존재하지 않는 핸들러 구독 해지 테스트"""
        # 설정
        def event_handler(event_data):
            pass
        
        subscription_id = await event_bus.subscribe("stock_price_update", event_handler)
        
        # 테스트 실행
        result = await event_bus.unsubscribe("nonexistent-subscription-id")
        
        # 결과 검증
        assert result is False
    
    @pytest.mark.asyncio
    async def test_publish_stock_price_update(self, event_bus, mock_producer):
        """주식 가격 업데이트 이벤트 발행 테스트"""
        # 테스트 실행
        result = await event_bus.publish_stock_price_update(
            symbol="AAPL",
            price=150.25,
            change=2.5,
            change_percent=1.67
        )
        
        # 결과 검증
        assert result is True
        mock_producer.send_and_wait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_sentiment_update(self, event_bus, mock_producer):
        """감성 분석 업데이트 이벤트 발행 테스트"""
        # 테스트 실행
        result = await event_bus.publish_sentiment_update(
            symbol="AAPL",
            sentiment_score=0.75,
            mention_count=100
        )
        
        # 결과 검증
        assert result is True
        mock_producer.send_and_wait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_event_statistics(self, event_bus):
        """이벤트 통계 조회 테스트"""
        # 설정
        event_bus.event_stats["published"] = 100
        event_bus.event_stats["consumed"] = 95
        event_bus.event_stats["failed"] = 5
        
        # 테스트 실행
        stats = await event_bus.get_event_statistics()
        
        # 결과 검증
        assert stats["published"] == 100
        assert stats["consumed"] == 95
        assert stats["failed"] == 5
        assert stats["active_subscriptions"] == 0
        assert stats["connected"] is False
        assert stats["running"] is False
    
    @pytest.mark.asyncio
    async def test_close(self, event_bus, mock_producer, mock_consumer):
        """이벤트 버스 종료 테스트"""
        # 테스트 실행
        await event_bus.stop()
        
        # 결과 검증
        mock_producer.stop.assert_called_once()
        mock_consumer.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_system_alert(self, event_bus, mock_producer):
        """시스템 알림 이벤트 발행 테스트"""
        # 테스트 실행
        result = await event_bus.publish_system_alert(
            alert_type="high_cpu_usage",
            message="CPU usage exceeded 80%",
            severity="warning",
            details={"cpu_usage": 85.2, "threshold": 80.0}
        )
        
        # 결과 검증
        assert result is True
        mock_producer.send_and_wait.assert_called_once()