"""Routes for Data Collector Service."""

import logging
from typing import List
import httpx

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer

from models.gateway_models import GatewayResponse, ServiceName
from services.service_discovery import get_service_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-collector", tags=["data-collector"])
security = HTTPBearer()


async def get_data_collector_service_url() -> str:
    """Get Data Collector Service URL."""
    registry = get_service_registry()
    url = registry.get_service_url("data_collector")
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Data Collector Service not available"
        )
    return url


@router.post("/collect/yahoo-finance", response_model=GatewayResponse)
async def collect_yahoo_finance(
    symbols: List[str] = Query(...),
    service_url: str = Depends(get_data_collector_service_url)
):
    """Proxy Yahoo Finance data collection request.

    Args:
        symbols: List of stock symbols
        service_url: Data Collector Service URL

    Returns:
        Collected stock data
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/collect/yahoo-finance",
                json={"symbols": symbols},
                timeout=30.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return GatewayResponse(
            service=ServiceName.DATA_COLLECTOR,
            status_code=response.status_code,
            data=response.json(),
            timestamp=None,
            request_id=None
        )

    except httpx.TimeoutException:
        logger.error("Data Collector Service timeout")
        raise HTTPException(status_code=504, detail="Data Collector Service timeout")
    except Exception as e:
        logger.error(f"Data Collector Service error: {e}")
        raise HTTPException(status_code=503, detail="Data Collector Service error")


@router.post("/collect/reddit", response_model=GatewayResponse)
async def collect_reddit_data(
    symbols: List[str] = Query(...),
    limit: int = Query(10),
    service_url: str = Depends(get_data_collector_service_url)
):
    """Proxy Reddit sentiment data collection request.

    Args:
        symbols: List of stock symbols
        limit: Number of posts to retrieve
        service_url: Data Collector Service URL

    Returns:
        Collected Reddit data
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/collect/reddit",
                json={
                    "symbols": symbols,
                    "limit": limit
                },
                timeout=30.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return GatewayResponse(
            service=ServiceName.DATA_COLLECTOR,
            status_code=response.status_code,
            data=response.json(),
            timestamp=None,
            request_id=None
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Data Collector Service timeout")
    except Exception as e:
        logger.error(f"Reddit collection error: {e}")
        raise HTTPException(status_code=503, detail="Data Collector Service error")


@router.post("/collect/twitter", response_model=GatewayResponse)
async def collect_twitter_data(
    symbols: List[str] = Query(...),
    limit: int = Query(10),
    service_url: str = Depends(get_data_collector_service_url)
):
    """Proxy Twitter sentiment data collection request.

    Args:
        symbols: List of stock symbols
        limit: Number of tweets to retrieve
        service_url: Data Collector Service URL

    Returns:
        Collected Twitter data
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/collect/twitter",
                json={
                    "symbols": symbols,
                    "limit": limit
                },
                timeout=30.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return GatewayResponse(
            service=ServiceName.DATA_COLLECTOR,
            status_code=response.status_code,
            data=response.json(),
            timestamp=None,
            request_id=None
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Data Collector Service timeout")
    except Exception as e:
        logger.error(f"Twitter collection error: {e}")
        raise HTTPException(status_code=503, detail="Data Collector Service error")


@router.get("/status/{collector_id}")
async def get_collection_status(
    collector_id: str,
    service_url: str = Depends(get_data_collector_service_url)
):
    """Get status of a background collection task.

    Args:
        collector_id: Collection task ID
        service_url: Data Collector Service URL

    Returns:
        Task status and progress
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{service_url}/api/v1/status/{collector_id}",
                timeout=10.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Data Collector Service timeout")
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=503, detail="Data Collector Service error")
