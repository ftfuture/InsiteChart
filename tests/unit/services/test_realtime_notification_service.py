"""
RealtimeNotificationService 단위 테스트

실시간 알림 서비스의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from backend.services.realtime_notification_service import (
    RealtimeNotificationService,
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel,
    NotificationTemplate,
    NotificationRule,
    NotificationError
)


class TestNotification:
    """Notification 모델 테스트 클래스"""
    
    def test_notification_creation(self):
        """Notification 생성 테스트"""
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            data={"symbol": "AAPL", "price": 150.25, "threshold": 150.0},
            status=NotificationStatus.PENDING,
            created_at=datetime.utcnow(),
            scheduled_at=None
        )
        
        assert notification.id == "notif-123"
        assert notification.user_id == "user-456"
        assert notification.type == NotificationType.PRICE_ALERT
        assert notification.title == "Stock Price Alert"
        assert notification.message == "AAPL price has reached $150.25"
        assert notification.priority == NotificationPriority.HIGH
        assert NotificationChannel.EMAIL in notification.channels
        assert NotificationChannel.PUSH in notification.channels
        assert notification.data["symbol"] == "AAPL"
        assert notification.data["price"] == 150.25
        assert notification.data["threshold"] == 150.0
        assert notification.status == NotificationStatus.PENDING
        assert notification.scheduled_at is None
    
    def test_notification_to_dict(self):
        """Notification 딕셔너리 변환 테스트"""
        created_at = datetime.utcnow()
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25},
            status=NotificationStatus.PENDING,
            created_at=created_at
        )
        
        notification_dict = notification.to_dict()
        
        assert notification_dict["id"] == "notif-123"
        assert notification_dict["user_id"] == "user-456"
        assert notification_dict["type"] == "price_alert"
        assert notification_dict["title"] == "Stock Price Alert"
        assert notification_dict["message"] == "AAPL price has reached $150.25"
        assert notification_dict["priority"] == "high"
        assert notification_dict["channels"] == ["email"]
        assert notification_dict["data"]["symbol"] == "AAPL"
        assert notification_dict["data"]["price"] == 150.25
        assert notification_dict["status"] == "pending"
        assert notification_dict["created_at"] == created_at.isoformat()
    
    def test_notification_from_dict(self):
        """딕셔너리로부터 Notification 생성 테스트"""
        created_at = datetime.utcnow()
        notification_dict = {
            "id": "notif-123",
            "user_id": "user-456",
            "type": "price_alert",
            "title": "Stock Price Alert",
            "message": "AAPL price has reached $150.25",
            "priority": "high",
            "channels": ["email", "push"],
            "data": {"symbol": "AAPL", "price": 150.25},
            "status": "pending",
            "created_at": created_at.isoformat()
        }
        
        notification = Notification.from_dict(notification_dict)
        
        assert notification.id == "notif-123"
        assert notification.user_id == "user-456"
        assert notification.type == NotificationType.PRICE_ALERT
        assert notification.title == "Stock Price Alert"
        assert notification.message == "AAPL price has reached $150.25"
        assert notification.priority == NotificationPriority.HIGH
        assert NotificationChannel.EMAIL in notification.channels
        assert NotificationChannel.PUSH in notification.channels
        assert notification.data["symbol"] == "AAPL"
        assert notification.data["price"] == 150.25
        assert notification.status == NotificationStatus.PENDING


class TestNotificationTemplate:
    """NotificationTemplate 모델 테스트 클래스"""
    
    def test_notification_template_creation(self):
        """NotificationTemplate 생성 테스트"""
        template = NotificationTemplate(
            id="template-123",
            name="Price Alert Template",
            type=NotificationType.PRICE_ALERT,
            title_template="Price Alert for {symbol}",
            message_template="The price of {symbol} has reached {price}, exceeding your threshold of {threshold}",
            default_channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            default_priority=NotificationPriority.MEDIUM
        )
        
        assert template.id == "template-123"
        assert template.name == "Price Alert Template"
        assert template.type == NotificationType.PRICE_ALERT
        assert template.title_template == "Price Alert for {symbol}"
        assert template.message_template == "The price of {symbol} has reached {price}, exceeding your threshold of {threshold}"
        assert NotificationChannel.EMAIL in template.default_channels
        assert NotificationChannel.PUSH in template.default_channels
        assert template.default_priority == NotificationPriority.MEDIUM
    
    def test_notification_template_render(self):
        """NotificationTemplate 렌더링 테스트"""
        template = NotificationTemplate(
            id="template-123",
            name="Price Alert Template",
            type=NotificationType.PRICE_ALERT,
            title_template="Price Alert for {symbol}",
            message_template="The price of {symbol} has reached {price}, exceeding your threshold of {threshold}",
            default_channels=[NotificationChannel.EMAIL],
            default_priority=NotificationPriority.MEDIUM
        )
        
        # 테스트 실행
        title, message = template.render({
            "symbol": "AAPL",
            "price": 150.25,
            "threshold": 150.0
        })
        
        # 결과 검증
        assert title == "Price Alert for AAPL"
        assert message == "The price of AAPL has reached 150.25, exceeding your threshold of 150.0"


class TestNotificationRule:
    """NotificationRule 모델 테스트 클래스"""
    
    def test_notification_rule_creation(self):
        """NotificationRule 생성 테스트"""
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={
                "symbol": "AAPL",
                "price_above": 150.0
            },
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=True
        )
        
        assert rule.id == "rule-123"
        assert rule.user_id == "user-456"
        assert rule.name == "AAPL Price Alert"
        assert rule.type == NotificationType.PRICE_ALERT
        assert rule.conditions["symbol"] == "AAPL"
        assert rule.conditions["price_above"] == 150.0
        assert rule.template_id == "template-123"
        assert NotificationChannel.EMAIL in rule.channels
        assert rule.priority == NotificationPriority.HIGH
        assert rule.enabled is True
    
    def test_notification_rule_evaluate(self):
        """NotificationRule 평가 테스트"""
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={
                "symbol": "AAPL",
                "price_above": 150.0
            },
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=True
        )
        
        # 테스트 실행
        result1 = rule.evaluate({"symbol": "AAPL", "price": 150.25})  # 조건 만족
        result2 = rule.evaluate({"symbol": "AAPL", "price": 149.75})  # 조건 불만족
        result3 = rule.evaluate({"symbol": "GOOGL", "price": 2500.0})  # 심볼 불일치
        
        # 결과 검증
        assert result1 is True
        assert result2 is False
        assert result3 is False
    
    def test_notification_rule_disabled(self):
        """비활성화된 NotificationRule 평가 테스트"""
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={"symbol": "AAPL", "price_above": 150.0},
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=False  # 비활성화
        )
        
        # 테스트 실행
        result = rule.evaluate({"symbol": "AAPL", "price": 150.25})
        
        # 결과 검증
        assert result is False  # 비활성화된 규칙은 항상 False


class TestRealtimeNotificationService:
    """RealtimeNotificationService 테스트 클래스"""
    
    @pytest.fixture
    def mock_email_service(self):
        """모의 이메일 서비스"""
        service = AsyncMock()
        service.send_email.return_value = True
        return service
    
    @pytest.fixture
    def mock_push_service(self):
        """모의 푸시 서비스"""
        service = AsyncMock()
        service.send_push_notification.return_value = True
        return service
    
    @pytest.fixture
    def mock_sms_service(self):
        """모의 SMS 서비스"""
        service = AsyncMock()
        service.send_sms.return_value = True
        return service
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """모의 WebSocket 관리자"""
        manager = AsyncMock()
        manager.send_notification.return_value = True
        return manager
    
    @pytest.fixture
    def notification_service(self, mock_email_service, mock_push_service, mock_sms_service, mock_websocket_manager):
        """RealtimeNotificationService 인스턴스"""
        from unittest.mock import MagicMock
        
        # Create a mock cache manager
        mock_cache_manager = MagicMock()
        
        return RealtimeNotificationService(
            cache_manager=mock_cache_manager,
            email_service=mock_email_service,
            push_service=mock_push_service,
            sms_service=mock_sms_service,
            websocket_manager=mock_websocket_manager
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_single_channel(self, notification_service, mock_email_service):
        """단일 채널 알림 발송 테스트"""
        # 설정
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service.send_notification(notification)
        
        # 결과 검증
        assert result is True
        assert notification.status == NotificationStatus.SENT
        
        # 모의 호출 검증
        mock_email_service.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_multiple_channels(self, notification_service, mock_email_service, mock_push_service):
        """다중 채널 알림 발송 테스트"""
        # 설정
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service.send_notification(notification)
        
        # 결과 검증
        assert result is True
        assert notification.status == NotificationStatus.SENT
        
        # 모의 호출 검증
        mock_email_service.send_email.assert_called_once()
        mock_push_service.send_push_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_partial_failure(self, notification_service, mock_email_service, mock_push_service):
        """부분적 실패 알림 발송 테스트"""
        # 설정
        mock_email_service.send_email.return_value = True
        mock_push_service.send_push_notification.return_value = False  # 푸시 실패
        
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service.send_notification(notification)
        
        # 결과 검증
        assert result is True  # 하나 이상 성공하면 True
        assert notification.status == NotificationStatus.PARTIAL_SENT
        
        # 모의 호출 검증
        mock_email_service.send_email.assert_called_once()
        mock_push_service.send_push_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_all_channels_failed(self, notification_service, mock_email_service, mock_push_service):
        """모든 채널 실패 알림 발송 테스트"""
        # 설정
        mock_email_service.send_email.return_value = False
        mock_push_service.send_push_notification.return_value = False
        
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service.send_notification(notification)
        
        # 결과 검증
        assert result is False
        assert notification.status == NotificationStatus.FAILED
        
        # 모의 호출 검증
        mock_email_service.send_email.assert_called_once()
        mock_push_service.send_push_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_email_channel(self, notification_service, mock_email_service):
        """이메일 채널 알림 발송 테스트"""
        # 설정
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service._send_via_email(notification)
        
        # 결과 검증
        assert result is True
        
        # 모의 호출 검증
        mock_email_service.send_email.assert_called_once_with(
            user_id="user-456",
            subject="Stock Price Alert",
            body="AAPL price has reached $150.25"
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_push_channel(self, notification_service, mock_push_service):
        """푸시 채널 알림 발송 테스트"""
        # 설정
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.PUSH],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service._send_via_push(notification)
        
        # 결과 검증
        assert result is True
        
        # 모의 호출 검증
        mock_push_service.send_push_notification.assert_called_once_with(
            user_id="user-456",
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            data={"symbol": "AAPL", "price": 150.25}
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_sms_channel(self, notification_service, mock_sms_service):
        """SMS 채널 알림 발송 테스트"""
        # 설정
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.SMS],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service._send_via_sms(notification)
        
        # 결과 검증
        assert result is True
        
        # 모의 호출 검증
        mock_sms_service.send_sms.assert_called_once_with(
            user_id="user-456",
            message="AAPL price has reached $150.25"
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_websocket_channel(self, notification_service, mock_websocket_manager):
        """WebSocket 채널 알림 발송 테스트"""
        # 설정
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.WEBSOCKET],
            data={"symbol": "AAPL", "price": 150.25}
        )
        
        # 테스트 실행
        result = await notification_service._send_via_websocket(notification)
        
        # 결과 검증
        assert result is True
        
        # 모의 호출 검증
        mock_websocket_manager.send_notification.assert_called_once_with(
            user_id="user-456",
            notification=notification.to_dict()
        )
    
    @pytest.mark.asyncio
    async def test_create_notification_from_template(self, notification_service):
        """템플릿으로부터 알림 생성 테스트"""
        # 설정
        template = NotificationTemplate(
            id="template-123",
            name="Price Alert Template",
            type=NotificationType.PRICE_ALERT,
            title_template="Price Alert for {symbol}",
            message_template="The price of {symbol} has reached {price}, exceeding your threshold of {threshold}",
            default_channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            default_priority=NotificationPriority.MEDIUM
        )
        
        notification_service.templates["template-123"] = template
        
        # 테스트 실행
        notification = await notification_service.create_notification_from_template(
            template_id="template-123",
            user_id="user-456",
            data={"symbol": "AAPL", "price": 150.25, "threshold": 150.0}
        )
        
        # 결과 검증
        assert notification.user_id == "user-456"
        assert notification.type == NotificationType.PRICE_ALERT
        assert notification.title == "Price Alert for AAPL"
        assert notification.message == "The price of AAPL has reached 150.25, exceeding your threshold of 150.0"
        assert NotificationChannel.EMAIL in notification.channels
        assert NotificationChannel.PUSH in notification.channels
        assert notification.priority == NotificationPriority.MEDIUM
        assert notification.data["symbol"] == "AAPL"
        assert notification.data["price"] == 150.25
        assert notification.data["threshold"] == 150.0
    
    @pytest.mark.asyncio
    async def test_create_notification_from_template_not_found(self, notification_service):
        """존재하지 않는 템플릿으로 알림 생성 테스트"""
        # 테스트 실행
        with pytest.raises(NotificationError, match="Template not found"):
            await notification_service.create_notification_from_template(
                template_id="nonexistent-template",
                user_id="user-456",
                data={}
            )
    
    @pytest.mark.asyncio
    async def test_create_notification_from_template_render_error(self, notification_service):
        """템플릿 렌더링 오류 알림 생성 테스트"""
        # 설정
        template = NotificationTemplate(
            id="template-123",
            name="Price Alert Template",
            type=NotificationType.PRICE_ALERT,
            title_template="Price Alert for {symbol}",
            message_template="The price of {symbol} has reached {price}, exceeding your threshold of {threshold}",
            default_channels=[NotificationChannel.EMAIL],
            default_priority=NotificationPriority.MEDIUM
        )
        
        notification_service.templates["template-123"] = template
        
        # 테스트 실행 (필요한 데이터 누락)
        with pytest.raises(NotificationError, match="Template rendering failed"):
            await notification_service.create_notification_from_template(
                template_id="template-123",
                user_id="user-456",
                data={"symbol": "AAPL"}  # price와 threshold 누락
            )
    
    @pytest.mark.asyncio
    async def test_schedule_notification(self, notification_service):
        """예약 알림 테스트"""
        # 설정
        scheduled_time = datetime.utcnow() + timedelta(minutes=5)
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25},
            scheduled_at=scheduled_time
        )
        
        # 테스트 실행
        result = await notification_service.schedule_notification(notification)
        
        # 결과 검증
        assert result is True
        assert notification.id in notification_service.scheduled_notifications
        assert notification.status == NotificationStatus.SCHEDULED
    
    @pytest.mark.asyncio
    async def test_schedule_notification_past_time(self, notification_service):
        """과거 시간 예약 알림 테스트"""
        # 설정
        past_time = datetime.utcnow() - timedelta(minutes=5)
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25},
            scheduled_at=past_time
        )
        
        # 테스트 실행
        result = await notification_service.schedule_notification(notification)
        
        # 결과 검증
        assert result is False  # 과거 시간은 예약 불가
    
    @pytest.mark.asyncio
    async def test_cancel_scheduled_notification(self, notification_service):
        """예약된 알림 취소 테스트"""
        # 설정
        scheduled_time = datetime.utcnow() + timedelta(minutes=5)
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25},
            scheduled_at=scheduled_time
        )
        
        # 먼저 예약
        await notification_service.schedule_notification(notification)
        
        # 테스트 실행
        result = await notification_service.cancel_scheduled_notification("notif-123")
        
        # 결과 검증
        assert result is True
        assert "notif-123" not in notification_service.scheduled_notifications
    
    @pytest.mark.asyncio
    async def test_cancel_scheduled_notification_not_found(self, notification_service):
        """존재하지 않는 예약 알림 취소 테스트"""
        # 테스트 실행
        result = await notification_service.cancel_scheduled_notification("nonexistent-notif")
        
        # 결과 검증
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_scheduled_notifications(self, notification_service, mock_email_service):
        """예약된 알림 처리 테스트"""
        # 설정
        past_time = datetime.utcnow() - timedelta(minutes=1)
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25},
            scheduled_at=past_time
        )
        
        # 예약된 알림 추가
        notification_service.scheduled_notifications["notif-123"] = notification
        
        # 테스트 실행
        await notification_service._process_scheduled_notifications()
        
        # 결과 검증
        assert "notif-123" not in notification_service.scheduled_notifications  # 처리되어 제거됨
        assert notification.status == NotificationStatus.SENT  # 발송됨
        
        # 모의 호출 검증
        mock_email_service.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_scheduled_notifications_future_time(self, notification_service):
        """미래 시간 예약 알림 처리 테스트"""
        # 설정
        future_time = datetime.utcnow() + timedelta(minutes=5)
        notification = Notification(
            id="notif-123",
            user_id="user-456",
            type=NotificationType.PRICE_ALERT,
            title="Stock Price Alert",
            message="AAPL price has reached $150.25",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            data={"symbol": "AAPL", "price": 150.25},
            scheduled_at=future_time,
            status=NotificationStatus.SCHEDULED  # 명시적으로 상태 설정
        )
        
        # 예약된 알림 추가
        notification_service.scheduled_notifications["notif-123"] = notification
        
        # 테스트 실행
        await notification_service._process_scheduled_notifications()
        
        # 결과 검증
        assert "notif-123" in notification_service.scheduled_notifications  # 아직 처리되지 않음
        assert notification.status == NotificationStatus.SCHEDULED  # 상태 유지
    
    @pytest.mark.asyncio
    async def test_add_notification_rule(self, notification_service):
        """알림 규칙 추가 테스트"""
        # 설정
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={"symbol": "AAPL", "price_above": 150.0},
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=True
        )
        
        # 테스트 실행
        result = await notification_service.add_notification_rule(rule)
        
        # 결과 검증
        assert result is True
        assert "rule-123" in notification_service.notification_rules
        assert notification_service.notification_rules["rule-123"] == rule
    
    @pytest.mark.asyncio
    async def test_remove_notification_rule(self, notification_service):
        """알림 규칙 제거 테스트"""
        # 설정
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={"symbol": "AAPL", "price_above": 150.0},
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=True
        )
        
        # 먼저 규칙 추가
        await notification_service.add_notification_rule(rule)
        
        # 테스트 실행
        result = await notification_service.remove_notification_rule("rule-123")
        
        # 결과 검증
        assert result is True
        assert "rule-123" not in notification_service.notification_rules
    
    @pytest.mark.asyncio
    async def test_remove_notification_rule_not_found(self, notification_service):
        """존재하지 않는 알림 규칙 제거 테스트"""
        # 테스트 실행
        result = await notification_service.remove_notification_rule("nonexistent-rule")
        
        # 결과 검증
        assert result is False
    
    @pytest.mark.asyncio
    async def test_evaluate_rules(self, notification_service):
        """알림 규칙 평가 테스트"""
        # 설정
        template = NotificationTemplate(
            id="template-123",
            name="Price Alert Template",
            type=NotificationType.PRICE_ALERT,
            title_template="Price Alert for {symbol}",
            message_template="The price of {symbol} has reached {price}",
            default_channels=[NotificationChannel.EMAIL],
            default_priority=NotificationPriority.MEDIUM
        )
        
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={"symbol": "AAPL", "price_above": 150.0},
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=True
        )
        
        notification_service.templates["template-123"] = template
        await notification_service.add_notification_rule(rule)
        
        # 테스트 실행
        notifications = await notification_service.evaluate_rules({
            "symbol": "AAPL",
            "price": 150.25
        })
        
        # 결과 검증
        assert len(notifications) == 1
        assert notifications[0].user_id == "user-456"
        assert notifications[0].type == NotificationType.PRICE_ALERT
        assert notifications[0].title == "Price Alert for AAPL"
        assert notifications[0].message == "The price of AAPL has reached 150.25"
    
    @pytest.mark.asyncio
    async def test_evaluate_rules_no_match(self, notification_service):
        """일치하지 않는 알림 규칙 평가 테스트"""
        # 설정
        template = NotificationTemplate(
            id="template-123",
            name="Price Alert Template",
            type=NotificationType.PRICE_ALERT,
            title_template="Price Alert for {symbol}",
            message_template="The price of {symbol} has reached {price}",
            default_channels=[NotificationChannel.EMAIL],
            default_priority=NotificationPriority.MEDIUM
        )
        
        rule = NotificationRule(
            id="rule-123",
            user_id="user-456",
            name="AAPL Price Alert",
            type=NotificationType.PRICE_ALERT,
            conditions={"symbol": "AAPL", "price_above": 150.0},
            template_id="template-123",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            enabled=True
        )
        
        notification_service.templates["template-123"] = template
        await notification_service.add_notification_rule(rule)
        
        # 테스트 실행 (조건 불만족)
        notifications = await notification_service.evaluate_rules({
            "symbol": "AAPL",
            "price": 149.75  # 150.0 미만
        })
        
        # 결과 검증
        assert len(notifications) == 0
    
    @pytest.mark.asyncio
    async def test_get_notification_statistics(self, notification_service):
        """알림 통계 조회 테스트"""
        # 설정
        notification_service.total_notifications = 100
        notification_service.successful_notifications = 95
        notification_service.failed_notifications = 5
        notification_service.scheduled_count = 10
        
        # 테스트 실행
        stats = await notification_service.get_notification_statistics()
        
        # 결과 검증
        assert stats["total_notifications"] == 100
        assert stats["successful_notifications"] == 95
        assert stats["failed_notifications"] == 5
        assert stats["success_rate"] == 95.0
        assert stats["scheduled_count"] == 10
        assert stats["active_rules"] == 0
        assert stats["active_templates"] == 0
    
    def test_notification_error(self):
        """NotificationError 테스트"""
        # 테스트 실행
        error = NotificationError("Test error message")
        
        # 결과 검증
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    @pytest.mark.asyncio
    async def test_start_scheduler(self, notification_service):
        """스케줄러 시작 테스트"""
        # 테스트 실행
        await notification_service.start_scheduler()
        
        # 결과 검증
        assert notification_service.scheduler_running is True
        assert notification_service.scheduler_task is not None
        
        # 정리
        await notification_service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self, notification_service):
        """스케줄러 중지 테스트"""
        # 설정
        await notification_service.start_scheduler()
        
        # 테스트 실행
        await notification_service.stop_scheduler()
        
        # 결과 검증
        assert notification_service.scheduler_running is False
        assert notification_service.scheduler_task is None