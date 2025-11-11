"""
Auto Scaling API Routes for InsiteChart platform.

This module provides REST API endpoints for cloud-native auto-scaling
and resource management functionality.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.auto_scaling_service import (
    AutoScalingService,
    ScalingDirection,
    ScalingTrigger,
    CloudProvider
)
from ..cache.unified_cache import UnifiedCacheManager
from ..middleware.auth_middleware import get_current_user
from ..logging.structured_logger import StructuredLogger

# Initialize router
router = APIRouter(prefix="/api/auto-scaling", tags=["auto-scaling"])

# Initialize logger
logger = StructuredLogger(__name__)

# Pydantic models for request/response
class ManualScalingRequest(BaseModel):
    target_instances: int = Field(..., description="Target number of instances", ge=1, le=50)
    reason: str = Field("Manual scaling", description="Reason for scaling")

class ConfigurationUpdateRequest(BaseModel):
    provider: Optional[CloudProvider] = Field(None, description="Cloud provider")
    target_cpu: Optional[float] = Field(None, description="Target CPU utilization percentage", ge=0, le=100)
    target_memory: Optional[float] = Field(None, description="Target memory utilization percentage", ge=0, le=100)
    target_response_time: Optional[float] = Field(None, description="Target response time in milliseconds", ge=0)
    scale_out_threshold: Optional[float] = Field(None, description="Scale out threshold percentage", ge=0, le=100)
    scale_in_threshold: Optional[float] = Field(None, description="Scale in threshold percentage", ge=0, le=100)
    cooldown_period: Optional[int] = Field(None, description="Cooldown period in seconds", ge=60)
    min_instances: Optional[int] = Field(None, description="Minimum number of instances", ge=1)
    max_instances: Optional[int] = Field(None, description="Maximum number of instances", ge=1)

class ScalingPolicyRequest(BaseModel):
    name: str = Field(..., description="Policy name")
    trigger_type: ScalingTrigger = Field(..., description="Trigger type")
    threshold_min: float = Field(..., description="Minimum threshold")
    threshold_max: float = Field(..., description="Maximum threshold")
    scale_out_cooldown: int = Field(300, description="Scale out cooldown in seconds", ge=60)
    scale_in_cooldown: int = Field(300, description="Scale in cooldown in seconds", ge=60)
    min_instances: int = Field(1, description="Minimum instances", ge=1)
    max_instances: int = Field(10, description="Maximum instances", ge=1)
    scale_out_step: int = Field(1, description="Scale out step", ge=1)
    scale_in_step: int = Field(1, description="Scale in step", ge=1)
    enabled: bool = Field(True, description="Whether policy is enabled")

# Dependency injection
async def get_auto_scaling_service() -> AutoScalingService:
    """Get auto scaling service instance."""
    cache_manager = UnifiedCacheManager()
    return AutoScalingService(cache_manager)

@router.get("/status", response_model=Dict[str, Any])
async def get_scaling_status(
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current auto-scaling service status and metrics.
    
    Returns configuration, current metrics, and scaling history.
    """
    try:
        logger.info(
            "Getting auto-scaling status",
            user_id=current_user.get("user_id")
        )
        
        status = await service.get_service_status()
        
        return {
            "success": True,
            "data": status,
            "message": "Auto-scaling status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting auto-scaling status",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=Dict[str, Any])
async def get_current_metrics(
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current resource metrics.
    
    Returns CPU, memory, disk, network, and application metrics.
    """
    try:
        logger.info(
            "Getting current metrics",
            user_id=current_user.get("user_id")
        )
        
        metrics = await service.get_current_metrics()
        
        if metrics:
            metrics_data = {
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "disk_usage": metrics.disk_usage,
                "network_io": metrics.network_io,
                "request_rate": metrics.request_rate,
                "response_time": metrics.response_time,
                "queue_depth": metrics.queue_depth,
                "active_connections": metrics.active_connections,
                "custom_metrics": metrics.custom_metrics
            }
        else:
            metrics_data = None
        
        return {
            "success": True,
            "data": metrics_data,
            "message": "Current metrics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting current metrics",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=Dict[str, Any])
async def get_scaling_history(
    limit: int = Query(50, description="Number of events to return", ge=1, le=1000),
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get auto-scaling event history.
    
    - **limit**: Maximum number of events to return
    """
    try:
        logger.info(
            "Getting scaling history",
            user_id=current_user.get("user_id"),
            limit=limit
        )
        
        history = await service.get_scaling_history(limit)
        
        return {
            "success": True,
            "data": {
                "events": history,
                "total_events": len(history)
            },
            "message": "Scaling history retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting scaling history",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start", response_model=Dict[str, Any])
async def start_monitoring(
    background_tasks: BackgroundTasks,
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Start auto-scaling monitoring.
    
    Begins continuous monitoring and automatic scaling based on configured policies.
    """
    try:
        logger.info(
            "Starting auto-scaling monitoring",
            user_id=current_user.get("user_id")
        )
        
        await service.start_monitoring()
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Auto-scaling monitoring started",
            user_id=current_user.get("user_id")
        )
        
        return {
            "success": True,
            "message": "Auto-scaling monitoring started successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error starting auto-scaling monitoring",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop", response_model=Dict[str, Any])
async def stop_monitoring(
    background_tasks: BackgroundTasks,
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Stop auto-scaling monitoring.
    
    Stops continuous monitoring but maintains current instance count.
    """
    try:
        logger.info(
            "Stopping auto-scaling monitoring",
            user_id=current_user.get("user_id")
        )
        
        await service.stop_monitoring()
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Auto-scaling monitoring stopped",
            user_id=current_user.get("user_id")
        )
        
        return {
            "success": True,
            "message": "Auto-scaling monitoring stopped successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error stopping auto-scaling monitoring",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual-scale", response_model=Dict[str, Any])
async def manual_scaling(
    request: ManualScalingRequest,
    background_tasks: BackgroundTasks,
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Execute manual scaling.
    
    - **target_instances**: Target number of instances
    - **reason**: Reason for manual scaling
    """
    try:
        logger.info(
            "Executing manual scaling",
            user_id=current_user.get("user_id"),
            target_instances=request.target_instances,
            reason=request.reason
        )
        
        result = await service.manual_scale(
            target_instances=request.target_instances,
            reason=request.reason
        )
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Manual scaling executed",
            user_id=current_user.get("user_id"),
            target_instances=request.target_instances,
            result=result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "data": result,
            "message": result.get("message", "Manual scaling completed")
        }
        
    except Exception as e:
        logger.error(
            "Error executing manual scaling",
            user_id=current_user.get("user_id"),
            target_instances=request.target_instances,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/configuration", response_model=Dict[str, Any])
async def update_configuration(
    request: ConfigurationUpdateRequest,
    background_tasks: BackgroundTasks,
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Update auto-scaling configuration.
    
    - **provider**: Cloud provider
    - **target_cpu**: Target CPU utilization percentage
    - **target_memory**: Target memory utilization percentage
    - **target_response_time**: Target response time in milliseconds
    - **scale_out_threshold**: Scale out threshold percentage
    - **scale_in_threshold**: Scale in threshold percentage
    - **cooldown_period**: Cooldown period in seconds
    - **min_instances**: Minimum number of instances
    - **max_instances**: Maximum number of instances
    """
    try:
        logger.info(
            "Updating auto-scaling configuration",
            user_id=current_user.get("user_id")
        )
        
        # Build update dictionary with only provided fields
        update_data = {}
        if request.provider is not None:
            update_data['provider'] = request.provider
        if request.target_cpu is not None:
            update_data['target_cpu'] = request.target_cpu
        if request.target_memory is not None:
            update_data['target_memory'] = request.target_memory
        if request.target_response_time is not None:
            update_data['target_response_time'] = request.target_response_time
        if request.scale_out_threshold is not None:
            update_data['scale_out_threshold'] = request.scale_out_threshold
        if request.scale_in_threshold is not None:
            update_data['scale_in_threshold'] = request.scale_in_threshold
        if request.cooldown_period is not None:
            update_data['cooldown_period'] = request.cooldown_period
        if request.min_instances is not None:
            update_data['min_instances'] = request.min_instances
        if request.max_instances is not None:
            update_data['max_instances'] = request.max_instances
        
        result = await service.update_configuration(update_data)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Auto-scaling configuration updated",
            user_id=current_user.get("user_id"),
            updated_fields=update_data.keys(),
            success=result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "data": result,
            "message": result.get("message", "Configuration updated")
        }
        
    except Exception as e:
        logger.error(
            "Error updating configuration",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers", response_model=Dict[str, Any])
async def get_cloud_providers(
    current_user: Dict = Depends(get_current_user)
):
    """Get supported cloud providers."""
    try:
        providers = [
            {
                "value": provider.value,
                "name": provider.value.upper(),
                "description": _get_provider_description(provider)
            }
            for provider in CloudProvider
        ]
        
        return {
            "success": True,
            "data": providers,
            "message": "Cloud providers retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting cloud providers",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/triggers", response_model=Dict[str, Any])
async def get_scaling_triggers(
    current_user: Dict = Depends(get_current_user)
):
    """Get available scaling trigger types."""
    try:
        triggers = [
            {
                "value": trigger.value,
                "name": trigger.value.replace("_", " ").title(),
                "description": _get_trigger_description(trigger)
            }
            for trigger in ScalingTrigger
        ]
        
        return {
            "success": True,
            "data": triggers,
            "message": "Scaling triggers retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting scaling triggers",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies", response_model=Dict[str, Any])
async def get_scaling_policies(
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """Get current scaling policies."""
    try:
        status = await service.get_service_status()
        policies = status.get("policies", [])
        
        return {
            "success": True,
            "data": {
                "policies": policies,
                "total_policies": len(policies)
            },
            "message": "Scaling policies retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting scaling policies",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies", response_model=Dict[str, Any])
async def create_scaling_policy(
    request: ScalingPolicyRequest,
    background_tasks: BackgroundTasks,
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new scaling policy.
    
    - **name**: Policy name
    - **trigger_type**: Trigger type for scaling
    - **threshold_min**: Minimum threshold for scaling in
    - **threshold_max**: Maximum threshold for scaling out
    - **scale_out_cooldown**: Cooldown period after scaling out
    - **scale_in_cooldown**: Cooldown period after scaling in
    - **min_instances**: Minimum instances for this policy
    - **max_instances**: Maximum instances for this policy
    - **scale_out_step**: Number of instances to add when scaling out
    - **scale_in_step**: Number of instances to remove when scaling in
    - **enabled**: Whether the policy is enabled
    """
    try:
        logger.info(
            "Creating scaling policy",
            user_id=current_user.get("user_id"),
            policy_name=request.name,
            trigger_type=request.trigger_type.value
        )
        
        # This would typically add the policy to the service
        # For now, return a mock response
        result = {
            "success": True,
            "policy_id": f"policy_{datetime.utcnow().timestamp()}",
            "message": f"Scaling policy '{request.name}' created successfully"
        }
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Scaling policy created",
            user_id=current_user.get("user_id"),
            policy_name=request.name,
            policy_id=result.get("policy_id")
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Scaling policy created successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error creating scaling policy",
            user_id=current_user.get("user_id"),
            policy_name=request.name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/policies/{policy_name}", response_model=Dict[str, Any])
async def delete_scaling_policy(
    policy_name: str,
    background_tasks: BackgroundTasks,
    service: AutoScalingService = Depends(get_auto_scaling_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete a scaling policy.
    
    - **policy_name**: Name of the policy to delete
    """
    try:
        logger.info(
            "Deleting scaling policy",
            user_id=current_user.get("user_id"),
            policy_name=policy_name
        )
        
        # This would typically remove the policy from the service
        # For now, return a mock response
        result = {
            "success": True,
            "message": f"Scaling policy '{policy_name}' deleted successfully"
        }
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Scaling policy deleted",
            user_id=current_user.get("user_id"),
            policy_name=policy_name
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Scaling policy deleted successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error deleting scaling policy",
            user_id=current_user.get("user_id"),
            policy_name=policy_name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

def _get_provider_description(provider: CloudProvider) -> str:
    """Get description for cloud provider."""
    descriptions = {
        CloudProvider.AWS: "Amazon Web Services - EC2 Auto Scaling Groups",
        CloudProvider.GCP: "Google Cloud Platform - Compute Engine Managed Instance Groups",
        CloudProvider.AZURE: "Microsoft Azure - Virtual Machine Scale Sets",
        CloudProvider.KUBERNETES: "Kubernetes - Horizontal Pod Autoscaler",
        CloudProvider.DOCKER: "Docker - Docker Swarm scaling"
    }
    return descriptions.get(provider, "Unknown cloud provider")

def _get_trigger_description(trigger: ScalingTrigger) -> str:
    """Get description for scaling trigger."""
    descriptions = {
        ScalingTrigger.CPU_THRESHOLD: "Scale based on CPU utilization percentage",
        ScalingTrigger.MEMORY_THRESHOLD: "Scale based on memory utilization percentage",
        ScalingTrigger.RESPONSE_TIME: "Scale based on application response time",
        ScalingTrigger.REQUEST_RATE: "Scale based on incoming request rate",
        ScalingTrigger.QUEUE_DEPTH: "Scale based on message queue depth",
        ScalingTrigger.CUSTOM_METRIC: "Scale based on custom application metrics"
    }
    return descriptions.get(trigger, "Unknown scaling trigger")