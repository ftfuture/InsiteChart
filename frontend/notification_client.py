"""
WebSocket Notification Client for InsiteChart Frontend.

This module provides a client interface for real-time notifications
using WebSocket connections to the InsiteChart backend.
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import streamlit as st
import websockets
from threading import Thread
import queue
import time

from .api_client import InsiteChartAPIClient


class NotificationClient:
    """WebSocket client for real-time notifications."""
    
    def __init__(self, api_client: InsiteChartAPIClient, user_id: str):
        self.api_client = api_client
        self.user_id = user_id
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Event handlers
        self.on_notification: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        
        # Message queue for thread-safe communication
        self.message_queue = queue.Queue()
        self.notification_history: List[Dict] = []
        
        # Background thread for WebSocket
        self.background_thread: Optional[Thread] = None
        self.should_stop = False
        
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """Connect to WebSocket server."""
        try:
            # Extract WebSocket URL from API base URL
            ws_url = self.api_client.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url = f"{ws_url}/notifications/{self.user_id}"
            
            # Start background thread for WebSocket connection
            self.background_thread = Thread(target=self._run_websocket, args=(ws_url,))
            self.background_thread.daemon = True
            self.background_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from WebSocket server."""
        try:
            self.should_stop = True
            self.is_connected = False
            
            if self.websocket:
                self.websocket.close()
            
            if self.background_thread and self.background_thread.is_alive():
                self.background_thread.join(timeout=5)
            
            self.logger.info("Disconnected from WebSocket")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from WebSocket: {str(e)}")
    
    def subscribe(self, symbols: List[str], notification_types: List[str] = None,
                price_threshold: float = None, sentiment_threshold: float = None):
        """Subscribe to notifications."""
        try:
            if not self.is_connected:
                return False
            
            subscription_message = {
                "type": "subscribe",
                "data": {
                    "symbols": symbols,
                    "notification_types": notification_types or [],
                    "price_threshold": price_threshold,
                    "sentiment_threshold": sentiment_threshold
                }
            }
            
            self._send_message(subscription_message)
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing to notifications: {str(e)}")
            return False
    
    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        """Get notification history."""
        try:
            # Get from backend API
            response = self.api_client._make_request(
                "GET", 
                f"/notifications/{self.user_id}",
                params={"limit": limit}
            )
            
            if response.get("success", False):
                self.notification_history = response.get("data", [])
                return self.notification_history
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting notification history: {str(e)}")
            return []
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read."""
        try:
            response = self.api_client._make_request(
                "POST",
                f"/notifications/{self.user_id}/mark_read",
                json={"notification_id": notification_id}
            )
            
            return response.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    def mark_all_notifications_read(self) -> bool:
        """Mark all notifications as read."""
        try:
            response = self.api_client._make_request(
                "POST",
                f"/notifications/{self.user_id}/mark_all_read"
            )
            
            if response.get("success", False):
                # Update local history
                for notification in self.notification_history:
                    notification["is_read"] = True
            
            return response.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Error marking all notifications as read: {str(e)}")
            return False
    
    def send_test_notification(self, message: str = "Test notification") -> bool:
        """Send a test notification."""
        try:
            response = self.api_client._make_request(
                "POST",
                f"/notifications/test",
                json={"user_id": self.user_id, "message": message}
            )
            
            return response.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Error sending test notification: {str(e)}")
            return False
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return len([n for n in self.notification_history if not n.get("is_read", False)])
    
    def _run_websocket(self, ws_url: str):
        """Run WebSocket connection in background thread."""
        while not self.should_stop and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Connect to WebSocket
                self.websocket = websockets.connect(ws_url)
                
                with self.websocket as ws:
                    self.is_connected = True
                    self.reconnect_attempts = 0
                    
                    # Notify connection change
                    if self.on_connection_change:
                        self.on_connection_change(True)
                    
                    self.logger.info(f"Connected to WebSocket: {ws_url}")
                    
                    # Send initial ping
                    self._send_message({"type": "ping"})
                    
                    # Listen for messages
                    while not self.should_stop:
                        try:
                            message = ws.recv()
                            self._handle_message(message)
                            
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception as e:
                            self.logger.error(f"Error receiving message: {str(e)}")
                            break
                    
                    self.is_connected = False
                    
                    # Notify connection change
                    if self.on_connection_change:
                        self.on_connection_change(False)
            
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {str(e)}")
                self.is_connected = False
                
                # Notify connection change
                if self.on_connection_change:
                    self.on_connection_change(False)
            
            # Reconnect logic
            if not self.should_stop and self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                self.logger.info(f"Reconnecting in {self.reconnect_delay} seconds (attempt {self.reconnect_attempts})")
                time.sleep(self.reconnect_delay)
                
                # Exponential backoff
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)
    
    def _handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "notification":
                # Handle notification
                notification = data.get("data", {})
                self.notification_history.insert(0, notification)
                
                # Keep only last 100 notifications
                if len(self.notification_history) > 100:
                    self.notification_history = self.notification_history[:100]
                
                # Call notification handler
                if self.on_notification:
                    self.on_notification(notification)
            
            elif message_type == "pong":
                # Handle pong response
                self.logger.debug("Received pong from server")
            
            elif message_type == "subscription_confirmed":
                # Handle subscription confirmation
                self.logger.info("Subscription confirmed")
            
            elif message_type == "notification_history":
                # Handle notification history
                history = data.get("data", [])
                self.notification_history = history
            
            elif message_type == "notification_marked_read":
                # Handle notification marked as read
                notification_id = data.get("notification_id")
                for notification in self.notification_history:
                    if notification.get("id") == notification_id:
                        notification["is_read"] = True
                        break
            
            elif message_type == "error":
                # Handle error message
                error_message = data.get("message", "Unknown error")
                self.logger.error(f"WebSocket error: {error_message}")
            
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON received from WebSocket")
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {str(e)}")
    
    def _send_message(self, message: Dict):
        """Send message to WebSocket."""
        try:
            if self.websocket and self.is_connected:
                self.websocket.send(json.dumps(message))
            else:
                self.logger.warning("Cannot send message: WebSocket not connected")
        
        except Exception as e:
            self.logger.error(f"Error sending WebSocket message: {str(e)}")


# Streamlit integration utilities
@st.cache_resource
def get_notification_client(user_id: str) -> NotificationClient:
    """Get cached notification client instance."""
    api_client = get_api_client()
    return NotificationClient(api_client, user_id)


def init_notification_system(user_id: str = "demo_user"):
    """Initialize notification system in Streamlit."""
    # Initialize notification client
    if 'notification_client' not in st.session_state:
        st.session_state.notification_client = get_notification_client(user_id)
        
        # Set up event handlers
        def on_notification(notification):
            """Handle incoming notification."""
            # Add to session state for UI updates
            if 'notifications' not in st.session_state:
                st.session_state.notifications = []
            
            st.session_state.notifications.insert(0, notification)
            
            # Keep only last 50 notifications
            if len(st.session_state.notifications) > 50:
                st.session_state.notifications = st.session_state.notifications[:50]
            
            # Trigger rerun to update UI
            st.rerun()
        
        def on_connection_change(connected):
            """Handle connection change."""
            st.session_state.notification_connected = connected
            st.rerun()
        
        client = st.session_state.notification_client
        client.on_notification = on_notification
        client.on_connection_change = on_connection_change
        
        # Connect to WebSocket
        if not client.is_connected:
            client.connect()
    
    # Initialize notifications list
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    
    return st.session_state.notification_client


def render_notification_panel():
    """Render notification panel in Streamlit sidebar."""
    if 'notification_client' not in st.session_state:
        return
    
    client = st.session_state.notification_client
    
    # Connection status
    if client.is_connected:
        st.sidebar.success("🟢 Notifications Connected")
    else:
        st.sidebar.error("🔴 Notifications Disconnected")
    
    # Unread count
    unread_count = client.get_unread_count()
    if unread_count > 0:
        st.sidebar.markdown(f"### 🔔 Notifications ({unread_count})")
    else:
        st.sidebar.markdown("### 🔔 Notifications")
    
    # Recent notifications
    notifications = st.session_state.get('notifications', [])
    
    if notifications:
        for notification in notifications[:5]:  # Show only 5 most recent
            is_read = notification.get('is_read', False)
            notification_type = notification.get('type', 'system_notification')
            
            # Notification styling
            if not is_read:
                bg_color = "#e8f5e8"
                border_color = "#26a69a"
            else:
                bg_color = "#f8f9fa"
                border_color = "#dee2e6"
            
            # Icon based on type
            icons = {
                "price_alert": "💰",
                "sentiment_alert": "💬",
                "trending_alert": "🔥",
                "volume_spike": "📊",
                "market_event": "🌊",
                "system_notification": "ℹ️"
            }
            
            icon = icons.get(notification_type, "ℹ️")
            
            st.sidebar.markdown(f"""
            <div style="padding: 10px; margin: 5px 0; border-left: 3px solid {border_color}; 
                        background-color: {bg_color}; border-radius: 3px;">
                <strong>{icon} {notification.get('title', 'Notification')}</strong><br>
                <small>{notification.get('message', '')}</small><br>
                <small>{notification.get('timestamp', '')}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Notification actions
    st.sidebar.markdown("---")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🔄 Refresh", key="refresh_notifications"):
            notifications = client.get_notification_history()
            st.session_state.notifications = notifications
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear All", key="clear_notifications"):
            client.mark_all_notifications_read()
            st.session_state.notifications = []
            st.rerun()
    
    # Test notification
    if st.sidebar.button("🧪 Test Notification"):
        client.send_test_notification("This is a test notification from InsiteChart")


def subscribe_to_symbol_notifications(symbols: List[str], 
                                 price_threshold: float = 5.0,
                                 sentiment_threshold: float = 0.3):
    """Subscribe to notifications for specific symbols."""
    if 'notification_client' not in st.session_state:
        return False
    
    client = st.session_state.notification_client
    
    if not client.is_connected:
        return False
    
    notification_types = [
        "price_alert",
        "sentiment_alert", 
        "trending_alert",
        "volume_spike"
    ]
    
    return client.subscribe(
        symbols=symbols,
        notification_types=notification_types,
        price_threshold=price_threshold,
        sentiment_threshold=sentiment_threshold
    )