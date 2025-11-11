"""
테스트 데이터베이스 설정 및 픽스처
"""

import asyncio
import os
import sqlite3
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

from backend.models.unified_models import Base
from backend.database import get_db


# 테스트 데이터베이스 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_data/test.db"
SYNC_TEST_DATABASE_URL = "sqlite:///./test_data/test.db"


@pytest.fixture(scope="session")
def test_db_dir():
    """테스트 데이터베이스 디렉토리 생성"""
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session")
def test_db_engine(test_db_dir):
    """동기 테스트 데이터베이스 엔진"""
    engine = create_engine(
        SYNC_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 정리
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine):
    """동기 테스트 데이터베이스 세션"""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture(scope="session")
async def async_test_db_engine(test_db_dir):
    """비동기 테스트 데이터베이스 엔진"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 정리
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_test_db_session(async_test_db_engine):
    """비동기 테스트 데이터베이스 세션"""
    async_session = sessionmaker(
        async_test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def override_get_db(async_test_db_session):
    """데이터베이스 의존성 오버라이드"""
    async def _override_get_db():
        async with async_test_db_session:
            yield async_test_db_session
    
    return _override_get_db


@pytest.fixture
def sample_stock_data():
    """샘플 주식 데이터"""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 150.25,
        "change": 2.50,
        "change_percent": 1.69,
        "volume": 1000000,
        "market_cap": 2500000000000,
        "pe_ratio": 25.5,
        "dividend_yield": 0.5,
        "high_52w": 180.0,
        "low_52w": 120.0,
        "beta": 1.2
    }


@pytest.fixture
def sample_sentiment_data():
    """샘플 센티먼트 데이터"""
    return {
        "symbol": "AAPL",
        "sentiment_score": 0.75,
        "sentiment_label": "positive",
        "confidence": 0.85,
        "source": "news",
        "timestamp": "2023-01-01T12:00:00Z",
        "text": "Apple reports strong quarterly earnings",
        "keywords": ["earnings", "growth", "revenue"]
    }


@pytest.fixture
def sample_market_data():
    """샘플 시장 데이터"""
    return {
        "indices": {
            "S&P 500": {"value": 4500.25, "change": 15.50, "change_percent": 0.35},
            "NASDAQ": {"value": 14000.75, "change": 50.25, "change_percent": 0.36},
            "DOW": {"value": 35000.50, "change": 100.75, "change_percent": 0.29}
        },
        "sectors": {
            "Technology": {"change_percent": 0.8},
            "Healthcare": {"change_percent": -0.2},
            "Finance": {"change_percent": 0.3},
            "Energy": {"change_percent": 1.2}
        },
        "market_sentiment": {
            "fear_greed_index": 65,
            "volatility_index": 18.5,
            "market_mood": "bullish"
        }
    }


@pytest.fixture
def sample_user_data():
    """샘플 사용자 데이터"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "is_premium": False,
        "preferences": {
            "theme": "light",
            "language": "en",
            "notifications": True,
            "watchlist": ["AAPL", "GOOGL", "MSFT"]
        }
    }


@pytest.fixture
def sample_notification_data():
    """샘플 알림 데이터"""
    return {
        "id": 1,
        "user_id": 1,
        "type": "price_alert",
        "title": "Price Alert: AAPL",
        "message": "AAPL has reached your target price of $150",
        "data": {
            "symbol": "AAPL",
            "current_price": 150.25,
            "target_price": 150.00,
            "change": 2.50
        },
        "is_read": False,
        "created_at": "2023-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_api_key_data():
    """샘플 API 키 데이터"""
    return {
        "id": 1,
        "user_id": 1,
        "name": "Test API Key",
        "key": "test_api_key_12345",
        "permissions": ["read", "write"],
        "rate_limit": 1000,
        "is_active": True,
        "created_at": "2023-01-01T00:00:00Z",
        "expires_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_cache_data():
    """샘플 캐시 데이터"""
    return {
        "key": "stock:AAPL:current",
        "value": {
            "symbol": "AAPL",
            "price": 150.25,
            "timestamp": "2023-01-01T12:00:00Z"
        },
        "ttl": 300,
        "tags": ["stock", "realtime"]
    }


@pytest.fixture
def sample_webhook_data():
    """샘플 웹훅 데이터"""
    return {
        "id": 1,
        "user_id": 1,
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "events": ["price_alert", "sentiment_change"],
        "secret": "webhook_secret_123",
        "is_active": True,
        "created_at": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_portfolio_data():
    """샘플 포트폴리오 데이터"""
    return {
        "id": 1,
        "user_id": 1,
        "name": "Test Portfolio",
        "description": "A test portfolio for testing purposes",
        "holdings": [
            {
                "symbol": "AAPL",
                "shares": 100,
                "average_cost": 145.00,
                "current_price": 150.25,
                "market_value": 15025.00,
                "gain_loss": 525.00,
                "gain_loss_percent": 3.62
            },
            {
                "symbol": "GOOGL",
                "shares": 50,
                "average_cost": 2500.00,
                "current_price": 2550.75,
                "market_value": 127537.50,
                "gain_loss": 2537.50,
                "gain_loss_percent": 2.03
            }
        ],
        "total_value": 142562.50,
        "total_cost": 139500.00,
        "total_gain_loss": 3062.50,
        "total_gain_loss_percent": 2.20,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_analysis_data():
    """샘플 분석 데이터"""
    return {
        "symbol": "AAPL",
        "technical_indicators": {
            "rsi": 65.5,
            "macd": 2.3,
            "bollinger_bands": {
                "upper": 155.0,
                "middle": 150.0,
                "lower": 145.0
            },
            "moving_averages": {
                "sma_20": 148.5,
                "sma_50": 145.0,
                "ema_12": 149.0,
                "ema_26": 146.5
            }
        },
        "fundamental_analysis": {
            "pe_ratio": 25.5,
            "pb_ratio": 8.2,
            "debt_to_equity": 0.3,
            "roe": 0.25,
            "revenue_growth": 0.08,
            "earnings_growth": 0.12
        },
        "sentiment_analysis": {
            "overall_sentiment": 0.75,
            "news_sentiment": 0.80,
            "social_sentiment": 0.70,
            "analyst_sentiment": 0.75,
            "confidence": 0.85
        },
        "price_targets": {
            "analyst_target": 165.0,
            "model_target": 158.5,
            "support_level": 145.0,
            "resistance_level": 155.0
        },
        "recommendation": "BUY",
        "confidence": 0.78,
        "risk_level": "MEDIUM",
        "time_horizon": "3-6 months",
        "created_at": "2023-01-01T12:00:00Z"
    }


# 데이터베이스 초기화 함수
async def initialize_test_database():
    """테스트 데이터베이스 초기화"""
    # 테스트 데이터베이스 디렉토리 생성
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # 비동기 엔진 생성
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False
    )
    
    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()


async def cleanup_test_database():
    """테스트 데이터베이스 정리"""
    # 테스트 데이터베이스 파일 삭제
    test_db_file = Path("test_data/test.db")
    if test_db_file.exists():
        test_db_file.unlink()


# 테스트 데이터 삽입 함수
async def insert_test_data(session: AsyncSession, data_type: str, data: dict):
    """테스트 데이터 삽입"""
    # 실제 구현에서는 모델에 따라 데이터 삽입 로직 구현
    pass


# 테스트 유틸리티 함수
async def create_test_user(session: AsyncSession, user_data: dict):
    """테스트 사용자 생성"""
    # 실제 구현에서는 User 모델 사용
    pass


async def create_test_stock(session: AsyncSession, stock_data: dict):
    """테스트 주식 데이터 생성"""
    # 실제 구현에서는 Stock 모델 사용
    pass


async def create_test_sentiment(session: AsyncSession, sentiment_data: dict):
    """테스트 센티먼트 데이터 생성"""
    # 실제 구현에서는 Sentiment 모델 사용
    pass


# 데이터베이스 연결 테스트 유틸리티
def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        conn = sqlite3.connect(SYNC_TEST_DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


# 테스트 데이터베이스 상태 확인
async def check_test_database_health():
    """테스트 데이터베이스 상태 확인"""
    try:
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
        await engine.dispose()
        return row[0] == 1
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False


# 테스트 데이터베이스 리셋
async def reset_test_database():
    """테스트 데이터베이스 리셋"""
    await cleanup_test_database()
    await initialize_test_database()


# 테스트 데이터베이스 백업
def backup_test_database():
    """테스트 데이터베이스 백업"""
    import shutil
    src = Path("test_data/test.db")
    dst = Path("test_data/test_backup.db")
    if src.exists():
        shutil.copy2(src, dst)
        return True
    return False


# 테스트 데이터베이스 복원
def restore_test_database():
    """테스트 데이터베이스 복원"""
    import shutil
    src = Path("test_data/test_backup.db")
    dst = Path("test_data/test.db")
    if src.exists():
        shutil.copy2(src, dst)
        return True
    return False