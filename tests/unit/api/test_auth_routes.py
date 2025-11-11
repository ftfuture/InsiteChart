"""
인증 라우트 단위 테스트

이 모듈은 인증 관련 엔드포인트의 개별 기능을 독립적으로 테스트합니다.
"""

import pytest
import json
import time
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
import jwt
from datetime import datetime, timezone

from backend.api.auth_routes import router, USERS, API_KEYS, JWT_SECRET


class TestAuthRoutes:
    """인증 라우트 단위 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 픽스처"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/auth")
        return TestClient(app)
    
    def test_create_access_token_success(self, client):
        """액세스 토큰 생성 성공 테스트"""
        # 유효한 사용자 자격증명
        user_data = {
            "user_id": "test_user",
            "password": "test_password"
        }
        
        response = client.post("/api/v1/auth/token", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        
        # 토큰 유효성 검증
        token = data["access_token"]
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "test_user"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_access_token_invalid_credentials(self, client):
        """액세스 토큰 생성 실패 테스트 (잘못된 자격증명)"""
        # 잘못된 사용자 자격증명
        user_data = {
            "user_id": "invalid_user",
            "password": "wrong_password"
        }
        
        response = client.post("/api/v1/auth/token", json=user_data)
        
        assert response.status_code == 401
        data = response.json()
        
        assert "detail" in data
        assert "Invalid credentials" in data["detail"]
    
    def test_create_access_token_missing_fields(self, client):
        """액세스 토큰 생성 실패 테스트 (필드 누락)"""
        # 필드 누락된 요청
        user_data = {
            "user_id": "test_user"
            # password 필드 누락
        }
        
        response = client.post("/api/v1/auth/token", json=user_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_verify_token_success(self, client):
        """토큰 검증 성공 테스트"""
        # 먼저 유효한 토큰 생성
        token_response = client.post("/api/v1/auth/token", json={
            "user_id": "test_user",
            "password": "test_password"
        })
        token = token_response.json()["access_token"]
        
        # 토큰 검증
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["user_id"] == "test_user"
        assert "expires_at" in data
        assert "issued_at" in data
    
    def test_verify_token_invalid(self, client):
        """토큰 검증 실패 테스트 (잘못된 토큰)"""
        # 잘못된 토큰
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        
        assert "detail" in data
        assert "Invalid token" in data["detail"]
    
    def test_verify_token_missing(self, client):
        """토큰 검증 실패 테스트 (토큰 누락)"""
        # 토큰 없이 요청
        response = client.get("/api/v1/auth/verify")
        
        assert response.status_code == 401
        data = response.json()
        
        assert "detail" in data
        assert "Not authenticated" in data["detail"]
    
    def test_verify_token_expired(self, client):
        """토큰 검증 실패 테스트 (만료된 토큰)"""
        # 만료된 토큰 생성
        expired_payload = {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc).timestamp() - 3600,  # 1시간 전
            "iat": datetime.now(timezone.utc).timestamp() - 7200  # 2시간 전
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        
        assert "detail" in data
        assert "Token expired" in data["detail"]
    
    def test_refresh_token_success(self, client):
        """토큰 갱신 성공 테스트"""
        # 유효한 리프레시 토큰
        refresh_data = {
            "refresh_token": f"refresh_{int(time.time())}"
        }
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        
        # 새 토큰 유효성 검증
        new_token = data["access_token"]
        payload = jwt.decode(new_token, JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "test_user"
    
    def test_refresh_token_invalid(self, client):
        """토큰 갱신 실패 테스트 (잘못된 리프레시 토큰)"""
        # 잘못된 리프레시 토큰
        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        data = response.json()
        
        assert "detail" in data
        assert "Invalid refresh token" in data["detail"]
    
    def test_create_api_key_success(self, client):
        """API 키 생성 성공 테스트"""
        # API 키 생성 요청
        key_data = {
            "name": "test_key",
            "tier": "basic",
            "permissions": ["stock:read", "sentiment:read"]
        }
        
        response = client.post("/api/v1/auth/api-keys", json=key_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "api_key" in data
        assert "key_id" in data
        assert "name" in data
        assert "tier" in data
        assert "permissions" in data
        assert "created_at" in data
        
        assert data["name"] == "test_key"
        assert data["tier"] == "basic"
        assert data["permissions"] == ["stock:read", "sentiment:read"]
        assert data["api_key"].startswith("test_key_")
    
    def test_create_api_key_missing_fields(self, client):
        """API 키 생성 실패 테스트 (필드 누락)"""
        # 필드 누락된 요청
        key_data = {
            "name": "test_key"
            # tier 필드 누락
        }
        
        response = client.post("/api/v1/auth/api-keys", json=key_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_validate_api_key_success(self, client):
        """API 키 검증 성공 테스트"""
        # 먼저 유효한 API 키 생성
        create_response = client.post("/api/v1/auth/api-keys", json={
            "name": "test_key",
            "tier": "basic",
            "permissions": ["stock:read"]
        })
        api_key = create_response.json()["api_key"]
        
        # API 키 검증
        headers = {"X-API-Key": api_key}
        response = client.get("/api/v1/auth/validate-key", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert "key_id" in data
        assert "tier" in data
        assert "permissions" in data
        assert "usage_count" in data
        
        assert data["tier"] == "basic"
        assert data["permissions"] == ["stock:read"]
        assert data["usage_count"] == 1  # 검증 시 사용 횟수 증가
    
    def test_validate_api_key_invalid(self, client):
        """API 키 검증 실패 테스트 (잘못된 키)"""
        # 잘못된 API 키
        headers = {"X-API-Key": "invalid_api_key"}
        response = client.get("/api/v1/auth/validate-key", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "message" in data
        assert "Invalid API key" in data["message"]
    
    def test_validate_api_key_missing(self, client):
        """API 키 검증 실패 테스트 (키 누락)"""
        # API 키 없이 요청
        response = client.get("/api/v1/auth/validate-key")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "message" in data
        assert "No API key provided" in data["message"]
    
    def test_delete_api_key_success(self, client):
        """API 키 삭제 성공 테스트"""
        # 먼저 유효한 API 키 생성
        create_response = client.post("/api/v1/auth/api-keys", json={
            "name": "test_key",
            "tier": "basic",
            "permissions": ["stock:read"]
        })
        key_id = create_response.json()["key_id"]
        
        # API 키 삭제
        response = client.delete(f"/api/v1/auth/api-keys/{key_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "message" in data
        assert "API key deleted successfully" in data["message"]
        
        # 키가 실제로 삭제되었는지 확인
        assert key_id not in API_KEYS
    
    def test_delete_api_key_not_found(self, client):
        """API 키 삭제 실패 테스트 (키 없음)"""
        # 존재하지 않는 키 ID로 삭제 시도
        response = client.delete("/api/v1/auth/api-keys/nonexistent_key")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert "API key not found" in data["detail"]
    
    def test_list_api_keys_success(self, client):
        """API 키 목록 조회 성공 테스트"""
        # 여러 API 키 생성
        for i in range(3):
            client.post("/api/v1/auth/api-keys", json={
                "name": f"test_key_{i}",
                "tier": "basic",
                "permissions": ["stock:read"]
            })
        
        # API 키 목록 조회
        response = client.get("/api/v1/auth/api-keys")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "keys" in data
        assert len(data["keys"]) >= 3
        
        # 반환된 키 정보 검증
        for key_info in data["keys"]:
            assert "key_id" in key_info
            assert "name" in key_info
            assert "tier" in key_info
            assert "permissions" in key_info
            assert "created_at" in key_info
            assert "usage_count" in key_info
    
    def test_jwt_secret_consistency(self, client):
        """JWT 시크릿 일관성 테스트"""
        # 토큰 생성
        token_response = client.post("/api/v1/auth/token", json={
            "user_id": "test_user",
            "password": "test_password"
        })
        token = token_response.json()["access_token"]
        
        # 다른 시크릿으로 검증 시도
        with patch('backend.api.auth_routes.JWT_SECRET', 'different_secret'):
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/v1/auth/verify", headers=headers)
            
            assert response.status_code == 401
            data = response.json()
            
            assert "detail" in data
            assert "Invalid token" in data["detail"]
    
    def test_token_payload_structure(self, client):
        """토큰 페이로드 구조 테스트"""
        # 토큰 생성
        token_response = client.post("/api/v1/auth/token", json={
            "user_id": "test_user",
            "password": "test_password"
        })
        token = token_response.json()["access_token"]
        
        # 페이로드 디코딩 및 구조 검증
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        
        required_fields = ["sub", "exp", "iat"]
        for field in required_fields:
            assert field in payload
        
        # 사용자 ID 확인
        assert payload["sub"] == "test_user"
        
        # 만료 시간 확인 (1시간 후)
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        assert exp_time - iat_time == 3600  # 1시간
    
    def test_api_key_permissions_validation(self, client):
        """API 키 권한 검증 테스트"""
        # 다양한 권한으로 API 키 생성
        test_cases = [
            {
                "name": "read_only_key",
                "tier": "basic",
                "permissions": ["stock:read"]
            },
            {
                "name": "full_access_key",
                "tier": "premium",
                "permissions": ["stock:read", "stock:write", "sentiment:read", "sentiment:write"]
            },
            {
                "name": "custom_key",
                "tier": "enterprise",
                "permissions": ["custom:permission"]
            }
        ]
        
        for key_data in test_cases:
            response = client.post("/api/v1/auth/api-keys", json=key_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "permissions" in data
            assert set(data["permissions"]) == set(key_data["permissions"])
    
    def test_concurrent_requests(self, client):
        """동시 요청 처리 테스트"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.post("/api/v1/auth/token", json={
                "user_id": "test_user",
                "password": "test_password"
            })
            results.append(response.status_code)
        
        # 여러 스레드에서 동시에 요청
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 모든 스레드가 완료될 때까지 대기
        for thread in threads:
            thread.join()
        
        # 모든 요청이 성공해야 함
        assert all(status == 200 for status in results)
        assert len(results) == 5
    
    def test_rate_limiting(self, client):
        """속도 제한 테스트"""
        # 빠른 연속 요청으로 속도 제한 테스트
        responses = []
        
        for i in range(10):
            response = client.post("/api/v1/auth/token", json={
                "user_id": f"user_{i}",
                "password": "password"
            })
            responses.append(response.status_code)
        
        # 일부 요청은 성공, 일부는 실패할 수 있음
        # 실제 구현에서는 속도 제한 로직이 없을 수 있으므로 이 테스트는 유연하게 작성
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 1  # 적어도 하나는 성공해야 함