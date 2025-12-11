"""
Redis Pub/Sub Manager for InsiteChart platform.

This module handles Redis Pub/Sub for:
- Distributed data collection coordination
- Cache invalidation across multiple servers
- Real-time event broadcasting
- Multi-server synchronization
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

import redis.asyncio as redis
from redis.asyncio.client import PubSub

from ..config import get_settings


logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """Redis Pub/Sub channel types."""
    DATA_COLLECTION_TASK = "data_collection:task"
    DATA_COLLECTION_RESULT = "data_collection:result"
    DATA_COLLECTION_ERROR = "data_collection:error"
    CACHE_INVALIDATION = "cache:invalidation"
    SERVER_HEARTBEAT = "server:heartbeat"
    SERVER_COORDINATION = "server:coordination"
    NOTIFICATION_SEND = "notification:send"
    PRIORITY_UPDATE = "priority:update"


@dataclass
class PubSubMessage:
    """Standard Pub/Sub message structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: str = ""
    message_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    source_server: str = ""
    priority: int = 1  # 1=Low, 5=Critical

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "channel": self.channel,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source_server": self.source_server,
            "priority": self.priority
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PubSubMessage":
        """Create message from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            channel=data.get("channel", ""),
            message_type=data.get("message_type", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            data=data.get("data", {}),
            source_server=data.get("source_server", ""),
            priority=data.get("priority", 1)
        )


class SubscriptionStats:
    """Subscription statistics tracking."""

    def __init__(self):
        self.messages_received = 0
        self.messages_sent = 0
        self.errors = 0
        self.last_message_time: Optional[datetime] = None
        self.subscriptions_count = 0
        self.active_channels: Set[str] = set()

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "errors": self.errors,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "subscriptions_count": self.subscriptions_count,
            "active_channels": list(self.active_channels)
        }


class RedisPubSubManager:
    """
    Redis Pub/Sub Manager for distributed event broadcasting.

    Features:
    - Multi-channel subscription and publishing
    - Automatic reconnection with exponential backoff
    - Message serialization/deserialization
    - Subscription state tracking
    - Per-channel message callbacks
    """

    # Channel name templates
    CHANNELS = {
        'data_collection_task': "data_collection:task:{priority}",
        'data_collection_result': "data_collection:result:{task_id}",
        'data_collection_error': "data_collection:error:{source}",
        'cache_invalidation': "cache:invalidation:{symbol}",
        'server_heartbeat': "server:heartbeat:{server_id}",
        'server_coordination': "server:coordination:{type}",
        'notification_send': "notification:send:{user_id}",
        'priority_update': "priority:update:{symbol}"
    }

    def __init__(
        self,
        server_id: str = "",
        max_reconnect_attempts: int = 10,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        backoff_multiplier: float = 2.0
    ):
        """
        Initialize Redis Pub/Sub Manager.

        Args:
            server_id: Unique server identifier
            max_reconnect_attempts: Maximum reconnection attempts
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Exponential backoff multiplier
        """
        self.server_id = server_id or f"server-{uuid.uuid4().hex[:8]}"
        self.max_reconnect_attempts = max_reconnect_attempts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None

        # Subscriptions management
        self.subscriptions: Dict[str, Callable] = {}  # channel -> callback
        self.listen_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = SubscriptionStats()
        self.error_log: List[str] = []

    async def initialize(self) -> bool:
        """
        Initialize Redis connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            settings = get_settings()

            # Create Redis client
            self.redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                password=settings.redis_password,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.redis_max_connections
            )

            # Test connection
            await self.redis_client.ping()

            # Create Pub/Sub instance
            self.pubsub = self.redis_client.pubsub()

            logger.info(f"Redis Pub/Sub Manager initialized for server {self.server_id}")
            return True

        except Exception as e:
            logger.error(f"Error initializing Redis Pub/Sub Manager: {str(e)}")
            self.error_log.append(f"Initialization error: {str(e)}")
            return False

    async def subscribe(
        self,
        channel: str,
        callback: Callable,
        pattern: bool = False
    ) -> bool:
        """
        Subscribe to a channel or pattern.

        Args:
            channel: Channel name (supports wildcards with pattern=True)
            callback: Callback function for messages
            pattern: Whether to use pattern subscription

        Returns:
            True if subscription successful
        """
        try:
            if not self.pubsub:
                logger.error("Pub/Sub not initialized")
                return False

            # Subscribe
            if pattern:
                await self.pubsub.psubscribe(channel)
                logger.info(f"Pattern subscribed: {channel}")
            else:
                await self.pubsub.subscribe(channel)
                logger.info(f"Subscribed to channel: {channel}")

            # Store callback
            self.subscriptions[channel] = callback
            self.stats.subscriptions_count = len(self.subscriptions)
            self.stats.active_channels.add(channel)

            return True

        except Exception as e:
            logger.error(f"Error subscribing to {channel}: {str(e)}")
            self.error_log.append(f"Subscribe error for {channel}: {str(e)}")
            return False

    async def unsubscribe(self, channel: str) -> bool:
        """
        Unsubscribe from a channel.

        Args:
            channel: Channel name to unsubscribe from

        Returns:
            True if unsubscription successful
        """
        try:
            if not self.pubsub:
                return False

            await self.pubsub.unsubscribe(channel)
            self.subscriptions.pop(channel, None)
            self.stats.subscriptions_count = len(self.subscriptions)
            self.stats.active_channels.discard(channel)

            logger.info(f"Unsubscribed from channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing from {channel}: {str(e)}")
            return False

    async def publish(
        self,
        channel: str,
        message: PubSubMessage
    ) -> bool:
        """
        Publish message to channel.

        Args:
            channel: Channel to publish to
            message: Message to publish

        Returns:
            True if publish successful
        """
        try:
            if not self.redis_client:
                logger.error("Redis client not initialized")
                return False

            # Update source server
            message.source_server = self.server_id

            # Serialize message
            message_data = json.dumps(message.to_dict())

            # Publish
            await self.redis_client.publish(channel, message_data)

            self.stats.messages_sent += 1
            self.stats.last_message_time = datetime.utcnow()

            logger.debug(f"Published to {channel}: {message.id}")
            return True

        except Exception as e:
            logger.error(f"Error publishing to {channel}: {str(e)}")
            self.stats.errors += 1
            self.error_log.append(f"Publish error to {channel}: {str(e)}")
            return False

    async def start_listening(self) -> None:
        """Start listening to subscribed channels."""
        try:
            if not self.pubsub:
                logger.error("Pub/Sub not initialized")
                return

            # Start listen loop
            self.listen_task = asyncio.create_task(self._listen_loop())
            logger.info(f"Started listening to channels for {self.server_id}")

        except Exception as e:
            logger.error(f"Error starting listener: {str(e)}")

    async def stop_listening(self) -> None:
        """Stop listening to subscribed channels."""
        try:
            if self.listen_task and not self.listen_task.done():
                self.listen_task.cancel()
                try:
                    await self.listen_task
                except asyncio.CancelledError:
                    pass

            logger.info(f"Stopped listening for {self.server_id}")

        except Exception as e:
            logger.error(f"Error stopping listener: {str(e)}")

    async def _listen_loop(self) -> None:
        """Main listening loop for Pub/Sub messages."""
        backoff_delay = self.initial_backoff

        while True:
            try:
                if not self.pubsub:
                    await asyncio.sleep(backoff_delay)
                    continue

                # Listen for messages
                async for message in self.pubsub.listen():
                    try:
                        # Handle subscription messages
                        if message['type'] in ('subscribe', 'psubscribe', 'unsubscribe', 'punsubscribe'):
                            logger.debug(f"Subscription event: {message['type']}")
                            continue

                        # Process actual message
                        if message['type'] == 'message':
                            await self._handle_message(message)
                        elif message['type'] == 'pmessage':
                            await self._handle_pattern_message(message)

                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        self.stats.errors += 1

                # Reset backoff on successful listen
                backoff_delay = self.initial_backoff

            except asyncio.CancelledError:
                logger.debug("Listen loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in listen loop: {str(e)}")
                self.stats.errors += 1

                # Exponential backoff
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(
                    backoff_delay * self.backoff_multiplier,
                    self.max_backoff
                )

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle received message.

        Args:
            message: Message from Redis Pub/Sub
        """
        try:
            channel = message.get('channel', '')
            data = message.get('data', '')

            # Deserialize message
            pubsub_message = PubSubMessage.from_dict(json.loads(data))

            # Call subscription callback if exists
            if channel in self.subscriptions:
                callback = self.subscriptions[channel]

                if asyncio.iscoroutinefunction(callback):
                    await callback(pubsub_message)
                else:
                    callback(pubsub_message)

            self.stats.messages_received += 1
            self.stats.last_message_time = datetime.utcnow()

            logger.debug(f"Processed message from {channel}: {pubsub_message.id}")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            self.stats.errors += 1

    async def _handle_pattern_message(self, message: Dict[str, Any]) -> None:
        """
        Handle pattern-based message.

        Args:
            message: Message from pattern subscription
        """
        try:
            pattern = message.get('pattern', '')
            channel = message.get('channel', '')
            data = message.get('data', '')

            # Deserialize message
            pubsub_message = PubSubMessage.from_dict(json.loads(data))

            # Call subscription callback if exists
            if pattern in self.subscriptions:
                callback = self.subscriptions[pattern]

                if asyncio.iscoroutinefunction(callback):
                    await callback(pubsub_message)
                else:
                    callback(pubsub_message)

            self.stats.messages_received += 1
            self.stats.last_message_time = datetime.utcnow()

            logger.debug(f"Processed pattern message from {pattern}/{channel}: {pubsub_message.id}")

        except Exception as e:
            logger.error(f"Error handling pattern message: {str(e)}")
            self.stats.errors += 1

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await self.stop_listening()

            if self.pubsub:
                await self.pubsub.close()
                self.pubsub = None

            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None

            logger.info(f"Redis Pub/Sub Manager closed for {self.server_id}")

        except Exception as e:
            logger.error(f"Error closing Pub/Sub Manager: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get Pub/Sub statistics."""
        return self.stats.to_dict()

    def get_subscriptions(self) -> Dict[str, str]:
        """Get list of subscriptions."""
        return {
            channel: callback.__name__ if hasattr(callback, '__name__') else str(callback)
            for channel, callback in self.subscriptions.items()
        }

    def get_error_log(self, limit: int = 20) -> List[str]:
        """Get recent errors."""
        return self.error_log[-limit:]


# Global Pub/Sub Manager instance
redis_pubsub_manager: Optional[RedisPubSubManager] = None


async def get_redis_pubsub_manager() -> RedisPubSubManager:
    """Get or create Redis Pub/Sub Manager instance."""
    global redis_pubsub_manager

    if redis_pubsub_manager is None:
        redis_pubsub_manager = RedisPubSubManager()
        await redis_pubsub_manager.initialize()

    return redis_pubsub_manager
