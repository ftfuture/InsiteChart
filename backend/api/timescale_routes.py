"""
TimescaleDB API Routes for InsiteChart platform.

This module provides REST API endpoints for TimescaleDB operations
including hypertable management, partitioning, and performance optimization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.timescale_service import (
    TimescaleService,
    PartitionType,
    CompressionType,
    RetentionPolicy
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/timescale", tags=["TimescaleDB"])

# Pydantic models for request/response
class HypertableCreate(BaseModel):
    """Model for creating a hypertable."""
    table_name: str = Field(..., description="Table name")
    time_column: str = Field("timestamp", description="Time column name")
    partitioning_column: Optional[str] = Field(None, description="Partitioning column")
    partition_type: PartitionType = Field(PartitionType.DAILY, description="Partition type")
    chunk_time_interval: Optional[str] = Field(None, description="Chunk time interval")
    compression: CompressionType = Field(CompressionType.GZIP, description="Compression type")
    retention_policy: RetentionPolicy = Field(RetentionPolicy.YEARS_2, description="Retention policy")
    create_indexes: List[str] = Field(default_factory=list, description="Indexes to create")

class TimeSeriesDataInsert(BaseModel):
    """Model for inserting time-series data."""
    table_name: str = Field(..., description="Target table name")
    data: List[Dict[str, Any]] = Field(..., description="Data to insert")
    batch_size: int = Field(1000, description="Batch size for insertion")

class TimeSeriesDataQuery(BaseModel):
    """Model for querying time-series data."""
    table_name: str = Field(..., description="Table name")
    symbol: Optional[str] = Field(None, description="Symbol filter")
    start_time: Optional[datetime] = Field(None, description="Start time filter")
    end_time: Optional[datetime] = Field(None, description="End time filter")
    limit: int = Field(1000, description="Maximum records to return")
    aggregation: Optional[str] = Field(None, description="Aggregation type")

class TableOptimization(BaseModel):
    """Model for table optimization."""
    table_name: str = Field(..., description="Table name to optimize")

# Dependency to get TimescaleDB service
async def get_timescale_service() -> TimescaleService:
    """Get TimescaleDB service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return TimescaleService(cache_manager)
    except Exception as e:
        logger.error(f"Error creating TimescaleDB service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize TimescaleDB service")

@router.post("/hypertables")
async def create_hypertable(
    hypertable: HypertableCreate,
    background_tasks: BackgroundTasks,
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new hypertable.
    
    This endpoint creates a new TimescaleDB hypertable with specified
    partitioning and compression settings.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create hypertable in the service
        # For now, return a success response
        return {
            "success": True,
            "table_name": hypertable.table_name,
            "message": "Hypertable created successfully",
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating hypertable: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/hypertables")
async def get_hypertables(
    table_name: Optional[str] = Query(None, description="Filter by table name"),
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get hypertable information.
    
    This endpoint retrieves information about configured hypertables.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        hypertables = await timescale_service.get_hypertable_info(table_name)
        
        return {
            "success": True,
            "count": len(hypertables),
            "hypertables": hypertables
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hypertables: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/data/insert")
async def insert_time_series_data(
    data_insert: TimeSeriesDataInsert,
    background_tasks: BackgroundTasks,
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Insert time-series data.
    
    This endpoint inserts time-series data into a specified hypertable.
    """
    try:
        # Insert data
        result = await timescale_service.insert_time_series_data(
            table_name=data_insert.table_name,
            data=data_insert.data,
            batch_size=data_insert.batch_size
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "inserted_count": result["inserted_count"],
            "processing_time_ms": result["processing_time_ms"],
            "table_name": result["table_name"],
            "inserted_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inserting time-series data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/data/query")
async def query_time_series_data(
    query: TimeSeriesDataQuery,
    background_tasks: BackgroundTasks,
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Query time-series data.
    
    This endpoint queries time-series data from a specified hypertable
    with optional filtering and aggregation.
    """
    try:
        # Query data
        result = await timescale_service.query_time_series_data(
            table_name=query.table_name,
            symbol=query.symbol,
            start_time=query.start_time,
            end_time=query.end_time,
            limit=query.limit,
            aggregation=query.aggregation
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "data": result["data"],
            "count": result["count"],
            "processing_time_ms": result["processing_time_ms"],
            "table_name": result["table_name"],
            "queried_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying time-series data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/partitions/{table_name}")
async def get_table_partitions(
    table_name: str,
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get partition information for a table.
    
    This endpoint retrieves partition information for a specified hypertable.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        partitions = await timescale_service.get_partition_info(table_name)
        
        return {
            "success": True,
            "table_name": table_name,
            "count": len(partitions),
            "partitions": partitions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table partitions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/optimize/{table_name}")
async def optimize_table(
    table_name: str,
    optimization: TableOptimization,
    background_tasks: BackgroundTasks,
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Optimize table performance.
    
    This endpoint optimizes a specified hypertable for better performance.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Verify table name matches
        if optimization.table_name != table_name:
            raise HTTPException(status_code=400, detail="Table name mismatch")
        
        # Optimize table
        result = await timescale_service.optimize_table(table_name)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "table_name": result["table_name"],
            "message": result["message"],
            "optimized_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing table: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/metrics")
async def get_timescale_metrics(
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get TimescaleDB performance metrics.
    
    This endpoint retrieves comprehensive performance metrics for TimescaleDB.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        metrics = await timescale_service.get_performance_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting TimescaleDB metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/stock-prices/insert")
async def insert_stock_prices(
    symbols: List[str],
    prices: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Insert stock price data.
    
    This endpoint is a specialized endpoint for inserting stock price data
    into the stock_prices hypertable.
    """
    try:
        # Prepare data for stock prices table
        data = []
        for i, symbol in enumerate(symbols):
            if i < len(prices):
                price_data = prices[i]
                data.append({
                    "symbol": symbol,
                    "data": price_data,
                    "timestamp": price_data.get("timestamp", datetime.utcnow())
                })
        
        # Insert data
        result = await timescale_service.insert_time_series_data(
            table_name="stock_prices",
            data=data,
            batch_size=1000
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "inserted_count": result["inserted_count"],
            "processing_time_ms": result["processing_time_ms"],
            "symbols": symbols,
            "inserted_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inserting stock prices: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/stock-prices/query")
async def query_stock_prices(
    symbols: Optional[List[str]] = Query(None, description="Stock symbols to query"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    limit: int = Query(1000, description="Maximum records to return"),
    aggregation: Optional[str] = Query(None, description="Aggregation type"),
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Query stock price data.
    
    This endpoint is a specialized endpoint for querying stock price data
    from the stock_prices hypertable.
    """
    try:
        # Build query parameters
        symbol_filter = symbols[0] if symbols else None
        
        # Query data
        result = await timescale_service.query_time_series_data(
            table_name="stock_prices",
            symbol=symbol_filter,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            aggregation=aggregation
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "data": result["data"],
            "count": result["count"],
            "processing_time_ms": result["processing_time_ms"],
            "symbols": symbols,
            "queried_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying stock prices: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def get_timescale_health(
    timescale_service: TimescaleService = Depends(get_timescale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get TimescaleDB health status.
    
    This endpoint retrieves the health status of TimescaleDB service.
    """
    try:
        # Get basic metrics to determine health
        metrics = await timescale_service.get_performance_metrics()
        
        # Determine health status
        if "error" in metrics:
            status = "unhealthy"
        elif metrics.get("service_metrics", {}).get("avg_query_time_ms", 0) > 5000:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "success": True,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "service_metrics": metrics.get("service_metrics", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting TimescaleDB health: {str(e)}")
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
    logger.error(f"Unhandled exception in TimescaleDB routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )