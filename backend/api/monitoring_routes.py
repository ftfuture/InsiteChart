"""
Real-time Monitoring API Routes for InsiteChart platform.

This module provides REST API endpoints for real-time performance monitoring,
alerting, and system health management.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..monitoring.operational_monitor import (
    operational_monitor,
    AlertSeverity,
    OperationalStatus
)
from ..middleware.auth_middleware import get_current_user
from ..logging.structured_logger import StructuredLogger

# Initialize router
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Initialize logger
logger = StructuredLogger(__name__)

# Pydantic models for request/response
class AlertAcknowledgeRequest(BaseModel):
    alert_id: str = Field(..., description="Alert ID to acknowledge")
    acknowledged_by: str = Field(..., description="User acknowledging the alert")

class AlertResolutionRequest(BaseModel):
    alert_id: str = Field(..., description="Alert ID to resolve")

class ThresholdUpdateRequest(BaseModel):
    cpu_warning: Optional[float] = Field(None, description="CPU warning threshold", ge=0, le=100)
    cpu_critical: Optional[float] = Field(None, description="CPU critical threshold", ge=0, le=100)
    memory_warning: Optional[float] = Field(None, description="Memory warning threshold", ge=0, le=100)
    memory_critical: Optional[float] = Field(None, description="Memory critical threshold", ge=0, le=100)
    disk_warning: Optional[float] = Field(None, description="Disk warning threshold", ge=0, le=100)
    disk_critical: Optional[float] = Field(None, description="Disk critical threshold", ge=0, le=100)
    network_latency_warning: Optional[float] = Field(None, description="Network latency warning threshold in ms", ge=0)
    network_latency_critical: Optional[float] = Field(None, description="Network latency critical threshold in ms", ge=0)
    cache_hit_rate_warning: Optional[float] = Field(None, description="Cache hit rate warning threshold", ge=0, le=100)
    cache_hit_rate_critical: Optional[float] = Field(None, description="Cache hit rate critical threshold", ge=0, le=100)

class ManualAlertRequest(BaseModel):
    message: str = Field(..., description="Alert message")
    source: str = Field("manual", description="Alert source")
    severity: AlertSeverity = Field(AlertSeverity.WARNING, description="Alert severity")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional alert data")

@router.get("/status", response_model=Dict[str, Any])
async def get_monitoring_status(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current monitoring system status.
    
    Returns system health, active alerts, and monitoring statistics.
    """
    try:
        logger.info(
            "Getting monitoring status",
            user_id=current_user.get("user_id")
        )
        
        status = await operational_monitor.get_operational_status()
        
        return {
            "success": True,
            "data": status,
            "message": "Monitoring status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting monitoring status",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=Dict[str, Any])
async def get_system_health(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current system health status.
    
    Returns detailed health metrics and overall system status.
    """
    try:
        logger.info(
            "Getting system health",
            user_id=current_user.get("user_id")
        )
        
        health = operational_monitor.check_system_health()
        
        return {
            "success": True,
            "data": health,
            "message": "System health retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting system health",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=Dict[str, Any])
async def get_performance_metrics(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current performance metrics.
    
    Returns CPU, memory, disk, network, and application metrics.
    """
    try:
        logger.info(
            "Getting performance metrics",
            user_id=current_user.get("user_id")
        )
        
        metrics = operational_monitor.collect_performance_metrics()
        
        return {
            "success": True,
            "data": metrics,
            "message": "Performance metrics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting performance metrics",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=Dict[str, Any])
async def get_active_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="Filter by alert severity"),
    limit: int = Query(50, description="Maximum number of alerts to return", ge=1, le=1000),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get active alerts.
    
    - **severity**: Filter alerts by severity level
    - **limit**: Maximum number of alerts to return
    """
    try:
        logger.info(
            "Getting active alerts",
            user_id=current_user.get("user_id"),
            severity=severity.value if severity else None,
            limit=limit
        )
        
        alerts = await operational_monitor.get_active_alerts(severity)
        
        # Apply limit
        limited_alerts = alerts[:limit]
        
        return {
            "success": True,
            "data": {
                "alerts": limited_alerts,
                "total_count": len(alerts),
                "filtered_count": len(limited_alerts)
            },
            "message": "Active alerts retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting active alerts",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/acknowledge", response_model=Dict[str, Any])
async def acknowledge_alert(
    request: AlertAcknowledgeRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Acknowledge an active alert.
    
    - **alert_id**: ID of the alert to acknowledge
    - **acknowledged_by**: User acknowledging the alert
    """
    try:
        logger.info(
            "Acknowledging alert",
            user_id=current_user.get("user_id"),
            alert_id=request.alert_id,
            acknowledged_by=request.acknowledged_by
        )
        
        success = await operational_monitor.acknowledge_alert(
            alert_id=request.alert_id,
            acknowledged_by=request.acknowledged_by
        )
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Alert acknowledged",
            user_id=current_user.get("user_id"),
            alert_id=request.alert_id,
            success=success
        )
        
        if success:
            return {
                "success": True,
                "message": f"Alert {request.alert_id} acknowledged successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Alert {request.alert_id} not found or already acknowledged"
            }
        
    except Exception as e:
        logger.error(
            "Error acknowledging alert",
            user_id=current_user.get("user_id"),
            alert_id=request.alert_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    request: AlertResolutionRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Resolve an active alert.
    
    - **alert_id**: ID of the alert to resolve
    """
    try:
        logger.info(
            "Resolving alert",
            user_id=current_user.get("user_id"),
            alert_id=request.alert_id
        )
        
        success = await operational_monitor.resolve_alert(alert_id=request.alert_id)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Alert resolved",
            user_id=current_user.get("user_id"),
            alert_id=request.alert_id,
            success=success
        )
        
        if success:
            return {
                "success": True,
                "message": f"Alert {request.alert_id} resolved successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Alert {request.alert_id} not found or already resolved"
            }
        
    except Exception as e:
        logger.error(
            "Error resolving alert",
            user_id=current_user.get("user_id"),
            alert_id=request.alert_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/manual", response_model=Dict[str, Any])
async def create_manual_alert(
    request: ManualAlertRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a manual alert.
    
    - **message**: Alert message
    - **source**: Alert source
    - **severity**: Alert severity level
    - **data**: Additional alert data
    """
    try:
        logger.info(
            "Creating manual alert",
            user_id=current_user.get("user_id"),
            message=request.message,
            source=request.source,
            severity=request.severity.value
        )
        
        operational_monitor.create_alert({
            "message": request.message,
            "source": request.source,
            "severity": request.severity.value,
            "data": request.data
        })
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Manual alert created",
            user_id=current_user.get("user_id"),
            message=request.message
        )
        
        return {
            "success": True,
            "message": "Manual alert created successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error creating manual alert",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/history", response_model=Dict[str, Any])
async def get_metrics_history(
    start_time: Optional[datetime] = Query(None, description="Start time for metrics history"),
    end_time: Optional[datetime] = Query(None, description="End time for metrics history"),
    interval: str = Query("5m", description="Aggregation interval (1m, 5m, 15m, 1h)"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get historical metrics data.
    
    - **start_time**: Start time for historical data
    - **end_time**: End time for historical data
    - **interval**: Aggregation interval for metrics
    """
    try:
        logger.info(
            "Getting metrics history",
            user_id=current_user.get("user_id"),
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
            interval=interval
        )
        
        # Convert to timestamps if provided
        start_timestamp = start_time.timestamp() if start_time else (datetime.utcnow() - timedelta(hours=24)).timestamp()
        end_timestamp = end_time.timestamp() if end_time else datetime.utcnow().timestamp()
        
        history = operational_monitor.aggregate_metrics(
            start_time=start_timestamp,
            end_time=end_timestamp,
            interval=interval
        )
        
        return {
            "success": True,
            "data": {
                "metrics": history,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "interval": interval
            },
            "message": "Metrics history retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting metrics history",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get comprehensive dashboard data.
    
    Returns all monitoring data needed for the dashboard view.
    """
    try:
        logger.info(
            "Getting dashboard data",
            user_id=current_user.get("user_id")
        )
        
        dashboard_data = operational_monitor.get_dashboard_data()
        
        return {
            "success": True,
            "data": dashboard_data,
            "message": "Dashboard data retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting dashboard data",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/thresholds", response_model=Dict[str, Any])
async def update_alert_thresholds(
    request: ThresholdUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Update alert thresholds.
    
    - **cpu_warning**: CPU warning threshold percentage
    - **cpu_critical**: CPU critical threshold percentage
    - **memory_warning**: Memory warning threshold percentage
    - **memory_critical**: Memory critical threshold percentage
    - **disk_warning**: Disk warning threshold percentage
    - **disk_critical**: Disk critical threshold percentage
    - **network_latency_warning**: Network latency warning threshold in ms
    - **network_latency_critical**: Network latency critical threshold in ms
    - **cache_hit_rate_warning**: Cache hit rate warning threshold percentage
    - **cache_hit_rate_critical**: Cache hit rate critical threshold percentage
    """
    try:
        logger.info(
            "Updating alert thresholds",
            user_id=current_user.get("user_id")
        )
        
        # Build threshold updates dictionary
        threshold_updates = {}
        
        if request.cpu_warning is not None:
            threshold_updates["cpu_warning"] = request.cpu_warning
        if request.cpu_critical is not None:
            threshold_updates["cpu_critical"] = request.cpu_critical
        if request.memory_warning is not None:
            threshold_updates["memory_warning"] = request.memory_warning
        if request.memory_critical is not None:
            threshold_updates["memory_critical"] = request.memory_critical
        if request.disk_warning is not None:
            threshold_updates["disk_warning"] = request.disk_warning
        if request.disk_critical is not None:
            threshold_updates["disk_critical"] = request.disk_critical
        if request.network_latency_warning is not None:
            threshold_updates["network_latency_warning"] = request.network_latency_warning
        if request.network_latency_critical is not None:
            threshold_updates["network_latency_critical"] = request.network_latency_critical
        if request.cache_hit_rate_warning is not None:
            threshold_updates["cache_hit_rate_warning"] = request.cache_hit_rate_warning
        if request.cache_hit_rate_critical is not None:
            threshold_updates["cache_hit_rate_critical"] = request.cache_hit_rate_critical
        
        # Update thresholds
        operational_monitor.update_alert_thresholds(threshold_updates)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Alert thresholds updated",
            user_id=current_user.get("user_id"),
            updated_thresholds=list(threshold_updates.keys())
        )
        
        return {
            "success": True,
            "data": {
                "updated_thresholds": list(threshold_updates.keys()),
                "current_thresholds": operational_monitor.alert_thresholds
            },
            "message": "Alert thresholds updated successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error updating alert thresholds",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/thresholds", response_model=Dict[str, Any])
async def get_alert_thresholds(
    current_user: Dict = Depends(get_current_user)
):
    """Get current alert thresholds."""
    try:
        logger.info(
            "Getting alert thresholds",
            user_id=current_user.get("user_id")
        )
        
        return {
            "success": True,
            "data": operational_monitor.alert_thresholds,
            "message": "Alert thresholds retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting alert thresholds",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services", response_model=Dict[str, Any])
async def get_monitored_services(
    current_user: Dict = Depends(get_current_user)
):
    """Get list of monitored services."""
    try:
        logger.info(
            "Getting monitored services",
            user_id=current_user.get("user_id")
        )
        
        services = list(operational_monitor.monitored_services.keys())
        
        return {
            "success": True,
            "data": {
                "services": services,
                "total_count": len(services)
            },
            "message": "Monitored services retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting monitored services",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start", response_model=Dict[str, Any])
async def start_monitoring(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """Start the monitoring system."""
    try:
        logger.info(
            "Starting monitoring system",
            user_id=current_user.get("user_id")
        )
        
        await operational_monitor.start_monitoring()
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Monitoring system started",
            user_id=current_user.get("user_id")
        )
        
        return {
            "success": True,
            "message": "Monitoring system started successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error starting monitoring system",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop", response_model=Dict[str, Any])
async def stop_monitoring(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """Stop the monitoring system."""
    try:
        logger.info(
            "Stopping monitoring system",
            user_id=current_user.get("user_id")
        )
        
        await operational_monitor.stop_monitoring()
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Monitoring system stopped",
            user_id=current_user.get("user_id")
        )
        
        return {
            "success": True,
            "message": "Monitoring system stopped successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error stopping monitoring system",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/severities", response_model=Dict[str, Any])
async def get_alert_severities(
    current_user: Dict = Depends(get_current_user)
):
    """Get available alert severity levels."""
    try:
        severities = [
            {
                "value": severity.value,
                "name": severity.value.title(),
                "description": _get_severity_description(severity)
            }
            for severity in AlertSeverity
        ]
        
        return {
            "success": True,
            "data": severities,
            "message": "Alert severities retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting alert severities",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statuses", response_model=Dict[str, Any])
async def get_operational_statuses(
    current_user: Dict = Depends(get_current_user)
):
    """Get available operational status types."""
    try:
        statuses = [
            {
                "value": status.value,
                "name": status.value.title(),
                "description": _get_status_description(status)
            }
            for status in OperationalStatus
        ]
        
        return {
            "success": True,
            "data": statuses,
            "message": "Operational statuses retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting operational statuses",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

def _get_severity_description(severity: AlertSeverity) -> str:
    """Get description for alert severity."""
    descriptions = {
        AlertSeverity.INFO: "Informational alert for general notifications",
        AlertSeverity.WARNING: "Warning alert for potential issues that require attention",
        AlertSeverity.ERROR: "Error alert for confirmed issues that need investigation",
        AlertSeverity.CRITICAL: "Critical alert for severe issues requiring immediate action"
    }
    return descriptions.get(severity, "Unknown severity")

def _get_status_description(status: OperationalStatus) -> str:
    """Get description for operational status."""
    descriptions = {
        OperationalStatus.HEALTHY: "System is operating normally with no issues",
        OperationalStatus.DEGRADED: "System is experiencing performance issues but still functional",
        OperationalStatus.UNHEALTHY: "System has significant issues affecting functionality",
        OperationalStatus.DOWN: "System is completely non-functional"
    }
    return descriptions.get(status, "Unknown status")