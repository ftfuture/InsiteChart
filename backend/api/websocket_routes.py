"""
WebSocket routes for real-time notifications in InsiteChart platform.

This module handles WebSocket connections for real-time notifications,
including stock price alerts, sentiment changes, and market events.

Features:
- Heartbeat mechanism for connection stability
- Exponential backoff reconnection strategy
- Message sequencing for ordering guarantees
- Connection state tracking and metrics
- Automatic subscription recovery after reconnection
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.responses import JSONResponse

from ..services.realtime_notification_service import (
    RealtimeNotificationService,
    NotificationSubscription,
    NotificationType
)
from ..services.websocket_connection_manager import (
    WebSocketConnectionManager,
    ConnectionState,
    MessageType
)
from ..services.unified_service import UnifiedService
from ..cache.unified_cache import UnifiedCacheManager
from ..config import get_settings


# Create router
router = APIRouter()
logger = logging.getLogger(__name__)


# Global notification service instance
notification_service: Optional[RealtimeNotificationService] = None

# Global WebSocket connection managers per user
connection_managers: Dict[str, WebSocketConnectionManager] = {}


async def get_notification_service() -> RealtimeNotificationService:
    """Dependency to get notification service instance."""
    global notification_service
    
    if notification_service is None:
        # Initialize with unified service and cache manager
        from ..services.stock_service import StockService
        from ..services.sentiment_service import SentimentService
        
        stock_service = StockService()
        sentiment_service = SentimentService()
        cache_manager = UnifiedCacheManager()
        unified_service = UnifiedService(stock_service, sentiment_service, cache_manager)
        
        notification_service = RealtimeNotificationService(cache_manager)
        await notification_service.start()
    
    return notification_service


@router.websocket("/notifications/{user_id}")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str,
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """WebSocket endpoint for real-time notifications with enhanced stability."""
    settings = get_settings()

    # Create or get connection manager
    if user_id not in connection_managers:
        connection_managers[user_id] = WebSocketConnectionManager(
            user_id=user_id,
            heartbeat_interval=settings.websocket_heartbeat_interval,
            heartbeat_timeout=10,
            max_reconnect_attempts=10,
            initial_backoff=1.0,
            max_backoff=30.0,
            backoff_multiplier=2.0
        )

    conn_manager = connection_managers[user_id]

    try:
        # Accept WebSocket connection
        await websocket.accept()

        # Connect with the old service
        await service.connect(websocket, user_id)

        # Connect with the new manager
        await conn_manager.connect(websocket)

        logger.info(f"WebSocket connected for user {user_id} with connection manager")

        # Handle WebSocket messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle message through connection manager
                await conn_manager.handle_message(message)

                # Handle different message types
                message_type = message.get("type")

                if message_type == "subscribe":
                    # Handle subscription
                    subscription_data = message.get("data", {})
                    subscription = NotificationSubscription(
                        user_id=user_id,
                        symbols=subscription_data.get("symbols", []),
                        notification_types=[
                            NotificationType(t) for t in subscription_data.get("notification_types", [])
                        ],
                        price_threshold=subscription_data.get("price_threshold"),
                        sentiment_threshold=subscription_data.get("sentiment_threshold")
                    )

                    await service.subscribe(user_id, subscription)

                    # Store subscription in connection manager for recovery
                    await conn_manager.subscribe(
                        symbols=subscription.symbols,
                        notification_types=[nt.value for nt in subscription.notification_types],
                        price_threshold=subscription.price_threshold,
                        sentiment_threshold=subscription.sentiment_threshold
                    )

                    # Send confirmation
                    response = {
                        "type": "subscription_confirmed",
                        "data": subscription.dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == MessageType.PING.value:
                    # Handle ping/pong for connection health (now handled by manager)
                    response = {
                        "type": MessageType.PONG.value,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                    await conn_manager.acknowledge_message(message.get("id"))

                elif message_type == "get_history":
                    # Get notification history
                    limit = message.get("limit", 50)
                    notifications = await service.get_user_notifications(user_id, limit)

                    response = {
                        "type": "notification_history",
                        "data": [
                            {
                                "id": notif.id,
                                "type": notif.type.value,
                                "priority": notif.priority.value,
                                "title": notif.title,
                                "message": notif.message,
                                "data": notif.data,
                                "timestamp": notif.timestamp.isoformat(),
                                "symbol": notif.symbol,
                                "is_read": notif.is_read
                            }
                            for notif in notifications
                        ],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                    await conn_manager.acknowledge_message(message.get("id"))

                elif message_type == "mark_read":
                    # Mark notification as read
                    notification_id = message.get("notification_id")
                    if notification_id:
                        await service.mark_notification_read(user_id, notification_id)

                        response = {
                            "type": "notification_marked_read",
                            "notification_id": notification_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(response))
                        await conn_manager.acknowledge_message(message.get("id"))

                elif message_type == MessageType.ACKNOWLEDGE.value:
                    # Handle acknowledgment
                    await conn_manager.handle_message(message)

                else:
                    # Unknown message type
                    response = {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))

            except WebSocketDisconnect:
                # Client disconnected
                logger.info(f"WebSocket client disconnected for user {user_id}")
                break
            except json.JSONDecodeError:
                # Invalid JSON
                response = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    await websocket.send_text(json.dumps(response))
                except:
                    pass
            except Exception as e:
                # Error handling message
                logger.error(f"Error handling WebSocket message for user {user_id}: {str(e)}")
                response = {
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    await websocket.send_text(json.dumps(response))
                except:
                    pass

    except WebSocketDisconnect:
        # Client disconnected
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        # Error in WebSocket connection
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        # Clean up connections
        await service.disconnect(user_id)
        await conn_manager.disconnect()

        # Clean up manager from global dict
        if user_id in connection_managers:
            del connection_managers[user_id]

        logger.info(f"WebSocket cleanup completed for user {user_id}")


@router.post("/notifications/subscribe")
async def subscribe_notifications(
    subscription: NotificationSubscription,
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Subscribe to notifications via REST API."""
    try:
        await service.subscribe(subscription.user_id, subscription)
        
        return {
            "success": True,
            "message": "Successfully subscribed to notifications",
            "subscription": subscription.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to notifications: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to subscribe to notifications",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notifications/{user_id}")
async def get_notifications(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications"),
    unread_only: bool = Query(False, description="Get only unread notifications"),
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Get notification history for a user."""
    try:
        notifications = await service.get_user_notifications(user_id, limit)
        
        # Filter by read status if requested
        if unread_only:
            notifications = [n for n in notifications if not n.is_read]
        
        return {
            "success": True,
            "data": [
                {
                    "id": notif.id,
                    "type": notif.type.value,
                    "priority": notif.priority.value,
                    "title": notif.title,
                    "message": notif.message,
                    "data": notif.data,
                    "timestamp": notif.timestamp.isoformat(),
                    "symbol": notif.symbol,
                    "is_read": notif.is_read
                }
                for notif in notifications
            ],
            "count": len(notifications),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get notifications",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/notifications/{user_id}/mark_read")
async def mark_notification_read(
    user_id: str,
    notification_id: str,
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Mark a notification as read."""
    try:
        await service.mark_notification_read(user_id, notification_id)
        
        return {
            "success": True,
            "message": "Notification marked as read",
            "notification_id": notification_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to mark notification as read",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/notifications/{user_id}/mark_all_read")
async def mark_all_notifications_read(
    user_id: str,
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Mark all notifications as read for a user."""
    try:
        notifications = await service.get_user_notifications(user_id, 1000)
        
        for notification in notifications:
            if not notification.is_read:
                await service.mark_notification_read(user_id, notification.id)
        
        return {
            "success": True,
            "message": "All notifications marked as read",
            "count": len([n for n in notifications if not n.is_read]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to mark all notifications as read",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notifications/stats")
async def get_notification_stats(
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Get notification system statistics."""
    try:
        stats = await service.get_system_stats()
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get notification stats",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/notifications/test")
async def test_notification(
    user_id: str,
    message: str = "Test notification",
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Send a test notification to a user."""
    try:
        from ..services.realtime_notification_service import (
            Notification,
            NotificationType,
            NotificationPriority
        )
        
        # Create test notification
        notification = Notification(
            id=f"test_{int(datetime.utcnow().timestamp())}",
            type=NotificationType.SYSTEM_NOTIFICATION,
            priority=NotificationPriority.LOW,
            title="Test Notification",
            message=message,
            data={"test": True},
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        
        await service.create_notification(notification)
        
        return {
            "success": True,
            "message": "Test notification sent",
            "notification_id": notification.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to send test notification",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/connections/{user_id}/metrics")
async def get_connection_metrics(user_id: str):
    """Get WebSocket connection metrics for a user."""
    try:
        if user_id not in connection_managers:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Connection not found",
                    "message": f"No active connection for user {user_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        conn_manager = connection_managers[user_id]
        metrics = conn_manager.get_metrics()

        return {
            "success": True,
            "user_id": user_id,
            "data": {
                "state": conn_manager.get_state().value,
                "metrics": metrics,
                "subscriptions": {
                    key: {
                        "symbols": sub.symbols,
                        "notification_types": sub.notification_types,
                        "price_threshold": sub.price_threshold,
                        "sentiment_threshold": sub.sentiment_threshold,
                        "timestamp": sub.timestamp.isoformat()
                    }
                    for key, sub in conn_manager.get_subscriptions().items()
                },
                "message_buffer_size": len(conn_manager.get_message_buffer())
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting connection metrics for user {user_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get connection metrics",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/connections/status")
async def get_all_connections_status():
    """Get status of all active WebSocket connections."""
    try:
        connections_status = {}

        for user_id, conn_manager in connection_managers.items():
            metrics = conn_manager.get_metrics()
            connections_status[user_id] = {
                "state": conn_manager.get_state().value,
                "connection_duration_seconds": metrics.get("connection_duration_seconds"),
                "total_messages_sent": metrics.get("total_messages_sent"),
                "total_messages_received": metrics.get("total_messages_received"),
                "reconnection_attempts": metrics.get("reconnection_attempts"),
                "successful_reconnections": metrics.get("successful_reconnections"),
                "subscriptions_count": len(conn_manager.get_subscriptions()),
                "message_buffer_size": len(conn_manager.get_message_buffer())
            }

        return {
            "success": True,
            "total_connections": len(connections_status),
            "data": connections_status,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting all connections status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get connections status",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/connections/{user_id}/disconnect")
async def disconnect_user(user_id: str):
    """Force disconnect a user's WebSocket connection."""
    try:
        if user_id not in connection_managers:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Connection not found",
                    "message": f"No active connection for user {user_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        conn_manager = connection_managers[user_id]
        await conn_manager.disconnect()

        # Clean up from global dict
        if user_id in connection_managers:
            del connection_managers[user_id]

        return {
            "success": True,
            "message": f"Connection disconnected for user {user_id}",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error disconnecting user {user_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to disconnect user",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/pubsub/stats")
async def get_pubsub_stats():
    """Get Redis Pub/Sub Manager statistics."""
    try:
        from ..services.redis_pubsub_manager import redis_pubsub_manager

        if not redis_pubsub_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Redis Pub/Sub Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        stats = redis_pubsub_manager.get_stats()

        return {
            "success": True,
            "server_id": redis_pubsub_manager.server_id,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Pub/Sub stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get Pub/Sub stats",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/pubsub/subscriptions")
async def get_pubsub_subscriptions():
    """Get list of active Pub/Sub subscriptions."""
    try:
        from ..services.redis_pubsub_manager import redis_pubsub_manager

        if not redis_pubsub_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Redis Pub/Sub Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        subscriptions = redis_pubsub_manager.get_subscriptions()

        return {
            "success": True,
            "data": {
                "server_id": redis_pubsub_manager.server_id,
                "subscription_count": len(subscriptions),
                "subscriptions": subscriptions
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Pub/Sub subscriptions: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get Pub/Sub subscriptions",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/pubsub/errors")
async def get_pubsub_errors():
    """Get recent Pub/Sub errors."""
    try:
        from ..services.redis_pubsub_manager import redis_pubsub_manager

        if not redis_pubsub_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Redis Pub/Sub Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        errors = redis_pubsub_manager.get_error_log(limit=20)

        return {
            "success": True,
            "data": {
                "server_id": redis_pubsub_manager.server_id,
                "error_count": len(errors),
                "recent_errors": errors
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Pub/Sub errors: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get Pub/Sub errors",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/message-ordering/stats")
async def get_message_ordering_stats():
    """Get Message Ordering Manager statistics."""
    try:
        from ..services.message_ordering_manager import message_ordering_manager

        if not message_ordering_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Message Ordering Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        stats = message_ordering_manager.get_stats()

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting message ordering stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get message ordering stats",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/message-ordering/queue-status")
async def get_message_ordering_queue_status():
    """Get Message Ordering Manager queue status."""
    try:
        from ..services.message_ordering_manager import message_ordering_manager

        if not message_ordering_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Message Ordering Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        queue_size = message_ordering_manager.message_queue.qsize()
        stats = message_ordering_manager.get_stats()

        return {
            "success": True,
            "data": {
                "queue_size": queue_size,
                "current_global_sequence": stats.get("current_global_sequence"),
                "partition_count": stats.get("partition_count"),
                "total_messages": stats.get("total_messages"),
                "processed_messages": stats.get("processed_messages"),
                "failed_messages": stats.get("failed_messages"),
                "duplicates_detected": stats.get("duplicates_detected"),
                "delivery_guarantee": stats.get("delivery_guarantee")
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting message ordering queue status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get message ordering queue status",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/message-ordering/duplicate-detector-status")
async def get_duplicate_detector_status():
    """Get Duplicate Detector statistics."""
    try:
        from ..services.message_ordering_manager import message_ordering_manager

        if not message_ordering_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Message Ordering Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        duplicate_detector = message_ordering_manager.duplicate_detector

        return {
            "success": True,
            "data": {
                "ttl_seconds": duplicate_detector.ttl_seconds,
                "local_cache_size": len(duplicate_detector.local_cache),
                "processed_messages_count": len(duplicate_detector.processed_messages),
                "redis_client_available": duplicate_detector.redis_client is not None
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting duplicate detector status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get duplicate detector status",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/message-ordering/locks-status")
async def get_locks_status():
    """Get Distributed Lock Manager status."""
    try:
        from ..services.message_ordering_manager import message_ordering_manager

        if not message_ordering_manager:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Message Ordering Manager not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        lock_manager = message_ordering_manager.lock_manager
        local_locks = lock_manager.local_locks

        locks_info = {}
        for resource_id, lock in local_locks.items():
            locks_info[resource_id] = {
                "lock_id": lock.lock_id,
                "owner": lock.owner,
                "ttl_seconds": lock.ttl_seconds,
                "acquired_at": lock.acquired_at.isoformat(),
                "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
                "is_expired": lock.is_expired()
            }

        return {
            "success": True,
            "data": {
                "total_locks": len(locks_info),
                "locks": locks_info,
                "redis_client_available": lock_manager.redis_client is not None
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting locks status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get locks status",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notification-templates/stats")
async def get_notification_template_stats(
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Get notification template statistics."""
    try:
        if not service or not service.template_service:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Notification Template Service not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        stats = await service.template_service.get_template_stats()

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting template stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get template stats",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notification-templates/list")
async def list_notification_templates(
    template_type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """List notification templates with optional filters."""
    try:
        if not service or not service.template_service:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Notification Template Service not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        from ..services.notification_template_service import TemplateType, TemplateLanguage

        # Parse filter parameters
        tt = TemplateType(template_type) if template_type else None
        lang = TemplateLanguage(language) if language else None
        ch = channel if channel else None

        templates = await service.template_service.list_templates(
            template_type=tt,
            language=lang,
            active_only=True
        )

        templates_data = [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type.value,
                "language": t.language.value,
                "title_template": t.title_template,
                "message_template": t.message_template,
                "variables": t.variables,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat()
            }
            for t in templates
        ]

        return {
            "success": True,
            "total": len(templates_data),
            "data": templates_data,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to list templates",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notification-templates/{template_id}")
async def get_notification_template(
    template_id: str,
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Get a specific notification template."""
    try:
        if not service or not service.template_service:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Notification Template Service not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        template = await service.template_service.get_template(template_id)

        if not template:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Template not found",
                    "message": f"Template {template_id} does not exist",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        return {
            "success": True,
            "data": {
                "id": template.id,
                "name": template.name,
                "type": template.type.value,
                "language": template.language.value,
                "title_template": template.title_template,
                "message_template": template.message_template,
                "variables": template.variables,
                "is_active": template.is_active,
                "created_at": template.created_at.isoformat(),
                "updated_at": template.updated_at.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting template {template_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get template",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notification-templates/{template_id}/render")
async def render_notification_template(
    template_id: str,
    variables: str = Query("{}"),
    service: RealtimeNotificationService = Depends(get_notification_service)
):
    """Render a notification template with variables."""
    try:
        if not service or not service.template_service:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Notification Template Service not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        # Parse variables JSON
        import json
        try:
            vars_dict = json.loads(variables)
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid JSON variables",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        rendered = await service.template_service.render_template(template_id, vars_dict)

        if not rendered:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Failed to render template",
                    "message": f"Could not render template {template_id}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        return {
            "success": True,
            "data": {
                "template_id": rendered.template_id,
                "title": rendered.title,
                "message": rendered.message,
                "language": rendered.language.value,
                "variables": rendered.variables,
                "rendered_at": rendered.rendered_at.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error rendering template {template_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to render template",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/notification-templates/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    try:
        from ..services.notification_template_service import TemplateLanguage

        languages = [
            {"code": lang.value, "name": lang.name}
            for lang in TemplateLanguage
        ]

        return {
            "success": True,
            "total": len(languages),
            "data": languages,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting languages: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get languages",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )