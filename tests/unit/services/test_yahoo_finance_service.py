"""
YahooFinanceService 단위 테스트

Yahoo Finance 서비스의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from dataclasses import asdict

from backend.services.yahoo_finance_service import (
    YahooFinanceService,
    StockData,
    HistoricalData
)


class TestStockData:
    """StockData 모델 테스트 클래스"""
    
    def test_stock_data_creation(self):
        """StockData 생성 테스트"""
        stock_data = StockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            current_price=150.25,
            previous_close=147.75,
            open_price=148.50,
            day_high=151.00,
            day_low=147.75,
            volume=1000000,
            market_cap=3000000000,
            exchange="NASDAQ",
            currency="USD",
            short_name="Apple",
            long_name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            website="https://www.apple.com"
        )
        
        assert stock_data.symbol == "AAPL"
        assert stock_data.company_name == "Apple Inc."
        assert stock_data.current_price == 150.25
        assert stock_data.previous_close == 147.75
        assert stock_data.open_price == 148.50
        assert stock_data.day_high == 151.00
        assert stock_data.day_low == 147.75
        assert stock_data.volume == 1000000
        assert stock_data.market_cap == 3000000000
        assert stock_data.exchange == "NASDAQ"
        assert stock_data.currency == "USD"
        assert stock_data.short_name == "Apple"
        assert stock_data.long_name == "Apple Inc."
        assert stock_data.sector == "Technology"
        assert stock_data.industry == "Consumer Electronics"
        assert stock_data.website == "https://www.apple.com"
        assert stock_data.price_change == 2.5  # 자동 계산
        assert abs(stock_data.price_change_percent - 1.69) < 0.01  # 자동 계산 (부동소수점 오차 허용)
    
    def test_stock_data_post_init(self):
        """StockData __post_init__ 테스트"""
        stock_data = StockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            current_price=150.25,
            previous_close=147.75,
            open_price=148.50,
            day_high=151.00,
            day_low=147.75,
            volume=1000000
        )
        
        assert stock_data.price_change == 2.5  # 150.25 - 147.75
        assert abs(stock_data.price_change_percent - 1.69) < 0.01  # (2.5 / 147.75) * 100 (부동소수점 오차 허용)
        assert stock_data.timestamp is not None  # 자동 설정


class TestHistoricalData:
    """HistoricalData 모델 테스트 클래스"""
    
    def test_historical_data_creation(self):
        """HistoricalData 생성 테스트"""
        historical_data = HistoricalData(
            symbol="AAPL",
            date="2023-01-01",
            open=148.50,
            high=151.00,
            low=147.75,
            close=150.25,
            volume=1000000,
            adj_close=150.10
        )
        
        assert historical_data.symbol == "AAPL"
        assert historical_data.date == "2023-01-01"
        assert historical_data.open == 148.50
        assert historical_data.high == 151.00
        assert historical_data.low == 147.75
        assert historical_data.close == 150.25
        assert historical_data.volume == 1000000
        assert historical_data.adj_close == 150.10


class TestYahooFinanceService:
    """YahooFinanceService 테스트 클래스"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """모의 Redis 클라이언트"""
        client = AsyncMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.setex.return_value = True
        return client
    
    @pytest.fixture
    def mock_response(self):
        """모의 HTTP 응답"""
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": 150.25,
                        "previousClose": 147.75,
                        "regularMarketOpen": 148.50,
                        "regularMarketDayHigh": 151.00,
                        "regularMarketDayLow": 147.75,
                        "regularMarketVolume": 1000000,
                        "marketCap": 3000000000,
                        "exchangeName": "NASDAQ",
                        "currency": "USD",
                        "shortName": "Apple",
                        "longName": "Apple Inc.",
                        "regularMarketTime": time.time()
                    }
                }]
            }
        })
        return response
    
    @pytest.fixture
    def mock_session(self):
        """모의 HTTP 세션"""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def yahoo_finance_service(self, mock_redis_client, mock_session):
        """YahooFinanceService 인스턴스"""
        service = YahooFinanceService()
        service.redis_client = mock_redis_client
        # 세션 초기화
        service.session = mock_session
        return service
    
    @pytest.mark.asyncio
    async def test_get_stock_data_success(self, yahoo_finance_service, mock_response):
        """주식 데이터 조회 성공 테스트"""
        # 직접 _fetch_stock_data 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_stock_data') as mock_fetch:
            mock_fetch.return_value = StockData(
                symbol="AAPL",
                company_name="Apple Inc.",
                current_price=150.25,
                previous_close=147.75,
                open_price=148.50,
                day_high=151.00,
                day_low=147.75,
                volume=1000000,
                market_cap=3000000000,
                exchange="NASDAQ",
                currency="USD",
                short_name="Apple",
                long_name="Apple Inc."
            )
            
            # 테스트 실행
            stock_data = await yahoo_finance_service.get_stock_data("AAPL")
            
            # 결과 검증
            assert stock_data is not None
            assert stock_data.symbol == "AAPL"
            assert stock_data.current_price == 150.25
            assert stock_data.previous_close == 147.75
            assert stock_data.open_price == 148.50
            assert stock_data.day_high == 151.00
            assert stock_data.day_low == 147.75
            assert stock_data.volume == 1000000
            assert stock_data.market_cap == 3000000000
            assert stock_data.exchange == "NASDAQ"
            assert stock_data.currency == "USD"
            assert stock_data.short_name == "Apple"
            assert stock_data.long_name == "Apple Inc."
    
    @pytest.mark.asyncio
    async def test_get_stock_data_cache_hit(self, yahoo_finance_service, mock_redis_client):
        """캐시 히트 주식 데이터 조회 테스트"""
        # 설정
        cached_data = asdict(StockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            current_price=150.25,
            previous_close=147.75,
            open_price=148.50,
            day_high=151.00,
            day_low=147.75,
            volume=1000000
        ))
        mock_redis_client.get.return_value = json.dumps(cached_data)
        
        # 테스트 실행
        stock_data = await yahoo_finance_service.get_stock_data("AAPL")
        
        # 결과 검증
        assert stock_data is not None
        assert stock_data.symbol == "AAPL"
        assert stock_data.current_price == 150.25
    
    @pytest.mark.asyncio
    async def test_get_stock_data_rate_limit(self, yahoo_finance_service):
        """속도 제한 주식 데이터 조회 테스트"""
        # 설정
        yahoo_finance_service.request_count["minute"] = 60  # 속도 제한 도달
        
        # 테스트 실행
        result = await yahoo_finance_service.get_stock_data("AAPL")
        
        # 결과 검증
        assert result is None  # 속도 제한으로 None 반환
    
    @pytest.mark.asyncio
    async def test_get_stock_data_network_error(self, yahoo_finance_service, mock_session):
        """네트워크 오류 주식 데이터 조회 테스트"""
        # 직접 _fetch_stock_data 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_stock_data') as mock_fetch:
            mock_fetch.return_value = None  # 오류 발생 시 None 반환
            
            # 테스트 실행
            result = await yahoo_finance_service.get_stock_data("AAPL")
            
            # 결과 검증
            assert result is None  # 오류 발생 시 None 반환
    
    @pytest.mark.asyncio
    async def test_get_multiple_stocks_success(self, yahoo_finance_service, mock_session):
        """다중 주식 데이터 조회 성공 테스트"""
        # 모의 응답 설정
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": 150.25,
                        "previousClose": 147.75,
                        "regularMarketOpen": 148.50,
                        "regularMarketDayHigh": 151.00,
                        "regularMarketDayLow": 147.75,
                        "regularMarketVolume": 1000000,
                        "marketCap": 3000000000,
                        "exchangeName": "NASDAQ",
                        "currency": "USD",
                        "shortName": "Apple",
                        "longName": "Apple Inc.",
                        "regularMarketTime": time.time()
                    }
                }]
            }
        })
        
        # 직접 _fetch_stock_data 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_stock_data') as mock_fetch:
            mock_fetch.return_value = StockData(
                symbol="AAPL",
                company_name="Apple Inc.",
                current_price=150.25,
                previous_close=147.75,
                open_price=148.50,
                day_high=151.00,
                day_low=147.75,
                volume=1000000,
                market_cap=3000000000,
                exchange="NASDAQ",
                currency="USD",
                short_name="Apple",
                long_name="Apple Inc."
            )
            
            # 테스트 실행
            stock_data_dict = await yahoo_finance_service.get_multiple_stocks(["AAPL", "GOOGL"])
            
            # 결과 검증
            assert len(stock_data_dict) == 2
            assert "AAPL" in stock_data_dict
            assert "GOOGL" in stock_data_dict
    
    @pytest.mark.asyncio
    async def test_get_multiple_stocks_empty_list(self, yahoo_finance_service):
        """빈 목록 다중 주식 데이터 조회 테스트"""
        # 테스트 실행
        stock_data_dict = await yahoo_finance_service.get_multiple_stocks([])
        
        # 결과 검증
        assert stock_data_dict == {}
    
    @pytest.mark.asyncio
    async def test_get_historical_data_success(self, yahoo_finance_service, mock_session):
        """과거 데이터 조회 성공 테스트"""
        # 설정
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "chart": {
                "result": [{
                    "timestamp": [1640995200, 1641081600],
                    "indicators": {
                        "quote": [{
                            "open": [148.50, 149.00],
                            "high": [151.00, 151.50],
                            "low": [147.75, 148.25],
                            "close": [150.25, 150.75],
                            "volume": [1000000, 1100000]
                        }]
                    }
                }]
            }
        })
        
        # 직접 _fetch_historical_data 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_historical_data') as mock_fetch:
            mock_fetch.return_value = [
                HistoricalData(
                    symbol="AAPL",
                    date="2023-01-01",
                    open=148.50,
                    high=151.00,
                    low=147.75,
                    close=150.25,
                    volume=1000000
                ),
                HistoricalData(
                    symbol="AAPL",
                    date="2023-01-02",
                    open=149.00,
                    high=151.50,
                    low=148.25,
                    close=150.75,
                    volume=1100000
                )
            ]
            
            # 테스트 실행
            historical_data = await yahoo_finance_service.get_historical_data("AAPL", "1mo", "1d")
            
            # 결과 검증
            assert len(historical_data) == 2
            assert historical_data[0].symbol == "AAPL"
            assert historical_data[0].open == 148.50
            assert historical_data[0].high == 151.00
            assert historical_data[0].low == 147.75
            assert historical_data[0].close == 150.25
            assert historical_data[0].volume == 1000000
    
    @pytest.mark.asyncio
    async def test_get_historical_data_cache_hit(self, yahoo_finance_service, mock_redis_client):
        """캐시 히트 과거 데이터 조회 테스트"""
        # 설정
        cached_data = [asdict(HistoricalData(
            symbol="AAPL",
            date="2023-01-01",
            open=148.50,
            high=151.00,
            low=147.75,
            close=150.25,
            volume=1000000
        ))]
        mock_redis_client.get.return_value = json.dumps(cached_data)
        
        # 테스트 실행
        historical_data = await yahoo_finance_service.get_historical_data("AAPL", "1mo", "1d")
        
        # 결과 검증
        assert len(historical_data) == 1
        assert historical_data[0].symbol == "AAPL"
        assert historical_data[0].open == 148.50
    
    @pytest.mark.asyncio
    async def test_get_historical_data_rate_limit(self, yahoo_finance_service):
        """속도 제한 과거 데이터 조회 테스트"""
        # 설정
        yahoo_finance_service.request_count["minute"] = 60  # 속도 제한 도달
        
        # 테스트 실행
        historical_data = await yahoo_finance_service.get_historical_data("AAPL", "1mo", "1d")
        
        # 결과 검증
        assert historical_data == []  # 속도 제한으로 빈 목록 반환
    
    @pytest.mark.asyncio
    async def test_search_stocks_success(self, yahoo_finance_service, mock_session):
        """주식 검색 성공 테스트"""
        # 설정
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "quotes": [
                {
                    "symbol": "AAPL",
                    "shortname": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY"
                },
                {
                    "symbol": "GOOGL",
                    "shortname": "Alphabet Inc.",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY"
                }
            ]
        })
        
        # 직접 _fetch_search_results 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_search_results') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "type": "EQUITY"
                },
                {
                    "symbol": "GOOGL",
                    "name": "Alphabet Inc.",
                    "exchange": "NASDAQ",
                    "type": "EQUITY"
                }
            ]
            
            # 테스트 실행
            search_results = await yahoo_finance_service.search_stocks("Apple")
            
            # 결과 검증
            assert len(search_results) == 2
            assert search_results[0]["symbol"] == "AAPL"
            assert search_results[0]["name"] == "Apple Inc."
            assert search_results[0]["exchange"] == "NASDAQ"
    
    @pytest.mark.asyncio
    async def test_search_stocks_cache_hit(self, yahoo_finance_service, mock_redis_client):
        """캐시 히트 주식 검색 테스트"""
        # 설정
        cached_data = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "type": "EQUITY"
            }
        ]
        mock_redis_client.get.return_value = json.dumps(cached_data)
        
        # 테스트 실행
        search_results = await yahoo_finance_service.search_stocks("Apple")
        
        # 결과 검증
        assert len(search_results) == 1
        assert search_results[0]["symbol"] == "AAPL"
        assert search_results[0]["name"] == "Apple Inc."
    
    @pytest.mark.asyncio
    async def test_search_stocks_rate_limit(self, yahoo_finance_service):
        """속도 제한 주식 검색 테스트"""
        # 설정
        yahoo_finance_service.request_count["minute"] = 60  # 속도 제한 도달
        
        # 테스트 실행
        search_results = await yahoo_finance_service.search_stocks("Apple")
        
        # 결과 검증
        assert search_results == []  # 속도 제한으로 빈 목록 반환
    
    @pytest.mark.asyncio
    async def test_get_company_profile_success(self, yahoo_finance_service, mock_session):
        """회사 프로필 조회 성공 테스트"""
        # 설정
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "quoteSummary": {
                "result": [{
                    "price": {
                        "symbol": "AAPL",
                        "currency": "USD",
                        "marketCap": 3000000000
                    },
                    "assetProfile": {
                        "website": "https://www.apple.com",
                        "fullTimeEmployees": 147000,
                        "city": "Cupertino",
                        "country": "United States"
                    },
                    "summaryProfile": {
                        "longName": "Apple Inc.",
                        "shortName": "Apple",
                        "sector": "Technology",
                        "industry": "Consumer Electronics"
                    }
                }]
            }
        })
        
        # 직접 _fetch_profile_data 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_profile_data') as mock_fetch:
            mock_fetch.return_value = {
                "symbol": "AAPL",
                "long_name": "Apple Inc.",
                "short_name": "Apple",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "website": "https://www.apple.com",
                "employees": 147000,
                "city": "Cupertino",
                "country": "United States"
            }
            
            # 테스트 실행
            profile = await yahoo_finance_service.get_company_profile("AAPL")
            
            # 결과 검증
            assert profile is not None
            assert profile["symbol"] == "AAPL"
            assert profile["long_name"] == "Apple Inc."
            assert profile["short_name"] == "Apple"
            assert profile["sector"] == "Technology"
            assert profile["industry"] == "Consumer Electronics"
            assert profile["website"] == "https://www.apple.com"
            assert profile["employees"] == 147000
            assert profile["city"] == "Cupertino"
            assert profile["country"] == "United States"
    
    @pytest.mark.asyncio
    async def test_get_company_profile_cache_hit(self, yahoo_finance_service, mock_redis_client):
        """캐시 히트 회사 프로필 조회 테스트"""
        # 설정
        cached_data = {
            "symbol": "AAPL",
            "long_name": "Apple Inc.",
            "sector": "Technology"
        }
        mock_redis_client.get.return_value = json.dumps(cached_data)
        
        # 테스트 실행
        profile = await yahoo_finance_service.get_company_profile("AAPL")
        
        # 결과 검증
        assert profile is not None
        assert profile["symbol"] == "AAPL"
        assert profile["long_name"] == "Apple Inc."
        assert profile["sector"] == "Technology"
    
    @pytest.mark.asyncio
    async def test_get_company_profile_rate_limit(self, yahoo_finance_service):
        """속도 제한 회사 프로필 조회 테스트"""
        # 설정
        yahoo_finance_service.request_count["minute"] = 60  # 속도 제한 도달
        
        # 테스트 실행
        profile = await yahoo_finance_service.get_company_profile("AAPL")
        
        # 결과 검증
        assert profile is None  # 속도 제한으로 None 반환
    
    @pytest.mark.asyncio
    async def test_transform_stock_data_success(self, yahoo_finance_service):
        """주식 데이터 변환 성공 테스트"""
        # 설정
        data = {
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": 150.25,
                        "previousClose": 147.75,
                        "regularMarketOpen": 148.50,
                        "regularMarketDayHigh": 151.00,
                        "regularMarketDayLow": 147.75,
                        "regularMarketVolume": 1000000,
                        "exchangeName": "NASDAQ",
                        "currency": "USD",
                        "shortName": "Apple",
                        "longName": "Apple Inc.",
                        "regularMarketTime": time.time()
                    }
                }]
            }
        }
        
        # 테스트 실행
        stock_data = yahoo_finance_service._transform_stock_data(data, "AAPL")
        
        # 결과 검증
        assert stock_data is not None
        assert stock_data.symbol == "AAPL"
        assert stock_data.current_price == 150.25
        assert stock_data.previous_close == 147.75
        assert stock_data.open_price == 148.50
        assert stock_data.day_high == 151.00
        assert stock_data.day_low == 147.75
        assert stock_data.volume == 1000000
    
    @pytest.mark.asyncio
    async def test_transform_stock_data_no_result(self, yahoo_finance_service):
        """결과 없는 주식 데이터 변환 테스트"""
        # 설정
        data = {
            "chart": {
                "result": []
            }
        }
        
        # 테스트 실행
        stock_data = yahoo_finance_service._transform_stock_data(data, "AAPL")
        
        # 결과 검증
        assert stock_data is None
    
    @pytest.mark.asyncio
    async def test_transform_historical_data_success(self, yahoo_finance_service):
        """과거 데이터 변환 성공 테스트"""
        # 설정
        data = {
            "chart": {
                "result": [{
                    "timestamp": [1640995200, 1641081600],
                    "indicators": {
                        "quote": [{
                            "open": [148.50, 149.00],
                            "high": [151.00, 151.50],
                            "low": [147.75, 148.25],
                            "close": [150.25, 150.75],
                            "volume": [1000000, 1100000]
                        }]
                    }
                }]
            }
        }
        
        # 테스트 실행
        historical_data = yahoo_finance_service._transform_historical_data(data, "AAPL")
        
        # 결과 검증
        assert len(historical_data) == 2
        assert historical_data[0].symbol == "AAPL"
        assert historical_data[0].open == 148.50
        assert historical_data[0].high == 151.00
        assert historical_data[0].low == 147.75
        assert historical_data[0].close == 150.25
        assert historical_data[0].volume == 1000000
    
    @pytest.mark.asyncio
    async def test_transform_historical_data_no_result(self, yahoo_finance_service):
        """결과 없는 과거 데이터 변환 테스트"""
        # 설정
        data = {
            "chart": {
                "result": []
            }
        }
        
        # 테스트 실행
        historical_data = yahoo_finance_service._transform_historical_data(data, "AAPL")
        
        # 결과 검증
        assert historical_data == []
    
    @pytest.mark.asyncio
    async def test_transform_search_results_success(self, yahoo_finance_service):
        """검색 결과 변환 성공 테스트"""
        # 설정
        data = {
            "quotes": [
                {
                    "symbol": "AAPL",
                    "shortname": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                    "score": 1.0
                },
                {
                    "symbol": "GOOGL",
                    "shortname": "Alphabet Inc.",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                    "score": 0.8
                }
            ]
        }
        
        # 테스트 실행
        search_results = yahoo_finance_service._transform_search_results(data)
        
        # 결과 검증
        assert len(search_results) == 2
        assert search_results[0]["symbol"] == "AAPL"
        assert search_results[0]["name"] == "Apple Inc."
        assert search_results[0]["exchange"] == "NASDAQ"
        assert search_results[0]["type"] == "EQUITY"
        assert search_results[0]["score"] == 1.0
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limits(self, yahoo_finance_service):
        """속도 제한 내에서의 확인 테스트"""
        # 설정
        yahoo_finance_service.request_count["minute"] = 30
        yahoo_finance_service.request_count["hour"] = 100
        
        # 테스트 실행
        result = await yahoo_finance_service._check_rate_limit()
        
        # 결과 검증
        assert result is True
        assert yahoo_finance_service.request_count["minute"] == 31
        assert yahoo_finance_service.request_count["hour"] == 101
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded_minute(self, yahoo_finance_service):
        """분당 속도 제한 초과 확인 테스트"""
        # 설정
        yahoo_finance_service.request_count["minute"] = 60  # 한계 도달
        
        # 테스트 실행
        result = await yahoo_finance_service._check_rate_limit()
        
        # 결과 검증
        assert result is False
        assert yahoo_finance_service.request_count["minute"] == 60  # 증가하지 않음
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded_hour(self, yahoo_finance_service):
        """시간당 속도 제한 초과 확인 테스트"""
        # 설정
        yahoo_finance_service.request_count["hour"] = 2000  # 한계 도달
        
        # 테스트 실행
        result = await yahoo_finance_service._check_rate_limit()
        
        # 결과 검증
        assert result is False
        assert yahoo_finance_service.request_count["hour"] == 2000  # 증가하지 않음
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_time_reset(self, yahoo_finance_service):
        """속도 제한 시간 초기화 테스트"""
        # 설정
        current_time = time.time()
        old_minute = int(current_time // 60) - 1
        old_hour = int(current_time // 3600) - 1
        
        yahoo_finance_service.request_count["minute"] = 60
        yahoo_finance_service.request_count["hour"] = 2000
        yahoo_finance_service.request_count["last_minute"] = old_minute
        yahoo_finance_service.request_count["last_hour"] = old_hour
        
        # 테스트 실행
        result = await yahoo_finance_service._check_rate_limit()
        
        # 결과 검증
        assert result is True  # 시간이 초기화되어 다시 허용
        assert yahoo_finance_service.request_count["minute"] == 1  # 초기화 후 1로 설정
        assert yahoo_finance_service.request_count["hour"] == 1  # 초기화 후 1로 설정
    
    @pytest.mark.asyncio
    async def test_get_from_cache_success(self, yahoo_finance_service, mock_redis_client):
        """캐시에서 데이터 가져오기 성공 테스트"""
        # 설정
        test_data = {"symbol": "AAPL", "price": 150.25}
        mock_redis_client.get.return_value = json.dumps(test_data)
        
        # 테스트 실행
        result = await yahoo_finance_service._get_from_cache("test_key", "current")
        
        # 결과 검증
        assert result == test_data
        mock_redis_client.get.assert_called_once_with("test_key")