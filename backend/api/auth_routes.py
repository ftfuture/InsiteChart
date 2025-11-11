"""
Authentication routes for automation testing.
This module provides authentication endpoints for testing.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
import time
import jwt
import os
from datetime import datetime, timezone

router = APIRouter()
security = HTTPBearer()

# Mock user database
USERS = {
    "test_user": {
        "id": 1,
        "username": "test_user",
        "email": "test@example.com",
        "password": "test_password"
    }
}

# Mock API keys database
API_KEYS = {}

# JWT Secret - 환경 변수에서 가져오거나 기본값 사용
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "test_secret_key_for_automation_testing")


@router.post("/token")
async def create_access_token(user_data: Dict[str, Any]):
    """Create JWT access token."""
    username = user_data.get("user_id")
    password = user_data.get("password", "test_password")
    
    # Validate user (simplified for testing)
    if username in USERS or username == "test_user_123":
        # Create token
        payload = {
            "sub": username,
            "exp": datetime.now(timezone.utc).timestamp() + 3600,  # 1 hour
            "iat": datetime.now(timezone.utc).timestamp()
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "refresh_token": f"refresh_{int(time.time())}",
            "expires_in": 3600
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat")
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/refresh")
async def refresh_token(refresh_data: Dict[str, Any]):
    """Refresh JWT token."""
    refresh_token = refresh_data.get("refresh_token")
    
    # Simple validation for testing
    if refresh_token and refresh_token.startswith("refresh_"):
        # Create new token
        payload = {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
            "iat": datetime.now(timezone.utc).timestamp()
        }
        
        new_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "refresh_token": f"refresh_{int(time.time())}",
            "expires_in": 3600
        }
    
    raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/api-keys")
async def create_api_key(key_data: Dict[str, Any]):
    """Create API key for testing."""
    name = key_data.get("name")
    tier = key_data.get("tier", "basic")
    permissions = key_data.get("permissions", ["stock:read"])
    
    # Generate mock API key
    api_key = f"test_key_{int(time.time())}_{name}"
    key_id = f"key_{int(time.time())}"
    
    # Store in mock database
    API_KEYS[key_id] = {
        "key_id": key_id,
        "api_key": api_key,
        "name": name,
        "tier": tier,
        "permissions": permissions,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage_count": 0
    }
    
    return {
        "api_key": api_key,
        "key_id": key_id,
        "name": name,
        "tier": tier,
        "permissions": permissions,
        "created_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/validate-key")
async def validate_api_key(request: Request):
    """Validate API key."""
    # Try to get from header
    api_key = None
    
    # 여러 방법으로 API 키 확인 (대소문자 구분 없이)
    for header_name, header_value in request.headers.items():
        if header_name.lower() == "x-api-key":
            api_key = header_value
            break
    
    # 디버깅을 위해 헤더 정보 로깅
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Extracted API key: {api_key}")
    
    if not api_key:
        return {"valid": False, "message": "No API key provided"}
    
    # Check against mock database
    for key_id, key_info in API_KEYS.items():
        if key_info["api_key"] == api_key:
            # Update usage count
            key_info["usage_count"] += 1
            
            return {
                "valid": True,
                "key_id": key_id,
                "tier": key_info["tier"],
                "permissions": key_info["permissions"],
                "usage_count": key_info["usage_count"]
            }
    
    return {"valid": False, "message": "Invalid API key"}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str):
    """Delete API key."""
    if key_id in API_KEYS:
        del API_KEYS[key_id]
        return {"success": True, "message": "API key deleted successfully"}
    
    raise HTTPException(status_code=404, detail="API key not found")


@router.get("/api-keys")
async def list_api_keys():
    """List all API keys."""
    return {
        "keys": [
            {
                "key_id": key_id,
                "name": key_info["name"],
                "tier": key_info["tier"],
                "permissions": key_info["permissions"],
                "created_at": key_info["created_at"],
                "usage_count": key_info["usage_count"]
            }
            for key_id, key_info in API_KEYS.items()
        ]
    }