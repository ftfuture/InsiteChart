"""Routes for Analytics Service."""

import logging
from typing import List, Optional
import httpx

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer

from middleware.auth import JWTHandler, get_jwt_handler
from models.gateway_models import GatewayResponse, ServiceName
from services.service_discovery import get_service_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])
security = HTTPBearer()


async def get_analytics_service_url() -> str:
    """Get Analytics Service URL."""
    registry = get_service_registry()
    url = registry.get_service_url("analytics")
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Analytics Service not available"
        )
    return url


@router.post("/analyze/sentiment", response_model=GatewayResponse)
async def analyze_sentiment(
    symbol: str,
    text: str,
    model: str = "ensemble",
    service_url: str = Depends(get_analytics_service_url)
):
    """Proxy sentiment analysis request to Analytics Service.

    Args:
        symbol: Stock symbol
        text: Text to analyze
        model: Model type (vader, bert, ensemble)
        service_url: Analytics Service URL

    Returns:
        Gateway response with analysis results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/analyze/sentiment",
                json={
                    "symbol": symbol,
                    "text": text,
                    "model": model
                },
                timeout=10.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return GatewayResponse(
            service=ServiceName.ANALYTICS,
            status_code=response.status_code,
            data=response.json(),
            timestamp=None,
            request_id=None
        )

    except httpx.TimeoutException:
        logger.error("Analytics Service timeout")
        raise HTTPException(status_code=504, detail="Analytics Service timeout")
    except Exception as e:
        logger.error(f"Analytics Service error: {e}")
        raise HTTPException(status_code=503, detail="Analytics Service error")


@router.post("/analyze/sentiment/batch")
async def analyze_sentiment_batch(
    texts: List[str] = Query(...),
    model: str = Query("ensemble"),
    service_url: str = Depends(get_analytics_service_url)
):
    """Proxy batch sentiment analysis request.

    Args:
        texts: List of texts to analyze
        model: Model type (vader, bert, ensemble)
        service_url: Analytics Service URL

    Returns:
        Batch analysis results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/analyze/sentiment/batch",
                params={"model": model},
                json={"texts": texts},
                timeout=30.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Analytics Service timeout")
    except Exception as e:
        logger.error(f"Analytics batch sentiment error: {e}")
        raise HTTPException(status_code=503, detail="Analytics Service error")


@router.post("/analyze/correlation", response_model=GatewayResponse)
async def analyze_correlation(
    symbols: List[str] = Query(...),
    period: str = Query("1mo"),
    include_market: bool = Query(True),
    service_url: str = Depends(get_analytics_service_url)
):
    """Proxy correlation analysis request.

    Args:
        symbols: List of stock symbols
        period: Time period (1d, 1w, 1mo, 3mo, 6mo, 1y)
        include_market: Include market index
        service_url: Analytics Service URL

    Returns:
        Correlation analysis results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/analyze/correlation",
                json={
                    "symbols": symbols,
                    "period": period,
                    "include_market": include_market
                },
                timeout=15.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return GatewayResponse(
            service=ServiceName.ANALYTICS,
            status_code=response.status_code,
            data=response.json(),
            timestamp=None,
            request_id=None
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Analytics Service timeout")
    except Exception as e:
        logger.error(f"Analytics correlation error: {e}")
        raise HTTPException(status_code=503, detail="Analytics Service error")


@router.post("/analyze/trends", response_model=GatewayResponse)
async def analyze_trends(
    symbol: str,
    lookback_days: int = 30,
    include_anomalies: bool = True,
    service_url: str = Depends(get_analytics_service_url)
):
    """Proxy trend analysis request.

    Args:
        symbol: Stock symbol
        lookback_days: Historical days to analyze
        include_anomalies: Include anomaly detection
        service_url: Analytics Service URL

    Returns:
        Trend analysis results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/analyze/trends",
                json={
                    "symbol": symbol,
                    "lookback_days": lookback_days,
                    "include_anomalies": include_anomalies
                },
                timeout=15.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return GatewayResponse(
            service=ServiceName.ANALYTICS,
            status_code=response.status_code,
            data=response.json(),
            timestamp=None,
            request_id=None
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Analytics Service timeout")
    except Exception as e:
        logger.error(f"Analytics trends error: {e}")
        raise HTTPException(status_code=503, detail="Analytics Service error")


@router.post("/analyze/trends/batch")
async def analyze_trends_batch(
    symbols: List[str] = Query(...),
    lookback_days: int = Query(30),
    service_url: str = Depends(get_analytics_service_url)
):
    """Proxy batch trend analysis request.

    Args:
        symbols: List of stock symbols
        lookback_days: Historical days to analyze
        service_url: Analytics Service URL

    Returns:
        Batch trend analysis results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/analyze/trends/batch",
                params={"lookback_days": lookback_days},
                json={"symbols": symbols},
                timeout=60.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Analytics Service timeout")
    except Exception as e:
        logger.error(f"Analytics batch trends error: {e}")
        raise HTTPException(status_code=503, detail="Analytics Service error")
