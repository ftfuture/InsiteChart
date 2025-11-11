"""
SQLAlchemy database models for InsiteChart platform.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="basic")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    watchlist_items = relationship("WatchlistItem", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")


class APIKey(Base):
    """API Key model."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    tier = Column(String(20), nullable=False, default="basic")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")


class Stock(Base):
    """Stock model."""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    stock_type = Column(String(20), nullable=False, default="EQUITY")
    exchange = Column(String(50), nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    stock_prices = relationship("StockPrice", back_populates="stock")
    watchlist_items = relationship("WatchlistItem", back_populates="stock")
    sentiment_data = relationship("SentimentData", back_populates="stock")


class StockPrice(Base):
    """Stock price model."""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    price = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    stock = relationship("Stock", back_populates="stock_prices")
    
    # Indexes
    __table_args__ = (
        Index('idx_stock_price_timestamp', 'stock_id', 'timestamp'),
        Index('idx_stock_price_latest', 'stock_id', 'timestamp'),
    )


class SentimentData(Base):
    """Sentiment data model."""
    __tablename__ = "sentiment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    source = Column(String(20), nullable=False)  # REDDIT, TWITTER, NEWS
    compound_score = Column(Float, nullable=False)
    positive_score = Column(Float, nullable=False)
    negative_score = Column(Float, nullable=False)
    neutral_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    mention_count = Column(Integer, default=0, nullable=False)
    positive_mentions = Column(Integer, default=0, nullable=False)
    negative_mentions = Column(Integer, default=0, nullable=False)
    neutral_mentions = Column(Integer, default=0, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    stock = relationship("Stock", back_populates="sentiment_data")
    
    # Indexes
    __table_args__ = (
        Index('idx_sentiment_stock_timestamp', 'stock_id', 'timestamp'),
        Index('idx_sentiment_source', 'source'),
    )


# Alias for backward compatibility with tests
SentimentAnalysis = SentimentData


class WatchlistItem(Base):
    """Watchlist item model."""
    __tablename__ = "watchlist_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    category = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    alert_threshold = Column(Float, nullable=True)
    sentiment_alert = Column(Boolean, default=False, nullable=False)
    added_date = Column(DateTime, default=func.now(), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="watchlist_items")
    stock = relationship("Stock", back_populates="watchlist_items")
    
    # Indexes
    __table_args__ = (
        Index('idx_watchlist_user', 'user_id'),
        Index('idx_watchlist_stock', 'stock_id'),
    )


class SearchHistory(Base):
    """Search history model."""
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query = Column(String(500), nullable=False)
    filters = Column(Text, nullable=True)
    results_count = Column(Integer, default=0, nullable=False)
    search_time_ms = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_search_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_search_query', 'query'),
    )


class UserSession(Base):
    """User session model."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_session_token', 'session_token'),
        Index('idx_session_user', 'user_id'),
        Index('idx_session_expires', 'expires_at'),
    )


class SystemLog(Base):
    """System log model."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_log_level_timestamp', 'level', 'timestamp'),
        Index('idx_log_component', 'component'),
        Index('idx_log_user', 'user_id'),
    )


class UserFeedback(Base):
    """User feedback model."""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # bug_report, feature_request, general, ui_ux
    category = Column(String(100), nullable=True)  # chart, sentiment_analysis, performance, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 stars for feature satisfaction
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(20), default="open")  # open, in_progress, resolved, closed
    response = Column(Text, nullable=True)  # Admin response
    responded_by = Column(Integer, nullable=True)  # Admin user ID
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    responder = relationship("User", foreign_keys=[responded_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_user', 'user_id'),
        Index('idx_feedback_type', 'feedback_type'),
        Index('idx_feedback_status', 'status'),
        Index('idx_feedback_priority', 'priority'),
    )


class UserActivity(Base):
    """User activity tracking model."""
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), nullable=True)
    activity_type = Column(String(50), nullable=False)  # page_view, feature_use, search, etc.
    feature_name = Column(String(100), nullable=True)  # chart_analysis, sentiment_analysis, etc.
    action = Column(String(100), nullable=False)  # view, click, search, add_to_watchlist, etc.
    activity_metadata = Column(JSON, nullable=True)  # Additional context data
    duration = Column(Integer, nullable=True)  # Time spent on feature (seconds)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_activity_user', 'user_id'),
        Index('idx_activity_session', 'session_id'),
        Index('idx_activity_type', 'activity_type'),
        Index('idx_activity_feature', 'feature_name'),
        Index('idx_activity_timestamp', 'created_at'),
    )


class FeatureUsage(Base):
    """Feature usage statistics model."""
    __tablename__ = "feature_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    feature_name = Column(String(100), nullable=False, unique=True)
    usage_count = Column(Integer, default=0, nullable=False)
    unique_users = Column(Integer, default=0, nullable=False)
    avg_duration = Column(Float, default=0.0, nullable=False)  # Average time spent (seconds)
    last_used = Column(DateTime, nullable=True)
    satisfaction_score = Column(Float, nullable=True)  # Average user satisfaction (1-5)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_feature_name', 'feature_name'),
        Index('idx_feature_usage_count', 'usage_count'),
    )


class UserBehavior(Base):
    """User behavior analytics model."""
    __tablename__ = "user_behavior"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), nullable=True)
    behavior_type = Column(String(50), nullable=False)  # navigation_pattern, feature_preference, time_spent
    behavior_data = Column(JSON, nullable=False)  # Structured behavior data
    context = Column(JSON, nullable=True)  # Additional context (device, browser, etc.)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_behavior_user', 'user_id'),
        Index('idx_behavior_session', 'session_id'),
        Index('idx_behavior_type', 'behavior_type'),
        Index('idx_behavior_timestamp', 'created_at'),
    )