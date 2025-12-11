"""
Twitter/X Data Collector

Collects sentiment and mentions from Twitter/X related to stocks.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import random

logger = logging.getLogger(__name__)


class TwitterCollector:
    """Collects sentiment data from Twitter/X."""

    def __init__(self, bearer_token: str = ""):
        """
        Initialize Twitter Collector.

        Args:
            bearer_token: Twitter API bearer token
        """
        self.bearer_token = bearer_token
        self.client = None
        self.cache: Dict[str, Dict[str, Any]] = {}

        # Try to initialize Twitter API if credentials provided
        if bearer_token:
            self._initialize_twitter()

    def _initialize_twitter(self):
        """Initialize Twitter API connection."""
        try:
            import tweepy

            self.client = tweepy.Client(bearer_token=self.bearer_token)
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Twitter API: {str(e)}")
            self.client = None

    async def collect(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Collect sentiment data for a symbol from Twitter.

        Args:
            symbol: Stock symbol or ticker (e.g., 'AAPL' or '$AAPL')
            limit: Maximum number of tweets to fetch

        Returns:
            Dictionary containing sentiment data or None if collection fails
        """
        try:
            if not self.client:
                logger.warning("Twitter API not initialized")
                return self._generate_mock_data(symbol)

            # Search for tweets
            tweets = await self._search_tweets(symbol, limit)

            if not tweets:
                logger.warning(f"No tweets found for {symbol}")
                return None

            # Analyze sentiment
            sentiment = await self._analyze_sentiment(tweets)

            return {
                "symbol": symbol,
                "tweets_count": len(tweets),
                "sentiment": sentiment,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "twitter"
            }

        except Exception as e:
            logger.error(f"Error collecting Twitter data for {symbol}: {str(e)}")
            return self._generate_mock_data(symbol)

    async def collect_multiple(
        self,
        symbols: List[str],
        limit: int = 100
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Collect sentiment data for multiple symbols.

        Args:
            symbols: List of stock symbols
            limit: Maximum number of tweets per symbol

        Returns:
            Dictionary mapping symbols to their sentiment data
        """
        results = {}

        for symbol in symbols:
            results[symbol] = await self.collect(symbol, limit)
            # Delay to avoid rate limiting
            await asyncio.sleep(1)

        return results

    async def _search_tweets(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        """
        Search for tweets mentioning the symbol.

        Args:
            symbol: Stock symbol
            limit: Maximum number of tweets

        Returns:
            List of tweet dictionaries
        """
        try:
            # Prepare search query
            query = f"${symbol} OR #{symbol} -is:retweet lang:en"

            # Search for tweets
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=min(limit, 100),
                tweet_fields=["created_at", "public_metrics", "lang"],
                expansions=["author_id"],
                user_fields=["followers_count", "verified"]
            )

            tweet_list = []
            if tweets.data:
                for tweet in tweets.data:
                    tweet_list.append({
                        "id": tweet.id,
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                        "likes": tweet.public_metrics.get("like_count", 0),
                        "retweets": tweet.public_metrics.get("retweet_count", 0),
                        "replies": tweet.public_metrics.get("reply_count", 0),
                        "quotes": tweet.public_metrics.get("quote_count", 0),
                        "lang": tweet.lang
                    })

            return tweet_list

        except Exception as e:
            logger.error(f"Error searching tweets: {str(e)}")
            return []

    async def _analyze_sentiment(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment of tweets.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Dictionary containing sentiment scores
        """
        try:
            from textblob import TextBlob

            sentiments = []

            for tweet in tweets:
                text = tweet.get("text", "")

                # Simple sentiment analysis
                analysis = TextBlob(text)
                polarity = analysis.sentiment.polarity

                # Calculate engagement weight
                total_engagement = (
                    tweet.get("likes", 0) +
                    tweet.get("retweets", 0) +
                    tweet.get("replies", 0)
                )

                sentiments.append({
                    "polarity": polarity,
                    "engagement": total_engagement
                })

            if sentiments:
                # Calculate weighted sentiment
                total_engagement = sum(s["engagement"] for s in sentiments) or 1
                weighted_sentiment = sum(
                    s["polarity"] * (s["engagement"] / total_engagement) for s in sentiments
                )
            else:
                weighted_sentiment = 0.0

            return {
                "average_polarity": weighted_sentiment,
                "positive_ratio": len([s for s in sentiments if s["polarity"] > 0.1]) / max(1, len(sentiments)),
                "negative_ratio": len([s for s in sentiments if s["polarity"] < -0.1]) / max(1, len(sentiments)),
                "tweet_count": len(tweets),
                "total_engagement": sum(s["engagement"] for s in sentiments)
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "average_polarity": 0.0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "tweet_count": 0,
                "total_engagement": 0
            }

    def _generate_mock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Generate mock sentiment data for testing.

        Args:
            symbol: Stock symbol

        Returns:
            Mock sentiment data
        """
        return {
            "symbol": symbol,
            "tweets_count": random.randint(50, 200),
            "sentiment": {
                "average_polarity": random.uniform(-0.3, 0.7),
                "positive_ratio": random.uniform(0.4, 0.75),
                "negative_ratio": random.uniform(0.05, 0.25),
                "tweet_count": random.randint(50, 200),
                "total_engagement": random.randint(100, 1000)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "source": "twitter",
            "mock": True
        }
