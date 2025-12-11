"""
Yahoo Finance Data Collector

Collects stock price, volume, and market data from Yahoo Finance.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class YahooFinanceCollector:
    """Collects stock data from Yahoo Finance."""

    def __init__(self, cache_ttl: int = 300):
        """
        Initialize Yahoo Finance Collector.

        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}

    async def collect(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Collect stock data for a symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dictionary containing stock data or None if collection fails
        """
        try:
            # Check cache first
            if self._is_cached(symbol):
                logger.debug(f"Using cached data for {symbol}")
                return self.cache[symbol]

            # Fetch from Yahoo Finance
            data = await self._fetch_stock_data(symbol)

            if data:
                # Cache the data
                self.cache[symbol] = data
                self.cache_timestamps[symbol] = datetime.utcnow()
                logger.info(f"Successfully collected data for {symbol}")
                return data
            else:
                logger.warning(f"No data returned for symbol {symbol}")
                return None

        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {str(e)}")
            return None

    async def collect_multiple(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Collect stock data for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to their data
        """
        results = {}

        for symbol in symbols:
            results[symbol] = await self.collect(symbol)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

        return results

    async def _fetch_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch stock data from Yahoo Finance.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary containing stock data
        """
        try:
            # Create ticker object
            ticker = yf.Ticker(symbol)

            # Fetch historical data (last 1 day)
            hist = ticker.history(period="1d")

            if hist.empty:
                logger.warning(f"No historical data for {symbol}")
                return None

            # Get the latest data point
            latest = hist.iloc[-1]

            # Get info
            info = ticker.info

            return {
                "symbol": symbol,
                "price": float(latest.get("Close", 0)),
                "open": float(latest.get("Open", 0)),
                "high": float(latest.get("High", 0)),
                "low": float(latest.get("Low", 0)),
                "volume": int(latest.get("Volume", 0)),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "52_week_high": info.get("fiftyTwoWeekHigh", 0),
                "52_week_low": info.get("fiftyTwoWeekLow", 0),
                "avg_volume_30d": info.get("averageVolume", 0),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "source": "yahoo_finance"
            }

        except Exception as e:
            logger.error(f"Error fetching data from Yahoo Finance for {symbol}: {str(e)}")
            return None

    def _is_cached(self, symbol: str) -> bool:
        """
        Check if data is cached and not expired.

        Args:
            symbol: Stock symbol

        Returns:
            True if cached and not expired, False otherwise
        """
        if symbol not in self.cache or symbol not in self.cache_timestamps:
            return False

        cache_age = (datetime.utcnow() - self.cache_timestamps[symbol]).total_seconds()
        return cache_age < self.cache_ttl

    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_symbols": len(self.cache),
            "cache_ttl": self.cache_ttl,
            "symbols": list(self.cache.keys())
        }
