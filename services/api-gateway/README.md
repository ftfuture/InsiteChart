# API Gateway

Central API Gateway for InsiteChart microservices. Provides unified access point to:
- Analytics Service (port 8002)
- Data Collector Service (port 8001)
- Backend Services (port 8000)

## Features

- **Request Routing**: Smart routing to appropriate microservices
- **Authentication**: JWT token-based authentication
- **Rate Limiting**: Per-user and per-IP rate limiting (minute, hour, day)
- **Request Logging**: Detailed logging with request IDs
- **Service Discovery**: Automatic health checks for microservices
- **Error Handling**: Unified error responses

## Architecture

```
API Gateway (Port 8080)
├── Authentication Middleware (JWT)
├── Rate Limiting Middleware
├── Request Logging Middleware
├── Service Discovery & Health Checks
└── Routes
    ├── Analytics Service (8002)
    ├── Data Collector Service (8001)
    └── Backend Services (8000)
```

## Installation

### Local Development

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Run the gateway**
```bash
python main.py
```

Gateway available at `http://localhost:8080`

### Docker

```bash
# Build image
docker build -t insitechart-gateway:latest .

# Run container
docker run -d \
  -p 8080:8080 \
  -e BACKEND_URL=http://backend:8000 \
  -e DATA_COLLECTOR_URL=http://data-collector:8001 \
  -e ANALYTICS_URL=http://analytics:8002 \
  --name api-gateway \
  insitechart-gateway:latest
```

## Configuration

### Environment Variables

```env
# Server
PORT=8080
HOST=0.0.0.0

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# Rate Limiting
RATE_LIMIT_MINUTE=60
RATE_LIMIT_HOUR=1000
RATE_LIMIT_DAY=10000

# Microservices
BACKEND_URL=http://localhost:8000
DATA_COLLECTOR_URL=http://localhost:8001
ANALYTICS_URL=http://localhost:8002

# Logging
LOG_LEVEL=INFO
```

## API Endpoints

### Authentication

#### POST /auth/token
Get JWT access token.

```bash
curl -X POST http://localhost:8080/auth/token \
  -d "username=demo_user&password=demo_password"
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### GET /auth/users
List available demo users.

### System Endpoints

#### GET /
Root endpoint with gateway info.

#### GET /health
Check gateway and microservices health.

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "services": [
    {
      "name": "analytics",
      "url": "http://localhost:8002",
      "status": "healthy",
      "response_time_ms": 45.5
    }
  ]
}
```

#### GET /status
Detailed gateway status.

#### GET /info
Gateway information and endpoints.

### Analytics Service Routes

#### POST /api/v1/analytics/analyze/sentiment
Analyze sentiment of text.

```bash
curl -X POST http://localhost:8080/api/v1/analytics/analyze/sentiment \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "text": "Great product launch!",
    "model": "ensemble"
  }'
```

#### POST /api/v1/analytics/analyze/correlation
Analyze stock correlations.

```bash
curl -X POST http://localhost:8080/api/v1/analytics/analyze/correlation \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "period": "1mo"
  }'
```

#### POST /api/v1/analytics/analyze/trends
Analyze price trends.

```bash
curl -X POST http://localhost:8080/api/v1/analytics/analyze/trends \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "lookback_days": 30,
    "include_anomalies": true
  }'
```

### Data Collector Service Routes

#### POST /api/v1/data-collector/collect/yahoo-finance
Collect Yahoo Finance data.

```bash
curl -X POST "http://localhost:8080/api/v1/data-collector/collect/yahoo-finance?symbols=AAPL&symbols=MSFT"
```

#### POST /api/v1/data-collector/collect/reddit
Collect Reddit sentiment data.

#### POST /api/v1/data-collector/collect/twitter
Collect Twitter sentiment data.

## Authentication

### Using JWT Tokens

1. **Get token**:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/auth/token \
  -d "username=demo_user&password=demo_password" \
  | jq -r '.access_token')
```

2. **Use in requests**:
```bash
curl -X GET http://localhost:8080/api/v1/analytics/status \
  -H "Authorization: Bearer $TOKEN"
```

### Demo Users

- Username: `demo_user`, Password: `demo_password`
- Username: `admin`, Password: `admin_password`

## Rate Limiting

Rate limits are applied per user (if authenticated) or per IP:

- **Per Minute**: 60 requests
- **Per Hour**: 1,000 requests
- **Per Day**: 10,000 requests

Rate limit info in response headers:
```
X-RateLimit-Limit-Minute: 60
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Reset-Minute: 2025-12-11T10:31:00Z
```

Error when limit exceeded:
```json
{
  "detail": "Rate limit exceeded (minute). Reset at 2025-12-11T10:31:00Z"
}
```

## Request/Response

All gateway responses have consistent structure:

```json
{
  "service": "analytics",
  "status_code": 200,
  "data": {
    "symbol": "AAPL",
    "sentiment": {...}
  },
  "error": null,
  "timestamp": "2025-12-11T10:30:00Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Error Handling

Errors follow standard format:

```json
{
  "error": "Unauthorized",
  "error_code": "AUTH_001",
  "message": "Invalid or missing authentication token",
  "details": {...},
  "timestamp": "2025-12-11T10:30:00Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Common error codes:
- `HTTP_400`: Bad Request
- `HTTP_401`: Unauthorized
- `HTTP_403`: Forbidden
- `HTTP_404`: Not Found
- `HTTP_429`: Rate Limit Exceeded
- `HTTP_503`: Service Unavailable
- `HTTP_504`: Gateway Timeout

## Service Discovery

The gateway automatically:
- Discovers registered microservices
- Performs periodic health checks
- Updates service status in real-time
- Routes requests only to healthy services

Health check interval: 30 seconds (configurable)

## Logging

All requests are logged with:
- Unique request ID
- HTTP method and path
- Response time
- Status code
- Client IP
- User agent
- Errors (if any)

View logs:
```bash
# Real-time logs
docker logs -f api-gateway

# Filter by level
docker logs api-gateway | grep ERROR
```

## Monitoring

### Health Check

```bash
curl http://localhost:8080/health
```

### Metrics (Prometheus compatible)

Endpoint: `/metrics` (available in extended version)

Metrics:
- Request count per service
- Response time percentiles (p50, p95, p99)
- Error rates
- Service availability

## Testing

### Run tests

```bash
pytest tests/ -v
```

### Coverage

```bash
pytest tests/ --cov=. --cov-report=html
```

## Performance

### Latency

- Gateway overhead: ~5-10ms
- Total request time depends on backend service

### Throughput

- Handles 1000+ requests per second (depending on backend)
- Scales with asyncio and uvicorn workers

### Optimization Tips

1. **Increase workers**: `uvicorn main:app --workers 4`
2. **Enable caching**: Configure Redis for response caching
3. **Load balancing**: Deploy multiple gateway instances behind load balancer
4. **Connection pooling**: Reuse HTTP connections to backend services

## Troubleshooting

### Service Not Available

Check service health:
```bash
curl http://localhost:8080/health
```

Ensure backend services are running on configured ports.

### Rate Limited

Check remaining requests:
```bash
curl -i http://localhost:8080/api/v1/analytics/analyze/sentiment
# Look for X-RateLimit headers
```

### Authentication Failed

Verify token:
1. Get new token: `curl -X POST http://localhost:8080/auth/token ...`
2. Use in Authorization header: `Authorization: Bearer <token>`

### Timeout Issues

Increase timeout in gateway for slow services:
- Edit `timeout=` in route handlers
- Increase backend service responsiveness

## Contributing

1. Create feature branch: `git checkout -b feature/gateway-xyz`
2. Make changes
3. Add tests
4. Submit pull request

## License

MIT - Part of InsiteChart project

## Next Steps

- [ ] Add backend service routes
- [ ] Implement caching layer (Redis)
- [ ] Add metrics/monitoring (Prometheus)
- [ ] Implement circuit breaker pattern
- [ ] Add API versioning support
- [ ] Implement webhooks for events
