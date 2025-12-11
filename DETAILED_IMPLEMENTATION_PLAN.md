# InsiteChart 상세 구현 계획서 (Detailed Implementation Plan)

**작성일**: 2025년 12월 11일
**버전**: 1.0
**상태**: 진행 중
**총 작업 항목**: 62개

---

## 📋 목차

1. [개요](#개요)
2. [PRIORITY 1 - 즉시 필수 완료](#priority-1---즉시-필수-완료-5개-phase)
3. [PRIORITY 2 - 중기 완료](#priority-2---중기-완료-3-4개월)
4. [PRIORITY 3 - 장기 고도화](#priority-3---장기-고도화-5-8개월-이상)
5. [작업 의존성](#작업-의존성)
6. [위험 분석](#위험-분석)
7. [성공 기준](#성공-기준)

---

## 개요

InsiteChart는 현재 **75-85% 완성도**의 금융 분석 플랫폼입니다.

**현재 상태**:
- ✅ 코어 기능 구현됨 (주식 데이터, 기본 센티먼트 분석)
- ⚠️ 실시간 데이터 동기화 부분 구현 (WebSocket 있지만 실제 작동 안 함)
- ❌ 마이크로서비스 분리 미구현 (여전히 모놀리식)
- ❌ Kafka 메시지 큐 테스트 환경만 구성
- ❌ GDPR 자동화 기본 구조만 구현

본 계획은 62개의 구체적인 작업을 3개 우선순위로 분류하여 단계적으로 구현하기 위한 로드맵입니다.

---

## PRIORITY 1 - 즉시 필수 완료 (4개 Phase)

### 완료 기한: 1-2개월
### 목표: 프로덕션 배포를 위한 핵심 인프라 구축

---

## Phase 1: 실시간 데이터 동기화 시스템 구축

**목표**: 주식 데이터와 센티먼트 분석을 1초 이내 지연시간으로 실시간 전송
**기한**: 2주
**현재 상태**: WebSocket 구조만 있고 실제 동기화 미구현

### 1.1 WebSocket 연결 안정화 및 재연결 메커니즘

**상세 요구사항**:
- 자동 재연결 로직 (exponential backoff: 1s → 2s → 4s → max 30s)
- 연결 끊김 시 자동 재구독
- 하트비트/핑-퐁 메커니즘 (30초 간격)
- 최대 동시 연결: 1000개
- 연결 타임아웃: 60초

**구현 파일**:
- `/home/user/InsiteChart/backend/api/websocket_routes.py` (수정)
  - 현재 상태: 기본 WebSocket 구조만 존재
  - 필요한 추가: 재연결 메커니즘, 하트비트

**기술 스택**:
- WebSockets 11.0
- asyncio 타이밍 관리
- Redis Pub/Sub (브로드캐스트)

**테스트**:
```bash
pytest tests/test_websocket_reconnection.py -v --markers websocket
# 테스트 항목:
# - 정상 연결/해제
# - 강제 연결 끊김 후 자동 재연결
# - 하트비트 타임아웃
# - 최대 연결 수 도달 시 처리
# - 메시지 손실 없음
```

---

### 1.2 실시간 데이터 스트리밍 파이프라인

**상세 요구사항**:
- **주가 데이터**: 5초마다 Yahoo Finance에서 수집 → WebSocket 전송
- **거래량 데이터**: 1분마다 집계
- **센티먼트 업데이트**: 10초마다 (Redis에서 캐시된 데이터)
- 데이터 손실 방지: 각 업데이트에 시퀀스 번호

**구현 단계**:

1. **데이터 수집 스케줄러** (`backend/services/realtime_data_collector.py`):
```python
async def collect_stock_data_periodic():
    """5초마다 Yahoo Finance에서 데이터 수집"""
    while True:
        try:
            for symbol in watched_symbols:
                data = await fetch_yahoo_finance(symbol)
                await cache.set(f"stock:{symbol}", data, ttl=5)
                await publish_to_redis(f"stock_updates:{symbol}", data)
        except Exception as e:
            logger.error(f"Data collection error: {e}")
        await asyncio.sleep(5)

async def collect_sentiment_data_periodic():
    """10초마다 센티먼트 데이터 업데이트"""
    while True:
        try:
            for symbol in watched_symbols:
                sentiment = await cache.get(f"sentiment:{symbol}")
                await publish_to_redis(f"sentiment_updates:{symbol}", sentiment)
        except Exception as e:
            logger.error(f"Sentiment collection error: {e}")
        await asyncio.sleep(10)
```

2. **WebSocket 브로드캐스트**:
```python
async def broadcast_stock_update(symbol: str, data: dict):
    """모든 구독 클라이언트에게 업데이트 전송"""
    key = f"stock_updates:{symbol}"
    await redis_pub_sub.publish(key, json.dumps({
        "type": "stock_update",
        "symbol": symbol,
        "data": data,
        "sequence": next_sequence(),
        "timestamp": datetime.utcnow().isoformat()
    }))
```

**구현 파일**:
- `/home/user/InsiteChart/backend/services/realtime_data_collector.py` (현재 비활성화됨 - 재활성화)
- `/home/user/InsiteChart/backend/main.py` (라인 104 - 비활성화 제거)

**테스트**:
```bash
pytest tests/test_realtime_streaming.py -v
# 테스트 항목:
# - 5초 간격 데이터 수집
# - 데이터 정확성 (Yahoo Finance vs 캐시)
# - 세퀀스 번호 연속성
# - 레이턴시 < 1초
# - 데이터 손실 없음
```

---

### 1.3 Redis Pub/Sub 이벤트 브로드캐스트 시스템

**상세 요구사항**:
- 여러 서버 인스턴스에서 메시지 브로드캐스트
- 메시지 순서 보장
- 구독자 관리 (자동 정리)
- 메시지 재전송 로직 (실패 시)

**구현**:

```python
# Redis Pub/Sub Manager
class RedisPubSubManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.subscriptions = {}  # channel → [callback, ...]

    async def subscribe(self, channel: str, callback):
        """채널 구독"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        self.subscriptions[channel].append(callback)

    async def publish(self, channel: str, message: dict):
        """메시지 발행"""
        serialized = json.dumps({
            **message,
            "sequence": self.get_next_sequence(),
            "timestamp": datetime.utcnow().isoformat(),
            "publisher": get_server_id()
        })
        await self.redis.publish(channel, serialized)

    async def listen(self, channel: str):
        """채널 메시지 수신"""
        async with self.redis.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            while True:
                message = await pubsub.get_message()
                if message and message['type'] == 'message':
                    for callback in self.subscriptions.get(channel, []):
                        await callback(message['data'])
```

**채널 네이밍 컨벤션**:
- `stock_updates:{symbol}` - 주가 업데이트
- `sentiment_updates:{symbol}` - 센티먼트 업데이트
- `alert:{user_id}` - 사용자별 알림
- `system:notifications` - 시스템 알림

**구현 파일**:
- `/home/user/InsiteChart/backend/cache/redis_pubsub_manager.py` (새 파일)

---

### 1.4 동시성 처리 및 메시지 순서 보장

**상세 요구사항**:
- 멀티 스레드/프로세스 환경에서 메시지 순서 유지
- 데이터 경합(race condition) 방지
- 메모리 누수 방지 (long-running async tasks)
- 데드락(deadlock) 방지

**구현 전략**:

```python
# 글로벌 시퀀스 번호 생성기 (Redis 사용 - 분산 환경)
class SequenceGenerator:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def next_sequence(self, key: str = "global_sequence") -> int:
        """분산 환경에서 안전한 시퀀스 번호 생성"""
        # Redis INCR는 atomic operation
        return await self.redis.incr(key)

# 메시지 큐 (순서 보장)
class OrderedMessageQueue:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "message_queue"

    async def enqueue(self, message: dict) -> int:
        """메시지 추가 (순서 보장)"""
        sequence = await SequenceGenerator(self.redis).next_sequence()
        message['_sequence'] = sequence
        await self.redis.rpush(self.queue_key, json.dumps(message))
        return sequence

    async def dequeue(self, timeout=1) -> dict:
        """메시지 추출 (FIFO)"""
        data = await self.redis.blpop(self.queue_key, timeout=timeout)
        return json.loads(data) if data else None
```

**테스트**:
```bash
pytest tests/test_concurrent_messaging.py -v
# 테스트 항목:
# - 1000 동시 연결
# - 메시지 순서 유지 (시퀀스 번호로 검증)
# - 메모리 누수 없음
# - 데드락 없음
```

---

### 1.5 실시간 알림 템플릿 및 다국어 지원

**상세 요구사항**:
- 알림 템플릿 시스템 (동적 변수 치환)
- 13개 언어 지원
- 알림 우선순위 (CRITICAL, HIGH, MEDIUM, LOW)
- 사용자별 알림 설정 저장

**알림 템플릿 예시**:

```json
{
  "template_id": "price_alert",
  "name": "가격 알림",
  "subject": "{stock_symbol} 가격 변동",
  "templates": {
    "en": {
      "subject": "{stock_symbol} Price Alert",
      "body": "{stock_symbol} has moved {change_percent}% to {current_price}",
      "priority": "HIGH"
    },
    "ko": {
      "subject": "{stock_symbol} 가격 알림",
      "body": "{stock_symbol}가 {change_percent}% 변동하여 {current_price}가 되었습니다",
      "priority": "HIGH"
    }
  }
}
```

**구현 파일**:
- `/home/user/InsiteChart/backend/services/notification_template_service.py` (확장)
- `/home/user/InsiteChart/backend/models/database_models.py` (NotificationTemplate 테이블 추가)

**데이터베이스 스키마**:
```sql
CREATE TABLE notification_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(100) UNIQUE,
    name VARCHAR(200),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE notification_translations (
    id SERIAL PRIMARY KEY,
    template_id INT REFERENCES notification_templates(id),
    language VARCHAR(10),  -- 'en', 'ko', etc.
    subject TEXT,
    body TEXT,
    priority VARCHAR(20),  -- 'CRITICAL', 'HIGH', etc.
    UNIQUE(template_id, language)
);

CREATE TABLE user_notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    template_id INT REFERENCES notification_templates(id),
    enabled BOOLEAN DEFAULT TRUE,
    preferred_language VARCHAR(10),
    channels TEXT[],  -- ['email', 'push', 'websocket']
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    UNIQUE(user_id, template_id)
);
```

---

## Phase 2: 마이크로서비스 아키텍처 분리

**목표**: 모놀리식 아키텍처를 마이크로서비스로 분리
**기한**: 4주
**현재 상태**: 서비스 레이어 존재하지만 강하게 결합됨 (모놀리식)

### 2.1 데이터 수집 서비스 독립화

**목표**: 주식 데이터, Reddit 센티먼트, Twitter 센티먼트 수집을 별도 서비스로

**서비스 구조**:

```
data-collector-service/
├─ main.py (FastAPI 앱)
├─ collectors/
│  ├─ yahoo_finance_collector.py
│  ├─ reddit_collector.py
│  ├─ twitter_collector.py
│  └─ news_collector.py
├─ models/
│  └─ collector_models.py
└─ requirements.txt
```

**API 엔드포인트**:
```
POST /api/v1/collect/stocks
Body: { "symbols": ["AAPL", "MSFT"], "priority": "HIGH" }
Response: { "job_id": "uuid", "status": "started" }

GET /api/v1/collect/status/{job_id}
Response: { "job_id": "uuid", "status": "running", "progress": 45 }

POST /api/v1/collect/sentiment
Body: { "symbols": ["AAPL"], "sources": ["reddit", "twitter"] }
```

**통신 방식**:
- 동기: HTTP/REST API
- 비동기: Kafka 메시지 큐 (Phase 4에서 구현)

**구현 세부사항**:

```python
# data-collector-service/main.py
from fastapi import FastAPI
from .collectors import YahooFinanceCollector, RedditCollector

app = FastAPI()
yahoo_collector = YahooFinanceCollector()
reddit_collector = RedditCollector()

@app.post("/api/v1/collect/stocks")
async def collect_stocks(symbols: List[str]):
    """주식 데이터 수집"""
    job_id = str(uuid4())

    # 백그라운드 작업으로 실행
    asyncio.create_task(
        run_collection_job(job_id, symbols)
    )

    return {
        "job_id": job_id,
        "status": "started",
        "symbols": symbols
    }

async def run_collection_job(job_id: str, symbols: List[str]):
    """실제 수집 로직"""
    try:
        results = []
        for symbol in symbols:
            stock_data = await yahoo_collector.collect(symbol)
            await redis.set(f"stock:{symbol}", stock_data)

            # Kafka로 이벤트 발행 (Phase 4)
            # await kafka_producer.send("stock_updates", {
            #     "symbol": symbol,
            #     "data": stock_data,
            #     "timestamp": datetime.utcnow().isoformat()
            # })

            results.append(stock_data)

        # 작업 상태 업데이트
        await redis.set(f"job:{job_id}", {
            "status": "completed",
            "results_count": len(results),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Collection job {job_id} failed: {e}")
        await redis.set(f"job:{job_id}", {
            "status": "failed",
            "error": str(e)
        })
```

**Docker 배포**:
```dockerfile
# data-collector-service/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Docker Compose 추가**:
```yaml
# docker-compose.yml에 추가
data-collector-service:
  build:
    context: ./services/data-collector
  ports:
    - "8001:8000"
  environment:
    - REDIS_URL=redis://redis:6379
    - KAFKA_BROKERS=kafka:9092
  depends_on:
    - redis
    - kafka
  networks:
    - insitechart-network
```

**테스트**:
```bash
# services/data-collector/tests/
pytest test_collectors.py -v --markers collector
# - Yahoo Finance 수집 정확성
# - Reddit 데이터 파싱
# - Twitter 데이터 파싱
# - 에러 처리
# - 재시도 로직
```

---

### 2.2 분석 서비스 분리

**목표**: 센티먼트, 상관관계, 트렌드 분석을 별도 서비스로

**서비스 구조**:

```
analytics-service/
├─ main.py
├─ analyzers/
│  ├─ sentiment_analyzer.py (VADER, BERT)
│  ├─ correlation_analyzer.py
│  ├─ trend_analyzer.py
│  └─ ml_models/
│      ├─ bert_model.py
│      └─ ml_trend_model.py
├─ models/
│  └─ analysis_models.py
└─ requirements.txt
```

**API 엔드포인트**:
```
POST /api/v1/analyze/sentiment
Body: { "symbol": "AAPL", "sources": ["reddit", "twitter"] }
Response: {
  "symbol": "AAPL",
  "sentiment": {
    "compound": 0.65,
    "positive": 0.72,
    "negative": 0.15,
    "neutral": 0.13,
    "confidence": 0.92,
    "model": "bert"
  }
}

POST /api/v1/analyze/correlation
Body: { "symbols": ["AAPL", "MSFT", "GOOGL"], "period": "1mo" }
Response: {
  "correlation_matrix": [[1.0, 0.85, 0.78], ...],
  "strong_pairs": [{"symbol1": "AAPL", "symbol2": "MSFT", "coef": 0.85}]
}

POST /api/v1/analyze/trends
Body: { "symbol": "AAPL", "lookback_days": 30 }
Response: {
  "trend": "uptrend",
  "strength": 0.85,
  "support_levels": [150.0, 148.5],
  "resistance_levels": [165.0, 167.5],
  "anomalies": [{"timestamp": "...", "magnitude": 2.5}]
}
```

**구현 세부사항**:

```python
# analytics-service/analyzers/sentiment_analyzer.py
class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.bert_model = BertForSequenceClassification.from_pretrained(
            'distilbert-base-uncased-finetuned-sst-2-english'
        )

    async def analyze(self, symbol: str, text: str, model: str = "ensemble"):
        """센티먼트 분석 (VADER 또는 BERT)"""
        if model == "vader":
            return await self._analyze_vader(text)
        elif model == "bert":
            return await self._analyze_bert(text)
        else:  # ensemble
            vader_result = await self._analyze_vader(text)
            bert_result = await self._analyze_bert(text)

            # 앙상블: 가중 평균
            return {
                "compound": (vader_result["compound"] + bert_result["score"]) / 2,
                "positive": max(vader_result["pos"], bert_result["positive"]),
                "negative": max(vader_result["neg"], bert_result["negative"]),
                "neutral": vader_result["neu"],
                "confidence": min(vader_result["confidence"], bert_result["confidence"]),
                "model": "ensemble"
            }
```

---

### 2.3 API 게이트웨이 구현 및 라우팅 로직

**목표**: 클라이언트 요청을 올바른 마이크로서비스로 라우팅

**게이트웨이 구조**:

```
api-gateway/
├─ main.py
├─ router.py (라우팅 규칙)
├─ circuit_breaker.py (서킷 브레이커)
├─ rate_limiter.py (분산 레이트 리미팅)
└─ service_registry.py (서비스 디스커버리)
```

**라우팅 규칙 예시**:

```python
# api-gateway/router.py
ROUTE_MAP = {
    "/api/v1/stocks": {
        "service": "backend-api",
        "url": "http://backend-api:8000",
        "timeout": 30,
        "circuit_breaker": True,
        "rate_limit": {"requests": 100, "window": 60}
    },
    "/api/v1/collect": {
        "service": "data-collector",
        "url": "http://data-collector:8001",
        "timeout": 60,
        "circuit_breaker": True,
        "rate_limit": {"requests": 50, "window": 60}
    },
    "/api/v1/analyze": {
        "service": "analytics",
        "url": "http://analytics:8002",
        "timeout": 30,
        "circuit_breaker": True,
        "rate_limit": {"requests": 100, "window": 60}
    }
}

# api-gateway/main.py
class APIGateway(FastAPI):
    async def route_request(self, path: str, method: str, body: dict):
        """요청 라우팅"""
        route_config = self._find_route(path)

        # 서킷 브레이커 체크
        if not self.circuit_breaker.is_healthy(route_config["service"]):
            return {"error": "Service temporarily unavailable"}

        # 레이트 리미팅 체크
        if not self.rate_limiter.allow_request(path):
            return {"error": "Rate limit exceeded"}, 429

        # 백엔드 서비스로 프록시
        try:
            response = await self._proxy_request(
                route_config["url"],
                path,
                method,
                body,
                timeout=route_config["timeout"]
            )
            return response
        except asyncio.TimeoutError:
            self.circuit_breaker.record_failure(route_config["service"])
            return {"error": "Service timeout"}, 504
        except Exception as e:
            logger.error(f"Routing error: {e}")
            return {"error": "Internal server error"}, 500
```

**서킷 브레이커 구현**:

```python
# api-gateway/circuit_breaker.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.services = {}  # service_name → {failures, last_failure, state}

    def is_healthy(self, service_name: str) -> bool:
        """서비스 건강 상태 확인"""
        if service_name not in self.services:
            return True

        service = self.services[service_name]

        # OPEN 상태 (circuit breaker 열림)
        if service["failures"] >= self.failure_threshold:
            # 복구 타임아웃 경과했는지 확인
            if time.time() - service["last_failure"] > self.recovery_timeout:
                service["failures"] = 0  # 리셋
                return True
            return False

        return True

    def record_failure(self, service_name: str):
        """실패 기록"""
        if service_name not in self.services:
            self.services[service_name] = {"failures": 0, "last_failure": 0, "state": "CLOSED"}

        self.services[service_name]["failures"] += 1
        self.services[service_name]["last_failure"] = time.time()

    def record_success(self, service_name: str):
        """성공 기록"""
        if service_name in self.services:
            self.services[service_name]["failures"] = 0
```

**분산 레이트 리미팅** (Redis 사용):

```python
# api-gateway/rate_limiter.py
class RedisRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def allow_request(self, endpoint: str, user_id: str = "anonymous") -> bool:
        """요청 허용 여부 확인"""
        key = f"rate_limit:{endpoint}:{user_id}"

        # 현재 요청 수 확인
        current = await self.redis.get(key)
        current_count = int(current) if current else 0

        # 레이트 리미트 설정 조회
        limit = RATE_LIMITS.get(endpoint, {})
        max_requests = limit.get("requests", 100)
        window = limit.get("window", 60)

        if current_count >= max_requests:
            return False

        # 카운트 증가
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()

        return True
```

**구현 파일**:
- `/home/user/InsiteChart/backend/api/gateway.py` (확장)

---

### 2.4 서비스 간 통신 및 메시지 큐 (Kafka 준비)

**목표**: 서비스 간 느슨한 결합(loose coupling) 구현

**통신 패턴**:

```
동기 통신 (HTTP REST):
클라이언트 → API Gateway → 특정 서비스 → 응답

비동기 통신 (Kafka):
Service A → Kafka Topic → Service B (수신)
Service A → Kafka Topic → Service C (수신)
```

**Kafka 토픽 설계**:

```
Topics:
├─ stock_updates (stock-collector → analytics, backend)
│  └─ Partitions: 5 (symbol 기반)
├─ sentiment_updates (sentiment-analyzer → backend)
│  └─ Partitions: 5
├─ alerts (backend → notification-service)
│  └─ Partitions: 3 (user_id 기반)
├─ user_events (backend → analytics)
│  └─ Partitions: 5
└─ system_events (all → monitoring)
   └─ Partitions: 1
```

**메시지 포맷**:

```json
{
  "event_type": "stock_update",
  "event_id": "uuid",
  "source_service": "data-collector",
  "timestamp": "2025-12-11T10:30:45.123Z",
  "data": {
    "symbol": "AAPL",
    "price": 150.25,
    "volume": 1000000,
    "change_percent": 1.5
  },
  "version": "1.0",
  "correlation_id": "uuid"  // 요청 추적용
}
```

**구현** (Phase 4에서 상세 구현):
- 현재: Kafka 토픽 설계만 진행
- Phase 4: 실제 프로듀서/컨슈머 구현

---

### 2.5 각 마이크로서비스의 독립적 배포 및 스케일링 설정

**목표**: 각 서비스를 독립적으로 배포, 업데이트, 스케일링 가능하게

**Docker Compose 구조** (Phase 1 완료 후):

```yaml
# 향후 docker-compose.prod.yml
version: '3.8'

services:
  # 기존 백엔드 (축소됨)
  backend-api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - KAFKA_BROKERS=kafka:9092
    depends_on:
      - postgres
      - redis
      - kafka

  # 새로운 마이크로서비스
  data-collector:
    build: ./services/data-collector
    ports:
      - "8001:8000"
    environment:
      - KAFKA_BROKERS=kafka:9092
    deploy:
      replicas: 3  # 3개 인스턴스
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  analytics-service:
    build: ./services/analytics
    ports:
      - "8002:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - KAFKA_BROKERS=kafka:9092
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'  # BERT 모델 때문에 높음
          memory: 1G

  api-gateway:
    build: ./services/api-gateway
    ports:
      - "8080:8000"
    environment:
      - BACKEND_URL=http://backend-api:8000
      - DATA_COLLECTOR_URL=http://data-collector:8000
      - ANALYTICS_URL=http://analytics-service:8000
    depends_on:
      - backend-api
      - data-collector
      - analytics-service

  # 기존 인프라 (postgres, redis, kafka, nginx 등)
  postgres:
    image: postgres:15-alpine
    ...
```

**서비스별 스케일링 전략**:

```
data-collector:
  - 수평 확장 (Horizontal Scaling)
  - 인스턴스 3개 → 10개로 확장
  - Kafka 파티션 수와 일치 (5개)
  - 부하: CPU 기반

analytics-service:
  - 수평 확장 가능
  - BERT 모델 때문에 메모리 많이 사용
  - 인스턴스당 1GB 이상 필요
  - 부하: CPU, GPU (있으면) 기반

backend-api:
  - 상태 있음 (세션, 컨텍스트) → 수직 확장 권장
  - Sticky session 필요
  - 인스턴스 1개 → 2-3개로 확장
  - 부하: 요청 수 기반
```

**모니터링 메트릭** (Prometheus):

```yaml
# monitoring/prometheus.yml 추가
scrape_configs:
  - job_name: 'data-collector'
    static_configs:
      - targets: ['localhost:8001', 'localhost:8001', 'localhost:8001']

  - job_name: 'analytics-service'
    static_configs:
      - targets: ['localhost:8002', 'localhost:8002']
```

**배포 파일** (kubernetes 준비):

```yaml
# k8s/data-collector-deployment.yaml (향후)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-collector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-collector
  template:
    metadata:
      labels:
        app: data-collector
    spec:
      containers:
      - name: data-collector
        image: insitechart/data-collector:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

## Phase 4: Kafka 이벤트 버스 실제 통합

**목표**: 테스트 환경의 Kafka를 프로덕션 환경으로 이동 및 완전 통합
**기한**: 3주
**현재 상태**: 코드는 구현되었지만 테스트 환경(`docker-compose.test.yml`)에만 존재

### 4.1 Kafka 클러스터 설정 및 토픽 구성

**프로덕션 Kafka 구성**: `docker-compose.yml` 수정

```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - insitechart-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9093:9093"  # 내부 포트
      - "9092:9092"  # 외부 포트 (클라이언트용)
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_INTERNAL://kafka:9093
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_INTERNAL:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT_INTERNAL
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_LOG_RETENTION_HOURS: 24
      KAFKA_LOG_SEGMENT_BYTES: 1073741824  # 1GB
    networks:
      - insitechart-network

  kafka-ui:  # Kafka 모니터링 UI
    image: provectuslabs/kafka-ui:latest
    depends_on:
      - kafka
    ports:
      - "8082:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: insitechart
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
    networks:
      - insitechart-network
```

**토픽 생성 스크립트**: `scripts/create-kafka-topics.sh`

```bash
#!/bin/bash

# Kafka가 시작될 때까지 대기
until docker-compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list > /dev/null 2>&1; do
  echo "Waiting for Kafka..."
  sleep 2
done

# 토픽 생성
KAFKA_CMD="docker-compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --create"

# 1. stock_updates 토픽
$KAFKA_CMD --topic stock_updates \
  --partitions 5 \
  --replication-factor 1 \
  --config retention.ms=86400000 \  # 24시간
  --config compression.type=snappy || echo "stock_updates already exists"

# 2. sentiment_updates 토픽
$KAFKA_CMD --topic sentiment_updates \
  --partitions 5 \
  --replication-factor 1 \
  --config retention.ms=86400000 || echo "sentiment_updates already exists"

# 3. alerts 토픽
$KAFKA_CMD --topic alerts \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \ # 7일
  --config compression.type=snappy || echo "alerts already exists"

# 4. user_events 토픽
$KAFKA_CMD --topic user_events \
  --partitions 5 \
  --replication-factor 1 \
  --config retention.ms=604800000 || echo "user_events already exists"

# 5. system_events 토픽
$KAFKA_CMD --topic system_events \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=2592000000 \ # 30일
  --config compression.type=gzip || echo "system_events already exists"

echo "Kafka topics created successfully!"
```

**토픽별 파티션 설계**:

```
stock_updates (5 partitions):
  - symbol 기반 파티셔닝
  - 각 파티션은 특정 심볼 그룹을 담당
  - 병렬 처리 가능

sentiment_updates (5 partitions):
  - source 기반 파티셔닝
  - Reddit, Twitter, Discord 등 각 소스별 처리

alerts (3 partitions):
  - user_id % 3 으로 파티셔닝
  - 사용자별 알림 순서 보장

user_events (5 partitions):
  - event_type 기반
  - 이벤트 타입별 분석

system_events (1 partition):
  - 순서 보장 필수
  - 파티션 1개만 사용
```

---

### 4.2 Kafka 프로듀서 구현

**파일**: `backend/services/kafka_event_producer.py`

```python
from aiokafka import AIOKafkaProducer
import json
from typing import Dict, Any
from datetime import datetime
import uuid

class KafkaEventProducer:
    def __init__(self, bootstrap_servers="kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        """프로듀서 시작"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            compression_type='snappy',
            acks='all',  # 모든 복제본에서 확인
            retries=3,
            linger_ms=10,  # 배치 처리를 위해 10ms 대기
        )
        await self.producer.start()

    async def stop(self):
        """프로듀서 종료"""
        if self.producer:
            await self.producer.stop()

    async def send_stock_update(self, symbol: str, price: float, volume: int):
        """주가 업데이트 이벤트"""
        event = {
            "event_type": "stock_update",
            "event_id": str(uuid.uuid4()),
            "source_service": "backend-api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "currency": "USD"
            },
            "version": "1.0"
        }

        # symbol 기반 파티셔닝을 위해 key로 symbol 사용
        await self.producer.send_and_wait(
            "stock_updates",
            value=json.dumps(event).encode(),
            key=symbol.encode(),
            timestamp_ms=int(datetime.utcnow().timestamp() * 1000)
        )

    async def send_sentiment_update(self, symbol: str, sentiment: Dict[str, float]):
        """센티먼트 업데이트 이벤트"""
        event = {
            "event_type": "sentiment_update",
            "event_id": str(uuid.uuid4()),
            "source_service": "analytics-service",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "symbol": symbol,
                "sentiment": sentiment,
                "confidence": sentiment.get("confidence", 0.0)
            },
            "version": "1.0"
        }

        await self.producer.send_and_wait(
            "sentiment_updates",
            value=json.dumps(event).encode(),
            key=symbol.encode()
        )

    async def send_alert(self, user_id: int, alert_type: str, message: str):
        """알림 이벤트"""
        event = {
            "event_type": "user_alert",
            "event_id": str(uuid.uuid4()),
            "source_service": "backend-api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "user_id": user_id,
                "alert_type": alert_type,
                "message": message
            },
            "version": "1.0"
        }

        # user_id 기반 파티셔닝
        await self.producer.send_and_wait(
            "alerts",
            value=json.dumps(event).encode(),
            key=str(user_id % 3).encode()  # 3개 파티션
        )

    async def send_user_event(self, user_id: int, event_type: str, data: Dict[str, Any]):
        """사용자 이벤트"""
        event = {
            "event_type": event_type,
            "event_id": str(uuid.uuid4()),
            "source_service": "backend-api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "user_id": user_id,
                **data
            },
            "version": "1.0"
        }

        await self.producer.send_and_wait(
            "user_events",
            value=json.dumps(event).encode(),
            key=event_type.encode()
        )
```

**FastAPI 통합**:

```python
# backend/main.py
from .services.kafka_event_producer import KafkaEventProducer

kafka_producer = None

@app.on_event("startup")
async def startup_kafka():
    global kafka_producer
    kafka_producer = KafkaEventProducer()
    await kafka_producer.start()
    logger.info("Kafka producer started")

@app.on_event("shutdown")
async def shutdown_kafka():
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Kafka producer stopped")

# 엔드포인트에서 사용
@app.post("/api/v1/stocks/{symbol}")
async def update_stock(symbol: str, data: StockData):
    # 주가 업데이트
    await kafka_producer.send_stock_update(symbol, data.price, data.volume)
    # ...
```

---

### 4.3 Kafka 컨슈머 구현

**파일**: `backend/services/kafka_event_consumer.py`

```python
from aiokafka import AIOKafkaConsumer
import json
from typing import Callable, Dict
import asyncio

class KafkaEventConsumer:
    def __init__(self, bootstrap_servers="kafka:9092", group_id="insitechart-group"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = None
        self.handlers: Dict[str, list] = {}  # event_type → [handlers]

    async def start(self):
        """컨슈머 시작"""
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )
        await self.consumer.start()

    async def stop(self):
        """컨슈머 종료"""
        if self.consumer:
            await self.consumer.stop()

    def register_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 등록"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def listen(self, topics: list):
        """토픽 구독 및 메시지 처리"""
        await self.consumer.subscribe(topics)

        try:
            async for message in self.consumer:
                event = message.value
                event_type = event.get("event_type")

                # 등록된 핸들러 실행
                if event_type in self.handlers:
                    for handler in self.handlers[event_type]:
                        try:
                            await handler(event)
                        except Exception as e:
                            logger.error(f"Handler error for {event_type}: {e}")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            await self.consumer.stop()

# 사용 예
async def handle_stock_update(event: dict):
    """주가 업데이트 핸들러"""
    stock_data = event["data"]
    symbol = stock_data["symbol"]

    # 캐시 업데이트
    await cache.set(f"stock:{symbol}", stock_data)

    # 데이터베이스 저장
    await db.save_stock_price(symbol, stock_data["price"])

    # 사용자에게 WebSocket으로 알림
    await websocket_manager.broadcast(f"stock_updates:{symbol}", event)

async def handle_sentiment_update(event: dict):
    """센티먼트 업데이트 핸들러"""
    sentiment_data = event["data"]
    symbol = sentiment_data["symbol"]

    # 캐시 업데이트
    await cache.set(f"sentiment:{symbol}", sentiment_data)

    # 데이터베이스 저장
    await db.save_sentiment(symbol, sentiment_data)
```

**FastAPI 통합**:

```python
# backend/main.py
kafka_consumer = None

@app.on_event("startup")
async def startup_kafka_consumer():
    global kafka_consumer
    kafka_consumer = KafkaEventConsumer()
    await kafka_consumer.start()

    # 핸들러 등록
    kafka_consumer.register_handler("stock_update", handle_stock_update)
    kafka_consumer.register_handler("sentiment_update", handle_sentiment_update)

    # 백그라운드 태스크로 리스닝 시작
    asyncio.create_task(
        kafka_consumer.listen([
            "stock_updates",
            "sentiment_updates",
            "alerts",
            "user_events",
            "system_events"
        ])
    )
```

---

### 4.4 메시지 순서 보장 및 중복 처리

**Idempotent Consumer 구현**:

```python
class IdempotentEventProcessor:
    """중복 제거 및 순서 보장"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400  # 24시간

    async def process_event(self, event: dict, handler: Callable) -> bool:
        """
        이벤트 처리 (중복 제거)
        Returns: True if processed, False if duplicate
        """
        event_id = event.get("event_id")

        # 이미 처리된 이벤트인지 확인
        key = f"processed_event:{event_id}"
        if await self.redis.exists(key):
            logger.warning(f"Duplicate event detected: {event_id}")
            return False

        try:
            # 이벤트 처리
            await handler(event)

            # 처리 완료 표시 (TTL과 함께 저장)
            await self.redis.setex(key, self.ttl, "processed")
            return True
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return False

# 사용
processor = IdempotentEventProcessor(redis_client)

async def handle_stock_update_idempotent(event: dict):
    """중복 제거되는 핸들러"""
    processed = await processor.process_event(
        event,
        handle_stock_update
    )
    if processed:
        logger.info(f"Event {event['event_id']} processed successfully")
```

**순서 보장 전략**:

```python
class OrderedEventProcessor:
    """이벤트 순서 보장"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.queues = {}  # key → queue

    async def process_ordered(self, partition_key: str, event: dict, handler: Callable):
        """
        파티션 키에 따라 순서대로 처리
        같은 파티션 키는 항상 같은 순서로 처리됨
        """
        queue_key = f"event_queue:{partition_key}"

        # 이벤트를 큐에 추가
        await self.redis.rpush(queue_key, json.dumps(event))

        # 이 파티션의 처리 중 여부 확인
        processing_key = f"processing:{partition_key}"

        if await self.redis.get(processing_key):
            # 이미 처리 중이면 대기
            return

        # 처리 시작 표시
        await self.redis.setex(processing_key, 3600, "1")  # 1시간 TTL

        # 큐의 모든 이벤트 처리
        while True:
            event_json = await self.redis.lpop(queue_key)
            if not event_json:
                break

            event = json.loads(event_json)
            await handler(event)

        # 처리 완료 표시
        await self.redis.delete(processing_key)
```

---

### 4.5 Kafka 모니터링 및 알림 시스템

**Kafka 메트릭 수집**: `backend/monitoring/kafka_monitor.py`

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
kafka_messages_produced = Counter(
    'kafka_messages_produced_total',
    'Total Kafka messages produced',
    ['topic']
)

kafka_messages_consumed = Counter(
    'kafka_messages_consumed_total',
    'Total Kafka messages consumed',
    ['topic', 'consumer_group']
)

kafka_consumer_lag = Gauge(
    'kafka_consumer_lag',
    'Consumer lag in messages',
    ['topic', 'partition', 'consumer_group']
)

kafka_processing_duration = Histogram(
    'kafka_message_processing_duration_seconds',
    'Time to process Kafka message',
    ['topic', 'event_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

class KafkaMonitor:
    def __init__(self, admin_client):
        self.admin = admin_client

    async def monitor_consumer_lag(self):
        """컨슈머 래그 모니터링"""
        while True:
            try:
                # 컨슈머 그룹의 래그 정보 조회
                partitions = await self.admin.fetch_consumer_offsets(
                    group_id="insitechart-group"
                )

                for (topic, partition), offset in partitions.items():
                    # 최신 오프셋 조회
                    latest = await self.admin.fetch_committed_offsets(
                        topic,
                        partitions=[partition]
                    )

                    lag = latest[partition].offset - offset.offset
                    kafka_consumer_lag.labels(
                        topic=topic,
                        partition=partition,
                        consumer_group="insitechart-group"
                    ).set(lag)

                    # 래그가 높으면 알림
                    if lag > 10000:
                        logger.warning(
                            f"High consumer lag detected: "
                            f"topic={topic}, partition={partition}, lag={lag}"
                        )

            except Exception as e:
                logger.error(f"Consumer lag monitoring error: {e}")

            await asyncio.sleep(60)  # 1분마다 확인
```

**Grafana 대시보드** (향후):
```yaml
# monitoring/grafana/dashboards/kafka-dashboard.json
{
  "dashboard": {
    "title": "Kafka Cluster Monitoring",
    "panels": [
      {
        "title": "Messages Produced per Topic",
        "targets": [
          {
            "expr": "rate(kafka_messages_produced_total[1m])"
          }
        ]
      },
      {
        "title": "Consumer Lag",
        "targets": [
          {
            "expr": "kafka_consumer_lag"
          }
        ]
      },
      {
        "title": "Processing Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, kafka_message_processing_duration_seconds)"
          }
        ]
      }
    ]
  }
}
```

---

## Phase 5: GDPR 자동화 시스템 완성

**목표**: GDPR 규정을 완전히 자동화하여 준수
**기한**: 3주
**현재 상태**: 기본 구조만 구현됨

### 5.1 데이터 보존 정책 자동화

**구현 파일**: `backend/services/gdpr_data_retention_service.py`

```python
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio

class GDPRDataRetentionService:
    """GDPR 데이터 보존 정책 자동화"""

    # 데이터별 보존 기간
    RETENTION_POLICIES = {
        "user_data": 365,  # 1년
        "user_activity": 90,  # 3개월
        "sentiment_data": 180,  # 6개월
        "price_history": 730,  # 2년
        "system_logs": 30,  # 30일
        "error_logs": 90,  # 3개월
    }

    def __init__(self, db_connection, logger):
        self.db = db_connection
        self.logger = logger

    async def cleanup_expired_data(self):
        """만료된 데이터 자동 삭제"""
        for data_type, retention_days in self.RETENTION_POLICIES.items():
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            try:
                if data_type == "user_activity":
                    await self._cleanup_user_activity(cutoff_date)
                elif data_type == "sentiment_data":
                    await self._cleanup_sentiment_data(cutoff_date)
                elif data_type == "system_logs":
                    await self._cleanup_system_logs(cutoff_date)
                # ... 다른 데이터 타입

                self.logger.info(
                    f"Cleaned up {data_type} older than {cutoff_date}"
                )
            except Exception as e:
                self.logger.error(f"Cleanup error for {data_type}: {e}")
                # 에러 발생해도 계속 진행

    async def _cleanup_user_activity(self, cutoff_date: datetime):
        """사용자 활동 데이터 삭제"""
        query = """
        DELETE FROM user_activity
        WHERE created_at < %s
        """
        await self.db.execute(query, (cutoff_date,))

        # 감사 로그
        await self._log_deletion("user_activity", cutoff_date)

    async def _cleanup_sentiment_data(self, cutoff_date: datetime):
        """센티먼트 데이터 삭제 (특히 개인 정보 포함)"""
        query = """
        DELETE FROM sentiment_data
        WHERE timestamp < %s
        AND source IN ('REDDIT', 'TWITTER')  -- 소셜 미디어 데이터만
        """
        await self.db.execute(query, (cutoff_date,))

        await self._log_deletion("sentiment_data", cutoff_date)

    async def _cleanup_system_logs(self, cutoff_date: datetime):
        """시스템 로그 삭제"""
        query = """
        DELETE FROM system_logs
        WHERE timestamp < %s
        """
        await self.db.execute(query, (cutoff_date,))

        await self._log_deletion("system_logs", cutoff_date)

    async def _log_deletion(self, data_type: str, cutoff_date: datetime):
        """삭제 작업 감사 로그"""
        query = """
        INSERT INTO gdpr_audit_log (action, data_type, cutoff_date, executed_at)
        VALUES (%s, %s, %s, %s)
        """
        await self.db.execute(
            query,
            ("automated_deletion", data_type, cutoff_date, datetime.utcnow())
        )

# 정기적으로 실행 (매일 자정)
async def run_scheduled_cleanup():
    """스케줄된 정리 작업"""
    service = GDPRDataRetentionService(db, logger)

    # APScheduler 또는 Celery 사용
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        service.cleanup_expired_data,
        'cron',
        hour=0,  # 매일 자정
        minute=0
    )
    scheduler.start()
```

**데이터베이스 스키마 추가**:

```sql
-- GDPR 감사 로그 테이블
CREATE TABLE gdpr_audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100),  -- 'automated_deletion', 'user_export', 'user_deletion'
    data_type VARCHAR(100),
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    cutoff_date TIMESTAMP,
    rows_affected INT DEFAULT 0,
    executed_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20),  -- 'pending', 'completed', 'failed'
    error_message TEXT
);

-- 데이터 보존 정책 테이블
CREATE TABLE gdpr_retention_policies (
    id SERIAL PRIMARY KEY,
    data_type VARCHAR(100) UNIQUE,
    retention_days INT,
    description TEXT,
    last_cleanup TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 초기 정책 데이터
INSERT INTO gdpr_retention_policies (data_type, retention_days, description) VALUES
('user_activity', 90, '사용자 활동 데이터'),
('sentiment_data', 180, '센티먼트 분석 데이터'),
('price_history', 730, '주가 이력 데이터'),
('system_logs', 30, '시스템 로그'),
('error_logs', 90, '에러 로그'),
('user_session', 90, '사용자 세션');
```

---

### 5.2 개인정보 자동 삭제 기능 (Right to be Forgotten)

**구현 파일**: `backend/services/gdpr_user_deletion_service.py`

```python
from typing import Dict, List
from datetime import datetime
import asyncio

class GDPRUserDeletionService:
    """사용자 삭제 요청 자동 처리"""

    def __init__(self, db_connection, logger):
        self.db = db_connection
        self.logger = logger

    async def process_deletion_request(self, user_id: int) -> Dict:
        """사용자 삭제 요청 처리"""
        request_id = str(uuid.uuid4())

        try:
            # 1. 요청 기록
            await self._log_deletion_request(user_id, request_id)

            # 2. 개인 정보 삭제
            await self._anonymize_user_data(user_id)

            # 3. 관련 데이터 삭제
            await self._delete_user_data(user_id)

            # 4. 최종 사용자 레코드 삭제
            await self._delete_user_account(user_id)

            # 5. 완료 기록
            await self._log_completion(user_id, request_id, "success")

            return {
                "status": "success",
                "request_id": request_id,
                "message": "사용자 데이터가 완전히 삭제되었습니다"
            }

        except Exception as e:
            self.logger.error(f"Deletion error for user {user_id}: {e}")
            await self._log_completion(user_id, request_id, "failed", str(e))

            return {
                "status": "failed",
                "request_id": request_id,
                "error": str(e)
            }

    async def _anonymize_user_data(self, user_id: int):
        """개인 정보 익명화"""
        # 사용자 테이블에서 개인 정보 제거
        query = """
        UPDATE users
        SET
            email = CONCAT('deleted_', %s, '@deleted.local'),
            username = CONCAT('deleted_user_', %s),
            password_hash = NULL,
            is_active = FALSE
        WHERE id = %s
        """
        await self.db.execute(query, (user_id, user_id, user_id))

        # 개인 설정 삭제
        await self.db.execute(
            "DELETE FROM user_notification_settings WHERE user_id = %s",
            (user_id,)
        )

    async def _delete_user_data(self, user_id: int):
        """사용자 관련 데이터 삭제"""
        tables_to_delete = [
            "watchlist_items",
            "search_history",
            "user_sessions",
            "user_activity",
            "user_behavior",
            "user_feedback",
            "api_keys"
        ]

        for table in tables_to_delete:
            query = f"DELETE FROM {table} WHERE user_id = %s"
            try:
                await self.db.execute(query, (user_id,))
                self.logger.info(f"Deleted records from {table} for user {user_id}")
            except Exception as e:
                self.logger.warning(
                    f"Could not delete from {table}: {e}"
                )

    async def _delete_user_account(self, user_id: int):
        """최종 사용자 레코드 삭제"""
        query = "DELETE FROM users WHERE id = %s"
        await self.db.execute(query, (user_id,))
        self.logger.info(f"User account {user_id} deleted")

    async def _log_deletion_request(self, user_id: int, request_id: str):
        """삭제 요청 로깅"""
        query = """
        INSERT INTO gdpr_deletion_requests
        (user_id, request_id, status, requested_at)
        VALUES (%s, %s, %s, %s)
        """
        await self.db.execute(
            query,
            (user_id, request_id, "processing", datetime.utcnow())
        )

    async def _log_completion(
        self,
        user_id: int,
        request_id: str,
        status: str,
        error: str = None
    ):
        """삭제 완료 로깅"""
        query = """
        UPDATE gdpr_deletion_requests
        SET status = %s, completed_at = %s, error_message = %s
        WHERE request_id = %s
        """
        await self.db.execute(
            query,
            (status, datetime.utcnow(), error, request_id)
        )
```

**API 엔드포인트**:

```python
# backend/api/gdpr_routes.py

@app.post("/api/v1/gdpr/delete")
async def request_user_deletion(
    current_user: User = Depends(get_current_user),
    confirmation: str = Body(...)  # "DELETE_MY_DATA"
):
    """사용자 자신의 데이터 삭제 요청"""

    if confirmation != "DELETE_MY_DATA":
        raise HTTPException(status_code=400, detail="Invalid confirmation")

    deletion_service = GDPRUserDeletionService(db, logger)
    result = await deletion_service.process_deletion_request(current_user.id)

    return {
        "status": "success",
        "message": "삭제 요청이 처리되었습니다",
        "request_id": result["request_id"]
    }

@app.get("/api/v1/gdpr/deletion-status/{request_id}")
async def check_deletion_status(request_id: str):
    """삭제 요청 상태 확인"""
    query = """
    SELECT status, completed_at, error_message
    FROM gdpr_deletion_requests
    WHERE request_id = %s
    """
    result = await db.fetchone(query, (request_id,))

    if not result:
        raise HTTPException(status_code=404, detail="Request not found")

    return {
        "request_id": request_id,
        "status": result["status"],
        "completed_at": result["completed_at"],
        "error": result["error_message"]
    }
```

---

### 5.3 동의 관리 및 추적 시스템

**구현 파일**: `backend/services/gdpr_consent_management_service.py`

```python
from enum import Enum
from datetime import datetime
from typing import List, Dict

class ConsentType(str, Enum):
    ANALYTICS = "analytics"  # 분석 추적
    MARKETING = "marketing"  # 마케팅 통신
    DATA_SHARING = "data_sharing"  # 제3자 데이터 공유
    COOKIES = "cookies"  # 필수 쿠키 외
    PROFILING = "profiling"  # 프로파일링

class GDPRConsentManagementService:
    """동의 관리 및 추적"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def save_consent(
        self,
        user_id: int,
        consent_type: ConsentType,
        granted: bool,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict:
        """동의 저장"""

        query = """
        INSERT INTO user_consents
        (user_id, consent_type, granted, ip_address, user_agent, granted_at, version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, consent_type)
        DO UPDATE SET
            granted = EXCLUDED.granted,
            ip_address = EXCLUDED.ip_address,
            user_agent = EXCLUDED.user_agent,
            granted_at = EXCLUDED.granted_at,
            version = EXCLUDED.version + 1
        RETURNING id, version
        """

        result = await self.db.fetchone(
            query,
            (
                user_id,
                consent_type.value,
                granted,
                ip_address,
                user_agent,
                datetime.utcnow(),
                1  # 초기 버전
            )
        )

        return {
            "consent_id": result["id"],
            "consent_type": consent_type,
            "granted": granted,
            "version": result["version"]
        }

    async def get_user_consents(self, user_id: int) -> List[Dict]:
        """사용자 동의 목록"""
        query = """
        SELECT consent_type, granted, granted_at, version
        FROM user_consents
        WHERE user_id = %s
        ORDER BY granted_at DESC
        """

        consents = await self.db.fetchall(query, (user_id,))

        return [
            {
                "consent_type": c["consent_type"],
                "granted": c["granted"],
                "granted_at": c["granted_at"].isoformat(),
                "version": c["version"]
            }
            for c in consents
        ]

    async def revoke_all_consents(self, user_id: int):
        """모든 동의 철회"""
        query = """
        UPDATE user_consents
        SET granted = FALSE, revoked_at = %s
        WHERE user_id = %s AND granted = TRUE
        """

        await self.db.execute(query, (datetime.utcnow(), user_id))

    async def check_consent(self, user_id: int, consent_type: ConsentType) -> bool:
        """특정 동의 확인"""
        query = """
        SELECT granted
        FROM user_consents
        WHERE user_id = %s AND consent_type = %s
        """

        result = await self.db.fetchone(query, (user_id, consent_type.value))

        return result["granted"] if result else False

# API 엔드포인트
@app.get("/api/v1/gdpr/consents")
async def get_consents(current_user: User = Depends(get_current_user)):
    """사용자 동의 목록 조회"""
    service = GDPRConsentManagementService(db)
    consents = await service.get_user_consents(current_user.id)
    return {"consents": consents}

@app.post("/api/v1/gdpr/consents")
async def update_consent(
    consent_type: ConsentType,
    granted: bool,
    current_user: User = Depends(get_current_user),
    request: Request
):
    """동의 저장"""
    service = GDPRConsentManagementService(db)

    result = await service.save_consent(
        user_id=current_user.id,
        consent_type=consent_type,
        granted=granted,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return result
```

---

### 5.4 데이터 접근 로깅 및 감사 추적

**구현 파일**: `backend/services/gdpr_audit_trail_service.py`

```python
from enum import Enum
from datetime import datetime
from typing import Any, Dict

class DataAccessType(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"

class GDPRAuditTrailService:
    """데이터 접근 감시 및 로깅"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def log_data_access(
        self,
        user_id: int,
        access_type: DataAccessType,
        data_type: str,
        description: str,
        ip_address: str = None,
        result: bool = True
    ):
        """데이터 접근 로깅"""

        query = """
        INSERT INTO gdpr_audit_trail
        (user_id, access_type, data_type, description, ip_address, result, accessed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        await self.db.execute(
            query,
            (
                user_id,
                access_type.value,
                data_type,
                description,
                ip_address,
                result,
                datetime.utcnow()
            )
        )

    async def get_audit_trail(
        self,
        user_id: int,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[Dict]:
        """감사 기록 조회"""

        query = """
        SELECT * FROM gdpr_audit_trail
        WHERE user_id = %s
        """

        params = [user_id]

        if start_date:
            query += " AND accessed_at >= %s"
            params.append(start_date)

        if end_date:
            query += " AND accessed_at <= %s"
            params.append(end_date)

        query += " ORDER BY accessed_at DESC LIMIT %s"
        params.append(limit)

        records = await self.db.fetchall(query, params)

        return [
            {
                "id": r["id"],
                "access_type": r["access_type"],
                "data_type": r["data_type"],
                "description": r["description"],
                "accessed_at": r["accessed_at"].isoformat(),
                "ip_address": r["ip_address"],
                "result": r["result"]
            }
            for r in records
        ]

    async def detect_suspicious_activity(self, user_id: int) -> List[Dict]:
        """의심 활동 감지"""

        # 예: 짧은 시간에 많은 데이터 접근
        query = """
        SELECT
            accessed_at,
            COUNT(*) as access_count,
            COUNT(DISTINCT data_type) as unique_data_types
        FROM gdpr_audit_trail
        WHERE user_id = %s
        AND accessed_at > NOW() - INTERVAL 1 hour
        GROUP BY HOUR(accessed_at)
        HAVING COUNT(*) > 50  -- 1시간에 50회 이상
        """

        suspicious = await self.db.fetchall(query, (user_id,))

        return [
            {
                "timestamp": s["accessed_at"].isoformat(),
                "access_count": s["access_count"],
                "data_types": s["unique_data_types"],
                "severity": "HIGH" if s["access_count"] > 100 else "MEDIUM"
            }
            for s in suspicious
        ]

# 미들웨어에서 자동으로 로깅
audit_service = GDPRAuditTrailService(db)

@app.middleware("http")
async def log_data_access(request: Request, call_next):
    """모든 API 요청의 데이터 접근 기록"""

    response = await call_next(request)

    # 사용자 인증된 경우만 로깅
    if hasattr(request.state, "user_id"):
        user_id = request.state.user_id

        # 접근 유형 판단
        access_type = DataAccessType.READ
        if request.method in ["POST", "PUT"]:
            access_type = DataAccessType.WRITE
        elif request.method == "DELETE":
            access_type = DataAccessType.DELETE

        # 데이터 타입 판단
        path_parts = request.url.path.split("/")
        data_type = path_parts[-1] if path_parts else "unknown"

        # 로깅
        await audit_service.log_data_access(
            user_id=user_id,
            access_type=access_type,
            data_type=data_type,
            description=f"{request.method} {request.url.path}",
            ip_address=request.client.host,
            result=response.status_code < 400
        )

    return response
```

---

### 5.5 GDPR 준수 보고서 자동 생성

**구현 파일**: `backend/services/gdpr_compliance_reporting_service.py`

```python
from datetime import datetime, timedelta
from typing import Dict
import json

class GDPRComplianceReportingService:
    """GDPR 준수 보고서 자동 생성"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """전체 GDPR 준수 보고서"""

        report = {
            "report_date": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "sections": {}
        }

        # 1. 데이터 처리 활동
        report["sections"]["data_processing"] = \
            await self._get_data_processing_summary(start_date, end_date)

        # 2. 데이터 삭제
        report["sections"]["data_deletions"] = \
            await self._get_deletion_summary(start_date, end_date)

        # 3. 사용자 동의
        report["sections"]["consents"] = \
            await self._get_consent_summary(start_date, end_date)

        # 4. 데이터 이동 (data portability)
        report["sections"]["data_portability"] = \
            await self._get_data_export_summary(start_date, end_date)

        # 5. 보안 사건
        report["sections"]["security_incidents"] = \
            await self._get_security_incidents(start_date, end_date)

        # 6. 감사 추적
        report["sections"]["audit_summary"] = \
            await self._get_audit_summary(start_date, end_date)

        return report

    async def _get_data_processing_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """데이터 처리 활동 요약"""

        query = """
        SELECT
            COUNT(DISTINCT user_id) as total_users,
            COUNT(*) as total_operations,
            COUNT(CASE WHEN access_type = 'read' THEN 1 END) as reads,
            COUNT(CASE WHEN access_type = 'write' THEN 1 END) as writes,
            COUNT(CASE WHEN access_type = 'delete' THEN 1 END) as deletes
        FROM gdpr_audit_trail
        WHERE accessed_at BETWEEN %s AND %s
        """

        result = await self.db.fetchone(query, (start_date, end_date))

        return {
            "total_users_processed": result["total_users"],
            "total_operations": result["total_operations"],
            "reads": result["reads"],
            "writes": result["writes"],
            "deletes": result["deletes"]
        }

    async def _get_deletion_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """삭제 활동 요약"""

        query = """
        SELECT
            COUNT(*) as deletion_requests,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            SUM(CASE WHEN status = 'completed' THEN rows_affected ELSE 0 END) as rows_deleted
        FROM gdpr_deletion_requests
        WHERE requested_at BETWEEN %s AND %s
        """

        result = await self.db.fetchone(query, (start_date, end_date))

        return {
            "deletion_requests": result["deletion_requests"],
            "successful_deletions": result["successful"],
            "failed_deletions": result["failed"],
            "total_rows_deleted": result["rows_deleted"] or 0
        }

    async def _get_consent_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """동의 관리 요약"""

        query = """
        SELECT
            consent_type,
            COUNT(CASE WHEN granted THEN 1 END) as granted_count,
            COUNT(CASE WHEN NOT granted THEN 1 END) as withheld_count
        FROM user_consents
        WHERE granted_at BETWEEN %s AND %s
        GROUP BY consent_type
        """

        results = await self.db.fetchall(query, (start_date, end_date))

        consent_summary = {}
        for row in results:
            consent_summary[row["consent_type"]] = {
                "granted": row["granted_count"],
                "withheld": row["withheld_count"],
                "grant_rate": row["granted_count"] / (row["granted_count"] + row["withheld_count"]) * 100
            }

        return consent_summary

    async def _get_data_export_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """데이터 이동성 (Portability) 요약"""

        query = """
        SELECT
            COUNT(*) as export_requests,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
            AVG(EXTRACT(EPOCH FROM (completed_at - requested_at))) as avg_completion_time_seconds
        FROM gdpr_data_exports
        WHERE requested_at BETWEEN %s AND %s
        """

        result = await self.db.fetchone(query, (start_date, end_date))

        return {
            "export_requests": result["export_requests"],
            "successful_exports": result["successful"],
            "avg_completion_time_seconds": result["avg_completion_time_seconds"] or 0
        }

    async def _get_security_incidents(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """보안 사건 요약"""

        query = """
        SELECT
            severity,
            COUNT(*) as count
        FROM security_incidents
        WHERE detected_at BETWEEN %s AND %s
        GROUP BY severity
        """

        results = await self.db.fetchall(query, (start_date, end_date))

        incidents = {}
        for row in results:
            incidents[row["severity"]] = row["count"]

        return {
            "total_incidents": sum(incidents.values()),
            "by_severity": incidents
        }

    async def _get_audit_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """감사 활동 요약"""

        query = """
        SELECT
            COUNT(*) as total_audits,
            COUNT(DISTINCT user_id) as audited_users,
            AVG(EXTRACT(EPOCH FROM accessed_at - accessed_at)) as avg_response_time
        FROM gdpr_audit_trail
        WHERE accessed_at BETWEEN %s AND %s
        """

        result = await self.db.fetchone(query, (start_date, end_date))

        return {
            "total_audit_entries": result["total_audits"],
            "users_with_activity": result["audited_users"],
            "audit_completeness": "100%"  # 모든 접근이 로깅되는 경우
        }

    async def export_report_as_pdf(self, report: Dict) -> bytes:
        """보고서를 PDF로 내보내기"""
        # ReportLab 또는 PyPDF2 사용
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak

        # PDF 생성 로직...
        # (자세한 구현은 별도)
        pass

# API 엔드포인트
@app.get("/api/v1/gdpr/compliance-report")
async def get_compliance_report(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    format: str = Query("json", regex="^(json|pdf)$")
):
    """GDPR 준수 보고서 조회"""

    service = GDPRComplianceReportingService(db)
    report = await service.generate_compliance_report(start_date, end_date)

    if format == "pdf":
        pdf_bytes = await service.export_report_as_pdf(report)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=gdpr_report.pdf"}
        )
    else:
        return report
```

---

## 작업 의존성

```
Phase 1: 실시간 데이터 동기화
    ├─ 1.1: WebSocket 재연결 (선행 필수 없음)
    ├─ 1.2: 데이터 스트리밍 파이프라인 (1.1 완료 후)
    ├─ 1.3: Redis Pub/Sub (1.1, 1.2 완료 후)
    ├─ 1.4: 동시성 처리 (1.3 완료 후)
    └─ 1.5: 알림 템플릿 (1.1-1.4 완료 후)

Phase 2: 마이크로서비스 분리
    ├─ 2.1: 데이터 수집 서비스 (선행 필수 없음, Phase 1과 병렬)
    ├─ 2.2: 분석 서비스 (2.1 완료 후)
    ├─ 2.3: API 게이트웨이 (2.1, 2.2 완료 후)
    ├─ 2.4: 서비스 간 통신 (2.3 완료 후, Phase 4와 연계)
    └─ 2.5: 배포 설정 (2.1-2.3 완료 후)

Phase 3: CI/CD 파이프라인
    ├─ 3.1: GitHub Actions 워크플로우 (선행 필수 없음)
    ├─ 3.2: 테스트 환경 (3.1 완료 후)
    ├─ 3.3: 빌드 파이프라인 (3.1, 3.2 완료 후)
    ├─ 3.4: 배포 전략 (3.3 완료 후)
    └─ 3.5: 모니터링 (3.4 완료 후)

Phase 4: Kafka 이벤트 버스
    ├─ 4.1: Kafka 클러스터 설정 (선행 필수: Phase 2 완료)
    ├─ 4.2: 프로듀서 (4.1 완료 후)
    ├─ 4.3: 컨슈머 (4.2 완료 후)
    ├─ 4.4: 순서 보장 (4.3 완료 후)
    └─ 4.5: 모니터링 (4.4 완료 후)

Phase 5: GDPR 자동화
    ├─ 5.1: 데이터 보존 정책 (선행 필수 없음)
    ├─ 5.2: 사용자 삭제 (5.1 완료 후)
    ├─ 5.3: 동의 관리 (5.2 완료 후)
    ├─ 5.4: 감사 추적 (5.3 완료 후)
    └─ 5.5: 보고서 생성 (5.4 완료 후)
```

---

## 위험 분석

### 🔴 높은 위험 (High Risk)

| 위험 | 영향 | 완화 전략 |
|------|------|---------|
| **WebSocket 대규모 동시 연결 실패** | 실시간 데이터 서비스 중단 | Phase 1.1에서 충분한 부하 테스트 (5000+ 동시) |
| **마이크로서비스 분리 시 데이터 불일치** | 비즈니스 로직 오류 | 트랜잭션 로그, 감시 메커니즘 구현 |
| **Kafka 메시지 손실** | 중요 데이터 유실 | acks='all', 복제본 설정, 데드레터 큐 |
| **CI/CD 자동화 오류** | 잘못된 배포 | 스테이징 환경에서 철저한 테스트 |

### 🟠 중간 위험 (Medium Risk)

| 위험 | 영향 | 완화 전략 |
|------|------|---------|
| **GDPR 준수 불완전** | 법적 처벌 | 법률팀 검토, 정기 감시 |
| **성능 저하** | 사용자 경험 악화 | 부하 테스트, 모니터링 |
| **보안 취약점** | 데이터 유출 | 보안 스캐닝, 침투 테스트 |

### 🟡 낮은 위험 (Low Risk)

| 위험 | 영향 | 완화 전략 |
|------|------|---------|
| **개발자 학습 곡선** | 초기 진행 지연 | 문서화, 팀 트레이닝 |
| **의존성 버전 호환성** | 빌드 실패 | 정기 의존성 업데이트 |

---

## 성공 기준

### Phase 1 성공 기준
- ✅ WebSocket 최소 1000개 동시 연결 유지
- ✅ 데이터 스트리밍 지연 시간 < 1초
- ✅ 메시지 손실율 = 0%
- ✅ 시스템 가용성 ≥ 99.5%
- ✅ 통합 테스트 커버리지 ≥ 80%

### Phase 2 성공 기준
- ✅ 4개 마이크로서비스 독립 배포 가능
- ✅ 서비스별 독립 스케일링 가능
- ✅ API 게이트웨이 요청 처리 < 100ms
- ✅ 서킷 브레이커 정상 작동 (장애 감지 < 30초)

### Phase 3 성공 기준
- ✅ 모든 PR에 대해 CI/CD 자동 실행
- ✅ 단위 테스트 커버리지 ≥ 80%
- ✅ 배포 시간 < 5분
- ✅ 스테이징 환경에서 검증 < 2시간

### Phase 4 성공 기준
- ✅ Kafka 토픽 생성 및 검증 완료
- ✅ 프로듀서/컨슈머 throughput > 1000 msg/sec
- ✅ 메시지 순서 보장 (같은 파티션 내)
- ✅ 컨슈머 래그 < 1000 메시지

### Phase 5 성공 기준
- ✅ 자동 데이터 정리 정책 실행 확인
- ✅ 사용자 삭제 요청 처리 < 24시간
- ✅ 동의 관리 API 정상 작동
- ✅ 감사 로그 누락률 = 0%
- ✅ GDPR 준수 보고서 자동 생성 가능

---

## 다음 단계

1. **즉시** (이번 주):
   - 작업 목록 승인
   - 팀 역할 배치
   - Phase 1 상세 일정 수립

2. **이번 주** (1주):
   - Phase 1.1 (WebSocket) 개발 시작
   - Phase 2.1 (데이터 수집 서비스) 개발 시작
   - Phase 3.1 (CI/CD) 개발 시작

3. **다음 주** (2주):
   - Phase 1 완료
   - Phase 2 시작
   - Phase 3 완료

---

**마지막 업데이트**: 2025-12-11
**담당자**: Development Team
**상태**: 진행 중

