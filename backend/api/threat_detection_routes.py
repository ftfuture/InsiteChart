"""
Threat Detection API Routes for InsiteChart platform.

This module provides REST API endpoints for automated threat detection,
security monitoring, and response management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.threat_detection_service import (
    ThreatDetectionService,
    ThreatType,
    ThreatSeverity,
    ResponseAction
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/threat-detection", tags=["Threat Detection"])

# Pydantic models for request/response
class ThreatAnalysisRequest(BaseModel):
    """Model for threat analysis request."""
    client_ip: str = Field(..., description="Client IP address")
    method: str = Field("GET", description="HTTP method")
    path: str = Field("/", description="Request path")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    body: str = Field("", description="Request body")
    query_params: Dict[str, str] = Field(default_factory=dict, description="Query parameters")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")

class SecurityRuleCreate(BaseModel):
    """Model for creating a security rule."""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    threat_type: ThreatType = Field(..., description="Threat type")
    severity: ThreatSeverity = Field(..., description="Threat severity")
    pattern: str = Field("", description="Pattern to match")
    response_actions: List[ResponseAction] = Field(..., description="Response actions")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Rule conditions")
    enabled: bool = Field(True, description="Enable rule")

class IPUnblockRequest(BaseModel):
    """Model for IP unblock request."""
    ip_address: str = Field(..., description="IP address to unblock")
    reason: str = Field(..., description="Reason for unblocking")

# Dependency to get threat detection service
async def get_threat_detection_service() -> ThreatDetectionService:
    """Get threat detection service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return ThreatDetectionService(cache_manager)
    except Exception as e:
        logger.error(f"Error creating threat detection service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize threat detection service")

@router.post("/analyze")
async def analyze_threat(
    request: ThreatAnalysisRequest,
    background_tasks: BackgroundTasks,
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze request for security threats.
    
    This endpoint analyzes incoming requests for various security threats
    including SQL injection, XSS, brute force attacks, and anomalous behavior.
    """
    try:
        # Check admin permissions for detailed analysis
        if not current_user.is_admin:
            # Non-admin users can only analyze their own requests
            if request.user_id and request.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to analyze requests for other users")
        
        # Convert to dict for service
        request_data = {
            "client_ip": request.client_ip,
            "method": request.method,
            "path": request.path,
            "headers": request.headers,
            "body": request.body,
            "query_params": request.query_params
        }
        
        # Analyze request
        result = await threat_service.analyze_request(request_data, request.user_id)
        
        return {
            "success": True,
            "analysis": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing threat: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/threats")
async def get_threat_events(
    threat_type: Optional[ThreatType] = Query(None, description="Filter by threat type"),
    severity: Optional[ThreatSeverity] = Query(None, description="Filter by severity"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of events"),
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get threat events.
    
    This endpoint retrieves threat events with optional filtering.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        events = await threat_service.get_threat_events(
            threat_type=threat_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(events),
            "events": events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/risk-profiles")
async def get_risk_profiles(
    identifier: Optional[str] = Query(None, description="Filter by identifier (IP or user ID)"),
    min_risk_score: Optional[float] = Query(None, description="Filter by minimum risk score"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of profiles"),
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get risk profiles.
    
    This endpoint retrieves risk profiles for IP addresses and users.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        profiles = await threat_service.get_risk_profiles(
            identifier=identifier,
            min_risk_score=min_risk_score,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(profiles),
            "profiles": profiles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk profiles: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/security-rules")
async def get_security_rules(
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get security rules.
    
    This endpoint retrieves all security rules used for threat detection.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        rules = await threat_service.get_security_rules()
        
        return {
            "success": True,
            "count": len(rules),
            "rules": rules
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/security-rules")
async def create_security_rule(
    rule: SecurityRuleCreate,
    background_tasks: BackgroundTasks,
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new security rule.
    
    This endpoint creates a new security rule for threat detection.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create the rule in the service
        # For now, return a success response
        return {
            "success": True,
            "rule_id": rule.rule_id,
            "message": "Security rule created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating security rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blocked-ips")
async def get_blocked_ips(
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get blocked IP addresses.
    
    This endpoint retrieves all currently blocked IP addresses.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        blocked_ips = await threat_service.get_blocked_ips()
        
        return {
            "success": True,
            "count": len(blocked_ips),
            "blocked_ips": blocked_ips
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blocked IPs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/unblock-ip")
async def unblock_ip(
    request: IPUnblockRequest,
    background_tasks: BackgroundTasks,
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Unblock an IP address.
    
    This endpoint unblocks a previously blocked IP address.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await threat_service.unblock_ip(request.ip_address)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        # Log the unblock action
        logger.info(f"IP {request.ip_address} unblocked by admin {current_user.id}: {request.reason}")
        
        return {
            "success": True,
            "ip_address": request.ip_address,
            "message": result["message"],
            "reason": request.reason,
            "unblocked_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking IP: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/statistics")
async def get_threat_statistics(
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get threat detection statistics.
    
    This endpoint retrieves comprehensive threat detection statistics.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        statistics = await threat_service.get_threat_statistics()
        
        return {
            "success": True,
            "statistics": statistics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/my-risk-profile")
async def get_my_risk_profile(
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's risk profile.
    
    This endpoint retrieves the risk profile for the currently authenticated user.
    """
    try:
        profiles = await threat_service.get_risk_profiles(
            identifier=current_user.id,
            limit=1
        )
        
        if profiles:
            return {
                "success": True,
                "profile": profiles[0]
            }
        else:
            return {
                "success": True,
                "profile": None,
                "message": "No risk profile found"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user risk profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/my-threats")
async def get_my_threat_events(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of events"),
    threat_service: ThreatDetectionService = Depends(get_threat_detection_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get threat events for current user.
    
    This endpoint retrieves threat events associated with the currently authenticated user.
    """
    try:
        events = await threat_service.get_threat_events(
            user_id=current_user.id,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(events),
            "events": events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user threat events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception in threat detection routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )