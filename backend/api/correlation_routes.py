"""
Correlation Analysis API Routes for InsiteChart platform.

This module provides REST API endpoints for correlation analysis
and visualization functionality.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.correlation_analysis_service import (
    CorrelationAnalysisService,
    CorrelationMethod,
    VisualizationType
)
from ..cache.unified_cache import UnifiedCacheManager
from ..middleware.auth_middleware import get_current_user
from ..logging.structured_logger import StructuredLogger

# Initialize router
router = APIRouter(prefix="/api/correlation", tags=["correlation"])

# Initialize logger
logger = StructuredLogger(__name__)

# Pydantic models for request/response
class CorrelationRequest(BaseModel):
    symbol1: str = Field(..., description="First symbol")
    symbol2: str = Field(..., description="Second symbol")
    method: CorrelationMethod = Field(CorrelationMethod.PEARSON, description="Correlation method")
    period_days: int = Field(252, description="Analysis period in days", ge=30, le=1000)
    min_periods: int = Field(30, description="Minimum periods required", ge=10)

class CorrelationMatrixRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols", min_items=2, max_items=50)
    method: CorrelationMethod = Field(CorrelationMethod.PEARSON, description="Correlation method")
    period_days: int = Field(252, description="Analysis period in days", ge=30, le=1000)
    min_periods: int = Field(30, description="Minimum periods required", ge=10)

class VisualizationRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols", min_items=2, max_items=50)
    visualization_type: VisualizationType = Field(VisualizationType.HEATMAP, description="Visualization type")
    method: CorrelationMethod = Field(CorrelationMethod.PEARSON, description="Correlation method")
    period_days: int = Field(252, description="Analysis period in days", ge=30, le=1000)
    config: Optional[Dict[str, Any]] = Field(None, description="Visualization configuration")

class SectorCorrelationRequest(BaseModel):
    sector_symbols: Dict[str, List[str]] = Field(..., description="Dictionary of sectors and their symbols")
    method: CorrelationMethod = Field(CorrelationMethod.PEARSON, description="Correlation method")
    period_days: int = Field(252, description="Analysis period in days", ge=30, le=1000)

# Dependency injection
async def get_correlation_service() -> CorrelationAnalysisService:
    """Get correlation analysis service instance."""
    cache_manager = UnifiedCacheManager()
    return CorrelationAnalysisService(cache_manager)

@router.post("/calculate", response_model=Dict[str, Any])
async def calculate_correlation(
    request: CorrelationRequest,
    background_tasks: BackgroundTasks,
    service: CorrelationAnalysisService = Depends(get_correlation_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Calculate correlation between two financial instruments.
    
    - **symbol1**: First symbol (e.g., "AAPL")
    - **symbol2**: Second symbol (e.g., "MSFT")
    - **method**: Correlation calculation method (pearson, spearman, kendall, dynamic_rolling)
    - **period_days**: Number of days of historical data to analyze
    - **min_periods**: Minimum number of data points required
    """
    try:
        logger.info(
            "Calculating correlation",
            user_id=current_user.get("user_id"),
            symbol1=request.symbol1,
            symbol2=request.symbol2,
            method=request.method.value
        )
        
        # Calculate correlation
        result = await service.calculate_correlation(
            symbol1=request.symbol1,
            symbol2=request.symbol2,
            method=request.method,
            period_days=request.period_days,
            min_periods=request.min_periods
        )
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "Correlation calculation completed",
            user_id=current_user.get("user_id"),
            symbol1=request.symbol1,
            symbol2=request.symbol2,
            correlation=result.correlation,
            significance=result.significance
        )
        
        return {
            "success": True,
            "data": result.__dict__,
            "message": "Correlation calculated successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error calculating correlation",
            user_id=current_user.get("user_id"),
            symbol1=request.symbol1,
            symbol2=request.symbol2,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/matrix", response_model=Dict[str, Any])
async def calculate_correlation_matrix(
    request: CorrelationMatrixRequest,
    background_tasks: BackgroundTasks,
    service: CorrelationAnalysisService = Depends(get_correlation_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Calculate correlation matrix for multiple symbols.
    
    - **symbols**: List of symbols to analyze
    - **method**: Correlation calculation method
    - **period_days**: Number of days of historical data to analyze
    - **min_periods**: Minimum number of data points required
    """
    try:
        logger.info(
            "Calculating correlation matrix",
            user_id=current_user.get("user_id"),
            symbols=request.symbols,
            method=request.method.value,
            symbol_count=len(request.symbols)
        )
        
        # Calculate correlation matrix
        result = await service.calculate_correlation_matrix(
            symbols=request.symbols,
            method=request.method,
            period_days=request.period_days,
            min_periods=request.min_periods
        )
        
        # Convert numpy arrays to lists for JSON serialization
        response_data = {
            "symbols": result.symbols,
            "matrix": result.matrix.tolist(),
            "method": result.method,
            "data_period": result.data_period,
            "sample_size": result.sample_size,
            "is_significant": result.is_significant.tolist(),
            "p_values": result.p_values.tolist()
        }
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "Correlation matrix calculation completed",
            user_id=current_user.get("user_id"),
            symbol_count=len(request.symbols),
            method=request.method.value
        )
        
        return {
            "success": True,
            "data": response_data,
            "message": "Correlation matrix calculated successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error calculating correlation matrix",
            user_id=current_user.get("user_id"),
            symbols=request.symbols,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualize", response_model=Dict[str, Any])
async def create_correlation_visualization(
    request: VisualizationRequest,
    background_tasks: BackgroundTasks,
    service: CorrelationAnalysisService = Depends(get_correlation_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create correlation visualization.
    
    - **symbols**: List of symbols to visualize
    - **visualization_type**: Type of visualization (heatmap, network, scatter_matrix, time_series, dendrogram)
    - **method**: Correlation calculation method
    - **period_days**: Number of days of historical data to analyze
    - **config**: Optional visualization configuration
    """
    try:
        logger.info(
            "Creating correlation visualization",
            user_id=current_user.get("user_id"),
            symbols=request.symbols,
            visualization_type=request.visualization_type.value,
            method=request.method.value
        )
        
        # Create visualization
        result = await service.create_correlation_visualization(
            symbols=request.symbols,
            visualization_type=request.visualization_type,
            method=request.method,
            period_days=request.period_days,
            config=request.config
        )
        
        # Convert datetime to string for JSON serialization
        response_data = result.__dict__.copy()
        response_data['generated_at'] = result.generated_at.isoformat()
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "Correlation visualization created",
            user_id=current_user.get("user_id"),
            visualization_type=request.visualization_type.value,
            symbol_count=len(request.symbols)
        )
        
        return {
            "success": True,
            "data": response_data,
            "message": "Correlation visualization created successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error creating correlation visualization",
            user_id=current_user.get("user_id"),
            symbols=request.symbols,
            visualization_type=request.visualization_type.value,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sectors", response_model=Dict[str, Any])
async def analyze_sector_correlations(
    request: SectorCorrelationRequest,
    background_tasks: BackgroundTasks,
    service: CorrelationAnalysisService = Depends(get_correlation_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Analyze correlations within and between sectors.
    
    - **sector_symbols**: Dictionary mapping sector names to lists of symbols
    - **method**: Correlation calculation method
    - **period_days**: Number of days of historical data to analyze
    """
    try:
        logger.info(
            "Analyzing sector correlations",
            user_id=current_user.get("user_id"),
            sectors=list(request.sector_symbols.keys()),
            method=request.method.value
        )
        
        # Analyze sector correlations
        result = await service.analyze_sector_correlations(
            sector_symbols=request.sector_symbols,
            method=request.method,
            period_days=request.period_days
        )
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "Sector correlation analysis completed",
            user_id=current_user.get("user_id"),
            sector_count=len(request.sector_symbols)
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Sector correlation analysis completed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error analyzing sector correlations",
            user_id=current_user.get("user_id"),
            sectors=list(request.sector_symbols.keys()),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/methods", response_model=Dict[str, Any])
async def get_correlation_methods(
    current_user: Dict = Depends(get_current_user)
):
    """Get available correlation calculation methods."""
    try:
        methods = [
            {
                "value": method.value,
                "name": method.value.replace("_", " ").title(),
                "description": _get_method_description(method)
            }
            for method in CorrelationMethod
        ]
        
        return {
            "success": True,
            "data": methods,
            "message": "Correlation methods retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting correlation methods",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/visualizations", response_model=Dict[str, Any])
async def get_visualization_types(
    current_user: Dict = Depends(get_current_user)
):
    """Get available visualization types."""
    try:
        visualizations = [
            {
                "value": viz_type.value,
                "name": viz_type.value.replace("_", " ").title(),
                "description": _get_visualization_description(viz_type)
            }
            for viz_type in VisualizationType
        ]
        
        return {
            "success": True,
            "data": visualizations,
            "message": "Visualization types retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting visualization types",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/default", response_model=Dict[str, Any])
async def get_default_config(
    current_user: Dict = Depends(get_current_user)
):
    """Get default visualization configuration."""
    try:
        service = CorrelationAnalysisService(UnifiedCacheManager())
        config = service.default_visualization_config
        
        return {
            "success": True,
            "data": config,
            "message": "Default configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting default config",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

def _get_method_description(method: CorrelationMethod) -> str:
    """Get description for correlation method."""
    descriptions = {
        CorrelationMethod.PEARSON: "Standard linear correlation coefficient",
        CorrelationMethod.SPEARMAN: "Rank-based correlation coefficient",
        CorrelationMethod.KENDALL: "Rank-based correlation measuring ordinal association",
        CorrelationMethod.DYNAMIC_ROLLING: "Time-varying correlation using rolling windows"
    }
    return descriptions.get(method, "Unknown method")

def _get_visualization_description(viz_type: VisualizationType) -> str:
    """Get description for visualization type."""
    descriptions = {
        VisualizationType.HEATMAP: "Color-coded matrix showing correlation values",
        VisualizationType.NETWORK: "Graph showing relationships between assets",
        VisualizationType.SCATTER_MATRIX: "Matrix of scatter plots for all pairs",
        VisualizationType.TIME_SERIES: "Time series of rolling correlations",
        VisualizationType.DENDROGRAM: "Hierarchical clustering visualization"
    }
    return descriptions.get(viz_type, "Unknown visualization type")