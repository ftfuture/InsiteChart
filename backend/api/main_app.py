"""
Main FastAPI application for InsiteChart platform.

This module creates and configures the main FastAPI application with
all routes, middleware, and error handling.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
from datetime import datetime

from .stock_routes import router as stock_router
from .sentiment_routes import router as sentiment_router
from .unified_routes import router as unified_router
from .auth_routes import router as auth_router
from .middleware import setup_middleware, SecurityMiddleware
from ..cache.unified_cache import UnifiedCacheManager
from ..cache.redis_cache import RedisCacheManager
from ..cache.memory_cache import MemoryCacheManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting InsiteChart API...")
    
    # Initialize cache based on environment
    cache_backend = None
    cache_type = os.getenv('CACHE_TYPE', 'memory').lower()
    
    if cache_type == 'redis':
        try:
            cache_backend = RedisCacheManager(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD')
            )
            await cache_backend.connect()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.info("Falling back to memory cache")
            cache_backend = MemoryCacheManager()
    else:
        cache_backend = MemoryCacheManager()
        logger.info("Using memory cache")
    
    # Store cache in app state
    app.state.cache_manager = UnifiedCacheManager(cache_backend)
    
    # Initialize services
    from ..services.stock_service import StockService
    from ..services.sentiment_service import SentimentService
    
    app.state.stock_service = StockService(app.state.cache_manager)
    app.state.sentiment_service = SentimentService(app.state.cache_manager)
    
    logger.info("InsiteChart API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down InsiteChart API...")
    
    # Close service connections
    if hasattr(app.state.stock_service, 'close'):
        await app.state.stock_service.close()
    
    if hasattr(app.state.sentiment_service, 'close'):
        await app.state.sentiment_service.close()
    
    # Disconnect cache
    if hasattr(cache_backend, 'disconnect'):
        await cache_backend.disconnect()
    
    logger.info("InsiteChart API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Create FastAPI app
    app = FastAPI(
        title="InsiteChart API",
        description="Financial analysis and social sentiment platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv('ALLOWED_HOSTS', '*').split(',')
    )
    
    # Add custom middleware
    setup_middleware(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
        tags=["Authentication"]
    )
    
    app.include_router(
        stock_router,
        prefix="/api/v1/stocks",
        tags=["Stocks"]
    )
    
    app.include_router(
        sentiment_router,
        prefix="/api/v1/sentiment",
        tags=["Sentiment"]
    )
    
    app.include_router(
        unified_router,
        prefix="/api/v1",
        tags=["Unified"]
    )
    
    # Add root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": "InsiteChart API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Add health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    
    return app


def setup_exception_handlers(app: FastAPI):
    """Setup custom exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors."""
        logger.error(f"Value error: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "Invalid input value",
                "details": str(exc),
                "status_code": 400,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "status_code": 500,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_app:app",
        host="0.0.0.0",
        port=int(os.getenv('PORT', 8000)),
        reload=os.getenv('DEBUG', 'false').lower() == 'true',
        log_level="info"
    )