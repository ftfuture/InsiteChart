"""
WebSocket routes for real-time notifications in InsiteChart platform.

This module handles WebSocket connections for real-time notifications,
including stock price alerts, sentiment changes, and market events.
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
from ..services.unified_service import UnifiedService
from ..cache.unified_cache import UnifiedCacheManager


# Create router
router = APIRouter()
logger = logging.getLogger(__name__)


# Global notification service instance
notification_service: Optional[RealtimeNotificationService] = None


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
    """WebSocket endpoint for real-time notifications."""
    try:
        # Connect user
        await service.connect(websocket, user_id)
        
        # Handle WebSocket messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
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
                    
                    # Send confirmation
                    response = {
                        "type": "subscription_confirmed",
                        "data": subscription.dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                
                elif message_type == "ping":
                    # Handle ping/pong for connection health
                    response = {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                
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
                break
            except json.JSONDecodeError:
                # Invalid JSON
                response = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(response))
            except Exception as e:
                # Error handling message
                logger.error(f"Error handling WebSocket message: {str(e)}")
                response = {
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(response))
    
    except WebSocketDisconnect:
        # Client disconnected
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        # Error in WebSocket connection
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        # Clean up connection
        await service.disconnect(user_id)


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