"""
Test routes for automation testing.
This module provides simple test endpoints for automation testing.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time
import random

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint."""
    return {
        "message": "Test endpoint working",
        "timestamp": time.time(),
        "random": random.randint(1, 100)
    }


@router.get("/test-cache")
async def test_cache_endpoint():
    """Test cache endpoint."""
    return {
        "message": "Cache test endpoint working",
        "timestamp": time.time(),
        "cache_test": True
    }


@router.get("/stocks/{symbol}")
async def get_stock_data(symbol: str):
    """Get stock data for testing."""
    # Mock stock data for testing
    mock_data = {
        "symbol": symbol.upper(),
        "company_name": f"{symbol.upper()} Company",
        "current_price": round(random.uniform(100, 500), 2),
        "previous_close": round(random.uniform(100, 500), 2),
        "day_change": round(random.uniform(-10, 10), 2),
        "day_change_pct": round(random.uniform(-5, 5), 2),
        "volume": random.randint(1000000, 10000000),
        "timestamp": time.time()
    }
    
    return mock_data


@router.post("/events/publish")
async def publish_event(event_data: Dict[str, Any]):
    """Publish event for testing."""
    return {
        "success": True,
        "message": "Event published successfully",
        "event_id": f"evt_{int(time.time())}",
        "timestamp": time.time()
    }


@router.get("/events/subscribe/{event_type}")
async def subscribe_event(event_type: str):
    """Subscribe to event for testing."""
    return {
        "subscribed": True,
        "event_type": event_type,
        "subscription_id": f"sub_{int(time.time())}",
        "timestamp": time.time()
    }


@router.get("/monitoring/collection-status")
async def get_collection_status():
    """Get collection status for testing."""
    return {
        "running": True,
        "total_collections": random.randint(100, 1000),
        "last_collection": time.time() - random.randint(60, 3600),
        "active_symbols": ["AAPL", "GOOGL", "MSFT", "AMZN"],
        "timestamp": time.time()
    }


@router.post("/monitoring/trigger-collection")
async def trigger_collection():
    """Trigger collection for testing."""
    return {
        "triggered": True,
        "message": "Collection triggered successfully",
        "collection_id": f"col_{int(time.time())}",
        "timestamp": time.time()
    }


@router.get("/cache/warming-status")
async def get_cache_warming_status():
    """Get cache warming status for testing."""
    return {
        "active": True,
        "warmed_keys": random.randint(50, 200),
        "total_keys": random.randint(100, 500),
        "last_warming": time.time() - random.randint(300, 1800),
        "timestamp": time.time()
    }


@router.get("/cache/distributed-status")
async def get_distributed_cache_status():
    """Get distributed cache status for testing."""
    return {
        "nodes": random.randint(2, 5),
        "active_nodes": random.randint(2, 5),
        "total_memory": random.randint(1024, 4096),
        "used_memory": random.randint(512, 2048),
        "timestamp": time.time()
    }


@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    """Get monitoring dashboard data for testing."""
    return {
        "widgets": {
            "cpu_usage": random.uniform(20, 80),
            "memory_usage": random.uniform(30, 70),
            "disk_usage": random.uniform(40, 60),
            "network_io": random.uniform(10, 100)
        },
        "alerts": [
            {
                "severity": "info",
                "message": "System running normally",
                "timestamp": time.time() - random.randint(60, 300)
            }
        ],
        "timestamp": time.time()
    }


@router.get("/monitoring/metrics")
async def get_metrics():
    """Get system metrics for testing."""
    return {
        "cpu_usage": round(random.uniform(20, 80), 2),
        "memory_usage": round(random.uniform(30, 70), 2),
        "disk_usage": round(random.uniform(40, 60), 2),
        "network_io": round(random.uniform(10, 100), 2),
        "uptime": random.randint(3600, 86400),
        "timestamp": time.time()
    }


@router.get("/monitoring/logging-status")
async def get_logging_status():
    """Get logging status for testing."""
    return {
        "structured_logging": True,
        "log_level": "INFO",
        "log_storage": "redis",
        "total_logs": random.randint(1000, 10000),
        "logs_per_second": round(random.uniform(1, 10), 2),
        "timestamp": time.time()
    }


@router.post("/monitoring/log")
async def create_log(log_data: Dict[str, Any]):
    """Create log entry for testing."""
    return {
        "success": True,
        "message": "Log created successfully",
        "log_id": f"log_{int(time.time())}",
        "timestamp": time.time()
    }


@router.get("/monitoring/logs")
async def get_logs(limit: int = 10):
    """Get logs for testing."""
    logs = []
    for i in range(min(limit, 50)):
        logs.append({
            "id": f"log_{int(time.time()) - i}",
            "level": random.choice(["INFO", "WARNING", "ERROR"]),
            "message": f"Test log message {i}",
            "timestamp": time.time() - i * 60,
            "component": random.choice(["api", "cache", "database", "auth"])
        })
    
    return {
        "logs": logs,
        "total_count": len(logs),
        "timestamp": time.time()
    }