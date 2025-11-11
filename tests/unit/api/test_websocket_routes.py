"""
WebSocket 라우트 단위 테스트

이 모듈은 WebSocket 관련 API 엔드포인트의 개별 기능을 테스트합니다.
"""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect

from backend.api.websocket_routes import router
from backend.services.realtime_notification_service import (
    NotificationSubscription,
    Notification,
    NotificationType,
    NotificationPriority
)


class TestWebSocketRoutes:
    """WebSocket 라우트 단위 테스트 클래스"""
    
    @pytest.fixture
    def app(self):
        """FastAPI 애플리케이션 픽스처"""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app
    
    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트 픽스처"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_notification_service(self):
        """모의 알림 서비스 픽스처"""
        service = MagicMock()
        service.connect = AsyncMock(return_value=None)
        service.disconnect = AsyncMock(return_value=None)
        service.subscribe = AsyncMock(return_value=None)
        service.get_user_notifications = AsyncMock(return_value=[])
        service.mark_notification_read = AsyncMock(return_value=None)
        service.create_notification = AsyncMock(return_value=None)
        service.get_system_stats = AsyncMock(return_value={})
        return service
    
    @pytest.fixture
    def sample_notification_subscription(self):
        """샘플 알림 구독 픽스처"""
        return NotificationSubscription(
            user_id="test_user",
            symbols=["AAPL", "GOOGL"],
            notification_types=[
                NotificationType.PRICE_ALERT,
                NotificationType.SENTIMENT_CHANGE
            ],
            price_threshold=150.0,
            sentiment_threshold=0.7
        )
    
    @pytest.fixture
    def sample_notification(self):
        """샘플 알림 픽스처"""
        return Notification(
            id="notif_001",
            type=NotificationType.PRICE_ALERT,
            priority=NotificationPriority.HIGH,
            title="Stock Price Alert",
            message="AAPL stock price reached $150.00",
            data={"symbol": "AAPL", "price": 150.0, "change": 2.5},
            timestamp=datetime.utcnow(),
            user_id="test_user",
            symbol="AAPL",
            is_read=False
        )
    
    def test_subscribe_notifications_rest_success(self, client, mock_notification_service, sample_notification_subscription):
        """REST API를 통한 알림 구독 성공 테스트"""
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post(
                "/api/notifications/subscribe",
                json=sample_notification_subscription.dict()
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Successfully subscribed to notifications"
            assert "subscription" in data
            assert "timestamp" in data
            
            # 서비스 호출 확인
            mock_notification_service.subscribe.assert_called_once()
    
    def test_subscribe_notifications_rest_error(self, client, mock_notification_service, sample_notification_subscription):
        """REST API를 통한 알림 구독 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_notification_service.subscribe.side_effect = Exception("Subscription failed")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post(
                "/api/notifications/subscribe",
                json=sample_notification_subscription.dict()
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Failed to subscribe to notifications"
    
    def test_get_notifications_success(self, client, mock_notification_service, sample_notification):
        """알림 목록 가져오기 성공 테스트"""
        # 모의 서비스 설정
        mock_notification_service.get_user_notifications.return_value = [sample_notification]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.get("/api/notifications/test_user")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert len(data["data"]) == 1
            assert data["count"] == 1
            
            notification = data["data"][0]
            assert notification["id"] == "notif_001"
            assert notification["type"] == "price_alert"
            assert notification["priority"] == "high"
            assert notification["title"] == "Stock Price Alert"
            assert notification["symbol"] == "AAPL"
            assert notification["is_read"] is False
    
    def test_get_notifications_unread_only(self, client, mock_notification_service, sample_notification):
        """읽지 않은 알림만 가져오기 테스트"""
        # 읽지 않은 알림과 읽은 알림 설정
        read_notification = Notification(
            id="notif_002",
            type=NotificationType.SENTIMENT_CHANGE,
            priority=NotificationPriority.MEDIUM,
            title="Sentiment Change",
            message="AAPL sentiment changed",
            timestamp=datetime.utcnow(),
            user_id="test_user",
            symbol="AAPL",
            is_read=True
        )
        
        mock_notification_service.get_user_notifications.return_value = [sample_notification, read_notification]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.get("/api/notifications/test_user?unread_only=true")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1  # 읽지 않은 알림만 반환
            assert data["data"][0]["id"] == "notif_001"
            assert data["data"][0]["is_read"] is False
    
    def test_get_notifications_error(self, client, mock_notification_service):
        """알림 목록 가져오기 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_notification_service.get_user_notifications.side_effect = Exception("Database error")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.get("/api/notifications/test_user")
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Failed to get notifications"
    
    def test_mark_notification_read_success(self, client, mock_notification_service):
        """알림 읽음 표시 성공 테스트"""
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post("/api/notifications/test_user/mark_read", json={"notification_id": "notif_001"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Notification marked as read"
            assert data["notification_id"] == "notif_001"
            assert "timestamp" in data
            
            # 서비스 호출 확인
            mock_notification_service.mark_notification_read.assert_called_once_with("test_user", "notif_001")
    
    def test_mark_notification_read_error(self, client, mock_notification_service):
        """알림 읽음 표시 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_notification_service.mark_notification_read.side_effect = Exception("Update failed")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post("/api/notifications/test_user/mark_read", json={"notification_id": "notif_001"})
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Failed to mark notification as read"
    
    def test_mark_all_notifications_read_success(self, client, mock_notification_service, sample_notification):
        """모든 알림 읽음 표시 성공 테스트"""
        # 읽지 않은 알림과 읽은 알림 설정
        read_notification = Notification(
            id="notif_002",
            type=NotificationType.SENTIMENT_CHANGE,
            priority=NotificationPriority.MEDIUM,
            title="Sentiment Change",
            message="AAPL sentiment changed",
            timestamp=datetime.utcnow(),
            user_id="test_user",
            symbol="AAPL",
            is_read=True
        )
        
        mock_notification_service.get_user_notifications.return_value = [sample_notification, read_notification]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post("/api/notifications/test_user/mark_all_read")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "All notifications marked as read"
            assert data["count"] == 1  # 읽지 않은 알림 수
            
            # 서비스 호출 확인
            assert mock_notification_service.mark_notification_read.call_count == 1
    
    def test_mark_all_notifications_read_error(self, client, mock_notification_service):
        """모든 알림 읽음 표시 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_notification_service.get_user_notifications.side_effect = Exception("Database error")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post("/api/notifications/test_user/mark_all_read")
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Failed to mark all notifications as read"
    
    def test_get_notification_stats_success(self, client, mock_notification_service):
        """알림 통계 가져오기 성공 테스트"""
        # 모의 통계 데이터
        stats = {
            "total_users": 100,
            "active_connections": 45,
            "total_notifications_today": 250,
            "notifications_by_type": {
                "price_alert": 120,
                "sentiment_change": 80,
                "system_notification": 50
            },
            "notifications_by_priority": {
                "high": 60,
                "medium": 120,
                "low": 70
            }
        }
        mock_notification_service.get_system_stats.return_value = stats
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.get("/api/notifications/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["total_users"] == 100
            assert data["data"]["active_connections"] == 45
            assert data["data"]["total_notifications_today"] == 250
            assert data["data"]["notifications_by_type"]["price_alert"] == 120
            assert data["data"]["notifications_by_priority"]["high"] == 60
    
    def test_get_notification_stats_error(self, client, mock_notification_service):
        """알림 통계 가져오기 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_notification_service.get_system_stats.side_effect = Exception("Stats error")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.get("/api/notifications/stats")
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Failed to get notification stats"
    
    def test_send_test_notification_success(self, client, mock_notification_service):
        """테스트 알림 전송 성공 테스트"""
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post("/api/notifications/test?user_id=test_user&message=Test message")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Test notification sent"
            assert "notification_id" in data
            assert "timestamp" in data
            
            # 서비스 호출 확인
            mock_notification_service.create_notification.assert_called_once()
            
            # 생성된 알림 확인
            call_args = mock_notification_service.create_notification.call_args[0][0]
            assert call_args.type == NotificationType.SYSTEM_NOTIFICATION
            assert call_args.priority == NotificationPriority.LOW
            assert call_args.title == "Test Notification"
            assert call_args.message == "Test message"
            assert call_args.user_id == "test_user"
            assert call_args.data["test"] is True
    
    def test_send_test_notification_error(self, client, mock_notification_service):
        """테스트 알림 전송 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_notification_service.create_notification.side_effect = Exception("Send failed")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            response = client.post("/api/notifications/test?user_id=test_user&message=Test message")
            
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Failed to send test notification"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_and_subscription(self, mock_notification_service, sample_notification_subscription):
        """WebSocket 연결 및 구독 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # 구독 메시지 설정
        subscribe_message = {
            "type": "subscribe",
            "data": sample_notification_subscription.dict()
        }
        websocket.receive_text.side_effect = [
            json.dumps(subscribe_message),
            WebSocketDisconnect()  # 연결 종료
        ]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except:
                pass  # WebSocketDisconnect 예외 무시
            
            # 연결 수락 확인
            websocket.accept.assert_called_once()
            
            # 서비스 연결 확인
            mock_notification_service.connect.assert_called_once_with(websocket, "test_user")
            
            # 구독 확인
            mock_notification_service.subscribe.assert_called_once()
            
            # 구독 확인 응답 확인
            websocket.send_text.assert_called()
            response_message = json.loads(websocket.send_text.call_args[0][0])
            assert response_message["type"] == "subscription_confirmed"
            assert "data" in response_message
            assert "timestamp" in response_message
            
            # 연결 해제 확인
            mock_notification_service.disconnect.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, mock_notification_service):
        """WebSocket ping/pong 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # ping 메시지 설정
        ping_message = {"type": "ping"}
        websocket.receive_text.side_effect = [
            json.dumps(ping_message),
            WebSocketDisconnect()  # 연결 종료
        ]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except:
                pass  # WebSocketDisconnect 예외 무시
            
            # pong 응답 확인
            websocket.send_text.assert_called()
            response_message = json.loads(websocket.send_text.call_args[0][0])
            assert response_message["type"] == "pong"
            assert "timestamp" in response_message
    
    @pytest.mark.asyncio
    async def test_websocket_get_history(self, mock_notification_service, sample_notification):
        """WebSocket 알림 기록 가져오기 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # 알림 기록 메시지 설정
        history_message = {"type": "get_history", "limit": 10}
        websocket.receive_text.side_effect = [
            json.dumps(history_message),
            WebSocketDisconnect()  # 연결 종료
        ]
        
        # 모의 서비스 설정
        mock_notification_service.get_user_notifications.return_value = [sample_notification]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except:
                pass  # WebSocketDisconnect 예외 무시
            
            # 알림 기록 응답 확인
            websocket.send_text.assert_called()
            response_message = json.loads(websocket.send_text.call_args[0][0])
            assert response_message["type"] == "notification_history"
            assert "data" in response_message
            assert len(response_message["data"]) == 1
            assert response_message["data"][0]["id"] == "notif_001"
            assert "timestamp" in response_message
    
    @pytest.mark.asyncio
    async def test_websocket_mark_read(self, mock_notification_service):
        """WebSocket 알림 읽음 표시 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # 읽음 표시 메시지 설정
        mark_read_message = {"type": "mark_read", "notification_id": "notif_001"}
        websocket.receive_text.side_effect = [
            json.dumps(mark_read_message),
            WebSocketDisconnect()  # 연결 종료
        ]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except:
                pass  # WebSocketDisconnect 예외 무시
            
            # 서비스 호출 확인
            mock_notification_service.mark_notification_read.assert_called_once_with("test_user", "notif_001")
            
            # 읽음 표시 응답 확인
            websocket.send_text.assert_called()
            response_message = json.loads(websocket.send_text.call_args[0][0])
            assert response_message["type"] == "notification_marked_read"
            assert response_message["notification_id"] == "notif_001"
            assert "timestamp" in response_message
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self, mock_notification_service):
        """WebSocket 잘못된 JSON 처리 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # 잘못된 JSON 메시지 설정
        websocket.receive_text.side_effect = [
            "invalid json",
            WebSocketDisconnect()  # 연결 종료
        ]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except:
                pass  # WebSocketDisconnect 예외 무시
            
            # 오류 응답 확인
            websocket.send_text.assert_called()
            response_message = json.loads(websocket.send_text.call_args[0][0])
            assert response_message["type"] == "error"
            assert response_message["message"] == "Invalid JSON format"
            assert "timestamp" in response_message
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self, mock_notification_service):
        """WebSocket 알 수 없는 메시지 타입 처리 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # 알 수 없는 메시지 타입 설정
        unknown_message = {"type": "unknown_type", "data": {}}
        websocket.receive_text.side_effect = [
            json.dumps(unknown_message),
            WebSocketDisconnect()  # 연결 종료
        ]
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except:
                pass  # WebSocketDisconnect 예외 무시
            
            # 오류 응답 확인
            websocket.send_text.assert_called()
            response_message = json.loads(websocket.send_text.call_args[0][0])
            assert response_message["type"] == "error"
            assert "unknown_type" in response_message["message"]
            assert "timestamp" in response_message
    
    @pytest.mark.asyncio
    async def test_websocket_connection_error(self, mock_notification_service):
        """WebSocket 연결 오류 처리 테스트"""
        # WebSocket 모의 객체 생성
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        
        # 연결 오류 설정
        websocket.accept.side_effect = Exception("Connection failed")
        
        with patch('backend.api.websocket_routes.get_notification_service', return_value=mock_notification_service):
            from backend.api.websocket_routes import websocket_notifications
            
            # WebSocket 핸들러 실행
            try:
                await websocket_notifications(websocket, "test_user")
            except Exception:
                pass  # 연결 오류 무시
            
            # 연결 시도 확인
            websocket.accept.assert_called_once()