"""
Unified data models for InsiteChart platform.

This module contains the core data models that are used across all services
to ensure consistency and type safety.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class StockType(Enum):
    """Stock type enumeration."""
    EQUITY = "EQUITY"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    CRYPTO = "CRYPTO"
    INDEX = "INDEX"


class SentimentSource(Enum):
    """Sentiment data source enumeration."""
    REDDIT = "REDDIT"
    TWITTER = "TWITTER"
    DISCORD = "DISCORD"
    NEWS = "NEWS"


class InvestmentStyle(Enum):
    """Investment style enumeration for sentiment analysis."""
    DAY_TRADING = "DAY_TRADING"
    SWING_TRADING = "SWING_TRADING"
    VALUE_INVESTING = "VALUE_INVESTING"
    GROWTH_INVESTING = "GROWTH_INVESTING"
    LONG_TERM = "LONG_TERM"


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    compound_score: float
    positive_score: float
    negative_score: float
    neutral_score: float
    confidence: float
    source: SentimentSource
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StockMention:
    """Social media stock mention data."""
    symbol: str
    text: str
    source: SentimentSource
    community: str
    author: str
    timestamp: datetime
    upvotes: int = 0
    sentiment_score: Optional[float] = None
    investment_style: Optional[InvestmentStyle] = None
    url: Optional[str] = None


@dataclass
class User:
    """User data model."""
    id: int
    username: str
    email: str
    password_hash: str
    role: str = "basic"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    permissions: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WatchlistItem:
    """Watchlist item data model."""
    id: int
    user_id: int
    symbol: str
    category: Optional[str] = None
    note: Optional[str] = None
    added_date: datetime = field(default_factory=datetime.utcnow)
    order_index: int = 0
    alert_threshold: Optional[float] = None
    sentiment_alert: bool = False


@dataclass
class UnifiedStockData:
    """Unified stock data model combining financial and sentiment data."""
    
    # Basic Information
    symbol: str
    company_name: str
    stock_type: StockType
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    
    # Price Information
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    day_change: Optional[float] = None
    day_change_pct: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    
    # Financial Metrics
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    eps: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    
    # Sentiment Data
    overall_sentiment: Optional[float] = None
    sentiment_sources: Dict[SentimentSource, float] = field(default_factory=dict)
    mention_count_24h: Optional[int] = None
    mention_count_1h: Optional[int] = None
    positive_mentions: Optional[int] = None
    negative_mentions: Optional[int] = None
    neutral_mentions: Optional[int] = None
    trending_status: bool = False
    trend_score: Optional[float] = None
    trend_duration_hours: Optional[int] = None
    
    # Search and Interaction Data
    relevance_score: float = 0.0
    search_count: int = 0
    view_count: int = 0
    last_viewed: Optional[datetime] = None
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    data_quality_score: float = 1.0  # 0.0-1.0 data quality score
    data_sources: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        # Calculate day change if not provided
        if self.current_price and self.previous_close:
            if self.day_change is None:
                self.day_change = self.current_price - self.previous_close
            if self.day_change_pct is None:
                self.day_change_pct = (self.day_change / self.previous_close) * 100
        
        # Ensure sentiment_sources uses proper enum keys
        if self.sentiment_sources:
            self.sentiment_sources = {
                SentimentSource(k) if isinstance(k, str) else k: v
                for k, v in self.sentiment_sources.items()
            }
        
        # Add default data sources if not provided
        if not self.data_sources:
            self.data_sources = ["yahoo_finance"]
            if self.overall_sentiment is not None:
                self.data_sources.extend(["reddit", "twitter"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'stock_type': self.stock_type.value,
            'exchange': self.exchange,
            'sector': self.sector,
            'industry': self.industry,
            'market_cap': self.market_cap,
            'current_price': self.current_price,
            'previous_close': self.previous_close,
            'day_change': self.day_change,
            'day_change_pct': self.day_change_pct,
            'volume': self.volume,
            'avg_volume': self.avg_volume,
            'day_high': self.day_high,
            'day_low': self.day_low,
            'pe_ratio': self.pe_ratio,
            'dividend_yield': self.dividend_yield,
            'beta': self.beta,
            'eps': self.eps,
            'fifty_two_week_high': self.fifty_two_week_high,
            'fifty_two_week_low': self.fifty_two_week_low,
            'overall_sentiment': self.overall_sentiment,
            'sentiment_sources': {k.value: v for k, v in self.sentiment_sources.items()},
            'mention_count_24h': self.mention_count_24h,
            'mention_count_1h': self.mention_count_1h,
            'positive_mentions': self.positive_mentions,
            'negative_mentions': self.negative_mentions,
            'neutral_mentions': self.neutral_mentions,
            'trending_status': self.trending_status,
            'trend_score': self.trend_score,
            'trend_duration_hours': self.trend_duration_hours,
            'relevance_score': self.relevance_score,
            'search_count': self.search_count,
            'view_count': self.view_count,
            'last_viewed': self.last_viewed.isoformat() if self.last_viewed else None,
            'last_updated': self.last_updated.isoformat(),
            'data_quality_score': self.data_quality_score,
            'data_sources': self.data_sources
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedStockData':
        """Create instance from dictionary."""
        # Convert stock_type string to enum
        if 'stock_type' in data and isinstance(data['stock_type'], str):
            data['stock_type'] = StockType(data['stock_type'])
        
        # Convert sentiment_sources keys to enums
        if 'sentiment_sources' in data and isinstance(data['sentiment_sources'], dict):
            data['sentiment_sources'] = {
                SentimentSource(k): v for k, v in data['sentiment_sources'].items()
            }
        
        # Convert datetime strings
        for field in ['last_viewed', 'last_updated']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)


@dataclass
class SearchQuery:
    """Search query model."""
    query: str
    user_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    limit: int = 20
    offset: int = 0
    sort_by: str = "relevance"
    sort_order: str = "desc"
    
    def __post_init__(self):
        """Initialize default values."""
        if self.filters is None:
            self.filters = {}
    
    def to_hash(self) -> str:
        """Generate hash for cache key."""
        import hashlib
        query_str = f"{self.query}_{json.dumps(self.filters, sort_keys=True)}_{self.limit}_{self.offset}_{self.sort_by}_{self.sort_order}"
        return hashlib.md5(query_str.encode()).hexdigest()


@dataclass
class SearchResult:
    """Search result model."""
    query: SearchQuery
    results: List[UnifiedStockData]
    total_count: int
    search_time_ms: float
    cache_hit: bool = False
    suggestions: Optional[List[str]] = None
    facets: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'query': self.query.to_dict(),
            'results': [stock.to_dict() for stock in self.results],
            'total_count': self.total_count,
            'search_time_ms': self.search_time_ms,
            'cache_hit': self.cache_hit,
            'suggestions': self.suggestions,
            'facets': self.facets
        }


# Add to_dict method to SearchQuery
SearchQuery.to_dict = lambda self: {
    'query': self.query,
    'user_id': self.user_id,
    'filters': self.filters,
    'timestamp': self.timestamp.isoformat(),
    'limit': self.limit,
    'offset': self.offset,
    'sort_by': self.sort_by,
    'sort_order': self.sort_order
}