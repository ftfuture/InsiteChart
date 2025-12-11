"""JWT authentication middleware."""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt

logger = logging.getLogger(__name__)


class JWTHandler:
    """Handle JWT token generation and validation."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30
    ):
        """Initialize JWT handler.

        Args:
            secret_key: Secret key for encoding/decoding
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Token expiration time
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token.

        Args:
            data: Payload data
            expires_delta: Custom expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            raise

    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(status_code=401, detail="Token verification failed")


class AuthMiddleware:
    """Authentication middleware for request validation."""

    def __init__(self, jwt_handler: JWTHandler):
        """Initialize auth middleware.

        Args:
            jwt_handler: JWT handler instance
        """
        self.jwt_handler = jwt_handler
        self.security = HTTPBearer()

    async def __call__(self, credentials: HTTPAuthCredentials) -> dict:
        """Validate authentication credentials.

        Args:
            credentials: HTTP Bearer credentials

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If authentication fails
        """
        token = credentials.credentials

        if not token:
            raise HTTPException(
                status_code=403,
                detail="No authentication credentials provided"
            )

        payload = self.jwt_handler.verify_token(token)
        return payload

    def get_current_user(self, payload: dict) -> str:
        """Extract current user from token payload.

        Args:
            payload: Token payload

        Returns:
            Username/user ID
        """
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user information"
            )
        return username


# Predefined users for demo (in production, use a database)
USERS = {
    "demo_user": {
        "username": "demo_user",
        "password": "demo_password",  # In production, use hashed passwords
        "email": "demo@insitechart.com",
        "scopes": ["read", "write"]
    },
    "admin": {
        "username": "admin",
        "password": "admin_password",  # In production, use hashed passwords
        "email": "admin@insitechart.com",
        "scopes": ["read", "write", "admin"]
    }
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user credentials.

    Args:
        username: Username
        password: Password

    Returns:
        User dict if authentication successful, None otherwise
    """
    user = USERS.get(username)

    if not user:
        logger.warning(f"Authentication failed: user {username} not found")
        return None

    # In production, use proper password hashing
    if user.get("password") != password:
        logger.warning(f"Authentication failed: wrong password for user {username}")
        return None

    return user


# Create global JWT handler instance
@lru_cache(maxsize=1)
def get_jwt_handler() -> JWTHandler:
    """Get JWT handler singleton.

    Returns:
        JWTHandler instance
    """
    return JWTHandler()


def get_auth_middleware(jwt_handler: Optional[JWTHandler] = None) -> AuthMiddleware:
    """Get auth middleware instance.

    Args:
        jwt_handler: Optional JWT handler instance

    Returns:
        AuthMiddleware instance
    """
    if jwt_handler is None:
        jwt_handler = get_jwt_handler()

    return AuthMiddleware(jwt_handler)
