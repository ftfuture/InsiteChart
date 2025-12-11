"""
WebSocket Connection Manager for InsiteChart platform.

This module provides robust WebSocket connection management with:
- Heartbeat/ping-pong mechanism for connection stability
- Exponential backoff reconnection strategy
- Connection state tracking
- Automatic subscription recovery after reconnection
- Connection pooling and lifecycle management
- Message sequence tracking for message ordering guarantees
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enum."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"


class MessageType(Enum):
    """Standard WebSocket message types."""
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    NOTIFICATION = "notification"
    ACKNOWLEDGE = "acknowledge"
    ERROR = "error"
    STATE_CHANGE = "state_change"


@dataclass
class WebSocketMessage:
    """Standard WebSocket message structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    sequence_number: int = 0  # Message sequence for ordering
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    requires_ack: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "requires_ack": self.requires_ack
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketMessage":
        """Create message from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=data.get("type", ""),
            sequence_number=data.get("sequence_number", 0),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            data=data.get("data", {}),
            requires_ack=data.get("requires_ack", False)
        )


@dataclass
class SubscriptionInfo:
    """Subscription information for auto-recovery."""
    symbols: List[str] = field(default_factory=list)
    notification_types: List[str] = field(default_factory=list)
    price_threshold: Optional[float] = None
    sentiment_threshold: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConnectionMetrics:
    """Connection metrics tracking."""

    def __init__(self):
        self.connection_start_time: Optional[datetime] = None
        self.last_heartbeat_time: Optional[datetime] = None
        self.last_message_time: Optional[datetime] = None
        self.total_messages_sent: int = 0
        self.total_messages_received: int = 0
        self.reconnection_attempts: int = 0
        self.successful_reconnections: int = 0
        self.heartbeat_failures: int = 0
        self.errors: List[str] = []

    def get_connection_duration(self) -> Optional[float]:
        """Get connection duration in seconds."""
        if self.connection_start_time:
            return (datetime.utcnow() - self.connection_start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "connection_start_time": self.connection_start_time.isoformat() if self.connection_start_time else None,
            "last_heartbeat_time": self.last_heartbeat_time.isoformat() if self.last_heartbeat_time else None,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "reconnection_attempts": self.reconnection_attempts,
            "successful_reconnections": self.successful_reconnections,
            "heartbeat_failures": self.heartbeat_failures,
            "connection_duration_seconds": self.get_connection_duration(),
            "error_count": len(self.errors)
        }


class WebSocketConnectionManager:
    """
    Manages WebSocket connections with advanced features.

    Features:
    - Heartbeat mechanism (ping/pong)
    - Exponential backoff reconnection
    - Connection state tracking
    - Automatic subscription recovery
    - Message sequence numbering
    - Connection metrics and monitoring
    """

    def __init__(
        self,
        user_id: str,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 10,
        max_reconnect_attempts: int = 10,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        backoff_multiplier: float = 2.0
    ):
        """
        Initialize WebSocket connection manager.

        Args:
            user_id: User ID for this connection
            heartbeat_interval: Seconds between heartbeat pings
            heartbeat_timeout: Seconds to wait for pong response
            max_reconnect_attempts: Maximum reconnection attempts
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Exponential backoff multiplier
        """
        self.user_id = user_id
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

        self.websocket: Optional[WebSocket] = None
        self.state = ConnectionState.DISCONNECTED
        self.sequence_number = 0

        # Subscription management
        self.subscriptions: Dict[str, SubscriptionInfo] = {}
        self.pending_acks: Dict[str, datetime] = {}  # Message ID -> timestamp

        # State management
        self.metrics = ConnectionMetrics()
        self.message_buffer: List[WebSocketMessage] = []
        self.max_buffer_size = 1000

        # Task management
        self.tasks: Set[asyncio.Task] = set()
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.ack_monitor_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_reconnecting: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    async def connect(self, websocket: WebSocket) -> bool:
        """
        Establish WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self._set_state(ConnectionState.CONNECTING)

            self.websocket = websocket
            self.metrics.connection_start_time = datetime.utcnow()

            logger.info(f"WebSocket connecting for user {self.user_id}")

            # Start heartbeat mechanism
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.tasks.add(self.heartbeat_task)
            self.heartbeat_task.add_done_callback(self.tasks.discard)

            # Start acknowledgment monitor
            self.ack_monitor_task = asyncio.create_task(self._ack_monitor_loop())
            self.tasks.add(self.ack_monitor_task)
            self.ack_monitor_task.add_done_callback(self.tasks.discard)

            await self._set_state(ConnectionState.CONNECTED)
            logger.info(f"WebSocket connected for user {self.user_id}")

            if self.on_connected:
                await self._execute_callback(self.on_connected)

            return True

        except Exception as e:
            logger.error(f"Error connecting WebSocket for user {self.user_id}: {str(e)}")
            self.metrics.errors.append(f"Connection error: {str(e)}")
            await self._set_state(ConnectionState.DISCONNECTED)

            if self.on_error:
                await self._execute_callback(self.on_error, str(e))

            return False

    async def disconnect(self) -> None:
        """Disconnect WebSocket gracefully."""
        try:
            await self._set_state(ConnectionState.CLOSING)

            # Cancel all tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to finish
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)

            self.websocket = None
            await self._set_state(ConnectionState.CLOSED)

            logger.info(f"WebSocket disconnected for user {self.user_id}")

            if self.on_disconnected:
                await self._execute_callback(self.on_disconnected)

        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for user {self.user_id}: {str(e)}")
            self.metrics.errors.append(f"Disconnection error: {str(e)}")

    async def send_message(
        self,
        message_type: str,
        data: Dict[str, Any] = None,
        requires_ack: bool = False
    ) -> Optional[str]:
        """
        Send message through WebSocket.

        Args:
            message_type: Type of message
            data: Message data
            requires_ack: Whether message requires acknowledgment

        Returns:
            Message ID if sent successfully, None otherwise
        """
        if self.state != ConnectionState.CONNECTED or not self.websocket:
            logger.warning(f"Cannot send message: WebSocket not connected for user {self.user_id}")
            return None

        try:
            self.sequence_number += 1

            message = WebSocketMessage(
                type=message_type,
                sequence_number=self.sequence_number,
                data=data or {},
                requires_ack=requires_ack
            )

            # Add to buffer
            self._add_to_buffer(message)

            # Send message
            await self.websocket.send_text(json.dumps(message.to_dict()))

            # Track for acknowledgment if needed
            if requires_ack:
                self.pending_acks[message.id] = datetime.utcnow()

            self.metrics.total_messages_sent += 1
            self.metrics.last_message_time = datetime.utcnow()

            logger.debug(f"Message sent for user {self.user_id}: {message_type} (seq: {self.sequence_number})")

            return message.id

        except Exception as e:
            logger.error(f"Error sending message for user {self.user_id}: {str(e)}")
            self.metrics.errors.append(f"Send error: {str(e)}")

            if self.on_error:
                await self._execute_callback(self.on_error, str(e))

            return None

    async def subscribe(
        self,
        symbols: List[str],
        notification_types: List[str],
        price_threshold: Optional[float] = None,
        sentiment_threshold: Optional[float] = None
    ) -> bool:
        """
        Subscribe to notifications.

        Args:
            symbols: Stock symbols to monitor
            notification_types: Types of notifications
            price_threshold: Price change threshold
            sentiment_threshold: Sentiment change threshold

        Returns:
            True if subscription successful
        """
        try:
            # Store subscription info for recovery
            self.subscriptions["current"] = SubscriptionInfo(
                symbols=symbols,
                notification_types=notification_types,
                price_threshold=price_threshold,
                sentiment_threshold=sentiment_threshold
            )

            # Send subscription message
            message_id = await self.send_message(
                MessageType.SUBSCRIBE.value,
                {
                    "symbols": symbols,
                    "notification_types": notification_types,
                    "price_threshold": price_threshold,
                    "sentiment_threshold": sentiment_threshold
                },
                requires_ack=True
            )

            if message_id:
                logger.info(f"Subscription created for user {self.user_id}: {symbols}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error subscribing for user {self.user_id}: {str(e)}")
            self.metrics.errors.append(f"Subscribe error: {str(e)}")

            if self.on_error:
                await self._execute_callback(self.on_error, str(e))

            return False

    async def acknowledge_message(self, message_id: str) -> bool:
        """
        Send acknowledgment for received message.

        Args:
            message_id: ID of message to acknowledge

        Returns:
            True if acknowledgment sent successfully
        """
        try:
            result = await self.send_message(
                MessageType.ACKNOWLEDGE.value,
                {"message_id": message_id}
            )

            if result:
                # Remove from pending if it's our message
                self.pending_acks.pop(message_id, None)
                return True

            return False

        except Exception as e:
            logger.error(f"Error acknowledging message for user {self.user_id}: {str(e)}")
            return False

    async def handle_message(self, message_data: Dict[str, Any]) -> None:
        """
        Handle received message.

        Args:
            message_data: Received message data
        """
        try:
            message = WebSocketMessage.from_dict(message_data)

            # Add to buffer
            self._add_to_buffer(message)

            self.metrics.total_messages_received += 1
            self.metrics.last_message_time = datetime.utcnow()

            # Handle acknowledgments
            if message.type == MessageType.ACKNOWLEDGE.value:
                message_id = message.data.get("message_id")
                if message_id in self.pending_acks:
                    del self.pending_acks[message_id]
                logger.debug(f"Acknowledgment received for message {message_id}")

            # Send to callback
            if self.on_message:
                await self._execute_callback(self.on_message, message)

        except Exception as e:
            logger.error(f"Error handling message for user {self.user_id}: {str(e)}")
            self.metrics.errors.append(f"Handle error: {str(e)}")

            if self.on_error:
                await self._execute_callback(self.on_error, str(e))

    def get_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics."""
        return self.metrics.to_dict()

    def get_subscriptions(self) -> Dict[str, SubscriptionInfo]:
        """Get current subscriptions."""
        return self.subscriptions

    def get_message_buffer(self, limit: int = 100) -> List[WebSocketMessage]:
        """Get message buffer (most recent messages)."""
        return self.message_buffer[-limit:] if self.message_buffer else []

    async def _set_state(self, new_state: ConnectionState) -> None:
        """
        Set connection state and trigger callback.

        Args:
            new_state: New connection state
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state

            logger.info(f"Connection state changed for user {self.user_id}: {old_state.value} -> {new_state.value}")

            if self.on_state_change:
                await self._execute_callback(self.on_state_change, old_state, new_state)

    async def _heartbeat_loop(self) -> None:
        """
        Heartbeat loop for connection monitoring.

        Sends periodic ping messages and detects stale connections.
        """
        consecutive_failures = 0

        while self.state in [ConnectionState.CONNECTED, ConnectionState.RECONNECTING]:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if self.state != ConnectionState.CONNECTED or not self.websocket:
                    continue

                # Send ping message
                ping_id = await self.send_message(
                    MessageType.PING.value,
                    {"timestamp": datetime.utcnow().isoformat()},
                    requires_ack=True
                )

                if ping_id:
                    self.metrics.last_heartbeat_time = datetime.utcnow()
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    self.metrics.heartbeat_failures += 1

                    if consecutive_failures >= 3:
                        logger.warning(f"Heartbeat failed {consecutive_failures} times for user {self.user_id}")
                        # Will be handled by ack_monitor_loop

            except asyncio.CancelledError:
                logger.debug(f"Heartbeat loop cancelled for user {self.user_id}")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop for user {self.user_id}: {str(e)}")
                self.metrics.errors.append(f"Heartbeat error: {str(e)}")

    async def _ack_monitor_loop(self) -> None:
        """
        Monitor for acknowledgments with timeout.

        Detects unacknowledged messages and triggers reconnection if needed.
        """
        while self.state in [ConnectionState.CONNECTED, ConnectionState.RECONNECTING]:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds

                current_time = datetime.utcnow()
                timed_out_messages = []

                # Check for timed-out acknowledgments
                for message_id, sent_time in self.pending_acks.items():
                    elapsed = (current_time - sent_time).total_seconds()

                    if elapsed > self.heartbeat_timeout:
                        timed_out_messages.append(message_id)

                if timed_out_messages:
                    logger.warning(
                        f"Messages timed out for user {self.user_id}: {len(timed_out_messages)}"
                    )

                    # Remove timed-out messages
                    for message_id in timed_out_messages:
                        del self.pending_acks[message_id]

                    # If too many timeouts, reconnect
                    if len(timed_out_messages) > 2:
                        logger.warning(f"Too many message timeouts for user {self.user_id}, triggering reconnection")
                        await self._handle_reconnection()

            except asyncio.CancelledError:
                logger.debug(f"ACK monitor loop cancelled for user {self.user_id}")
                break
            except Exception as e:
                logger.error(f"Error in ACK monitor loop for user {self.user_id}: {str(e)}")

    async def _handle_reconnection(self) -> None:
        """
        Handle reconnection with exponential backoff.

        Implements exponential backoff strategy with maximum retry attempts.
        Automatically recovers subscriptions after successful reconnection.
        """
        await self._set_state(ConnectionState.RECONNECTING)

        backoff_delay = self.initial_backoff

        for attempt in range(1, self.max_reconnect_attempts + 1):
            try:
                logger.info(
                    f"Reconnection attempt {attempt}/{self.max_reconnect_attempts} "
                    f"for user {self.user_id} (delay: {backoff_delay:.1f}s)"
                )

                self.metrics.reconnection_attempts += 1

                # Wait with exponential backoff
                await asyncio.sleep(backoff_delay)

                # Update backoff for next attempt
                backoff_delay = min(
                    backoff_delay * self.backoff_multiplier,
                    self.max_backoff
                )

                # Attempt to reconnect (this would be implemented at the connection layer)
                # For now, we log the attempt and wait for external reconnection
                logger.info(f"Ready for reconnection attempt {attempt} for user {self.user_id}")

                # If reconnection is successful (set by external code)
                if self.state == ConnectionState.CONNECTED:
                    self.metrics.successful_reconnections += 1

                    # Recover subscriptions
                    await self._recover_subscriptions()

                    logger.info(f"Reconnection successful for user {self.user_id}")
                    return

            except asyncio.CancelledError:
                logger.debug(f"Reconnection loop cancelled for user {self.user_id}")
                break
            except Exception as e:
                logger.error(f"Error in reconnection attempt for user {self.user_id}: {str(e)}")
                self.metrics.errors.append(f"Reconnection error: {str(e)}")

        # Max retries exceeded
        logger.error(f"Reconnection failed after {self.max_reconnect_attempts} attempts for user {self.user_id}")
        await self._set_state(ConnectionState.DISCONNECTED)

        if self.on_error:
            await self._execute_callback(self.on_error, "Max reconnection attempts exceeded")

    async def _recover_subscriptions(self) -> None:
        """
        Recover subscriptions after reconnection.

        Re-subscribes to all previously active subscriptions.
        """
        try:
            for key, subscription in self.subscriptions.items():
                logger.info(f"Recovering subscription {key} for user {self.user_id}")

                await self.subscribe(
                    symbols=subscription.symbols,
                    notification_types=subscription.notification_types,
                    price_threshold=subscription.price_threshold,
                    sentiment_threshold=subscription.sentiment_threshold
                )

                # Small delay between subscriptions
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error recovering subscriptions for user {self.user_id}: {str(e)}")
            self.metrics.errors.append(f"Subscription recovery error: {str(e)}")

    def _add_to_buffer(self, message: WebSocketMessage) -> None:
        """
        Add message to circular buffer.

        Args:
            message: Message to buffer
        """
        self.message_buffer.append(message)

        # Remove old messages if buffer is full
        if len(self.message_buffer) > self.max_buffer_size:
            self.message_buffer = self.message_buffer[-self.max_buffer_size:]

    async def _execute_callback(self, callback: Callable, *args) -> None:
        """
        Execute callback safely.

        Args:
            callback: Callback function
            *args: Callback arguments
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Error executing callback: {str(e)}")
