# 테스트 프레임워크 구축 계획

## 1. 개요

본 문서는 주식 차트 분석 애플리케이션의 포괄적인 테스트 프레임워크 구축을 위한 상세한 계획을 제시합니다. 단위 테스트, 통합 테스트, E2E 테스트, 성능 테스트, 보안 테스트 등 다양한 테스트 레벨과 자동화된 테스트 파이프라인을 다룹니다.

## 2. 테스트 전략 아키텍처

### 2.1 테스트 피라미드

```
┌─────────────────────────────────────────────────────────────┐
│                   E2E Tests (10%)                       │
│  • 사용자 시나리오 테스트                            │
│  • 크로스 브라우저 테스트                             │
│  • 실제 데이터 통합 테스트                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                Integration Tests (20%)                    │
│  • API 통합 테스트                                   │
│  • 데이터베이스 연동 테스트                           │
│  • 마이크로서비스 통합 테스트                         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                Unit Tests (70%)                          │
│  • 개별 컴포넌트 테스트                             │
│  • 비즈니스 로직 테스트                               │
│  • 유틸리티 함수 테스트                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 테스트 환경 구성

```mermaid
graph TD
    A[개발자 로컬] --> B[단위 테스트]
    A --> C[통합 테스트]
    
    D[CI/CD 파이프라인] --> E[자동화된 테스트]
    E --> F[단위 테스트]
    E --> G[통합 테스트]
    E --> H[E2E 테스트]
    E --> I[성능 테스트]
    E --> J[보안 테스트]
    
    K[테스트 환경] --> L[통합 테스트]
    K --> M[E2E 테스트]
    K --> N[성능 테스트]
    
    O[프로덕션 환경] --> P[모니터링 테스트]
    O --> Q[카나리 릴리즈]
```

## 3. 단위 테스트 프레임워크

### 3.1 테스트 구조 설정
```python
# tests/conftest.py
import pytest
import asyncio
import redis
import asyncpg
from fastapi.testclient import TestClient
from httpx import AsyncClient
import tempfile
import os
from unittest.mock import Mock, AsyncMock

# 테스트 데이터베이스 설정
@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 생성"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """테스트 데이터베이스 연결"""
    dsn = "postgresql://test_user:test_pass@localhost:5433/test_db"
    conn = await asyncpg.connect(dsn)
    
    # 테스트 데이터베이스 초기화
    await _init_test_db(conn)
    
    yield conn
    
    await conn.close()

@pytest.fixture(scope="session")
async def test_redis():
    """테스트 Redis 연결"""
    redis_client = redis.Redis(host='localhost', port=6380, db=1)
    
    # 테스트 Redis 초기화
    redis_client.flushdb()
    
    yield redis_client
    
    redis_client.flushdb()

@pytest.fixture
def test_client():
    """FastAPI 테스트 클라이언트"""
    from app.main import app
    return TestClient(app)

@pytest.fixture
async def async_test_client():
    """비동기 FastAPI 테스트 클라이언트"""
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_yfinance():
    """yfinance 모의 객체"""
    with pytest.mock.patch('yfinance.Ticker') as mock_ticker:
        yield mock_ticker

@pytest.fixture
def mock_reddit():
    """Reddit API 모의 객체"""
    with pytest.mock.patch('praw.Reddit') as mock_reddit:
        yield mock_reddit

@pytest.fixture
def mock_twitter():
    """Twitter API 모의 객체"""
    with pytest.mock.patch('tweepy.Client') as mock_twitter:
        yield mock_twitter

async def _init_test_db(conn):
    """테스트 데이터베이스 초기화"""
    # 테스트 테이블 생성
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS test_stock_data (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            symbol VARCHAR(10) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            open DECIMAL(10,2),
            high DECIMAL(10,2),
            low DECIMAL(10,2),
            close DECIMAL(10,2),
            volume BIGINT
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS test_sentiment_data (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            symbol VARCHAR(10) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            sentiment_score DECIMAL(3,2),
            confidence DECIMAL(3,2),
            platform VARCHAR(20)
        )
    """)

# 테스트 데이터 생성기
@pytest.fixture
def sample_stock_data():
    """샘플 주식 데이터"""
    return {
        'symbol': 'AAPL',
        'timestamp': '2024-01-01T10:00:00Z',
        'open': 150.00,
        'high': 155.00,
        'low': 149.00,
        'close': 154.50,
        'volume': 1000000
    }

@pytest.fixture
def sample_sentiment_data():
    """샘플 감성 데이터"""
    return {
        'symbol': 'AAPL',
        'timestamp': '2024-01-01T10:00:00Z',
        'sentiment_score': 0.65,
        'confidence': 0.85,
        'platform': 'reddit'
    }
```

### 3.2 서비스 단위 테스트
```python
# tests/unit/test_stock_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from datetime import datetime, timedelta

from services.stock_service import StockService
from models.stock_models import StockData, StockQuote

class TestStockService:
    @pytest.fixture
    def stock_service(self, test_db, test_redis):
        return StockService(test_db, test_redis)
    
    @pytest.mark.asyncio
    async def test_get_stock_quote_success(self, stock_service, mock_yfinance):
        """주식 현재가 조회 성공 테스트"""
        # 모의 데이터 설정
        mock_ticker = Mock()
        mock_ticker.info = {
            'currentPrice': 154.50,
            'previousClose': 150.00,
            'volume': 1000000,
            'marketCap': 2500000000000
        }
        mock_yfinance.return_value = mock_ticker
        
        # 테스트 실행
        result = await stock_service.get_stock_quote('AAPL')
        
        # 결과 검증
        assert result.symbol == 'AAPL'
        assert result.price == 154.50
        assert result.change == 4.50
        assert result.change_percent == 3.0
        assert result.volume == 1000000
        
        # yfinance 호출 확인
        mock_yfinance.assert_called_once_with('AAPL')
    
    @pytest.mark.asyncio
    async def test_get_stock_quote_invalid_symbol(self, stock_service, mock_yfinance):
        """잘못된 심볼로 주식 조회 테스트"""
        # 모의 데이터 설정
        mock_ticker = Mock()
        mock_ticker.info = {}
        mock_yfinance.return_value = mock_ticker
        
        # 테스트 실행 및 예외 확인
        with pytest.raises(ValueError, match="Invalid stock symbol"):
            await stock_service.get_stock_quote('INVALID')
    
    @pytest.mark.asyncio
    async def test_get_stock_history_success(self, stock_service, mock_yfinance):
        """주식 과거 데이터 조회 성공 테스트"""
        # 모의 데이터 설정
        mock_ticker = Mock()
        mock_history = pd.DataFrame({
            'Open': [150.00, 151.00, 152.00],
            'High': [155.00, 153.00, 154.00],
            'Low': [149.00, 150.00, 151.00],
            'Close': [154.50, 152.50, 153.00],
            'Volume': [1000000, 1200000, 900000]
        }, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        mock_ticker.history.return_value = mock_history
        mock_yfinance.return_value = mock_ticker
        
        # 테스트 실행
        result = await stock_service.get_stock_history('AAPL', '1mo')
        
        # 결과 검증
        assert len(result) == 3
        assert result[0].symbol == 'AAPL'
        assert result[0].open == 150.00
        assert result[0].high == 155.00
        assert result[0].low == 149.00
        assert result[0].close == 154.50
        assert result[0].volume == 1000000
        
        # yfinance 호출 확인
        mock_yfinance.assert_called_once_with('AAPL')
        mock_ticker.history.assert_called_once_with(period='1mo')
    
    @pytest.mark.asyncio
    async def test_calculate_technical_indicators(self, stock_service):
        """기술적 지표 계산 테스트"""
        # 테스트 데이터
        stock_data = [
            StockData(
                symbol='AAPL',
                timestamp=datetime(2024, 1, 1),
                open=150.00,
                high=155.00,
                low=149.00,
                close=154.50,
                volume=1000000
            ),
            StockData(
                symbol='AAPL',
                timestamp=datetime(2024, 1, 2),
                open=154.50,
                high=156.00,
                low=153.00,
                close=155.00,
                volume=1200000
            ),
            StockData(
                symbol='AAPL',
                timestamp=datetime(2024, 1, 3),
                open=155.00,
                high=157.00,
                low=154.00,
                close=156.50,
                volume=900000
            )
        ]
        
        # 테스트 실행
        indicators = await stock_service.calculate_technical_indicators(stock_data)
        
        # 결과 검증
        assert 'sma_20' in indicators
        assert 'rsi' in indicators
        assert 'macd' in indicators
        assert 'bollinger_bands' in indicators
        
        # SMA 계산 검증
        expected_sma = (154.50 + 155.00 + 156.50) / 3
        assert abs(indicators['sma_20'] - expected_sma) < 0.01
    
    @pytest.mark.asyncio
    async def test_cache_stock_quote(self, stock_service, test_redis):
        """주식 데이터 캐싱 테스트"""
        # 캐시 모의 설정
        test_redis.get.return_value = None
        test_redis.setex.return_value = True
        
        # 테스트 실행
        with patch.object(stock_service, '_fetch_from_yfinance') as mock_fetch:
            mock_fetch.return_value = StockQuote(
                symbol='AAPL',
                price=154.50,
                change=4.50,
                change_percent=3.0,
                volume=1000000
            )
            
            result = await stock_service.get_stock_quote('AAPL')
            
            # 캐시 저장 확인
            test_redis.setex.assert_called_once()
            cache_key = test_redis.setex.call_args[0][0]
            assert 'stock_quote:AAPL' in cache_key
            assert test_redis.setex.call_args[0][1] == 60  # TTL 60초
```

### 3.3 API 엔드포인트 단위 테스트
```python
# tests/unit/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, AsyncMock

class TestStockAPI:
    def test_get_stock_quote_success(self, test_client, mock_yfinance):
        """주식 현재가 API 성공 테스트"""
        # 모의 데이터 설정
        mock_ticker = Mock()
        mock_ticker.info = {
            'currentPrice': 154.50,
            'previousClose': 150.00,
            'volume': 1000000
        }
        mock_yfinance.return_value = mock_ticker
        
        # API 호출
        response = test_client.get("/api/v1/stocks/AAPL/quote")
        
        # 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert data['symbol'] == 'AAPL'
        assert data['price'] == 154.50
        assert data['change'] == 4.50
        assert data['volume'] == 1000000
    
    def test_get_stock_quote_invalid_symbol(self, test_client, mock_yfinance):
        """잘못된 심볼 API 테스트"""
        # 모의 데이터 설정
        mock_ticker = Mock()
        mock_ticker.info = {}
        mock_yfinance.return_value = mock_ticker
        
        # API 호출
        response = test_client.get("/api/v1/stocks/INVALID/quote")
        
        # 결과 검증
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        assert data['error']['code'] == 'INVALID_SYMBOL'
    
    def test_search_stocks_success(self, test_client):
        """주식 검색 API 성공 테스트"""
        # 모의 데이터 설정
        with patch('services.stock_service.search_stocks') as mock_search:
            mock_search.return_value = [
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'EQUITY'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'type': 'EQUITY'}
            ]
            
            # API 호출
            response = test_client.get("/api/v1/stocks/search?q=Apple")
            
            # 결과 검증
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]['symbol'] == 'AAPL'
            assert data[0]['name'] == 'Apple Inc.'
    
    def test_rate_limiting(self, test_client):
        """속도 제한 테스트"""
        # 여러 요청 보내기
        responses = []
        for _ in range(150):  # 속도 제한 초과
            response = test_client.get("/api/v1/stocks/AAPL/quote")
            responses.append(response)
        
        # 속도 제한 확인
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0
        
        # 속도 제한 응답 헤더 확인
        rate_limit_response = rate_limited_responses[0]
        assert 'X-RateLimit-Limit' in rate_limit_response.headers
        assert 'X-RateLimit-Remaining' in rate_limit_response.headers
        assert 'X-RateLimit-Reset' in rate_limit_response.headers

class TestSentimentAPI:
    @pytest.mark.asyncio
    async def test_get_sentiment_current_success(self, async_test_client, mock_reddit, mock_twitter):
        """현재 감성 분석 API 성공 테스트"""
        # 모의 데이터 설정
        mock_reddit.return_value.search.return_value = []
        mock_twitter.return_value.search_recent_tweets.return_value.data = []
        
        # API 호출
        response = await async_test_client.get("/api/v1/sentiment/AAPL/current")
        
        # 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert 'symbol' in data
        assert 'current_sentiment' in data
        assert 'mention_volume' in data
        assert 'analysis_timestamp' in data
    
    @pytest.mark.asyncio
    async def test_get_sentiment_history_success(self, async_test_client):
        """감성 과거 데이터 API 성공 테스트"""
        # API 호출
        response = await async_test_client.get("/api/v1/sentiment/AAPL/history?days=7")
        
        # 결과 검증
        assert response.status_code == 200
        data = response.json()
        assert 'symbol' in data
        assert 'history' in data
        assert len(data['history']) <= 7  # 최대 7일 데이터
```

## 4. 통합 테스트 프레임워크

### 4.1 데이터베이스 통합 테스트
```python
# tests/integration/test_database_integration.py
import pytest
import asyncpg
from datetime import datetime, timedelta

from services.stock_service import StockService
from services.sentiment_service import SentimentService
from models.stock_models import StockData
from models.sentiment_models import SentimentData

class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_stock_data_crud_operations(self, test_db):
        """주식 데이터 CRUD 작업 통합 테스트"""
        stock_service = StockService(test_db, None)
        
        # 생성 테스트
        stock_data = StockData(
            symbol='AAPL',
            timestamp=datetime.utcnow(),
            open=150.00,
            high=155.00,
            low=149.00,
            close=154.50,
            volume=1000000
        )
        
        created_id = await stock_service.create_stock_data(stock_data)
        assert created_id is not None
        
        # 조회 테스트
        retrieved_data = await stock_service.get_stock_data_by_id(created_id)
        assert retrieved_data is not None
        assert retrieved_data.symbol == 'AAPL'
        assert retrieved_data.close == 154.50
        
        # 업데이트 테스트
        retrieved_data.volume = 2000000
        updated = await stock_service.update_stock_data(retrieved_data)
        assert updated is True
        
        # 삭제 테스트
        deleted = await stock_service.delete_stock_data(created_id)
        assert deleted is True
        
        # 삭제 확인
        deleted_data = await stock_service.get_stock_data_by_id(created_id)
        assert deleted_data is None
    
    @pytest.mark.asyncio
    async def test_sentiment_data_crud_operations(self, test_db):
        """감성 데이터 CRUD 작업 통합 테스트"""
        sentiment_service = SentimentService(test_db, None)
        
        # 생성 테스트
        sentiment_data = SentimentData(
            symbol='AAPL',
            timestamp=datetime.utcnow(),
            sentiment_score=0.65,
            confidence=0.85,
            platform='reddit'
        )
        
        created_id = await sentiment_service.create_sentiment_data(sentiment_data)
        assert created_id is not None
        
        # 조회 테스트
        retrieved_data = await sentiment_service.get_sentiment_data_by_id(created_id)
        assert retrieved_data is not None
        assert retrieved_data.symbol == 'AAPL'
        assert retrieved_data.sentiment_score == 0.65
        
        # 업데이트 테스트
        retrieved_data.confidence = 0.90
        updated = await sentiment_service.update_sentiment_data(retrieved_data)
        assert updated is True
        
        # 삭제 테스트
        deleted = await sentiment_service.delete_sentiment_data(created_id)
        assert deleted is True
    
    @pytest.mark.asyncio
    async def test_stock_sentiment_correlation_query(self, test_db):
        """주식-감성 상관관계 쿼리 통합 테스트"""
        # 테스트 데이터 삽입
        await self._insert_test_correlation_data(test_db)
        
        # 상관관계 분석 서비스
        from services.correlation_service import CorrelationAnalyzer
        analyzer = CorrelationAnalyzer(test_db)
        
        # 상관관계 분석
        correlation_result = await analyzer.analyze_stock_sentiment_correlation(
            'AAPL',
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        # 결과 검증
        assert correlation_result is not None
        assert 'correlation_coefficient' in correlation_result
        assert 'p_value' in correlation_result
        assert 'sample_size' in correlation_result
        assert correlation_result['sample_size'] > 0
    
    async def _insert_test_correlation_data(self, conn):
        """상관관계 테스트 데이터 삽입"""
        # 주식 데이터 삽입
        for i in range(30):
            await conn.execute("""
                INSERT INTO test_stock_data (symbol, timestamp, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 'AAPL', datetime.utcnow() - timedelta(days=i), 
                150 + i, 155 + i, 149 + i, 154 + i, 1000000 + i * 10000)
        
        # 감성 데이터 삽입
        for i in range(30):
            sentiment_score = 0.5 + (i % 10) * 0.1  # 변동하는 감성 점수
            await conn.execute("""
                INSERT INTO test_sentiment_data (symbol, timestamp, sentiment_score, confidence, platform)
                VALUES ($1, $2, $3, $4, $5)
            """, 'AAPL', datetime.utcnow() - timedelta(days=i), 
                sentiment_score, 0.8, 'reddit')
```

### 4.2 마이크로서비스 통합 테스트
```python
# tests/integration/test_microservices_integration.py
import pytest
import asyncio
from httpx import AsyncClient
import json

class TestMicroservicesIntegration:
    @pytest.mark.asyncio
    async def test_stock_sentiment_service_integration(self):
        """주식-감성 서비스 통합 테스트"""
        # API Gateway를 통한 통합 테스트
        async with AsyncClient(base_url="http://localhost:8080") as client:
            # 주식 데이터 조회
            stock_response = await client.get("/api/v1/stocks/AAPL/quote")
            assert stock_response.status_code == 200
            stock_data = stock_response.json()
            
            # 감성 데이터 조회
            sentiment_response = await client.get("/api/v1/sentiment/AAPL/current")
            assert sentiment_response.status_code == 200
            sentiment_data = sentiment_response.json()
            
            # 상관관계 분석
            correlation_response = await client.get("/api/v1/correlation/AAPL/sentiment")
            assert correlation_response.status_code == 200
            correlation_data = correlation_response.json()
            
            # 데이터 일관성 확인
            assert stock_data['symbol'] == sentiment_data['symbol'] == correlation_data['symbol']
            assert 'correlation_coefficient' in correlation_data
    
    @pytest.mark.asyncio
    async def test_service_communication_failure(self):
        """서비스 통신 실패 테스트"""
        # Stock Service 다운 시뮬레이션
        with patch('services.stock_service.StockService.get_stock_quote') as mock_stock:
            mock_stock.side_effect = Exception("Service unavailable")
            
            async with AsyncClient(base_url="http://localhost:8080") as client:
                response = await client.get("/api/v1/stocks/AAPL/quote")
                
                # 서비스 unavailable 응답 확인
                assert response.status_code == 503
                data = response.json()
                assert data['error']['code'] == 'SERVICE_UNAVAILABLE'
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """서킷 브레이커 패턴 테스트"""
        # 여러 실패 시뮬레이션
        with patch('services.stock_service.StockService.get_stock_quote') as mock_stock:
            mock_stock.side_effect = Exception("Service failure")
            
            async with AsyncClient(base_url="http://localhost:8080") as client:
                # 여러 요청 보내기
                responses = []
                for _ in range(10):
                    response = await client.get("/api/v1/stocks/AAPL/quote")
                    responses.append(response)
                
                # 서킷 브레이커 동작 확인
                failure_count = sum(1 for r in responses if r.status_code == 503)
                circuit_open_count = sum(1 for r in responses if r.status_code == 503 and 
                                     'circuit_breaker' in r.json().get('error', {}).get('code', ''))
                
                assert failure_count >= 5  # 일부 실패
                assert circuit_open_count > 0  # 서킷 브레이커 동작
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_services(self):
        """서비스 간 데이터 일관성 테스트"""
        async with AsyncClient(base_url="http://localhost:8080") as client:
            # 동시에 여러 서비스에 데이터 요청
            tasks = [
                client.get("/api/v1/stocks/AAPL/quote"),
                client.get("/api/v1/sentiment/AAPL/current"),
                client.get("/api/v1/stocks/AAPL/history?period=1d")
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 모든 요청 성공 확인
            for response in responses:
                if isinstance(response, Exception):
                    pytest.fail(f"Request failed: {response}")
                assert response.status_code == 200
            
            # 데이터 일관성 확인
            stock_data = responses[0].json()
            sentiment_data = responses[1].json()
            history_data = responses[2].json()
            
            # 심볼 일관성
            assert stock_data['symbol'] == sentiment_data['symbol'] == history_data['symbol']
            
            # 시간 일관성 (모든 타임스탬프가 합리적인 범위 내)
            stock_time = stock_data.get('timestamp')
            sentiment_time = sentiment_data.get('analysis_timestamp')
            
            if stock_time and sentiment_time:
                time_diff = abs(stock_time - sentiment_time)
                assert time_diff < 300  # 5분 이내 차이
```

## 5. E2E 테스트 프레임워크

### 5.1 Playwright E2E 테스트
```python
# tests/e2e/test_user_workflows.py
import pytest
from playwright.async_api import async_playwright, Page, Browser
import asyncio

class TestUserWorkflows:
    @pytest.mark.asyncio
    async def test_stock_search_and_analysis_workflow(self):
        """주식 검색 및 분석 워크플로우 테스트"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 1. 메인 페이지 접속
                await page.goto("http://localhost:3000")
                await page.wait_for_load_state('networkidle')
                
                # 2. 주식 검색
                search_input = page.locator('[data-testid="stock-search-input"]')
                await search_input.fill("Apple")
                await search_input.press("Enter")
                
                # 3. 검색 결과 확인
                search_results = page.locator('[data-testid="search-results"]')
                await search_results.wait_for(state='visible')
                
                # 4. AAPL 선택
                aapl_result = page.locator('[data-testid="result-AAPL"]')
                await aapl_result.click()
                
                # 5. 주식 차트 로딩 확인
                chart_container = page.locator('[data-testid="stock-chart"]')
                await chart_container.wait_for(state='visible')
                
                # 6. 기술적 지표 토글
                rsi_toggle = page.locator('[data-testid="rsi-toggle"]')
                await rsi_toggle.click()
                
                # 7. RSI 차트 확인
                rsi_chart = page.locator('[data-testid="rsi-chart"]')
                await rsi_chart.wait_for(state='visible')
                
                # 8. 시간 프레임 변경
                timeframe_1m = page.locator('[data-testid="timeframe-1m"]')
                await timeframe_1m.click()
                
                # 9. 데이터 업데이트 확인
                await page.wait_for_timeout(2000)  # 데이터 로딩 대기
                
                # 10. 감성 분석 탭으로 이동
                sentiment_tab = page.locator('[data-testid="sentiment-tab"]')
                await sentiment_tab.click()
                
                # 11. 감성 데이터 확인
                sentiment_chart = page.locator('[data-testid="sentiment-chart"]')
                await sentiment_chart.wait_for(state='visible')
                
                # 12. 스냅샷 찍기 (테스트 실패 시 디버깅용)
                await page.screenshot(path="test_results/stock_analysis_workflow.png")
                
            finally:
                await browser.close()
    
    @pytest.mark.asyncio
    async def test_watchlist_management_workflow(self):
        """왓치리스트 관리 워크플로우 테스트"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 1. 로그인
                await page.goto("http://localhost:3000/login")
                await page.fill('[data-testid="email-input"]', "test@example.com")
                await page.fill('[data-testid="password-input"]', "testpassword")
                await page.click('[data-testid="login-button"]')
                
                # 2. 대시보드 접속 확인
                await page.wait_for_url("**/dashboard")
                
                # 3. 왓치리스트 접속
                watchlist_link = page.locator('[data-testid="watchlist-link"]')
                await watchlist_link.click()
                
                # 4. 새 주식 추가
                add_stock_input = page.locator('[data-testid="add-stock-input"]')
                await add_stock_input.fill("MSFT")
                await add_stock_input.press("Enter")
                
                # 5. 추가 확인
                msft_item = page.locator('[data-testid="watchlist-MSFT"]')
                await msft_item.wait_for(state='visible')
                
                # 6. 주식 제거
                remove_button = page.locator('[data-testid="remove-MSFT"]')
                await remove_button.click()
                
                # 7. 제거 확인
                await msft_item.wait_for(state='hidden')
                
                # 8. 스냅샷
                await page.screenshot(path="test_results/watchlist_workflow.png")
                
            finally:
                await browser.close()
    
    @pytest.mark.asyncio
    async def test_multi_stock_comparison_workflow(self):
        """다중 주식 비교 워크플로우 테스트"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 1. 비교 페이지 접속
                await page.goto("http://localhost:3000/compare")
                await page.wait_for_load_state('networkidle')
                
                # 2. 여러 주식 입력
                stock_inputs = page.locator('[data-testid^="stock-input-"]')
                await stock_inputs.nth(0).fill("AAPL")
                await stock_inputs.nth(1).fill("MSFT")
                await stock_inputs.nth(2).fill("GOOGL")
                
                # 3. 비교 버튼 클릭
                compare_button = page.locator('[data-testid="compare-button"]')
                await compare_button.click()
                
                # 4. 비교 차트 로딩 확인
                comparison_chart = page.locator('[data-testid="comparison-chart"]')
                await comparison_chart.wait_for(state='visible')
                
                # 5. 성능 테이블 확인
                performance_table = page.locator('[data-testid="performance-table"]')
                await performance_table.wait_for(state='visible')
                
                # 6. 데이터 내용 검증
                aapl_row = page.locator('[data-testid="row-AAPL"]')
                msft_row = page.locator('[data-testid="row-MSFT"]')
                googl_row = page.locator('[data-testid="row-GOOGL"]')
                
                await aapl_row.wait_for(state='visible')
                await msft_row.wait_for(state='visible')
                await googl_row.wait_for(state='visible')
                
                # 7. 시간 프레임 변경 테스트
                timeframe_1y = page.locator('[data-testid="timeframe-1y"]')
                await timeframe_1y.click()
                
                # 8. 데이터 업데이트 대기
                await page.wait_for_timeout(3000)
                
                # 9. 스냅샷
                await page.screenshot(path="test_results/comparison_workflow.png")
                
            finally:
                await browser.close()
    
    @pytest.mark.asyncio
    async def test_responsive_design_workflow(self):
        """반응형 디자인 워크플로우 테스트"""
        async with async_playwright() as p:
            # 다양한 디바이스 크기 테스트
            devices = [
                {'viewport': {'width': 1920, 'height': 1080}, 'name': 'desktop'},
                {'viewport': {'width': 768, 'height': 1024}, 'name': 'tablet'},
                {'viewport': {'width': 375, 'height': 667}, 'name': 'mobile'}
            ]
            
            for device in devices:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    # 뷰포트 설정
                    await page.set_viewport_size(**device['viewport'])
                    
                    # 1. 메인 페이지 접속
                    await page.goto("http://localhost:3000")
                    await page.wait_for_load_state('networkidle')
                    
                    # 2. 주요 요소 접근성 확인
                    search_input = page.locator('[data-testid="stock-search-input"]')
                    await search_input.wait_for(state='visible')
                    
                    # 3. 모바일에서 메뉴 토글 확인
                    if device['name'] == 'mobile':
                        menu_toggle = page.locator('[data-testid="mobile-menu-toggle"]')
                        if await menu_toggle.is_visible():
                            await menu_toggle.click()
                            
                            mobile_menu = page.locator('[data-testid="mobile-menu"]')
                            await mobile_menu.wait_for(state='visible')
                    
                    # 4. 차트 반응성 확인
                    chart_container = page.locator('[data-testid="stock-chart"]')
                    await chart_container.wait_for(state='visible')
                    
                    # 5. 스냅샷
                    await page.screenshot(
                        path=f"test_results/responsive_{device['name']}.png",
                        full_page=True
                    )
                    
                finally:
                    await browser.close()
```

### 5.2 시각적 회귀 테스트
```python
# tests/e2e/test_visual_regression.py
import pytest
from playwright.async_api import async_playwright, Page
import os
import imagehash
from PIL import Image

class TestVisualRegression:
    @pytest.mark.asyncio
    async def test_chart_visual_consistency(self):
        """차트 시각적 일관성 테스트"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 1. 특정 주식 차트 페이지 접속
                await page.goto("http://localhost:3000/stocks/AAPL")
                await page.wait_for_load_state('networkidle')
                
                # 2. 차트 영역 스크린샷
                chart_element = page.locator('[data-testid="stock-chart"]')
                await chart_element.wait_for(state='visible')
                
                screenshot_path = "test_results/current_chart.png"
                await chart_element.screenshot(path=screenshot_path)
                
                # 3. 기준 이미지와 비교
                baseline_path = "tests/baselines/chart_baseline.png"
                
                if os.path.exists(baseline_path):
                    # 이미지 해시 비교
                    current_hash = self._calculate_image_hash(screenshot_path)
                    baseline_hash = self._calculate_image_hash(baseline_path)
                    
                    # 해시 차이 확인 (유사도 측정)
                    hash_difference = abs(current_hash - baseline_hash)
                    assert hash_difference < 5, f"Visual regression detected: hash difference {hash_difference}"
                else:
                    # 기준 이미지가 없으면 생성
                    os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
                    await chart_element.screenshot(path=baseline_path)
                    
            finally:
                await browser.close()
    
    def _calculate_image_hash(self, image_path: str) -> imagehash.ImageHash:
        """이미지 해시 계산"""
        image = Image.open(image_path)
        return imagehash.average_hash(image)
    
    @pytest.mark.asyncio
    async def test_ui_component_consistency(self):
        """UI 컴포넌트 시각적 일관성 테스트"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 1. 다양한 페이지에서 UI 컴포넌트 스크린샷
                pages_to_test = [
                    "/stocks/AAPL",
                    "/sentiment/AAPL",
                    "/compare",
                    "/dashboard"
                ]
                
                for page_url in pages_to_test:
                    await page.goto(f"http://localhost:3000{page_url}")
                    await page.wait_for_load_state('networkidle')
                    
                    # 헤더 컴포넌트 스크린샷
                    header_element = page.locator('[data-testid="header"]')
                    if await header_element.is_visible():
                        screenshot_path = f"test_results/header_{page_url.replace('/', '_')}.png"
                        await header_element.screenshot(path=screenshot_path)
                        
                        # 기준 이미지와 비교
                        baseline_path = f"tests/baselines/header_{page_url.replace('/', '_')}.png"
                        if os.path.exists(baseline_path):
                            await self._compare_images(screenshot_path, baseline_path)
                
            finally:
                await browser.close()
    
    async def _compare_images(self, current_path: str, baseline_path: str):
        """이미지 비교"""
        current_image = Image.open(current_path)
        baseline_image = Image.open(baseline_path)
        
        # 이미지 크기 확인
        assert current_image.size == baseline_image.size, "Image size mismatch"
        
        # 픽셀 단위 비교
        current_hash = imagehash.average_hash(current_image)
        baseline_hash = imagehash.average_hash(baseline_image)
        
        # 해시 차이 계산
        hash_difference = current_hash - baseline_hash
        difference_magnitude = abs(hash_difference)
        
        # 차이가 너무 크면 실패
        assert difference_magnitude < 10, f"Visual regression detected: {difference_magnitude}"
```

## 6. 성능 테스트 프레임워크

### 6.1 부하 테스트
```python
# tests/performance/test_load_testing.py
import pytest
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict
import concurrent.futures

class TestLoadTesting:
    @pytest.mark.asyncio
    async def test_api_load_testing(self):
        """API 부하 테스트"""
        base_url = "http://localhost:8080"
        endpoint = "/api/v1/stocks/AAPL/quote"
        
        # 부하 테스트 파라미터
        concurrent_users = 50
        requests_per_user = 20
        total_requests = concurrent_users * requests_per_user
        
        # 결과 수집
        response_times = []
        status_codes = {}
        errors = []
        
        async def make_request(session, user_id):
            """단일 사용자 요청"""
            user_response_times = []
            user_errors = []
            
            for request_id in range(requests_per_user):
                start_time = time.time()
                
                try:
                    async with session.get(f"{base_url}{endpoint}") as response:
                        await response.text()
                        end_time = time.time()
                        
                        response_time = end_time - start_time
                        user_response_times.append(response_time)
                        
                        # 상태 코드 기록
                        status_code = response.status
                        status_codes[status_code] = status_codes.get(status_code, 0) + 1
                        
                except Exception as e:
                    end_time = time.time()
                    user_errors.append({
                        'error': str(e),
                        'response_time': end_time - start_time,
                        'user_id': user_id,
                        'request_id': request_id
                    })
                
                # 요청 간 간격
                await asyncio.sleep(0.1)
            
            return user_response_times, user_errors
        
        # 동시 요청 실행
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                make_request(session, user_id) 
                for user_id in range(concurrent_users)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 결과 집계
        for user_response_times, user_errors in results:
            response_times.extend(user_response_times)
            errors.extend(user_errors)
        
        # 성능 메트릭 계산
        avg_response_time = statistics.mean(response_times) if response_times else 0
        median_response_time = statistics.median(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
        
        success_rate = (status_codes.get(200, 0) / total_requests) * 100
        error_rate = (len(errors) / total_requests) * 100
        requests_per_second = total_requests / total_time if total_time > 0 else 0
        
        # 성능 기준 검증
        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}s"
        assert p95_response_time < 2.0, f"95th percentile response time too high: {p95_response_time}s"
        assert success_rate > 99.0, f"Success rate too low: {success_rate}%"
        assert requests_per_second > 100, f"Requests per second too low: {requests_per_second}"
        
        # 결과 출력
        print(f"Load Test Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Concurrent Users: {concurrent_users}")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Requests/Second: {requests_per_second:.2f}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Error Rate: {error_rate:.2f}%")
        print(f"  Avg Response Time: {avg_response_time:.3f}s")
        print(f"  Median Response Time: {median_response_time:.3f}s")
        print(f"  95th Percentile: {p95_response_time:.3f}s")
        print(f"  99th Percentile: {p99_response_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_database_load_testing(self):
        """데이터베이스 부하 테스트"""
        from services.stock_service import StockService
        from database.connection_pool import db_pool
        
        await db_pool.initialize()
        stock_service = StockService(db_pool, None)
        
        # 동시 데이터베이스 작업
        concurrent_operations = 20
        operations_per_connection = 50
        
        async def perform_db_operations(connection_id):
            """데이터베이스 작업 수행"""
            operation_times = []
            
            for operation_id in range(operations_per_connection):
                start_time = time.time()
                
                try:
                    # 삽입 작업
                    stock_data = {
                        'symbol': f'TEST{connection_id}{operation_id}',
                        'timestamp': time.time(),
                        'open': 100.0 + operation_id,
                        'high': 105.0 + operation_id,
                        'low': 95.0 + operation_id,
                        'close': 102.0 + operation_id,
                        'volume': 1000000
                    }
                    
                    await stock_service.create_stock_data(stock_data)
                    
                    # 조회 작업
                    await stock_service.get_stock_data_by_symbol(f'TEST{connection_id}{operation_id}')
                    
                    end_time = time.time()
                    operation_times.append(end_time - start_time)
                    
                except Exception as e:
                    print(f"DB operation error: {e}")
                
                # 작업 간 간격
                await asyncio.sleep(0.01)
            
            return operation_times
        
        # 동시 작업 실행
        start_time = time.time()
        
        tasks = [
            perform_db_operations(connection_id)
            for connection_id in range(concurrent_operations)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 결과 집계
        all_operation_times = []
        for operation_times in results:
            if isinstance(operation_times, list):
                all_operation_times.extend(operation_times)
        
        if all_operation_times:
            avg_operation_time = statistics.mean(all_operation_times)
            total_operations = len(all_operation_times)
            operations_per_second = total_operations / total_time
            
            # 성능 기준 검증
            assert avg_operation_time < 0.1, f"DB operation time too high: {avg_operation_time}s"
            assert operations_per_second > 100, f"DB operations per second too low: {operations_per_second}"
            
            print(f"Database Load Test Results:")
            print(f"  Total Operations: {total_operations}")
            print(f"  Concurrent Connections: {concurrent_operations}")
            print(f"  Operations/Second: {operations_per_second:.2f}")
            print(f"  Avg Operation Time: {avg_operation_time:.3f}s")
```

### 6.2 스트레스 테스트
```python
# tests/performance/test_stress_testing.py
import pytest
import asyncio
import aiohttp
import time
import statistics
from typing import List

class TestStressTesting:
    @pytest.mark.asyncio
    async def test_api_stress_testing(self):
        """API 스트레스 테스트"""
        base_url = "http://localhost:8080"
        endpoint = "/api/v1/stocks/AAPL/quote"
        
        # 스트레스 테스트 파라미터
        max_concurrent_users = 200
        ramp_up_time = 30  # 30초 동안 점진적 증가
        test_duration = 60  # 60초 동안 유지
        
        # 결과 수집
        response_times = []
        status_codes = {}
        errors = []
        user_counts = []
        
        async def make_request(session, user_id, start_delay):
            """요청 수행 (지연 시간 포함)"""
            await asyncio.sleep(start_delay)
            
            end_time = time.time() + test_duration
            
            while time.time() < end_time:
                request_start = time.time()
                
                try:
                    async with session.get(f"{base_url}{endpoint}") as response:
                        await response.text()
                        request_end = time.time()
                        
                        response_time = request_end - request_start
                        response_times.append(response_time)
                        
                        status_code = response.status
                        status_codes[status_code] = status_codes.get(status_code, 0) + 1
                        
                except Exception as e:
                    errors.append({
                        'error': str(e),
                        'user_id': user_id,
                        'timestamp': time.time()
                    })
                
                # 요청 간 간격
                await asyncio.sleep(0.1)
        
        # 사용자 수 점진적 증가
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for user_id in range(max_concurrent_users):
                # 지연 시간 계산 (점진적 증가)
                start_delay = (user_id / max_concurrent_users) * ramp_up_time
                
                task = make_request(session, user_id, start_delay)
                tasks.append(task)
            
            # 모든 작업 동시 실행
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 성능 메트릭 계산
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
            
            success_rate = (status_codes.get(200, 0) / len(response_times)) * 100
            error_rate = (len(errors) / len(response_times)) * 100
            
            # 스트레스 테스트 기준 검증
            assert avg_response_time < 2.0, f"Average response time under stress: {avg_response_time}s"
            assert p95_response_time < 5.0, f"95th percentile response time under stress: {p95_response_time}s"
            assert success_rate > 95.0, f"Success rate under stress: {success_rate}%"
            
            print(f"Stress Test Results:")
            print(f"  Max Concurrent Users: {max_concurrent_users}")
            print(f"  Ramp-up Time: {ramp_up_time}s")
            print(f"  Test Duration: {test_duration}s")
            print(f"  Total Requests: {len(response_times)}")
            print(f"  Success Rate: {success_rate:.2f}%")
            print(f"  Error Rate: {error_rate:.2f}%")
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            print(f"  Median Response Time: {median_response_time:.3f}s")
            print(f"  95th Percentile: {p95_response_time:.3f}s")
            print(f"  99th Percentile: {p99_response_time:.3f}s")
```

## 7. 보안 테스트 프레임워크

### 7.1 보안 취약점 테스트
```python
# tests/security/test_security_vulnerabilities.py
import pytest
import aiohttp
import asyncio
import json
from unittest.mock import patch

class TestSecurityVulnerabilities:
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self):
        """SQL 인젝션 보호 테스트"""
        base_url = "http://localhost:8080"
        
        # SQL 인젝션 시도
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT username, password FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        async with aiohttp.ClientSession() as session:
            for malicious_input in malicious_inputs:
                # 검색 엔드포인트에 SQL 인젝션 시도
                search_url = f"{base_url}/api/v1/stocks/search"
                params = {'q': malicious_input}
                
                async with session.get(search_url, params=params) as response:
                    # SQL 인젝션이 성공하면 안 됨
                    assert response.status_code in [200, 400, 422]
                    
                    if response.status_code == 200:
                        data = await response.json()
                        # 에러 메시지가 노출되지 않아야 함
                        assert 'error' not in data or 'sql' not in data.get('error', '').lower()
    
    @pytest.mark.asyncio
    async def test_xss_protection(self):
        """XSS 보호 테스트"""
        base_url = "http://localhost:8080"
        
        # XSS 시도
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>"
        ]
        
        async with aiohttp.ClientSession() as session:
            for xss_payload in xss_payloads:
                # 검색 엔드포인트에 XSS 시도
                search_url = f"{base_url}/api/v1/stocks/search"
                params = {'q': xss_payload}
                
                async with session.get(search_url, params=params) as response:
                    if response.status_code == 200:
                        # 응답에 스크립트가 포함되지 않아야 함
                        response_text = await response.text()
                        assert '<script>' not in response_text
                        assert 'javascript:' not in response_text
                        assert 'onerror=' not in response_text
                        assert 'onload=' not in response_text
    
    @pytest.mark.asyncio
    async def test_authentication_bypass_attempts(self):
        """인증 우회 시도 테스트"""
        base_url = "http://localhost:8080"
        
        # 인증 우회 시도
        bypass_attempts = [
            # 잘못된 토큰
            {"Authorization": "Bearer invalid_token"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic invalid_credentials"},
            
            # 헤더 조작
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Real-IP": "127.0.0.1"},
            {"X-Originating-IP": "127.0.0.1"},
            
            # API 키 조작
            {"X-API-Key": "invalid_key"},
            {"X-API-Key": ""},
            {"X-API-Key": "admin"}
        ]
        
        protected_endpoints = [
            "/api/v1/users/profile",
            "/api/v1/sentiment/AAPL/current",
            "/api/v1/analytics/dashboard"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in protected_endpoints:
                for headers in bypass_attempts:
                    async with session.get(f"{base_url}{endpoint}", headers=headers) as response:
                        # 인증 실패해야 함
                        assert response.status_code in [401, 403, 422]
    
    @pytest.mark.asyncio
    async def test_rate_limiting_effectiveness(self):
        """속도 제한 효과성 테스트"""
        base_url = "http://localhost:8080"
        endpoint = "/api/v1/stocks/AAPL/quote"
        
        # 속도 제한 초과 요청
        async with aiohttp.ClientSession() as session:
            responses = []
            
            # 100개 요청 빠르게 보내기
            for _ in range(100):
                async with session.get(f"{base_url}{endpoint}") as response:
                    responses.append(response)
                
                # 간격 없이 빠르게 요청
                await asyncio.sleep(0.01)
            
            # 속도 제한 동작 확인
            rate_limited_responses = [r for r in responses if r.status_code == 429]
            assert len(rate_limited_responses) > 0, "Rate limiting not working"
            
            # 속도 제한 헤더 확인
            rate_limit_response = rate_limited_responses[0]
            assert 'X-RateLimit-Limit' in rate_limit_response.headers
            assert 'X-RateLimit-Remaining' in rate_limit_response.headers
            assert 'X-RateLimit-Reset' in rate_limit_response.headers
    
    @pytest.mark.asyncio
    async def test_sensitive_data_exposure(self):
        """민감 데이터 노출 테스트"""
        base_url = "http://localhost:8080"
        
        # 에러 상황에서 민감 정보 노출 확인
        error_endpoints = [
            "/api/v1/stocks/INVALID/quote",
            "/api/v1/users/999999",  # 존재하지 않는 사용자 ID
            "/api/v1/nonexistent/endpoint"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in error_endpoints:
                async with session.get(f"{base_url}{endpoint}") as response:
                    response_text = await response.text()
                    
                    # 민감 정보가 노출되지 않아야 함
                    sensitive_patterns = [
                        'password', 'secret', 'key', 'token',
                        'database', 'connection', 'internal',
                        'stack trace', 'file path', 'sql'
                    ]
                    
                    for pattern in sensitive_patterns:
                        assert pattern not in response_text.lower(), \
                            f"Sensitive information exposed: {pattern}"
    
    @pytest.mark.asyncio
    async def test_cors_configuration(self):
        """CORS 설정 테스트"""
        base_url = "http://localhost:8080"
        
        # 허용되지 않은 오리진에서의 요청
        malicious_origins = [
            "http://evil.com",
            "https://malicious-site.net",
            "http://localhost:8081"
        ]
        
        async with aiohttp.ClientSession() as session:
            for origin in malicious_origins:
                headers = {"Origin": origin}
                
                async with session.get(f"{base_url}/api/v1/stocks/AAPL/quote", headers=headers) as response:
                    # CORS 헤더 확인
                    if 'Access-Control-Allow-Origin' in response.headers:
                        allowed_origin = response.headers['Access-Control-Allow-Origin']
                        # 와일드카드가 아니면 특정 오리진만 허용되어야 함
                        if allowed_origin != '*':
                            assert allowed_origin not in malicious_origins, \
                                f"Malicious origin allowed: {allowed_origin}"
```

## 8. 테스트 자동화 및 CI/CD 통합

### 8.1 GitHub Actions 워크플로우
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
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
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
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=app --cov-report=xml --cov-report=html
    
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
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
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
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Start services
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 30
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --cov=app --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: integration
        name: codecov-umbrella

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd frontend
        npm install
    
    - name: Install Playwright
      run: |
        cd frontend
        npx playwright install
    
    - name: Start application
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 60
    
    - name: Run E2E tests
      run: |
        cd frontend
        npx playwright test
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: playwright-report
        path: frontend/playwright-report/

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'main'  # 메인 브랜치에서만 실행
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Start services
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 60
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v --benchmark-only
    
    - name: Upload performance results
      uses: actions/upload-artifact@v3
      with:
        name: performance-results
        path: test_results/

  security-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run security tests
      run: |
        pytest tests/security/ -v
    
    - name: Run security scan
      run: |
        bandit -r app/ -f json -o security-report.json
    
    - name: Upload security results
      uses: actions/upload-artifact@v3
      with:
        name: security-results
        path: security-report.json
```

### 8.2 테스트 보고서 생성
```python
# tests/utils/report_generator.py
import json
import html
from datetime import datetime
from typing import Dict, List, Any
import os

class TestReportGenerator:
    def __init__(self):
        self.report_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {},
            'unit_tests': {},
            'integration_tests': {},
            'e2e_tests': {},
            'performance_tests': {},
            'security_tests': {}
        }
    
    def add_unit_test_results(self, results: Dict[str, Any]):
        """단위 테스트 결과 추가"""
        self.report_data['unit_tests'] = results
    
    def add_integration_test_results(self, results: Dict[str, Any]):
        """통합 테스트 결과 추가"""
        self.report_data['integration_tests'] = results
    
    def add_e2e_test_results(self, results: Dict[str, Any]):
        """E2E 테스트 결과 추가"""
        self.report_data['e2e_tests'] = results
    
    def add_performance_test_results(self, results: Dict[str, Any]):
        """성능 테스트 결과 추가"""
        self.report_data['performance_tests'] = results
    
    def add_security_test_results(self, results: Dict[str, Any]):
        """보안 테스트 결과 추가"""
        self.report_data['security_tests'] = results
    
    def generate_html_report(self) -> str:
        """HTML 테스트 보고서 생성"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .success { color: green; }
                .failure { color: red; }
                .warning { color: orange; }
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .chart { margin: 20px 0; }
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <div class="header">
                <h1>Test Report</h1>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="section">
                <h2>Summary</h2>
                {summary_content}
            </div>
            
            <div class="section">
                <h2>Unit Tests</h2>
                {unit_test_content}
            </div>
            
            <div class="section">
                <h2>Integration Tests</h2>
                {integration_test_content}
            </div>
            
            <div class="section">
                <h2>E2E Tests</h2>
                {e2e_test_content}
            </div>
            
            <div class="section">
                <h2>Performance Tests</h2>
                {performance_test_content}
            </div>
            
            <div class="section">
                <h2>Security Tests</h2>
                {security_test_content}
            </div>
        </body>
        </html>
        """
        
        # 각 섹션 내용 생성
        summary_content = self._generate_summary_content()
        unit_test_content = self._generate_test_section_content('unit_tests', 'Unit Tests')
        integration_test_content = self._generate_test_section_content('integration_tests', 'Integration Tests')
        e2e_test_content = self._generate_test_section_content('e2e_tests', 'E2E Tests')
        performance_test_content = self._generate_performance_section_content()
        security_test_content = self._generate_security_section_content()
        
        return html_template.format(
            timestamp=self.report_data['timestamp'],
            summary_content=summary_content,
            unit_test_content=unit_test_content,
            integration_test_content=integration_test_content,
            e2e_test_content=e2e_test_content,
            performance_test_content=performance_test_content,
            security_test_content=security_test_content
        )
    
    def _generate_summary_content(self) -> str:
        """요약 섹션 내용 생성"""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for test_type in ['unit_tests', 'integration_tests', 'e2e_tests']:
            test_data = self.report_data.get(test_type, {})
            total_tests += test_data.get('total', 0)
            total_passed += test_data.get('passed', 0)
            total_failed += test_data.get('failed', 0)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        return f"""
        <div class="summary">
            <p><strong>Total Tests:</strong> {total_tests}</p>
            <p><strong>Passed:</strong> <span class="success">{total_passed}</span></p>
            <p><strong>Failed:</strong> <span class="failure">{total_failed}</span></p>
            <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
        </div>
        """
    
    def _generate_test_section_content(self, test_type: str, title: str) -> str:
        """테스트 섹션 내용 생성"""
        test_data = self.report_data.get(test_type, {})
        
        if not test_data:
            return f"<p>No {title} results available.</p>"
        
        total = test_data.get('total', 0)
        passed = test_data.get('passed', 0)
        failed = test_data.get('failed', 0)
        skipped = test_data.get('skipped', 0)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return f"""
        <div class="test-results">
            <p><strong>Total:</strong> {total}</p>
            <p><strong>Passed:</strong> <span class="success">{passed}</span></p>
            <p><strong>Failed:</strong> <span class="failure">{failed}</span></p>
            <p><strong>Skipped:</strong> <span class="warning">{skipped}</span></p>
            <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
            
            {self._generate_test_details_table(test_data)}
        </div>
        """
    
    def _generate_test_details_table(self, test_data: Dict[str, Any]) -> str:
        """테스트 상세 테이블 생성"""
        test_results = test_data.get('test_results', [])
        
        if not test_results:
            return ""
        
        table_rows = ""
        for test in test_results:
            status_class = "success" if test.get('passed') else "failure"
            table_rows += f"""
            <tr>
                <td>{test.get('name', '')}</td>
                <td>{test.get('duration', 0):.3f}s</td>
                <td class="{status_class}">{test.get('status', '')}</td>
                <td>{test.get('message', '')}</td>
            </tr>
            """
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Message</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """
    
    def _generate_performance_section_content(self) -> str:
        """성능 테스트 섹션 내용 생성"""
        perf_data = self.report_data.get('performance_tests', {})
        
        if not perf_data:
            return "<p>No performance test results available.</p>"
        
        return f"""
        <div class="performance-results">
            <h3>Load Test Results</h3>
            <p><strong>Average Response Time:</strong> {perf_data.get('avg_response_time', 0):.3f}s</p>
            <p><strong>95th Percentile:</strong> {perf_data.get('p95_response_time', 0):.3f}s</p>
            <p><strong>Requests/Second:</strong> {perf_data.get('requests_per_second', 0):.2f}</p>
            <p><strong>Success Rate:</strong> {perf_data.get('success_rate', 0):.1f}%</p>
            
            <div class="chart">
                <canvas id="performanceChart"></canvas>
            </div>
        </div>
        
        <script>
            // 성능 차트 생성
            const ctx = document.getElementById('performanceChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(perf_data.get('time_labels', []))},
                    datasets: [{{
                        label: 'Response Time',
                        data: {json.dumps(perf_data.get('response_times', []))},
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Response Time (s)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
    
    def _generate_security_section_content(self) -> str:
        """보안 테스트 섹션 내용 생성"""
        security_data = self.report_data.get('security_tests', {})
        
        if not security_data:
            return "<p>No security test results available.</p>"
        
        vulnerabilities = security_data.get('vulnerabilities', [])
        
        if not vulnerabilities:
            return '<p class="success">No security vulnerabilities found.</p>'
        
        vuln_rows = ""
        for vuln in vulnerabilities:
            severity_class = {
                'high': 'failure',
                'medium': 'warning',
                'low': 'warning'
            }.get(vuln.get('severity', 'low'), 'warning')
            
            vuln_rows += f"""
            <tr>
                <td>{vuln.get('type', '')}</td>
                <td>{vuln.get('description', '')}</td>
                <td class="{severity_class}">{vuln.get('severity', '')}</td>
                <td>{vuln.get('recommendation', '')}</td>
            </tr>
            """
        
        return f"""
        <div class="security-results">
            <p><strong>Vulnerabilities Found:</strong> {len(vulnerabilities)}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Description</th>
                        <th>Severity</th>
                        <th>Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    {vuln_rows}
                </tbody>
            </table>
        </div>
        """
    
    def save_report(self, output_path: str = "test_report.html"):
        """보고서 저장"""
        html_content = self.generate_html_report()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Test report saved to: {output_path}")
```

## 9. 결론

본 테스트 프레임워크 구축 계획은 단위 테스트, 통합 테스트, E2E 테스트, 성능 테스트, 보안 테스트 등 다양한 레벨의 포괄적인 테스트 전략을 제시합니다.

주요 특징:
1. **테스트 피라미드**: 70% 단위 테스트, 20% 통합 테스트, 10% E2E 테스트
2. **자동화된 CI/CD**: GitHub Actions를 통한 자동화된 테스트 파이프라인
3. **다양한 테스트 도구**: pytest, Playwright, 성능 테스트 도구
4. **모의 객체**: 외부 API 의존성을 제거한 격리된 테스트
5. **보안 테스트**: SQL 인젝션, XSS, 인증 우회 등 보안 취약점 테스트
6. **성능 테스트**: 부하 테스트, 스트레스 테스트를 통한 성능 검증
7. **테스트 보고서**: 자동화된 HTML 보고서 생성 및 시각화
8. **커버리지 측정**: 코드 커버리지 자동 측정 및 보고

이 테스트 프레임워크를 통해 애플리케이션의 품질을 체계적으로 보장하고, 개발 과정에서의 버그를 조기에 발견하며, 안정적인 소프트웨어 배포를 가능하게 할 수 있습니다.