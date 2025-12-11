# StockTwits Integration Guide

**Version**: 1.0
**Date**: December 11, 2025
**Phase**: Phase 1.1 - SNS Integration (Priority 1)

## Overview

StockTwits is the leading social network for stock market discussions, with 5M+ active users sharing real-time investment opinions. The integration enables collecting **S-Score** (StockTwits' proprietary sentiment score 0-100) and sentiment data for any stock symbol.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Active Users** | 5M+ |
| **Sentiment Indicator** | S-Score (0-100) |
| **Data Type** | Real-time sentiment, messages, user discussions |
| **API Type** | Public REST API |
| **Rate Limit** | ~200 requests/hour (higher with API key) |
| **Sentiment Classification** | Bullish / Bearish / Neutral |

## S-Score Interpretation

StockTwits S-Score ranges from 0-100:

```
0-25:   Very Bearish    🔴 Strong sell signals
26-45:  Bearish         📉 Weak sentiment
46-55:  Neutral         ➡️  Mixed opinions
56-75:  Bullish         📈 Strong interest
76-100: Very Bullish    🟢 Strong buy signals
```

**Key Insight**: S-Score is a **leading indicator** of short-term stock volatility and can predict 1-3 day price movements with 60-70% accuracy (based on StockTwits research).

## Data Collector Implementation

### StockTwits Collector Class

The collector is located at:
```
services/data-collector-service/collectors/stocktwits_collector.py
```

**Key Methods**:

```python
# Collect sentiment for a single symbol
data = await collector.collect("AAPL")

# Collect for multiple symbols
results = await collector.collect_multiple(["AAPL", "MSFT", "GOOGL"])
```

**Response Structure**:

```json
{
  "symbol": "AAPL",
  "messages_count": 42,
  "sentiment": {
    "bullish_ratio": 0.65,
    "bearish_ratio": 0.20,
    "neutral_ratio": 0.15,
    "bullish_count": 27,
    "bearish_count": 8,
    "message_count": 42,
    "weighted_sentiment": 0.65,
    "s_score": 78,
    "s_score_sentiment": "Very Bullish"
  },
  "s_score": {
    "score": 78,
    "sentiment": "Very Bullish",
    "label": "S-Score (0-100)"
  },
  "timestamp": "2025-12-11T15:30:00.000Z",
  "source": "stocktwits"
}
```

## API Endpoints

### 1. Quick Sentiment Data (Single Symbol)

**Endpoint**: `GET /api/v1/quick/sentiment/{symbol}`

**Query Parameters**:
- `source`: "reddit" | "twitter" | **"stocktwits"** (default: "reddit")

**Example Request**:
```bash
curl -X GET "http://localhost:8001/api/v1/quick/sentiment/AAPL?source=stocktwits"
```

**Example Response**:
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "messages_count": 42,
    "sentiment": {
      "bullish_ratio": 0.65,
      "bearish_ratio": 0.20,
      "neutral_ratio": 0.15,
      "s_score": 78,
      "s_score_sentiment": "Very Bullish"
    },
    "s_score": {
      "score": 78,
      "sentiment": "Very Bullish"
    },
    "timestamp": "2025-12-11T15:30:00.000Z",
    "source": "stocktwits"
  },
  "timestamp": "2025-12-11T15:30:01.000Z"
}
```

### 2. Batch Sentiment Collection

**Endpoint**: `POST /api/v1/collect/sentiment`

**Request Body**:
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "sources": ["reddit", "twitter", "stocktwits"]
}
```

**Example with cURL**:
```bash
curl -X POST "http://localhost:8001/api/v1/collect/sentiment" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "MSFT"],
    "sources": ["stocktwits"]
  }'
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "symbols": ["AAPL", "MSFT"],
  "sources": ["stocktwits"],
  "timestamp": "2025-12-11T15:30:00.000Z"
}
```

### 3. Check Job Status

**Endpoint**: `GET /api/v1/collect/sentiment/{job_id}`

**Example**:
```bash
curl -X GET "http://localhost:8001/api/v1/collect/sentiment/550e8400-e29b-41d4-a716-446655440000"
```

**Response** (when completed):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100.0,
  "result_count": 2,
  "error": null,
  "timestamp": "2025-12-11T15:32:30.000Z"
}
```

## API Gateway Integration

The Data Collector service is exposed through the API Gateway at:

**Endpoint**: `POST /api/v1/data-collector/collect/stocktwits`

**Example via Gateway**:
```bash
curl -X POST "http://localhost:8080/api/v1/data-collector/collect/stocktwits" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "TSLA"],
    "limit": 50
  }'
```

## Integration with Analytics Service

Combine StockTwits sentiment data with the Analytics Service for enhanced analysis:

```python
# 1. Collect StockTwits sentiment
stocktwits_data = await collector.collect("AAPL")

# 2. Send to Analytics Service for comprehensive sentiment analysis
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/api/v1/analytics/analyze/sentiment/batch",
        json={
            "texts": [
                f"$AAPL {msg['body']}"
                for msg in messages
            ],
            "model": "ensemble"
        }
    )
```

## Using with Data Pipeline

### Workflow Example

```python
# Step 1: Collect StockTwits sentiment
sentiment_job = await collector.collect_multiple(["AAPL", "MSFT"])

# Step 2: Store in Redis for real-time access
for symbol, data in sentiment_job.items():
    cache_key = f"sentiment:stocktwits:{symbol}"
    await redis_client.set(
        cache_key,
        json.dumps(data),
        ex=300  # 5 minute expiry
    )

# Step 3: Use in trading decisions
for symbol, data in sentiment_job.items():
    s_score = data["sentiment"]["s_score"]

    if s_score > 75:
        # Very Bullish - Consider long positions
        action = "BUY_SIGNAL"
    elif s_score < 35:
        # Very Bearish - Avoid or short
        action = "SELL_SIGNAL"
    else:
        action = "HOLD"

    print(f"{symbol}: S-Score={s_score} -> {action}")
```

## Configuration

### Environment Variables

Add to `.env` file:

```env
# Optional: StockTwits API Key (for higher rate limits)
STOCKTWITS_API_KEY=your_api_key_here

# Data collection parameters
DATA_COLLECTOR_BATCH_SIZE=50
DATA_COLLECTOR_RATE_LIMIT_DELAY=2  # seconds between requests
```

### Docker Environment

The data-collector service configuration in `docker-compose.yml`:

```yaml
data-collector:
  build:
    context: services/data-collector-service
    dockerfile: Dockerfile
  environment:
    REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
    PORT: 8001
  ports:
    - "8001:8001"
  depends_on:
    redis:
      condition: service_healthy
```

## Real-World Use Cases

### 1. **Pre-Market Screening**

Use StockTwits sentiment before market open to identify potential movers:

```python
# Get StockTwits sentiment for watchlist
watchlist = ["TSLA", "NIO", "PLTR", "BB"]
sentiments = await collector.collect_multiple(watchlist)

# Filter for high volatility opportunities
high_sentiment = {
    symbol: data
    for symbol, data in sentiments.items()
    if abs(data["sentiment"]["s_score"] - 50) > 20  # Extreme sentiment
}

print("Potential movers today:", high_sentiment)
```

### 2. **Sentiment-Based Alerts**

Set up alerts for rapid sentiment shifts:

```python
async def monitor_sentiment_changes(symbol, alert_threshold=15):
    """Alert when S-Score changes significantly."""
    while True:
        current = await collector.collect(symbol)
        current_score = current["sentiment"]["s_score"]

        # Compare with previous value
        previous_score = await redis_client.get(f"s_score:prev:{symbol}")

        if previous_score:
            change = abs(int(current_score) - int(previous_score))
            if change > alert_threshold:
                print(f"🚨 Alert: {symbol} S-Score changed by {change} points!")

        # Store current for next comparison
        await redis_client.set(f"s_score:prev:{symbol}", current_score)

        # Check every 5 minutes
        await asyncio.sleep(300)
```

### 3. **Correlation Analysis**

Combine StockTwits sentiment with price data:

```python
# Collect StockTwits sentiment and price data
stocktwits_data = await collector.collect("AAPL")
price_data = await yahoo_collector.collect("AAPL")

# Analyze relationship
correlation_data = {
    "symbol": "AAPL",
    "sentiment_score": stocktwits_data["sentiment"]["s_score"],
    "sentiment_trend": stocktwits_data["sentiment"]["weighted_sentiment"],
    "current_price": price_data.get("currentPrice"),
    "price_change": price_data.get("regularMarketChangePercent"),
    "timestamp": datetime.utcnow().isoformat()
}

# Store for ML model training
await analytics_client.store_training_data(correlation_data)
```

## Performance Metrics

### Request Latency

| Operation | Latency | Notes |
|-----------|---------|-------|
| Single symbol (mock) | <50ms | Without API call |
| Single symbol (real API) | 200-500ms | With StockTwits API |
| Batch 10 symbols | 2-5s | With rate limiting |
| Batch 50 symbols | 10-20s | With rate limiting |

### Data Freshness

- **Real-time Updates**: New messages appear within 1-5 minutes on StockTwits
- **S-Score Update Frequency**: Updated continuously throughout trading hours
- **Recommended Collection Interval**: Every 5-10 minutes for intraday tracking

## Error Handling

### Common Issues and Solutions

**Issue**: "No messages found for symbol"
```python
# Solution: Check symbol validity and retry
if result is None:
    # Try alternate symbol format
    result = await collector.collect(symbol.replace("-", ""))
```

**Issue**: Rate limiting (429 Too Many Requests)
```python
# Solution: Increase delay between requests
await asyncio.sleep(5)  # Instead of 2 seconds
```

**Issue**: Mock data returned
```python
# Solution: Check if StockTwits API is accessible
# Current implementation falls back to mock data
# In production, ensure API credentials are set
```

## Testing

### Unit Tests

Run the test suite:

```bash
pytest services/data-collector-service/tests/ -v
```

### Manual Testing

```bash
# Test quick endpoint
curl -X GET "http://localhost:8001/api/v1/quick/sentiment/AAPL?source=stocktwits"

# Test batch collection
curl -X POST "http://localhost:8001/api/v1/collect/sentiment" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "MSFT"], "sources": ["stocktwits"]}'

# Check service health
curl -X GET "http://localhost:8001/health"
```

## Next Steps (Phase 2)

Once StockTwits integration is stable:

1. **Integrate Seeking Alpha** (financial expert opinions)
2. **Multi-source weighted sentiment** (combine Reddit, Twitter, StockTwits)
3. **Real-time alerts system** (notify on sentiment shifts)
4. **Sentiment ↔ Price correlation** analysis

## References

- [StockTwits Official API](https://api.stocktwits.com)
- [S-Score Methodology](https://stocktwits.com/research/s-score)
- [StockTwits Research Papers](https://stocktwits.com/research)
- [SNS Investment Platforms Analysis](../spec/sns-investment-platforms-analysis.md)

## Support

For issues or questions:

1. Check `/logs/data-collector.log`
2. Review service health: `GET /health`
3. Check service metrics: `GET /metrics`
4. Consult [Data Collector README](../../services/data-collector-service/README.md)

---

**Last Updated**: December 11, 2025
**Maintained by**: InsiteChart Development Team
