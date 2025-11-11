"""
UnifiedService 단위 테스트

통합 서비스의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from backend.services.unified_service import (
    UnifiedService,
    UnifiedDataRequest,
    UnifiedDataResponse,
    DataSource,
    DataType,
    AnalysisType
)


class TestUnifiedDataRequest:
    """UnifiedDataRequest 모델 테스트 클래스"""
    
    def test_unified_data_request_creation(self):
        """UnifiedDataRequest 생성 테스트"""
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE, DataType.FINANCIALS],
            analysis_types=[AnalysisType.TECHNICAL, AnalysisType.SENTIMENT],
            sources=[DataSource.YAHOO_FINANCE, DataSource.ALPHA_VANTAGE],
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            options={"include_extended": True}
        )
        
        assert request.symbol == "AAPL"
        assert DataType.STOCK_PRICE in request.data_types
        assert DataType.FINANCIALS in request.data_types
        assert AnalysisType.TECHNICAL in request.analysis_types
        assert AnalysisType.SENTIMENT in request.analysis_types
        assert DataSource.YAHOO_FINANCE in request.sources
        assert DataSource.ALPHA_VANTAGE in request.sources
        assert request.options["include_extended"] is True


class TestUnifiedDataResponse:
    """UnifiedDataResponse 모델 테스트 클래스"""
    
    def test_unified_data_response_creation(self):
        """UnifiedDataResponse 생성 테스트"""
        response = UnifiedDataResponse(
            symbol="AAPL",
            data={"price": 150.25, "volume": 1000000},
            analysis={"trend": "bullish", "sentiment": "positive"},
            metadata={"source": DataSource.YAHOO_FINANCE, "updated_at": datetime.utcnow()},
            errors=[],
            warnings=["Data limited to last 30 days"]
        )
        
        assert response.symbol == "AAPL"
        assert response.data["price"] == 150.25
        assert response.analysis["trend"] == "bullish"
        assert response.metadata["source"] == DataSource.YAHOO_FINANCE
        assert len(response.errors) == 0
        assert len(response.warnings) == 1


class TestUnifiedService:
    """UnifiedService 테스트 클래스"""
    
    @pytest.fixture
    def mock_stock_service(self):
        """모의 주식 서비스"""
        service = AsyncMock()
        service.get_stock_data.return_value = {
            "symbol": "AAPL",
            "price": 150.25,
            "volume": 1000000,
            "timestamp": datetime.utcnow()
        }
        service.get_financial_data.return_value = {
            "symbol": "AAPL",
            "revenue": 365817000000,
            "net_income": 94680000000,
            "period": "2023"
        }
        return service
    
    @pytest.fixture
    def mock_sentiment_service(self):
        """모의 감성 분석 서비스"""
        service = AsyncMock()
        service.analyze_stock_sentiment.return_value = {
            "symbol": "AAPL",
            "sentiment": "positive",
            "score": 0.75,
            "confidence": 0.85,
            "articles_analyzed": 50
        }
        return service
    
    @pytest.fixture
    def mock_cache_manager(self):
        """모의 캐시 관리자"""
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = True
        return cache
    
    @pytest.fixture
    def unified_service(self, mock_stock_service, mock_sentiment_service, mock_cache_manager):
        """UnifiedService 인스턴스"""
        return UnifiedService(
            stock_service=mock_stock_service,
            sentiment_service=mock_sentiment_service,
            cache_manager=mock_cache_manager
        )
    
    @pytest.mark.asyncio
    async def test_get_unified_data_stock_price_only(self, unified_service, mock_stock_service):
        """주식 가격 데이터만 요청하는 통합 데이터 조회 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        assert response.data["price"] == 150.25
        assert len(response.errors) == 0
        
        # 모의 호출 검증
        mock_stock_service.get_stock_data.assert_called_once_with("AAPL")
        mock_stock_service.get_financial_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_unified_data_with_financials(self, unified_service, mock_stock_service):
        """재무 데이터 포함 통합 데이터 조회 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE, DataType.FINANCIALS],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        assert "revenue" in response.data
        assert response.data["revenue"] == 365817000000
        
        # 모의 호출 검증
        mock_stock_service.get_stock_data.assert_called_once_with("AAPL")
        mock_stock_service.get_financial_data.assert_called_once_with("AAPL")
    
    @pytest.mark.asyncio
    async def test_get_unified_data_with_sentiment(self, unified_service, mock_sentiment_service):
        """감성 분석 포함 통합 데이터 조회 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[AnalysisType.SENTIMENT],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        assert "sentiment" in response.analysis
        assert response.analysis["sentiment"] == "positive"
        
        # 모의 호출 검증
        mock_sentiment_service.analyze_stock_sentiment.assert_called_once_with("AAPL")
    
    @pytest.mark.asyncio
    async def test_get_unified_data_cache_hit(self, unified_service, mock_cache_manager):
        """캐시 히트 통합 데이터 조회 테스트"""
        # 설정
        cached_response = UnifiedDataResponse(
            symbol="AAPL",
            data={"price": 150.25},
            analysis={},
            metadata={"source": DataSource.YAHOO_FINANCE, "updated_at": datetime.utcnow()},
            errors=[],
            warnings=[]
        )
        
        mock_cache_manager.get.return_value = cached_response
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert response.data["price"] == 150.25
        
        # 모의 호출 검증
        mock_cache_manager.get.assert_called_once()
        mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_unified_data_cache_miss(self, unified_service, mock_cache_manager):
        """캐시 미스 통합 데이터 조회 테스트"""
        # 설정
        mock_cache_manager.get.return_value = None
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        
        # 모의 호출 검증
        mock_cache_manager.get.assert_called_once()
        mock_cache_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_unified_data_service_error(self, unified_service, mock_stock_service):
        """서비스 오류 통합 데이터 조회 테스트"""
        # 설정
        mock_stock_service.get_stock_data.side_effect = Exception("Service unavailable")
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert len(response.errors) > 0
        assert "Service unavailable" in response.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_unified_data_partial_success(self, unified_service, mock_stock_service, mock_sentiment_service):
        """부분적 성공 통합 데이터 조회 테스트"""
        # 설정
        mock_sentiment_service.analyze_stock_sentiment.side_effect = Exception("Sentiment service error")
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[AnalysisType.SENTIMENT],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data  # 주식 데이터는 성공
        assert len(response.errors) > 0  # 감성 분석은 실패
        assert "Sentiment service error" in response.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_unified_data_with_date_range(self, unified_service, mock_stock_service):
        """날짜 범위 포함 통합 데이터 조회 테스트"""
        # 설정
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE],
            start_date=start_date,
            end_date=end_date
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        
        # 모의 호출 검증
        mock_stock_service.get_stock_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_unified_data_with_options(self, unified_service, mock_stock_service):
        """옵션 포함 통합 데이터 조회 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE],
            options={"include_extended": True, "interval": "1h"}
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        
        # 모의 호출 검증
        mock_stock_service.get_stock_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_unified_data_multiple_sources(self, unified_service, mock_stock_service):
        """여러 소스 통합 데이터 조회 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE, DataSource.ALPHA_VANTAGE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert "price" in response.data
        
        # 모의 호출 검증
        mock_stock_service.get_stock_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_unified_data_empty_request(self, unified_service):
        """빈 요청 통합 데이터 조회 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[],
            analysis_types=[],
            sources=[]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert len(response.data) == 0
        assert len(response.analysis) == 0
        assert len(response.warnings) > 0
        assert "No data types specified" in response.warnings[0]
    
    @pytest.mark.asyncio
    async def test_get_unified_data_invalid_symbol(self, unified_service, mock_stock_service):
        """잘못된 심볼 통합 데이터 조회 테스트"""
        # 설정
        mock_stock_service.get_stock_data.side_effect = ValueError("Invalid symbol")
        
        request = UnifiedDataRequest(
            symbol="INVALID",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "INVALID"
        assert len(response.errors) > 0
        assert "Invalid symbol" in response.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_unified_data_timeout(self, unified_service, mock_stock_service):
        """타임아웃 통합 데이터 조회 테스트"""
        # 설정
        mock_stock_service.get_stock_data.side_effect = asyncio.TimeoutError("Request timeout")
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert len(response.errors) > 0
        assert "Request timeout" in response.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_unified_data_rate_limit(self, unified_service, mock_stock_service):
        """속도 제한 통합 데이터 조회 테스트"""
        # 설정
        mock_stock_service.get_stock_data.side_effect = Exception("Rate limit exceeded")
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert len(response.errors) > 0
        assert "Rate limit exceeded" in response.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_unified_data_network_error(self, unified_service, mock_stock_service):
        """네트워크 오류 통합 데이터 조회 테스트"""
        # 설정
        mock_stock_service.get_stock_data.side_effect = ConnectionError("Network error")
        
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        response = await unified_service.get_unified_data(request)
        
        # 결과 검증
        assert response.symbol == "AAPL"
        assert len(response.errors) > 0
        assert "Network error" in response.errors[0]
    
    def test_generate_cache_key(self, unified_service):
        """캐시 키 생성 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE, DataType.FINANCIALS],
            analysis_types=[AnalysisType.TECHNICAL, AnalysisType.SENTIMENT],
            sources=[DataSource.YAHOO_FINANCE],
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        # 테스트 실행
        cache_key = unified_service._generate_cache_key(request)
        
        # 결과 검증
        assert "AAPL" in cache_key
        assert "stock_price" in cache_key
        assert "financials" in cache_key
        assert "technical" in cache_key
        assert "sentiment" in cache_key
        assert "yahoo_finance" in cache_key
    
    def test_generate_cache_key_different_requests(self, unified_service):
        """다른 요청에 대한 캐시 키 생성 테스트"""
        # 설정
        request1 = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        request2 = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.FINANCIALS],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        cache_key1 = unified_service._generate_cache_key(request1)
        cache_key2 = unified_service._generate_cache_key(request2)
        
        # 결과 검증
        assert cache_key1 != cache_key2
    
    @pytest.mark.asyncio
    async def test_merge_data_sources(self, unified_service):
        """여러 데이터 소스 병합 테스트"""
        # 설정
        source1_data = {"price": 150.25, "volume": 1000000}
        source2_data = {"price": 150.30, "market_cap": 3000000000}
        
        # 테스트 실행
        merged_data = unified_service._merge_data_sources([source1_data, source2_data])
        
        # 결과 검증
        assert merged_data["price"] == 150.30  # 마지막 소스가 우선
        assert merged_data["volume"] == 1000000
        assert merged_data["market_cap"] == 3000000000
    
    @pytest.mark.asyncio
    async def test_merge_analyses(self, unified_service):
        """여러 분석 결과 병합 테스트"""
        # 설정
        analysis1 = {"trend": "bullish", "strength": 0.7}
        analysis2 = {"sentiment": "positive", "confidence": 0.8}
        
        # 테스트 실행
        merged_analysis = unified_service._merge_analyses([analysis1, analysis2])
        
        # 결과 검증
        assert merged_analysis["trend"] == "bullish"
        assert merged_analysis["strength"] == 0.7
        assert merged_analysis["sentiment"] == "positive"
        assert merged_analysis["confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_validate_request_valid(self, unified_service):
        """유효한 요청 검증 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        is_valid, errors = unified_service._validate_request(request)
        
        # 결과 검증
        assert is_valid is True
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_request_empty_symbol(self, unified_service):
        """빈 심볼 요청 검증 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="",
            data_types=[DataType.STOCK_PRICE],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        is_valid, errors = unified_service._validate_request(request)
        
        # 결과 검증
        assert is_valid is False
        assert len(errors) > 0
        assert "Symbol is required" in errors[0]
    
    @pytest.mark.asyncio
    async def test_validate_request_no_data_types(self, unified_service):
        """데이터 타입 없는 요청 검증 테스트"""
        # 설정
        request = UnifiedDataRequest(
            symbol="AAPL",
            data_types=[],
            analysis_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        is_valid, errors = unified_service._validate_request(request)
        
        # 결과 검증
        assert is_valid is False
        assert len(errors) > 0
        assert "At least one data type is required" in errors[0]