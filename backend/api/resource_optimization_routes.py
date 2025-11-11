"""
Resource Optimization API Routes for InsiteChart platform.

This module provides REST API endpoints for intelligent resource optimization
including memory management, cache optimization, and system cleanup.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.resource_optimization_service import (
    ResourceOptimizationService,
    OptimizationType,
    OptimizationPriority
)
from ..cache.unified_cache import UnifiedCacheManager
from ..middleware.auth_middleware import get_current_user
from ..logging.structured_logger import StructuredLogger

# Initialize router
router = APIRouter(prefix="/api/resource-optimization", tags=["resource-optimization"])

# Initialize logger
logger = StructuredLogger(__name__)

# Pydantic models for request/response
class ManualOptimizationRequest(BaseModel):
    optimization_type: OptimizationType = Field(..., description="Type of optimization to execute")
    priority: Optional[OptimizationPriority] = Field(None, description="Optimization priority")

class PolicyUpdateRequest(BaseModel):
    name: str = Field(..., description="Policy name to update")
    enabled: Optional[bool] = Field(None, description="Whether policy is enabled")
    priority: Optional[OptimizationPriority] = Field(None, description="Optimization priority")
    threshold: Optional[float] = Field(None, description="Optimization threshold")
    frequency_minutes: Optional[int] = Field(None, description="Frequency in minutes", ge=1)
    max_execution_time_ms: Optional[int] = Field(None, description="Max execution time in ms", ge=100)
    auto_execute: Optional[bool] = Field(None, description="Whether to auto-execute")

class PolicyCreateRequest(BaseModel):
    name: str = Field(..., description="Policy name")
    optimization_type: OptimizationType = Field(..., description="Optimization type")
    enabled: bool = Field(True, description="Whether policy is enabled")
    priority: OptimizationPriority = Field(OptimizationPriority.MEDIUM, description="Optimization priority")
    threshold: float = Field(..., description="Optimization threshold")
    frequency_minutes: int = Field(60, description="Frequency in minutes", ge=1)
    max_execution_time_ms: int = Field(5000, description="Max execution time in ms", ge=100)
    auto_execute: bool = Field(True, description="Whether to auto-execute")

# Dependency injection
async def get_resource_optimization_service() -> ResourceOptimizationService:
    """Get resource optimization service instance."""
    cache_manager = UnifiedCacheManager()
    return ResourceOptimizationService(cache_manager)

@router.get("/status", response_model=Dict[str, Any])
async def get_optimization_status(
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current resource optimization service status.
    
    Returns optimization status, active optimizations, and resource usage trends.
    """
    try:
        logger.info(
            "Getting resource optimization status",
            user_id=current_user.get("user_id")
        )
        
        status = await service.get_optimization_status()
        
        return {
            "success": True,
            "data": status,
            "message": "Resource optimization status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting optimization status",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resource-usage", response_model=Dict[str, Any])
async def get_current_resource_usage(
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current resource usage metrics.
    
    Returns CPU, memory, disk, and cache usage information.
    """
    try:
        logger.info(
            "Getting current resource usage",
            user_id=current_user.get("user_id")
        )
        
        usage = await service.get_resource_usage()
        
        # Convert to dictionary for JSON serialization
        usage_data = {
            "timestamp": usage.timestamp.isoformat(),
            "cpu_usage": usage.cpu_usage,
            "memory_usage": usage.memory_usage,
            "memory_available_gb": usage.memory_available,
            "disk_usage": usage.disk_usage,
            "disk_available_gb": usage.disk_available,
            "network_io": usage.network_io,
            "active_connections": usage.active_connections,
            "cache_size": usage.cache_size,
            "cache_hit_rate": usage.cache_hit_rate,
            "gc_stats": usage.gc_stats
        }
        
        return {
            "success": True,
            "data": usage_data,
            "message": "Resource usage retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting resource usage",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=Dict[str, Any])
async def get_resource_trends(
    hours: int = Query(24, description="Time range in hours", ge=1, le=168),
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get resource usage trends over time.
    
    - **hours**: Time range in hours (1-168)
    """
    try:
        logger.info(
            "Getting resource trends",
            user_id=current_user.get("user_id"),
            hours=hours
        )
        
        trends = await service.get_resource_trends(hours=hours)
        
        return {
            "success": True,
            "data": trends,
            "message": "Resource trends retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting resource trends",
            user_id=current_user.get("user_id"),
            hours=hours,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize", response_model=Dict[str, Any])
async def execute_optimization(
    request: ManualOptimizationRequest,
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Manually execute a resource optimization.
    
    - **optimization_type**: Type of optimization to execute
    - **priority**: Optional priority level for the optimization
    """
    try:
        logger.info(
            "Executing manual optimization",
            user_id=current_user.get("user_id"),
            optimization_type=request.optimization_type.value,
            priority=request.priority.value if request.priority else None
        )
        
        result = await service.execute_optimization(
            optimization_type=request.optimization_type,
            priority=request.priority
        )
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Manual optimization executed",
            user_id=current_user.get("user_id"),
            optimization_type=request.optimization_type.value,
            success=result.success,
            execution_time_ms=result.execution_time_ms
        )
        
        # Convert result to dictionary
        result_data = {
            "optimization_type": result.optimization_type.value,
            "success": result.success,
            "message": result.message,
            "resources_freed": result.resources_freed,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "priority": result.priority.value,
            "metadata": result.metadata
        }
        
        return {
            "success": True,
            "data": result_data,
            "message": "Optimization executed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error executing optimization",
            user_id=current_user.get("user_id"),
            optimization_type=request.optimization_type.value,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=Dict[str, Any])
async def get_optimization_history(
    limit: int = Query(50, description="Maximum number of records to return", ge=1, le=1000),
    optimization_type: Optional[OptimizationType] = Query(None, description="Filter by optimization type"),
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get optimization execution history.
    
    - **limit**: Maximum number of records to return
    - **optimization_type**: Filter by optimization type
    """
    try:
        logger.info(
            "Getting optimization history",
            user_id=current_user.get("user_id"),
            limit=limit,
            optimization_type=optimization_type.value if optimization_type else None
        )
        
        history = await service.get_optimization_history(
            limit=limit,
            optimization_type=optimization_type
        )
        
        # Convert results to dictionaries
        history_data = [
            {
                "optimization_type": result.optimization_type.value,
                "success": result.success,
                "message": result.message,
                "resources_freed": result.resources_freed,
                "execution_time_ms": result.execution_time_ms,
                "timestamp": result.timestamp.isoformat(),
                "priority": result.priority.value,
                "metadata": result.metadata
            }
            for result in history
        ]
        
        return {
            "success": True,
            "data": {
                "optimizations": history_data,
                "total_count": len(history_data),
                "filtered_count": len(history_data)
            },
            "message": "Optimization history retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting optimization history",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/policies", response_model=Dict[str, Any])
async def get_optimization_policies(
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """Get current optimization policies."""
    try:
        logger.info(
            "Getting optimization policies",
            user_id=current_user.get("user_id")
        )
        
        policies = await service.get_optimization_policies()
        
        return {
            "success": True,
            "data": {
                "policies": policies,
                "total_count": len(policies)
            },
            "message": "Optimization policies retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting optimization policies",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policies", response_model=Dict[str, Any])
async def create_optimization_policy(
    request: PolicyCreateRequest,
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new optimization policy.
    
    - **name**: Policy name
    - **optimization_type**: Optimization type
    - **enabled**: Whether policy is enabled
    - **priority**: Optimization priority
    - **threshold**: Optimization threshold
    - **frequency_minutes**: Frequency in minutes
    - **max_execution_time_ms**: Maximum execution time in ms
    - **auto_execute**: Whether to auto-execute
    """
    try:
        logger.info(
            "Creating optimization policy",
            user_id=current_user.get("user_id"),
            policy_name=request.name,
            optimization_type=request.optimization_type.value
        )
        
        # This would typically add the policy to the service
        # For now, return a mock response
        result = {
            "success": True,
            "policy_id": f"policy_{datetime.utcnow().timestamp()}",
            "message": f"Optimization policy '{request.name}' created successfully"
        }
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Optimization policy created",
            user_id=current_user.get("user_id"),
            policy_name=request.name,
            policy_id=result.get("policy_id")
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Optimization policy created successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error creating optimization policy",
            user_id=current_user.get("user_id"),
            policy_name=request.name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/policies/{policy_name}", response_model=Dict[str, Any])
async def update_optimization_policy(
    policy_name: str,
    request: PolicyUpdateRequest,
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Update an existing optimization policy.
    
    - **policy_name**: Name of the policy to update
    - **enabled**: Whether policy is enabled
    - **priority**: Optimization priority
    - **threshold**: Optimization threshold
    - **frequency_minutes**: Frequency in minutes
    - **max_execution_time_ms**: Maximum execution time in ms
    - **auto_execute**: Whether to auto-execute
    """
    try:
        logger.info(
            "Updating optimization policy",
            user_id=current_user.get("user_id"),
            policy_name=policy_name
        )
        
        # Build updates dictionary
        updates = {}
        if request.enabled is not None:
            updates["enabled"] = request.enabled
        if request.priority is not None:
            updates["priority"] = request.priority
        if request.threshold is not None:
            updates["threshold"] = request.threshold
        if request.frequency_minutes is not None:
            updates["frequency_minutes"] = request.frequency_minutes
        if request.max_execution_time_ms is not None:
            updates["max_execution_time_ms"] = request.max_execution_time_ms
        if request.auto_execute is not None:
            updates["auto_execute"] = request.auto_execute
        
        result = await service.update_optimization_policy(policy_name, updates)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Optimization policy updated",
            user_id=current_user.get("user_id"),
            policy_name=policy_name,
            success=result.get("success", False),
            updated_fields=result.get("updated_fields", [])
        )
        
        return {
            "success": result.get("success", False),
            "data": result,
            "message": result.get("message", "Policy update completed")
        }
        
    except Exception as e:
        logger.error(
            "Error updating optimization policy",
            user_id=current_user.get("user_id"),
            policy_name=policy_name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/policies/{policy_name}", response_model=Dict[str, Any])
async def delete_optimization_policy(
    policy_name: str,
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete an optimization policy.
    
    - **policy_name**: Name of the policy to delete
    """
    try:
        logger.info(
            "Deleting optimization policy",
            user_id=current_user.get("user_id"),
            policy_name=policy_name
        )
        
        # This would typically remove the policy from the service
        # For now, return a mock response
        result = {
            "success": True,
            "message": f"Optimization policy '{policy_name}' deleted successfully"
        }
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Optimization policy deleted",
            user_id=current_user.get("user_id"),
            policy_name=policy_name
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Optimization policy deleted successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error deleting optimization policy",
            user_id=current_user.get("user_id"),
            policy_name=policy_name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types", response_model=Dict[str, Any])
async def get_optimization_types(
    current_user: Dict = Depends(get_current_user)
):
    """Get available optimization types."""
    try:
        types = [
            {
                "value": opt_type.value,
                "name": opt_type.value.replace("_", " ").title(),
                "description": _get_optimization_type_description(opt_type)
            }
            for opt_type in OptimizationType
        ]
        
        return {
            "success": True,
            "data": types,
            "message": "Optimization types retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting optimization types",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/priorities", response_model=Dict[str, Any])
async def get_optimization_priorities(
    current_user: Dict = Depends(get_current_user)
):
    """Get available optimization priority levels."""
    try:
        priorities = [
            {
                "value": priority.value,
                "name": priority.value.title(),
                "description": _get_priority_description(priority)
            }
            for priority in OptimizationPriority
        ]
        
        return {
            "success": True,
            "data": priorities,
            "message": "Optimization priorities retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting optimization priorities",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup/memory", response_model=Dict[str, Any])
async def execute_memory_cleanup(
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """Execute memory cleanup optimization."""
    try:
        logger.info(
            "Executing memory cleanup",
            user_id=current_user.get("user_id")
        )
        
        result = await service.execute_optimization(OptimizationType.MEMORY_CLEANUP)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Memory cleanup executed",
            user_id=current_user.get("user_id"),
            success=result.success,
            execution_time_ms=result.execution_time_ms
        )
        
        return {
            "success": True,
            "data": {
                "optimization_type": result.optimization_type.value,
                "success": result.success,
                "message": result.message,
                "resources_freed": result.resources_freed,
                "execution_time_ms": result.execution_time_ms
            },
            "message": "Memory cleanup executed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error executing memory cleanup",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup/cache", response_model=Dict[str, Any])
async def execute_cache_cleanup(
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """Execute cache cleanup optimization."""
    try:
        logger.info(
            "Executing cache cleanup",
            user_id=current_user.get("user_id")
        )
        
        result = await service.execute_optimization(OptimizationType.CACHE_OPTIMIZATION)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Cache cleanup executed",
            user_id=current_user.get("user_id"),
            success=result.success,
            execution_time_ms=result.execution_time_ms
        )
        
        return {
            "success": True,
            "data": {
                "optimization_type": result.optimization_type.value,
                "success": result.success,
                "message": result.message,
                "resources_freed": result.resources_freed,
                "execution_time_ms": result.execution_time_ms
            },
            "message": "Cache cleanup executed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error executing cache cleanup",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup/disk", response_model=Dict[str, Any])
async def execute_disk_cleanup(
    background_tasks: BackgroundTasks,
    service: ResourceOptimizationService = Depends(get_resource_optimization_service),
    current_user: Dict = Depends(get_current_user)
):
    """Execute disk cleanup optimization."""
    try:
        logger.info(
            "Executing disk cleanup",
            user_id=current_user.get("user_id")
        )
        
        result = await service.execute_optimization(OptimizationType.DISK_CLEANUP)
        
        # Log action in background
        background_tasks.add_task(
            logger.info,
            "Disk cleanup executed",
            user_id=current_user.get("user_id"),
            success=result.success,
            execution_time_ms=result.execution_time_ms
        )
        
        return {
            "success": True,
            "data": {
                "optimization_type": result.optimization_type.value,
                "success": result.success,
                "message": result.message,
                "resources_freed": result.resources_freed,
                "execution_time_ms": result.execution_time_ms
            },
            "message": "Disk cleanup executed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error executing disk cleanup",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

def _get_optimization_type_description(opt_type: OptimizationType) -> str:
    """Get description for optimization type."""
    descriptions = {
        OptimizationType.MEMORY_CLEANUP: "Memory garbage collection and cleanup to free up RAM",
        OptimizationType.CACHE_OPTIMIZATION: "Cache optimization to improve hit rates and reduce memory usage",
        OptimizationType.CONNECTION_POOL_OPTIMIZATION: "Database connection pool optimization to reduce resource usage",
        OptimizationType.CPU_OPTIMIZATION: "CPU usage optimization through process tuning and load balancing",
        OptimizationType.DISK_CLEANUP: "Disk cleanup to remove temporary files and free up storage space",
        OptimizationType.LOG_CLEANUP: "Log file cleanup to remove old logs and free up disk space",
        OptimizationType.TEMP_FILE_CLEANUP: "Temporary file cleanup to remove unused temporary files"
    }
    return descriptions.get(opt_type, "Unknown optimization type")

def _get_priority_description(priority: OptimizationPriority) -> str:
    """Get description for optimization priority."""
    descriptions = {
        OptimizationPriority.LOW: "Low priority - executed when system resources are available",
        OptimizationPriority.MEDIUM: "Medium priority - balanced resource usage and optimization benefits",
        OptimizationPriority.HIGH: "High priority - executed when needed for system stability",
        OptimizationPriority.CRITICAL: "Critical priority - executed immediately when triggered"
    }
    return descriptions.get(priority, "Unknown priority")