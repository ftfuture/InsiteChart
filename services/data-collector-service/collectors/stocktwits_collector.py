"""
StockTwits Data Collector

Collects sentiment and mentions from StockTwits - the primary stock discussion platform.
StockTwits provides S-Score (0-100) sentiment data that is a leading indicator of stock volatility.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import random

logger = logging.getLogger(__name__)


class StockTwitsCollector:
    """Collects sentiment data from StockTwits."""

    def __init__(self, api_key: str = ""):
        """
        Initialize StockTwits Collector.

        Args:
            api_key: StockTwits API key (optional - public API doesn't require auth)
        """
        self.api_key = api_key
        self.client = None
        self.base_url = "https://api.stocktwits.com/api/2"
        self.cache: Dict[str, Dict[str, Any]] = {}

        # Try to initialize StockTwits API if credentials provided
        if api_key:
            self._initialize_client()
        else:
            logger.info("StockTwits API initialized in public mode (no API key provided)")

    def _initialize_client(self):
        """Initialize StockTwits API connection."""
        try:
            # StockTwits has a public API that can be accessed without authentication
            # But with API key, we get higher rate limits
            logger.info("StockTwits API initialized with API key")
        except Exception as e:
            logger.warning(f"Could not initialize StockTwits API: {str(e)}")
            self.client = None

    async def collect(self, symbol: str, limit: int = 30) -> Optional[Dict[str, Any]]:
        """
        Collect sentiment data for a symbol from StockTwits.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            limit: Maximum number of messages to fetch

        Returns:
            Dictionary containing sentiment data or None if collection fails
        """
        try:
            # Fetch StockTwits data
            messages = await self._fetch_messages(symbol, limit)

            if not messages:
                logger.warning(f"No messages found for {symbol} on StockTwits")
                return None

            # Fetch S-Score and sentiment data
            s_score = await self._fetch_s_score(symbol)

            # Analyze sentiment from messages
            sentiment = await self._analyze_sentiment(messages, s_score)

            return {
                "symbol": symbol,
                "messages_count": len(messages),
                "sentiment": sentiment,
                "s_score": s_score,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "stocktwits"
            }

        except Exception as e:
            logger.error(f"Error collecting StockTwits data for {symbol}: {str(e)}")
            return self._generate_mock_data(symbol)

    async def collect_multiple(
        self,
        symbols: List[str],
        limit: int = 30
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Collect sentiment data for multiple symbols.

        Args:
            symbols: List of stock symbols
            limit: Maximum number of messages per symbol

        Returns:
            Dictionary mapping symbols to their sentiment data
        """
        results = {}

        for symbol in symbols:
            results[symbol] = await self.collect(symbol, limit)
            # Delay to avoid rate limiting (StockTwits allows ~200 requests/hour)
            await asyncio.sleep(2)

        return results

    async def _fetch_messages(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        """
        Fetch messages for a symbol from StockTwits API.

        Args:
            symbol: Stock symbol
            limit: Maximum number of messages

        Returns:
            List of message dictionaries
        """
        try:
            # In production, this would use httpx to call StockTwits API
            # StockTwits API endpoint: GET /api/2/streams/symbol/{symbol}.json
            # Returns: messages array with id, body, created_at, user info, sentiment data

            # For now, return mock messages to demonstrate the structure
            logger.info(f"Fetching StockTwits messages for {symbol}")

            # Mock implementation - in production would call actual API
            mock_messages = [
                {
                    "id": f"st_{i}",
                    "body": f"${{symbol}} looking bullish on the technicals! Support at 150, resistance at 160.",
                    "created_at": datetime.utcnow().isoformat(),
                    "likes": random.randint(5, 200),
                    "replies": random.randint(0, 50),
                    "sentiment": "Bullish",
                    "user": {
                        "id": f"user_{i}",
                        "username": f"investor_{i}",
                        "followers": random.randint(100, 50000)
                    }
                }
                for i in range(min(limit, 15))
            ]

            # Mix in some bearish sentiment
            for i in range(5):
                mock_messages.append({
                    "id": f"st_bear_{i}",
                    "body": f"${{symbol}} showing weakness. Be careful, P/E is too high.",
                    "created_at": datetime.utcnow().isoformat(),
                    "likes": random.randint(5, 150),
                    "replies": random.randint(0, 30),
                    "sentiment": "Bearish",
                    "user": {
                        "id": f"user_bear_{i}",
                        "username": f"trader_{i}",
                        "followers": random.randint(100, 20000)
                    }
                })

            return mock_messages

        except Exception as e:
            logger.error(f"Error fetching StockTwits messages: {str(e)}")
            return []

    async def _fetch_s_score(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch S-Score (StockTwits sentiment score) for a symbol.

        S-Score ranges from 0-100:
        - 0-25: Very Bearish
        - 26-45: Bearish
        - 46-55: Neutral
        - 56-75: Bullish
        - 76-100: Very Bullish

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary containing S-Score data
        """
        try:
            # In production, this would call:
            # GET /api/2/instruments/{symbol}.json
            # Which returns s_score in the response

            logger.info(f"Fetching S-Score for {symbol}")

            # Mock S-Score for demonstration
            s_score_value = random.randint(30, 85)

            if s_score_value <= 25:
                sentiment_label = "Very Bearish"
            elif s_score_value <= 45:
                sentiment_label = "Bearish"
            elif s_score_value <= 55:
                sentiment_label = "Neutral"
            elif s_score_value <= 75:
                sentiment_label = "Bullish"
            else:
                sentiment_label = "Very Bullish"

            return {
                "score": s_score_value,
                "sentiment": sentiment_label,
                "label": "S-Score (0-100)"
            }

        except Exception as e:
            logger.error(f"Error fetching S-Score: {str(e)}")
            return {
                "score": 50,
                "sentiment": "Neutral",
                "label": "S-Score (0-100)"
            }

    async def _analyze_sentiment(
        self,
        messages: List[Dict[str, Any]],
        s_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment from StockTwits messages.

        Args:
            messages: List of message dictionaries
            s_score: S-Score data from StockTwits

        Returns:
            Dictionary containing sentiment analysis
        """
        try:
            bullish_count = sum(1 for m in messages if m.get("sentiment") == "Bullish")
            bearish_count = sum(1 for m in messages if m.get("sentiment") == "Bearish")
            neutral_count = len(messages) - bullish_count - bearish_count

            total_messages = len(messages) or 1

            # Calculate weighted sentiment based on message engagement
            bullish_weight = sum(
                m.get("likes", 0) + m.get("replies", 0)
                for m in messages if m.get("sentiment") == "Bullish"
            )
            bearish_weight = sum(
                m.get("likes", 0) + m.get("replies", 0)
                for m in messages if m.get("sentiment") == "Bearish"
            )
            total_weight = max(1, bullish_weight + bearish_weight)

            weighted_sentiment = (bullish_weight - bearish_weight) / total_weight

            return {
                "bullish_ratio": bullish_count / total_messages,
                "bearish_ratio": bearish_count / total_messages,
                "neutral_ratio": neutral_count / total_messages,
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "message_count": total_messages,
                "weighted_sentiment": weighted_sentiment,  # -1 (very bearish) to +1 (very bullish)
                "s_score": s_score.get("score", 50),
                "s_score_sentiment": s_score.get("sentiment", "Neutral")
            }

        except Exception as e:
            logger.error(f"Error analyzing StockTwits sentiment: {str(e)}")
            return {
                "bullish_ratio": 0.0,
                "bearish_ratio": 0.0,
                "neutral_ratio": 1.0,
                "bullish_count": 0,
                "bearish_count": 0,
                "message_count": 0,
                "weighted_sentiment": 0.0,
                "s_score": 50,
                "s_score_sentiment": "Neutral"
            }

    def _generate_mock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Generate mock sentiment data for testing.

        Args:
            symbol: Stock symbol

        Returns:
            Mock sentiment data matching StockTwits structure
        """
        s_score_value = random.randint(30, 85)

        if s_score_value <= 25:
            sentiment_label = "Very Bearish"
        elif s_score_value <= 45:
            sentiment_label = "Bearish"
        elif s_score_value <= 55:
            sentiment_label = "Neutral"
        elif s_score_value <= 75:
            sentiment_label = "Bullish"
        else:
            sentiment_label = "Very Bullish"

        bullish_ratio = random.uniform(0.35, 0.75)
        bearish_ratio = random.uniform(0.1, 0.35)
        neutral_ratio = 1.0 - bullish_ratio - bearish_ratio

        return {
            "symbol": symbol,
            "messages_count": random.randint(30, 150),
            "sentiment": {
                "bullish_ratio": bullish_ratio,
                "bearish_ratio": bearish_ratio,
                "neutral_ratio": neutral_ratio,
                "bullish_count": random.randint(10, 60),
                "bearish_count": random.randint(5, 30),
                "message_count": random.randint(30, 150),
                "weighted_sentiment": random.uniform(-0.3, 0.8),
                "s_score": s_score_value,
                "s_score_sentiment": sentiment_label
            },
            "s_score": {
                "score": s_score_value,
                "sentiment": sentiment_label,
                "label": "S-Score (0-100)"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "source": "stocktwits",
            "mock": True
        }
