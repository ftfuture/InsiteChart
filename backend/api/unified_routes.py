"""
Unified API routes for InsiteChart platform.

This module provides combined endpoints that integrate stock data
with sentiment analysis for a comprehensive view.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from fastapi.responses import JSONResponse

from ..models.unified_models import (
    UnifiedStockData,
    SearchQuery,
    SearchResult,
    StockType
)
from ..services.unified_service import UnifiedService
from ..middleware.auth_middleware import require_auth, optional_auth, require_permission

logger = logging.getLogger(__name__)
router = APIRouter()

# Import the global service instances from routes.py
from .routes import get_unified_service


@router.get("/stocks/{symbol}", response_model=UnifiedStockData)
async def get_stock(
    symbol: str = Path(..., description="Stock symbol"),
    include_sentiment: bool = Query(True, description="Include sentiment data"),
    include_historical: bool = Query(False, description="Include historical data"),
    period: str = Query("1y", description="Historical data period"),
    unified_service: UnifiedService = Depends(get_unified_service),
    user_data: Dict[str, Any] = Depends(optional_auth)
):
    """
    Get comprehensive stock information including sentiment data.
    
    This endpoint combines financial data with social sentiment analysis
    to provide a unified view of stock information.
    """
    try:
        stock_data = await unified_service.get_stock_data(
            symbol, 
            include_sentiment=include_sentiment
        )
        
        if not stock_data:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {symbol} not found"
            )
        
        # Include historical data if requested
        if include_historical:
            historical_data = await unified_service.get_historical_data(symbol, period)
            if historical_data:
                stock_data.historical_data = historical_data
        
        return stock_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/search", response_model=SearchResult)
async def search_stocks(
    query: SearchQuery,
    include_sentiment: bool = Query(True, description="Include sentiment data in results"),
    unified_service: UnifiedService = Depends(get_unified_service),
    user_data: Dict[str, Any] = Depends(optional_auth)
):
    """
    Search for stocks with integrated sentiment data.
    
    This endpoint provides search results that combine financial information
    with social sentiment analysis for comprehensive stock discovery.
    """
    try:
        search_results = await unified_service.search_stocks(query)
        
        # Add sentiment data if requested
        if include_sentiment:
            for stock in search_results.results:
                if not stock.overall_sentiment:
                    sentiment_data = await unified_service.get_sentiment_data(stock.symbol)
                    if sentiment_data:
                        stock.overall_sentiment = sentiment_data.get('overall_sentiment')
                        stock.mention_count_24h = sentiment_data.get('mention_count_24h')
                        stock.trending_status = sentiment_data.get('trending_status', False)
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching stocks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Search service unavailable"
        )


@router.get("/trending", response_model=List[UnifiedStockData])
async def get_trending_stocks(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    timeframe: str = Query("24h", regex="^(1h|6h|24h|7d)$", description="Timeframe for trending analysis"),
    include_sentiment: bool = Query(True, description="Include sentiment details"),
    unified_service: UnifiedService = Depends(get_unified_service),
    user_data: Dict[str, Any] = Depends(optional_auth)
):
    """
    Get currently trending stocks with comprehensive data.
    
    This endpoint identifies stocks that are trending on social media
    and provides detailed financial and sentiment analysis.
    """
    try:
        trending_stocks = await unified_service.get_trending_stocks(limit, timeframe)
        
        # Enhance with additional data if sentiment is requested
        if include_sentiment:
            for stock in trending_stocks:
                # Add community breakdown if available
                if not stock.sentiment_sources:
                    sentiment_data = await unified_service.get_sentiment_data(stock.symbol)
                    if sentiment_data and 'community_breakdown' in sentiment_data:
                        stock.community_breakdown = sentiment_data['community_breakdown']
        
        return trending_stocks
        
    except Exception as e:
        logger.error(f"Error getting trending stocks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Trending analysis service unavailable"
        )


@router.get("/market-overview")
async def get_market_overview(
    include_indices: bool = Query(True, description="Include market indices"),
    include_trending: bool = Query(True, description="Include trending stocks"),
    unified_service: UnifiedService = Depends(get_unified_service)
):
    """
    Get comprehensive market overview.
    
    This endpoint provides a snapshot of market conditions including
    major indices, trending stocks, and market sentiment.
    """
    try:
        overview = {}
        
        # Market indices
        if include_indices:
            indices = await unified_service.get_market_indices()
            overview['indices'] = indices
        
        # Trending stocks
        if include_trending:
            trending = await unified_service.get_trending_stocks(10, "24h")
            overview['trending'] = [stock.to_dict() for stock in trending]
        
        # Market sentiment
        market_sentiment = await unified_service.get_market_sentiment()
        overview['market_sentiment'] = market_sentiment
        
        # Market statistics
        market_stats = await unified_service.get_market_statistics()
        overview['statistics'] = market_stats
        
        # Metadata
        overview['last_updated'] = datetime.utcnow().isoformat()
        overview['data_quality'] = await unified_service.get_data_quality_report()
        
        return overview
        
    except Exception as e:
        logger.error(f"Error getting market overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Market overview service unavailable"
        )


@router.get("/compare")
async def compare_stocks(
    symbols: List[str] = Query(..., description="Stock symbols to compare"),
    period: str = Query("1y", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$", description="Comparison period"),
    include_sentiment: bool = Query(True, description="Include sentiment comparison"),
    unified_service: UnifiedService = Depends(get_unified_service)
):
    """
    Compare multiple stocks with integrated analysis.
    
    This endpoint provides side-by-side comparison of multiple stocks
    including both financial metrics and sentiment analysis.
    """
    try:
        if len(symbols) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 symbols can be compared at once"
            )
        
        comparison_data = await unified_service.compare_stocks(
            symbols, 
            period=period,
            include_sentiment=include_sentiment
        )
        
        return comparison_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing stocks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Stock comparison service unavailable"
        )


@router.get("/sentiment/{symbol}")
async def get_detailed_sentiment(
    symbol: str = Path(..., description="Stock symbol"),
    sources: Optional[str] = Query(None, description="Comma-separated sources: reddit,twitter,discord"),
    timeframe: str = Query("24h", regex="^(1h|6h|24h|7d)$", description="Analysis timeframe"),
    include_mentions: bool = Query(False, description="Include individual mentions"),
    unified_service: UnifiedService = Depends(get_unified_service)
):
    """
    Get detailed sentiment analysis for a stock.
    
    This endpoint provides comprehensive sentiment analysis including
    source breakdown, mention trends, and community analysis.
    """
    try:
        sentiment_data = await unified_service.get_detailed_sentiment(
            symbol=symbol,
            sources=sources.split(',') if sources else None,
            timeframe=timeframe,
            include_mentions=include_mentions
        )
        
        if not sentiment_data:
            raise HTTPException(
                status_code=404,
                detail=f"No sentiment data available for {symbol}"
            )
        
        return sentiment_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sentiment for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Sentiment analysis service unavailable"
        )


@router.get("/correlation/{symbol1}/{symbol2}")
async def get_correlation_analysis(
    symbol1: str = Path(..., description="First stock symbol"),
    symbol2: str = Path(..., description="Second stock symbol"),
    period: str = Query("1y", regex="^(1mo|3mo|6mo|1y|2y)$", description="Analysis period"),
    include_sentiment: bool = Query(True, description="Include sentiment correlation"),
    unified_service: UnifiedService = Depends(get_unified_service)
):
    """
    Get correlation analysis between two stocks.
    
    This endpoint analyzes price correlation and sentiment correlation
    between two stocks over the specified period.
    """
    try:
        correlation_data = await unified_service.get_correlation_analysis(
            symbol1=symbol1,
            symbol2=symbol2,
            period=period,
            include_sentiment=include_sentiment
        )
        
        return correlation_data
        
    except Exception as e:
        logger.error(f"Error getting correlation analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Correlation analysis service unavailable"
        )


@router.get("/watchlist/{user_id}")
async def get_user_watchlist(
    user_id: str = Path(..., description="User ID"),
    include_sentiment: bool = Query(True, description="Include sentiment data"),
    include_alerts: bool = Query(True, description="Include price/sentiment alerts"),
    unified_service: UnifiedService = Depends(get_unified_service),
    user_data: Dict[str, Any] = Depends(require_auth)
):
    """
    Get user's watchlist with integrated data.
    
    This endpoint retrieves the user's watchlist with both financial
    and sentiment data for comprehensive portfolio tracking.
    """
    try:
        watchlist_data = await unified_service.get_user_watchlist(
            user_id=user_id,
            include_sentiment=include_sentiment,
            include_alerts=include_alerts
        )
        
        return watchlist_data
        
    except Exception as e:
        logger.error(f"Error getting watchlist for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Watchlist service unavailable"
        )


@router.post("/watchlist/{user_id}")
async def add_to_watchlist(
    user_id: str = Path(..., description="User ID"),
    symbol: str = Query(..., description="Stock symbol to add"),
    category: Optional[str] = Query(None, description="Watchlist category"),
    alert_threshold: Optional[float] = Query(None, description="Price change alert threshold"),
    sentiment_alert: bool = Query(False, description="Enable sentiment alerts"),
    unified_service: UnifiedService = Depends(get_unified_service),
    user_data: Dict[str, Any] = Depends(require_auth)
):
    """
    Add stock to user's watchlist with alert preferences.
    
    This endpoint adds a stock to the user's watchlist and configures
    personalized alerts for price movements and sentiment changes.
    """
    try:
        result = await unified_service.add_to_watchlist(
            user_id=user_id,
            symbol=symbol,
            category=category,
            alert_threshold=alert_threshold,
            sentiment_alert=sentiment_alert
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error adding {symbol} to watchlist: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Watchlist service unavailable"
        )


@router.get("/analytics/insights")
async def get_market_insights(
    timeframe: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$", description="Analysis timeframe"),
    category: Optional[str] = Query(None, description="Stock category filter"),
    unified_service: UnifiedService = Depends(get_unified_service)
):
    """
    Get market insights and analytics.
    
    This endpoint provides market-wide insights including trending sectors,
    sentiment patterns, and investment opportunities.
    """
    try:
        insights = await unified_service.get_market_insights(
            timeframe=timeframe,
            category=category
        )
        
        return insights
        
    except Exception as e:
        logger.error(f"Error getting market insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Analytics service unavailable"
        )