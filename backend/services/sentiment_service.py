"""
Sentiment analysis service for InsiteChart platform.

This service handles social media data collection, sentiment analysis,
and trend detection for stocks.
"""

import asyncio
import aiohttp
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from ..models.unified_models import (
    StockMention, 
    SentimentResult, 
    SentimentSource, 
    InvestmentStyle,
    UnifiedStockData
)


class SentimentService:
    """Sentiment analysis service for social media data."""
    
    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        self.analyzer = SentimentIntensityAnalyzer()
        self.reddit_session = None
        self.twitter_session = None
        
        # Rate limiting
        self.reddit_requests_per_minute = 60
        self.twitter_requests_per_minute = 300
        self.reddit_request_times = []
        self.twitter_request_times = []
        
        # Stock-specific lexicon
        self.stock_lexicon = self._load_stock_lexicon()
        
        # Cache TTL
        self.cache_ttl = 300  # 5 minutes
    
    def _load_stock_lexicon(self) -> Dict[str, float]:
        """Load stock-specific sentiment lexicon."""
        return {
            # Bullish terms
            'moon': 0.8, 'rocket': 0.8, 'diamond hands': 0.9, 'bullish': 0.7,
            'buy': 0.6, 'hold': 0.3, 'long': 0.5, 'calls': 0.7,
            'ath': 0.6, 'to the moon': 0.9, 'stonks': 0.5, 'gain': 0.6,
            
            # Bearish terms
            'crash': -0.8, 'paper hands': -0.9, 'bearish': -0.7,
            'sell': -0.6, 'short': -0.5, 'puts': -0.7, 'loss': -0.6,
            'dump': -0.8, 'bagholder': -0.7, 'rekt': -0.9,
            
            # Neutral/analysis terms
            'analysis': 0.0, 'technical': 0.0, 'fundamental': 0.0,
            'chart': 0.0, 'resistance': 0.0, 'support': 0.0
        }
    
    async def _get_reddit_session(self) -> aiohttp.ClientSession:
        """Get or create Reddit HTTP session."""
        if self.reddit_session is None or self.reddit_session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                'User-Agent': 'InsiteChart/1.0 (Sentiment Analysis Bot)'
            }
            self.reddit_session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.reddit_session
    
    async def _get_twitter_session(self) -> aiohttp.ClientSession:
        """Get or create Twitter HTTP session."""
        if self.twitter_session is None or self.twitter_session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                'Authorization': f'Bearer {os.getenv("TWITTER_BEARER_TOKEN", "")}',
                'User-Agent': 'InsiteChart/1.0 (Sentiment Analysis Bot)'
            }
            self.twitter_session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.twitter_session
    
    async def _check_rate_limit(self, service: str):
        """Check and enforce rate limiting."""
        now = time.time()
        
        if service == 'reddit':
            # Remove requests older than 1 minute
            self.reddit_request_times = [t for t in self.reddit_request_times if now - t < 60]
            
            if len(self.reddit_request_times) >= self.reddit_requests_per_minute:
                sleep_time = 60 - (now - self.reddit_request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            self.reddit_request_times.append(now)
        
        elif service == 'twitter':
            # Remove requests older than 1 minute
            self.twitter_request_times = [t for t in self.twitter_request_times if now - t < 60]
            
            if len(self.twitter_request_times) >= self.twitter_requests_per_minute:
                sleep_time = 60 - (now - self.twitter_request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            self.twitter_request_times.append(now)
    
    async def collect_mentions(self, symbol: str, timeframe: str = "24h") -> List[StockMention]:
        """Collect stock mentions from social media."""
        mentions = []
        
        # Reddit mentions
        reddit_mentions = await self._collect_reddit_mentions(symbol, timeframe)
        mentions.extend(reddit_mentions)
        
        # Twitter mentions
        twitter_mentions = await self._collect_twitter_mentions(symbol, timeframe)
        mentions.extend(twitter_mentions)
        
        # Sort by timestamp
        mentions.sort(key=lambda x: x.timestamp, reverse=True)
        
        self.logger.info(f"Collected {len(mentions)} mentions for {symbol}")
        return mentions
    
    async def _collect_reddit_mentions(self, symbol: str, timeframe: str) -> List[StockMention]:
        """Collect mentions from Reddit."""
        try:
            await self._check_rate_limit('reddit')
            
            # Calculate time range
            time_mapping = {
                '1h': 1, '6h': 6, '24h': 24, '7d': 168
            }
            hours = time_mapping.get(timeframe, 24)
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Reddit search URL (using pushshift API for historical data)
            url = "https://api.pushshift.io/reddit/search/submission"
            params = {
                'q': symbol,
                'subreddit': 'wallstreetbets,investing,stocks,SecurityAnalysis',
                'size': 100,
                'after': int(since.timestamp())
            }
            
            session = await self._get_reddit_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"Reddit API error: {response.status}")
                    return []
                
                data = await response.json()
                mentions = []
                
                for post in data.get('data', []):
                    # Extract stock symbols from title and selftext
                    text = f"{post.get('title', '')} {post.get('selftext', '')}"
                    
                    if self._contains_stock_mention(text, symbol):
                        sentiment = self.analyze_sentiment(text)
                        investment_style = self._detect_investment_style(text)
                        
                        mention = StockMention(
                            symbol=symbol,
                            text=text,
                            source=SentimentSource.REDDIT,
                            community=post.get('subreddit', ''),
                            author=post.get('author', ''),
                            timestamp=datetime.fromtimestamp(post.get('created_utc', 0)),
                            upvotes=post.get('score', 0),
                            sentiment_score=sentiment.compound_score,
                            investment_style=investment_style,
                            url=f"https://reddit.com{post.get('permalink', '')}"
                        )
                        mentions.append(mention)
                
                return mentions
                
        except Exception as e:
            self.logger.error(f"Error collecting Reddit mentions for {symbol}: {str(e)}")
            return []
    
    async def _collect_twitter_mentions(self, symbol: str, timeframe: str) -> List[StockMention]:
        """Collect mentions from Twitter."""
        try:
            await self._check_rate_limit('twitter')
            
            # Twitter API v2 search URL
            url = "https://api.twitter.com/2/tweets/search/recent"
            params = {
                'query': f"${symbol} OR {symbol} stock",
                'max_results': 100,
                'tweet.fields': 'created_at,author_id,public_metrics,context_annotations',
                'expansions': 'author_id'
            }
            
            session = await self._get_twitter_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"Twitter API error: {response.status}")
                    return []
                
                data = await response.json()
                mentions = []
                
                for tweet in data.get('data', []):
                    text = tweet.get('text', '')
                    
                    if self._contains_stock_mention(text, symbol):
                        sentiment = self.analyze_sentiment(text)
                        investment_style = self._detect_investment_style(text)
                        
                        mention = StockMention(
                            symbol=symbol,
                            text=text,
                            source=SentimentSource.TWITTER,
                            community='twitter',
                            author=tweet.get('author_id', ''),
                            timestamp=datetime.fromisoformat(tweet.get('created_at', '').replace('Z', '+00:00')),
                            upvotes=tweet.get('public_metrics', {}).get('like_count', 0),
                            sentiment_score=sentiment.compound_score,
                            investment_style=investment_style,
                            url=f"https://twitter.com/twitter/status/{tweet.get('id', '')}"
                        )
                        mentions.append(mention)
                
                return mentions
                
        except Exception as e:
            self.logger.error(f"Error collecting Twitter mentions for {symbol}: {str(e)}")
            return []
    
    def _contains_stock_mention(self, text: str, symbol: str) -> bool:
        """Check if text contains a legitimate stock mention."""
        text_lower = text.lower()
        symbol_lower = symbol.lower()
        
        # Check for $symbol or symbol followed by stock-related terms
        patterns = [
            rf'\${symbol_lower}',
            rf'\b{symbol_lower}\b.*(?:stock|shares|trading|invest)',
            rf'\b{symbol_lower}\b(?=\s|$)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment of text."""
        # Basic VADER analysis
        vader_scores = self.analyzer.polarity_scores(text)
        
        # Stock-specific term analysis
        stock_scores = self._analyze_stock_specific_terms(text)
        
        # Calculate weighted sentiment
        vader_weight = 0.7
        stock_weight = 0.3
        
        compound_score = (vader_scores['compound'] * vader_weight + 
                        stock_scores['compound'] * stock_weight)
        
        # Calculate confidence
        confidence = self._calculate_confidence(vader_scores, stock_scores)
        
        return SentimentResult(
            compound_score=compound_score,
            positive_score=vader_scores['pos'],
            negative_score=vader_scores['neg'],
            neutral_score=vader_scores['neu'],
            confidence=confidence,
            source=SentimentSource.NEWS  # Default source
        )
    
    def _analyze_stock_specific_terms(self, text: str) -> Dict[str, float]:
        """Analyze stock-specific sentiment terms."""
        text_lower = text.lower()
        scores = {'positive': 0, 'negative': 0, 'compound': 0}
        
        for term, sentiment in self.stock_lexicon.items():
            if term in text_lower:
                if sentiment > 0:
                    scores['positive'] += abs(sentiment)
                elif sentiment < 0:
                    scores['negative'] += abs(sentiment)
        
        # Calculate compound score
        if scores['positive'] + scores['negative'] > 0:
            scores['compound'] = (scores['positive'] - scores['negative']) / (scores['positive'] + scores['negative'])
        
        return scores
    
    def _calculate_confidence(self, vader_scores: Dict[str, float], stock_scores: Dict[str, float]) -> float:
        """Calculate confidence score for sentiment analysis."""
        # Higher confidence for more extreme sentiments
        vader_confidence = max(vader_scores['pos'], vader_scores['neg']) * 2
        stock_confidence = min(abs(stock_scores['compound']) * 2, 1.0)
        
        # Combine confidences
        return min((vader_confidence + stock_confidence) / 2, 1.0)
    
    def _detect_investment_style(self, text: str) -> InvestmentStyle:
        """Detect investment style from text."""
        text_lower = text.lower()
        
        # Day trading indicators
        day_trading_terms = ['day trade', 'scalp', 'intraday', 'swing', 'flip']
        if any(term in text_lower for term in day_trading_terms):
            return InvestmentStyle.DAY_TRADING
        
        # Value investing indicators
        value_terms = ['value', 'undervalued', 'fundamentals', 'pe ratio', 'dividend']
        if any(term in text_lower for term in value_terms):
            return InvestmentStyle.VALUE_INVESTING
        
        # Growth investing indicators
        growth_terms = ['growth', 'potential', 'future', 'innovation', 'disrupt']
        if any(term in text_lower for term in growth_terms):
            return InvestmentStyle.GROWTH_INVESTING
        
        # Long term indicators
        long_term_terms = ['long term', 'hold', 'retirement', 'buy and hold']
        if any(term in text_lower for term in long_term_terms):
            return InvestmentStyle.LONG_TERM
        
        return InvestmentStyle.SWING_TRADING  # Default
    
    async def get_sentiment_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive sentiment data for a stock."""
        try:
            # Check cache first
            cache_key = f"sentiment_{symbol}"
            if self.cache_manager:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    self.logger.info(f"Cache hit for sentiment data: {symbol}")
                    return cached_data
            
            # Collect mentions
            mentions = await self.collect_mentions(symbol, "24h")
            
            if not mentions:
                return None
            
            # Analyze mentions
            sentiment_scores = [m.sentiment_score for m in mentions if m.sentiment_score is not None]
            
            if not sentiment_scores:
                return None
            
            # Calculate metrics
            overall_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            positive_count = sum(1 for s in sentiment_scores if s > 0.1)
            negative_count = sum(1 for s in sentiment_scores if s < -0.1)
            neutral_count = len(sentiment_scores) - positive_count - negative_count
            
            # Check trending status
            trending_status, trend_score = await self._check_trending_status(symbol, mentions)
            
            # Community breakdown
            community_breakdown = self._analyze_community_breakdown(mentions)
            
            sentiment_data = {
                'symbol': symbol,
                'overall_sentiment': round(overall_sentiment, 3),
                'mention_count_24h': len(mentions),
                'positive_mentions': positive_count,
                'negative_mentions': negative_count,
                'neutral_mentions': neutral_count,
                'trending_status': trending_status,
                'trend_score': trend_score,
                'community_breakdown': community_breakdown,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # Cache result
            if self.cache_manager:
                await self.cache_manager.set(cache_key, sentiment_data, ttl=self.cache_ttl)
            
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment data for {symbol}: {str(e)}")
            return None
    
    async def _check_trending_status(self, symbol: str, mentions: List[StockMention]) -> tuple[bool, Optional[float]]:
        """Check if stock is trending and calculate trend score."""
        try:
            # Compare with historical data
            historical_mentions = await self._get_historical_mention_count(symbol, "7d")
            current_mentions = len(mentions)
            
            if not historical_mentions:
                return False, None
            
            # Calculate trend score
            avg_historical = historical_mentions / 7  # Daily average
            if avg_historical == 0:
                return False, None
            
            trend_ratio = current_mentions / avg_historical
            trend_score = min(trend_ratio, 10.0)  # Cap at 10x
            
            # Consider trending if 200% increase
            trending = trend_ratio >= 2.0
            
            return trending, round(trend_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error checking trending status for {symbol}: {str(e)}")
            return False, None
    
    async def _get_historical_mention_count(self, symbol: str, timeframe: str) -> int:
        """Get historical mention count for comparison."""
        # This would typically query a database or time-series store
        # For now, return mock data
        import random
        return random.randint(50, 500)
    
    def _analyze_community_breakdown(self, mentions: List[StockMention]) -> List[Dict[str, Any]]:
        """Analyze mention breakdown by community."""
        community_counts = {}
        community_sentiments = {}
        
        for mention in mentions:
            community = mention.community
            if community not in community_counts:
                community_counts[community] = 0
                community_sentiments[community] = []
            
            community_counts[community] += 1
            if mention.sentiment_score is not None:
                community_sentiments[community].append(mention.sentiment_score)
        
        breakdown = []
        for community, count in community_counts.items():
            avg_sentiment = None
            if community_sentiments[community]:
                avg_sentiment = sum(community_sentiments[community]) / len(community_sentiments[community])
            
            breakdown.append({
                'community': community,
                'mentions': count,
                'avg_sentiment': round(avg_sentiment, 3) if avg_sentiment else None
            })
        
        # Sort by mention count
        breakdown.sort(key=lambda x: x['mentions'], reverse=True)
        return breakdown
    
    async def get_trending_stocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get currently trending stocks."""
        try:
            # Check cache first
            cache_key = f"trending_{limit}"
            if self.cache_manager:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    self.logger.info("Cache hit for trending stocks")
                    return cached_data
            
            # Get trending from popular symbols
            popular_symbols = ['GME', 'AMC', 'TSLA', 'AAPL', 'NVDA', 'AMD', 'PLTR', 'BB', 'NOK', 'SNDL']
            trending_stocks = []
            
            for symbol in popular_symbols:
                sentiment_data = await self.get_sentiment_data(symbol)
                if sentiment_data and sentiment_data.get('trending_status'):
                    trending_stock = {
                        'symbol': symbol,
                        'trend_score': sentiment_data['trend_score'],
                        'mention_count_24h': sentiment_data['mention_count_24h'],
                        'sentiment_score': sentiment_data['overall_sentiment']
                    }
                    trending_stocks.append(trending_stock)
            
            # Sort by trend score
            trending_stocks.sort(key=lambda x: x['trend_score'], reverse=True)
            
            # Limit results
            trending_stocks = trending_stocks[:limit]
            
            # Cache result
            if self.cache_manager:
                await self.cache_manager.set(cache_key, trending_stocks, ttl=self.cache_ttl)
            
            return trending_stocks
            
        except Exception as e:
            self.logger.error(f"Error getting trending stocks: {str(e)}")
            return []
    
    async def close(self):
        """Close HTTP sessions."""
        if self.reddit_session and not self.reddit_session.closed:
            await self.reddit_session.close()
        
        if self.twitter_session and not self.twitter_session.closed:
            await self.twitter_session.close()