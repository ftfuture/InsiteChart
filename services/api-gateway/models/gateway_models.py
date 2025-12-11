"""Pydantic models for API Gateway."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ServiceName(str, Enum):
    """Available microservices."""
    BACKEND = "backend"
    DATA_COLLECTOR = "data_collector"
    ANALYTICS = "analytics"


class RequestMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


# ============================================================================
# Authentication Models
# ============================================================================

class TokenRequest(BaseModel):
    """Request for token generation."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # subject (username)
    exp: int  # expiration time
    iat: int  # issued at
    scopes: List[str] = []


# ============================================================================
# Service Models
# ============================================================================

class ServiceStatus(str, Enum):
    """Service status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceInfo(BaseModel):
    """Service information."""
    name: str
    url: str
    status: ServiceStatus
    last_check: Optional[datetime] = None
    response_time_ms: Optional[float] = None

    class Config:
        example = {
            "name": "analytics-service",
            "url": "http://localhost:8002",
            "status": "healthy",
            "last_check": "2025-12-11T10:30:00Z",
            "response_time_ms": 45.5
        }


class ServiceRegistry(BaseModel):
    """Service registry information."""
    services: List[ServiceInfo]
    timestamp: datetime


# ============================================================================
# Request/Response Models
# ============================================================================

class GatewayRequest(BaseModel):
    """Generic gateway request wrapper."""
    service: ServiceName
    path: str
    method: RequestMethod = RequestMethod.GET
    body: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None


class GatewayResponse(BaseModel):
    """Generic gateway response wrapper."""
    service: ServiceName
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime
    request_id: str

    class Config:
        example = {
            "service": "analytics",
            "status_code": 200,
            "data": {
                "symbol": "AAPL",
                "sentiment": {"compound": 0.65}
            },
            "error": None,
            "timestamp": "2025-12-11T10:30:00Z",
            "request_id": "req_abc123"
        }


# ============================================================================
# Rate Limit Models
# ============================================================================

class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000

    class Config:
        example = {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        }


class RateLimitStatus(BaseModel):
    """Rate limit status."""
    limit_minute: int
    remaining_minute: int
    reset_minute_timestamp: datetime
    limit_hour: int
    remaining_hour: int
    reset_hour_timestamp: datetime
    limit_day: int
    remaining_day: int
    reset_day_timestamp: datetime


# ============================================================================
# Audit Log Models
# ============================================================================

class AuditLog(BaseModel):
    """Audit log entry."""
    timestamp: datetime
    request_id: str
    user: Optional[str]
    method: str
    path: str
    service: ServiceName
    status_code: int
    response_time_ms: float
    ip_address: str
    user_agent: Optional[str] = None
    error: Optional[str] = None

    class Config:
        example = {
            "timestamp": "2025-12-11T10:30:00Z",
            "request_id": "req_abc123",
            "user": "user123",
            "method": "POST",
            "path": "/api/v1/analyze/sentiment",
            "service": "analytics",
            "status_code": 200,
            "response_time_ms": 125.5,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0...",
            "error": None
        }


# ============================================================================
# Health Check Models
# ============================================================================

class HealthCheck(BaseModel):
    """Gateway health check response."""
    status: str = "healthy"
    version: str
    uptime_seconds: float
    services: List[ServiceInfo]
    timestamp: datetime

    class Config:
        example = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": 3600.5,
            "services": [
                {
                    "name": "analytics-service",
                    "url": "http://localhost:8002",
                    "status": "healthy",
                    "response_time_ms": 45.5
                }
            ],
            "timestamp": "2025-12-11T10:30:00Z"
        }


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: str

    class Config:
        example = {
            "error": "Unauthorized",
            "error_code": "AUTH_001",
            "message": "Invalid or missing authentication token",
            "details": {"required": "Authorization header"},
            "timestamp": "2025-12-11T10:30:00Z",
            "request_id": "req_abc123"
        }


# ============================================================================
# Metrics Models
# ============================================================================

class ServiceMetrics(BaseModel):
    """Service metrics."""
    service_name: str
    total_requests: int
    total_errors: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    uptime_percentage: float
    last_error: Optional[str] = None
    last_error_timestamp: Optional[datetime] = None

    class Config:
        example = {
            "service_name": "analytics",
            "total_requests": 10000,
            "total_errors": 45,
            "avg_response_time_ms": 125.5,
            "p95_response_time_ms": 250.0,
            "p99_response_time_ms": 500.0,
            "uptime_percentage": 99.5,
            "last_error": "Connection timeout",
            "last_error_timestamp": "2025-12-11T10:25:00Z"
        }


class GatewayMetrics(BaseModel):
    """Overall gateway metrics."""
    total_requests: int
    total_errors: int
    avg_response_time_ms: float
    services: List[ServiceMetrics]
    timestamp: datetime
