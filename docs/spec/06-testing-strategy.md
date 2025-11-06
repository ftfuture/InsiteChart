# 테스트 전략

## 1. 테스트 프레임워크

### 1.1 테스트 아키텍처

#### 1.1.1 테스트 계층 구조
```
테스트 피라미드
├── E2E (End-to-End) 테스트 (5%)
│   ├── 사용자 시나리오 테스트
│   └── 시스템 통합 테스트
├── 통합 테스트 (25%)
│   ├── API 통합 테스트
│   ├── 데이터베이스 통합 테스트
│   └── 외부 서비스 통합 테스트
└── 단위 테스트 (70%)
    ├── 모델 테스트
    ├── 서비스 테스트
    └── 유틸리티 테스트
```

#### 1.1.2 테스트 환경 설정
```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
from fastapi import FastAPI

# 테스트 데이터베이스 설정
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_insitechart"
TEST_REDIS_URL = "redis://localhost:6379/1"  # DB 1 사용

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 생성"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """테스트 데이터베이스 엔진"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    
    # 테스트 테이블 생성
    from app.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 테스트 테이블 정리
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트 데이터베이스 세션"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session

@pytest.fixture
async def test_redis():
    """테스트 Redis 연결"""
    redis_client = redis.from_url(TEST_REDIS_URL)
    
    # Redis 초기화
    await redis_client.flushdb()
    
    yield redis_client
    
    await redis_client.flushdb()
    await redis_client.close()

@pytest.fixture
async def test_app(test_session, test_redis) -> FastAPI:
    """테스트 애플리케이션"""
    from app.main import create_app
    
    app = create_app()
    
    # 테스트 데이터베이스 및 Redis 의존성 주입
    app.dependency_overrides[get_db_session] = lambda: test_session
    app.dependency_overrides[get_redis_client] = lambda: test_redis
    
    return app

@pytest.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """테스트 HTTP 클라이언트"""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def mock_external_apis():
    """외부 API 모킹"""
    from unittest.mock import AsyncMock
    
    # Yahoo Finance API 모킹
    yahoo_mock = AsyncMock()
    yahoo_mock.get_stock_info.return_value = {
        'symbol': 'AAPL',
        'company_name': 'Apple Inc.',
        'current_price': 150.0,
        'change': 2.5,
        'change_percent': 1.69
    }
    
    # Reddit API 모킹
    reddit_mock = AsyncMock()
    reddit_mock.collect_mentions.return_value = [
        {
            'symbol': 'AAPL',
            'text': 'AAPL is going to the moon!',
            'source': 'reddit',
            'timestamp': '2023-12-01T10:00:00'
        }
    ]
    
    # Twitter API 모킹
    twitter_mock = AsyncMock()
    twitter_mock.collect_mentions.return_value = [
        {
            'symbol': 'AAPL',
            'text': 'Bullish on $AAPL',
            'source': 'twitter',
            'timestamp': '2023-12-01T10:00:00'
        }
    ]
    
    return {
        'yahoo_finance': yahoo_mock,
        'reddit': reddit_mock,
        'twitter': twitter_mock
    }

@pytest.fixture
async def sample_stock_data():
    """샘플 주식 데이터"""
    return {
        'symbol': 'AAPL',
        'company_name': 'Apple Inc.',
        'stock_type': 'Common Stock',
        'exchange': 'NASDAQ',
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'current_price': 150.0,
        'previous_close': 147.5,
        'change': 2.5,
        'change_percent': 1.69,
        'volume': 50000000,
        'market_cap': 2500000000000,
        'pe_ratio': 25.5,
        'dividend_yield': 0.5
    }

@pytest.fixture
async def sample_sentiment_data():
    """샘플 센티먼트 데이터"""
    return {
        'symbol': 'AAPL',
        'overall_sentiment': 0.65,
        'reddit_sentiment': 0.7,
        'twitter_sentiment': 0.6,
        'mention_count': 1250,
        'positive_mentions': 750,
        'negative_mentions': 250,
        'neutral_mentions': 250,
        'timestamp': '2023-12-01T10:00:00'
    }

@pytest.fixture
async def sample_user_data():
    """샘플 사용자 데이터"""
    return {
        'user_id': 'test_user_123',
        'username': 'testuser',
        'email': 'test@example.com',
        'is_active': True,
        'created_at': '2023-01-01T00:00:00',
        'last_login': '2023-12-01T10:00:00'
    }
```

### 1.2 단위 테스트

#### 1.2.1 모델 테스트
```python
# tests/unit/test_models.py
import pytest
from datetime import datetime
from app.models.stock import Stock
from app.models.sentiment import SentimentData
from app.models.user import User

class TestStockModel:
    """주식 모델 테스트"""
    
    def test_stock_creation(self, sample_stock_data):
        """주식 생성 테스트"""
        stock = Stock(**sample_stock_data)
        
        assert stock.symbol == 'AAPL'
        assert stock.company_name == 'Apple Inc.'
        assert stock.current_price == 150.0
        assert stock.change == 2.5
        assert stock.change_percent == 1.69
    
    def test_stock_price_change_calculation(self):
        """주식 가격 변화 계산 테스트"""
        stock = Stock(
            symbol='AAPL',
            current_price=150.0,
            previous_close=147.5
        )
        
        change = stock.calculate_price_change()
        change_percent = stock.calculate_price_change_percent()
        
        assert change == 2.5
        assert abs(change_percent - 1.69) < 0.01
    
    def test_stock_is_positive_change(self):
        """양수 가격 변화 확인 테스트"""
        stock = Stock(
            symbol='AAPL',
            current_price=150.0,
            previous_close=147.5
        )
        
        assert stock.is_positive_change() == True
    
    def test_stock_is_negative_change(self):
        """음수 가격 변화 확인 테스트"""
        stock = Stock(
            symbol='AAPL',
            current_price=145.0,
            previous_close=147.5
        )
        
        assert stock.is_positive_change() == False
    
    def test_stock_validation(self):
        """주식 데이터 유효성 검증 테스트"""
        # 유효한 데이터
        valid_stock = Stock(
            symbol='AAPL',
            current_price=150.0,
            previous_close=147.5
        )
        assert valid_stock.is_valid() == True
        
        # 무효한 데이터 (음수 가격)
        invalid_stock = Stock(
            symbol='AAPL',
            current_price=-150.0,
            previous_close=147.5
        )
        assert invalid_stock.is_valid() == False

class TestSentimentModel:
    """센티먼트 모델 테스트"""
    
    def test_sentiment_creation(self, sample_sentiment_data):
        """센티먼트 데이터 생성 테스트"""
        sentiment = SentimentData(**sample_sentiment_data)
        
        assert sentiment.symbol == 'AAPL'
        assert sentiment.overall_sentiment == 0.65
        assert sentiment.mention_count == 1250
    
    def test_sentiment_classification(self):
        """센티먼트 분류 테스트"""
        # 긍정적 센티먼트
        positive_sentiment = SentimentData(
            symbol='AAPL',
            overall_sentiment=0.65
        )
        assert positive_sentiment.get_sentiment_label() == 'positive'
        
        # 부정적 센티먼트
        negative_sentiment = SentimentData(
            symbol='AAPL',
            overall_sentiment=-0.65
        )
        assert negative_sentiment.get_sentiment_label() == 'negative'
        
        # 중립적 센티먼트
        neutral_sentiment = SentimentData(
            symbol='AAPL',
            overall_sentiment=0.1
        )
        assert neutral_sentiment.get_sentiment_label() == 'neutral'
    
    def test_sentiment_confidence_score(self):
        """센티먼트 신뢰도 점수 테스트"""
        # 높은 신뢰도 (많은 언급)
        high_confidence = SentimentData(
            symbol='AAPL',
            overall_sentiment=0.65,
            mention_count=1000
        )
        assert high_confidence.get_confidence_score() > 0.8
        
        # 낮은 신뢰도 (적은 언급)
        low_confidence = SentimentData(
            symbol='AAPL',
            overall_sentiment=0.65,
            mention_count=10
        )
        assert low_confidence.get_confidence_score() < 0.5

class TestUserModel:
    """사용자 모델 테스트"""
    
    def test_user_creation(self, sample_user_data):
        """사용자 생성 테스트"""
        user = User(**sample_user_data)
        
        assert user.user_id == 'test_user_123'
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.is_active == True
    
    def test_user_email_validation(self):
        """사용자 이메일 유효성 검증 테스트"""
        # 유효한 이메일
        valid_user = User(
            user_id='test_user',
            email='test@example.com'
        )
        assert valid_user.is_valid_email() == True
        
        # 무효한 이메일
        invalid_user = User(
            user_id='test_user',
            email='invalid_email'
        )
        assert invalid_user.is_valid_email() == False
    
    def test_user_last_login_update(self):
        """사용자 최종 로그인 업데이트 테스트"""
        user = User(
            user_id='test_user',
            last_login='2023-12-01T10:00:00'
        )
        
        new_login_time = '2023-12-01T11:00:00'
        user.update_last_login(new_login_time)
        
        assert user.last_login == new_login_time
```

#### 1.2.2 서비스 테스트
```python
# tests/unit/test_services.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.stock_service import StockService
from app.services.sentiment_service import SentimentService
from app.services.user_service import UserService

class TestStockService:
    """주식 서비스 테스트"""
    
    @pytest.fixture
    def stock_service(self, test_session, test_redis):
        """주식 서비스 픽스처"""
        return StockService(test_session, test_redis)
    
    @pytest.mark.asyncio
    async def test_get_stock_info(self, stock_service, sample_stock_data):
        """주식 정보 조회 테스트"""
        # 데이터베이스에 샘플 데이터 저장
        from app.models.stock import Stock
        stock = Stock(**sample_stock_data)
        stock_service.session.add(stock)
        await stock_service.session.commit()
        
        # 서비스를 통해 데이터 조회
        result = await stock_service.get_stock_info('AAPL')
        
        assert result is not None
        assert result.symbol == 'AAPL'
        assert result.current_price == 150.0
    
    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, stock_service):
        """존재하지 않는 주식 정보 조회 테스트"""
        result = await stock_service.get_stock_info('NONEXISTENT')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_stock_price(self, stock_service, sample_stock_data):
        """주식 가격 업데이트 테스트"""
        # 초기 데이터 저장
        from app.models.stock import Stock
        stock = Stock(**sample_stock_data)
        stock_service.session.add(stock)
        await stock_service.session.commit()
        
        # 가격 업데이트
        new_price = 155.0
        await stock_service.update_stock_price('AAPL', new_price)
        
        # 업데이트 확인
        updated_stock = await stock_service.get_stock_info('AAPL')
        assert updated_stock.current_price == new_price
    
    @pytest.mark.asyncio
    async def test_search_stocks(self, stock_service, sample_stock_data):
        """주식 검색 테스트"""
        # 샘플 데이터 저장
        from app.models.stock import Stock
        stock = Stock(**sample_stock_data)
        stock_service.session.add(stock)
        await stock_service.session.commit()
        
        # 검색
        results = await stock_service.search_stocks('Apple')
        
        assert len(results) > 0
        assert any(stock.symbol == 'AAPL' for stock in results)
    
    @pytest.mark.asyncio
    async def test_get_trending_stocks(self, stock_service, sample_stock_data):
        """트렌딩 주식 조회 테스트"""
        # 샘플 데이터 저장
        from app.models.stock import Stock
        stock = Stock(**sample_stock_data)
        stock_service.session.add(stock)
        await stock_service.session.commit()
        
        # 트렌딩 주식 조회
        trending = await stock_service.get_trending_stocks(limit=10)
        
        assert isinstance(trending, list)
        assert len(trending) <= 10

class TestSentimentService:
    """센티먼트 서비스 테스트"""
    
    @pytest.fixture
    def sentiment_service(self, test_session, test_redis):
        """센티먼트 서비스 픽스처"""
        return SentimentService(test_session, test_redis)
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data(self, sentiment_service, sample_sentiment_data):
        """센티먼트 데이터 조회 테스트"""
        # 데이터베이스에 샘플 데이터 저장
        from app.models.sentiment import SentimentData
        sentiment = SentimentData(**sample_sentiment_data)
        sentiment_service.session.add(sentiment)
        await sentiment_service.session.commit()
        
        # 서비스를 통해 데이터 조회
        result = await sentiment_service.get_sentiment_data('AAPL')
        
        assert result is not None
        assert result.symbol == 'AAPL'
        assert result.overall_sentiment == 0.65
    
    @pytest.mark.asyncio
    async def test_calculate_sentiment_score(self, sentiment_service):
        """센티먼트 점수 계산 테스트"""
        mentions = [
            {'text': 'I love AAPL!', 'sentiment': 1.0},
            {'text': 'AAPL is okay', 'sentiment': 0.0},
            {'text': 'AAPL is terrible', 'sentiment': -1.0}
        ]
        
        score = await sentiment_service.calculate_sentiment_score(mentions)
        
        assert score == 0.0  # (1.0 + 0.0 - 1.0) / 3
    
    @pytest.mark.asyncio
    async def test_update_sentiment_data(self, sentiment_service, sample_sentiment_data):
        """센티먼트 데이터 업데이트 테스트"""
        # 초기 데이터 저장
        from app.models.sentiment import SentimentData
        sentiment = SentimentData(**sample_sentiment_data)
        sentiment_service.session.add(sentiment)
        await sentiment_service.session.commit()
        
        # 센티먼트 업데이트
        new_sentiment = 0.8
        await sentiment_service.update_sentiment_data('AAPL', new_sentiment)
        
        # 업데이트 확인
        updated_sentiment = await sentiment_service.get_sentiment_data('AAPL')
        assert updated_sentiment.overall_sentiment == new_sentiment
    
    @pytest.mark.asyncio
    async def test_get_sentiment_trends(self, sentiment_service, sample_sentiment_data):
        """센티먼트 트렌드 조회 테스트"""
        # 샘플 데이터 저장
        from app.models.sentiment import SentimentData
        sentiment = SentimentData(**sample_sentiment_data)
        sentiment_service.session.add(sentiment)
        await sentiment_service.session.commit()
        
        # 트렌드 조회
        trends = await sentiment_service.get_sentiment_trends('AAPL', days=7)
        
        assert isinstance(trends, list)
        assert len(trends) <= 7

class TestUserService:
    """사용자 서비스 테스트"""
    
    @pytest.fixture
    def user_service(self, test_session, test_redis):
        """사용자 서비스 픽스처"""
        return UserService(test_session, test_redis)
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_service, sample_user_data):
        """사용자 생성 테스트"""
        user = await user_service.create_user(
            username=sample_user_data['username'],
            email=sample_user_data['email']
        )
        
        assert user is not None
        assert user.username == sample_user_data['username']
        assert user.email == sample_user_data['email']
        assert user.is_active == True
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, sample_user_data):
        """ID로 사용자 조회 테스트"""
        # 사용자 생성
        user = await user_service.create_user(
            username=sample_user_data['username'],
            email=sample_user_data['email']
        )
        
        # ID로 조회
        found_user = await user_service.get_user_by_id(user.user_id)
        
        assert found_user is not None
        assert found_user.user_id == user.user_id
        assert found_user.username == user.username
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, user_service, sample_user_data):
        """사용자 설정 업데이트 테스트"""
        # 사용자 생성
        user = await user_service.create_user(
            username=sample_user_data['username'],
            email=sample_user_data['email']
        )
        
        # 설정 업데이트
        preferences = {'theme': 'dark', 'notifications': True}
        await user_service.update_user_preferences(user.user_id, preferences)
        
        # 업데이트 확인
        updated_user = await user_service.get_user_by_id(user.user_id)
        assert updated_user.preferences == preferences
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, sample_user_data):
        """사용자 비활성화 테스트"""
        # 사용자 생성
        user = await user_service.create_user(
            username=sample_user_data['username'],
            email=sample_user_data['email']
        )
        
        # 사용자 비활성화
        await user_service.deactivate_user(user.user_id)
        
        # 비활성화 확인
        deactivated_user = await user_service.get_user_by_id(user.user_id)
        assert deactivated_user.is_active == False
```

## 2. 통합 테스트

### 2.1 API 통합 테스트

#### 2.1.1 주식 API 테스트
```python
# tests/integration/test_stock_api.py
import pytest
from httpx import AsyncClient
from app.main import app

class TestStockAPI:
    """주식 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_stock_info(self, client: AsyncClient, sample_stock_data):
        """주식 정보 조회 API 테스트"""
        # 테스트 데이터 설정
        from app.models.stock import Stock
        from app.database import get_db_session
        
        # 데이터베이스에 샘플 데이터 저장
        async with get_db_session() as session:
            stock = Stock(**sample_stock_data)
            session.add(stock)
            await session.commit()
        
        # API 호출
        response = await client.get("/api/v1/stocks/AAPL")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data['symbol'] == 'AAPL'
        assert data['current_price'] == 150.0
        assert data['change'] == 2.5
    
    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, client: AsyncClient):
        """존재하지 않는 주식 정보 조회 API 테스트"""
        response = await client.get("/api/v1/stocks/NONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert data['detail'] == 'Stock not found'
    
    @pytest.mark.asyncio
    async def test_search_stocks(self, client: AsyncClient, sample_stock_data):
        """주식 검색 API 테스트"""
        # 테스트 데이터 설정
        from app.models.stock import Stock
        from app.database import get_db_session
        
        async with get_db_session() as session:
            stock = Stock(**sample_stock_data)
            session.add(stock)
            await session.commit()
        
        # API 호출
        response = await client.get("/api/v1/stocks/search?query=Apple")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) > 0
        assert any(stock['symbol'] == 'AAPL' for stock in data['results'])
    
    @pytest.mark.asyncio
    async def test_get_trending_stocks(self, client: AsyncClient):
        """트렌딩 주식 조회 API 테스트"""
        response = await client.get("/api/v1/stocks/trending")
        
        assert response.status_code == 200
        data = response.json()
        assert 'trending_stocks' in data
        assert isinstance(data['trending_stocks'], list)
    
    @pytest.mark.asyncio
    async def test_get_stock_historical_data(self, client: AsyncClient, sample_stock_data):
        """주식 과거 데이터 조회 API 테스트"""
        # 테스트 데이터 설정
        from app.models.stock import Stock
        from app.database import get_db_session
        
        async with get_db_session() as session:
            stock = Stock(**sample_stock_data)
            session.add(stock)
            await session.commit()
        
        # API 호출
        response = await client.get("/api/v1/stocks/AAPL/historical?period=1d")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert 'historical_data' in data
        assert isinstance(data['historical_data'], list)
    
    @pytest.mark.asyncio
    async def test_batch_stock_info(self, client: AsyncClient, sample_stock_data):
        """일괄 주식 정보 조회 API 테스트"""
        # 테스트 데이터 설정
        from app.models.stock import Stock
        from app.database import get_db_session
        
        async with get_db_session() as session:
            stock = Stock(**sample_stock_data)
            session.add(stock)
            await session.commit()
        
        # API 호출
        response = await client.post(
            "/api/v1/stocks/batch",
            json={"symbols": ["AAPL", "MSFT"]}
        )
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert 'AAPL' in data
        assert data['AAPL']['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_add_watchlist(self, client: AsyncClient, sample_user_data):
        """관심종목 추가 API 테스트"""
        # 사용자 인증 (가정)
        headers = {"Authorization": "Bearer test_token"}
        
        # API 호출
        response = await client.post(
            "/api/v1/users/watchlist",
            json={"symbol": "AAPL"},
            headers=headers
        )
        
        # 응답 검증
        assert response.status_code == 201
        data = response.json()
        assert data['message'] == 'Stock added to watchlist'
    
    @pytest.mark.asyncio
    async def test_remove_watchlist(self, client: AsyncClient):
        """관심종목 제거 API 테스트"""
        # 사용자 인증 (가정)
        headers = {"Authorization": "Bearer test_token"}
        
        # API 호출
        response = await client.delete(
            "/api/v1/users/watchlist/AAPL",
            headers=headers
        )
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Stock removed from watchlist'
```

#### 2.1.2 센티먼트 API 테스트
```python
# tests/integration/test_sentiment_api.py
import pytest
from httpx import AsyncClient
from app.main import app

class TestSentimentAPI:
    """센티먼트 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data(self, client: AsyncClient, sample_sentiment_data):
        """센티먼트 데이터 조회 API 테스트"""
        # 테스트 데이터 설정
        from app.models.sentiment import SentimentData
        from app.database import get_db_session
        
        async with get_db_session() as session:
            sentiment = SentimentData(**sample_sentiment_data)
            session.add(sentiment)
            await session.commit()
        
        # API 호출
        response = await client.get("/api/v1/sentiment/AAPL")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data['symbol'] == 'AAPL'
        assert data['overall_sentiment'] == 0.65
        assert data['mention_count'] == 1250
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data_not_found(self, client: AsyncClient):
        """존재하지 않는 센티먼트 데이터 조회 API 테스트"""
        response = await client.get("/api/v1/sentiment/NONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert data['detail'] == 'Sentiment data not found'
    
    @pytest.mark.asyncio
    async def test_get_sentiment_trends(self, client: AsyncClient):
        """센티먼트 트렌드 조회 API 테스트"""
        response = await client.get("/api/v1/sentiment/AAPL/trends?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert 'trends' in data
        assert isinstance(data['trends'], list)
    
    @pytest.mark.asyncio
    async def test_get_sentiment_comparison(self, client: AsyncClient):
        """센티먼트 비교 API 테스트"""
        response = await client.post(
            "/api/v1/sentiment/compare",
            json={"symbols": ["AAPL", "MSFT", "GOOGL"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'comparison' in data
        assert isinstance(data['comparison'], list)
    
    @pytest.mark.asyncio
    async def test_get_social_mentions(self, client: AsyncClient):
        """소셜 언급 조회 API 테스트"""
        response = await client.get("/api/v1/sentiment/AAPL/mentions?source=reddit&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert 'mentions' in data
        assert isinstance(data['mentions'], list)
        assert len(data['mentions']) <= 10
    
    @pytest.mark.asyncio
    async def test_get_sentiment_summary(self, client: AsyncClient):
        """센티먼트 요약 조회 API 테스트"""
        response = await client.get("/api/v1/sentiment/AAPL/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data
        assert 'overall_sentiment' in data['summary']
        assert 'mention_count' in data['summary']
```

### 2.2 데이터베이스 통합 테스트

#### 2.2.1 데이터베이스 연결 테스트
```python
# tests/integration/test_database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session, engine
from app.models.stock import Stock
from app.models.sentiment import SentimentData
from app.models.user import User

class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """데이터베이스 연결 테스트"""
        async with get_db_session() as session:
            # 간단한 쿼리 실행
            result = await session.execute("SELECT 1")
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_stock_crud_operations(self, test_session: AsyncSession):
        """주식 CRUD 작업 테스트"""
        # 생성
        stock_data = {
            'symbol': 'AAPL',
            'company_name': 'Apple Inc.',
            'current_price': 150.0,
            'previous_close': 147.5,
            'change': 2.5,
            'change_percent': 1.69
        }
        
        stock = Stock(**stock_data)
        test_session.add(stock)
        await test_session.commit()
        await test_session.refresh(stock)
        
        assert stock.stock_id is not None
        
        # 조회
        retrieved_stock = await test_session.get(Stock, stock.stock_id)
        assert retrieved_stock is not None
        assert retrieved_stock.symbol == 'AAPL'
        
        # 업데이트
        retrieved_stock.current_price = 155.0
        await test_session.commit()
        await test_session.refresh(retrieved_stock)
        
        assert retrieved_stock.current_price == 155.0
        
        # 삭제
        await test_session.delete(retrieved_stock)
        await test_session.commit()
        
        deleted_stock = await test_session.get(Stock, stock.stock_id)
        assert deleted_stock is None
    
    @pytest.mark.asyncio
    async def test_sentiment_crud_operations(self, test_session: AsyncSession):
        """센티먼트 CRUD 작업 테스트"""
        # 생성
        sentiment_data = {
            'symbol': 'AAPL',
            'overall_sentiment': 0.65,
            'reddit_sentiment': 0.7,
            'twitter_sentiment': 0.6,
            'mention_count': 1250
        }
        
        sentiment = SentimentData(**sentiment_data)
        test_session.add(sentiment)
        await test_session.commit()
        await test_session.refresh(sentiment)
        
        assert sentiment.sentiment_id is not None
        
        # 조회
        retrieved_sentiment = await test_session.get(SentimentData, sentiment.sentiment_id)
        assert retrieved_sentiment is not None
        assert retrieved_sentiment.symbol == 'AAPL'
        
        # 업데이트
        retrieved_sentiment.overall_sentiment = 0.7
        await test_session.commit()
        await test_session.refresh(retrieved_sentiment)
        
        assert retrieved_sentiment.overall_sentiment == 0.7
        
        # 삭제
        await test_session.delete(retrieved_sentiment)
        await test_session.commit()
        
        deleted_sentiment = await test_session.get(SentimentData, sentiment.sentiment_id)
        assert deleted_sentiment is None
    
    @pytest.mark.asyncio
    async def test_user_crud_operations(self, test_session: AsyncSession):
        """사용자 CRUD 작업 테스트"""
        # 생성
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'is_active': True
        }
        
        user = User(**user_data)
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        assert user.user_id is not None
        
        # 조회
        retrieved_user = await test_session.get(User, user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.username == 'testuser'
        
        # 업데이트
        retrieved_user.is_active = False
        await test_session.commit()
        await test_session.refresh(retrieved_user)
        
        assert retrieved_user.is_active == False
        
        # 삭제
        await test_session.delete(retrieved_user)
        await test_session.commit()
        
        deleted_user = await test_session.get(User, user.user_id)
        assert deleted_user is None
    
    @pytest.mark.asyncio
    async def test_relationships(self, test_session: AsyncSession):
        """모델 관계 테스트"""
        # 사용자 생성
        user = User(username='testuser', email='test@example.com')
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # 주식 생성
        stock = Stock(
            symbol='AAPL',
            company_name='Apple Inc.',
            current_price=150.0
        )
        test_session.add(stock)
        await test_session.commit()
        await test_session.refresh(stock)
        
        # 센티먼트 데이터 생성
        sentiment = SentimentData(
            symbol='AAPL',
            overall_sentiment=0.65,
            mention_count=1250
        )
        test_session.add(sentiment)
        await test_session.commit()
        await test_session.refresh(sentiment)
        
        # 관계 확인 (실제 관계에 따라 조정)
        # 이 예시에서는 가상의 관계를 가정
        assert user.user_id is not None
        assert stock.stock_id is not None
        assert sentiment.sentiment_id is not None
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_session: AsyncSession):
        """트랜잭션 롤백 테스트"""
        # 트랜잭션 시작
        await test_session.begin()
        
        try:
            # 데이터 생성
            stock = Stock(
                symbol='TEST',
                company_name='Test Company',
                current_price=100.0
            )
            test_session.add(stock)
            
            # 의도적으로 에러 발생
            raise Exception("Test exception")
            
        except Exception:
            # 롤백
            await test_session.rollback()
        
        # 롤백 확인
        from sqlalchemy import select
        result = await test_session.execute(select(Stock).where(Stock.symbol == 'TEST'))
        stocks = result.scalars().all()
        
        assert len(stocks) == 0
    
    @pytest.mark.asyncio
    async def test_database_constraints(self, test_session: AsyncSession):
        """데이터베이스 제약 조건 테스트"""
        # 고유 제약 조건 테스트
        stock1 = Stock(
            symbol='AAPL',
            company_name='Apple Inc.',
            current_price=150.0
        )
        test_session.add(stock1)
        await test_session.commit()
        
        # 동일한 심볼로 다른 주식 생성 (제약 조건 위반)
        stock2 = Stock(
            symbol='AAPL',
            company_name='Apple Inc. 2',
            current_price=155.0
        )
        test_session.add(stock2)
        
        # 제약 조건 위반으로 에러 발생
        with pytest.raises(Exception):  # 실제로는 IntegrityError
            await test_session.commit()
        
        # 롤백
        await test_session.rollback()
```

### 2.3 외부 서비스 통합 테스트

#### 2.3.1 외부 API 연동 테스트
```python
# tests/integration/test_external_apis.py
import pytest
from unittest.mock import AsyncMock, patch
from app.api_clients.yahoo_finance_client import YahooFinanceClient
from app.api_clients.reddit_client import RedditClient
from app.api_clients.twitter_client import TwitterClient

class TestYahooFinanceAPI:
    """Yahoo Finance API 통합 테스트"""
    
    @pytest.fixture
    def yahoo_config(self):
        """Yahoo Finance 설정 픽스처"""
        from app.api_clients.base_client import APIConfig
        return APIConfig(
            base_url="https://query1.finance.yahoo.com",
            api_key="test_key",
            api_secret="test_secret"
        )
    
    @pytest.mark.asyncio
    async def test_get_stock_info_success(self, yahoo_config):
        """주식 정보 조회 성공 테스트"""
        # 모킹된 응답
        mock_response = {
            'symbol': 'AAPL',
            'company_name': 'Apple Inc.',
            'current_price': 150.0,
            'change': 2.5,
            'change_percent': 1.69
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.info = mock_response
            mock_ticker.return_value = mock_ticker_instance
            
            client = YahooFinanceClient(yahoo_config)
            await client.initialize()
            
            result = await client.get_stock_info('AAPL')
            
            assert result is not None
            assert result['symbol'] == 'AAPL'
            assert result['current_price'] == 150.0
    
    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, yahoo_config):
        """존재하지 않는 주식 정보 조회 테스트"""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.info = None
            mock_ticker.return_value = mock_ticker_instance
            
            client = YahooFinanceClient(yahoo_config)
            await client.initialize()
            
            result = await client.get_stock_info('NONEXISTENT')
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_search_stocks(self, yahoo_config):
        """주식 검색 테스트"""
        mock_response = [
            {
                'symbol': 'AAPL',
                'company_name': 'Apple Inc.',
                'stock_type': 'Common Stock',
                'exchange': 'NASDAQ'
            }
        ]
        
        with patch('yfinance.Tickers') as mock_tickers:
            mock_tickers_instance = AsyncMock()
            mock_tickers_instance.tickers = [AsyncMock()]
            mock_tickers_instance.tickers[0].info = mock_response[0]
            mock_tickers.return_value = mock_tickers_instance
            
            client = YahooFinanceClient(yahoo_config)
            await client.initialize()
            
            result = await client.search_stocks('Apple')
            
            assert len(result) > 0
            assert result[0]['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, yahoo_config):
        """과거 데이터 조회 테스트"""
        import pandas as pd
        mock_historical_data = pd.DataFrame({
            'Open': [147.5, 148.0, 148.5],
            'High': [148.0, 148.5, 149.0],
            'Low': [147.0, 147.5, 148.0],
            'Close': [148.0, 148.5, 149.0],
            'Adj Close': [148.0, 148.5, 149.0],
            'Volume': [1000000, 1100000, 1200000]
        })
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.history.return_value = mock_historical_data
            mock_ticker.return_value = mock_ticker_instance
            
            client = YahooFinanceClient(yahoo_config)
            await client.initialize()
            
            result = await client.get_historical_data('AAPL', '1d')
            
            assert result is not None
            assert len(result) == 3
            assert result[0]['open'] == 147.5
            assert result[0]['close'] == 148.0

class TestRedditAPI:
    """Reddit API 통합 테스트"""
    
    @pytest.fixture
    def reddit_config(self):
        """Reddit 설정 픽스처"""
        from app.api_clients.base_client import APIConfig
        return APIConfig(
            base_url="https://oauth.reddit.com",
            api_key="test_key",
            api_secret="test_secret"
        )
    
    @pytest.mark.asyncio
    async def test_collect_mentions(self, reddit_config):
        """언급 데이터 수집 테스트"""
        mock_mentions = [
            {
                'symbol': 'AAPL',
                'text': 'AAPL is going to the moon!',
                'source': 'reddit',
                'community': 'wallstreetbets',
                'author': 'testuser',
                'timestamp': '2023-12-01T10:00:00',
                'upvotes': 100
            }
        ]
        
        with patch('praw.Reddit') as mock_reddit:
            mock_subreddit = AsyncMock()
            mock_post = AsyncMock()
            mock_post.created_utc = 1701427200  # 2023-12-01 10:00:00 UTC
            mock_post.score = 100
            mock_post.permalink = 'https://reddit.com/r/test/post/123'
            
            mock_subreddit.hot.return_value = [mock_post]
            mock_subreddit.new.return_value = [mock_post]
            
            mock_reddit_instance = AsyncMock()
            mock_reddit_instance.subreddit.return_value = mock_subreddit
            mock_reddit.return_value = mock_reddit_instance
            
            client = RedditClient(reddit_config)
            await client.initialize()
            
            result = await client.collect_mentions("24h")
            
            assert len(result) > 0
            assert result[0]['symbol'] == 'AAPL'
            assert result[0]['source'] == 'reddit'
    
    @pytest.mark.asyncio
    async def test_extract_stock_symbols(self, reddit_config):
        """주식 심볼 추출 테스트"""
        client = RedditClient(reddit_config)
        
        text1 = "I love $AAPL and think it will go up!"
        symbols1 = client._extract_stock_symbols(text1)
        assert 'AAPL' in symbols1
        
        text2 = "TSLA is also a good investment."
        symbols2 = client._extract_stock_symbols(text2)
        assert 'TSLA' in symbols2
        
        text3 = "THE AND FOR are common words, not stock symbols."
        symbols3 = client._extract_stock_symbols(text3)
        assert len(symbols3) == 0

class TestTwitterAPI:
    """Twitter API 통합 테스트"""
    
    @pytest.fixture
    def twitter_config(self):
        """Twitter 설정 픽스처"""
        from app.api_clients.base_client import APIConfig
        return APIConfig(
            base_url="https://api.twitter.com/2",
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret"
        )
    
    @pytest.mark.asyncio
    async def test_collect_mentions(self, twitter_config):
        """언급 데이터 수집 테스트"""
        mock_mentions = [
            {
                'symbol': 'AAPL',
                'text': 'Bullish on $AAPL',
                'source': 'twitter',
                'author': 'testuser',
                'timestamp': '2023-12-01T10:00:00',
                'upvotes': 50,
                'retweets': 10
            }
        ]
        
        with patch('tweepy.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_tweet = AsyncMock()
            mock_tweet.text = 'Bullish on $AAPL'
            mock_tweet.created_at = '2023-12-01T10:00:00'
            mock_tweet.author_id = 'testuser'
            mock_tweet.public_metrics = {
                'like_count': 50,
                'retweet_count': 10,
                'reply_count': 5,
                'quote_count': 2
            }
            mock_tweet.id = '123456789'
            
            mock_client_instance.search_recent_tweets.return_value = [mock_tweet]
            
            client = TwitterClient(twitter_config)
            await client.initialize()
            
            result = await client.collect_mentions()
            
            assert len(result) > 0
            assert result[0]['symbol'] == 'AAPL'
            assert result[0]['source'] == 'twitter'
    
    @pytest.mark.asyncio
    async def test_get_trending_topics(self, twitter_config):
        """트렌딩 토픽 조회 테스트"""
        mock_trending = [
            {
                'trends': [
                    {
                        'name': 'AAPL',
                        'url': 'https://twitter.com/search?q=AAPL',
                        'promoted_content': False,
                        'tweet_volume': 10000
                    }
                ]
            }
        ]
        
        with patch('tweepy.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_place_trends.return_value = mock_trending
            
            client = TwitterClient(twitter_config)
            await client.initialize()
            
            result = await client.get_trending_topics()
            
            assert len(result) > 0
            assert result[0]['name'] == 'AAPL'
            assert result[0]['tweet_volume'] == 10000
```

## 3. E2E 테스트

### 3.1 사용자 시나리오 테스트

#### 3.1.1 주식 검색 및 조회 시나리오
```python
# tests/e2e/test_stock_scenarios.py
import pytest
from playwright.async_api import async_playwright, Page, Browser
import asyncio

class TestStockScenarios:
    """주식 관련 E2E 시나리오 테스트"""
    
    @pytest.fixture
    async def browser(self):
        """Playwright 브라우저 픽스처"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def page(self, browser: Browser):
        """페이지 픽스처"""
        page = await browser.new_page()
        yield page
        await page.close()
    
    @pytest.mark.asyncio
    async def test_stock_search_and_view(self, page: Page):
        """주식 검색 및 조회 시나리오 테스트"""
        # 애플리케이션 접속
        await page.goto("http://localhost:8000")
        
        # 검색창에 주식 입력
        await page.fill('[data-testid="stock-search-input"]', "Apple")
        
        # 검색 버튼 클릭
        await page.click('[data-testid="search-button"]')
        
        # 검색 결과 대기
        await page.wait_for_selector('[data-testid="search-results"]')
        
        # Apple Inc. 결과 클릭
        await page.click('[data-testid="stock-result-AAPL"]')
        
        # 주식 상세 페이지 로드 확인
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 주식 정보 확인
        symbol = await page.text_content('[data-testid="stock-symbol"]')
        company_name = await page.text_content('[data-testid="company-name"]')
        current_price = await page.text_content('[data-testid="current-price"]')
        
        assert symbol == "AAPL"
        assert "Apple" in company_name
        assert "$" in current_price
        
        # 차트 탭 클릭
        await page.click('[data-testid="chart-tab"]')
        
        # 차트 로드 확인
        await page.wait_for_selector('[data-testid="stock-chart"]')
        
        # 기간 선택 (1개월)
        await page.select_option('[data-testid="period-select"]', "1M")
        
        # 차트 업데이트 확인
        await page.wait_for_timeout(1000)
        chart_visible = await page.is_visible('[data-testid="stock-chart"]')
        assert chart_visible
    
    @pytest.mark.asyncio
    async def test_add_to_watchlist(self, page: Page):
        """관심종목 추가 시나리오 테스트"""
        # 로그인 (가정)
        await page.goto("http://localhost:8000/login")
        await page.fill('[data-testid="username-input"]', "testuser")
        await page.fill('[data-testid="password-input"]', "testpassword")
        await page.click('[data-testid="login-button"]')
        
        # 메인 페이지로 이동 확인
        await page.wait_for_selector('[data-testid="main-content"]')
        
        # 주식 검색
        await page.fill('[data-testid="stock-search-input"]', "AAPL")
        await page.click('[data-testid="search-button"]')
        await page.wait_for_selector('[data-testid="search-results"]')
        await page.click('[data-testid="stock-result-AAPL"]')
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 관심종목 추가 버튼 클릭
        await page.click('[data-testid="add-to-watchlist-button"]')
        
        # 성공 메시지 확인
        success_message = await page.text_content('[data-testid="success-message"]')
        assert "added to watchlist" in success_message.lower()
        
        # 관심종목 페이지로 이동
        await page.click('[data-testid="watchlist-link"]')
        await page.wait_for_selector('[data-testid="watchlist"]')
        
        # 관심종목에 추가된 주식 확인
        watchlist_items = await page.query_selector_all('[data-testid="watchlist-item"]')
        assert len(watchlist_items) > 0
        
        # AAPL이 관심종목에 있는지 확인
        aapl_found = False
        for item in watchlist_items:
            symbol = await item.text_content('[data-testid="stock-symbol"]')
            if symbol == "AAPL":
                aapl_found = True
                break
        
        assert aapl_found
    
    @pytest.mark.asyncio
    async def test_compare_stocks(self, page: Page):
        """주식 비교 시나리오 테스트"""
        # 첫 번째 주식 검색 및 추가
        await page.goto("http://localhost:8000")
        await page.fill('[data-testid="stock-search-input"]', "AAPL")
        await page.click('[data-testid="search-button"]')
        await page.wait_for_selector('[data-testid="search-results"]')
        await page.click('[data-testid="stock-result-AAPL"]')
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 비교 버튼 클릭
        await page.click('[data-testid="compare-button"]')
        
        # 두 번째 주식 검색 및 추가
        await page.fill('[data-testid="compare-search-input"]', "MSFT")
        await page.click('[data-testid="compare-search-button"]')
        await page.wait_for_selector('[data-testid="compare-results"]')
        await page.click('[data-testid="compare-result-MSFT"]')
        
        # 비교 페이지로 이동 확인
        await page.wait_for_selector('[data-testid="comparison-chart"]')
        
        # 비교 데이터 확인
        compared_stocks = await page.query_selector_all('[data-testid="compared-stock"]')
        assert len(compared_stocks) == 2
        
        # AAPL과 MSFT가 모두 있는지 확인
        symbols = []
        for stock in compared_stocks:
            symbol = await stock.text_content('[data-testid="stock-symbol"]')
            symbols.append(symbol)
        
        assert "AAPL" in symbols
        assert "MSFT" in symbols
    
    @pytest.mark.asyncio
    async def test_stock_alerts(self, page: Page):
        """주식 알림 설정 시나리오 테스트"""
        # 로그인
        await page.goto("http://localhost:8000/login")
        await page.fill('[data-testid="username-input"]', "testuser")
        await page.fill('[data-testid="password-input"]', "testpassword")
        await page.click('[data-testid="login-button"]')
        
        # 주식 페이지로 이동
        await page.goto("http://localhost:8000/stocks/AAPL")
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 알림 설정 버튼 클릭
        await page.click('[data-testid="alert-settings-button"]')
        await page.wait_for_selector('[data-testid="alert-modal"]')
        
        # 가격 알림 설정
        await page.fill('[data-testid="price-threshold-input"]', "160")
        await page.select_option('[data-testid="price-condition-select"]', "above")
        await page.click('[data-testid="save-alert-button"]')
        
        # 성공 메시지 확인
        success_message = await page.text_content('[data-testid="alert-success-message"]')
        assert "alert created" in success_message.lower()
        
        # 알림 목록 확인
        await page.goto("http://localhost:8000/alerts")
        await page.wait_for_selector('[data-testid="alerts-list"]')
        
        alert_items = await page.query_selector_all('[data-testid="alert-item"]')
        assert len(alert_items) > 0
        
        # 설정한 알림이 있는지 확인
        alert_found = False
        for item in alert_items:
            symbol = await item.text_content('[data-testid="alert-symbol"]')
            condition = await item.text_content('[data-testid="alert-condition"]')
            
            if symbol == "AAPL" and "160" in condition:
                alert_found = True
                break
        
        assert alert_found
```

#### 3.1.2 센티먼트 분석 시나리오
```python
# tests/e2e/test_sentiment_scenarios.py
import pytest
from playwright.async_api import async_playwright, Page, Browser
import asyncio

class TestSentimentScenarios:
    """센티먼트 관련 E2E 시나리오 테스트"""
    
    @pytest.fixture
    async def browser(self):
        """Playwright 브라우저 픽스처"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def page(self, browser: Browser):
        """페이지 픽스처"""
        page = await browser.new_page()
        yield page
        await page.close()
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_view(self, page: Page):
        """센티먼트 분석 보기 시나리오 테스트"""
        # 주식 페이지로 이동
        await page.goto("http://localhost:8000/stocks/AAPL")
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 센티먼트 탭 클릭
        await page.click('[data-testid="sentiment-tab"]')
        await page.wait_for_selector('[data-testid="sentiment-analysis"]')
        
        # 센티먼트 정보 확인
        overall_sentiment = await page.text_content('[data-testid="overall-sentiment"]')
        mention_count = await page.text_content('[data-testid="mention-count"]')
        
        assert "sentiment" in overall_sentiment.lower()
        assert "mentions" in mention_count.lower()
        
        # 소셜 미디어 섹션 확인
        reddit_sentiment = await page.text_content('[data-testid="reddit-sentiment"]')
        twitter_sentiment = await page.text_content('[data-testid="twitter-sentiment"]')
        
        assert reddit_sentiment is not None
        assert twitter_sentiment is not None
        
        # 최근 언급 목록 확인
        mentions = await page.query_selector_all('[data-testid="mention-item"]')
        assert len(mentions) > 0
        
        # 언급 상세 확인
        first_mention = mentions[0]
        mention_text = await first_mention.text_content('[data-testid="mention-text"]')
        mention_source = await first_mention.text_content('[data-testid="mention-source"]')
        mention_time = await first_mention.text_content('[data-testid="mention-time"]')
        
        assert mention_text is not None
        assert mention_source in ["Reddit", "Twitter"]
        assert mention_time is not None
    
    @pytest.mark.asyncio
    async def test_sentiment_trends(self, page: Page):
        """센티먼트 트렌드 시나리오 테스트"""
        # 주식 페이지로 이동
        await page.goto("http://localhost:8000/stocks/AAPL")
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 센티먼트 탭 클릭
        await page.click('[data-testid="sentiment-tab"]')
        await page.wait_for_selector('[data-testid="sentiment-analysis"]')
        
        # 트렌드 섹션 확인
        await page.wait_for_selector('[data-testid="sentiment-trends"]')
        
        # 기간 선택 (7일)
        await page.select_option('[data-testid="trend-period-select"]', "7D")
        
        # 트렌드 차트 로드 확인
        await page.wait_for_selector('[data-testid="sentiment-trend-chart"]')
        
        # 트렌드 데이터 확인
        trend_points = await page.query_selector_all('[data-testid="trend-point"]')
        assert len(trend_points) > 0
        
        # 트렌드 요약 정보 확인
        trend_summary = await page.text_content('[data-testid="trend-summary"]')
        assert "trend" in trend_summary.lower()
    
    @pytest.mark.asyncio
    async def test_sentiment_comparison(self, page: Page):
        """센티먼트 비교 시나리오 테스트"""
        # 센티먼트 비교 페이지로 이동
        await page.goto("http://localhost:8000/sentiment/compare")
        await page.wait_for_selector('[data-testid="sentiment-comparison"]')
        
        # 첫 번째 주식 추가
        await page.fill('[data-testid="compare-stock-1-input"]', "AAPL")
        await page.click('[data-testid="add-stock-1-button"]')
        await page.wait_for_selector('[data-testid="stock-1-added"]')
        
        # 두 번째 주식 추가
        await page.fill('[data-testid="compare-stock-2-input"]', "MSFT")
        await page.click('[data-testid="add-stock-2-button"]')
        await page.wait_for_selector('[data-testid="stock-2-added"]')
        
        # 비교 실행
        await page.click('[data-testid="compare-sentiment-button"]')
        await page.wait_for_selector('[data-testid="comparison-results"]')
        
        # 비교 결과 확인
        compared_stocks = await page.query_selector_all('[data-testid="compared-sentiment-stock"]')
        assert len(compared_stocks) == 2
        
        # 각 주식의 센티먼트 정보 확인
        for stock in compared_stocks:
            symbol = await stock.text_content('[data-testid="stock-symbol"]')
            sentiment = await stock.text_content('[data-testid="stock-sentiment"]')
            mentions = await stock.text_content('[data-testid="stock-mentions"]')
            
            assert symbol in ["AAPL", "MSFT"]
            assert sentiment is not None
            assert mentions is not None
    
    @pytest.mark.asyncio
    async def test_sentiment_alerts(self, page: Page):
        """센티먼트 알림 시나리오 테스트"""
        # 로그인
        await page.goto("http://localhost:8000/login")
        await page.fill('[data-testid="username-input"]', "testuser")
        await page.fill('[data-testid="password-input"]', "testpassword")
        await page.click('[data-testid="login-button"]')
        
        # 주식 페이지로 이동
        await page.goto("http://localhost:8000/stocks/AAPL")
        await page.wait_for_selector('[data-testid="stock-details"]')
        
        # 센티먼트 탭 클릭
        await page.click('[data-testid="sentiment-tab"]')
        await page.wait_for_selector('[data-testid="sentiment-analysis"]')
        
        # 알림 설정 버튼 클릭
        await page.click('[data-testid="sentiment-alert-button"]')
        await page.wait_for_selector('[data-testid="sentiment-alert-modal"]')
        
        # 센티먼트 알림 설정
        await page.select_option('[data-testid="sentiment-threshold-select"]', "positive")
        await page.fill('[data-testid="sentiment-threshold-input"]', "0.8")
        await page.click('[data-testid="save-sentiment-alert-button"]')
        
        # 성공 메시지 확인
        success_message = await page.text_content('[data-testid="alert-success-message"]')
        assert "alert created" in success_message.lower()
        
        # 알림 목록 확인
        await page.goto("http://localhost:8000/alerts")
        await page.wait_for_selector('[data-testid="alerts-list"]')
        
        # 설정한 센티먼트 알림이 있는지 확인
        alert_items = await page.query_selector_all('[data-testid="alert-item"]')
        sentiment_alert_found = False
        
        for item in alert_items:
            alert_type = await item.text_content('[data-testid="alert-type"]')
            if "sentiment" in alert_type.lower():
                sentiment_alert_found = True
                break
        
        assert sentiment_alert_found
```

## 4. 테스트 자동화

### 4.1 CI/CD 파이프라인

#### 4.1.1 GitHub Actions 워크플로우
```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_insitechart
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 app tests
        black --check app tests
        isort --check-only app tests
    
    - name: Run type checking
      run: |
        mypy app
    
    - name: Run security checks
      run: |
        bandit -r app
        safety check
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        pytest tests/unit -v --cov=app --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_insitechart
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
        YAHOO_API_KEY: ${{ secrets.YAHOO_API_KEY }}
        REDDIT_API_KEY: ${{ secrets.REDDIT_API_KEY }}
        TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
      run: |
        pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install Playwright
      run: |
        npm install -g playwright
        playwright install chromium
    
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Start application
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        sleep 10
    
    - name: Run E2E tests
      run: |
        pytest tests/e2e -v --browser chromium
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: playwright-report
        path: playwright-report/

  performance-tests:
    runs-on: ubuntu-latest
    needs: e2e-tests
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        pip install locust
    
    - name: Start application
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        sleep 10
    
    - name: Run performance tests
      run: |
        locust -f tests/performance/locustfile.py --headless --users 100 --spawn-rate 10 --run-time 60s --host http://localhost:8000
```

### 4.2 테스트 보고

#### 4.2.1 테스트 결과 수집
```python
# tests/utils/test_reporter.py
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import pytest
from _pytest.config import Config
from _pytest.reports import TestReport

class TestReporter:
    """테스트 결과 보고서 생성기"""
    
    def __init__(self, config: Config):
        self.config = config
        self.results = {
            'test_run': {
                'start_time': None,
                'end_time': None,
                'duration': None,
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': 0
            },
            'tests': [],
            'coverage': {},
            'performance': {}
        }
    
    def pytest_runtest_logreport(self, report: TestReport):
        """테스트 결과 로깅"""
        if report.when == 'call':
            test_result = {
                'name': report.nodeid,
                'outcome': report.outcome,
                'duration': report.duration,
                'keywords': list(report.keywords),
                'sections': []
            }
            
            # 섹션 정보 추가
            for section in report.sections:
                test_result['sections'].append({
                    'name': section[0],
                    'content': section[1]
                })
            
            # 실패 정보 추가
            if report.failed:
                test_result['failure'] = {
                    'message': str(report.longrepr),
                    'traceback': report.longreprtext if hasattr(report, 'longreprtext') else None
                }
            
            self.results['tests'].append(test_result)
            
            # 통계 업데이트
            self.results['test_run']['total_tests'] += 1
            
            if report.passed:
                self.results['test_run']['passed'] += 1
            elif report.failed:
                self.results['test_run']['failed'] += 1
            elif report.skipped:
                self.results['test_run']['skipped'] += 1
    
    def pytest_sessionstart(self, session):
        """테스트 세션 시작"""
        self.results['test_run']['start_time'] = datetime.now().isoformat()
    
    def pytest_sessionfinish(self, session):
        """테스트 세션 종료"""
        self.results['test_run']['end_time'] = datetime.now().isoformat()
        
        # 기간 계산
        if self.results['test_run']['start_time']:
            start = datetime.fromisoformat(self.results['test_run']['start_time'])
            end = datetime.fromisoformat(self.results['test_run']['end_time'])
            self.results['test_run']['duration'] = (end - start).total_seconds()
        
        # 보고서 생성
        self._generate_report()
    
    def _generate_report(self):
        """테스트 보고서 생성"""
        # JSON 보고서
        self._generate_json_report()
        
        # HTML 보고서
        self._generate_html_report()
        
        # 커버리지 보고서
        self._generate_coverage_report()
    
    def _generate_json_report(self):
        """JSON 보고서 생성"""
        report_dir = os.path.join(os.getcwd(), 'test-reports')
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, 'test-results.json')
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def _generate_html_report(self):
        """HTML 보고서 생성"""
        report_dir = os.path.join(os.getcwd(), 'test-reports')
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, 'test-results.html')
        
        # HTML 템플릿
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Results</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .passed { color: green; }
                .failed { color: red; }
                .skipped { color: orange; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>Test Results</h1>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {total_tests}</p>
                <p class="passed">Passed: {passed}</p>
                <p class="failed">Failed: {failed}</p>
                <p class="skipped">Skipped: {skipped}</p>
                <p>Duration: {duration:.2f} seconds</p>
            </div>
            
            <h2>Test Details</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Outcome</th>
                    <th>Duration (s)</th>
                    <th>Failure Message</th>
                </tr>
                {test_rows}
            </table>
        </body>
        </html>
        """
        
        # 테스트 행 생성
        test_rows = ""
        for test in self.results['tests']:
            outcome_class = test['outcome']
            failure_message = ""
            
            if test['outcome'] == 'failed' and 'failure' in test:
                failure_message = test['failure']['message']
            
            test_rows += f"""
            <tr>
                <td>{test['name']}</td>
                <td class="{outcome_class}">{test['outcome']}</td>
                <td>{test['duration']:.3f}</td>
                <td>{failure_message}</td>
            </tr>
            """
        
        # HTML 렌더링
        html_content = html_template.format(
            total_tests=self.results['test_run']['total_tests'],
            passed=self.results['test_run']['passed'],
            failed=self.results['test_run']['failed'],
            skipped=self.results['test_run']['skipped'],
            duration=self.results['test_run']['duration'] or 0,
            test_rows=test_rows
        )
        
        with open(report_file, 'w') as f:
            f.write(html_content)
    
    def _generate_coverage_report(self):
        """커버리지 보고서 생성"""
        # 커버리지 데이터 로드 (가정)
        coverage_file = os.path.join(os.getcwd(), 'coverage.json')
        
        if os.path.exists(coverage_file):
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            self.results['coverage'] = coverage_data
            
            # 커버리지 보고서 생성
            report_dir = os.path.join(os.getcwd(), 'test-reports')
            os.makedirs(report_dir, exist_ok=True)
            
            coverage_report_file = os.path.join(report_dir, 'coverage-report.html')
            
            # 커버리지 HTML 템플릿
            coverage_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Coverage Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    .low-coverage { background-color: #ffcccc; }
                    .medium-coverage { background-color: #ffffcc; }
                    .high-coverage { background-color: #ccffcc; }
                </style>
            </head>
            <body>
                <h1>Coverage Report</h1>
                
                <div class="summary">
                    <h2>Summary</h2>
                    <p>Total Coverage: {total_coverage:.1f}%</p>
                    <p>Lines Covered: {lines_covered}/{total_lines}</p>
                </div>
                
                <h2>Coverage by File</h2>
                <table>
                    <tr>
                        <th>File</th>
                        <th>Coverage</th>
                        <th>Lines Covered</th>
                        <th>Total Lines</th>
                    </tr>
                    {file_rows}
                </table>
            </body>
            </html>
            """
            
            # 파일 커버리지 행 생성
            file_rows = ""
            for file_data in coverage_data.get('files', []):
                filename = file_data.get('filename', '')
                coverage = file_data.get('coverage', 0)
                lines_covered = file_data.get('lines_covered', 0)
                total_lines = file_data.get('total_lines', 0)
                
                # 커버리지 수준에 따른 클래스 결정
                if coverage < 50:
                    coverage_class = 'low-coverage'
                elif coverage < 80:
                    coverage_class = 'medium-coverage'
                else:
                    coverage_class = 'high-coverage'
                
                file_rows += f"""
                <tr class="{coverage_class}">
                    <td>{filename}</td>
                    <td>{coverage:.1f}%</td>
                    <td>{lines_covered}</td>
                    <td>{total_lines}</td>
                </tr>
                """
            
            # HTML 렌더링
            html_content = coverage_template.format(
                total_coverage=coverage_data.get('total_coverage', 0),
                lines_covered=coverage_data.get('lines_covered', 0),
                total_lines=coverage_data.get('total_lines', 0),
                file_rows=file_rows
            )
            
            with open(coverage_report_file, 'w') as f:
                f.write(html_content)

# pytest 플러그인 등록
def pytest_configure(config):
    """pytest 설정"""
    config.pluginmanager.register(TestReporter(config), 'test-reporter')
```

이 테스트 전략 문서는 포괄적인 테스트 접근 방식을 제공합니다. 단위 테스트, 통합 테스트, E2E 테스트를 통해 시스템의 각 계층을 철저히 검증하고, CI/CD 파이프라인과 자동화된 테스트 보고를 통해 개발 프로세스의 품질을 보장할 수 있습니다.