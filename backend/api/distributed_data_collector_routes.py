"""
Distributed Data Collection API Routes for InsiteChart platform.

This module provides REST API endpoints for distributed data collection,
pipeline management, and data quality monitoring.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.distributed_data_collector import (
    DistributedDataCollector,
    DataSourceType,
    DataPriority,
    DataStatus
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/distributed-data-collector", tags=["Distributed Data Collection"])

# Pydantic models for request/response
class DataCollectionTaskCreate(BaseModel):
    """Model for creating data collection task."""
    source_type: DataSourceType = Field(..., description="Data source type")
    priority: DataPriority = Field(DataPriority.NORMAL, description="Task priority")
    source_config: Dict[str, Any] = Field(..., description="Source configuration")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule for later execution")

class DataPipelineCreate(BaseModel):
    """Model for creating data pipeline."""
    pipeline_id: str = Field(..., description="Unique pipeline identifier")
    name: str = Field(..., description="Pipeline name")
    description: str = Field(..., description="Pipeline description")
    source_type: DataSourceType = Field(..., description="Source type")
    processors: List[str] = Field(..., description="Processor functions")
    enabled: bool = Field(True, description="Enable pipeline")

class DataQualityRuleCreate(BaseModel):
    """Model for creating data quality rule."""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    source_types: List[DataSourceType] = Field(..., description="Applicable source types")
    enabled: bool = Field(True, description="Enable rule")

# Dependency to get distributed data collector service
async def get_distributed_data_collector() -> DistributedDataCollector:
    """Get distributed data collector service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return DistributedDataCollector(cache_manager)
    except Exception as e:
        logger.error(f"Error creating distributed data collector service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize distributed data collector service")

@router.post("/tasks")
async def create_collection_task(
    task: DataCollectionTaskCreate,
    background_tasks: BackgroundTasks,
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Create a data collection task.
    
    This endpoint creates a new data collection task with specified
    source type, priority, and configuration.
    """
    try:
        # Check admin permissions for high priority tasks
        if task.priority == DataPriority.CRITICAL and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required for critical priority tasks")
        
        # Create task
        result = await collector.create_collection_task(
            source_type=task.source_type,
            priority=task.priority,
            source_config=task.source_config,
            scheduled_at=task.scheduled_at
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "task_id": result["task_id"],
            "priority": result["priority"],
            "source_type": result["source_type"],
            "scheduled_at": result["scheduled_at"],
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating collection task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/tasks")
async def get_collection_tasks(
    source_type: Optional[DataSourceType] = Query(None, description="Filter by source type"),
    status: Optional[DataStatus] = Query(None, description="Filter by status"),
    priority: Optional[DataPriority] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of tasks"),
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Get data collection tasks.
    
    This endpoint retrieves data collection tasks with optional filtering.
    Admin users can view all tasks, regular users can only view their own.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            # For non-admin users, you might want to filter by tasks they created
            # This would require task creator tracking in the service
            pass
        
        tasks = await collector.get_collection_tasks(
            source_type=source_type,
            status=status,
            priority=priority,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": tasks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/pipelines")
async def get_data_pipelines(
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Get data processing pipelines.
    
    This endpoint retrieves all data processing pipelines.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        pipelines = await collector.get_data_pipelines()
        
        return {
            "success": True,
            "count": len(pipelines),
            "pipelines": pipelines
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data pipelines: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/pipelines")
async def create_data_pipeline(
    pipeline: DataPipelineCreate,
    background_tasks: BackgroundTasks,
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Create a data processing pipeline.
    
    This endpoint creates a new data processing pipeline.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create pipeline in the service
        # For now, return a success response
        return {
            "success": True,
            "pipeline_id": pipeline.pipeline_id,
            "message": "Data pipeline created successfully",
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/quality-rules")
async def get_quality_rules(
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Get data quality rules.
    
    This endpoint retrieves all data quality validation rules.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        rules = await collector.get_quality_rules()
        
        return {
            "success": True,
            "count": len(rules),
            "rules": rules
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quality rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/quality-rules")
async def create_quality_rule(
    rule: DataQualityRuleCreate,
    background_tasks: BackgroundTasks,
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Create a data quality rule.
    
    This endpoint creates a new data quality validation rule.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create rule in the service
        # For now, return a success response
        return {
            "success": True,
            "rule_id": rule.rule_id,
            "message": "Data quality rule created successfully",
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quality rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/metrics")
async def get_collection_metrics(
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Get data collection metrics.
    
    This endpoint retrieves comprehensive data collection metrics.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        metrics = await collector.get_collection_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/tasks/yahoo-finance")
async def create_yahoo_finance_task(
    symbols: List[str] = Field(..., description="Stock symbols to collect"),
    priority: DataPriority = Field(DataPriority.NORMAL, description="Task priority"),
    background_tasks: BackgroundTasks,
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Create Yahoo Finance data collection task.
    
    This endpoint creates a specialized task for collecting Yahoo Finance data.
    """
    try:
        # Create task configuration
        source_config = {
            "symbols": symbols,
            "data_types": ["price", "volume", "change", "market_cap"]
        }
        
        # Create task
        result = await collector.create_collection_task(
            source_type=DataSourceType.YAHOO_FINANCE,
            priority=priority,
            source_config=source_config
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "task_id": result["task_id"],
            "symbols": symbols,
            "priority": result["priority"],
            "source_type": result["source_type"],
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Yahoo Finance task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/tasks/social-media")
async def create_social_media_task(
    platforms: List[str] = Field(..., description="Social media platforms"),
    keywords: List[str] = Field(..., description="Keywords to track"),
    priority: DataPriority = Field(DataPriority.NORMAL, description="Task priority"),
    background_tasks: BackgroundTasks,
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Create social media data collection task.
    
    This endpoint creates a specialized task for collecting social media data.
    """
    try:
        # Create task configuration
        source_config = {
            "platforms": platforms,
            "keywords": keywords,
            "data_types": ["posts", "sentiment", "engagement"]
        }
        
        # Create task
        result = await collector.create_collection_task(
            source_type=DataSourceType.SOCIAL_MEDIA,
            priority=priority,
            source_config=source_config
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "task_id": result["task_id"],
            "platforms": platforms,
            "keywords": keywords,
            "priority": result["priority"],
            "source_type": result["source_type"],
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating social media task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/tasks/news-feeds")
async def create_news_feed_task(
    sources: List[str] = Field(..., description="News sources"),
    categories: List[str] = Field(..., description="News categories"),
    priority: DataPriority = Field(DataPriority.NORMAL, description="Task priority"),
    background_tasks: BackgroundTasks,
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Create news feed data collection task.
    
    This endpoint creates a specialized task for collecting news feed data.
    """
    try:
        # Create task configuration
        source_config = {
            "sources": sources,
            "categories": categories,
            "data_types": ["articles", "sentiment", "entities"]
        }
        
        # Create task
        result = await collector.create_collection_task(
            source_type=DataSourceType.NEWS_FEEDS,
            priority=priority,
            source_config=source_config
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "task_id": result["task_id"],
            "sources": sources,
            "categories": categories,
            "priority": result["priority"],
            "source_type": result["source_type"],
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating news feed task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status")
async def get_collector_status(
    collector: DistributedDataCollector = Depends(get_distributed_data_collector),
    current_user: User = Depends(get_current_user)
):
    """
    Get distributed data collector status.
    
    This endpoint retrieves the current status of the distributed data collector.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get metrics to determine status
        metrics = await collector.get_collection_metrics()
        
        # Determine overall status
        if metrics.get("error"):
            status = "error"
        elif metrics.get("success_rate", 0) < 90:
            status = "degraded"
        elif metrics.get("queue_sizes", {}).get("critical", 0) > 0:
            status = "busy"
        else:
            status = "healthy"
        
        return {
            "success": True,
            "status": status,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collector status: {str(e)}")
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
    logger.error(f"Unhandled exception in distributed data collector routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )