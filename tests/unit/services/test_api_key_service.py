"""
API 키 서비스 단위 테스트

이 모듈은 API 키 서비스의 개별 기능을 테스트합니다.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from backend.services.api_key_service import APIKeyService
from backend.models.unified_models import APIKey, APIKeyPermission


class TestAPIKeyService:
    """API 키 서비스 단위 테스트 클래스"""
    
    @pytest.fixture
    def api_key_service(self):
        """API 키 서비스 픽스처"""
        return APIKeyService()
    
    @pytest.fixture
    def mock_db_session(self):
        """모의 데이터베이스 세션 픽스처"""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.query = MagicMock()
        session.filter = MagicMock()
        session.first = MagicMock()
        session.all = MagicMock()
        session.delete = MagicMock()
        session.refresh = MagicMock()
        return session
    
    @pytest.mark.asyncio
    async def test_generate_api_key(self, api_key_service, mock_db_session):
        """API 키 생성 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # API 키 생성 요청
            key_request = {
                "name": "Test API Key",
                "description": "API key for testing",
                "permissions": ["read:stocks", "read:sentiment"],
                "rate_limit": 1000,
                "expires_days": 365
            }
            
            result = await api_key_service.generate_api_key(
                user_id="user123",
                **key_request
            )
            
            # 결과 확인
            assert result is not None
            assert "key_id" in result
            assert "api_key" in result
            assert "name" in result
            assert "permissions" in result
            assert "rate_limit" in result
            assert "expires_at" in result
            assert "created_at" in result
            
            # 생성된 키 확인
            assert result["name"] == "Test API Key"
            assert result["permissions"] == ["read:stocks", "read:sentiment"]
            assert result["rate_limit"] == 1000
            assert len(result["api_key"]) >= 32  # 최소 길이 확인
            
            # 데이터베이스 저장 확인
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_validate_api_key_valid(self, api_key_service, mock_db_session):
        """유효한 API 키 검증 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키 데이터
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_test_valid_key_123456789",
                name="Test Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS, APIKeyPermission.READ_SENTIMENT],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow(),
                last_used_at=None
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # API 키 검증
            result = await api_key_service.validate_api_key("sk_test_valid_key_123456789")
            
            assert result is not None
            assert result.is_valid is True
            assert result.key_id == "key123"
            assert result.name == "Test Key"
            assert result.user_id == "user123"
            assert len(result.permissions) == 2
            assert result.rate_limit == 1000
            assert result.is_active is True
    
    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, api_key_service, mock_db_session):
        """유효하지 않은 API 키 검증 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 존재하지 않는 API 키
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            # API 키 검증
            result = await api_key_service.validate_api_key("sk_invalid_key_123456789")
            
            assert result is not None
            assert result.is_valid is False
            assert result.error == "API key not found"
    
    @pytest.mark.asyncio
    async def test_validate_api_key_expired(self, api_key_service, mock_db_session):
        """만료된 API 키 검증 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 만료된 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_expired_key_123456789",
                name="Expired Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() - timedelta(days=1),  # 어제 만료
                created_at=datetime.utcnow() - timedelta(days=30),
                last_used_at=None
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # API 키 검증
            result = await api_key_service.validate_api_key("sk_expired_key_123456789")
            
            assert result is not None
            assert result.is_valid is False
            assert result.error == "API key expired"
    
    @pytest.mark.asyncio
    async def test_validate_api_key_inactive(self, api_key_service, mock_db_session):
        """비활성 API 키 검증 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 비활성 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_inactive_key_123456789",
                name="Inactive Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=False,  # 비활성
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow() - timedelta(days=10),
                last_used_at=None
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # API 키 검증
            result = await api_key_service.validate_api_key("sk_inactive_key_123456789")
            
            assert result is not None
            assert result.is_valid is False
            assert result.error == "API key is inactive"
    
    @pytest.mark.asyncio
    async def test_update_api_key_usage(self, api_key_service, mock_db_session):
        """API 키 사용량 업데이트 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_test_key_123456789",
                name="Test Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow() - timedelta(days=10),
                last_used_at=datetime.utcnow() - timedelta(hours=1)
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # 사용량 업데이트
            await api_key_service.update_api_key_usage("sk_test_key_123456789")
            
            # 마지막 사용 시간 업데이트 확인
            assert mock_api_key.last_used_at > datetime.utcnow() - timedelta(minutes=1)
            mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_revoke_api_key(self, api_key_service, mock_db_session):
        """API 키 폐지 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_test_key_123456789",
                name="Test Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow() - timedelta(days=10),
                last_used_at=datetime.utcnow() - timedelta(hours=1)
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # API 키 폐지
            result = await api_key_service.revoke_api_key(
                user_id="user123",
                key_id="key123"
            )
            
            assert result is True
            assert mock_api_key.is_active is False
            assert mock_api_key.revoked_at is not None
            mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_list_user_api_keys(self, api_key_service, mock_db_session):
        """사용자 API 키 목록 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키 목록
            mock_api_keys = [
                APIKey(
                    key_id="key1",
                    api_key="sk_key1_123456789",
                    name="Key 1",
                    user_id="user123",
                    permissions=[APIKeyPermission.READ_STOCKS],
                    rate_limit=1000,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    created_at=datetime.utcnow() - timedelta(days=10)
                ),
                APIKey(
                    key_id="key2",
                    api_key="sk_key2_123456789",
                    name="Key 2",
                    user_id="user123",
                    permissions=[APIKeyPermission.READ_SENTIMENT],
                    rate_limit=500,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(days=60),
                    created_at=datetime.utcnow() - timedelta(days=5)
                )
            ]
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_api_keys
            
            # 사용자 API 키 목록 조회
            result = await api_key_service.list_user_api_keys("user123")
            
            assert result is not None
            assert len(result) == 2
            assert result[0].key_id == "key1"
            assert result[0].name == "Key 1"
            assert result[1].key_id == "key2"
            assert result[1].name == "Key 2"
    
    @pytest.mark.asyncio
    async def test_update_api_key_permissions(self, api_key_service, mock_db_session):
        """API 키 권한 업데이트 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_test_key_123456789",
                name="Test Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # 권한 업데이트
            new_permissions = [
                APIKeyPermission.READ_STOCKS,
                APIKeyPermission.READ_SENTIMENT,
                APIKeyPermission.WRITE_WATCHLIST
            ]
            
            result = await api_key_service.update_api_key_permissions(
                user_id="user123",
                key_id="key123",
                permissions=new_permissions
            )
            
            assert result is True
            assert len(mock_api_key.permissions) == 3
            assert APIKeyPermission.READ_SENTIMENT in mock_api_key.permissions
            assert APIKeyPermission.WRITE_WATCHLIST in mock_api_key.permissions
            mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_api_key_rate_limit(self, api_key_service, mock_db_session):
        """API 키 속도 제한 확인 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_test_key_123456789",
                name="Test Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # 속도 제한 확인 (제한 내)
            with patch('backend.services.api_key_service.get_current_usage') as mock_usage:
                mock_usage.return_value = 500  # 1000 제한 내
                
                result = await api_key_service.check_api_key_rate_limit(
                    api_key="sk_test_key_123456789"
                )
                
                assert result.is_allowed is True
                assert result.remaining_requests == 500
                assert result.reset_time is not None
            
            # 속도 제한 확인 (제한 초과)
            with patch('backend.services.api_key_service.get_current_usage') as mock_usage:
                mock_usage.return_value = 1000  # 제한 도달
                
                result = await api_key_service.check_api_key_rate_limit(
                    api_key="sk_test_key_123456789"
                )
                
                assert result.is_allowed is False
                assert result.remaining_requests == 0
                assert result.reset_time is not None
    
    @pytest.mark.asyncio
    async def test_regenerate_api_key(self, api_key_service, mock_db_session):
        """API 키 재생성 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 API 키
            mock_api_key = APIKey(
                key_id="key123",
                api_key="sk_old_key_123456789",
                name="Test Key",
                user_id="user123",
                permissions=[APIKeyPermission.READ_STOCKS],
                rate_limit=1000,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow() - timedelta(days=10)
            )
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_api_key
            
            # API 키 재생성
            result = await api_key_service.regenerate_api_key(
                user_id="user123",
                key_id="key123"
            )
            
            assert result is not None
            assert "api_key" in result
            assert "key_id" in result
            assert result["key_id"] == "key123"
            assert result["api_key"] != "sk_old_key_123456789"  # 새로운 키
            assert len(result["api_key"]) >= 32
            
            # 이전 키 비활성화 확인
            assert mock_api_key.is_active is False
            assert mock_api_key.revoked_at is not None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, api_key_service, mock_db_session):
        """만료된 API 키 정리 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 만료된 API 키 목록
            expired_keys = [
                APIKey(
                    key_id="key1",
                    api_key="sk_expired_key1_123456789",
                    name="Expired Key 1",
                    user_id="user123",
                    permissions=[APIKeyPermission.READ_STOCKS],
                    rate_limit=1000,
                    is_active=True,
                    expires_at=datetime.utcnow() - timedelta(days=1),  # 만료됨
                    created_at=datetime.utcnow() - timedelta(days=30)
                ),
                APIKey(
                    key_id="key2",
                    api_key="sk_expired_key2_123456789",
                    name="Expired Key 2",
                    user_id="user456",
                    permissions=[APIKeyPermission.READ_SENTIMENT],
                    rate_limit=500,
                    is_active=True,
                    expires_at=datetime.utcnow() - timedelta(days=2),  # 만료됨
                    created_at=datetime.utcnow() - timedelta(days=20)
                )
            ]
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = expired_keys
            
            # 만료된 키 정리
            result = await api_key_service.cleanup_expired_keys()
            
            assert result is not None
            assert result.cleaned_count == 2
            assert result.cleaned_keys == ["key1", "key2"]
            
            # 비활성화 확인
            for key in expired_keys:
                assert key.is_active is False
                assert key.revoked_at is not None
            
            mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_api_key_statistics(self, api_key_service, mock_db_session):
        """API 키 통계 조회 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 통계 데이터
            with patch('backend.services.api_key_service.get_usage_statistics') as mock_stats:
                mock_stats.return_value = {
                    "total_requests": 10000,
                    "requests_today": 500,
                    "requests_this_month": 5000,
                    "average_requests_per_day": 333,
                    "peak_usage_day": "2023-01-15",
                    "peak_usage_count": 1200,
                    "error_rate": 0.02,
                    "average_response_time": 150.5
                }
                
                result = await api_key_service.get_api_key_statistics(
                    user_id="user123",
                    key_id="key123",
                    period="30d"
                )
                
                assert result is not None
                assert result.total_requests == 10000
                assert result.requests_today == 500
                assert result.requests_this_month == 5000
                assert result.average_requests_per_day == 333
                assert result.peak_usage_day == "2023-01-15"
                assert result.peak_usage_count == 1200
                assert result.error_rate == 0.02
                assert result.average_response_time == 150.5
    
    @pytest.mark.asyncio
    async def test_api_key_security_audit(self, api_key_service, mock_db_session):
        """API 키 보안 감사 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 감사 데이터
            with patch('backend.services.api_key_service.get_security_events') as mock_events:
                mock_events.return_value = [
                    {
                        "timestamp": datetime.utcnow() - timedelta(hours=2),
                        "event_type": "api_key_used",
                        "ip_address": "192.168.1.100",
                        "user_agent": "TestClient/1.0",
                        "endpoint": "/api/stocks/AAPL",
                        "success": True
                    },
                    {
                        "timestamp": datetime.utcnow() - timedelta(hours=1),
                        "event_type": "api_key_used",
                        "ip_address": "192.168.1.100",
                        "user_agent": "TestClient/1.0",
                        "endpoint": "/api/search",
                        "success": True
                    },
                    {
                        "timestamp": datetime.utcnow() - timedelta(minutes=30),
                        "event_type": "api_key_used",
                        "ip_address": "192.168.1.200",  # 다른 IP
                        "user_agent": "TestClient/1.0",
                        "endpoint": "/api/stocks/MSFT",
                        "success": False  # 실패
                    }
                ]
                
                result = await api_key_service.api_key_security_audit(
                    user_id="user123",
                    key_id="key123",
                    period="24h"
                )
                
                assert result is not None
                assert len(result.events) == 3
                assert result.unique_ip_addresses == 2
                assert result.successful_requests == 2
                assert result.failed_requests == 1
                assert result.suspicious_activity is False  # 2개 IP는 정상
                assert result.most_used_ip == "192.168.1.100"
                assert result.first_seen is not None
                assert result.last_seen is not None
    
    @pytest.mark.asyncio
    async def test_api_key_performance_monitoring(self, api_key_service, mock_db_session):
        """API 키 성능 모니터링 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 모의 성능 데이터
            with patch('backend.services.api_key_service.get_performance_metrics') as mock_metrics:
                mock_metrics.return_value = {
                    "average_response_time": 150.5,
                    "p95_response_time": 300.0,
                    "p99_response_time": 500.0,
                    "requests_per_second": 10.5,
                    "error_rate": 0.02,
                    "timeout_rate": 0.01,
                    "throughput_mbps": 2.5,
                    "concurrent_connections": 25
                }
                
                result = await api_key_service.get_api_key_performance(
                    key_id="key123",
                    period="1h"
                )
                
                assert result is not None
                assert result.average_response_time == 150.5
                assert result.p95_response_time == 300.0
                assert result.p99_response_time == 500.0
                assert result.requests_per_second == 10.5
                assert result.error_rate == 0.02
                assert result.timeout_rate == 0.01
                assert result.throughput_mbps == 2.5
                assert result.concurrent_connections == 25
                assert result.performance_grade in ["excellent", "good", "fair", "poor"]
    
    @pytest.mark.asyncio
    async def test_batch_api_key_operations(self, api_key_service, mock_db_session):
        """일괄 API 키 작업 테스트"""
        with patch('backend.services.api_key_service.get_db_session') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # 일괄 작업 요청
            batch_requests = [
                {
                    "name": "Batch Key 1",
                    "permissions": ["read:stocks"],
                    "rate_limit": 500
                },
                {
                    "name": "Batch Key 2",
                    "permissions": ["read:sentiment"],
                    "rate_limit": 300
                },
                {
                    "name": "Batch Key 3",
                    "permissions": ["read:stocks", "read:sentiment"],
                    "rate_limit": 800
                }
            ]
            
            result = await api_key_service.batch_generate_api_keys(
                user_id="user123",
                keys=batch_requests
            )
            
            assert result is not None
            assert len(result.generated_keys) == 3
            assert result.success_count == 3
            assert result.failure_count == 0
            
            # 생성된 키 확인
            for i, key_data in enumerate(result.generated_keys):
                assert key_data["name"] == f"Batch Key {i+1}"
                assert len(key_data["api_key"]) >= 32
                assert "key_id" in key_data
                assert "permissions" in key_data
                assert "rate_limit" in key_data
            
            # 데이터베이스 저장 확인
            assert mock_db_session.add.call_count == 3
            assert mock_db_session.commit.call_count == 3
    
    def test_api_key_format_validation(self, api_key_service):
        """API 키 형식 검증 테스트"""
        # 유효한 API 키 형식
        valid_keys = [
            "sk_test_1234567890abcdef",
            "sk_live_abcdef1234567890",
            "sk_prod_1234567890abcdef1234",
            "sk_dev_1234567890abcdef1234567890"
        ]
        
        for key in valid_keys:
            assert api_key_service.validate_api_key_format(key) is True
        
        # 유효하지 않은 API 키 형식
        invalid_keys = [
            "invalid_key",
            "sk_123",  # 너무 짧음
            "sk_test_1234567890abcdef123456789012345678901234567890",  # 너무 김
            "pk_test_1234567890abcdef",  # 잘못된 접두사
            "",  # 빈 문자열
            None  # None 값
        ]
        
        for key in invalid_keys:
            assert api_key_service.validate_api_key_format(key) is False
    
    def test_api_key_permission_validation(self, api_key_service):
        """API 키 권한 검증 테스트"""
        # 유효한 권한
        valid_permissions = [
            "read:stocks",
            "read:sentiment",
            "write:watchlist",
            "read:portfolio",
            "write:portfolio",
            "admin:users"
        ]
        
        for permission in valid_permissions:
            assert api_key_service.validate_permission(permission) is True
        
        # 유효하지 않은 권한
        invalid_permissions = [
            "invalid:permission",
            "read",  # 너무 일반적
            "stocks",  # 동사 없음
            "read:invalid_resource",
            "write:stocks",  # 쓰기 권한 없음
            "",  # 빈 문자열
            None  # None 값
        ]
        
        for permission in invalid_permissions:
            assert api_key_service.validate_permission(permission) is False
    
    def test_api_key_service_performance(self, api_key_service):
        """API 키 서비스 성능 테스트"""
        import time
        
        # 성능 측정
        start_time = time.time()
        
        # 여러 API 키 형식 검증
        for i in range(1000):
            key = f"sk_test_{i:040d}abcdef"
            api_key_service.validate_api_key_format(key)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_validation = total_time / 1000
        
        # 성능 기준 확인
        assert avg_time_per_validation < 0.001  # 검증당 1ms 이하
        
        print(f"API Key Service Performance:")
        print(f"  Total Validations: 1000")
        print(f"  Total Time: {total_time:.4f}s")
        print(f"  Average Time per Validation: {avg_time_per_validation:.6f}s")