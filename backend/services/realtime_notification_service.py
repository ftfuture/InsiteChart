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
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..models.unified_models import UnifiedStockData
from ..cache.unified_cache import UnifiedCacheManager


class NotificationType(str, Enum):
    """Types of notifications."""
    PRICE_ALERT = "price_alert"
    SENTIMENT_ALERT = "sentiment_alert"
    TRENDING_ALERT = "trending_alert"
    VOLUME_SPIKE = "volume_spike"
    MARKET_EVENT = "market_event"
    SYSTEM_NOTIFICATION = "system_notification"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Notification data structure."""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    symbol: Optional[str] = None
    is_read: bool = False
    expires_at: Optional[datetime] = None


class NotificationSubscription(BaseModel):
    """WebSocket subscription model."""
    user_id: str
    symbols: List[str] = []
    notification_types: List[NotificationType] = []
    price_threshold: Optional[float] = None
    sentiment_threshold: Optional[float] = None


class RealtimeNotificationService:
    """Real-time notification service using WebSocket."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
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
        
        self.logger.info("RealtimeNotificationService initialized")
    
    async def start(self):
        """Start the notification service."""
        try:
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
        """Create and queue a notification."""
        try:
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
        """Monitor market events and generate notifications."""
        try:
            while True:
                try:
                    # Check for price alerts
                    await self._check_price_alerts()
                    
                    # Check for sentiment changes
                    await self._check_sentiment_alerts()
                    
                    # Check for trending stocks
                    await self._check_trending_alerts()
                    
                    # Check for volume spikes
                    await self._check_volume_spikes()
                    
                    # Wait before next check
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error in market monitoring: {str(e)}")
                    await asyncio.sleep(60)  # Wait longer on error
                    
        except asyncio.CancelledError:
            self.logger.info("Market monitoring task cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in market monitoring: {str(e)}")
    
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
        """Send notification to a specific user."""
        try:
            if user_id not in self.active_connections:
                return
            
            websocket = self.active_connections[user_id]
            
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
            
            self.logger.debug(f"Notification sent to user {user_id}: {notification.id}")
            
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