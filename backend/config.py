"""
Configuration settings for InsiteChart backend API.

This module manages all configuration settings including environment variables,
database connections, API keys, and other platform settings.
"""

import os
from typing import Optional, List
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    app_name: str = Field(default="InsiteChart API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Database settings
    database_url: str = Field(
        default="postgresql://user:password@localhost/insitechart",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    # Cache settings
    cache_ttl_default: int = Field(default=300, env="CACHE_TTL_DEFAULT")  # 5 minutes
    cache_ttl_short: int = Field(default=60, env="CACHE_TTL_SHORT")  # 1 minute
    cache_ttl_long: int = Field(default=3600, env="CACHE_TTL_LONG")  # 1 hour
    
    # API rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # External API settings
    yahoo_finance_timeout: int = Field(default=30, env="YAHOO_FINANCE_TIMEOUT")
    reddit_timeout: int = Field(default=30, env="REDDIT_TIMEOUT")
    twitter_timeout: int = Field(default=30, env="TWITTER_TIMEOUT")
    
    # API Keys (should be set in environment)
    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="InsiteChart/1.0", env="REDDIT_USER_AGENT")
    
    twitter_bearer_token: Optional[str] = Field(default=None, env="TWITTER_BEARER_TOKEN")
    twitter_api_key: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(default=None, env="TWITTER_API_SECRET")
    
    # Alpha Vantage API (optional, for additional financial data)
    alpha_vantage_api_key: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY")
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        env="SECRET_KEY"
    )
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="ALLOWED_METHODS"
    )
    allowed_headers: List[str] = Field(
        default=["*"],
        env="ALLOWED_HEADERS"
    )
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Sentiment analysis settings
    sentiment_analysis_enabled: bool = Field(default=True, env="SENTIMENT_ANALYSIS_ENABLED")
    sentiment_batch_size: int = Field(default=100, env="SENTIMENT_BATCH_SIZE")
    sentiment_update_interval: int = Field(default=300, env="SENTIMENT_UPDATE_INTERVAL")  # seconds
    
    # Data collection settings
    data_collection_enabled: bool = Field(default=True, env="DATA_COLLECTION_ENABLED")
    data_collection_interval: int = Field(default=60, env="DATA_COLLECTION_INTERVAL")  # seconds
    max_stocks_per_collection: int = Field(default=50, env="MAX_STOCKS_PER_COLLECTION")
    
    # Backup settings
    backup_enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    backup_interval: int = Field(default=86400, env="BACKUP_INTERVAL")  # 24 hours
    backup_retention_days: int = Field(default=30, env="BACKUP_RETENTION_DAYS")
    backup_s3_bucket: Optional[str] = Field(default=None, env="BACKUP_S3_BUCKET")
    backup_s3_region: str = Field(default="us-east-1", env="BACKUP_S3_REGION")
    
    # WebSocket settings
    websocket_enabled: bool = Field(default=True, env="WEBSOCKET_ENABLED")
    websocket_heartbeat_interval: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    websocket_max_connections: int = Field(default=1000, env="WEBSOCKET_MAX_CONNECTIONS")
    
    # Internationalization settings
    default_locale: str = Field(default="en", env="DEFAULT_LOCALE")
    supported_locales: List[str] = Field(
        default=["en", "ko", "ja", "zh", "es", "fr", "de", "it", "pt", "ru"],
        env="SUPPORTED_LOCALES"
    )
    
    # Frontend Settings
    backend_url: Optional[str] = Field(default="http://localhost:8000", env="BACKEND_URL")
    api_base_url: Optional[str] = Field(default="http://localhost:8000/api/v1", env="API_BASE_URL")
    
    # Development Settings
    testing: bool = Field(default=False, env="TESTING")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


# Database URL configuration
def get_database_url() -> str:
    """Get database URL."""
    return settings.database_url


# Redis URL configuration
def get_redis_url() -> str:
    """Get Redis URL."""
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_url.split('://', 1)[1]}/{settings.redis_db}"
    return f"{settings.redis_url}/{settings.redis_db}"


# CORS configuration
def get_cors_config() -> dict:
    """Get CORS configuration."""
    return {
        "allow_origins": settings.allowed_origins,
        "allow_credentials": True,
        "allow_methods": settings.allowed_methods,
        "allow_headers": settings.allowed_headers,
    }


# Logging configuration
def get_logging_config() -> dict:
    """Get logging configuration."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "detailed",
                "filename": "logs/insitechart.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }


# Environment-specific configurations
def is_development() -> bool:
    """Check if running in development environment."""
    return settings.debug


def is_production() -> bool:
    """Check if running in production environment."""
    return not settings.debug


def is_testing() -> bool:
    """Check if running in testing environment."""
    return os.getenv("TESTING", "false").lower() == "true"