# Data Collector Service

Microservice for collecting financial data from multiple sources:
- **Yahoo Finance**: Stock prices, market data, fundamental data
- **Reddit**: Sentiment analysis from r/stocks, r/investing
- **Twitter/X**: Real-time sentiment from financial discussions

## Features

- **Multi-source data collection**: Simultaneously collect from Yahoo Finance, Reddit, and Twitter
- **Job-based background processing**: Asynchronous collection jobs with progress tracking
- **Redis caching**: Cache collected data for improved performance
- **Health checks**: Built-in health check and metrics endpoints
- **Docker support**: Full containerization with health checks

## API Endpoints

### Health & Metrics
- `GET /health` - Service health check
- `GET /metrics` - Service metrics (active jobs, cache stats)

### Stock Collection
- `POST /api/v1/collect/stocks` - Start background job to collect stock data
- `GET /api/v1/collect/stocks/{job_id}` - Get job status
- `GET /api/v1/quick/stock/{symbol}` - Quickly get data for a single stock

### Sentiment Collection
- `POST /api/v1/collect/sentiment` - Start background job to collect sentiment
- `GET /api/v1/collect/sentiment/{job_id}` - Get job status
- `GET /api/v1/quick/sentiment/{symbol}` - Quickly get sentiment for a single stock

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Docker

```bash
# Build image
docker build -t data-collector-service .

# Run container
docker run -d \
  -p 8001:8001 \
  -e REDIS_URL=redis://redis:6379 \
  data-collector-service
```

## Configuration

Environment variables:
- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379)
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage Examples

### Collect Stock Data
```bash
curl -X POST http://localhost:8001/api/v1/collect/stocks \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "GOOGL", "MSFT"],
    "priority": "HIGH"
  }'

# Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "symbols": ["AAPL", "GOOGL", "MSFT"],
  "priority": "HIGH"
}
```

### Check Job Status
```bash
curl http://localhost:8001/api/v1/collect/stocks/550e8400-e29b-41d4-a716-446655440000

# Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100.0,
  "result_count": 3
}
```

### Quick Stock Data
```bash
curl http://localhost:8001/api/v1/quick/stock/AAPL

# Response:
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "price": 189.45,
    "open": 188.50,
    ...
  }
}
```

### Collect Sentiment
```bash
curl -X POST http://localhost:8001/api/v1/collect/sentiment \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "TSLA"],
    "sources": ["reddit", "twitter"]
  }'
```

## Integration with API Gateway

This service is designed to be called through the API Gateway. The gateway handles:
- Routing
- Rate limiting
- Circuit breaking
- Load balancing

Example configuration:
```yaml
routes:
  - path: /api/v1/collect
    service: data-collector
    url: http://data-collector:8001
    timeout: 60
    rate_limit: 50 requests per minute
```

## Development

```bash
# Install development dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Architecture

The service uses:
- **FastAPI**: High-performance async web framework
- **Pydantic**: Data validation and serialization
- **Redis**: Distributed caching and job tracking
- **aiohttp/httpx**: Async HTTP clients for external APIs

## Data Flow

```
Client Request
    ↓
API Gateway
    ↓
Data Collector Service
    ├─ Yahoo Finance Collector
    ├─ Reddit Collector
    └─ Twitter Collector
    ↓
Redis Cache
    ↓
Response to Client
```

## License

Part of InsiteChart platform.
