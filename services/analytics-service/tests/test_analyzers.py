"""Unit tests for Analytics Service analyzers."""

import pytest
from datetime import datetime

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.correlation_analyzer import CorrelationAnalyzer
from analyzers.trend_analyzer import TrendAnalyzer


class TestSentimentAnalyzer:
    """Test Sentiment Analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create sentiment analyzer instance."""
        return SentimentAnalyzer()

    def test_analyze_positive_text(self, analyzer):
        """Test positive sentiment detection."""
        result = analyzer.analyze("Apple's new iPhone is amazing!", model="vader")

        assert result["sentiment"] == "positive"
        assert result["positive"] > 0.5
        assert result["compound"] > 0

    def test_analyze_negative_text(self, analyzer):
        """Test negative sentiment detection."""
        result = analyzer.analyze("Stock crash is terrible", model="vader")

        assert result["sentiment"] == "negative"
        assert result["negative"] > 0.5
        assert result["compound"] < 0

    def test_analyze_neutral_text(self, analyzer):
        """Test neutral sentiment detection."""
        result = analyzer.analyze("The stock price is 150", model="vader")

        assert result["sentiment"] == "neutral"
        assert abs(result["compound"]) < 0.1

    def test_analyze_ensemble(self, analyzer):
        """Test ensemble model."""
        result = analyzer.analyze("Great product launch", model="ensemble")

        assert "compound" in result
        assert "confidence" in result
        assert "model" in result
        assert result["model"] == "ensemble"

    def test_empty_text(self, analyzer):
        """Test empty text error handling."""
        with pytest.raises(ValueError):
            analyzer.analyze("", model="vader")

    def test_long_text_truncation(self, analyzer):
        """Test long text truncation."""
        long_text = "word " * 2000  # 10000+ characters
        result = analyzer.analyze(long_text, model="vader")

        assert "compound" in result

    def test_batch_analyze(self, analyzer):
        """Test batch analysis."""
        texts = [
            "Great product",
            "Terrible experience",
            "Average performance"
        ]

        results = analyzer.batch_analyze(texts, model="vader")

        assert len(results) == 3
        assert all("compound" in r for r in results)


class TestCorrelationAnalyzer:
    """Test Correlation Analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create correlation analyzer instance."""
        return CorrelationAnalyzer()

    def test_analyze_multiple_symbols(self, analyzer):
        """Test correlation analysis."""
        result = analyzer.analyze(
            symbols=["AAPL", "MSFT", "GOOGL"],
            period="1mo"
        )

        assert result["symbols"] == ["AAPL", "MSFT", "GOOGL"]
        assert len(result["correlation_matrix"]) == 3
        assert len(result["correlation_matrix"][0]) == 3

    def test_correlation_matrix_properties(self, analyzer):
        """Test correlation matrix properties."""
        result = analyzer.analyze(
            symbols=["AAPL", "MSFT"],
            period="1mo"
        )

        # Diagonal should be 1.0
        assert abs(result["correlation_matrix"][0][0] - 1.0) < 0.01
        assert abs(result["correlation_matrix"][1][1] - 1.0) < 0.01

        # Values between -1 and 1
        for row in result["correlation_matrix"]:
            for val in row:
                assert -1 <= val <= 1

    def test_strong_pairs_detection(self, analyzer):
        """Test strong pair detection."""
        result = analyzer.analyze(
            symbols=["AAPL", "MSFT", "GOOGL"],
            period="1mo"
        )

        # Should have some results
        assert isinstance(result["strong_pairs"], list)
        assert isinstance(result["weak_pairs"], list)

    def test_invalid_symbol_count(self, analyzer):
        """Test error with single symbol."""
        with pytest.raises(ValueError):
            analyzer.analyze(symbols=["AAPL"], period="1mo")

    def test_invalid_period(self, analyzer):
        """Test error with invalid period."""
        with pytest.raises(ValueError):
            analyzer.analyze(
                symbols=["AAPL", "MSFT"],
                period="invalid"
            )

    def test_too_many_symbols(self, analyzer):
        """Test error with too many symbols."""
        with pytest.raises(ValueError):
            symbols = [f"SYM{i}" for i in range(51)]
            analyzer.analyze(symbols=symbols, period="1mo")

    def test_rolling_correlation(self, analyzer):
        """Test rolling correlation calculation."""
        result = analyzer.rolling_correlation(
            symbols=["AAPL", "MSFT"],
            window_days=10,
            period="1mo"
        )

        assert result["symbols"] == ["AAPL", "MSFT"]
        assert "mean_correlation" in result


class TestTrendAnalyzer:
    """Test Trend Analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create trend analyzer instance."""
        return TrendAnalyzer()

    def test_analyze_single_symbol(self, analyzer):
        """Test trend analysis."""
        result = analyzer.analyze(
            symbol="AAPL",
            lookback_days=30
        )

        assert result["symbol"] == "AAPL"
        assert result["trend"] in ["uptrend", "downtrend", "sideways"]
        assert 0 <= result["strength"] <= 1

    def test_moving_averages(self, analyzer):
        """Test moving average calculation."""
        result = analyzer.analyze(
            symbol="AAPL",
            lookback_days=30
        )

        assert "moving_averages" in result
        assert "SMA_50" in result["moving_averages"]
        assert "SMA_200" in result["moving_averages"]

    def test_rsi_range(self, analyzer):
        """Test RSI is in valid range."""
        result = analyzer.analyze(
            symbol="AAPL",
            lookback_days=30
        )

        assert 0 <= result["rsi"] <= 100

    def test_support_resistance_levels(self, analyzer):
        """Test support and resistance level detection."""
        result = analyzer.analyze(
            symbol="AAPL",
            lookback_days=30
        )

        assert isinstance(result["support_levels"], list)
        assert isinstance(result["resistance_levels"], list)

    def test_anomaly_detection(self, analyzer):
        """Test anomaly detection."""
        result = analyzer.analyze(
            symbol="AAPL",
            lookback_days=30,
            include_anomalies=True
        )

        assert "anomalies" in result
        if result["anomalies"]:
            anomaly = result["anomalies"][0]
            assert "timestamp" in anomaly
            assert "price" in anomaly
            assert "magnitude" in anomaly
            assert "type" in anomaly

    def test_no_anomaly_flag(self, analyzer):
        """Test anomalies excluded when flag is False."""
        result = analyzer.analyze(
            symbol="AAPL",
            lookback_days=30,
            include_anomalies=False
        )

        assert result["anomalies"] is None

    def test_invalid_symbol(self, analyzer):
        """Test error with empty symbol."""
        with pytest.raises(ValueError):
            analyzer.analyze(symbol="", lookback_days=30)

    def test_invalid_lookback_days(self, analyzer):
        """Test error with invalid lookback days."""
        with pytest.raises(ValueError):
            analyzer.analyze(symbol="AAPL", lookback_days=2)

        with pytest.raises(ValueError):
            analyzer.analyze(symbol="AAPL", lookback_days=400)

    def test_batch_analyze(self, analyzer):
        """Test batch analysis."""
        results = analyzer.batch_analyze(
            symbols=["AAPL", "MSFT", "GOOGL"],
            lookback_days=30
        )

        assert len(results) == 3
        assert all("symbol" in r for r in results)

    def test_timestamp_format(self, analyzer):
        """Test timestamp is ISO format."""
        result = analyzer.analyze(symbol="AAPL", lookback_days=30)

        # Should be ISO format with Z suffix
        assert result["timestamp"].endswith("Z")
        # Parse to verify it's valid ISO
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))


class TestIntegration:
    """Integration tests."""

    def test_all_analyzers_initialize(self):
        """Test all analyzers can be initialized."""
        sentiment = SentimentAnalyzer()
        correlation = CorrelationAnalyzer()
        trend = TrendAnalyzer()

        assert sentiment is not None
        assert correlation is not None
        assert trend is not None

    def test_complete_workflow(self):
        """Test complete analysis workflow."""
        # Sentiment
        sentiment = SentimentAnalyzer()
        sentiment_result = sentiment.analyze(
            "Great stock performance",
            model="vader"
        )
        assert sentiment_result["sentiment"] == "positive"

        # Correlation
        correlation = CorrelationAnalyzer()
        corr_result = correlation.analyze(
            symbols=["AAPL", "MSFT"],
            period="1mo"
        )
        assert "correlation_matrix" in corr_result

        # Trend
        trend = TrendAnalyzer()
        trend_result = trend.analyze(
            symbol="AAPL",
            lookback_days=30
        )
        assert trend_result["trend"] in ["uptrend", "downtrend", "sideways"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
