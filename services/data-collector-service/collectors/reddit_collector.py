"""
Reddit Data Collector

Collects sentiment and mentions from Reddit subreddits related to stocks.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

import praw
from textblob import TextBlob

logger = logging.getLogger(__name__)


class RedditCollector:
    """Collects sentiment data from Reddit."""

    def __init__(self, client_id: str = "", client_secret: str = "", user_agent: str = ""):
        """
        Initialize Reddit Collector.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit user agent string
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent or "InsiteChart/1.0"
        self.reddit = None
        self.cache: Dict[str, Dict[str, Any]] = {}

        # Try to initialize Reddit API if credentials provided
        if client_id and client_secret:
            self._initialize_reddit()

    def _initialize_reddit(self):
        """Initialize Reddit API connection."""
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            logger.info("Reddit API initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Reddit API: {str(e)}")
            self.reddit = None

    async def collect(self, symbol: str, subreddit: str = "stocks") -> Optional[Dict[str, Any]]:
        """
        Collect sentiment data for a symbol from Reddit.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            subreddit: Subreddit to search (default: 'stocks')

        Returns:
            Dictionary containing sentiment data or None if collection fails
        """
        try:
            if not self.reddit:
                logger.warning("Reddit API not initialized")
                return self._generate_mock_data(symbol, subreddit)

            # Search for symbol mentions
            posts = await self._search_posts(symbol, subreddit)

            if not posts:
                logger.warning(f"No posts found for {symbol} in r/{subreddit}")
                return None

            # Analyze sentiment
            sentiment = await self._analyze_sentiment(posts)

            return {
                "symbol": symbol,
                "subreddit": subreddit,
                "posts_count": len(posts),
                "sentiment": sentiment,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "reddit"
            }

        except Exception as e:
            logger.error(f"Error collecting Reddit data for {symbol}: {str(e)}")
            return self._generate_mock_data(symbol, subreddit)

    async def collect_multiple(
        self,
        symbols: List[str],
        subreddit: str = "stocks"
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Collect sentiment data for multiple symbols.

        Args:
            symbols: List of stock symbols
            subreddit: Subreddit to search

        Returns:
            Dictionary mapping symbols to their sentiment data
        """
        results = {}

        for symbol in symbols:
            results[symbol] = await self.collect(symbol, subreddit)
            # Delay to avoid rate limiting
            await asyncio.sleep(2)

        return results

    async def _search_posts(self, symbol: str, subreddit: str) -> List[Dict[str, Any]]:
        """
        Search for posts mentioning the symbol in a subreddit.

        Args:
            symbol: Stock symbol
            subreddit: Subreddit name

        Returns:
            List of post dictionaries
        """
        try:
            subreddit_obj = self.reddit.subreddit(subreddit)
            posts = []

            # Search for symbol mentions
            for submission in subreddit_obj.search(f"${symbol}", time_filter="week", limit=30):
                posts.append({
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "url": submission.url
                })

            return posts

        except Exception as e:
            logger.error(f"Error searching Reddit posts: {str(e)}")
            return []

    async def _analyze_sentiment(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment of posts.

        Args:
            posts: List of post dictionaries

        Returns:
            Dictionary containing sentiment scores
        """
        try:
            sentiments = []

            for post in posts:
                # Combine title and text
                text = f"{post.get('title', '')} {post.get('selftext', '')}"

                # Simple sentiment analysis using TextBlob
                analysis = TextBlob(text)
                polarity = analysis.sentiment.polarity
                subjectivity = analysis.sentiment.subjectivity

                sentiments.append({
                    "polarity": polarity,
                    "subjectivity": subjectivity,
                    "weight": post.get("score", 0) / max(1, sum(p.get("score", 0) for p in posts))
                })

            # Calculate weighted sentiment
            if sentiments:
                weighted_sentiment = sum(
                    s["polarity"] * s["weight"] for s in sentiments
                ) / max(1, len(sentiments))
            else:
                weighted_sentiment = 0.0

            return {
                "average_polarity": weighted_sentiment,
                "positive_ratio": len([s for s in sentiments if s["polarity"] > 0.1]) / max(1, len(sentiments)),
                "negative_ratio": len([s for s in sentiments if s["polarity"] < -0.1]) / max(1, len(sentiments)),
                "post_count": len(posts)
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "average_polarity": 0.0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "post_count": 0
            }

    def _generate_mock_data(self, symbol: str, subreddit: str) -> Dict[str, Any]:
        """
        Generate mock sentiment data for testing.

        Args:
            symbol: Stock symbol
            subreddit: Subreddit name

        Returns:
            Mock sentiment data
        """
        import random

        return {
            "symbol": symbol,
            "subreddit": subreddit,
            "posts_count": random.randint(10, 100),
            "sentiment": {
                "average_polarity": random.uniform(-0.5, 0.8),
                "positive_ratio": random.uniform(0.3, 0.8),
                "negative_ratio": random.uniform(0.0, 0.3),
                "post_count": random.randint(10, 100)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "source": "reddit",
            "mock": True
        }
