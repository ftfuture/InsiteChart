"""
Real-time Notification Service for InsiteChart platform.

This service handles real-time notifications for stock price movements,
sentiment changes, and other market events using WebSocket connections.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..models.unified_models import UnifiedStockData, NotificationChannel
from ..cache.unified_cache import UnifiedCacheManager
from .notification_template_service import NotificationTemplateService, TemplateLanguage
from .notification_types import NotificationType, NotificationPriority, NotificationStatus
from .notification_template_service import NotificationTemplate


class NotificationError(Exception):
    """Exception raised for notification-related errors."""
    pass


class Notification:
    """Notification data structure."""
    def __init__(
        self,
        id: str,
        type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        user_id: Optional[str] = None,
        symbol: Optional[str] = None,
        is_read: bool = False,
        expires_at: Optional[datetime] = None,
        channels: Optional[List[NotificationChannel]] = None,
        status: NotificationStatus = NotificationStatus.PENDING,
        scheduled_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None  # For compatibility with tests
    ):
        self.id = id
        self.type = type
        self.priority = priority
        self.title = title
        self.message = message
        self.data = data
        # Use created_at if provided, otherwise use timestamp
        self.timestamp = created_at if created_at is not None else (timestamp or datetime.utcnow())
        self.user_id = user_id
        self.symbol = symbol
        self.is_read = is_read
        self.expires_at = expires_at
        self.channels = channels if channels is not None else [NotificationChannel.WEBSOCKET]
        self.status = status
        self.scheduled_at = scheduled_at
    
    @property
    def created_at(self) -> datetime:
        """Get created_at timestamp for compatibility."""
        return self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "channels": [channel.value for channel in self.channels],
            "data": self.data,
            "status": self.status.value,
            "created_at": self.timestamp.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Notification":
        """Create notification from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            type=NotificationType(data["type"]),
            title=data["title"],
            message=data["message"],
            priority=NotificationPriority(data["priority"]),
            channels=[NotificationChannel(channel) for channel in data["channels"]],
            data=data["data"],
            status=NotificationStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None
        )


class NotificationSubscription(BaseModel):
    """WebSocket subscription model."""
    user_id: str
    symbols: List[str] = []
    notification_types: List[NotificationType] = []
    price_threshold: Optional[float] = None
    sentiment_threshold: Optional[float] = None
    
    # Enhanced personalization options
    notification_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.WEBSOCKET])  # websocket, email, sms, push
    quiet_hours: Optional[Dict[str, Any]] = None  # {"start": "22:00", "end": "08:00", "timezone": "UTC"}
    max_notifications_per_hour: Optional[int] = None
    priority_filter: Optional[List[NotificationPriority]] = None
    
    # Advanced alert conditions
    price_conditions: Optional[Dict[str, Any]] = None  # {"above": 100, "below": 50, "change_pct": 5}
    volume_conditions: Optional[Dict[str, Any]] = None  # {"spike_multiplier": 3, "min_volume": 1000000}
    sentiment_conditions: Optional[Dict[str, Any]] = None  # {"positive_threshold": 0.5, "negative_threshold": -0.5}
    
    # Frequency controls
    cooldown_periods: Optional[Dict[str, int]] = None  # {"price_alert": 300, "sentiment_alert": 600}
    
    # User preferences
    language: str = "en"
    include_technical_indicators: bool = False
    include_news_context: bool = True
    include_sentiment_breakdown: bool = False


class UserNotificationProfile(BaseModel):
    """User notification profile for personalization."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    push_token: Optional[str] = None
    
    # Notification preferences
    preferred_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.WEBSOCKET])
    do_not_disturb: bool = False
    quiet_hours: Optional[Dict[str, Any]] = None
    
    # Risk tolerance and investment style
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    investment_style: str = "balanced"  # value, growth, balanced
    portfolio_value: Optional[float] = None
    
    # Content preferences
    language: str = "en"
    include_technical_analysis: bool = False
    include_fundamental_analysis: bool = True
    include_market_context: bool = True
    
    # Frequency preferences
    max_daily_notifications: int = 50
    max_hourly_notifications: int = 10
    
    # Special interests
    sectors_of_interest: List[str] = []
    watchlist_symbols: List[str] = []
    excluded_symbols: List[str] = []
    
    # Learning preferences
    adaptive_learning: bool = True  # System learns from user behavior
    feedback_weight: float = 0.7  # How much user feedback influences recommendations
    
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


@dataclass
class NotificationRule:
    """Notification rule for advanced filtering."""
    id: str
    user_id: str
    name: str
    type: NotificationType
    conditions: Dict[str, Any]
    template_id: str
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.MEDIUM
    enabled: bool = True
    is_active: bool = True
    actions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def evaluate(self, data: Dict[str, Any]) -> bool:
        """Evaluate if the rule conditions are met."""
        if not self.enabled or not self.is_active:
            return False
        
        # Check symbol condition
        if "symbol" in self.conditions:
            if data.get("symbol") != self.conditions["symbol"]:
                return False
        
        # Check price_above condition
        if "price_above" in self.conditions:
            if data.get("price", 0) <= self.conditions["price_above"]:
                return False
        
        # Check price_below condition
        if "price_below" in self.conditions:
            if data.get("price", float('inf')) >= self.conditions["price_below"]:
                return False
        
        # Add more condition checks as needed
        return True


class RealtimeNotificationService:
    """Real-time notification service using WebSocket."""
    
    def __init__(self, cache_manager: UnifiedCacheManager, email_service=None, push_service=None, sms_service=None, websocket_manager=None):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # External services
        self.email_service = email_service
        self.push_service = push_service
        self.sms_service = sms_service
        self.websocket_manager = websocket_manager
        
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_subscriptions: Dict[str, NotificationSubscription] = {}
        
        # Notification queue
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.processor_task: Optional[asyncio.Task] = None
        
        # Notification history
        self.notification_history: Dict[str, List[Notification]] = {}
        
        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, int]] = {}
        
        # User profiles for personalization
        self.user_profiles: Dict[str, UserNotificationProfile] = {}
        
        # Template service
        self.template_service: Optional[NotificationTemplateService] = None
        
        # Learning system for personalization
        self.user_feedback: Dict[str, List[Dict]] = {}
        self.notification_effectiveness: Dict[str, Dict[str, float]] = {}
        
        # Additional properties for testing
        self.templates: Dict[str, NotificationTemplate] = {}
        self.notification_rules: Dict[str, NotificationRule] = {}
        self.scheduled_notifications: Dict[str, Notification] = {}
        self.total_notifications = 0
        self.successful_notifications = 0
        self.failed_notifications = 0
        self.scheduled_count = 0
        self.scheduler_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        self.logger.info("RealtimeNotificationService initialized")
    
    async def start(self):
        """Start the notification service."""
        try:
            # Initialize template service
            self.template_service = NotificationTemplateService(self.cache_manager)
            await self.template_service.initialize()
            
            # Start background tasks
            self.monitoring_task = asyncio.create_task(self._monitor_market_events())
            self.processor_task = asyncio.create_task(self._process_notifications())
            
            self.logger.info("RealtimeNotificationService started")
            
        except Exception as e:
            self.logger.error(f"Failed to start RealtimeNotificationService: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the notification service."""
        try:
            # Cancel background tasks
            if self.monitoring_task:
                self.monitoring_task.cancel()
            if self.processor_task:
                self.processor_task.cancel()
            
            # Close all connections
            for connection in self.active_connections.values():
                try:
                    await connection.close()
                except Exception:
                    pass
            
            self.active_connections.clear()
            self.user_subscriptions.clear()
            
            self.logger.info("RealtimeNotificationService stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping RealtimeNotificationService: {str(e)}")
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a WebSocket client."""
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            
            # Send welcome message
            welcome_notification = Notification(
                id=f"welcome_{int(datetime.utcnow().timestamp())}",
                type=NotificationType.SYSTEM_NOTIFICATION,
                priority=NotificationPriority.LOW,
                title="Connected to InsiteChart",
                message="You are now connected to real-time notifications",
                data={"user_id": user_id},
                timestamp=datetime.utcnow()
            )
            
            await self._send_notification_to_user(user_id, welcome_notification)
            
            self.logger.info(f"User {user_id} connected to notifications")
            
        except Exception as e:
            self.logger.error(f"Error connecting user {user_id}: {str(e)}")
            raise
    
    async def disconnect(self, user_id: str):
        """Disconnect a WebSocket client."""
        try:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            
            if user_id in self.user_subscriptions:
                del self.user_subscriptions[user_id]
            
            self.logger.info(f"User {user_id} disconnected from notifications")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting user {user_id}: {str(e)}")
    
    async def subscribe(self, user_id: str, subscription: NotificationSubscription):
        """Subscribe user to notifications."""
        try:
            self.user_subscriptions[user_id] = subscription
            
            # Store subscription in cache
            await self.cache_manager.set(
                f"notification_subscription_{user_id}",
                subscription.dict(),
                ttl=3600  # 1 hour
            )
            
            # Send confirmation
            confirmation_notification = Notification(
                id=f"subscription_{int(datetime.utcnow().timestamp())}",
                type=NotificationType.SYSTEM_NOTIFICATION,
                priority=NotificationPriority.LOW,
                title="Subscription Updated",
                message=f"You are now subscribed to {len(subscription.symbols)} symbols",
                data={"symbols": subscription.symbols},
                timestamp=datetime.utcnow(),
                user_id=user_id
            )
            
            await self._send_notification_to_user(user_id, confirmation_notification)
            
            self.logger.info(f"User {user_id} subscribed to notifications")
            
        except Exception as e:
            self.logger.error(f"Error subscribing user {user_id}: {str(e)}")
            raise
    
    async def create_notification(self, notification: Notification):
        """Create and queue a notification with template rendering."""
        try:
            # Apply template if template service is available
            if self.template_service and notification.user_id:
                # Get user profile for language preference
                profile = await self.get_user_profile(notification.user_id)
                language = TemplateLanguage(profile.language) if profile else TemplateLanguage.ENGLISH
                
                # Get best template for this notification type
                template = await self.template_service.get_best_template(
                    notification.type,
                    language,
                    "websocket"
                )
                
                if template:
                    # Prepare template variables
                    variables = self._prepare_template_variables(notification)
                    
                    # Render template
                    rendered = await self.template_service.render_template(template.id, variables)
                    if rendered:
                        # Update notification with rendered content
                        notification.title = rendered["title"]
                        notification.message = rendered["message"]
            
            # Add to queue
            await self.notification_queue.put(notification)
            
            # Add to history
            if notification.user_id:
                if notification.user_id not in self.notification_history:
                    self.notification_history[notification.user_id] = []
                
                self.notification_history[notification.user_id].append(notification)
                
                # Keep only last 100 notifications per user
                if len(self.notification_history[notification.user_id]) > 100:
                    self.notification_history[notification.user_id] = \
                        self.notification_history[notification.user_id][-100:]
            
            self.logger.debug(f"Notification created: {notification.id}")
            
        except Exception as e:
            self.logger.error(f"Error creating notification: {str(e)}")
    
    def _prepare_template_variables(self, notification: Notification) -> Dict[str, Any]:
        """Prepare variables for template rendering."""
        try:
            variables = {
                "symbol": notification.symbol or "",
                "price": notification.data.get("current_price", 0),
                "change_pct": notification.data.get("day_change_pct", 0),
                "change": notification.data.get("day_change", 0),
                "sentiment_score": notification.data.get("sentiment_score", 0),
                "sentiment_type": "positive" if notification.data.get("sentiment_score", 0) > 0 else "negative",
                "score": notification.data.get("trend_score", 0),
                "ratio": notification.data.get("volume_ratio", 0),
                "intensity": notification.data.get("spike_intensity", "moderate"),
                "company_name": notification.data.get("company_name", ""),
                "market_change": notification.data.get("market_change_pct", 0),
                "message": notification.message  # For system notifications
            }
            
            return variables
            
        except Exception as e:
            self.logger.error(f"Error preparing template variables: {str(e)}")
            return {}
    
    async def get_user_notifications(self, user_id: str, limit: int = 50) -> List[Notification]:
        """Get notification history for a user."""
        try:
            # Get from cache first
            cached_notifications = await self.cache_manager.get(f"user_notifications_{user_id}")
            if cached_notifications:
                return [Notification(**notif) for notif in cached_notifications]
            
            # Get from memory
            notifications = self.notification_history.get(user_id, [])
            
            # Cache the result
            await self.cache_manager.set(
                f"user_notifications_{user_id}",
                [asdict(notif) for notif in notifications[-limit:]],
                ttl=300  # 5 minutes
            )
            
            return notifications[-limit:]
            
        except Exception as e:
            self.logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
            return []
    
    async def mark_notification_read(self, user_id: str, notification_id: str):
        """Mark a notification as read."""
        try:
            if user_id in self.notification_history:
                for notification in self.notification_history[user_id]:
                    if notification.id == notification_id:
                        notification.is_read = True
                        break
            
            # Update cache
            notifications = await self.get_user_notifications(user_id)
            await self.cache_manager.set(
                f"user_notifications_{user_id}",
                [asdict(notif) for notif in notifications],
                ttl=300
            )
            
        except Exception as e:
            self.logger.error(f"Error marking notification as read: {str(e)}")
    
    async def _monitor_market_events(self):
        """Monitor market events and generate notifications with improved event handling."""
        try:
            # Create tasks for parallel monitoring
            monitoring_tasks = [
                asyncio.create_task(self._monitor_price_changes()),
                asyncio.create_task(self._monitor_sentiment_changes()),
                asyncio.create_task(self._monitor_trending_stocks()),
                asyncio.create_task(self._monitor_volume_spikes()),
                asyncio.create_task(self._monitor_market_events_external())
            ]
            
            # Wait for all monitoring tasks
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Market monitoring task cancelled")
            # Cancel all sub-tasks
            for task in monitoring_tasks:
                if not task.done():
                    task.cancel()
        except Exception as e:
            self.logger.error(f"Fatal error in market monitoring: {str(e)}")
    
    async def _monitor_price_changes(self):
        """Monitor price changes with improved detection logic."""
        try:
            while True:
                try:
                    # Get all user subscriptions
                    for user_id, subscription in self.user_subscriptions.items():
                        if not subscription.symbols or subscription.price_threshold is None:
                            continue
                        
                        # Batch fetch stock data for efficiency
                        symbols_to_check = subscription.symbols
                        batch_data = await self._batch_fetch_stock_data(symbols_to_check)
                        
                        for symbol in symbols_to_check:
                            if symbol in batch_data:
                                await self._process_price_change_alert(user_id, symbol, batch_data[symbol], subscription)
                    
                    # Dynamic sleep based on market hours
                    sleep_duration = self._get_market_aware_sleep_duration()
                    await asyncio.sleep(sleep_duration)
                    
                except Exception as e:
                    self.logger.error(f"Error in price change monitoring: {str(e)}")
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            self.logger.info("Price change monitoring task cancelled")
    
    async def _monitor_sentiment_changes(self):
        """Monitor sentiment changes with improved detection."""
        try:
            while True:
                try:
                    for user_id, subscription in self.user_subscriptions.items():
                        if not subscription.symbols or subscription.sentiment_threshold is None:
                            continue
                        
                        # Get sentiment history for comparison
                        for symbol in subscription.symbols:
                            await self._process_sentiment_change_alert(user_id, symbol, subscription)
                    
                    await asyncio.sleep(60)  # Check every minute for sentiment changes
                    
                except Exception as e:
                    self.logger.error(f"Error in sentiment change monitoring: {str(e)}")
                    await asyncio.sleep(120)
                    
        except asyncio.CancelledError:
            self.logger.info("Sentiment change monitoring task cancelled")
    
    async def _monitor_trending_stocks(self):
        """Monitor trending stocks with improved detection."""
        try:
            while True:
                try:
                    # Get trending stocks from cache
                    trending_stocks = await self.cache_manager.get("trending_10_24h")
                    
                    if trending_stocks:
                        for user_id, subscription in self.user_subscriptions.items():
                            if not subscription.symbols:
                                continue
                            
                            await self._process_trending_alerts(user_id, trending_stocks, subscription)
                    
                    await asyncio.sleep(300)  # Check every 5 minutes for trending changes
                    
                except Exception as e:
                    self.logger.error(f"Error in trending stocks monitoring: {str(e)}")
                    await asyncio.sleep(300)
                    
        except asyncio.CancelledError:
            self.logger.info("Trending stocks monitoring task cancelled")
    
    async def _monitor_volume_spikes(self):
        """Monitor volume spikes with improved detection."""
        try:
            while True:
                try:
                    for user_id, subscription in self.user_subscriptions.items():
                        if not subscription.symbols:
                            continue
                        
                        # Batch fetch volume data
                        symbols_to_check = subscription.symbols
                        batch_data = await self._batch_fetch_stock_data(symbols_to_check)
                        
                        for symbol in symbols_to_check:
                            if symbol in batch_data:
                                await self._process_volume_spike_alert(user_id, symbol, batch_data[symbol])
                    
                    await asyncio.sleep(60)  # Check every minute for volume spikes
                    
                except Exception as e:
                    self.logger.error(f"Error in volume spike monitoring: {str(e)}")
                    await asyncio.sleep(120)
                    
        except asyncio.CancelledError:
            self.logger.info("Volume spike monitoring task cancelled")
    
    async def _monitor_market_events_external(self):
        """Monitor external market events and news."""
        try:
            while True:
                try:
                    # Check for major market events
                    await self._check_market_events()
                    
                    # Check for significant news
                    await self._check_significant_news()
                    
                    await asyncio.sleep(600)  # Check every 10 minutes for market events
                    
                except Exception as e:
                    self.logger.error(f"Error in external market events monitoring: {str(e)}")
                    await asyncio.sleep(300)
                    
        except asyncio.CancelledError:
            self.logger.info("External market events monitoring task cancelled")
    
    async def _check_price_alerts(self):
        """Check for price movement alerts."""
        try:
            for user_id, subscription in self.user_subscriptions.items():
                if not subscription.symbols or subscription.price_threshold is None:
                    continue
                
                for symbol in subscription.symbols:
                    # Get current stock data
                    cache_key = f"unified_stock_{symbol}_True"
                    stock_data = await self.cache_manager.get(cache_key)
                    
                    if not stock_data:
                        continue
                    
                    stock = UnifiedStockData.from_dict(stock_data)
                    
                    # Check price change
                    if stock.day_change_pct and abs(stock.day_change_pct) >= subscription.price_threshold:
                        # Create price alert notification
                        notification = Notification(
                            id=f"price_{symbol}_{int(datetime.utcnow().timestamp())}",
                            type=NotificationType.PRICE_ALERT,
                            priority=NotificationPriority.HIGH,
                            title=f"Price Alert for {symbol}",
                            message=f"{symbol} moved by {stock.day_change_pct:.2f}%",
                            data={
                                "symbol": symbol,
                                "current_price": stock.current_price,
                                "day_change": stock.day_change,
                                "day_change_pct": stock.day_change_pct,
                                "company_name": stock.company_name
                            },
                            timestamp=datetime.utcnow(),
                            user_id=user_id,
                            symbol=symbol
                        )
                        
                        await self.create_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error checking price alerts: {str(e)}")
    
    async def _check_sentiment_alerts(self):
        """Check for sentiment change alerts."""
        try:
            for user_id, subscription in self.user_subscriptions.items():
                if not subscription.symbols or subscription.sentiment_threshold is None:
                    continue
                
                for symbol in subscription.symbols:
                    # Get current stock data
                    cache_key = f"unified_stock_{symbol}_True"
                    stock_data = await self.cache_manager.get(cache_key)
                    
                    if not stock_data:
                        continue
                    
                    stock = UnifiedStockData.from_dict(stock_data)
                    
                    # Check sentiment change
                    if stock.overall_sentiment and abs(stock.overall_sentiment) >= subscription.sentiment_threshold:
                        sentiment_type = "positive" if stock.overall_sentiment > 0 else "negative"
                        
                        # Create sentiment alert notification
                        notification = Notification(
                            id=f"sentiment_{symbol}_{int(datetime.utcnow().timestamp())}",
                            type=NotificationType.SENTIMENT_ALERT,
                            priority=NotificationPriority.MEDIUM,
                            title=f"Sentiment Alert for {symbol}",
                            message=f"{symbol} showing {sentiment_type} sentiment ({stock.overall_sentiment:.2f})",
                            data={
                                "symbol": symbol,
                                "sentiment_score": stock.overall_sentiment,
                                "mention_count_24h": stock.mention_count_24h,
                                "trending_status": stock.trending_status,
                                "company_name": stock.company_name
                            },
                            timestamp=datetime.utcnow(),
                            user_id=user_id,
                            symbol=symbol
                        )
                        
                        await self.create_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error checking sentiment alerts: {str(e)}")
    
    async def _check_trending_alerts(self):
        """Check for trending stock alerts."""
        try:
            # Get trending stocks
            trending_stocks = await self.cache_manager.get("trending_10_24h")
            
            if not trending_stocks:
                return
            
            for user_id, subscription in self.user_subscriptions.items():
                if not subscription.symbols:
                    continue
                
                for stock_data in trending_stocks:
                    stock = UnifiedStockData.from_dict(stock_data)
                    
                    if stock.symbol in subscription.symbols and stock.trending_status:
                        # Create trending alert notification
                        notification = Notification(
                            id=f"trending_{stock.symbol}_{int(datetime.utcnow().timestamp())}",
                            type=NotificationType.TRENDING_ALERT,
                            priority=NotificationPriority.MEDIUM,
                            title=f"Trending Alert: {stock.symbol}",
                            message=f"{stock.symbol} is now trending with score {stock.trend_score:.1f}",
                            data={
                                "symbol": stock.symbol,
                                "trend_score": stock.trend_score,
                                "mention_count_24h": stock.mention_count_24h,
                                "overall_sentiment": stock.overall_sentiment,
                                "company_name": stock.company_name
                            },
                            timestamp=datetime.utcnow(),
                            user_id=user_id,
                            symbol=stock.symbol
                        )
                        
                        await self.create_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error checking trending alerts: {str(e)}")
    
    async def _check_volume_spike_alerts(self):
        """Check for volume spike alerts."""
        try:
            for user_id, subscription in self.user_subscriptions.items():
                if not subscription.symbols:
                    continue
                
                for symbol in subscription.symbols:
                    # Get current stock data
                    cache_key = f"unified_stock_{symbol}_True"
                    stock_data = await self.cache_manager.get(cache_key)
                    
                    if not stock_data:
                        continue
                    
                    stock = UnifiedStockData.from_dict(stock_data)
                    
                    # Check for volume spike (volume > 3x average)
                    if (stock.volume and stock.avg_volume and 
                        stock.volume > stock.avg_volume * 3):
                        
                        # Create volume spike notification
                        notification = Notification(
                            id=f"volume_{symbol}_{int(datetime.utcnow().timestamp())}",
                            type=NotificationType.VOLUME_SPIKE,
                            priority=NotificationPriority.HIGH,
                            title=f"Volume Spike: {symbol}",
                            message=f"{symbol} volume is {stock.volume / stock.avg_volume:.1f}x average",
                            data={
                                "symbol": symbol,
                                "current_volume": stock.volume,
                                "average_volume": stock.avg_volume,
                                "volume_ratio": stock.volume / stock.avg_volume,
                                "company_name": stock.company_name
                            },
                            timestamp=datetime.utcnow(),
                            user_id=user_id,
                            symbol=symbol
                        )
                        
                        await self.create_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Error checking volume spike alerts: {str(e)}")
    
    async def _process_notifications(self):
        """Process notifications from the queue."""
        try:
            while True:
                try:
                    # Get notification from queue
                    notification = await self.notification_queue.get()
                    
                    # Check rate limiting
                    if await self._is_rate_limited(notification):
                        continue
                    
                    # Send to user if specified
                    if notification.user_id:
                        await self._send_notification_to_user(notification.user_id, notification)
                    
                    # Send to all subscribed users if no specific user
                    else:
                        await self._broadcast_notification(notification)
                    
                    # Mark task as done
                    self.notification_queue.task_done()
                    
                except Exception as e:
                    self.logger.error(f"Error processing notification: {str(e)}")
                    
        except asyncio.CancelledError:
            self.logger.info("Notification processor task cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in notification processor: {str(e)}")
    
    async def _send_notification_to_user(self, user_id: str, notification: Notification):
        """Send notification to a specific user with personalization."""
        try:
            # Check if notification should be sent based on user preferences
            if not await self.should_send_notification(notification, user_id):
                self.logger.debug(f"Notification filtered for user {user_id}: {notification.id}")
                return
            
            # Personalize notification
            personalized_notification = await self.personalize_notification(notification, user_id)
            
            if user_id not in self.active_connections:
                return
            
            websocket = self.active_connections[user_id]
            
            # Prepare notification data
            notification_data = {
                "id": personalized_notification.id,
                "type": personalized_notification.type.value,
                "priority": personalized_notification.priority.value,
                "title": personalized_notification.title,
                "message": personalized_notification.message,
                "data": personalized_notification.data,
                "timestamp": personalized_notification.timestamp.isoformat(),
                "symbol": personalized_notification.symbol,
                "is_read": personalized_notification.is_read,
                "personalized": True
            }
            
            # Send via WebSocket
            await websocket.send_text(json.dumps(notification_data))
            
            self.logger.debug(f"Personalized notification sent to user {user_id}: {notification.id}")
            
        except WebSocketDisconnect:
            # User disconnected, remove from active connections
            await self.disconnect(user_id)
        except Exception as e:
            self.logger.error(f"Error sending notification to user {user_id}: {str(e)}")
    
    async def _broadcast_notification(self, notification: Notification):
        """Broadcast notification to all relevant users."""
        try:
            # Find relevant users based on subscription
            relevant_users = []
            
            for user_id, subscription in self.user_subscriptions.items():
                # Check if user is subscribed to this notification type
                if (notification.type in subscription.notification_types or 
                    not subscription.notification_types):
                    
                    # Check if symbol is in user's subscription
                    if (not notification.symbol or 
                        notification.symbol in subscription.symbols or 
                        not subscription.symbols):
                        relevant_users.append(user_id)
            
            # Send to all relevant users
            for user_id in relevant_users:
                await self._send_notification_to_user(user_id, notification)
            
        except Exception as e:
            self.logger.error(f"Error broadcasting notification: {str(e)}")
    
    async def _is_rate_limited(self, notification: Notification) -> bool:
        """Check if notification should be rate limited."""
        try:
            if not notification.user_id:
                return False
            
            user_id = notification.user_id
            current_time = datetime.utcnow()
            minute_key = current_time.strftime("%Y%m%d%H%M")
            
            # Initialize rate limit tracking
            if user_id not in self.rate_limits:
                self.rate_limits[user_id] = {}
            
            # Count notifications in current minute
            if minute_key not in self.rate_limits[user_id]:
                self.rate_limits[user_id][minute_key] = 0
            
            self.rate_limits[user_id][minute_key] += 1
            
            # Rate limits per minute based on priority
            rate_limits = {
                NotificationPriority.LOW: 10,
                NotificationPriority.MEDIUM: 20,
                NotificationPriority.HIGH: 30,
                NotificationPriority.CRITICAL: 50
            }
            
            max_per_minute = rate_limits.get(notification.priority, 20)
            
            # Clean old entries (older than 5 minutes)
            old_keys = [
                key for key in self.rate_limits[user_id].keys()
                if int(key) < int(current_time.strftime("%Y%m%d%H%M")) - 5
            ]
            for key in old_keys:
                del self.rate_limits[user_id][key]
            
            # Check if rate limited
            return self.rate_limits[user_id][minute_key] > max_per_minute
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {str(e)}")
            return False
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        try:
            return {
                "active_connections": len(self.active_connections),
                "user_subscriptions": len(self.user_subscriptions),
                "queue_size": self.notification_queue.qsize(),
                "notification_history_size": sum(
                    len(notifications) 
                    for notifications in self.notification_history.values()
                ),
                "monitoring_task_active": self.monitoring_task and not self.monitoring_task.done(),
                "processor_task_active": self.processor_task and not self.processor_task.done(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system stats: {str(e)}")
            return {}


    async def _batch_fetch_stock_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Batch fetch stock data for efficiency."""
        try:
            batch_data = {}
            
            # Use cache manager to batch fetch
            for symbol in symbols:
                cache_key = f"unified_stock_{symbol}_True"
                stock_data = await self.cache_manager.get(cache_key)
                if stock_data:
                    batch_data[symbol] = stock_data
            
            return batch_data
            
        except Exception as e:
            self.logger.error(f"Error batch fetching stock data: {str(e)}")
            return {}
    
    def _get_market_aware_sleep_duration(self) -> int:
        """Get sleep duration based on market hours."""
        try:
            from datetime import datetime
            import pytz
            
            # Get current time in US/Eastern timezone
            eastern = pytz.timezone('US/Eastern')
            now = datetime.now(eastern)
            
            # Check if market is open (9:30 AM - 4:00 PM ET, Monday-Friday)
            is_weekday = now.weekday() < 5
            is_market_hours = 9 <= now.hour < 16
            
            if is_weekday and is_market_hours:
                return 15  # Check every 15 seconds during market hours
            else:
                return 60  # Check every minute outside market hours
                
        except Exception:
            return 30  # Default to 30 seconds if timezone check fails
    
    async def _process_price_change_alert(self, user_id: str, symbol: str, stock_data: Dict, subscription: NotificationSubscription):
        """Process price change alert for a specific symbol."""
        try:
            stock = UnifiedStockData.from_dict(stock_data)
            
            # Check price change with improved logic
            if stock.day_change_pct and abs(stock.day_change_pct) >= subscription.price_threshold:
                # Get previous price data for comparison
                previous_data_key = f"price_history_{symbol}"
                previous_data = await self.cache_manager.get(previous_data_key)
                
                # Create enhanced price alert notification
                notification = Notification(
                    id=f"price_{symbol}_{int(datetime.utcnow().timestamp())}",
                    type=NotificationType.PRICE_ALERT,
                    priority=NotificationPriority.HIGH if abs(stock.day_change_pct) >= 10 else NotificationPriority.MEDIUM,
                    title=f"Price Alert for {symbol}",
                    message=f"{symbol} moved by {stock.day_change_pct:.2f}%",
                    data={
                        "symbol": symbol,
                        "current_price": stock.current_price,
                        "day_change": stock.day_change,
                        "day_change_pct": stock.day_change_pct,
                        "company_name": stock.company_name,
                        "volume": stock.volume,
                        "previous_close": stock.previous_close,
                        "market_cap": getattr(stock, 'market_cap', None),
                        "pe_ratio": getattr(stock, 'pe_ratio', None)
                    },
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    symbol=symbol
                )
                
                await self.create_notification(notification)
                
                # Update price history
                await self.cache_manager.set(
                    previous_data_key,
                    {
                        "price": stock.current_price,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    ttl=3600
                )
                
        except Exception as e:
            self.logger.error(f"Error processing price change alert for {symbol}: {str(e)}")
    
    async def _process_sentiment_change_alert(self, user_id: str, symbol: str, subscription: NotificationSubscription):
        """Process sentiment change alert for a specific symbol."""
        try:
            cache_key = f"unified_stock_{symbol}_True"
            stock_data = await self.cache_manager.get(cache_key)
            
            if not stock_data:
                return
            
            stock = UnifiedStockData.from_dict(stock_data)
            
            # Get sentiment history for comparison
            sentiment_history_key = f"sentiment_history_{symbol}"
            sentiment_history = await self.cache_manager.get(sentiment_history_key) or []
            
            # Check for significant sentiment change
            if stock.overall_sentiment and abs(stock.overall_sentiment) >= subscription.sentiment_threshold:
                # Compare with previous sentiment
                previous_sentiment = sentiment_history[-1] if sentiment_history else 0
                sentiment_change = stock.overall_sentiment - previous_sentiment
                
                # Only alert if there's a significant change
                if abs(sentiment_change) >= 0.2:
                    sentiment_type = "positive" if stock.overall_sentiment > 0 else "negative"
                    change_direction = "increased" if sentiment_change > 0 else "decreased"
                    
                    # Create enhanced sentiment alert notification
                    notification = Notification(
                        id=f"sentiment_{symbol}_{int(datetime.utcnow().timestamp())}",
                        type=NotificationType.SENTIMENT_ALERT,
                        priority=NotificationPriority.MEDIUM,
                        title=f"Sentiment Alert for {symbol}",
                        message=f"{symbol} sentiment {change_direction} to {sentiment_type} ({stock.overall_sentiment:.2f})",
                        data={
                            "symbol": symbol,
                            "sentiment_score": stock.overall_sentiment,
                            "previous_sentiment": previous_sentiment,
                            "sentiment_change": sentiment_change,
                            "mention_count_24h": stock.mention_count_24h,
                            "trending_status": stock.trending_status,
                            "company_name": stock.company_name,
                            "sentiment_sources": getattr(stock, 'sentiment_sources', {}),
                            "news_sentiment": getattr(stock, 'news_sentiment', None),
                            "social_sentiment": getattr(stock, 'social_sentiment', None)
                        },
                        timestamp=datetime.utcnow(),
                        user_id=user_id,
                        symbol=symbol
                    )
                    
                    await self.create_notification(notification)
                    
                    # Update sentiment history
                    sentiment_history.append(stock.overall_sentiment)
                    if len(sentiment_history) > 10:  # Keep only last 10 entries
                        sentiment_history = sentiment_history[-10:]
                    
                    await self.cache_manager.set(
                        sentiment_history_key,
                        sentiment_history,
                        ttl=3600
                    )
                
        except Exception as e:
            self.logger.error(f"Error processing sentiment change alert for {symbol}: {str(e)}")
    
    async def _process_trending_alerts(self, user_id: str, trending_stocks: List[Dict], subscription: NotificationSubscription):
        """Process trending alerts for a user."""
        try:
            for stock_data in trending_stocks:
                stock = UnifiedStockData.from_dict(stock_data)
                
                if stock.symbol in subscription.symbols and stock.trending_status:
                    # Check if this is a new trending stock
                    trending_history_key = f"trending_history_{user_id}"
                    trending_history = await self.cache_manager.get(trending_history_key) or []
                    
                    # Check if we already notified about this stock trending
                    already_notified = any(
                        item.get("symbol") == stock.symbol and
                        (datetime.utcnow() - datetime.fromisoformat(item.get("timestamp", ""))).total_seconds() < 3600
                        for item in trending_history
                    )
                    
                    if not already_notified:
                        # Create enhanced trending alert notification
                        notification = Notification(
                            id=f"trending_{stock.symbol}_{int(datetime.utcnow().timestamp())}",
                            type=NotificationType.TRENDING_ALERT,
                            priority=NotificationPriority.MEDIUM,
                            title=f"Trending Alert: {stock.symbol}",
                            message=f"{stock.symbol} is now trending with score {stock.trend_score:.1f}",
                            data={
                                "symbol": stock.symbol,
                                "trend_score": stock.trend_score,
                                "mention_count_24h": stock.mention_count_24h,
                                "overall_sentiment": stock.overall_sentiment,
                                "company_name": stock.company_name,
                                "trending_rank": getattr(stock, 'trending_rank', None),
                                "trending_duration": getattr(stock, 'trending_duration', None),
                                "related_symbols": getattr(stock, 'related_symbols', [])
                            },
                            timestamp=datetime.utcnow(),
                            user_id=user_id,
                            symbol=stock.symbol
                        )
                        
                        await self.create_notification(notification)
                        
                        # Update trending history
                        trending_history.append({
                            "symbol": stock.symbol,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        await self.cache_manager.set(
                            trending_history_key,
                            trending_history,
                            ttl=3600
                        )
                
        except Exception as e:
            self.logger.error(f"Error processing trending alerts for user {user_id}: {str(e)}")
    
    async def _process_volume_spike_alert(self, user_id: str, symbol: str, stock_data: Dict):
        """Process volume spike alert for a specific symbol."""
        try:
            stock = UnifiedStockData.from_dict(stock_data)
            
            # Enhanced volume spike detection
            if (stock.volume and stock.avg_volume and
                stock.volume > stock.avg_volume * 3):
                
                # Get volume history for comparison
                volume_history_key = f"volume_history_{symbol}"
                volume_history = await self.cache_manager.get(volume_history_key) or []
                
                # Calculate volume spike intensity
                volume_ratio = stock.volume / stock.avg_volume
                spike_intensity = "moderate" if volume_ratio < 5 else "high" if volume_ratio < 10 else "extreme"
                
                # Create enhanced volume spike notification
                notification = Notification(
                    id=f"volume_{symbol}_{int(datetime.utcnow().timestamp())}",
                    type=NotificationType.VOLUME_SPIKE,
                    priority=NotificationPriority.HIGH if volume_ratio > 5 else NotificationPriority.MEDIUM,
                    title=f"Volume Spike: {symbol}",
                    message=f"{symbol} volume is {volume_ratio:.1f}x average ({spike_intensity} spike)",
                    data={
                        "symbol": symbol,
                        "current_volume": stock.volume,
                        "average_volume": stock.avg_volume,
                        "volume_ratio": volume_ratio,
                        "spike_intensity": spike_intensity,
                        "company_name": stock.company_name,
                        "current_price": stock.current_price,
                        "day_change_pct": stock.day_change_pct,
                        "volume_history": volume_history[-5:] if volume_history else [],
                        "market_cap": getattr(stock, 'market_cap', None)
                    },
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    symbol=symbol
                )
                
                await self.create_notification(notification)
                
                # Update volume history
                volume_history.append({
                    "volume": stock.volume,
                    "timestamp": datetime.utcnow().isoformat()
                })
                if len(volume_history) > 20:  # Keep last 20 entries
                    volume_history = volume_history[-20:]
                
                await self.cache_manager.set(
                    volume_history_key,
                    volume_history,
                    ttl=3600
                )
                
        except Exception as e:
            self.logger.error(f"Error processing volume spike alert for {symbol}: {str(e)}")
    
    async def _check_market_events(self):
        """Check for major market events."""
        try:
            # Get market-wide data
            market_data = await self.cache_manager.get("market_overview")
            
            if not market_data:
                return
            
            # Check for major market movements
            market_change = market_data.get("market_change_pct", 0)
            
            if abs(market_change) >= 2.0:  # 2% market movement
                # Create market event notification
                notification = Notification(
                    id=f"market_event_{int(datetime.utcnow().timestamp())}",
                    type=NotificationType.MARKET_EVENT,
                    priority=NotificationPriority.HIGH if abs(market_change) >= 3.0 else NotificationPriority.MEDIUM,
                    title=f"Market Event: {market_change:+.2f}%",
                    message=f"Market moved by {market_change:+.2f}%",
                    data={
                        "market_change_pct": market_change,
                        "market_index": market_data.get("market_index", "Unknown"),
                        "market_volume": market_data.get("market_volume"),
                        "volatility_index": market_data.get("volatility_index"),
                        "sector_performance": market_data.get("sector_performance", {}),
                        "market_sentiment": market_data.get("market_sentiment"),
                        "key_movers": market_data.get("key_movers", [])
                    },
                    timestamp=datetime.utcnow()
                )
                
                await self.create_notification(notification)
                
        except Exception as e:
            self.logger.error(f"Error checking market events: {str(e)}")
    
    async def _check_significant_news(self):
        """Check for significant news that might affect stocks."""
        try:
            # Get recent news
            recent_news = await self.cache_manager.get("recent_financial_news")
            
            if not recent_news:
                return
            
            # Check for high-impact news
            high_impact_news = [
                news for news in recent_news
                if news.get("impact_score", 0) >= 7
            ]
            
            for news in high_impact_news:
                # Check if we already sent this news notification
                news_notification_key = f"news_notification_{news.get('id')}"
                already_sent = await self.cache_manager.get(news_notification_key)
                
                if not already_sent:
                    # Create news notification
                    notification = Notification(
                        id=f"news_{news.get('id')}_{int(datetime.utcnow().timestamp())}",
                        type=NotificationType.MARKET_EVENT,
                        priority=NotificationPriority.HIGH if news.get("impact_score", 0) >= 9 else NotificationPriority.MEDIUM,
                        title=f"Breaking News: {news.get('headline', 'Market News')}",
                        message=news.get("summary", "Significant market news detected"),
                        data={
                            "news_id": news.get("id"),
                            "headline": news.get("headline"),
                            "summary": news.get("summary"),
                            "impact_score": news.get("impact_score"),
                            "affected_symbols": news.get("affected_symbols", []),
                            "news_source": news.get("source"),
                            "publication_time": news.get("publication_time"),
                            "news_category": news.get("category"),
                            "sentiment": news.get("sentiment")
                        },
                        timestamp=datetime.utcnow()
                    )
                    
                    await self.create_notification(notification)
                    
                    # Mark as sent
                    await self.cache_manager.set(
                        news_notification_key,
                        True,
                        ttl=3600  # Don't send same news for 1 hour
                    )
                
        except Exception as e:
            self.logger.error(f"Error checking significant news: {str(e)}")
    
    async def create_user_profile(self, profile: UserNotificationProfile) -> bool:
        """Create or update user notification profile."""
        try:
            # Store in memory
            self.user_profiles[profile.user_id] = profile
            
            # Store in cache
            await self.cache_manager.set(
                f"user_profile_{profile.user_id}",
                profile.dict(),
                ttl=86400  # 24 hours
            )
            
            # Initialize feedback tracking
            if profile.user_id not in self.user_feedback:
                self.user_feedback[profile.user_id] = []
            
            # Initialize effectiveness tracking
            if profile.user_id not in self.notification_effectiveness:
                self.notification_effectiveness[profile.user_id] = {}
            
            self.logger.info(f"Created/updated user profile for {profile.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating user profile: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[UserNotificationProfile]:
        """Get user notification profile."""
        try:
            # Get from memory first
            if user_id in self.user_profiles:
                return self.user_profiles[user_id]
            
            # Get from cache
            cached_profile = await self.cache_manager.get(f"user_profile_{user_id}")
            if cached_profile:
                profile = UserNotificationProfile(**cached_profile)
                self.user_profiles[user_id] = profile
                return profile
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def should_send_notification(self, notification: Notification, user_id: str) -> bool:
        """Check if notification should be sent based on user preferences."""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return True  # Default to sending if no profile
            
            # Check do not disturb
            if profile.do_not_disturb:
                return False
            
            # Check quiet hours
            if profile.quiet_hours and self._is_in_quiet_hours(profile.quiet_hours):
                return False
            
            # Check priority filter
            subscription = self.user_subscriptions.get(user_id)
            if subscription and subscription.priority_filter and notification.priority not in subscription.priority_filter:
                return False
            
            # Check frequency limits
            if not await self._check_frequency_limits(notification, user_id, profile):
                return False
            
            # Check cooldown periods
            if subscription and not await self._check_cooldown_periods(notification, user_id, subscription):
                return False
            
            # Check adaptive learning
            if profile.adaptive_learning:
                if not await self._check_notification_relevance(notification, user_id):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if notification should be sent: {str(e)}")
            return True  # Default to sending on error
    
    def _is_in_quiet_hours(self, quiet_hours: Dict[str, Any]) -> bool:
        """Check if current time is in quiet hours."""
        try:
            from datetime import datetime
            import pytz
            
            # Get user's timezone
            user_timezone = quiet_hours.get("timezone", "UTC")
            tz = pytz.timezone(user_timezone)
            
            # Get current time in user's timezone
            now = datetime.now(tz)
            current_time = now.strftime("%H:%M")
            
            start_time = quiet_hours.get("start", "22:00")
            end_time = quiet_hours.get("end", "08:00")
            
            # Check if current time is in quiet hours
            if start_time <= end_time:
                # Normal case (e.g., 22:00 to 08:00 next day)
                return start_time <= current_time <= end_time
            else:
                # Overnight case (e.g., 22:00 to 08:00)
                return current_time >= start_time or current_time <= end_time
                
        except Exception:
            return False
    
    async def _check_frequency_limits(self, notification: Notification, user_id: str, profile: UserNotificationProfile) -> bool:
        """Check if user has exceeded frequency limits."""
        try:
            current_time = datetime.utcnow()
            hour_key = current_time.strftime("%Y%m%d%H")
            day_key = current_time.strftime("%Y%m%d")
            
            # Initialize tracking if needed
            if user_id not in self.rate_limits:
                self.rate_limits[user_id] = {}
            
            # Get current counts
            hourly_count = self.rate_limits[user_id].get(f"hourly_{hour_key}", 0)
            daily_count = self.rate_limits[user_id].get(f"daily_{day_key}", 0)
            
            # Check limits
            if hourly_count >= profile.max_hourly_notifications:
                return False
            
            if daily_count >= profile.max_daily_notifications:
                return False
            
            # Update counts
            self.rate_limits[user_id][f"hourly_{hour_key}"] = hourly_count + 1
            self.rate_limits[user_id][f"daily_{day_key}"] = daily_count + 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking frequency limits: {str(e)}")
            return True
    
    async def _check_cooldown_periods(self, notification: Notification, user_id: str, subscription: NotificationSubscription) -> bool:
        """Check if notification is in cooldown period."""
        try:
            if not subscription.cooldown_periods:
                return True
            
            cooldown_key = f"cooldown_{user_id}_{notification.type.value}"
            last_sent = await self.cache_manager.get(cooldown_key)
            
            if last_sent:
                cooldown_period = subscription.cooldown_periods.get(notification.type.value, 0)
                time_since_last = (datetime.utcnow() - datetime.fromisoformat(last_sent)).total_seconds()
                
                if time_since_last < cooldown_period:
                    return False
            
            # Update last sent time
            await self.cache_manager.set(
                cooldown_key,
                datetime.utcnow().isoformat(),
                ttl=3600  # 1 hour
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking cooldown periods: {str(e)}")
            return True
    
    async def _check_notification_relevance(self, notification: Notification, user_id: str) -> bool:
        """Check notification relevance based on user behavior and feedback."""
        try:
            if user_id not in self.notification_effectiveness:
                return True
            
            effectiveness = self.notification_effectiveness[user_id]
            notification_type = notification.type.value
            
            # Get effectiveness score for this notification type
            type_effectiveness = effectiveness.get(notification_type, 0.5)
            
            # Get relevance score based on user's interests
            relevance_score = await self._calculate_relevance_score(notification, user_id)
            
            # Combine scores
            combined_score = (type_effectiveness * 0.6) + (relevance_score * 0.4)
            
            # Send if score is above threshold
            return combined_score >= 0.3
            
        except Exception as e:
            self.logger.error(f"Error checking notification relevance: {str(e)}")
            return True
    
    async def _calculate_relevance_score(self, notification: Notification, user_id: str) -> float:
        """Calculate relevance score based on user's interests and behavior."""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return 0.5  # Default relevance
            
            score = 0.5  # Base score
            
            # Check if symbol is in watchlist
            if notification.symbol and notification.symbol in profile.watchlist_symbols:
                score += 0.3
            
            # Check if symbol is in excluded list
            if notification.symbol and notification.symbol in profile.excluded_symbols:
                score -= 0.4
            
            # Check sector relevance
            if hasattr(notification, 'sector') and notification.sector in profile.sectors_of_interest:
                score += 0.2
            
            # Check investment style alignment
            if notification.type == NotificationType.PRICE_ALERT:
                if profile.investment_style == "growth" and notification.data.get("day_change_pct", 0) > 0:
                    score += 0.1
                elif profile.investment_style == "value" and notification.data.get("day_change_pct", 0) < 0:
                    score += 0.1
            
            # Normalize score
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {str(e)}")
            return 0.5
    
    async def record_user_feedback(self, user_id: str, notification_id: str, feedback: Dict[str, Any]) -> bool:
        """Record user feedback for learning."""
        try:
            # Store feedback
            feedback_entry = {
                "notification_id": notification_id,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if user_id not in self.user_feedback:
                self.user_feedback[user_id] = []
            
            self.user_feedback[user_id].append(feedback_entry)
            
            # Keep only last 100 feedback entries
            if len(self.user_feedback[user_id]) > 100:
                self.user_feedback[user_id] = self.user_feedback[user_id][-100:]
            
            # Update effectiveness scores
            await self._update_effectiveness_scores(user_id, feedback)
            
            # Store in cache
            await self.cache_manager.set(
                f"user_feedback_{user_id}",
                self.user_feedback[user_id],
                ttl=86400
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording user feedback: {str(e)}")
            return False
    
    async def _update_effectiveness_scores(self, user_id: str, feedback: Dict[str, Any]):
        """Update notification effectiveness scores based on feedback."""
        try:
            if user_id not in self.notification_effectiveness:
                self.notification_effectiveness[user_id] = {}
            
            notification_type = feedback.get("notification_type")
            user_rating = feedback.get("rating", 0)  # -1 to 1 scale
            
            if notification_type:
                current_score = self.notification_effectiveness[user_id].get(notification_type, 0.5)
                
                # Update with exponential moving average
                alpha = 0.1  # Learning rate
                new_score = (alpha * user_rating) + ((1 - alpha) * current_score)
                
                self.notification_effectiveness[user_id][notification_type] = new_score
            
        except Exception as e:
            self.logger.error(f"Error updating effectiveness scores: {str(e)}")
    
    async def personalize_notification(self, notification: Notification, user_id: str) -> Notification:
        """Personalize notification based on user profile."""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return notification
            
            # Create a copy to modify
            personalized_notification = Notification(
                id=notification.id,
                type=notification.type,
                priority=notification.priority,
                title=notification.title,
                message=notification.message,
                data=notification.data.copy(),
                timestamp=notification.timestamp,
                user_id=notification.user_id,
                symbol=notification.symbol,
                is_read=notification.is_read,
                expires_at=notification.expires_at
            )
            
            # Personalize content based on preferences
            if profile.include_technical_analysis and notification.symbol:
                # Add technical indicators to data
                technical_data = await self._get_technical_indicators(notification.symbol)
                if technical_data:
                    personalized_notification.data["technical_indicators"] = technical_data
            
            if profile.include_fundamental_analysis and notification.symbol:
                # Add fundamental analysis to data
                fundamental_data = await self._get_fundamental_analysis(notification.symbol)
                if fundamental_data:
                    personalized_notification.data["fundamental_analysis"] = fundamental_data
            
            if profile.include_market_context:
                # Add market context to data
                market_context = await self._get_market_context()
                if market_context:
                    personalized_notification.data["market_context"] = market_context
            
            # Adjust message based on risk tolerance
            personalized_notification.message = self._adjust_message_for_risk_tolerance(
                personalized_notification.message, profile.risk_tolerance
            )
            
            return personalized_notification
            
        except Exception as e:
            self.logger.error(f"Error personalizing notification: {str(e)}")
            return notification
    
    async def _get_technical_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get technical indicators for a symbol."""
        try:
            # This would integrate with a technical analysis service
            # For now, return mock data
            return {
                "rsi": 65.5,
                "macd": 0.12,
                "bollinger_upper": 105.50,
                "bollinger_lower": 95.25,
                "moving_average_50": 98.75,
                "moving_average_200": 95.30
            }
        except Exception:
            return None
    
    async def _get_fundamental_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get fundamental analysis for a symbol."""
        try:
            # This would integrate with a fundamental analysis service
            # For now, return mock data
            return {
                "pe_ratio": 18.5,
                "pb_ratio": 2.3,
                "eps": 4.25,
                "revenue_growth": 0.12,
                "debt_to_equity": 0.45,
                "roe": 0.15
            }
        except Exception:
            return None
    
    async def _get_market_context(self) -> Optional[Dict[str, Any]]:
        """Get current market context."""
        try:
            # This would integrate with market data service
            # For now, return mock data
            return {
                "market_sentiment": "bullish",
                "volatility_index": 18.5,
                "sector_performance": {
                    "technology": 0.025,
                    "healthcare": 0.015,
                    "finance": 0.010
                },
                "major_indices": {
                    "S&P_500": 0.012,
                    "NASDAQ": 0.018,
                    "DOW": 0.008
                }
            }
        except Exception:
            return None
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send notification through appropriate channels."""
        try:
            success_count = 0
            total_channels = len(notification.channels)
            
            for channel in notification.channels:
                if channel == NotificationChannel.EMAIL and self.email_service:
                    result = await self._send_via_email(notification)
                    if result:
                        success_count += 1
                elif channel == NotificationChannel.PUSH and self.push_service:
                    result = await self._send_via_push(notification)
                    if result:
                        success_count += 1
                elif channel == NotificationChannel.SMS and self.sms_service:
                    result = await self._send_via_sms(notification)
                    if result:
                        success_count += 1
                elif channel == NotificationChannel.WEBSOCKET and notification.user_id:
                    result = await self._send_notification_to_user(notification.user_id, notification)
                    if result:
                        success_count += 1
            
            # Update statistics
            self.total_notifications += 1
            if success_count > 0:
                self.successful_notifications += 1
                if success_count == total_channels:
                    notification.status = NotificationStatus.SENT
                else:
                    notification.status = NotificationStatus.PARTIAL_SENT
                return True
            else:
                self.failed_notifications += 1
                notification.status = NotificationStatus.FAILED
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending notification: {str(e)}")
            notification.status = NotificationStatus.FAILED
            return False
    
    async def _send_via_email(self, notification: Notification) -> bool:
        """Send notification via email."""
        try:
            if self.email_service:
                return await self.email_service.send_email(
                    user_id=notification.user_id,
                    subject=notification.title,
                    body=notification.message
                )
            return False
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return False
    
    async def _send_via_push(self, notification: Notification) -> bool:
        """Send notification via push."""
        try:
            if self.push_service:
                return await self.push_service.send_push_notification(
                    user_id=notification.user_id,
                    title=notification.title,
                    message=notification.message,
                    data=notification.data
                )
            return False
        except Exception as e:
            self.logger.error(f"Error sending push: {str(e)}")
            return False
    
    async def _send_via_sms(self, notification: Notification) -> bool:
        """Send notification via SMS."""
        try:
            if self.sms_service:
                return await self.sms_service.send_sms(
                    user_id=notification.user_id,
                    message=notification.message
                )
            return False
        except Exception as e:
            self.logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    async def _send_via_websocket(self, notification: Notification) -> bool:
        """Send notification via WebSocket."""
        try:
            # Check if we have a websocket manager or direct connection
            if self.websocket_manager:
                # Use websocket manager
                return await self.websocket_manager.send_notification(
                    user_id=notification.user_id,
                    notification=notification.to_dict()
                )
            elif notification.user_id and notification.user_id in self.active_connections:
                # Use direct connection
                websocket = self.active_connections[notification.user_id]
                
                # Prepare notification data
                notification_data = {
                    "id": notification.id,
                    "type": notification.type.value,
                    "priority": notification.priority.value,
                    "title": notification.title,
                    "message": notification.message,
                    "data": notification.data,
                    "timestamp": notification.timestamp.isoformat(),
                    "symbol": notification.symbol,
                    "is_read": notification.is_read
                }
                
                # Send via WebSocket
                await websocket.send_text(json.dumps(notification_data))
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error sending WebSocket notification: {str(e)}")
            return False
    
    async def create_notification_from_template(
        self,
        template_id: str,
        user_id: str,
        data: Dict[str, Any]
    ) -> Notification:
        """Create notification from template."""
        try:
            template = self.templates.get(template_id)
            if not template:
                raise NotificationError("Template not found")
            
            title, message = template.render(data)
            
            notification = Notification(
                id=f"notif_{int(datetime.utcnow().timestamp())}",
                user_id=user_id,
                type=template.type,
                title=title,
                message=message,
                priority=template.default_priority,
                channels=template.default_channels,
                data=data,
                status=NotificationStatus.PENDING
            )
            
            return notification
            
        except Exception as e:
            if isinstance(e, NotificationError):
                raise
            raise NotificationError(f"Template rendering failed: {str(e)}")
    
    async def schedule_notification(self, notification: Notification) -> bool:
        """Schedule a notification for future delivery."""
        try:
            if notification.scheduled_at and notification.scheduled_at <= datetime.utcnow():
                return False
            
            # Set status to SCHEDULED before adding to the dictionary
            notification.status = NotificationStatus.SCHEDULED
            self.scheduled_notifications[notification.id] = notification
            self.scheduled_count += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling notification: {str(e)}")
            return False
    
    async def cancel_scheduled_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification."""
        try:
            if notification_id in self.scheduled_notifications:
                del self.scheduled_notifications[notification_id]
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error canceling scheduled notification: {str(e)}")
            return False
    
    async def _process_scheduled_notifications(self):
        """Process scheduled notifications."""
        try:
            current_time = datetime.utcnow()
            notifications_to_send = []
            
            for notification_id, notification in self.scheduled_notifications.items():
                if (notification.scheduled_at and
                    notification.scheduled_at <= current_time):
                    notifications_to_send.append(notification)
            
            for notification in notifications_to_send:
                await self.send_notification(notification)
                del self.scheduled_notifications[notification.id]
                
        except Exception as e:
            self.logger.error(f"Error processing scheduled notifications: {str(e)}")
    
    async def add_notification_rule(self, rule: NotificationRule) -> bool:
        """Add a notification rule."""
        try:
            self.notification_rules[rule.id] = rule
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding notification rule: {str(e)}")
            return False
    
    async def remove_notification_rule(self, rule_id: str) -> bool:
        """Remove a notification rule."""
        try:
            if rule_id in self.notification_rules:
                del self.notification_rules[rule_id]
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing notification rule: {str(e)}")
            return False
    
    async def evaluate_rules(self, data: Dict[str, Any]) -> List[Notification]:
        """Evaluate notification rules and create notifications."""
        try:
            notifications = []
            
            for rule in self.notification_rules.values():
                if rule.evaluate(data):
                    template = self.templates.get(rule.template_id)
                    if template:
                        title, message = template.render(data)
                        notification = Notification(
                            id=f"notif_{int(datetime.utcnow().timestamp())}",
                            user_id=rule.user_id,
                            type=rule.type,
                            title=title,
                            message=message,
                            priority=rule.priority,
                            channels=rule.channels,
                            data=data,
                            status=NotificationStatus.PENDING
                        )
                        notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"Error evaluating rules: {str(e)}")
            return []
    
    async def get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification statistics."""
        try:
            return {
                "total_notifications": self.total_notifications,
                "successful_notifications": self.successful_notifications,
                "failed_notifications": self.failed_notifications,
                "success_rate": (self.successful_notifications / max(self.total_notifications, 1)) * 100,
                "scheduled_count": self.scheduled_count,
                "active_rules": len(self.notification_rules),
                "active_templates": len(self.templates)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {str(e)}")
            return {}
    
    async def start_scheduler(self):
        """Start notification scheduler."""
        try:
            if not self.scheduler_running:
                self.scheduler_running = True
                self.scheduler_task = asyncio.create_task(self._scheduler_loop())
                self.logger.info("Notification scheduler started")
                
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {str(e)}")
    
    async def stop_scheduler(self):
        """Stop notification scheduler."""
        try:
            if self.scheduler_running:
                self.scheduler_running = False
                if self.scheduler_task:
                    self.scheduler_task.cancel()
                    self.scheduler_task = None
                self.logger.info("Notification scheduler stopped")
                
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {str(e)}")
    
    async def _scheduler_loop(self):
        """Scheduler background loop."""
        try:
            while self.scheduler_running:
                await self._process_scheduled_notifications()
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            self.logger.info("Scheduler task cancelled")
        except Exception as e:
            self.logger.error(f"Error in scheduler loop: {str(e)}")
    
    def _adjust_message_for_risk_tolerance(self, message: str, risk_tolerance: str) -> str:
        """Adjust notification message based on user's risk tolerance."""
        try:
            if risk_tolerance == "conservative":
                # Add cautionary language
                if "increase" in message.lower():
                    message += " (Consider your risk tolerance)"
                elif "decrease" in message.lower():
                    message += " (Review your position carefully)"
            elif risk_tolerance == "aggressive":
                # Add opportunity language
                if "spike" in message.lower():
                    message += " (Potential trading opportunity)"
                elif "trending" in message.lower():
                    message += " (High momentum detected)"
            
            return message
            
        except Exception:
            return message

