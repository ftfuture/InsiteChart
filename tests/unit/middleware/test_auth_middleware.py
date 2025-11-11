"""
인증 미들웨어 단위 테스트

이 모듈은 인증 미들웨어의 개별 기능을 테스트합니다.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, HTTPException
from starlette.responses import Response

from backend.middleware.auth_middleware import AuthMiddleware


class TestAuthMiddleware:
    """인증 미들웨어 단위 테스트 클래스"""
    
    @pytest.fixture
    def mock_app(self):
        """모의 애플리케이션 픽스처"""
        async def app(scope, receive, send):
            response = Response("Success", status_code=200)
            await response(scope, receive, send)
        return app
    
    @pytest.fixture
    def auth_middleware(self, mock_app):
        """인증 미들웨어 픽스처"""
        return AuthMiddleware(mock_app)
    
    @pytest.mark.asyncio
    async def test_public_endpoint_access(self, auth_middleware):
        """공개 엔드포인트 접근 테스트"""
        # 공개 엔드포인트 목록에 포함된 경로
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "query_string": b""
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # 미들웨어 통과 확인
        await auth_middleware(scope, receive, send)
        
        # send가 호출되었는지 확인
        assert send.called
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, auth_middleware):
        """토큰 없이 보호된 엔드포인트 접근 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [],
            "query_string": b""
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # HTTPException 발생 확인
        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware(scope, receive, send)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(self, auth_middleware):
        """유효한 토큰으로 보호된 엔드포인트 접근 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "role": "user"}
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"authorization", b"Bearer valid_token")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과 확인
            await auth_middleware(scope, receive, send)
            
            # 토큰 검증이 호출되었는지 확인
            mock_verify.assert_called_once_with("valid_token")
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, auth_middleware):
        """유효하지 않은 토큰으로 보호된 엔드포인트 접근 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"authorization", b"Bearer invalid_token")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # HTTPException 발생 확인
            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware(scope, receive, send)
            
            assert exc_info.value.status_code == 401
            assert "Invalid token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_access_with_admin_role(self, auth_middleware):
        """관리자 역할로 관리자 엔드포인트 접근 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "admin_user", "role": "admin"}
            
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/admin/users",
                "headers": [(b"authorization", b"Bearer admin_token")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과 확인
            await auth_middleware(scope, receive, send)
            
            # 토큰 검증이 호출되었는지 확인
            mock_verify.assert_called_once_with("admin_token")
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_access_with_user_role(self, auth_middleware):
        """일 사용자 역할로 관리자 엔드포인트 접근 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "regular_user", "role": "user"}
            
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/admin/users",
                "headers": [(b"authorization", b"Bearer user_token")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # HTTPException 발생 확인
            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware(scope, receive, send)
            
            assert exc_info.value.status_code == 403
            assert "Admin access required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_api_key_authentication(self, auth_middleware):
        """API 키 인증 테스트"""
        with patch('backend.middleware.auth_middleware.verify_api_key') as mock_verify:
            mock_verify.return_value = {"user_id": "api_user", "permissions": ["read"]}
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"x-api-key", b"valid_api_key")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과 확인
            await auth_middleware(scope, receive, send)
            
            # API 키 검증이 호출되었는지 확인
            mock_verify.assert_called_once_with("valid_api_key")
    
    @pytest.mark.asyncio
    async def test_api_key_with_insufficient_permissions(self, auth_middleware):
        """불충분한 권한을 가진 API 키 접근 테스트"""
        with patch('backend.middleware.auth_middleware.verify_api_key') as mock_verify:
            mock_verify.return_value = {"user_id": "api_user", "permissions": ["read"]}
            
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/stocks",  # 쓰기 권한 필요
                "headers": [(b"x-api-key", b"read_only_api_key")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # HTTPException 발생 확인
            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware(scope, receive, send)
            
            assert exc_info.value.status_code == 403
            assert "Insufficient permissions" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_malformed_authorization_header(self, auth_middleware):
        """형식이 잘못된 인증 헤더 테스트"""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/stocks",
            "headers": [(b"authorization", b"InvalidFormat token")],
            "query_string": b""
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # HTTPException 발생 확인
        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware(scope, receive, send)
        
        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_expired_token_handling(self, auth_middleware):
        """만료된 토큰 처리 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=401, detail="Token expired")
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"authorization", b"Bearer expired_token")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # HTTPException 발생 확인
            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware(scope, receive, send)
            
            assert exc_info.value.status_code == 401
            assert "Token expired" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_user_context_propagation(self, auth_middleware):
        """사용자 컨텍스트 전파 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            user_data = {"user_id": "test_user", "role": "user", "email": "test@example.com"}
            mock_verify.return_value = user_data
            
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/stocks",
                "headers": [(b"authorization", b"Bearer valid_token")],
                "query_string": b""
            }
            
            receive = AsyncMock()
            send = AsyncMock()
            
            # 미들웨어 통과 확인
            await auth_middleware(scope, receive, send)
            
            # 사용자 정보가 scope에 추가되었는지 확인
            assert "user" in scope
            assert scope["user"] == user_data
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, auth_middleware):
        """속도 제한 통합 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "role": "user"}
            
            with patch('backend.middleware.auth_middleware.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = True
                
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"authorization", b"Bearer valid_token")],
                    "query_string": b""
                }
                
                receive = AsyncMock()
                send = AsyncMock()
                
                # 미들웨어 통과 확인
                await auth_middleware(scope, receive, send)
                
                # 속도 제한 확인이 호출되었는지 확인
                mock_rate_limit.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, auth_middleware):
        """속도 제한 초과 테스트"""
        with patch('backend.middleware.auth_middleware.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "role": "user"}
            
            with patch('backend.middleware.auth_middleware.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = False
                
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/stocks",
                    "headers": [(b"authorization", b"Bearer valid_token")],
                    "query_string": b""
                }
                
                receive = AsyncMock()
                send = AsyncMock()
                
                # HTTPException 발생 확인
                with pytest.raises(HTTPException) as exc_info:
                    await auth_middleware(scope, receive, send)
                
                assert exc_info.value.status_code == 429
                assert "Rate limit exceeded" in str(exc_info.value.detail)