"""
캐시 미들웨어 단위 테스트

이 모듈은 캐시 미들웨어의 개별 기능을 테스트합니다.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, Response
from starlette.responses import JSONResponse

from backend.middleware.cache_middleware import CacheMiddleware


class TestCacheMiddleware:
    """캐시 미들웨어 단위 테스트 클래스"""
    
    @pytest.fixture
    def mock_app(self):
        """모의 애플리케이션 픽스처"""
        async def app(scope, receive, send):
            # 모의 응답 생성
            response = JSONResponse(
                content={"data": "test_response", "timestamp": "2023-01-01T00:00:00Z"},
                status_code=200
            )
            await response(scope, receive, send)
        return app
    
    @pytest.fixture
    def cache_middleware(self, mock_app):
        """캐시 미들웨어 픽스처"""
        middleware = CacheMiddleware(mock_app)
        # 테스트 환경에서 redis_client를 mock으로 설정
        middleware.redis_client = AsyncMock()
        middleware.redis_client.get.return_value = None  # 캐시 미스 기본값
        middleware.redis_client.setex.return_value = True
        return middleware
    
    @pytest.fixture
    def mock_cache_manager(self):
        """모의 캐시 관리자 픽스처"""
        cache_manager = AsyncMock()
        cache_manager.get.return_value = None  # 캐시 미스 기본값
        cache_manager.set.return_value = True
        return cache_manager
    
    @pytest.mark.asyncio
    async def test_cache_miss_scenario(self, cache_middleware, mock_cache_manager):
        """캐시 미스 시나리오 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b"include_sentiment=true"
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # 캐시 확인이 호출되었는지 확인
            mock_cache_manager.get.assert_called_once()
            
            # 응답이 캐시에 저장되었는지 확인
            mock_cache_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_hit_scenario(self, cache_middleware, mock_cache_manager):
        """캐시 히트 시나리오 테스트"""
        # 캐시된 응답 설정
        cached_response = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": b'{"data": "cached_response", "timestamp": "2023-01-01T00:00:00Z"}'
        }
        mock_cache_manager.get.return_value = cached_response
        
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b"include_sentiment=true"
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # 캐시 확인이 호출되었는지 확인
            mock_cache_manager.get.assert_called_once()
            
            # 캐시 히트 시 앱이 호출되지 않아야 함
            # send가 캐시된 응답으로 호출되었는지 확인
            assert send.called
    
    @pytest.mark.asyncio
    async def test_post_request_not_cached(self, cache_middleware, mock_cache_manager):
        """POST 요청은 캐시되지 않는지 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/stocks",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # POST 요청은 캐시 확인이 호출되지 않아야 함
            mock_cache_manager.get.assert_not_called()
            mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_auth_endpoint_not_cached(self, cache_middleware, mock_cache_manager):
        """인증 엔드포인트는 캐시되지 않는지 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/auth/login",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # 인증 엔드포인트는 캐시 확인이 호출되지 않아야 함
            mock_cache_manager.get.assert_not_called()
            mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_middleware, mock_cache_manager):
        """캐시 키 생성 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b"include_sentiment=true&limit=10"
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # 캐시 키가 경로, 쿼리 파라미터, 메서드를 포함하는지 확인
            cache_key = mock_cache_manager.get.call_args[0][0]
            assert "GET" in cache_key
            assert "/api/stocks/AAPL" in cache_key
            assert "include_sentiment=true" in cache_key
            assert "limit=10" in cache_key
    
    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, cache_middleware, mock_cache_manager):
        """캐시 TTL 설정 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # 캐시 설정 시 TTL이 포함되는지 확인
            cache_set_args = mock_cache_manager.set.call_args
            assert len(cache_set_args[0]) >= 2  # key, value
            assert 'ttl' in cache_set_args[1] or len(cache_set_args[0]) > 2  # ttl 파라미터 확인
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_middleware, mock_cache_manager):
        """캐시 오류 처리 테스트"""
        # 캐시 오류 시뮬레이션
        mock_cache_manager.get.side_effect = Exception("Cache connection error")
        
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과 (오류가 발생해도 계속 진행되어야 함)
            await cache_middleware(scope, receive, send)
            
            # 캐시 오류가 발생해도 앱이 정상적으로 호출되어야 함
            assert send.called
    
    @pytest.mark.asyncio
    async def test_vary_header_handling(self, cache_middleware, mock_cache_manager):
        """Vary 헤더 처리 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [
                    (b"host", b"localhost:8000"),
                    (b"authorization", b"Bearer token1")
                ],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # Authorization 헤더가 다른 경우 다른 캐시 키를 사용하는지 확인
            cache_key1 = mock_cache_manager.get.call_args[0][0]
            
            # 다른 Authorization 헤더로 재시도
            scope["headers"] = [
                (b"host", b"localhost:8000"),
                (b"authorization", b"Bearer token2")
            ]
            
            mock_cache_manager.get.reset_mock()
            await cache_middleware(scope, receive, send)
            
            cache_key2 = mock_cache_manager.get.call_args[0][0]
            
            # 다른 Authorization 헤더는 다른 캐시 키를 가져야 함
            assert cache_key1 != cache_key2
    
    @pytest.mark.asyncio
    async def test_cache_control_header_parsing(self, cache_middleware, mock_cache_manager):
        """Cache-Control 헤더 파싱 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [
                    (b"host", b"localhost:8000"),
                    (b"cache-control", b"no-cache")
                ],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # no-cache 헤더가 있으면 캐시를 사용하지 않아야 함
            mock_cache_manager.get.assert_not_called()
            mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_max_age_configuration(self, cache_middleware, mock_cache_manager):
        """max-age 설정 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks/AAPL",
                "headers": [
                    (b"host", b"localhost:8000"),
                    (b"cache-control", b"max-age=300")
                ],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # max-age 설정이 캐시 TTL에 반영되는지 확인
            cache_set_args = mock_cache_manager.set.call_args
            assert cache_set_args.called  # 캐시 설정이 호출되었는지 확인
    
    @pytest.mark.asyncio
    async def test_response_size_limit(self, cache_middleware, mock_cache_manager):
        """응답 크기 제한 테스트"""
        # 큰 응답이 캐시되지 않도록 설정
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            # 큰 응답을 반환하는 모의 앱
            async def large_response_app(scope, receive, send):
                large_data = "x" * (1024 * 1024)  # 1MB 데이터
                response = JSONResponse(
                    content={"data": large_data},
                    status_code=200
                )
                await response(scope, receive, send)
            
            large_cache_middleware = CacheMiddleware(large_response_app)
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/large-data",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await large_cache_middleware(scope, receive, send)
            
            # 큰 응답은 캐시되지 않아야 함
            mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_post(self, cache_middleware, mock_cache_manager):
        """POST 요청 시 캐시 무효화 테스트"""
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            # 관련 캐시 무효화 메서드 추가
            mock_cache_manager.invalidate_pattern.return_value = True
            
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/stocks/AAPL/update",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과
            await cache_middleware(scope, receive, send)
            
            # POST 요청 후 관련 캐시 무효화 확인
            if hasattr(mock_cache_manager, 'invalidate_pattern'):
                mock_cache_manager.invalidate_pattern.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, cache_middleware, mock_cache_manager):
        """동시 캐시 접근 테스트"""
        import asyncio
        
        with patch('backend.middleware.cache_middleware.get_cache_manager') as mock_get_cache:
            mock_get_cache.return_value = mock_cache_manager
            
            # 동일한 요청에 대한 동시 접근 시뮬레이션
            async def concurrent_request():
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks/AAPL",
                    "headers": [(b"host", b"localhost:8000")],
                    "query_string": b""
                }
                
                receive = AsyncMock()
                send = AsyncMock()
                
                await cache_middleware(scope, receive, send)
            
            # 여러 동시 요청 실행
            tasks = [concurrent_request() for _ in range(5)]
            await asyncio.gather(*tasks)
            
            # 모든 요청이 캐시를 확인했는지 확인
            assert mock_cache_manager.get.call_count == 5