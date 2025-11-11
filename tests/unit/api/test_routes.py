"""
API 라우트 단위 테스트

이 모듈은 API 엔드포인트의 개별 기능을 독립적으로 테스트합니다.
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.api.routes import router
from backend.models.unified_models import (
    UnifiedStockData, 
    SearchQuery, 
    SearchResult,
    StockType,
    SentimentSource
)


class TestRoutes:
    """API 라우트 단위 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 픽스처"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_unified_service(self):
        """UnifiedService 모의 객체 픽스처"""
        service = Mock()
        service.get_stock_data = AsyncMock()
        service.search_stocks = AsyncMock()
        service.get_trending_stocks = AsyncMock()
        service.get_market_indices = AsyncMock()
        service.get_market_sentiment = AsyncMock()
        service.compare_stocks = AsyncMock()
        service.get_detailed_sentiment = AsyncMock()
        service.get_correlation_analysis = AsyncMock()
        service.get_user_watchlist = AsyncMock()
        service.add_to_watchlist = AsyncMock()
        service.get_market_insights = AsyncMock()
        service.get_data_quality_report = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_stock_data(self):
        """샘플 주식 데이터 픽스처"""
        return UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000000000.0,
            current_price=150.0,
            previous_close=148.0,
            day_change=2.0,
            day_change_pct=1.35,
            volume=50000000,
            avg_volume=45000000,
            day_high=151.0,
            day_low=149.0,
            pe_ratio=25.5,
            dividend_yield=0.5,
            beta=1.2,
            eps=5.88,
            fifty_two_week_high=180.0,
            fifty_two_week_low=120.0,
            overall_sentiment=0.2,
            sentiment_sources={SentimentSource.REDDIT: 0.1, SentimentSource.TWITTER: 0.3},
            mention_count_24h=100,
            mention_count_1h=10,
            positive_mentions=60,
            negative_mentions=20,
            neutral_mentions=20,
            trending_status=True,
            trend_score=2.5,
            trend_duration_hours=12
        )
    
    @pytest.fixture
    def sample_search_result(self, sample_stock_data):
        """샘플 검색 결과 픽스처"""
        return SearchResult(
            query=SearchQuery(query="Apple", limit=10),
            results=[sample_stock_data],
            total_count=1,
            search_time_ms=150.0,
            cache_hit=False
        )
    
    def test_health_check(self, client):
        """상태 확인 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["status"] == "healthy"
        assert "timestamp" in data["data"]
        assert "version" in data["data"]
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_stock_data_success(self, mock_get_service, client, sample_stock_data):
        """주식 데이터 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_stock_data.return_value = sample_stock_data
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/stock",
            json={"symbol": "AAPL", "include_sentiment": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["symbol"] == "AAPL"
        assert data["data"]["company_name"] == "Apple Inc."
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_stock_data.assert_called_once_with("AAPL", True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_stock_data_not_found(self, mock_get_service, client):
        """주식 데이터 조회 실패 테스트 (주식 없음)"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_stock_data.return_value = None
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/stock",
            json={"symbol": "INVALID", "include_sentiment": True}
        )
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert "not found" in data["detail"]
    
    @patch('backend.api.routes.get_unified_service')
    def test_search_stocks_success(self, mock_get_service, client, sample_search_result):
        """주식 검색 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.search_stocks.return_value = sample_search_result
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/search",
            json={"query": "Apple", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["query"]["query"] == "Apple"
        assert len(data["data"]["results"]) == 1
        assert data["data"]["total_count"] == 1
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.search_stocks.assert_called_once()
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_trending_stocks_success(self, mock_get_service, client, sample_stock_data):
        """트렌딩 주식 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_trending_stocks.return_value = [sample_stock_data]
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/trending?limit=10&timeframe=24h")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["symbol"] == "AAPL"
        assert data["count"] == 1
        assert data["timeframe"] == "24h"
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_trending_stocks.assert_called_once_with(10, "24h")
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_market_indices_success(self, mock_get_service, client):
        """시장 지수 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_market_indices.return_value = [
            {"symbol": "^GSPC", "name": "S&P 500", "value": 4500.0},
            {"symbol": "^IXIC", "name": "NASDAQ", "value": 14000.0}
        ]
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/market/indices")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) == 2
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_market_indices.assert_called_once()
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_market_sentiment_success(self, mock_get_service, client):
        """시장 감성 분석 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_market_sentiment.return_value = {
            "overall_sentiment": 0.1,
            "positive_count": 500,
            "negative_count": 300,
            "neutral_count": 200
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/market/sentiment")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["overall_sentiment"] == 0.1
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_market_sentiment.assert_called_once()
    
    @patch('backend.api.routes.get_unified_service')
    def test_compare_stocks_success(self, mock_get_service, client, sample_stock_data):
        """주식 비교 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.compare_stocks.return_value = {
            "comparison": [
                {"symbol": "AAPL", "data": sample_stock_data.to_dict()},
                {"symbol": "MSFT", "data": sample_stock_data.to_dict()}
            ],
            "correlation": 0.75
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/compare",
            json={"symbols": ["AAPL", "MSFT"], "period": "1mo", "include_sentiment": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert "comparison" in data["data"]
        assert len(data["data"]["comparison"]) == 2
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.compare_stocks.assert_called_once_with(["AAPL", "MSFT"], "1mo", True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_detailed_sentiment_success(self, mock_get_service, client):
        """상세 감성 분석 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_detailed_sentiment.return_value = {
            "symbol": "AAPL",
            "overall_sentiment": 0.2,
            "mention_count_24h": 100,
            "positive_mentions": 60,
            "negative_mentions": 20,
            "neutral_mentions": 20,
            "trending_status": True,
            "trend_score": 2.5
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/sentiment",
            json={"symbol": "AAPL", "timeframe": "24h", "include_mentions": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["symbol"] == "AAPL"
        assert data["data"]["overall_sentiment"] == 0.2
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_detailed_sentiment.assert_called_once_with("AAPL", None, "24h", True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_detailed_sentiment_no_data(self, mock_get_service, client):
        """상세 감성 분석 조회 테스트 (데이터 없음)"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_detailed_sentiment.return_value = {}
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/sentiment",
            json={"symbol": "NEW", "timeframe": "24h", "include_mentions": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["symbol"] == "NEW"
        assert data["data"]["overall_sentiment"] == 0.0
        assert data["data"]["mention_count_24h"] == 0
        
        # 서비스 메서드 호출 확인
        mock_service.get_detailed_sentiment.assert_called_once_with("NEW", None, "24h", True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_correlation_analysis_success(self, mock_get_service, client):
        """상관관계 분석 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_correlation_analysis.return_value = {
            "symbol1": "AAPL",
            "symbol2": "MSFT",
            "correlation": 0.75,
            "sentiment_correlation": 0.65,
            "period": "1y"
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/correlation",
            json={"symbol1": "AAPL", "symbol2": "MSFT", "period": "1y", "include_sentiment": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["symbol1"] == "AAPL"
        assert data["data"]["symbol2"] == "MSFT"
        assert data["data"]["correlation"] == 0.75
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_correlation_analysis.assert_called_once_with("AAPL", "MSFT", "1y", True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_correlation_analysis_error(self, mock_get_service, client):
        """상관관계 분석 오류 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_correlation_analysis.return_value = {"error": "Insufficient data"}
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/correlation",
            json={"symbol1": "INVALID1", "symbol2": "INVALID2", "period": "1y", "include_sentiment": True}
        )
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert "Insufficient data" in data["detail"]
        
        # 서비스 메서드 호출 확인
        mock_service.get_correlation_analysis.assert_called_once_with("INVALID1", "INVALID2", "1y", True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_user_watchlist_success(self, mock_get_service, client, sample_stock_data):
        """사용자 관심목록 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_user_watchlist.return_value = {
            "user_id": "test_user",
            "watchlist": [sample_stock_data.to_dict()],
            "sentiment_data": {"overall_sentiment": 0.2}
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/watchlist/test_user?include_sentiment=True&include_alerts=True")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["user_id"] == "test_user"
        assert len(data["data"]["watchlist"]) == 1
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_user_watchlist.assert_called_once_with("test_user", True, True)
    
    @patch('backend.api.routes.get_unified_service')
    def test_add_to_watchlist_success(self, mock_get_service, client):
        """관심목록 추가 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.add_to_watchlist.return_value = {
            "success": True,
            "watchlist_symbols": ["AAPL", "MSFT"]
        }
        mock_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/watchlist",
            json={
                "user_id": "test_user",
                "symbol": "AAPL",
                "category": "Technology",
                "alert_threshold": 5.0,
                "sentiment_alert": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["success"] is True
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.add_to_watchlist.assert_called_once_with(
            "test_user", "AAPL", "Technology", 5.0, True
        )
    
    @patch('backend.api.routes.get_unified_service')
    def test_add_to_watchlist_failure(self, mock_get_service, client):
        """관심목록 추가 실패 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.add_to_watchlist.return_value = {
            "success": False,
            "error": "Invalid symbol"
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.post(
            "/watchlist",
            json={
                "user_id": "test_user",
                "symbol": "INVALID",
                "category": "Technology",
                "alert_threshold": 5.0,
                "sentiment_alert": True
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "Invalid symbol" in data["detail"]
        
        # 서비스 메서드 호출 확인
        mock_service.add_to_watchlist.assert_called_once_with(
            "test_user", "INVALID", "Technology", 5.0, True
        )
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_market_insights_success(self, mock_get_service, client):
        """시장 인사이트 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_market_insights.return_value = {
            "trending_sectors": ["Technology", "Healthcare"],
            "market_sentiment": 0.15,
            "top_gainers": ["AAPL", "NVDA"],
            "top_losers": ["META", "AMZN"]
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/insights?timeframe=24h&category=Technology")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["trending_sectors"] == ["Technology", "Healthcare"]
        assert data["data"]["market_sentiment"] == 0.15
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_market_insights.assert_called_once_with("24h", "Technology")
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_data_quality_report_success(self, mock_get_service, client):
        """데이터 품질 보고서 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.get_data_quality_report.return_value = {
            "overall_score": 0.85,
            "data_completeness": 0.9,
            "data_accuracy": 0.8,
            "data_freshness": 0.85,
            "issues": []
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/quality")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["overall_score"] == 0.85
        assert data["data"]["data_completeness"] == 0.9
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.get_data_quality_report.assert_called_once()
    
    @patch('backend.api.routes.get_unified_service')
    def test_get_cache_statistics_success(self, mock_get_service, client):
        """캐시 통계 조회 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.cache_manager = Mock()
        mock_service.cache_manager.get_cache_stats.return_value = {
            "l1_hits": 1000,
            "l2_hits": 500,
            "l1_misses": 200,
            "l2_misses": 100,
            "hit_rate": 0.85,
            "total_requests": 1800
        }
        mock_get_service.return_value = mock_service
        
        # 테스트 요청
        response = client.get("/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["l1_hits"] == 1000
        assert data["data"]["hit_rate"] == 0.85
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.cache_manager.get_cache_stats.assert_called_once()
    
    @patch('backend.api.routes.get_unified_service')
    def test_clear_cache_success(self, mock_get_service, client):
        """캐시 정리 성공 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        mock_service.cache_manager = Mock()
        mock_service.cache_manager.clear_all.return_value = 50
        mock_service.cache_manager.clear_pattern.return_value = 10
        mock_get_service.return_value = mock_service
        
        # 테스트 요청 (전체 정리)
        response = client.post("/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["cleared_entries"] == 50
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.cache_manager.clear_all.assert_called_once()
        
        # 테스트 요청 (패턴 정리)
        response = client.post("/cache/clear?pattern=stock_*")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["cleared_entries"] == 10
        assert "timestamp" in data
        
        # 서비스 메서드 호출 확인
        mock_service.cache_manager.clear_pattern.assert_called_once_with("stock_*")
    
    def test_request_validation(self, client):
        """요청 유효성 검증 테스트"""
        # 잘못된 요청 데이터
        response = client.post(
            "/stock",
            json={"symbol": "", "include_sentiment": True}  # 빈 심볼
        )
        
        assert response.status_code == 422  # Validation error
        
        # 필수 필드 누락
        response = client.post(
            "/stock",
            json={"include_sentiment": True}  # 심볼 필드 누락
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_error_handling(self, client):
        """오류 처리 테스트"""
        # 내부 서버 오류 시뮬레이션
        with patch('backend.api.routes.get_unified_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_stock_data.side_effect = Exception("Database error")
            mock_get_service.return_value = mock_service
            
            response = client.post(
                "/stock",
                json={"symbol": "AAPL", "include_sentiment": True}
            )
            
            assert response.status_code == 500
            data = response.json()
            
            assert "detail" in data
            assert "Internal server error" in data["detail"]