"""FastAPI API Gateway for InsiteChart microservices."""

import os
import logging
import time
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from routes import analytics, data_collector
from middleware.auth import JWTHandler, authenticate_user, get_jwt_handler, USERS
from middleware.logging_middleware import RequestIdMiddleware, LoggingMiddleware
from middleware.rate_limit import get_rate_limiter, get_rate_limit_middleware, RateLimitMiddleware
from services.service_discovery import get_service_registry, create_service_registry
from models.gateway_models import TokenResponse, HealthCheck, ErrorResponse, ServiceStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
jwt_handler = None
rate_limit_middleware = None
service_registry = None
start_time = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("API Gateway starting up...")
    global jwt_handler, rate_limit_middleware, service_registry, start_time

    start_time = time.time()

    try:
        # Initialize JWT handler
        jwt_handler = get_jwt_handler()
        logger.info("JWT handler initialized")

        # Initialize rate limiter
        rate_limiter = get_rate_limiter(
            requests_per_minute=int(os.getenv("RATE_LIMIT_MINUTE", "60")),
            requests_per_hour=int(os.getenv("RATE_LIMIT_HOUR", "1000")),
            requests_per_day=int(os.getenv("RATE_LIMIT_DAY", "10000"))
        )
        rate_limit_middleware = get_rate_limit_middleware(rate_limiter)
        logger.info("Rate limiter initialized")

        # Initialize service registry
        services_config = {
            "backend": {
                "url": os.getenv("BACKEND_URL", "http://localhost:8000"),
                "health_endpoint": "/health"
            },
            "data_collector": {
                "url": os.getenv("DATA_COLLECTOR_URL", "http://localhost:8001"),
                "health_endpoint": "/health"
            },
            "analytics": {
                "url": os.getenv("ANALYTICS_URL", "http://localhost:8002"),
                "health_endpoint": "/health"
            }
        }

        service_registry = create_service_registry(services_config)
        logger.info("Service registry initialized with {} services".format(
            len(services_config)
        ))

        # Start background health checks
        asyncio.create_task(service_registry.start_background_checks())
        logger.info("Background health checks started")

    except Exception as e:
        logger.error(f"Startup error: {e}")

    yield

    # Shutdown
    logger.info("API Gateway shutting down...")


# Create FastAPI app
app = FastAPI(
    title="InsiteChart API Gateway",
    description="Central API Gateway for InsiteChart Microservices",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestIdMiddleware)
app.add_middleware(LoggingMiddleware)


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/token", response_model=TokenResponse)
async def login(username: str, password: str):
    """Get JWT access token.

    Args:
        username: Username
        password: Password

    Returns:
        Access token

    Example:
        ```
        curl -X POST http://localhost:8080/auth/token \
          -d "username=demo_user&password=demo_password"
        ```
    """
    if not jwt_handler:
        raise HTTPException(status_code=503, detail="Auth service not initialized")

    # Authenticate user
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create token
    access_token = jwt_handler.create_access_token(
        data={"sub": user["username"], "scopes": user.get("scopes", [])}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_handler.access_token_expire_minutes * 60
    )


@app.get("/auth/users")
async def list_demo_users():
    """List available demo users for testing.

    Returns:
        Dictionary of available users and their credentials
    """
    return {
        "users": [
            {
                "username": username,
                "password": user.get("password", "***"),
                "email": user.get("email"),
                "scopes": user.get("scopes", [])
            }
            for username, user in USERS.items()
        ],
        "note": "These are demo users for testing. Use real authentication in production."
    }


# ============================================================================
# Health and Status Endpoints
# ============================================================================

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Check gateway and microservices health.

    Returns:
        Health status of gateway and all services
    """
    if not service_registry:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    uptime = time.time() - start_time if start_time else 0

    return HealthCheck(
        status="healthy",
        version="1.0.0",
        uptime_seconds=uptime,
        services=service_registry.get_all_services(),
        timestamp=None
    )


@app.get("/status")
async def gateway_status():
    """Get detailed gateway status.

    Returns:
        Gateway status information
    """
    if not service_registry:
        return {"status": "not_initialized"}

    return {
        "status": "running",
        "version": "1.0.0",
        "uptime_seconds": time.time() - start_time if start_time else 0,
        "services": {
            service.name: {
                "status": service.status,
                "url": service.url,
                "last_check": service.last_check,
                "response_time_ms": service.response_time_ms
            }
            for service in service_registry.get_all_services()
        }
    }


@app.get("/info")
async def gateway_info():
    """Get gateway information.

    Returns:
        Gateway metadata and available endpoints
    """
    return {
        "service": "InsiteChart API Gateway",
        "version": "1.0.0",
        "description": "Central API Gateway for InsiteChart Microservices",
        "endpoints": {
            "authentication": "/auth/token",
            "analytics": "/api/v1/analytics/*",
            "data_collector": "/api/v1/data-collector/*",
            "backend": "/api/v1/backend/*",
            "health": "/health",
            "status": "/status",
            "docs": "/docs"
        },
        "services": [
            "backend",
            "data-collector",
            "analytics"
        ]
    }


# ============================================================================
# API Routes
# ============================================================================

@app.include_router(analytics.router, prefix="/api/v1")
@app.include_router(data_collector.router, prefix="/api/v1")


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        Welcome message with gateway information
    """
    return {
        "service": "InsiteChart API Gateway",
        "status": "running",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "authentication": "/auth/token"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions.

    Args:
        request: HTTP request
        exc: HTTPException

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "timestamp": None,
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions.

    Args:
        request: HTTP request
        exc: Exception

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unexpected error: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "error_code": "INTERNAL_ERROR",
            "message": str(exc),
            "timestamp": None,
            "request_id": request_id
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Get configuration from environment
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting API Gateway on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
