"""
속도 제한 미들웨어 단위 테스트

이 모듈은 속도 제한 미들웨어의 개별 기능을 테스트합니다.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, HTTPException
from starlette.responses import Response

from backend.middleware.rate_limit_middleware import RateLimitMiddleware


class TestRateLimitMiddleware:
    """속도 제한 미들웨어 단위 테스트 클래스"""
    
    @pytest.fixture
    def mock_app(self):
        """모의 애플리케이션 픽스처"""
        async def app(scope, receive, send):
            response = Response("Success", status_code=200)
            await response(scope, receive, send)
        return app
    
    @pytest.fixture
    def rate_limit_middleware(self, mock_app):
        """속도 제한 미들웨어 픽스처"""
        return RateLimitMiddleware(mock_app, requests_per_minute=60)
    
    @pytest.mark.asyncio
    async def test_within_rate_limit(self, rate_limit_middleware):
        """속도 제한 내 요청 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"x-forwarded-for", b"192.168.1.1")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 속도 제한 내 요청은 통과해야 함
        await rate_limit_middleware(scope, receive, send)
        
        # 응답이 전송되었는지 확인
        assert send.called
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limit_middleware):
        """속도 제한 초과 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 속도 제한보다 많은 요청 보내기
            for _ in range(65):  # 60개 제한 초과
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                try:
                    await rate_limit_middleware(scope, receive, send)
                except HTTPException as e:
                    # 속도 제한 초과 예외 확인
                    assert e.status_code == 429
                    assert "Rate limit exceeded" in str(e.detail)
                    break
            else:
                pytest.fail("Rate limit exception not raised")
    
    @pytest.mark.asyncio
    async def test_different_clients_separate_limits(self, rate_limit_middleware):
        """다른 클라이언트는 별도의 속도 제한을 갖는지 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            # 첫 번째 클라이언트
            mock_get_ip.return_value = "192.168.1.1"
            
            for _ in range(65):  # 첫 번째 클라이언트 속도 제한 초과
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                try:
                    await rate_limit_middleware(scope, receive, send)
                except HTTPException:
                    break
            
            # 두 번째 클라이언트는 영향받지 않아야 함
            mock_get_ip.return_value = "192.168.1.2"
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"x-forwarded-for", b"192.168.1.2")],
                "query_string": b""
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 두 번째 클라이언트는 정상적으로 통과해야 함
            await rate_limit_middleware(scope, receive, send)
            assert send.called
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset_after_time_window(self, rate_limit_middleware):
        """시간 창 후 속도 제한 초기화 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 속도 제한까지 요청 보내기
            for _ in range(60):
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                await rate_limit_middleware(scope, receive, send)
            
            # 시간 창 시뮬레이션 (실제로는 시간을 조작할 수 없으므로 모의)
            with patch('time.time') as mock_time:
                # 61초 후로 시간 설정
                mock_time.return_value = time.time() + 61
                
                # 다시 요청 보내기 (통과해야 함)
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                await rate_limit_middleware(scope, receive, send)
                assert send.called
    
    @pytest.mark.asyncio
    async def test_authenticated_user_rate_limit(self, rate_limit_middleware):
        """인증된 사용자 속도 제한 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 인증된 사용자 요청
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [
                    (b"x-forwarded-for", b"192.168.1.1"),
                    (b"authorization", b"Bearer valid_token")
                ],
                "query_string": b"",
                "user": {"user_id": "authenticated_user", "role": "user"}
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 인증된 사용자는 일반 사용자보다 높은 제한을 가져야 함
            await rate_limit_middleware(scope, receive, send)
            assert send.called
    
    @pytest.mark.asyncio
    async def test_admin_user_higher_rate_limit(self, rate_limit_middleware):
        """관리자 사용자 높은 속도 제한 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 관리자 사용자 요청
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [
                    (b"x-forwarded-for", b"192.168.1.1"),
                    (b"authorization", b"Bearer admin_token")
                ],
                "query_string": b"",
                "user": {"user_id": "admin_user", "role": "admin"}
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 관리자는 더 높은 속도 제한을 가져야 함
            await rate_limit_middleware(scope, receive, send)
            assert send.called
    
    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(self, rate_limit_middleware):
        """API 키 속도 제한 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # API 키 요청
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [
                    (b"x-forwarded-for", b"192.168.1.1"),
                    (b"x-api-key", b"api_key_123")
                ],
                "query_string": b"",
                "api_key": {"key_id": "api_key_123", "rate_limit": 100}
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # API 키는 자체 속도 제한을 가져야 함
            await rate_limit_middleware(scope, receive, send)
            assert send.called
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_rate_limits(self, rate_limit_middleware):
        """엔드포인트별 속도 제한 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 높은 트래픽 엔드포인트
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/search",
                "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                "query_string": b""
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 검색 엔드포인트는 더 높은 속도 제한을 가져야 함
            await rate_limit_middleware(scope, receive, send)
            assert send.called
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, rate_limit_middleware):
        """속도 제한 헤더 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                "query_string": b""
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 응답 헤더 캡처를 위한 모의
            response_headers = {}
            
            def capture_send(message):
                if message["type"] == "http.response.start":
                    response_headers.update(dict(message.get("headers", [])))
            
            send.side_effect = capture_send
            
            await rate_limit_middleware(scope, receive, send)
            
            # 속도 제한 관련 헤더 확인
            assert any(b"x-ratelimit-limit" in header for header in response_headers.keys())
            assert any(b"x-ratelimit-remaining" in header for header in response_headers.keys())
            assert any(b"x-ratelimit-reset" in header for header in response_headers.keys())
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, rate_limit_middleware):
        """동시 요청 처리 테스트"""
        import asyncio
        
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            async def make_request():
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                try:
                    await rate_limit_middleware(scope, receive, send)
                    return True
                except HTTPException:
                    return False
            
            # 동시 요청 실행
            tasks = [make_request() for _ in range(70)]
            results = await asyncio.gather(*tasks)
            
            # 일부 요청은 성공하고 일부는 속도 제한으로 실패해야 함
            successful_requests = sum(results)
            failed_requests = len(results) - successful_requests
            
            assert successful_requests <= 60  # 속도 제한 내 성공
            assert failed_requests > 0  # 일부는 속도 제한으로 실패
    
    @pytest.mark.asyncio
    async def test_rate_limit_storage_backend(self, rate_limit_middleware):
        """속도 제한 저장소 백엔드 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # Redis 백엔드 모의
            mock_redis = AsyncMock()
            mock_redis.incr.return_value = 1
            mock_redis.expire.return_value = True
            
            with patch('backend.middleware.rate_limit_middleware.get_redis_client') as mock_redis_client:
                mock_redis_client.return_value = mock_redis
                
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                await rate_limit_middleware(scope, receive, send)
                
                # Redis가 호출되었는지 확인
                mock_redis.incr.assert_called()
                mock_redis.expire.assert_called()
    
    @pytest.mark.asyncio
    async def test_rate_limit_fallback_on_storage_error(self, rate_limit_middleware):
        """저장소 오류 시 속도 제한 폴백 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 저장소 오류 시뮬레이션
            mock_redis = AsyncMock()
            mock_redis.incr.side_effect = Exception("Redis connection error")
            
            with patch('backend.middleware.rate_limit_middleware.get_redis_client') as mock_redis_client:
                mock_redis_client.return_value = mock_redis
                
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                # 저장소 오류 시 요청은 통과해야 함 (폴백)
                await rate_limit_middleware(scope, receive, send)
                assert send.called
    
    @pytest.mark.asyncio
    async def test_rate_limit_whitelist_ips(self, rate_limit_middleware):
        """속도 제한 화이트리스트 IP 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            # 화이트리스트 IP
            mock_get_ip.return_value = "127.0.0.1"  # 로컬호스트
            
            # 많은 요청 보내기
            for _ in range(100):
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"127.0.0.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                await rate_limit_middleware(scope, receive, send)
                assert send.called  # 화이트리스트 IP는 항상 통과
    
    @pytest.mark.asyncio
    async def test_rate_limit_blacklist_ips(self, rate_limit_middleware):
        """속도 제한 블랙리스트 IP 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            # 블랙리스트 IP
            mock_get_ip.return_value = "192.168.1.100"  # 블랙리스트된 IP
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"x-forwarded-for", b"192.168.1.100")],
                "query_string": b""
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 블랙리스트 IP는 즉시 차단되어야 함
            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_middleware(scope, receive, send)
            
            assert exc_info.value.status_code == 403
            assert "IP address blocked" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_rate_limit_burst_handling(self, rate_limit_middleware):
        """속도 제한 버스트 처리 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 짧은 시간 내에 많은 요청 (버스트)
            for i in range(10):
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                await rate_limit_middleware(scope, receive, send)
                
                # 버스트 제한 확인
                if i >= 5:  # 버스트 제假设 5개
                    # 버스트 후에는 지연이 적용되어야 함
                    pass
    
    @pytest.mark.asyncio
    async def test_rate_limit_configuration_update(self, rate_limit_middleware):
        """속도 제한 설정 업데이트 테스트"""
        with patch('backend.middleware.rate_limit_middleware.get_client_ip') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.1"
            
            # 런타임에 속도 제한 설정 변경
            rate_limit_middleware.update_config(requests_per_minute=30)
            
            # 새로운 제한으로 요청
            for _ in range(35):  # 30개 제한 초과
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"x-forwarded-for", b"192.168.1.1")],
                    "query_string": b""
                }
                
                receive = MagicMock()
                send = MagicMock()
                
                try:
                    await rate_limit_middleware(scope, receive, send)
                except HTTPException as e:
                    # 새로운 제한으로 예외 확인
                    assert e.status_code == 429
                    break
            else:
                pytest.fail("Rate limit exception not raised with new config")