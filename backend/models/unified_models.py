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

# SQLAlchemy Base for database models
try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship
    Base = declarative_base()
except ImportError:
    # Fallback for when SQLAlchemy is not available
    class Base:
        """Fallback Base class for when SQLAlchemy is not available."""
        pass


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
    SOCIAL = "SOCIAL"
    ANALYST = "ANALYST"


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
    model_used: Optional[str] = None
    financial_keywords: List[str] = field(default_factory=list)


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
class SentimentPoint:
    """Sentiment data point for time series analysis."""
    timestamp: datetime
    sentiment_score: float  # -100 to +100 range
    mention_count: int
    source: SentimentSource
    confidence: float  # 0.0 to 1.0 range
    keywords: List[str] = field(default_factory=list)


@dataclass
class MentionDetail:
    """Detailed mention information from social media."""
    id: str
    text: str
    author: str
    community: str
    upvotes: int
    downvotes: int
    timestamp: datetime
    investment_style: InvestmentStyle
    sentiment_score: float
    confidence: float
    is_spam: bool = False


@dataclass
class UnifiedStockData:
    """Unified stock data model combining financial and sentiment data.
    
    This model standardizes data across all services and ensures consistency
    throughout the platform. All sentiment scores use -100 to +100 range.
    """
    
    # Basic Information
    symbol: str
    company_name: str
    stock_type: StockType
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    
    # Price Information
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    day_change: Optional[float] = None
    day_change_pct: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    market_cap: Optional[float] = None
    
    # Financial Metrics
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    eps: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    
    # Sentiment Data (standardized -100 to +100 range)
    overall_sentiment: Optional[float] = None  # -100 to +100
    sentiment_sources: Dict[SentimentSource, float] = field(default_factory=dict)
    mention_count_24h: Optional[int] = None
    mention_count_7d: Optional[int] = None
    mention_count_1h: Optional[int] = None
    positive_mentions: Optional[int] = None
    negative_mentions: Optional[int] = None
    neutral_mentions: Optional[int] = None
    trending_status: bool = False
    trend_score: Optional[float] = None
    trend_start_time: Optional[datetime] = None
    trend_duration_hours: Optional[int] = None
    
    # Detailed Sentiment Information
    sentiment_history: List[SentimentPoint] = field(default_factory=list)
    mention_details: List[MentionDetail] = field(default_factory=list)
    community_breakdown: Dict[str, int] = field(default_factory=dict)
    investment_style_distribution: Dict[InvestmentStyle, float] = field(default_factory=dict)
    
    # Search and Interaction Data
    relevance_score: float = 0.0
    search_count: int = 0
    view_count: int = 0
    last_searched: Optional[datetime] = None
    last_viewed: Optional[datetime] = None
    
    # Time Series Data (for correlation analysis)
    timestamps: List[datetime] = field(default_factory=list)
    prices: List[float] = field(default_factory=list)
    volumes: List[int] = field(default_factory=list)
    mentions: List[int] = field(default_factory=list)
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    data_quality_score: float = 1.0  # 0.0-1.0 data quality score
    data_sources: List[str] = field(default_factory=list)
    api_errors: List[str] = field(default_factory=list)
    
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
        
        # Validate data consistency
        self._validate_data_consistency()
        
        # Calculate data quality score
        if self.data_quality_score == 1.0:  # Default value
            self.data_quality_score = self._calculate_data_quality()
    
    def _validate_data_consistency(self):
        """Validate data consistency and fix common issues."""
        # Ensure sentiment score is within valid range
        if self.overall_sentiment is not None:
            self.overall_sentiment = max(-100.0, min(100.0, self.overall_sentiment))
        
        # Ensure sentiment sources scores are within valid range
        for source, score in self.sentiment_sources.items():
            self.sentiment_sources[source] = max(-100.0, min(100.0, score))
        
        # Ensure positive values for count fields
        if self.mention_count_24h is not None and self.mention_count_24h < 0:
            self.mention_count_24h = 0
        if self.mention_count_7d is not None and self.mention_count_7d < 0:
            self.mention_count_7d = 0
        if self.mention_count_1h is not None and self.mention_count_1h < 0:
            self.mention_count_1h = 0
        
        # Ensure consistency between positive/negative/neutral mentions
        if all(x is not None for x in [self.positive_mentions, self.negative_mentions, self.neutral_mentions]):
            total_mentions = self.positive_mentions + self.negative_mentions + self.neutral_mentions
            # Adjust mention_count_24h if it doesn't match
            if self.mention_count_24h is not None and self.mention_count_24h != total_mentions:
                self.mention_count_24h = total_mentions
    
    def _calculate_data_quality(self) -> float:
        """Calculate data quality score based on field completeness."""
        required_fields = [
            'current_price', 'volume', 'symbol', 'company_name', 'exchange'
        ]
        
        important_fields = [
            'previous_close', 'day_change', 'day_change_pct', 'market_cap',
            'pe_ratio', 'beta', 'eps'
        ]
        
        sentiment_fields = [
            'overall_sentiment', 'sentiment_sources', 'mention_count_24h'
        ]
        
        # Count available fields
        required_count = sum(1 for field in required_fields if getattr(self, field) is not None)
        important_count = sum(1 for field in important_fields if getattr(self, field) is not None)
        sentiment_count = sum(1 for field in sentiment_fields if getattr(self, field) is not None)
        
        # Calculate weighted score
        required_weight = 0.5
        important_weight = 0.3
        sentiment_weight = 0.2
        
        required_score = required_count / len(required_fields)
        important_score = important_count / len(important_fields)
        sentiment_score = sentiment_count / len(sentiment_fields)
        
        quality_score = (
            required_score * required_weight +
            important_score * important_weight +
            sentiment_score * sentiment_weight
        )
        
        return round(quality_score, 2)
    
    def merge_sentiment_data(self, sentiment_data: Dict[str, Any]):
        """Merge sentiment data into unified stock data."""
        if not sentiment_data:
            return
        
        # Update sentiment fields
        if 'overall_sentiment' in sentiment_data:
            self.overall_sentiment = sentiment_data['overall_sentiment']
        
        if 'sentiment_sources' in sentiment_data:
            for source, score in sentiment_data['sentiment_sources'].items():
                if isinstance(source, str):
                    source = SentimentSource(source)
                self.sentiment_sources[source] = score
        
        if 'mention_count_24h' in sentiment_data:
            self.mention_count_24h = sentiment_data['mention_count_24h']
        
        if 'mention_count_7d' in sentiment_data:
            self.mention_count_7d = sentiment_data['mention_count_7d']
        
        if 'mention_count_1h' in sentiment_data:
            self.mention_count_1h = sentiment_data['mention_count_1h']
        
        if 'positive_mentions' in sentiment_data:
            self.positive_mentions = sentiment_data['positive_mentions']
        
        if 'negative_mentions' in sentiment_data:
            self.negative_mentions = sentiment_data['negative_mentions']
        
        if 'neutral_mentions' in sentiment_data:
            self.neutral_mentions = sentiment_data['neutral_mentions']
        
        if 'trending_status' in sentiment_data:
            self.trending_status = sentiment_data['trending_status']
        
        if 'trend_score' in sentiment_data:
            self.trend_score = sentiment_data['trend_score']
        
        if 'trend_start_time' in sentiment_data:
            self.trend_start_time = sentiment_data['trend_start_time']
        
        if 'trend_duration_hours' in sentiment_data:
            self.trend_duration_hours = sentiment_data['trend_duration_hours']
        
        # Update data sources
        if 'sentiment_analysis' not in self.data_sources:
            self.data_sources.append('sentiment_analysis')
        
        # Update last_updated timestamp
        self.last_updated = datetime.utcnow()
        
        # Recalculate data quality score
        self.data_quality_score = self._calculate_data_quality()
    
    def merge_financial_data(self, financial_data: Dict[str, Any]):
        """Merge financial data into unified stock data."""
        if not financial_data:
            return
        
        # Update financial fields
        financial_fields = [
            'current_price', 'previous_close', 'day_change', 'day_change_pct',
            'volume', 'avg_volume', 'day_high', 'day_low', 'market_cap',
            'pe_ratio', 'dividend_yield', 'beta', 'eps',
            'fifty_two_week_high', 'fifty_two_week_low'
        ]
        
        for field in financial_fields:
            if field in financial_data and financial_data[field] is not None:
                setattr(self, field, financial_data[field])
        
        # Update basic info fields
        info_fields = ['company_name', 'sector', 'industry', 'description', 'website']
        for field in info_fields:
            if field in financial_data and financial_data[field] is not None:
                setattr(self, field, financial_data[field])
        
        # Update data sources
        if 'yahoo_finance' not in self.data_sources:
            self.data_sources.append('yahoo_finance')
        
        # Update last_updated timestamp
        self.last_updated = datetime.utcnow()
        
        # Recalculate data quality score
        self.data_quality_score = self._calculate_data_quality()
    
    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Get sentiment summary for quick display."""
        summary = {
            'overall_sentiment': self.overall_sentiment,
            'sentiment_label': self._get_sentiment_label(),
            'trending_status': self.trending_status,
            'trend_score': self.trend_score,
            'mention_count_24h': self.mention_count_24h
        }
        
        if self.sentiment_sources:
            summary['source_breakdown'] = {
                source.value: score for source, score in self.sentiment_sources.items()
            }
        
        if self.positive_mentions is not None and self.negative_mentions is not None and self.neutral_mentions is not None:
            total = self.positive_mentions + self.negative_mentions + self.neutral_mentions
            if total > 0:
                summary['sentiment_distribution'] = {
                    'positive': round(self.positive_mentions / total * 100, 1),
                    'negative': round(self.negative_mentions / total * 100, 1),
                    'neutral': round(self.neutral_mentions / total * 100, 1)
                }
        
        return summary
    
    def _get_sentiment_label(self) -> str:
        """Get sentiment label based on score."""
        if self.overall_sentiment is None:
            return 'unknown'
        
        if self.overall_sentiment > 20:
            return 'very_positive'
        elif self.overall_sentiment > 5:
            return 'positive'
        elif self.overall_sentiment > -5:
            return 'neutral'
        elif self.overall_sentiment > -20:
            return 'negative'
        else:
            return 'very_negative'
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary for quick display."""
        return {
            'current_price': self.current_price,
            'day_change': self.day_change,
            'day_change_pct': self.day_change_pct,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'pe_ratio': self.pe_ratio,
            'beta': self.beta
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Handle stock_type field - check if it's already a string or needs enum conversion
        stock_type_value = self.stock_type
        if hasattr(stock_type_value, 'value'):
            stock_type_value = stock_type_value.value
        elif isinstance(stock_type_value, str):
            stock_type_value = stock_type_value
        else:
            stock_type_value = str(stock_type_value)
            
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'stock_type': stock_type_value,
            'exchange': self.exchange,
            'sector': self.sector,
            'industry': self.industry,
            'description': self.description,
            'website': self.website,
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
            'mention_count_7d': self.mention_count_7d,
            'mention_count_1h': self.mention_count_1h,
            'positive_mentions': self.positive_mentions,
            'negative_mentions': self.negative_mentions,
            'neutral_mentions': self.neutral_mentions,
            'trending_status': self.trending_status,
            'trend_score': self.trend_score,
            'trend_start_time': self.trend_start_time.isoformat() if self.trend_start_time else None,
            'trend_duration_hours': self.trend_duration_hours,
            'sentiment_history': [
                {
                    'timestamp': sp.timestamp.isoformat(),
                    'sentiment_score': sp.sentiment_score,
                    'mention_count': sp.mention_count,
                    'source': sp.source.value,
                    'confidence': sp.confidence,
                    'keywords': sp.keywords
                }
                for sp in self.sentiment_history
            ],
            'mention_details': [
                {
                    'id': md.id,
                    'text': md.text,
                    'author': md.author,
                    'community': md.community,
                    'upvotes': md.upvotes,
                    'downvotes': md.downvotes,
                    'timestamp': md.timestamp.isoformat(),
                    'investment_style': md.investment_style.value,
                    'sentiment_score': md.sentiment_score,
                    'confidence': md.confidence,
                    'is_spam': md.is_spam
                }
                for md in self.mention_details
            ],
            'community_breakdown': self.community_breakdown,
            'investment_style_distribution': {
                k.value: v for k, v in self.investment_style_distribution.items()
            },
            'relevance_score': self.relevance_score,
            'search_count': self.search_count,
            'view_count': self.view_count,
            'last_searched': self.last_searched.isoformat() if self.last_searched else None,
            'last_viewed': self.last_viewed.isoformat() if self.last_viewed else None,
            'timestamps': [ts.isoformat() for ts in self.timestamps],
            'prices': self.prices,
            'volumes': self.volumes,
            'mentions': self.mentions,
            'last_updated': self.last_updated.isoformat(),
            'data_quality_score': self.data_quality_score,
            'data_sources': self.data_sources,
            'api_errors': self.api_errors
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
        
        # Convert sentiment_history
        if 'sentiment_history' in data and isinstance(data['sentiment_history'], list):
            data['sentiment_history'] = [
                SentimentPoint(
                    timestamp=datetime.fromisoformat(sp['timestamp']),
                    sentiment_score=sp['sentiment_score'],
                    mention_count=sp['mention_count'],
                    source=SentimentSource(sp['source']),
                    confidence=sp['confidence'],
                    keywords=sp.get('keywords', [])
                )
                for sp in data['sentiment_history']
            ]
        
        # Convert mention_details
        if 'mention_details' in data and isinstance(data['mention_details'], list):
            data['mention_details'] = [
                MentionDetail(
                    id=md['id'],
                    text=md['text'],
                    author=md['author'],
                    community=md['community'],
                    upvotes=md['upvotes'],
                    downvotes=md['downvotes'],
                    timestamp=datetime.fromisoformat(md['timestamp']),
                    investment_style=InvestmentStyle(md['investment_style']),
                    sentiment_score=md['sentiment_score'],
                    confidence=md['confidence'],
                    is_spam=md.get('is_spam', False)
                )
                for md in data['mention_details']
            ]
        
        # Convert investment_style_distribution keys to enums
        if 'investment_style_distribution' in data and isinstance(data['investment_style_distribution'], dict):
            data['investment_style_distribution'] = {
                InvestmentStyle(k): v for k, v in data['investment_style_distribution'].items()
            }
        
        # Convert datetime strings
        for field in ['last_viewed', 'last_searched', 'last_updated', 'trend_start_time']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert timestamps list
        if 'timestamps' in data and isinstance(data['timestamps'], list):
            data['timestamps'] = [
                datetime.fromisoformat(ts) if isinstance(ts, str) else ts
                for ts in data['timestamps']
            ]
        
        return cls(**data)
    
    def is_data_fresh(self, max_age_minutes: int = 5) -> bool:
        """Check if data is fresh based on last_updated timestamp."""
        if not self.last_updated:
            return False
        
        age_minutes = (datetime.utcnow() - self.last_updated).total_seconds() / 60
        return age_minutes <= max_age_minutes
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within market trading hours."""
        now = datetime.utcnow()
        # Convert to US Eastern time (market timezone)
        # This is a simplified check - in production, you'd use proper timezone handling
        eastern_time = now - timedelta(hours=5)  # UTC-5 for EST
        
        # Check if it's a weekday
        if eastern_time.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if it's within trading hours (9:30 AM - 4:00 PM ET)
        if eastern_time.hour < 9 or eastern_time.hour > 16:
            return False
        
        if eastern_time.hour == 9 and eastern_time.minute < 30:
            return False
        
        if eastern_time.hour == 16 and eastern_time.minute > 0:
            return False
        
        return True
    
    def get_price_change_color(self) -> str:
        """Get color indicator for price change."""
        if self.day_change_pct is None:
            return 'gray'
        
        if self.day_change_pct > 0:
            return 'green'
        elif self.day_change_pct < 0:
            return 'red'
        else:
            return 'gray'
    
    def get_sentiment_color(self) -> str:
        """Get color indicator for sentiment."""
        if self.overall_sentiment is None:
            return 'gray'
        
        if self.overall_sentiment > 10:
            return 'green'
        elif self.overall_sentiment > -10:
            return 'yellow'
        else:
            return 'red'
    
    def calculate_volatility_score(self) -> float:
        """Calculate volatility score based on price movement and volume."""
        if not self.day_change_pct or not self.volume or not self.avg_volume:
            return 0.0
        
        # Price volatility component
        price_volatility = abs(self.day_change_pct)
        
        # Volume anomaly component
        volume_ratio = self.volume / self.avg_volume if self.avg_volume > 0 else 1.0
        volume_anomaly = max(0, (volume_ratio - 1.0) * 50)  # Scale volume anomaly
        
        # Combined volatility score (0-100)
        volatility_score = min(100, price_volatility * 2 + volume_anomaly)
        
        return round(volatility_score, 2)
    
    def get_risk_level(self) -> str:
        """Get risk level based on volatility and other factors."""
        volatility = self.calculate_volatility_score()
        
        if self.beta is not None:
            beta_component = abs(self.beta - 1.0) * 20
            volatility = min(100, volatility + beta_component)
        
        if volatility > 70:
            return 'high'
        elif volatility > 40:
            return 'medium'
        else:
            return 'low'
    
    def get_key_metrics(self) -> Dict[str, Any]:
        """Get key metrics for dashboard display."""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'current_price': self.current_price,
            'day_change': self.day_change,
            'day_change_pct': self.day_change_pct,
            'price_color': self.get_price_change_color(),
            'volume': self.volume,
            'market_cap': self.market_cap,
            'sentiment_score': self.overall_sentiment,
            'sentiment_color': self.get_sentiment_color(),
            'sentiment_label': self._get_sentiment_label(),
            'trending_status': self.trending_status,
            'data_quality': self.data_quality_score,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'data_fresh': self.is_data_fresh(),
            'risk_level': self.get_risk_level(),
            'volatility_score': self.calculate_volatility_score()
        }
    
    def to_api_response(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert to API response format with optional details."""
        base_response = {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'stock_type': self.stock_type.value if hasattr(self.stock_type, 'value') else str(self.stock_type),
            'exchange': self.exchange,
            'current_price': self.current_price,
            'day_change': self.day_change,
            'day_change_pct': self.day_change_pct,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'overall_sentiment': self.overall_sentiment,
            'trending_status': self.trending_status,
            'trend_score': self.trend_score,
            'mention_count_24h': self.mention_count_24h,
            'data_quality_score': self.data_quality_score,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'data_sources': self.data_sources
        }
        
        if include_details:
            base_response.update({
                'sector': self.sector,
                'industry': self.industry,
                'description': self.description,
                'website': self.website,
                'previous_close': self.previous_close,
                'day_high': self.day_high,
                'day_low': self.day_low,
                'avg_volume': self.avg_volume,
                'pe_ratio': self.pe_ratio,
                'dividend_yield': self.dividend_yield,
                'beta': self.beta,
                'eps': self.eps,
                'fifty_two_week_high': self.fifty_two_week_high,
                'fifty_two_week_low': self.fifty_two_week_low,
                'sentiment_sources': {source.value: score for source, score in self.sentiment_sources.items()},
                'mention_count_7d': self.mention_count_7d,
                'mention_count_1h': self.mention_count_1h,
                'positive_mentions': self.positive_mentions,
                'negative_mentions': self.negative_mentions,
                'neutral_mentions': self.neutral_mentions,
                'trend_start_time': self.trend_start_time.isoformat() if self.trend_start_time else None,
                'trend_duration_hours': self.trend_duration_hours,
                'sentiment_summary': self.get_sentiment_summary(),
                'financial_summary': self.get_financial_summary(),
                'key_metrics': self.get_key_metrics(),
                'risk_level': self.get_risk_level(),
                'volatility_score': self.calculate_volatility_score(),
                'is_data_fresh': self.is_data_fresh(),
                'is_trading_hours': self.is_trading_hours()
            })
        
        return base_response
    
    @classmethod
    def create_from_financial_and_sentiment(
        cls,
        financial_data: Dict[str, Any],
        sentiment_data: Optional[Dict[str, Any]] = None
    ) -> 'UnifiedStockData':
        """Create UnifiedStockData from separate financial and sentiment data."""
        # Extract basic financial data
        stock_data = {
            'symbol': financial_data.get('symbol', ''),
            'company_name': financial_data.get('company_name', ''),
            'stock_type': StockType(financial_data.get('stock_type', 'EQUITY')),
            'exchange': financial_data.get('exchange', ''),
            'sector': financial_data.get('sector'),
            'industry': financial_data.get('industry'),
            'description': financial_data.get('description'),
            'website': financial_data.get('website'),
            'current_price': financial_data.get('current_price'),
            'previous_close': financial_data.get('previous_close'),
            'day_change': financial_data.get('day_change'),
            'day_change_pct': financial_data.get('day_change_pct'),
            'volume': financial_data.get('volume'),
            'avg_volume': financial_data.get('avg_volume'),
            'day_high': financial_data.get('day_high'),
            'day_low': financial_data.get('day_low'),
            'market_cap': financial_data.get('market_cap'),
            'pe_ratio': financial_data.get('pe_ratio'),
            'dividend_yield': financial_data.get('dividend_yield'),
            'beta': financial_data.get('beta'),
            'eps': financial_data.get('eps'),
            'fifty_two_week_high': financial_data.get('fifty_two_week_high'),
            'fifty_two_week_low': financial_data.get('fifty_two_week_low'),
            'data_sources': financial_data.get('data_sources', ['yahoo_finance'])
        }
        
        # Create instance
        unified_stock = cls(**stock_data)
        
        # Merge sentiment data if provided
        if sentiment_data:
            unified_stock.merge_sentiment_data(sentiment_data)
        
        return unified_stock
    
    def update_real_time_data(self, price_update: Dict[str, Any]):
        """Update real-time price data."""
        if 'current_price' in price_update:
            old_price = self.current_price
            self.current_price = price_update['current_price']
            
            # Recalculate day change if we have previous close
            if self.previous_close is not None:
                self.day_change = self.current_price - self.previous_close
                self.day_change_pct = (self.day_change / self.previous_close) * 100
        
        if 'volume' in price_update:
            self.volume = price_update['volume']
        
        if 'day_high' in price_update:
            self.day_high = price_update['day_high']
        
        if 'day_low' in price_update:
            self.day_low = price_update['day_low']
        
        # Update timestamp
        self.last_updated = datetime.utcnow()
        
        # Recalculate data quality score
        self.data_quality_score = self._calculate_data_quality()


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


@dataclass
class SentimentScore:
    """Sentiment score data model."""
    score: float
    confidence: float
    sentiment: str
    source: SentimentSource
    keywords: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class APIKeyPermission(Enum):
    """API key permission enumeration."""
    READ_STOCKS = "read:stocks"
    READ_SENTIMENT = "read:sentiment"
    WRITE_WATCHLIST = "write:watchlist"
    READ_PORTFOLIO = "read:portfolio"
    WRITE_PORTFOLIO = "write:portfolio"
    ADMIN_USERS = "admin:users"


@dataclass
class APIKey:
    """API key data model."""
    key_id: str
    api_key: str
    name: str
    user_id: str
    permissions: List[APIKeyPermission]
    rate_limit: int
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'key_id': self.key_id,
            'api_key': self.api_key,
            'name': self.name,
            'user_id': self.user_id,
            'permissions': [p.value for p in self.permissions],
            'rate_limit': self.rate_limit,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None
        }


class CacheStatus(str, Enum):
    """Cache status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UPDATING = "updating"
    ERROR = "error"


@dataclass
class CacheNode:
    """Cache node model for distributed cache."""
    id: str
    host: str
    port: int
    status: CacheStatus
    last_heartbeat: datetime
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    cache_size: int = 0
    hit_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class EventStatus(str, Enum):
    """Event status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataSourceType(str, Enum):
    """Data source type enumeration."""
    API = "api"
    WEBHOOK = "webhook"
    STREAMING = "streaming"
    BATCH = "batch"
    SCHEDULED = "scheduled"


class NotificationChannel(str, Enum):
    """Notification channel enumeration."""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


@dataclass
class DataSource:
    """Data source model."""
    id: str
    name: str
    type: DataSourceType
    url: Optional[str] = None
    api_key: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    last_sync: Optional[datetime] = None
    sync_frequency: int = 300  # seconds
    error_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UnifiedDataRequest:
    """Unified data request model."""
    request_id: str
    data_type: str
    user_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    limit: int = 100
    offset: int = 0
    include_metadata: bool = True
    include_sentiment: bool = True
    include_technical: bool = False
    include_fundamental: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class TestType(str, Enum):
    """Types of automated tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    API = "api"
    UI = "ui"
    END_TO_END = "end_to_end"


class TestStatus(str, Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TestPriority(str, Enum):
    """Test execution priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestSuite:
    """Test suite configuration."""
    suite_id: str
    name: str
    description: str
    test_type: TestType
    test_paths: List[str]
    test_files: List[str]
    enabled: bool
    timeout_seconds: int = 300
    parallel: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestExecution:
    """Test execution record."""
    execution_id: str
    suite_id: str
    status: TestStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: int
    test_results: List[Dict[str, Any]]
    error_message: Optional[str]
    environment: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestReport:
    """Test report."""
    report_id: str
    report_type: str
    execution_ids: List[str]
    generated_at: datetime
    summary: Dict[str, Any]
    details: Dict[str, Any]
    artifacts: List[str]