"""
Security API routes for InsiteChart platform.

This module provides security monitoring, threat detection,
and automated response endpoints.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..services.security_service import (
    SecurityService,
    SecurityEvent,
    SecurityRule,
    SecurityEventType,
    SecuritySeverity,
    SecurityAction
)
from ..cache.unified_cache import UnifiedCacheManager


# Create router
router = APIRouter()
logger = logging.getLogger(__name__)

# Security scheme for protected endpoints
security = HTTPBearer(auto_error=False)


# Global security service instance
security_service: Optional[SecurityService] = None


async def get_security_service() -> SecurityService:
    """Dependency to get security service instance."""
    global security_service
    
    if security_service is None:
        cache_manager = UnifiedCacheManager()
        security_service = SecurityService(cache_manager)
        await security_service.start()
    
    return security_service


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from credentials."""
    # This is a simplified implementation
    # In production, you'd validate JWT tokens or other auth mechanisms
    if credentials:
        return {"user_id": "authenticated_user", "role": "user"}
    return {"user_id": "anonymous", "role": "guest"}


@router.post("/security/analyze-request")
async def analyze_request_security(
    request: Request,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Analyze incoming request for security threats."""
    try:
        # Extract request data
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type")
        }
        
        # Get request body if available
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_data["body"] = body.decode("utf-8", errors="ignore")
            except Exception:
                request_data["body"] = None
        
        # Analyze for security threats
        events = await service.analyze_request(
            request_data=request_data,
            source_ip=request_data["client_ip"],
            user_id=user_data.get("user_id"),
            user_agent=request_data["user_agent"],
            endpoint=request_data["url"]
        )
        
        return {
            "success": True,
            "data": {
                "events_detected": len(events),
                "events": [
                    {
                        "id": event.id,
                        "event_type": event.event_type.value,
                        "severity": event.severity.value,
                        "description": event.description,
                        "timestamp": event.timestamp.isoformat(),
                        "response_actions": [action.value for action in (event.response_actions or [])]
                    }
                    for event in events
                ],
                "request_info": {
                    "ip": request_data["client_ip"],
                    "method": request_data["method"],
                    "endpoint": request_data["url"]
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing request security: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/security/events")
async def get_security_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    severity: Optional[SecuritySeverity] = Query(None, description="Filter by severity"),
    event_type: Optional[SecurityEventType] = Query(None, description="Filter by event type"),
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Get recent security events."""
    try:
        # Check permissions (only admin users can access all events)
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        events = await service.get_recent_events(limit, severity, event_type)
        
        return {
            "success": True,
            "data": {
                "events": [
                    {
                        "id": event.id,
                        "event_type": event.event_type.value,
                        "severity": event.severity.value,
                        "timestamp": event.timestamp.isoformat(),
                        "source_ip": event.source_ip,
                        "user_id": event.user_id,
                        "user_agent": event.user_agent,
                        "endpoint": event.endpoint,
                        "description": event.description,
                        "metadata": event.metadata,
                        "resolved": event.resolved,
                        "response_actions": [action.value for action in (event.response_actions or [])]
                    }
                    for event in events
                ],
                "count": len(events),
                "filters": {
                    "severity": severity.value if severity else None,
                    "event_type": event_type.value if event_type else None,
                    "limit": limit
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/security/metrics")
async def get_security_metrics(
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Get security metrics and statistics."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        metrics = await service.get_security_metrics()
        
        return {
            "success": True,
            "data": {
                "total_events": metrics.total_events,
                "events_by_type": dict(metrics.events_by_type),
                "events_by_severity": dict(metrics.events_by_severity),
                "blocked_ips": metrics.blocked_ips,
                "rate_limited_requests": metrics.rate_limited_requests,
                "active_investigations": metrics.active_investigations,
                "false_positives": metrics.false_positives,
                "detection_accuracy": metrics.detection_accuracy,
                "last_updated": metrics.last_updated.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/rules")
async def create_security_rule(
    rule: dict,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Create a new security rule."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Create security rule
        security_rule = SecurityRule(
            id=rule.get("id", f"rule_{int(datetime.utcnow().timestamp())}"),
            name=rule.get("name", "Unnamed Rule"),
            event_type=SecurityEventType(rule.get("event_type")),
            conditions=rule.get("conditions", {}),
            actions=[SecurityAction(action) for action in rule.get("actions", [])],
            severity=SecuritySeverity(rule.get("severity", "medium")),
            enabled=rule.get("enabled", True),
            cooldown_period=rule.get("cooldown_period", 300)
        )
        
        await service.add_security_rule(security_rule)
        
        return {
            "success": True,
            "data": {
                "rule_id": security_rule.id,
                "name": security_rule.name,
                "event_type": security_rule.event_type.value,
                "actions": [action.value for action in security_rule.actions],
                "severity": security_rule.severity.value,
                "enabled": security_rule.enabled,
                "cooldown_period": security_rule.cooldown_period
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating security rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/security/rules/{rule_id}")
async def update_security_rule(
    rule_id: str,
    updates: dict,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Update an existing security rule."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        await service.update_security_rule(rule_id, updates)
        
        return {
            "success": True,
            "data": {
                "rule_id": rule_id,
                "updates": updates
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating security rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/block-ip")
async def block_ip_address(
    ip_data: dict,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Block an IP address."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        ip_address = ip_data.get("ip_address")
        duration_hours = ip_data.get("duration_hours", 24)
        reason = ip_data.get("reason", "Manual block")
        
        if not ip_address:
            raise HTTPException(status_code=400, detail="IP address is required")
        
        await service.block_ip(ip_address, duration_hours, reason)
        
        return {
            "success": True,
            "data": {
                "ip_address": ip_address,
                "duration_hours": duration_hours,
                "reason": reason,
                "blocked_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking IP address: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/unblock-ip")
async def unblock_ip_address(
    ip_data: dict,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Unblock an IP address."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        ip_address = ip_data.get("ip_address")
        
        if not ip_address:
            raise HTTPException(status_code=400, detail="IP address is required")
        
        await service.unblock_ip(ip_address)
        
        return {
            "success": True,
            "data": {
                "ip_address": ip_address,
                "unblocked_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking IP address: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/security/ip-check/{ip_address}")
async def check_ip_status(
    ip_address: str,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Check if an IP address is blocked."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        is_blocked = await service.is_ip_blocked(ip_address)
        
        return {
            "success": True,
            "data": {
                "ip_address": ip_address,
                "is_blocked": is_blocked,
                "checked_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking IP status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/security/blocked-ips")
async def get_blocked_ips(
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Get list of blocked IP addresses."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get blocked IPs from service
        blocked_ips = service.blocked_ips
        
        blocked_list = []
        for ip, expiration in blocked_ips.items():
            blocked_list.append({
                "ip_address": ip,
                "expires_at": expiration.isoformat(),
                "remaining_hours": (expiration - datetime.utcnow()).total_seconds() / 3600
            })
        
        return {
            "success": True,
            "data": {
                "blocked_ips": blocked_list,
                "total_blocked": len(blocked_list)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blocked IPs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/security/test-alert")
async def test_security_alert(
    alert_data: dict,
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Create a test security alert."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Create test event
        test_event = SecurityEvent(
            id=f"test_{int(datetime.utcnow().timestamp())}",
            event_type=SecurityEventType(alert_data.get("event_type", "system_anomaly")),
            severity=SecuritySeverity(alert_data.get("severity", "medium")),
            timestamp=datetime.utcnow(),
            source_ip=alert_data.get("source_ip", "test_source"),
            user_id=user_data.get("user_id"),
            description=alert_data.get("description", "Test security alert"),
            metadata=alert_data.get("metadata", {"test": True})
        )
        
        # Process the test event
        await service._process_security_event(test_event)
        
        return {
            "success": True,
            "data": {
                "event_id": test_event.id,
                "event_type": test_event.event_type.value,
                "severity": test_event.severity.value,
                "description": test_event.description,
                "created_at": test_event.timestamp.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/security/dashboard")
async def get_security_dashboard(
    user_data: dict = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service)
):
    """Get security dashboard data."""
    try:
        # Check permissions
        if user_data.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get metrics
        metrics = await service.get_security_metrics()
        
        # Get recent events
        recent_events = await service.get_recent_events(limit=10)
        
        # Get blocked IPs count
        blocked_count = len(service.blocked_ips)
        
        # Get active investigations
        active_investigations = len(service.active_investigations)
        
        return {
            "success": True,
            "data": {
                "overview": {
                    "total_events": metrics.total_events,
                    "blocked_ips": blocked_count,
                    "active_investigations": active_investigations,
                    "detection_accuracy": metrics.detection_accuracy
                },
                "recent_events": [
                    {
                        "id": event.id,
                        "event_type": event.event_type.value,
                        "severity": event.severity.value,
                        "timestamp": event.timestamp.isoformat(),
                        "source_ip": event.source_ip,
                        "description": event.description
                    }
                    for event in recent_events
                ],
                "events_by_severity": dict(metrics.events_by_severity),
                "events_by_type": dict(metrics.events_by_type)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")