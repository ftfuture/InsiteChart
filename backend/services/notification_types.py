"""
Notification Types for InsiteChart platform.

This module defines notification types, priorities, and statuses
used throughout the notification system.
"""

from enum import Enum


class NotificationType(str, Enum):
    """Types of notifications."""
    PRICE_ALERT = "price_alert"
    SENTIMENT_ALERT = "sentiment_alert"
    TRENDING_ALERT = "trending_alert"
    VOLUME_SPIKE = "volume_spike"
    MARKET_EVENT = "market_event"
    SYSTEM_NOTIFICATION = "system_notification"
    WELCOME = "welcome"
    ERROR = "error"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Notification status."""
    PENDING = "pending"
    SENT = "sent"
    PARTIAL_SENT = "partial_sent"
    SCHEDULED = "scheduled"
    FAILED = "failed"
    READ = "read"
    ARCHIVED = "archived"