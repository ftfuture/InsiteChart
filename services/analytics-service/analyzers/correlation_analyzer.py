"""Correlation analysis for stocks."""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Analyze correlations between stocks."""

    # Period mappings to days
    PERIOD_DAYS = {
        "1d": 1,
        "1w": 7,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "ytd": 365  # Year-to-date
    }

    def __init__(self, redis_client=None):
        """Initialize correlation analyzer.

        Args:
            redis_client: Optional Redis client for caching
        """
        self.redis_client = redis_client

    def get_price_data(
        self,
        symbols: List[str],
        days: int = 30
    ) -> pd.DataFrame:
        """Get historical price data for symbols.

        In real implementation, this would fetch from data provider.
        For now, returns simulated data for testing.

        Args:
            symbols: List of stock symbols
            days: Number of historical days to fetch

        Returns:
            DataFrame with date as index and symbols as columns
        """
        # Simulated price data for demonstration
        # In production, fetch from Yahoo Finance, Alpha Vantage, etc.
        np.random.seed(42)  # For reproducibility

        dates = pd.date_range(end=datetime.utcnow(), periods=days, freq='D')
        data = {}

        for symbol in symbols:
            # Generate correlated price data
            price = 100 + np.cumsum(np.random.normal(0.5, 2, days))
            data[symbol] = price

        return pd.DataFrame(data, index=dates)

    def calculate_correlation_matrix(
        self,
        symbols: List[str],
        period: str = "1mo"
    ) -> Tuple[List[List[float]], np.ndarray]:
        """Calculate Pearson correlation matrix for symbols.

        Args:
            symbols: List of stock symbols
            period: Time period (1d, 1w, 1mo, 3mo, 6mo, 1y)

        Returns:
            Tuple of (correlation matrix as list, numpy array)
        """
        if not symbols or len(symbols) < 2:
            raise ValueError("At least 2 symbols required")

        # Get period in days
        days = self.PERIOD_DAYS.get(period, 30)

        # Get price data
        price_data = self.get_price_data(symbols, days)

        # Calculate returns (percent change)
        returns = price_data.pct_change().dropna()

        # Calculate correlation matrix
        corr_matrix = returns.corr(method='pearson')

        # Convert to list for JSON serialization
        corr_list = corr_matrix.values.tolist()

        return corr_list, corr_matrix.values

    def find_strong_pairs(
        self,
        corr_matrix: np.ndarray,
        symbols: List[str],
        threshold: float = 0.7
    ) -> List[Dict[str, any]]:
        """Find pairs with strong correlation.

        Args:
            corr_matrix: Correlation matrix (numpy array)
            symbols: List of stock symbols (same order as matrix)
            threshold: Minimum absolute correlation coefficient

        Returns:
            List of strongly correlated pairs with details
        """
        pairs = []

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                coef = corr_matrix[i, j]

                if abs(coef) >= threshold:
                    # Calculate p-value for correlation significance
                    p_value = self._calculate_p_value(coef, len(corr_matrix))

                    pairs.append({
                        "symbol1": symbols[i],
                        "symbol2": symbols[j],
                        "coefficient": round(float(coef), 4),
                        "p_value": round(float(p_value), 6),
                        "strength": self._get_correlation_strength(coef)
                    })

        # Sort by absolute coefficient (strongest first)
        pairs.sort(key=lambda x: abs(x["coefficient"]), reverse=True)

        return pairs

    def find_weak_pairs(
        self,
        corr_matrix: np.ndarray,
        symbols: List[str],
        threshold: float = 0.3
    ) -> List[Dict[str, any]]:
        """Find pairs with weak correlation (uncorrelated/diversifying).

        Args:
            corr_matrix: Correlation matrix (numpy array)
            symbols: List of stock symbols
            threshold: Maximum absolute correlation coefficient

        Returns:
            List of weakly correlated pairs
        """
        pairs = []

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                coef = corr_matrix[i, j]

                if abs(coef) <= threshold:
                    p_value = self._calculate_p_value(coef, len(corr_matrix))

                    pairs.append({
                        "symbol1": symbols[i],
                        "symbol2": symbols[j],
                        "coefficient": round(float(coef), 4),
                        "p_value": round(float(p_value), 6),
                        "strength": "uncorrelated" if abs(coef) < 0.1 else "weak"
                    })

        # Sort by absolute coefficient (weakest first)
        pairs.sort(key=lambda x: abs(x["coefficient"]))

        return pairs[:10]  # Limit to top 10 weakest pairs

    def analyze(
        self,
        symbols: List[str],
        period: str = "1mo",
        include_market: bool = True
    ) -> Dict[str, any]:
        """Analyze correlations between stocks.

        Args:
            symbols: List of stock symbols
            period: Time period for analysis
            include_market: Include market index (SPY)

        Returns:
            Dictionary with correlation analysis results
        """
        # Validate inputs
        if not symbols:
            raise ValueError("At least one symbol required")

        if len(symbols) < 2:
            raise ValueError("At least 2 symbols required for correlation")

        if len(symbols) > 50:
            raise ValueError("Maximum 50 symbols allowed")

        if period not in self.PERIOD_DAYS:
            raise ValueError(f"Invalid period. Valid values: {list(self.PERIOD_DAYS.keys())}")

        # Add market index if requested
        analysis_symbols = symbols.copy()
        if include_market and "SPY" not in analysis_symbols:
            analysis_symbols.append("SPY")

        try:
            # Calculate correlation matrix
            corr_list, corr_matrix = self.calculate_correlation_matrix(
                analysis_symbols,
                period
            )

            # Find strong and weak pairs
            strong_pairs = self.find_strong_pairs(corr_matrix, analysis_symbols, threshold=0.7)
            weak_pairs = self.find_weak_pairs(corr_matrix, analysis_symbols, threshold=0.3)

            # Return only requested symbols in results (exclude SPY if it wasn't requested)
            result_symbols = symbols if not include_market else analysis_symbols

            return {
                "symbols": symbols,  # Original symbols requested
                "period": period,
                "correlation_matrix": corr_list[:len(symbols)][:len(symbols)],  # Trim to original symbols
                "strong_pairs": strong_pairs,
                "weak_pairs": weak_pairs,
                "statistics": {
                    "mean_correlation": round(float(np.mean(np.abs(corr_matrix[corr_matrix != 1]))), 4),
                    "max_correlation": round(float(np.max(corr_matrix[corr_matrix != 1])), 4),
                    "min_correlation": round(float(np.min(corr_matrix[corr_matrix != 1])), 4)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            raise

    def rolling_correlation(
        self,
        symbols: List[str],
        window_days: int = 30,
        period: str = "1mo"
    ) -> Dict[str, any]:
        """Calculate rolling correlation over time.

        Args:
            symbols: List of stock symbols
            window_days: Window size for rolling calculation
            period: Total period for analysis

        Returns:
            Dictionary with rolling correlation time series
        """
        if len(symbols) < 2:
            raise ValueError("At least 2 symbols required")

        # Get period in days
        total_days = self.PERIOD_DAYS.get(period, 30)

        # Get price data
        price_data = self.get_price_data(symbols, total_days)
        returns = price_data.pct_change().dropna()

        # Calculate rolling correlation
        rolling_corr = returns[symbols[0]].rolling(window=window_days).corr(
            returns[symbols[1]] if len(symbols) > 1 else returns[symbols[0]]
        )

        return {
            "symbols": symbols,
            "window_days": window_days,
            "period": period,
            "rolling_correlation": rolling_corr.dropna().tolist(),
            "timestamps": rolling_corr.index.tolist(),
            "mean_correlation": round(float(rolling_corr.mean()), 4),
            "min_correlation": round(float(rolling_corr.min()), 4),
            "max_correlation": round(float(rolling_corr.max()), 4)
        }

    def _calculate_p_value(self, r: float, n: int) -> float:
        """Calculate p-value for Pearson correlation.

        Args:
            r: Correlation coefficient
            n: Sample size

        Returns:
            P-value
        """
        # Avoid division by zero
        if r >= 1.0 or r <= -1.0:
            return 0.0

        t_stat = r * np.sqrt(n - 2) / np.sqrt(1 - r ** 2)
        from scipy.stats import t
        p_value = 2 * (1 - t.cdf(abs(t_stat), n - 2))
        return float(p_value)

    def _get_correlation_strength(self, coef: float) -> str:
        """Get human-readable correlation strength description.

        Args:
            coef: Correlation coefficient

        Returns:
            Strength description
        """
        abs_coef = abs(coef)

        if abs_coef >= 0.9:
            return "very_strong"
        elif abs_coef >= 0.7:
            return "strong"
        elif abs_coef >= 0.5:
            return "moderate"
        elif abs_coef >= 0.3:
            return "weak"
        else:
            return "very_weak"
