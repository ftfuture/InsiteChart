"""
Integration tests for InsiteChart platform.

This module contains integration tests to verify the functionality
of the backend API and frontend integration.
"""

import pytest
import requests
import pandas as pd
from typing import Dict, Any, List
import time
import os
import sys

# Add the backend and frontend directories to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from backend.api.routes import router as api_router
from backend.config import get_settings
from frontend.api_client import InsiteChartAPIClient


class TestInsiteChartIntegration:
    """Integration tests for InsiteChart platform."""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API client for testing."""
        # Use test server URL
        base_url = os.getenv("TEST_API_URL", "http://localhost:8000/api/v1")
        return InsiteChartAPIClient(base_url)
    
    @pytest.fixture(scope="class")
    def test_symbols(self):
        """Test symbols for testing."""
        return ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    def test_api_health_check(self, api_client):
        """Test API health check endpoint."""
        response = api_client.health_check()
        
        assert response.get("success", False), "Health check should succeed"
        assert "status" in response.get("data", {}), "Health check should return status"
        assert response["data"]["status"] == "healthy", "API should be healthy"
    
    def test_get_stock_data(self, api_client, test_symbols):
        """Test getting stock data."""
        symbol = test_symbols[0]
        response = api_client.get_stock_data(symbol, include_sentiment=True)
        
        assert response.get("success", False), f"Should get data for {symbol}"
        data = response.get("data", {})
        
        # Check basic stock data fields
        assert data.get("symbol") == symbol, "Should return correct symbol"
        assert data.get("company_name") is not None, "Should return company name"
        assert data.get("current_price") is not None, "Should return current price"
        assert data.get("previous_close") is not None, "Should return previous close"
        
        # Check sentiment data (may be None if not available)
        sentiment = data.get("overall_sentiment")
        if sentiment is not None:
            assert isinstance(sentiment, (int, float)), "Sentiment should be numeric"
            assert -1 <= sentiment <= 1, "Sentiment should be between -1 and 1"
    
    def test_search_stocks(self, api_client):
        """Test stock search functionality."""
        query = "Apple"
        response = api_client.search_stocks(query, limit=5)
        
        assert response.get("success", False), "Search should succeed"
        data = response.get("data", {})
        
        if "results" in data and data["results"]:
            results = data["results"]
            assert len(results) <= 5, "Should not exceed limit"
            
            # Check result structure
            for result in results:
                assert "symbol" in result, "Result should have symbol"
                assert "company_name" in result, "Result should have company name"
    
    def test_get_trending_stocks(self, api_client):
        """Test getting trending stocks."""
        response = api_client.get_trending_stocks(limit=5)
        
        assert response.get("success", False), "Should get trending stocks"
        data = response.get("data", {})
        
        if data:
            assert isinstance(data, list), "Should return list of stocks"
            
            # Check trending stock structure
            for stock in data[:3]:  # Check first 3
                assert "symbol" in stock, "Trending stock should have symbol"
                assert "trend_score" in stock, "Trending stock should have trend score"
                assert isinstance(stock["trend_score"], (int, float)), "Trend score should be numeric"
    
    def test_get_market_indices(self, api_client):
        """Test getting market indices."""
        response = api_client.get_market_indices()
        
        assert response.get("success", False), "Should get market indices"
        data = response.get("data", {})
        
        if data:
            assert isinstance(data, list), "Should return list of indices"
            
            # Check index structure
            for index in data[:3]:  # Check first 3
                assert "symbol" in index, "Index should have symbol"
                assert "current_price" in index, "Index should have current price"
                assert "day_change" in index, "Index should have day change"
    
    def test_get_market_sentiment(self, api_client):
        """Test getting market sentiment."""
        response = api_client.get_market_sentiment()
        
        assert response.get("success", False), "Should get market sentiment"
        data = response.get("data", {})
        
        # Check sentiment structure
        assert "overall_sentiment" in data, "Should have overall sentiment"
        assert "sentiment_distribution" in data, "Should have sentiment distribution"
        
        overall_sentiment = data["overall_sentiment"]
        assert isinstance(overall_sentiment, (int, float)), "Overall sentiment should be numeric"
        assert -1 <= overall_sentiment <= 1, "Overall sentiment should be between -1 and 1"
    
    def test_compare_stocks(self, api_client, test_symbols):
        """Test stock comparison."""
        symbols = test_symbols[:3]  # Compare first 3 symbols
        response = api_client.compare_stocks(symbols, period="1mo", include_sentiment=True)
        
        assert response.get("success", False), "Stock comparison should succeed"
        data = response.get("data", {})
        
        # Check comparison structure
        assert "symbols" in data, "Should return compared symbols"
        assert "performance_metrics" in data, "Should return performance metrics"
        
        performance_metrics = data["performance_metrics"]
        for symbol in symbols:
            if symbol in performance_metrics:
                metrics = performance_metrics[symbol]
                assert "current_price" in metrics, f"Should have price for {symbol}"
                assert "daily_change" in metrics, f"Should have daily change for {symbol}"
    
    def test_get_detailed_sentiment(self, api_client, test_symbols):
        """Test detailed sentiment analysis."""
        symbol = test_symbols[0]
        response = api_client.get_detailed_sentiment(
            symbol, 
            timeframe="24h", 
            include_mentions=False
        )
        
        assert response.get("success", False), f"Should get sentiment for {symbol}"
        data = response.get("data", {})
        
        # Check sentiment structure
        assert "symbol" in data, "Should return symbol"
        assert "overall_sentiment" in data, "Should return overall sentiment"
        assert "mention_count_24h" in data, "Should return mention count"
        
        # Check sentiment breakdown
        positive = data.get("positive_mentions")
        negative = data.get("negative_mentions")
        neutral = data.get("neutral_mentions")
        
        if all(x is not None for x in [positive, negative, neutral]):
            total = positive + negative + neutral
            assert total == data.get("mention_count_24h"), "Mentions should add up to total"
    
    def test_correlation_analysis(self, api_client, test_symbols):
        """Test correlation analysis between stocks."""
        symbol1, symbol2 = test_symbols[0], test_symbols[1]
        response = api_client.get_correlation_analysis(
            symbol1, 
            symbol2, 
            period="1mo", 
            include_sentiment=True
        )
        
        assert response.get("success", False), "Correlation analysis should succeed"
        data = response.get("data", {})
        
        # Check correlation structure
        assert "symbol1" in data, "Should return first symbol"
        assert "symbol2" in data, "Should return second symbol"
        assert "price_correlation" in data, "Should return price correlation"
        assert "sentiment_correlation" in data, "Should return sentiment correlation"
        assert "combined_correlation" in data, "Should return combined correlation"
        
        # Check correlation values
        price_corr = data["price_correlation"]
        sentiment_corr = data["sentiment_correlation"]
        combined_corr = data["combined_correlation"]
        
        for corr in [price_corr, sentiment_corr, combined_corr]:
            assert isinstance(corr, (int, float)), "Correlation should be numeric"
            assert -1 <= corr <= 1, "Correlation should be between -1 and 1"
    
    def test_watchlist_operations(self, api_client, test_symbols):
        """Test watchlist operations."""
        user_id = "test_user"
        symbol = test_symbols[0]
        
        # Add to watchlist
        response = api_client.add_to_watchlist(
            user_id=user_id,
            symbol=symbol,
            category="test",
            sentiment_alert=True
        )
        
        assert response.get("success", False), "Should add to watchlist"
        
        # Get watchlist
        response = api_client.get_user_watchlist(
            user_id=user_id,
            include_sentiment=True,
            include_alerts=True
        )
        
        assert response.get("success", False), "Should get watchlist"
        data = response.get("data", {})
        
        if "watchlist" in data and data["watchlist"]:
            watchlist = data["watchlist"]
            symbols_in_watchlist = [item.get("symbol") for item in watchlist]
            assert symbol in symbols_in_watchlist, f"{symbol} should be in watchlist"
    
    def test_market_insights(self, api_client):
        """Test market insights."""
        response = api_client.get_market_insights(timeframe="24h")
        
        assert response.get("success", False), "Should get market insights"
        data = response.get("data", {})
        
        # Check insights structure
        assert "timeframe" in data, "Should return timeframe"
        assert "trending_stocks_count" in data, "Should return trending count"
        assert "sector_distribution" in data, "Should return sector distribution"
        assert "market_sentiment" in data, "Should return market sentiment"
    
    def test_data_quality_report(self, api_client):
        """Test data quality report."""
        response = api_client.get_data_quality_report()
        
        assert response.get("success", False), "Should get data quality report"
        data = response.get("data", {})
        
        # Check quality metrics
        assert "cache_hit_rate" in data, "Should return cache hit rate"
        assert "data_completeness" in data, "Should return data completeness"
        assert "overall_quality_score" in data, "Should return overall quality"
        
        # Check metric values
        for metric in ["cache_hit_rate", "data_completeness", "overall_quality_score"]:
            value = data[metric]
            assert isinstance(value, (int, float)), f"{metric} should be numeric"
            assert 0 <= value <= 1, f"{metric} should be between 0 and 1"
    
    def test_cache_operations(self, api_client):
        """Test cache operations."""
        # Get cache stats
        response = api_client.get_cache_statistics()
        
        assert response.get("success", False), "Should get cache stats"
        data = response.get("data", {})
        
        # Check cache stats structure
        assert "hits" in data, "Should return cache hits"
        assert "misses" in data, "Should return cache misses"
        assert "hit_rate" in data, "Should return hit rate"
        
        # Clear cache (optional test)
        # response = api_client.clear_cache()
        # assert response.get("success", False), "Should clear cache"


class TestPerformance:
    """Performance tests for InsiteChart platform."""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API client for testing."""
        base_url = os.getenv("TEST_API_URL", "http://localhost:8000/api/v1")
        return InsiteChartAPIClient(base_url)
    
    def test_api_response_time(self, api_client):
        """Test API response times."""
        symbol = "AAPL"
        
        # Measure response time for stock data
        start_time = time.time()
        response = api_client.get_stock_data(symbol)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.get("success", False), "API request should succeed"
        assert response_time < 5.0, f"Response time should be under 5 seconds, was {response_time:.2f}s"
    
    def test_concurrent_requests(self, api_client):
        """Test handling of concurrent requests."""
        import threading
        import queue
        
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
        results = queue.Queue()
        
        def get_stock_data(symbol):
            response = api_client.get_stock_data(symbol)
            results.put((symbol, response))
        
        # Create threads for concurrent requests
        threads = []
        for symbol in symbols:
            thread = threading.Thread(target=get_stock_data, args=(symbol,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Check results
        successful_requests = 0
        while not results.empty():
            symbol, response = results.get()
            if response.get("success", False):
                successful_requests += 1
        
        # Assertions
        assert successful_requests >= len(symbols) * 0.8, "At least 80% of requests should succeed"
        assert total_time < 10.0, f"Concurrent requests should complete in under 10 seconds, was {total_time:.2f}s"


class TestErrorHandling:
    """Error handling tests for InsiteChart platform."""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API client for testing."""
        base_url = os.getenv("TEST_API_URL", "http://localhost:8000/api/v1")
        return InsiteChartAPIClient(base_url)
    
    def test_invalid_symbol(self, api_client):
        """Test handling of invalid stock symbol."""
        invalid_symbol = "INVALID123"
        response = api_client.get_stock_data(invalid_symbol)
        
        # Should handle invalid symbol gracefully
        assert not response.get("success", True), "Invalid symbol should not succeed"
        assert "error" in response, "Should return error message"
    
    def test_empty_search_query(self, api_client):
        """Test handling of empty search query."""
        response = api_client.search_stocks("", limit=5)
        
        # Should handle empty query gracefully
        # API might either succeed with empty results or fail with error
        if response.get("success", False):
            data = response.get("data", {})
            if "results" in data:
                assert len(data["results"]) == 0, "Empty search should return no results"
    
    def test_nonexistent_watchlist(self, api_client):
        """Test getting watchlist for non-existent user."""
        response = api_client.get_user_watchlist("nonexistent_user")
        
        # Should handle non-existent user gracefully
        assert response.get("success", False), "Non-existent user should not have watchlist"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])