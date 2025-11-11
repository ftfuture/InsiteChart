"""
보안 API 라우트 단위 테스트

이 모듈은 보안 관련 API 엔드포인트의 개별 기능을 테스트합니다.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.security_routes import router
from backend.services.security_service import (
    SecurityEvent,
    SecurityRule,
    SecurityEventType,
    SecuritySeverity,
    SecurityAction,
    SecurityMetrics
)


class TestSecurityRoutes:
    """보안 API 라우트 단위 테스트 클래스"""
    
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
    def mock_security_service(self):
        """모의 보안 서비스 픽스처"""
        service = MagicMock()
        service.analyze_request = AsyncMock(return_value=[])
        service.get_recent_events = AsyncMock(return_value=[])
        service.get_security_metrics = AsyncMock(return_value=SecurityMetrics(
            total_events=0,
            events_by_type={},
            events_by_severity={},
            blocked_ips=0,
            rate_limited_requests=0,
            active_investigations=0,
            false_positives=0,
            detection_accuracy=0.0,
            last_updated=datetime.utcnow()
        ))
        service.add_security_rule = AsyncMock(return_value=None)
        service.update_security_rule = AsyncMock(return_value=None)
        service.block_ip = AsyncMock(return_value=None)
        service.unblock_ip = AsyncMock(return_value=None)
        service.is_ip_blocked = AsyncMock(return_value=False)
        service.blocked_ips = {}
        service.active_investigations = {}
        return service
    
    @pytest.fixture
    def sample_security_event(self):
        """샘플 보안 이벤트 픽스처"""
        return SecurityEvent(
            id="test_event_001",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            timestamp=datetime.utcnow(),
            source_ip="192.168.1.100",
            user_id="user123",
            user_agent="Mozilla/5.0 (Test Browser)",
            endpoint="/api/stocks",
            description="SQL injection attempt detected",
            metadata={"pattern": "sql_union"}
        )
    
    @pytest.fixture
    def admin_user_data(self):
        """관리자 사용자 데이터 픽스처"""
        return {"user_id": "admin_user", "role": "admin"}
    
    @pytest.fixture
    def regular_user_data(self):
        """일반 사용자 데이터 픽스처"""
        return {"user_id": "regular_user", "role": "user"}
    
    def test_analyze_request_security_success(self, client, mock_security_service):
        """보안 요청 분석 성공 테스트"""
        # 모의 서비스 설정
        mock_events = [
            SecurityEvent(
                id="test_event",
                event_type=SecurityEventType.INJECTION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_ip="192.168.1.100",
                description="Test injection attempt",
                response_actions=[SecurityAction.BLOCK_IP]
            )
        ]
        mock_security_service.analyze_request.return_value = mock_events
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value={"user_id": "test_user", "role": "user"}):
                response = client.post(
                    "/api/security/analyze-request",
                    headers={"Content-Type": "application/json"},
                    json={}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "events_detected" in data["data"]
                assert data["data"]["events_detected"] == 1
                assert len(data["data"]["events"]) == 1
                assert data["data"]["events"][0]["event_type"] == "injection_attempt"
                assert data["data"]["events"][0]["severity"] == "high"
                assert "block_ip" in data["data"]["events"][0]["response_actions"]
    
    def test_analyze_request_security_error(self, client, mock_security_service):
        """보안 요청 분석 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_security_service.analyze_request.side_effect = Exception("Analysis failed")
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value={"user_id": "test_user", "role": "user"}):
                response = client.post(
                    "/api/security/analyze-request",
                    headers={"Content-Type": "application/json"},
                    json={}
                )
                
                assert response.status_code == 500
                data = response.json()
                assert data["detail"] == "Internal server error"
    
    def test_get_security_events_admin_success(self, client, mock_security_service, sample_security_event, admin_user_data):
        """보안 이벤트 가져오기 (관리자) 성공 테스트"""
        # 모의 서비스 설정
        mock_security_service.get_recent_events.return_value = [sample_security_event]
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.get("/api/security/events")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "events" in data["data"]
                assert len(data["data"]["events"]) == 1
                assert data["data"]["events"][0]["id"] == "test_event_001"
                assert data["data"]["events"][0]["event_type"] == "injection_attempt"
                assert data["data"]["events"][0]["severity"] == "high"
                assert data["data"]["events"][0]["source_ip"] == "192.168.1.100"
    
    def test_get_security_events_regular_user_forbidden(self, client, mock_security_service, regular_user_data):
        """보안 이벤트 가져오기 (일반 사용자) 권한 없음 테스트"""
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=regular_user_data):
                response = client.get("/api/security/events")
                
                assert response.status_code == 403
                data = response.json()
                assert data["detail"] == "Admin access required"
    
    def test_get_security_metrics_admin_success(self, client, mock_security_service, admin_user_data):
        """보안 메트릭 가져오기 (관리자) 성공 테스트"""
        # 모의 서비스 설정
        mock_metrics = SecurityMetrics(
            total_events=100,
            events_by_type={"injection_attempt": 10, "xss_attempt": 5},
            events_by_severity={"high": 15, "medium": 30, "low": 55},
            blocked_ips=5,
            rate_limited_requests=20,
            active_investigations=2,
            false_positives=3,
            detection_accuracy=0.97,
            last_updated=datetime.utcnow()
        )
        mock_security_service.get_security_metrics.return_value = mock_metrics
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.get("/api/security/metrics")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["total_events"] == 100
                assert data["data"]["events_by_type"]["injection_attempt"] == 10
                assert data["data"]["events_by_severity"]["high"] == 15
                assert data["data"]["blocked_ips"] == 5
                assert data["data"]["rate_limited_requests"] == 20
                assert data["data"]["active_investigations"] == 2
                assert data["data"]["false_positives"] == 3
                assert data["data"]["detection_accuracy"] == 0.97
    
    def test_get_security_metrics_regular_user_forbidden(self, client, mock_security_service, regular_user_data):
        """보안 메트릭 가져오기 (일반 사용자) 권한 없음 테스트"""
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=regular_user_data):
                response = client.get("/api/security/metrics")
                
                assert response.status_code == 403
                data = response.json()
                assert data["detail"] == "Admin access required"
    
    def test_create_security_rule_admin_success(self, client, mock_security_service, admin_user_data):
        """보안 규칙 생성 (관리자) 성공 테스트"""
        rule_data = {
            "id": "test_rule",
            "name": "Test Rule",
            "event_type": "injection_attempt",
            "conditions": {"severity": "high"},
            "actions": ["block_ip", "alert_admin"],
            "severity": "high",
            "enabled": True,
            "cooldown_period": 300
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.post(
                    "/api/security/rules",
                    headers={"Content-Type": "application/json"},
                    json=rule_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["rule_id"] == "test_rule"
                assert data["data"]["name"] == "Test Rule"
                assert data["data"]["event_type"] == "injection_attempt"
                assert "block_ip" in data["data"]["actions"]
                assert "alert_admin" in data["data"]["actions"]
                assert data["data"]["severity"] == "high"
                assert data["data"]["enabled"] is True
                assert data["data"]["cooldown_period"] == 300
    
    def test_create_security_rule_regular_user_forbidden(self, client, mock_security_service, regular_user_data):
        """보안 규칙 생성 (일반 사용자) 권한 없음 테스트"""
        rule_data = {
            "id": "test_rule",
            "name": "Test Rule",
            "event_type": "injection_attempt",
            "actions": ["block_ip"]
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=regular_user_data):
                response = client.post(
                    "/api/security/rules",
                    headers={"Content-Type": "application/json"},
                    json=rule_data
                )
                
                assert response.status_code == 403
                data = response.json()
                assert data["detail"] == "Admin access required"
    
    def test_update_security_rule_admin_success(self, client, mock_security_service, admin_user_data):
        """보안 규칙 업데이트 (관리자) 성공 테스트"""
        updates = {
            "name": "Updated Rule Name",
            "enabled": False,
            "cooldown_period": 600
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.put(
                    "/api/security/rules/test_rule",
                    headers={"Content-Type": "application/json"},
                    json=updates
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["rule_id"] == "test_rule"
                assert data["data"]["updates"]["name"] == "Updated Rule Name"
                assert data["data"]["updates"]["enabled"] is False
                assert data["data"]["updates"]["cooldown_period"] == 600
    
    def test_update_security_rule_regular_user_forbidden(self, client, mock_security_service, regular_user_data):
        """보안 규칙 업데이트 (일반 사용자) 권한 없음 테스트"""
        updates = {"name": "Updated Rule Name"}
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=regular_user_data):
                response = client.put(
                    "/api/security/rules/test_rule",
                    headers={"Content-Type": "application/json"},
                    json=updates
                )
                
                assert response.status_code == 403
                data = response.json()
                assert data["detail"] == "Admin access required"
    
    def test_block_ip_address_admin_success(self, client, mock_security_service, admin_user_data):
        """IP 주소 차단 (관리자) 성공 테스트"""
        ip_data = {
            "ip_address": "192.168.1.100",
            "duration_hours": 24,
            "reason": "Test block"
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.post(
                    "/api/security/block-ip",
                    headers={"Content-Type": "application/json"},
                    json=ip_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["ip_address"] == "192.168.1.100"
                assert data["data"]["duration_hours"] == 24
                assert data["data"]["reason"] == "Test block"
                assert "blocked_at" in data["data"]
    
    def test_block_ip_address_missing_ip(self, client, mock_security_service, admin_user_data):
        """IP 주소 차단 (IP 주소 누락) 실패 테스트"""
        ip_data = {
            "duration_hours": 24,
            "reason": "Test block"
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.post(
                    "/api/security/block-ip",
                    headers={"Content-Type": "application/json"},
                    json=ip_data
                )
                
                assert response.status_code == 400
                data = response.json()
                assert data["detail"] == "IP address is required"
    
    def test_unblock_ip_address_admin_success(self, client, mock_security_service, admin_user_data):
        """IP 주소 차단 해제 (관리자) 성공 테스트"""
        ip_data = {"ip_address": "192.168.1.100"}
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.post(
                    "/api/security/unblock-ip",
                    headers={"Content-Type": "application/json"},
                    json=ip_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["ip_address"] == "192.168.1.100"
                assert "unblocked_at" in data["data"]
    
    def test_check_ip_status_admin_success(self, client, mock_security_service, admin_user_data):
        """IP 상태 확인 (관리자) 성공 테스트"""
        mock_security_service.is_ip_blocked.return_value = True
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.get("/api/security/ip-check/192.168.1.100")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["ip_address"] == "192.168.1.100"
                assert data["data"]["is_blocked"] is True
                assert "checked_at" in data["data"]
    
    def test_get_blocked_ips_admin_success(self, client, mock_security_service, admin_user_data):
        """차단된 IP 목록 가져오기 (관리자) 성공 테스트"""
        # 모의 차단된 IP 설정
        from datetime import datetime, timedelta
        mock_security_service.blocked_ips = {
            "192.168.1.100": datetime.utcnow() + timedelta(hours=24),
            "192.168.1.101": datetime.utcnow() + timedelta(hours=12)
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.get("/api/security/blocked-ips")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "blocked_ips" in data["data"]
                assert "total_blocked" in data["data"]
                assert len(data["data"]["blocked_ips"]) == 2
                assert data["data"]["total_blocked"] == 2
                
                # IP 주소 확인
                blocked_ips = data["data"]["blocked_ips"]
                ip_addresses = [ip["ip_address"] for ip in blocked_ips]
                assert "192.168.1.100" in ip_addresses
                assert "192.168.1.101" in ip_addresses
    
    def test_test_security_alert_admin_success(self, client, mock_security_service, admin_user_data):
        """테스트 보안 알림 생성 (관리자) 성공 테스트"""
        alert_data = {
            "event_type": "system_anomaly",
            "severity": "medium",
            "source_ip": "test_source",
            "description": "Test security alert",
            "metadata": {"test": True}
        }
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.post(
                    "/api/security/test-alert",
                    headers={"Content-Type": "application/json"},
                    json=alert_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "event_id" in data["data"]
                assert data["data"]["event_type"] == "system_anomaly"
                assert data["data"]["severity"] == "medium"
                assert data["data"]["description"] == "Test security alert"
                assert "created_at" in data["data"]
    
    def test_get_security_dashboard_admin_success(self, client, mock_security_service, admin_user_data):
        """보안 대시보드 가져오기 (관리자) 성공 테스트"""
        # 모의 서비스 설정
        mock_metrics = SecurityMetrics(
            total_events=100,
            events_by_type={"injection_attempt": 10, "xss_attempt": 5},
            events_by_severity={"high": 15, "medium": 30, "low": 55},
            blocked_ips=5,
            rate_limited_requests=20,
            active_investigations=2,
            false_positives=3,
            detection_accuracy=0.97,
            last_updated=datetime.utcnow()
        )
        mock_security_service.get_security_metrics.return_value = mock_metrics
        
        mock_events = [
            SecurityEvent(
                id=f"event_{i}",
                event_type=SecurityEventType.INJECTION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_ip=f"192.168.1.{100 + i}",
                description=f"Test event {i}"
            )
            for i in range(3)
        ]
        mock_security_service.get_recent_events.return_value = mock_events
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                response = client.get("/api/security/dashboard")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                
                # 개요 정보 확인
                overview = data["data"]["overview"]
                assert overview["total_events"] == 100
                assert overview["blocked_ips"] == 5
                assert overview["active_investigations"] == 2
                assert overview["detection_accuracy"] == 0.97
                
                # 최근 이벤트 확인
                recent_events = data["data"]["recent_events"]
                assert len(recent_events) == 3
                
                # 이벤트 통계 확인
                events_by_severity = data["data"]["events_by_severity"]
                assert events_by_severity["high"] == 15
                assert events_by_severity["medium"] == 30
                assert events_by_severity["low"] == 55
                
                events_by_type = data["data"]["events_by_type"]
                assert events_by_type["injection_attempt"] == 10
                assert events_by_type["xss_attempt"] == 5
    
    def test_get_security_dashboard_regular_user_forbidden(self, client, mock_security_service, regular_user_data):
        """보안 대시보드 가져오기 (일반 사용자) 권한 없음 테스트"""
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=regular_user_data):
                response = client.get("/api/security/dashboard")
                
                assert response.status_code == 403
                data = response.json()
                assert data["detail"] == "Admin access required"
    
    def test_analyze_request_with_body(self, client, mock_security_service):
        """요청 본문이 있는 보안 분석 테스트"""
        # 모의 서비스 설정
        mock_events = [
            SecurityEvent(
                id="test_event",
                event_type=SecurityEventType.INJECTION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_ip="192.168.1.100",
                description="Test injection attempt"
            )
        ]
        mock_security_service.analyze_request.return_value = mock_events
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value={"user_id": "test_user", "role": "user"}):
                # 요청 본문과 함께 POST 요청
                response = client.post(
                    "/api/security/analyze-request",
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Test Browser"
                    },
                    json={"query": "SELECT * FROM users"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["events_detected"] == 1
    
    def test_get_security_events_with_filters(self, client, mock_security_service, sample_security_event, admin_user_data):
        """필터와 함께 보안 이벤트 가져오기 테스트"""
        # 모의 서비스 설정
        mock_security_service.get_recent_events.return_value = [sample_security_event]
        
        with patch('backend.api.security_routes.get_security_service', return_value=mock_security_service):
            with patch('backend.api.security_routes.get_current_user', return_value=admin_user_data):
                # 필터와 함께 GET 요청
                response = client.get(
                    "/api/security/events?limit=10&severity=high&event_type=injection_attempt"
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "filters" in data["data"]
                assert data["data"]["filters"]["severity"] == "high"
                assert data["data"]["filters"]["event_type"] == "injection_attempt"
                assert data["data"]["filters"]["limit"] == 10