"""
Message Ordering Manager for InsiteChart platform.

This module ensures:
- Global message ordering across distributed systems
- Duplicate detection and prevention
- Transaction semantics (at-least-once delivery)
- Idempotent message processing
- Concurrent access control via distributed locking
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

import redis.asyncio as redis

from ..config import get_settings


logger = logging.getLogger(__name__)


class DeliveryGuarantee(Enum):
    """Message delivery guarantee types."""
    AT_LEAST_ONCE = "at_least_once"      # Messages may be duplicated
    AT_MOST_ONCE = "at_most_once"        # Messages may be lost
    EXACTLY_ONCE = "exactly_once"        # Messages delivered exactly once


class MessageProcessingStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class OrderedMessage:
    """Message with global ordering information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    global_sequence: int = 0              # Global ordering number
    local_sequence: int = 0               # Per-partition ordering
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""                      # Message source (user_id, service_id, etc.)
    partition_key: str = ""               # Partitioning key for local ordering
    data: Dict[str, Any] = field(default_factory=dict)
    status: MessageProcessingStatus = MessageProcessingStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    failed_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "global_sequence": self.global_sequence,
            "local_sequence": self.local_sequence,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "partition_key": self.partition_key,
            "data": self.data,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "failed_reason": self.failed_reason
        }


@dataclass
class DistributedLock:
    """Distributed lock using Redis."""
    resource_id: str = ""
    lock_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    owner: str = ""
    acquired_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    ttl_seconds: int = 30

    def is_expired(self) -> bool:
        """Check if lock has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class DuplicateDetector:
    """Detects and prevents duplicate message processing."""

    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 3600):
        """
        Initialize duplicate detector.

        Args:
            redis_client: Redis client instance
            ttl_seconds: Time-to-live for processed message IDs
        """
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self.processed_messages: Set[str] = set()
        self.local_cache: Dict[str, datetime] = {}

    async def is_duplicate(self, message_id: str) -> bool:
        """
        Check if message has been processed.

        Args:
            message_id: Message ID to check

        Returns:
            True if message is duplicate, False otherwise
        """
        try:
            # Check local cache first (faster)
            if message_id in self.local_cache:
                expiry = self.local_cache[message_id]
                if datetime.utcnow() < expiry:
                    logger.debug(f"Duplicate detected (local cache): {message_id}")
                    return True
                else:
                    del self.local_cache[message_id]

            # Check Redis (distributed)
            exists = await self.redis_client.exists(f"processed_msg:{message_id}")
            if exists:
                logger.debug(f"Duplicate detected (Redis): {message_id}")
                # Update local cache
                self.local_cache[message_id] = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking duplicate: {str(e)}")
            return False

    async def mark_processed(self, message_id: str) -> bool:
        """
        Mark message as processed.

        Args:
            message_id: Message ID to mark

        Returns:
            True if successfully marked, False otherwise
        """
        try:
            # Store in Redis
            await self.redis_client.setex(
                f"processed_msg:{message_id}",
                self.ttl_seconds,
                "1"
            )

            # Update local cache
            self.local_cache[message_id] = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

            logger.debug(f"Message marked as processed: {message_id}")
            return True

        except Exception as e:
            logger.error(f"Error marking message as processed: {str(e)}")
            return False

    async def clear_expired(self) -> None:
        """Clear expired entries from local cache."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self.local_cache.items()
            if now > expiry
        ]

        for key in expired_keys:
            del self.local_cache[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired entries from duplicate detector")


class DistributedLockManager:
    """Manages distributed locks for concurrent resource access."""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize lock manager.

        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.local_locks: Dict[str, DistributedLock] = {}

    async def acquire_lock(
        self,
        resource_id: str,
        owner: str = "",
        ttl_seconds: int = 30,
        timeout_seconds: int = 5
    ) -> Optional[DistributedLock]:
        """
        Acquire distributed lock.

        Args:
            resource_id: Resource identifier
            owner: Lock owner identifier
            ttl_seconds: Lock time-to-live
            timeout_seconds: Maximum wait time to acquire lock

        Returns:
            DistributedLock if acquired, None otherwise
        """
        try:
            lock_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            lock_key = f"lock:{resource_id}"

            while (datetime.utcnow() - start_time).total_seconds() < timeout_seconds:
                # Try to acquire lock
                success = await self.redis_client.set(
                    lock_key,
                    lock_id,
                    ex=ttl_seconds,
                    nx=True  # Only set if not exists
                )

                if success:
                    # Lock acquired
                    lock = DistributedLock(
                        resource_id=resource_id,
                        lock_id=lock_id,
                        owner=owner,
                        ttl_seconds=ttl_seconds,
                        expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds)
                    )

                    self.local_locks[resource_id] = lock
                    logger.debug(f"Lock acquired: {resource_id} by {owner}")
                    return lock

                # Wait before retrying
                await asyncio.sleep(0.1)

            logger.warning(f"Failed to acquire lock: {resource_id} (timeout)")
            return None

        except Exception as e:
            logger.error(f"Error acquiring lock: {str(e)}")
            return None

    async def release_lock(self, lock: DistributedLock) -> bool:
        """
        Release distributed lock.

        Args:
            lock: Lock to release

        Returns:
            True if released, False otherwise
        """
        try:
            lock_key = f"lock:{lock.resource_id}"
            lock_value = await self.redis_client.get(lock_key)

            # Verify lock ownership before releasing
            if lock_value == lock.lock_id:
                await self.redis_client.delete(lock_key)
                self.local_locks.pop(lock.resource_id, None)
                logger.debug(f"Lock released: {lock.resource_id}")
                return True

            logger.warning(f"Cannot release lock: ownership mismatch for {lock.resource_id}")
            return False

        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")
            return False

    async def extend_lock(self, lock: DistributedLock, additional_seconds: int = 10) -> bool:
        """
        Extend lock TTL.

        Args:
            lock: Lock to extend
            additional_seconds: Additional seconds to extend

        Returns:
            True if extended, False otherwise
        """
        try:
            lock_key = f"lock:{lock.resource_id}"
            lock_value = await self.redis_client.get(lock_key)

            # Verify lock ownership
            if lock_value == lock.lock_id:
                await self.redis_client.expire(lock_key, lock.ttl_seconds + additional_seconds)
                lock.expires_at = datetime.utcnow() + timedelta(
                    seconds=lock.ttl_seconds + additional_seconds
                )
                logger.debug(f"Lock extended: {lock.resource_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error extending lock: {str(e)}")
            return False


class MessageOrderingManager:
    """
    Manages message ordering and sequencing for distributed systems.

    Features:
    - Global message sequencing
    - Partition-based local ordering
    - Duplicate detection
    - Distributed locking for concurrent access
    - Transaction semantics
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE
    ):
        """
        Initialize Message Ordering Manager.

        Args:
            redis_client: Redis client instance
            delivery_guarantee: Delivery guarantee level
        """
        self.redis_client = redis_client
        self.delivery_guarantee = delivery_guarantee
        self.current_global_sequence = 0
        self.partition_sequences: Dict[str, int] = {}  # partition_key -> sequence

        # Sub-managers
        self.duplicate_detector = DuplicateDetector(redis_client)
        self.lock_manager = DistributedLockManager(redis_client)

        # Message buffer for ordering
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.processing_stats = {
            "total_messages": 0,
            "processed_messages": 0,
            "duplicates_detected": 0,
            "failed_messages": 0
        }

    async def initialize(self) -> bool:
        """Initialize the ordering manager."""
        try:
            # Load current global sequence from Redis
            current_seq = await self.redis_client.get("global_sequence")
            if current_seq:
                self.current_global_sequence = int(current_seq)

            logger.info(
                f"Message Ordering Manager initialized "
                f"(guarantee: {self.delivery_guarantee.value}, "
                f"current sequence: {self.current_global_sequence})"
            )
            return True

        except Exception as e:
            logger.error(f"Error initializing Message Ordering Manager: {str(e)}")
            return False

    async def assign_sequence(
        self,
        message: OrderedMessage
    ) -> Tuple[int, int]:
        """
        Assign global and local sequence numbers to message.

        Args:
            message: Message to assign sequence to

        Returns:
            Tuple of (global_sequence, local_sequence)
        """
        try:
            # Assign global sequence (atomic increment in Redis)
            global_seq = await self.redis_client.incr("global_sequence")
            self.current_global_sequence = global_seq

            # Assign local sequence (per partition)
            if message.partition_key not in self.partition_sequences:
                self.partition_sequences[message.partition_key] = 0

            local_seq = self.partition_sequences[message.partition_key] + 1
            self.partition_sequences[message.partition_key] = local_seq

            # Store in message
            message.global_sequence = global_seq
            message.local_sequence = local_seq

            logger.debug(
                f"Sequence assigned: msg={message.id}, "
                f"global={global_seq}, local={local_seq}"
            )

            return global_seq, local_seq

        except Exception as e:
            logger.error(f"Error assigning sequence: {str(e)}")
            return 0, 0

    async def enqueue_message(self, message: OrderedMessage) -> bool:
        """
        Enqueue message for processing.

        Args:
            message: Message to enqueue

        Returns:
            True if enqueued successfully
        """
        try:
            # Check for duplicates
            is_dup = await self.duplicate_detector.is_duplicate(message.id)
            if is_dup:
                self.processing_stats["duplicates_detected"] += 1
                logger.warning(f"Duplicate message discarded: {message.id}")
                return False

            # Assign sequences
            await self.assign_sequence(message)

            # Enqueue with priority (lower global_sequence = higher priority)
            await self.message_queue.put((message.global_sequence, message))

            self.processing_stats["total_messages"] += 1
            logger.debug(f"Message enqueued: {message.id} (seq: {message.global_sequence})")

            return True

        except Exception as e:
            logger.error(f"Error enqueueing message: {str(e)}")
            return False

    async def dequeue_message(self) -> Optional[OrderedMessage]:
        """
        Dequeue next message in order.

        Returns:
            Next message in global order, or None if queue empty
        """
        try:
            if self.message_queue.empty():
                return None

            _, message = await asyncio.wait_for(
                self.message_queue.get(),
                timeout=0.1
            )

            message.status = MessageProcessingStatus.PROCESSING
            return message

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error dequeueing message: {str(e)}")
            return None

    async def mark_message_processed(
        self,
        message: OrderedMessage
    ) -> bool:
        """
        Mark message as successfully processed.

        Args:
            message: Message that was processed

        Returns:
            True if marked successfully
        """
        try:
            message.status = MessageProcessingStatus.COMPLETED
            message.processed_at = datetime.utcnow()

            # Mark as processed (for duplicate detection)
            await self.duplicate_detector.mark_processed(message.id)

            self.processing_stats["processed_messages"] += 1

            logger.debug(f"Message marked as processed: {message.id}")
            return True

        except Exception as e:
            logger.error(f"Error marking message as processed: {str(e)}")
            return False

    async def mark_message_failed(
        self,
        message: OrderedMessage,
        reason: str = ""
    ) -> bool:
        """
        Mark message as failed.

        Args:
            message: Message that failed
            reason: Failure reason

        Returns:
            True if marked, False if moving to dead letter queue
        """
        try:
            message.retry_count += 1
            message.failed_reason = reason

            if message.retry_count >= message.max_retries:
                # Move to dead letter queue
                message.status = MessageProcessingStatus.DEAD_LETTER
                self.processing_stats["failed_messages"] += 1

                logger.error(
                    f"Message moved to dead letter queue: {message.id} "
                    f"(reason: {reason})"
                )

                # Store in dead letter queue
                await self.redis_client.lpush(
                    "dead_letter_queue",
                    json_serialize(message.to_dict())
                )
                return True
            else:
                # Retry
                message.status = MessageProcessingStatus.PENDING
                await self.enqueue_message(message)

                logger.warning(
                    f"Message requeued for retry: {message.id} "
                    f"(attempt {message.retry_count}/{message.max_retries})"
                )
                return False

        except Exception as e:
            logger.error(f"Error marking message as failed: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.processing_stats,
            "current_global_sequence": self.current_global_sequence,
            "partition_count": len(self.partition_sequences),
            "message_queue_size": self.message_queue.qsize(),
            "delivery_guarantee": self.delivery_guarantee.value
        }


def json_serialize(obj: Any) -> str:
    """
    JSON serialize object with datetime support.

    Args:
        obj: Object to serialize

    Returns:
        JSON string
    """
    import json
    from datetime import datetime

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)

    return json.dumps(obj, cls=DateTimeEncoder)


# Global Message Ordering Manager instance
message_ordering_manager: Optional[MessageOrderingManager] = None


async def get_message_ordering_manager() -> Optional[MessageOrderingManager]:
    """Get or create Message Ordering Manager instance."""
    global message_ordering_manager

    if message_ordering_manager is None:
        try:
            settings = get_settings()
            redis_client = redis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                password=settings.redis_password,
                encoding="utf-8",
                decode_responses=True
            )

            message_ordering_manager = MessageOrderingManager(redis_client)
            await message_ordering_manager.initialize()

        except Exception as e:
            logger.error(f"Error creating Message Ordering Manager: {str(e)}")
            return None

    return message_ordering_manager
