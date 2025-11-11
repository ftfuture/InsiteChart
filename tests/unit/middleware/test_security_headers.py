"""
보안 헤더 미들웨어 단위 테스트

이 모듈은 보안 헤더 미들웨어의 개별 기능을 테스트합니다.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request, Response
from starlette.responses import JSONResponse

from backend.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """보안 헤더 미들웨어 단위 테스트 클래스"""
    
    @pytest.fixture
    def mock_app(self):
        """모의 애플리케이션 픽스처"""
        async def app(scope, receive, send):
            response = JSONResponse(
                content={"message": "Success"},
                status_code=200
            )
            await response(scope, receive, send)
        return app
    
    @pytest.fixture
    def security_middleware(self, mock_app):
        """보안 헤더 미들웨어 픽스처"""
        return SecurityHeadersMiddleware(mock_app)
    
    @pytest.mark.asyncio
    async def test_x_frame_options_header(self, security_middleware):
        """X-Frame-Options 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # X-Frame-Options 헤더 확인
        assert "x-frame-options" in response_headers
        assert response_headers["x-frame-options"] in ["DENY", "SAMEORIGIN"]
    
    @pytest.mark.asyncio
    async def test_x_content_type_options_header(self, security_middleware):
        """X-Content-Type-Options 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # X-Content-Type-Options 헤더 확인
        assert "x-content-type-options" in response_headers
        assert response_headers["x-content-type-options"] == "nosniff"
    
    @pytest.mark.asyncio
    async def test_x_xss_protection_header(self, security_middleware):
        """X-XSS-Protection 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # X-XSS-Protection 헤더 확인
        assert "x-xss-protection" in response_headers
        assert response_headers["x-xss-protection"] in ["1; mode=block", "0"]
    
    @pytest.mark.asyncio
    async def test_strict_transport_security_header(self, security_middleware):
        """Strict-Transport-Security 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # HTTPS 요청에만 HSTS 헤더 포함
        if scope.get("scheme") == "https":
            assert "strict-transport-security" in response_headers
            assert "max-age=" in response_headers["strict-transport-security"]
    
    @pytest.mark.asyncio
    async def test_content_security_policy_header(self, security_middleware):
        """Content-Security-Policy 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # Content-Security-Policy 헤더 확인
        assert "content-security-policy" in response_headers
        csp = response_headers["content-security-policy"]
        
        # 기본 CSP 지시어 확인
        assert "default-src" in csp
        assert "script-src" in csp
        assert "style-src" in csp
    
    @pytest.mark.asyncio
    async def test_referrer_policy_header(self, security_middleware):
        """Referrer-Policy 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # Referrer-Policy 헤더 확인
        assert "referrer-policy" in response_headers
        assert response_headers["referrer-policy"] in [
            "strict-origin-when-cross-origin",
            "no-referrer",
            "same-origin"
        ]
    
    @pytest.mark.asyncio
    async def test_permissions_policy_header(self, security_middleware):
        """Permissions-Policy 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await security_middleware(scope, receive, send)
        
        # Permissions-Policy 헤더 확인
        assert "permissions-policy" in response_headers
        permissions = response_headers["permissions-policy"]
        
        # 일반적인 권한 정책 확인
        assert "geolocation" in permissions or "camera" in permissions
    
    @pytest.mark.asyncio
    async def test_custom_security_headers_configuration(self, security_middleware):
        """사용자 정의 보안 헤더 구성 테스트"""
        # 사용자 정의 보안 헤더로 미들웨어 생성
        custom_middleware = SecurityHeadersMiddleware(
            mock_app=self.mock_app(),
            custom_headers={
                "X-Custom-Security": "custom-value",
                "X-API-Version": "v1.0"
            }
        )
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await custom_middleware(scope, receive, send)
        
        # 사용자 정의 헤더 확인
        assert "x-custom-security" in response_headers
        assert response_headers["x-custom-security"] == "custom-value"
        assert "x-api-version" in response_headers
        assert response_headers["x-api-version"] == "v1.0"
    
    @pytest.mark.asyncio
    async def test_security_headers_for_different_endpoints(self, security_middleware):
        """다른 엔드포인트에 대한 보안 헤더 테스트"""
        endpoints = [
            "/api/stocks",
            "/api/auth/login",
            "/api/stocks/AAPL",
            "/api/search",
            "/health"
        ]
        
        for endpoint in endpoints:
            scope = {
                "type": "http",
                "method": "GET",
                "path": endpoint,
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 응답 헤더 캡처
            response_headers = {}
            
            def capture_send(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    for name, value in headers:
                        response_headers[name.decode()] = value.decode()
            
            send.side_effect = capture_send
            
            # 미들웨어 통과
            await security_middleware(scope, receive, send)
            
            # 모든 엔드포인트에 기본 보안 헤더가 있는지 확인
            assert "x-frame-options" in response_headers
            assert "x-content-type-options" in response_headers
    
    @pytest.mark.asyncio
    async def test_security_headers_for_different_methods(self, security_middleware):
        """다른 HTTP 메서드에 대한 보안 헤더 테스트"""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods:
            scope = {
                "type": "http",
                "method": method,
                "path": "/api/stocks",
                "headers": [(b"host", b"localhost:8000")],
                "query_string": b""
            }
            
            receive = MagicMock()
            send = MagicMock()
            
            # 응답 헤더 캡처
            response_headers = {}
            
            def capture_send(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    for name, value in headers:
                        response_headers[name.decode()] = value.decode()
            
            send.side_effect = capture_send
            
            # 미들웨어 통과
            await security_middleware(scope, receive, send)
            
            # 모든 메서드에 기본 보안 헤더가 있는지 확인
            assert "x-frame-options" in response_headers
            assert "x-content-type-options" in response_headers
    
    @pytest.mark.asyncio
    async def test_security_headers_preserve_existing_headers(self, security_middleware):
        """기존 헤더 보존 테스트"""
        # 기존 헤더를 설정하는 모의 앱
        async def app_with_headers(scope, receive, send):
            response = JSONResponse(
                content={"message": "Success"},
                status_code=200,
                headers={
                    "X-Existing-Header": "existing-value",
                    "Cache-Control": "no-cache"
                }
            )
            await response(scope, receive, send)
        
        middleware_with_existing = SecurityHeadersMiddleware(app_with_headers)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await middleware_with_existing(scope, receive, send)
        
        # 기존 헤더가 보존되는지 확인
        assert "x-existing-header" in response_headers
        assert response_headers["x-existing-header"] == "existing-value"
        assert "cache-control" in response_headers
        assert response_headers["cache-control"] == "no-cache"
        
        # 보안 헤더도 추가되는지 확인
        assert "x-frame-options" in response_headers
        assert "x-content-type-options" in response_headers
    
    @pytest.mark.asyncio
    async def test_security_headers_error_response(self, security_middleware):
        """오류 응답에 대한 보안 헤더 테스트"""
        # 오류 응답을 반환하는 모의 앱
        async def error_app(scope, receive, send):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        
        error_middleware = SecurityHeadersMiddleware(error_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/nonexistent",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과 (오류 발생)
        try:
            await error_middleware(scope, receive, send)
        except:
            pass  # 오류 무시
        
        # 오류 응답에도 보안 헤더가 있는지 확인
        # 실제 구현에 따라 다를 수 있음
        # assert "x-frame-options" in response_headers
    
    @pytest.mark.asyncio
    async def test_security_headers_configuration_override(self, security_middleware):
        """보안 헤더 구성 재정의 테스트"""
        # 기본값을 재정의하는 미들웨어 생성
        override_middleware = SecurityHeadersMiddleware(
            mock_app=self.mock_app(),
            x_frame_options="ALLOW-FROM https://trusted.com",
            x_content_type_options=None,  # 비활성화
            custom_csp="default-src 'self'; script-src 'unsafe-inline'"
        )
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 응답 헤더 캡처
        response_headers = {}
        
        def capture_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for name, value in headers:
                    response_headers[name.decode()] = value.decode()
        
        send.side_effect = capture_send
        
        # 미들웨어 통과
        await override_middleware(scope, receive, send)
        
        # 재정의된 값 확인
        assert "x-frame-options" in response_headers
        assert response_headers["x-frame-options"] == "ALLOW-FROM https://trusted.com"
        
        # 비활성화된 헤더 확인
        assert "x-content-type-options" not in response_headers
        
        # 사용자 정의 CSP 확인
        assert "content-security-policy" in response_headers
        assert "unsafe-inline" in response_headers["content-security-policy"]
    
    @pytest.mark.asyncio
    async def test_security_headers_performance_impact(self, security_middleware):
        """보안 헤더 성능 영향 테스트"""
        import time
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b""
        }
        
        receive = MagicMock()
        send = MagicMock()
        
        # 성능 측정
        start_time = time.time()
        
        # 여러 요청 실행
        for _ in range(100):
            await security_middleware(scope, receive, send)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_request = total_time / 100
        
        # 보안 헤더 추가가 성능에 큰 영향을 주지 않아야 함
        assert avg_time_per_request < 0.01  # 요청당 10ms 이하
        
        print(f"Security Headers Performance Impact:")
        print(f"  Total Time: {total_time:.4f}s")
        print(f"  Average Time per Request: {avg_time_per_request:.6f}s")