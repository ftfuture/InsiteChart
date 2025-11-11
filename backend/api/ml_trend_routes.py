"""
Machine Learning Trend Detection API Routes for InsiteChart platform.

This module provides REST API endpoints for ML-based trend detection
and prediction functionality.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.ml_trend_detection_service import (
    MLTrendDetectionService,
    ModelType,
    TrendDirection,
    TrendStrength
)
from ..cache.unified_cache import UnifiedCacheManager
from ..middleware.auth_middleware import get_current_user
from ..logging.structured_logger import StructuredLogger

# Initialize router
router = APIRouter(prefix="/api/ml-trend", tags=["ml-trend"])

# Initialize logger
logger = StructuredLogger(__name__)

# Pydantic models for request/response
class TrendPredictionRequest(BaseModel):
    symbol: str = Field(..., description="Symbol to analyze")
    model_type: ModelType = Field(ModelType.ENSEMBLE, description="ML model to use")
    horizon: int = Field(30, description="Prediction horizon in days", ge=1, le=365)
    period_days: int = Field(252, description="Historical data period in days", ge=30, le=1000)

class ModelTrainingRequest(BaseModel):
    symbol: str = Field(..., description="Symbol to train model for")
    model_type: ModelType = Field(..., description="Model type to train")
    period_days: int = Field(252, description="Training data period in days", ge=30, le=1000)

class BatchTrendRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to analyze", min_items=1, max_items=20)
    model_type: ModelType = Field(ModelType.ENSEMBLE, description="ML model to use")
    horizon: int = Field(30, description="Prediction horizon in days", ge=1, le=365)
    period_days: int = Field(252, description="Historical data period in days", ge=30, le=1000)

# Dependency injection
async def get_ml_trend_service() -> MLTrendDetectionService:
    """Get ML trend detection service instance."""
    cache_manager = UnifiedCacheManager()
    return MLTrendDetectionService(cache_manager)

@router.post("/predict", response_model=Dict[str, Any])
async def predict_trend(
    request: TrendPredictionRequest,
    background_tasks: BackgroundTasks,
    service: MLTrendDetectionService = Depends(get_ml_trend_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate trend prediction for a symbol using ML models.
    
    - **symbol**: Stock symbol to analyze (e.g., "AAPL")
    - **model_type**: ML model type (lstm, prophet, arima, random_forest, ensemble, technical_analysis)
    - **horizon**: Number of days to predict ahead
    - **period_days**: Number of days of historical data to use
    """
    try:
        logger.info(
            "Generating ML trend prediction",
            user_id=current_user.get("user_id"),
            symbol=request.symbol,
            model_type=request.model_type.value,
            horizon=request.horizon
        )
        
        # Generate trend prediction
        result = await service.predict_trend(
            symbol=request.symbol,
            model_type=request.model_type,
            horizon=request.horizon,
            period_days=request.period_days
        )
        
        # Convert result to dictionary for JSON serialization
        response_data = {
            "symbol": result.symbol,
            "current_trend": result.current_trend.value,
            "trend_strength": result.trend_strength.value,
            "trend_duration": result.trend_duration,
            "predictions": [
                {
                    "symbol": pred.symbol,
                    "current_price": pred.current_price,
                    "predicted_direction": pred.predicted_direction.value,
                    "predicted_strength": pred.predicted_strength.value,
                    "confidence": pred.confidence,
                    "time_horizon": pred.time_horizon,
                    "price_targets": pred.price_targets,
                    "support_levels": pred.support_levels,
                    "resistance_levels": pred.resistance_levels,
                    "volatility_forecast": pred.volatility_forecast,
                    "model_used": pred.model_used.value,
                    "signals": [
                        {
                            "timestamp": signal.timestamp.isoformat(),
                            "direction": signal.direction.value,
                            "strength": signal.strength.value,
                            "confidence": signal.confidence,
                            "price_target": signal.price_target,
                            "time_horizon": signal.time_horizon,
                            "volume_confirmation": signal.volume_confirmation,
                            "technical_indicators": signal.technical_indicators
                        }
                        for signal in pred.signals
                    ],
                    "generated_at": pred.generated_at.isoformat()
                }
                for pred in result.predictions
            ],
            "consensus_direction": result.consensus_direction.value,
            "consensus_strength": result.consensus_strength.value,
            "consensus_confidence": result.consensus_confidence,
            "key_levels": result.key_levels,
            "risk_factors": result.risk_factors,
            "opportunities": result.opportunities,
            "analysis_period": result.analysis_period
        }
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "ML trend prediction completed",
            user_id=current_user.get("user_id"),
            symbol=request.symbol,
            consensus_direction=result.consensus_direction.value,
            consensus_confidence=result.consensus_confidence
        )
        
        return {
            "success": True,
            "data": response_data,
            "message": "Trend prediction generated successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error generating ML trend prediction",
            user_id=current_user.get("user_id"),
            symbol=request.symbol,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train", response_model=Dict[str, Any])
async def train_model(
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    service: MLTrendDetectionService = Depends(get_ml_trend_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Train an ML model for a specific symbol.
    
    - **symbol**: Stock symbol to train model for
    - **model_type**: ML model type to train
    - **period_days**: Number of days of historical data to use for training
    """
    try:
        logger.info(
            "Training ML model",
            user_id=current_user.get("user_id"),
            symbol=request.symbol,
            model_type=request.model_type.value,
            period_days=request.period_days
        )
        
        # Train model
        result = await service.train_model(
            symbol=request.symbol,
            model_type=request.model_type,
            period_days=request.period_days
        )
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "ML model training completed",
            user_id=current_user.get("user_id"),
            symbol=request.symbol,
            model_type=request.model_type.value,
            status=result.get("status", "unknown")
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Model {request.model_type.value} trained successfully for {request.symbol}"
        }
        
    except Exception as e:
        logger.error(
            "Error training ML model",
            user_id=current_user.get("user_id"),
            symbol=request.symbol,
            model_type=request.model_type.value,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-predict", response_model=Dict[str, Any])
async def batch_predict_trends(
    request: BatchTrendRequest,
    background_tasks: BackgroundTasks,
    service: MLTrendDetectionService = Depends(get_ml_trend_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate trend predictions for multiple symbols.
    
    - **symbols**: List of stock symbols to analyze
    - **model_type**: ML model type to use
    - **horizon**: Number of days to predict ahead
    - **period_days**: Number of days of historical data to use
    """
    try:
        logger.info(
            "Generating batch ML trend predictions",
            user_id=current_user.get("user_id"),
            symbols=request.symbols,
            model_type=request.model_type.value,
            symbol_count=len(request.symbols)
        )
        
        # Generate predictions for all symbols
        results = {}
        errors = {}
        
        for symbol in request.symbols:
            try:
                result = await service.predict_trend(
                    symbol=symbol,
                    model_type=request.model_type,
                    horizon=request.horizon,
                    period_days=request.period_days
                )
                
                # Convert to simplified format for batch response
                results[symbol] = {
                    "current_trend": result.current_trend.value,
                    "trend_strength": result.trend_strength.value,
                    "consensus_direction": result.consensus_direction.value,
                    "consensus_strength": result.consensus_strength.value,
                    "consensus_confidence": result.consensus_confidence,
                    "price_targets": result.predictions[0].price_targets if result.predictions else [],
                    "risk_factors": result.risk_factors,
                    "opportunities": result.opportunities
                }
                
            except Exception as e:
                logger.error(f"Error predicting trend for {symbol}: {str(e)}")
                errors[symbol] = str(e)
        
        # Log completion in background
        background_tasks.add_task(
            logger.info,
            "Batch ML trend predictions completed",
            user_id=current_user.get("user_id"),
            total_symbols=len(request.symbols),
            successful=len(results),
            failed=len(errors)
        )
        
        return {
            "success": True,
            "data": {
                "predictions": results,
                "errors": errors,
                "summary": {
                    "total_symbols": len(request.symbols),
                    "successful": len(results),
                    "failed": len(errors)
                }
            },
            "message": f"Batch trend predictions completed for {len(results)} symbols"
        }
        
    except Exception as e:
        logger.error(
            "Error in batch ML trend predictions",
            user_id=current_user.get("user_id"),
            symbols=request.symbols,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=Dict[str, Any])
async def get_available_models(
    current_user: Dict = Depends(get_current_user)
):
    """Get available ML models and their information."""
    try:
        service = MLTrendDetectionService(UnifiedCacheManager())
        model_status = await service.get_model_status()
        
        # Format model information
        models = []
        for model_type, info in model_status.get("models", {}).items():
            models.append({
                "type": model_type,
                "name": model_type.replace("_", " ").title(),
                "description": _get_model_description(ModelType(model_type)),
                "is_trained": info.get("is_trained", False),
                "features": info.get("features", [])
            })
        
        return {
            "success": True,
            "data": {
                "models": models,
                "available_models": model_status.get("available_models", []),
                "cache_ttl": model_status.get("cache_ttl", {})
            },
            "message": "Available models retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting available models",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=Dict[str, Any])
async def get_service_status(
    service: MLTrendDetectionService = Depends(get_ml_trend_service),
    current_user: Dict = Depends(get_current_user)
):
    """Get ML trend detection service status."""
    try:
        status = await service.get_model_status()
        
        return {
            "success": True,
            "data": status,
            "message": "Service status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting service status",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trend-directions", response_model=Dict[str, Any])
async def get_trend_directions(
    current_user: Dict = Depends(get_current_user)
):
    """Get available trend direction types."""
    try:
        directions = [
            {
                "value": direction.value,
                "name": direction.value.replace("_", " ").title(),
                "description": _get_trend_direction_description(direction)
            }
            for direction in TrendDirection
        ]
        
        return {
            "success": True,
            "data": directions,
            "message": "Trend directions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting trend directions",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trend-strengths", response_model=Dict[str, Any])
async def get_trend_strengths(
    current_user: Dict = Depends(get_current_user)
):
    """Get available trend strength levels."""
    try:
        strengths = [
            {
                "value": strength.value,
                "name": strength.value.replace("_", " ").title(),
                "description": _get_trend_strength_description(strength)
            }
            for strength in TrendStrength
        ]
        
        return {
            "success": True,
            "data": strengths,
            "message": "Trend strengths retrieved successfully"
        }
        
    except Exception as e:
        logger.error(
            "Error getting trend strengths",
            user_id=current_user.get("user_id"),
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

def _get_model_description(model_type: ModelType) -> str:
    """Get description for ML model type."""
    descriptions = {
        ModelType.LSTM: "Long Short-Term Memory neural network for time series prediction",
        ModelType.PROPHET: "Facebook's Prophet time series forecasting model",
        ModelType.ARIMA: "AutoRegressive Integrated Moving Average model",
        ModelType.RANDOM_FOREST: "Random Forest ensemble model for trend prediction",
        ModelType.ENSEMBLE: "Combined prediction from multiple models for improved accuracy",
        ModelType.TECHNICAL_ANALYSIS: "Traditional technical analysis indicators and patterns"
    }
    return descriptions.get(model_type, "Unknown model type")

def _get_trend_direction_description(direction: TrendDirection) -> str:
    """Get description for trend direction."""
    descriptions = {
        TrendDirection.UPTREND: "Price is expected to increase over the prediction horizon",
        TrendDirection.DOWNTREND: "Price is expected to decrease over the prediction horizon",
        TrendDirection.SIDEWAYS: "Price is expected to remain relatively stable with minor fluctuations",
        TrendDirection.REVERSAL_UP: "Current downtrend is expected to reverse to an uptrend",
        TrendDirection.REVERSAL_DOWN: "Current uptrend is expected to reverse to a downtrend",
        TrendDirection.CONSOLIDATION: "Price is expected to consolidate in a narrow range"
    }
    return descriptions.get(direction, "Unknown trend direction")

def _get_trend_strength_description(strength: TrendStrength) -> str:
    """Get description for trend strength."""
    descriptions = {
        TrendStrength.WEAK: "Low confidence prediction with minimal price movement expected",
        TrendStrength.MODERATE: "Medium confidence prediction with moderate price movement expected",
        TrendStrength.STRONG: "High confidence prediction with significant price movement expected",
        TrendStrength.VERY_STRONG: "Very high confidence prediction with major price movement expected"
    }
    return descriptions.get(strength, "Unknown trend strength")