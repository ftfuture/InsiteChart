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

### 1.2 기본 단위 테스트

#### 1.2.1 모델 테스트
```python
# tests/unit/test_models.py
import pytest
from app.models.stock import Stock
from app.models.sentiment import SentimentData

class TestStockModel:
    """주식 모델 테스트"""
    
    def test_stock_creation(self, sample_stock_data):
        """주식 생성 테스트"""
        stock = Stock(**sample_stock_data)
        
        assert stock.symbol == 'AAPL'
        assert stock.company_name == 'Apple Inc.'
        assert stock.current_price == 150.0
        assert stock.change == 2.5
    
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
```

#### 1.2.2 서비스 테스트
```python
# tests/unit/test_services.py
import pytest
from app.services.stock_service import StockService
from app.services.sentiment_service import SentimentService

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
```

## 2. 기본 통합 테스트

### 2.1 API 통합 테스트

#### 2.1.1 주식 API 테스트
```python
# tests/integration/test_stock_api.py
import pytest
from httpx import AsyncClient

class TestStockAPI:
    """주식 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_stock_info(self, client: AsyncClient, sample_stock_data):
        """주식 정보 조회 API 테스트"""
        # 테스트 데이터 설정
        from app.models.stock import Stock
        stock = Stock(**sample_stock_data)
        client.app.dependency_overrides[get_db_session]().add(stock)
        await client.app.dependency_overrides[get_db_session]().commit()
        
        # API 호출
        response = await client.get("/api/v1/stocks/AAPL")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data['symbol'] == 'AAPL'
        assert data['current_price'] == 150.0
    
    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, client: AsyncClient):
        """존재하지 않는 주식 정보 조회 API 테스트"""
        response = await client.get("/api/v1/stocks/NONEXISTENT")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_search_stocks(self, client: AsyncClient, sample_stock_data):
        """주식 검색 API 테스트"""
        # 테스트 데이터 설정
        from app.models.stock import Stock
        stock = Stock(**sample_stock_data)
        client.app.dependency_overrides[get_db_session]().add(stock)
        await client.app.dependency_overrides[get_db_session]().commit()
        
        # API 호출
        response = await client.get("/api/v1/stocks/search?query=Apple")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) > 0

#### 2.1.2 센티먼트 API 테스트
```python
# tests/integration/test_sentiment_api.py
import pytest
from httpx import AsyncClient

class TestSentimentAPI:
    """센티먼트 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data(self, client: AsyncClient, sample_sentiment_data):
        """센티먼트 데이터 조회 API 테스트"""
        # 테스트 데이터 설정
        from app.models.sentiment import SentimentData
        sentiment = SentimentData(**sample_sentiment_data)
        client.app.dependency_overrides[get_db_session]().add(sentiment)
        await client.app.dependency_overrides[get_db_session]().commit()
        
        # API 호출
        response = await client.get("/api/v1/sentiment/AAPL")
        
        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data['symbol'] == 'AAPL'
        assert data['overall_sentiment'] == 0.65
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data_not_found(self, client: AsyncClient):
        """존재하지 않는 센티먼트 데이터 조회 API 테스트"""
        response = await client.get("/api/v1/sentiment/NONEXISTENT")
        
        assert response.status_code == 404
```

### 2.2 기본 데이터베이스 통합 테스트

#### 2.2.1 데이터베이스 연결 테스트
```python
# tests/integration/test_database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.stock import Stock
from app.models.sentiment import SentimentData

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
            'previous_close': 147.5
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
```

## 3. 기본 E2E 테스트

### 3.1 기본 사용자 시나리오 테스트

#### 3.1.1 주식 검색 및 조회 시나리오
```python
# tests/e2e/test_stock_scenarios.py
import pytest
from playwright.async_api import async_playwright, Page, Browser

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
```

## 4. 기본 테스트 자동화

### 4.1 단순화된 CI/CD 파이프라인

#### 4.1.1 기본 GitHub Actions 워크플로우
```yaml
# .github/workflows/simple-test.yml
name: Simple Test Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
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
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        pytest tests/unit -v --cov=app --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest httpx
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        pytest tests/integration -v
```

### 4.2 기본 테스트 보고

#### 4.2.1 단순화된 테스트 결과 수집
```python
# tests/utils/simple_test_reporter.py
import json
import os
from datetime import datetime
from typing import Dict, Any
import pytest

class SimpleTestReporter:
    """단순화된 테스트 결과 보고서 생성기"""
    
    def __init__(self):
        self.results = {
            'test_run': {
                'start_time': None,
                'end_time': None,
                'duration': None,
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            },
            'tests': []
        }
    
    def pytest_runtest_logreport(self, report):
        """테스트 결과 로깅"""
        if report.when == 'call':
            test_result = {
                'name': report.nodeid,
                'outcome': report.outcome,
                'duration': report.duration
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
        report_dir = os.path.join(os.getcwd(), 'test-reports')
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, 'test-results.json')
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)

# pytest 플러그인 등록
def pytest_configure(config):
    """pytest 설정"""
    config.pluginmanager.register(SimpleTestReporter(), 'simple-test-reporter')
```

이 단순화된 테스트 전략 문서는 기본적인 테스트 접근 방식을 제공합니다. 단위 테스트, 통합 테스트, E2E 테스트를 통해 시스템의 각 계층을 기본적으로 검증하고, 단순화된 CI/CD 파이프라인과 테스트 보고를 통해 개발 프로세스의 기본적인 품질을 보장할 수 있습니다.