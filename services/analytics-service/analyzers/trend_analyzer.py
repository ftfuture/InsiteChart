"""Trend analysis for stocks."""

import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyze price trends, support/resistance levels, and anomalies."""

    def __init__(self):
        """Initialize trend analyzer."""
        self.sma_periods = [50, 200]  # Standard SMA periods

    def get_simulated_price_data(
        self,
        symbol: str,
        days: int = 30,
        seed: int = None
    ) -> pd.DataFrame:
        """Get simulated historical price data.

        In production, this would fetch real data from a provider.

        Args:
            symbol: Stock symbol
            days: Number of historical days
            seed: Random seed for reproducibility

        Returns:
            DataFrame with OHLCV data
        """
        if seed is not None:
            np.random.seed(seed)

        dates = pd.date_range(end=datetime.utcnow(), periods=days, freq='D')

        # Generate realistic price movement
        price = 150  # Starting price
        prices = [price]
        volumes = []

        for i in range(1, days):
            # Random walk with slight uptrend
            change = np.random.normal(0.3, 2)  # Mean 0.3, std 2
            price = max(price + change, 50)  # Don't go below $50
            prices.append(price)
            volumes.append(np.random.randint(1000000, 5000000))

        prices = np.array(prices)

        return pd.DataFrame({
            "date": dates,
            "open": prices + np.random.normal(0, 0.5, days),
            "high": prices + np.random.uniform(0.5, 2, days),
            "low": prices - np.random.uniform(0.5, 2, days),
            "close": prices,
            "volume": volumes + [np.random.randint(1000000, 5000000)]
        }).set_index("date")

    def calculate_sma(
        self,
        prices: pd.Series,
        period: int
    ) -> pd.Series:
        """Calculate Simple Moving Average.

        Args:
            prices: Price series
            period: SMA period

        Returns:
            SMA series
        """
        return prices.rolling(window=period).mean()

    def calculate_rsi(
        self,
        prices: pd.Series,
        period: int = 14
    ) -> float:
        """Calculate Relative Strength Index.

        Args:
            prices: Price series
            period: RSI period (default 14)

        Returns:
            RSI value (0-100)
        """
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    def detect_trend(
        self,
        sma_50: float,
        sma_200: float,
        current_price: float,
        rsi: float
    ) -> Tuple[str, float]:
        """Detect trend based on moving averages and RSI.

        Args:
            sma_50: 50-day simple moving average
            sma_200: 200-day simple moving average
            current_price: Current price
            rsi: Relative Strength Index

        Returns:
            Tuple of (trend_direction, strength)
        """
        # Determine trend direction using crossover strategy
        if sma_50 > sma_200 and current_price > sma_50:
            trend = "uptrend"
            # Strength based on distance from SMA and RSI
            strength = min(0.95, (current_price - sma_50) / sma_50 + 0.3)
        elif sma_50 < sma_200 and current_price < sma_50:
            trend = "downtrend"
            # Strength based on distance from SMA (inverted)
            strength = min(0.95, (sma_50 - current_price) / sma_50 + 0.3)
        else:
            trend = "sideways"
            strength = 0.3  # Sideways trends are weak

        # Adjust strength based on RSI
        if trend == "uptrend" and rsi > 70:
            strength = min(strength + 0.1, 1.0)  # Overbought strengthens uptrend
        elif trend == "downtrend" and rsi < 30:
            strength = min(strength + 0.1, 1.0)  # Oversold strengthens downtrend

        return trend, round(float(strength), 4)

    def detect_support_resistance(
        self,
        prices: pd.Series,
        window: int = 20
    ) -> Tuple[List[float], List[float]]:
        """Detect support and resistance levels.

        Uses rolling min/max to identify price levels.

        Args:
            prices: Price series
            window: Rolling window for level detection

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        # Find recent lows (support) and highs (resistance)
        recent_prices = prices.tail(window * 3)

        rolling_min = recent_prices.rolling(window=window).min()
        rolling_max = recent_prices.rolling(window=window).max()

        # Get unique levels
        support_levels = sorted(set(rolling_min.dropna().round(2)))[-3:]  # Last 3 unique lows
        resistance_levels = sorted(set(rolling_max.dropna().round(2)))[-3:]  # Last 3 unique highs

        # Remove duplicates and very close values
        support_levels = [float(x) for x in support_levels if support_levels.count(x) == 1]
        resistance_levels = [float(x) for x in resistance_levels if resistance_levels.count(x) == 1]

        return support_levels, resistance_levels

    def detect_anomalies(
        self,
        prices: pd.Series,
        contamination: float = 0.05
    ) -> List[Dict[str, Any]]:
        """Detect price anomalies using Isolation Forest.

        Args:
            prices: Price series
            contamination: Expected proportion of anomalies (0-1)

        Returns:
            List of detected anomalies with timestamps and details
        """
        if len(prices) < 10:
            return []

        # Prepare data for Isolation Forest
        price_array = prices.values.reshape(-1, 1)

        # Detect anomalies
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        anomaly_labels = iso_forest.fit_predict(price_array)

        # Extract anomalies
        anomalies = []
        anomaly_scores = iso_forest.score_samples(price_array)

        for idx, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
            if label == -1:  # -1 indicates anomaly
                # Calculate magnitude in standard deviations
                mean_price = np.mean(prices)
                std_price = np.std(prices)
                magnitude = abs(prices.iloc[idx] - mean_price) / std_price if std_price > 0 else 0

                # Determine anomaly type
                if prices.iloc[idx] > mean_price:
                    anomaly_type = "spike"
                else:
                    anomaly_type = "drop"

                anomalies.append({
                    "timestamp": prices.index[idx].isoformat() + "Z",
                    "price": round(float(prices.iloc[idx]), 2),
                    "magnitude": round(float(magnitude), 2),
                    "type": anomaly_type,
                    "anomaly_score": round(float(score), 4)
                })

        return sorted(anomalies, key=lambda x: abs(x["magnitude"]), reverse=True)[:10]

    def analyze(
        self,
        symbol: str,
        lookback_days: int = 30,
        include_anomalies: bool = True
    ) -> Dict[str, Any]:
        """Analyze trend for a stock.

        Args:
            symbol: Stock symbol
            lookback_days: Historical data lookback period
            include_anomalies: Include anomaly detection

        Returns:
            Dictionary with trend analysis results
        """
        # Validate inputs
        if not symbol or len(symbol.strip()) == 0:
            raise ValueError("Symbol cannot be empty")

        if lookback_days < 5 or lookback_days > 365:
            raise ValueError("lookback_days must be between 5 and 365")

        try:
            # Get price data
            df = self.get_simulated_price_data(symbol, lookback_days, seed=42)

            # Get close prices
            close_prices = df["close"]

            # Calculate moving averages
            sma_50 = self.calculate_sma(close_prices, 50)
            sma_200 = self.calculate_sma(close_prices, 200)

            # Get latest values
            current_price = float(close_prices.iloc[-1])
            sma_50_value = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else current_price
            sma_200_value = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else current_price

            # Calculate RSI
            rsi = self.calculate_rsi(close_prices)

            # Detect trend
            trend, strength = self.detect_trend(sma_50_value, sma_200_value, current_price, rsi)

            # Detect support and resistance
            support_levels, resistance_levels = self.detect_support_resistance(close_prices)

            # Detect anomalies
            anomalies = []
            if include_anomalies and lookback_days >= 20:
                anomalies = self.detect_anomalies(close_prices)

            return {
                "symbol": symbol,
                "trend": trend,
                "strength": strength,
                "current_price": round(current_price, 2),
                "support_levels": [round(x, 2) for x in support_levels],
                "resistance_levels": [round(x, 2) for x in resistance_levels],
                "moving_averages": {
                    "SMA_50": round(sma_50_value, 2),
                    "SMA_200": round(sma_200_value, 2)
                },
                "rsi": round(rsi, 2),
                "anomalies": anomalies if include_anomalies else None,
                "lookback_days": lookback_days,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            logger.error(f"Trend analysis failed for {symbol}: {e}")
            raise

    def batch_analyze(
        self,
        symbols: List[str],
        lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Analyze trends for multiple stocks.

        Args:
            symbols: List of stock symbols
            lookback_days: Historical data lookback period

        Returns:
            List of trend analysis results
        """
        results = []
        for symbol in symbols:
            try:
                result = self.analyze(symbol, lookback_days)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        return results
