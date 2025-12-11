"""FastAPI application for Analytics Service microservice."""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.correlation_analyzer import CorrelationAnalyzer
from analyzers.trend_analyzer import TrendAnalyzer
from models.analysis_models import (
    SentimentRequest,
    SentimentResponse,
    CorrelationRequest,
    CorrelationResponse,
    TrendRequest,
    TrendResponse,
    HealthResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global analyzer instances
sentiment_analyzer = None
correlation_analyzer = None
trend_analyzer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Analytics Service starting up...")
    global sentiment_analyzer, correlation_analyzer, trend_analyzer

    try:
        sentiment_analyzer = SentimentAnalyzer()
        correlation_analyzer = CorrelationAnalyzer()
        trend_analyzer = TrendAnalyzer()
        logger.info("All analyzers initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize analyzers: {e}")

    yield

    # Shutdown
    logger.info("Analytics Service shutting down...")


# Create FastAPI application
app = FastAPI(
    title="InsiteChart Analytics Service",
    description="Sentiment, Correlation, and Trend Analysis Microservice",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health and Info Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and dependencies."""
    try:
        # Check if analyzers are initialized
        status = "healthy" if all([
            sentiment_analyzer,
            correlation_analyzer,
            trend_analyzer
        ]) else "degraded"

        dependencies = {
            "sentiment_analyzer": "loaded" if sentiment_analyzer else "error",
            "correlation_analyzer": "loaded" if correlation_analyzer else "error",
            "trend_analyzer": "loaded" if trend_analyzer else "error",
            "bert_model": "available" if sentiment_analyzer and sentiment_analyzer.bert_available else "not_available"
        }

        return HealthResponse(
            status=status,
            version="1.0.0",
            dependencies=dependencies
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            dependencies={"error": str(e)}
        )


@app.get("/info")
async def service_info():
    """Get service information."""
    return {
        "service": "InsiteChart Analytics Service",
        "version": "1.0.0",
        "description": "Sentiment, Correlation, and Trend Analysis for Financial Markets",
        "endpoints": {
            "sentiment": "/api/v1/analyze/sentiment",
            "correlation": "/api/v1/analyze/correlation",
            "trends": "/api/v1/analyze/trends",
            "health": "/health",
            "docs": "/docs"
        }
    }


# ============================================================================
# Sentiment Analysis Endpoints
# ============================================================================

@app.post("/api/v1/analyze/sentiment", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment of text.

    Supports three models:
    - vader: Fast, rule-based sentiment analysis
    - bert: Deep learning model, more accurate
    - ensemble: Weighted average of VADER and BERT

    Example request:
    ```json
    {
        "symbol": "AAPL",
        "text": "Apple's new iPhone is amazing!",
        "sources": ["twitter", "reddit"],
        "model": "ensemble"
    }
    ```
    """
    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Sentiment analyzer not initialized")

    try:
        analysis = sentiment_analyzer.analyze(
            text=request.text,
            model=request.model,
            symbol=request.symbol
        )

        return SentimentResponse(
            symbol=request.symbol,
            sentiment=analysis,
            timestamp=analysis.pop("timestamp"),
            text_preview=request.text[:100]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/analyze/sentiment/batch")
async def analyze_sentiment_batch(
    texts: List[str] = Query(...),
    model: str = Query("ensemble")
):
    """Batch analyze sentiment for multiple texts."""
    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Sentiment analyzer not initialized")

    if len(texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per batch")

    try:
        results = sentiment_analyzer.batch_analyze(texts, model)
        return {
            "count": len(results),
            "model": model,
            "results": results,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Batch sentiment analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Correlation Analysis Endpoints
# ============================================================================

@app.post("/api/v1/analyze/correlation", response_model=CorrelationResponse)
async def analyze_correlation(request: CorrelationRequest):
    """Analyze correlations between stocks.

    Returns correlation matrix, strong pairs (|coef| > 0.7),
    and weak pairs (|coef| < 0.3) for portfolio diversification analysis.

    Example request:
    ```json
    {
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "period": "1mo",
        "include_market": true
    }
    ```
    """
    if not correlation_analyzer:
        raise HTTPException(status_code=503, detail="Correlation analyzer not initialized")

    try:
        analysis = correlation_analyzer.analyze(
            symbols=request.symbols,
            period=request.period,
            include_market=request.include_market
        )

        return CorrelationResponse(
            symbols=analysis["symbols"],
            period=analysis["period"],
            correlation_matrix=analysis["correlation_matrix"],
            strong_pairs=analysis["strong_pairs"],
            weak_pairs=analysis["weak_pairs"],
            timestamp=analysis["timestamp"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Correlation analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/analyze/correlation/rolling")
async def get_rolling_correlation(
    symbol1: str,
    symbol2: str,
    window_days: int = 30,
    period: str = "1mo"
):
    """Get rolling correlation between two symbols over time."""
    if not correlation_analyzer:
        raise HTTPException(status_code=503, detail="Correlation analyzer not initialized")

    try:
        result = correlation_analyzer.rolling_correlation(
            symbols=[symbol1, symbol2],
            window_days=window_days,
            period=period
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Rolling correlation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Trend Analysis Endpoints
# ============================================================================

@app.post("/api/v1/analyze/trends", response_model=TrendResponse)
async def analyze_trends(request: TrendRequest):
    """Analyze price trends for a stock.

    Detects:
    - Trend direction (uptrend, downtrend, sideways)
    - Support and resistance levels
    - Moving averages (SMA 50, 200)
    - Relative Strength Index (RSI)
    - Price anomalies (spikes, drops)

    Example request:
    ```json
    {
        "symbol": "AAPL",
        "lookback_days": 30,
        "include_anomalies": true
    }
    ```
    """
    if not trend_analyzer:
        raise HTTPException(status_code=503, detail="Trend analyzer not initialized")

    try:
        analysis = trend_analyzer.analyze(
            symbol=request.symbol,
            lookback_days=request.lookback_days,
            include_anomalies=request.include_anomalies
        )

        return TrendResponse(
            symbol=analysis["symbol"],
            trend=analysis["trend"],
            strength=analysis["strength"],
            support_levels=analysis["support_levels"],
            resistance_levels=analysis["resistance_levels"],
            moving_averages=analysis["moving_averages"],
            rsi=analysis["rsi"],
            anomalies=analysis.get("anomalies"),
            timestamp=analysis["timestamp"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Trend analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/analyze/trends/batch")
async def analyze_trends_batch(
    symbols: List[str] = Query(...),
    lookback_days: int = Query(30, ge=5, le=365)
):
    """Batch analyze trends for multiple stocks."""
    if not trend_analyzer:
        raise HTTPException(status_code=503, detail="Trend analyzer not initialized")

    if len(symbols) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 symbols per batch")

    try:
        results = trend_analyzer.batch_analyze(symbols, lookback_days)
        return {
            "count": len(results),
            "lookback_days": lookback_days,
            "results": results,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Batch trend analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}")
    return HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Root and Catch-all
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "InsiteChart Analytics Service",
        "status": "running",
        "documentation": "/docs"
    }


@app.get("/docs", include_in_schema=False)
async def get_docs():
    """Redirect to Swagger UI."""
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Analytics API")


if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Analytics Service on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
