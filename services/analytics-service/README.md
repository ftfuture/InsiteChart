# Analytics Service

Sentiment, Correlation, and Trend Analysis Microservice for InsiteChart financial data platform.

## Overview

Analytics Service is a specialized microservice that provides advanced financial analysis capabilities:

- **Sentiment Analysis**: VADER + BERT ensemble model for accurate sentiment scoring
- **Correlation Analysis**: Pearson correlation analysis for portfolio diversification
- **Trend Analysis**: Support/resistance detection, moving averages, RSI, anomaly detection

## Features

### 1. Sentiment Analysis
- **Models**: VADER, BERT, or Ensemble
- **Input**: Text analysis for any content (news, social media, etc.)
- **Output**: Sentiment scores (positive, negative, neutral, compound) + confidence

```bash
curl -X POST http://localhost:8002/api/v1/analyze/sentiment \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "text": "Apple stock looks great!",
    "model": "ensemble"
  }'
```

### 2. Correlation Analysis
- **Function**: Analyze relationships between stocks
- **Output**: Correlation matrix + strong/weak pairs
- **Period Support**: 1d, 1w, 1mo, 3mo, 6mo, 1y

```bash
curl -X POST http://localhost:8002/api/v1/analyze/correlation \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "period": "1mo"
  }'
```

### 3. Trend Analysis
- **Indicators**: Moving averages (SMA 50/200), RSI, support/resistance
- **Trend Detection**: Uptrend, Downtrend, Sideways
- **Anomaly Detection**: Price spikes and drops

```bash
curl -X POST http://localhost:8002/api/v1/analyze/trends \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "lookback_days": 30,
    "include_anomalies": true
  }'
```

## Installation

### Requirements
- Python 3.11+
- pip or poetry

### Local Development

1. **Clone the repository**
```bash
cd services/analytics-service
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download NLTK data (for VADER)**
```bash
python -c "import nltk; nltk.download('vader_lexicon')"
```

5. **Run the service**
```bash
python main.py
```

Service will be available at http://localhost:8002

### Docker Deployment

1. **Build image**
```bash
docker build -t insitechart-analytics:latest .
```

2. **Run container**
```bash
docker run -d \
  -p 8002:8002 \
  -e REDIS_URL=redis://localhost:6379 \
  --name analytics-service \
  insitechart-analytics:latest
```

3. **Health check**
```bash
curl http://localhost:8002/health
```

## API Endpoints

### Sentiment Analysis

#### POST /api/v1/analyze/sentiment
Analyze sentiment of text.

**Request**:
```json
{
  "symbol": "AAPL",
  "text": "Great product launch",
  "sources": ["twitter", "reddit"],
  "model": "ensemble"
}
```

**Response**:
```json
{
  "symbol": "AAPL",
  "sentiment": {
    "compound": 0.65,
    "positive": 0.72,
    "negative": 0.15,
    "neutral": 0.13,
    "confidence": 0.92,
    "model": "ensemble",
    "sentiment": "positive"
  },
  "timestamp": "2025-12-11T10:30:00Z"
}
```

#### POST /api/v1/analyze/sentiment/batch
Batch sentiment analysis (max 100 texts).

**Query Parameters**:
- `texts`: List of texts to analyze
- `model`: vader | bert | ensemble (default: ensemble)

### Correlation Analysis

#### POST /api/v1/analyze/correlation
Analyze correlations between stocks.

**Request**:
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "period": "1mo",
  "include_market": true
}
```

**Response**:
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "period": "1mo",
  "correlation_matrix": [[1.0, 0.85, 0.78], ...],
  "strong_pairs": [
    {
      "symbol1": "AAPL",
      "symbol2": "MSFT",
      "coefficient": 0.85,
      "p_value": 0.001,
      "strength": "strong"
    }
  ],
  "weak_pairs": [],
  "statistics": {
    "mean_correlation": 0.76,
    "max_correlation": 0.85,
    "min_correlation": 0.65
  },
  "timestamp": "2025-12-11T10:30:00Z"
}
```

#### GET /api/v1/analyze/correlation/rolling
Get rolling correlation between two symbols.

**Query Parameters**:
- `symbol1`: First symbol
- `symbol2`: Second symbol
- `window_days`: Rolling window (default: 30)
- `period`: Total period (default: 1mo)

### Trend Analysis

#### POST /api/v1/analyze/trends
Analyze price trends.

**Request**:
```json
{
  "symbol": "AAPL",
  "lookback_days": 30,
  "include_anomalies": true
}
```

**Response**:
```json
{
  "symbol": "AAPL",
  "trend": "uptrend",
  "strength": 0.85,
  "current_price": 182.45,
  "support_levels": [150.0, 148.5],
  "resistance_levels": [165.0, 167.5],
  "moving_averages": {
    "SMA_50": 155.5,
    "SMA_200": 148.2
  },
  "rsi": 65.5,
  "anomalies": [
    {
      "timestamp": "2025-12-10T10:30:00Z",
      "price": 162.5,
      "magnitude": 2.5,
      "type": "spike"
    }
  ],
  "timestamp": "2025-12-11T10:30:00Z"
}
```

#### POST /api/v1/analyze/trends/batch
Batch trend analysis (max 50 symbols).

**Query Parameters**:
- `symbols`: List of symbols
- `lookback_days`: Days of history (5-365, default: 30)

### Health and Info

#### GET /health
Health check endpoint.

#### GET /info
Service information.

#### GET /
Root endpoint.

## Configuration

### Environment Variables

```env
# Service Port
PORT=8002
HOST=0.0.0.0

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379
REDIS_DB=1

# Logging
LOG_LEVEL=INFO

# Model Configuration
BERT_MODEL=distilbert-base-uncased-finetuned-sst-2-english
SENTIMENT_BATCH_SIZE=32
```

## Architecture

```
analytics-service/
├── main.py                      # FastAPI application
├── analyzers/
│   ├── sentiment_analyzer.py    # VADER + BERT sentiment
│   ├── correlation_analyzer.py  # Correlation analysis
│   ├── trend_analyzer.py        # Trend & anomaly detection
│   └── ml_models/               # Pre-trained models
├── models/
│   └── analysis_models.py       # Pydantic schemas
├── tests/
│   └── ...                      # Unit tests
├── requirements.txt             # Dependencies
├── Dockerfile                   # Container image
└── README.md
```

## Performance Considerations

### Optimization Tips

1. **Sentiment Analysis**
   - VADER is fast (~1-5ms per text)
   - BERT is slower (~50-200ms per text)
   - Use ensemble for balanced accuracy/speed

2. **Correlation Analysis**
   - Cached for repeated requests
   - Use shorter periods for faster computation
   - Max 50 symbols per request

3. **Trend Analysis**
   - Uses efficient NumPy operations
   - Isolation Forest for anomaly detection
   - Batch processing for multiple symbols

### Caching Strategy

- Redis caching for correlation matrices
- BERT model loaded once on startup
- Result caching with TTL

### Resource Requirements

| Component | Memory | CPU | Notes |
|-----------|--------|-----|-------|
| Base Service | 256MB | 1 core | Minimal overhead |
| BERT Model | 500MB | 1-2 cores | Loaded on startup |
| Redis Cache | Variable | Minimal | Optional |

## Testing

### Run Tests
```bash
pytest tests/ -v
```

### Coverage
```bash
pytest tests/ --cov=analyzers --cov-report=html
```

### Test Examples

```python
# Sentiment Analysis
analyzer = SentimentAnalyzer()
result = analyzer.analyze("Great product!", model="ensemble")

# Correlation Analysis
analyzer = CorrelationAnalyzer()
result = analyzer.analyze(
    symbols=["AAPL", "MSFT"],
    period="1mo"
)

# Trend Analysis
analyzer = TrendAnalyzer()
result = analyzer.analyze(symbol="AAPL", lookback_days=30)
```

## Monitoring

### Prometheus Metrics
- `sentiment_analysis_duration_seconds`: Analysis execution time
- `correlation_analysis_duration_seconds`: Analysis execution time
- `trend_analysis_duration_seconds`: Analysis execution time
- `analyzer_requests_total`: Total requests per analyzer

### Health Checks
- `/health`: Returns service status and dependency health
- Includes BERT model availability check
- Dependency status (redis, transformers, etc.)

## Contributing

1. Create feature branch: `git checkout -b feature/analytics-xyz`
2. Make changes following code style
3. Add tests for new functionality
4. Push and create pull request

## Performance Benchmarks

### Single Request Latency

| Operation | Model | Latency |
|-----------|-------|---------|
| Sentiment | VADER | ~5ms |
| Sentiment | BERT | ~150ms |
| Sentiment | Ensemble | ~160ms |
| Correlation | 10 symbols | ~50ms |
| Trend | Single symbol | ~30ms |
| Trend Batch | 50 symbols | ~1500ms |

### Throughput

- Sentiment: ~200 req/s (VADER), ~10 req/s (BERT)
- Correlation: ~100 req/s
- Trend: ~50 req/s

## Troubleshooting

### BERT Model Download Issues

If BERT model fails to download:

```bash
# Download manually
python -c "from transformers import AutoModel; AutoModel.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')"
```

### Memory Issues

- Reduce batch sizes
- Use VADER model only
- Implement request queuing

### Correlation Data Issues

- Ensure symbols exist in data provider
- Check period validity
- Verify sufficient historical data

## License

MIT - Part of InsiteChart project

## Version History

- **1.0.0** (2025-12-11): Initial release
  - Sentiment analysis (VADER + BERT)
  - Correlation analysis with rolling calculations
  - Trend analysis with anomaly detection
  - Batch processing endpoints
  - Docker support

## Next Steps

- [ ] Kafka event streaming integration
- [ ] Advanced ML models (LLMs for sentiment)
- [ ] Real-time data provider integration
- [ ] WebSocket streaming endpoints
- [ ] Caching layer optimization
