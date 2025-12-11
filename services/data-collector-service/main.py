"""
Data Collector Service

Microservice for collecting financial data from multiple sources:
- Yahoo Finance (stock prices, market data)
- Reddit (sentiment from r/stocks, r/investing)
- Twitter/X (sentiment from financial discussions)
"""

import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4
import asyncio

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis.asyncio as redis

from collectors import YahooFinanceCollector, RedditCollector, TwitterCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Pydantic Models
class CollectStocksRequest(BaseModel):
    """Request model for stock collection."""
    symbols: List[str] = Field(..., min_items=1, max_items=100)
    priority: str = Field(default="MEDIUM", regex="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class CollectSentimentRequest(BaseModel):
    """Request model for sentiment collection."""
    symbols: List[str] = Field(..., min_items=1, max_items=50)
    sources: List[str] = Field(default=["reddit"], regex="^(reddit|twitter)$")


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: float
    result_count: int = 0
    error: Optional[str] = None
    timestamp: str


class DataCollectionResponse(BaseModel):
    """Response model for collected data."""
    symbol: str
    data: Dict[str, Any]
    source: str
    timestamp: str


# Initialize FastAPI app
app = FastAPI(
    title="InsiteChart Data Collector Service",
    description="Microservice for collecting financial data from multiple sources",
    version="1.0.0"
)

# Global services
yahoo_collector = YahooFinanceCollector(cache_ttl=300)
reddit_collector = RedditCollector()
twitter_collector = TwitterCollector()

# Job tracking
jobs: Dict[str, Dict[str, Any]] = {}
redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global redis_client

    logger.info("Data Collector Service starting...")

    # Initialize Redis connection
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = await redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {str(e)}")
        redis_client = None

    logger.info("Data Collector Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global redis_client

    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

    logger.info("Data Collector Service shut down")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "data-collector",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics", tags=["Metrics"])
async def get_metrics():
    """Get service metrics."""
    return {
        "active_jobs": len([j for j in jobs.values() if j["status"] == "running"]),
        "completed_jobs": len([j for j in jobs.values() if j["status"] == "completed"]),
        "failed_jobs": len([j for j in jobs.values() if j["status"] == "failed"]),
        "cache_stats": yahoo_collector.get_cache_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }


# Stock Collection Endpoints
@app.post("/api/v1/collect/stocks", tags=["Data Collection"])
async def collect_stocks(
    request: CollectStocksRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a background job to collect stock data.

    Args:
        request: Collection request with symbols and priority

    Returns:
        Job information with job_id for tracking progress
    """
    try:
        job_id = str(uuid4())

        # Create job entry
        jobs[job_id] = {
            "id": job_id,
            "status": "started",
            "type": "stocks",
            "symbols": request.symbols,
            "priority": request.priority,
            "progress": 0,
            "result_count": 0,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }

        # Start background task
        background_tasks.add_task(
            _collect_stocks_job,
            job_id,
            request.symbols
        )

        logger.info(f"Started stock collection job {job_id} for symbols: {request.symbols}")

        return {
            "job_id": job_id,
            "status": "started",
            "symbols": request.symbols,
            "priority": request.priority,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting stock collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/collect/stocks/{job_id}", tags=["Data Collection"])
async def get_stocks_job_status(job_id: str):
    """
    Get the status of a stock collection job.

    Args:
        job_id: Job ID to check

    Returns:
        Job status information
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        result_count=job["result_count"],
        error=job.get("error"),
        timestamp=datetime.utcnow().isoformat()
    )


# Sentiment Collection Endpoints
@app.post("/api/v1/collect/sentiment", tags=["Data Collection"])
async def collect_sentiment(
    request: CollectSentimentRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a background job to collect sentiment data.

    Args:
        request: Collection request with symbols and sources

    Returns:
        Job information with job_id for tracking progress
    """
    try:
        job_id = str(uuid4())

        # Create job entry
        jobs[job_id] = {
            "id": job_id,
            "status": "started",
            "type": "sentiment",
            "symbols": request.symbols,
            "sources": request.sources,
            "progress": 0,
            "result_count": 0,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }

        # Start background task
        background_tasks.add_task(
            _collect_sentiment_job,
            job_id,
            request.symbols,
            request.sources
        )

        logger.info(f"Started sentiment collection job {job_id} for symbols: {request.symbols}")

        return {
            "job_id": job_id,
            "status": "started",
            "symbols": request.symbols,
            "sources": request.sources,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting sentiment collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/collect/sentiment/{job_id}", tags=["Data Collection"])
async def get_sentiment_job_status(job_id: str):
    """
    Get the status of a sentiment collection job.

    Args:
        job_id: Job ID to check

    Returns:
        Job status information
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        result_count=job["result_count"],
        error=job.get("error"),
        timestamp=datetime.utcnow().isoformat()
    )


# Background Job Functions
async def _collect_stocks_job(job_id: str, symbols: List[str]):
    """
    Background job for collecting stock data.

    Args:
        job_id: Job ID
        symbols: List of symbols to collect
    """
    try:
        jobs[job_id]["status"] = "running"

        # Collect data for each symbol
        results = await yahoo_collector.collect_multiple(symbols)

        # Filter out None results
        successful_results = {k: v for k, v in results.items() if v is not None}

        # Store results in Redis if available
        if redis_client:
            try:
                for symbol, data in successful_results.items():
                    cache_key = f"stock:{symbol}"
                    await redis_client.set(
                        cache_key,
                        str(data),
                        ex=300  # 5 minute expiry
                    )
            except Exception as e:
                logger.warning(f"Could not cache results in Redis: {str(e)}")

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100.0
        jobs[job_id]["result_count"] = len(successful_results)
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Stock collection job {job_id} completed with {len(successful_results)} results")

    except Exception as e:
        logger.error(f"Error in stock collection job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


async def _collect_sentiment_job(job_id: str, symbols: List[str], sources: List[str]):
    """
    Background job for collecting sentiment data.

    Args:
        job_id: Job ID
        symbols: List of symbols to collect
        sources: List of sources (reddit, twitter)
    """
    try:
        jobs[job_id]["status"] = "running"
        results_count = 0

        # Collect from Reddit
        if "reddit" in sources:
            reddit_results = await reddit_collector.collect_multiple(symbols)
            results_count += len([r for r in reddit_results.values() if r is not None])

        # Collect from Twitter
        if "twitter" in sources:
            twitter_results = await twitter_collector.collect_multiple(symbols)
            results_count += len([r for r in twitter_results.values() if r is not None])

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100.0
        jobs[job_id]["result_count"] = results_count
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Sentiment collection job {job_id} completed with {results_count} results")

    except Exception as e:
        logger.error(f"Error in sentiment collection job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


# Direct Collection Endpoints (for quick single requests)
@app.get("/api/v1/quick/stock/{symbol}", tags=["Quick Collection"])
async def get_stock_data(symbol: str = Query(..., min_length=1, max_length=10)):
    """
    Quickly get stock data for a single symbol (synchronous).

    Args:
        symbol: Stock symbol

    Returns:
        Stock data
    """
    try:
        data = await yahoo_collector.collect(symbol.upper())

        if data:
            return {
                "success": True,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

    except Exception as e:
        logger.error(f"Error getting stock data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/quick/sentiment/{symbol}", tags=["Quick Collection"])
async def get_sentiment_data(
    symbol: str = Query(..., min_length=1, max_length=10),
    source: str = Query("reddit", regex="^(reddit|twitter)$")
):
    """
    Quickly get sentiment data for a single symbol (synchronous).

    Args:
        symbol: Stock symbol
        source: Data source (reddit or twitter)

    Returns:
        Sentiment data
    """
    try:
        if source == "reddit":
            data = await reddit_collector.collect(symbol.upper())
        else:  # twitter
            data = await twitter_collector.collect(symbol.upper())

        if data:
            return {
                "success": True,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"No sentiment data found for {symbol}")

    except Exception as e:
        logger.error(f"Error getting sentiment data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
