# 스펙 충족을 위한 아키텍처 재설계 계획

## 1. 개요

본 문서는 현재 단일 모놀리식 Streamlit 애플리케이션을 스펙 요구사항에 맞는 마이크로서비스 아키텍처로 전환하기 위한 상세한 재설계 계획을 제시합니다.

## 2. 현재 vs 목표 아키텍처 비교

### 2.1 현재 아키텍처
```
┌─────────────────────────────────────┐
│           Streamlit App              │
│  ┌─────────────────────────────────┐ │
│  │  Stock Analysis Functions       │ │
│  │  - yfinance API calls           │ │
│  │  - Plotly charts               │ │
│  │  - Technical indicators        │ │
│  │  - Data formatting             │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │  UI Components                 │ │
│  │  - Watchlist                   │ │
│  │  - Chart controls              │ │
│  │  - Data export                 │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 2.2 목표 아키텍처
```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   React App     │  │   Mobile App    │  │   Admin UI   │ │
│  │   - Dashboard   │  │   - Native UI   │  │   - System   │ │
│  │   - Charts      │  │   - Offline     │  │   Monitoring │ │
│  │   - Watchlist   │  │   - Push Notif. │  │   - Config   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Auth Service  │  │   Rate Limiter  │  │   Load       │ │
│  │   - JWT         │  │   - API Keys    │  │   Balancer   │ │
│  │   - OAuth       │  │   - Throttling  │  │   - Health   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Microservices Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Stock Service  │  │  Sentiment      │  │  User        │ │
│  │  - Yahoo API    │  │  Service        │  │  Service     │ │
│  │  - Real-time    │  │  - Reddit API   │  │  - Profile   │ │
│  │  - Historical   │  │  - Twitter API  │  │  - Watchlist │ │
│  │  - Indicators   │  │  - Analysis     │  │  - Settings  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Notification   │  │  Analytics      │  │  Correlation │ │
│  │  Service        │  │  Service        │  │  Service     │ │
│  │  - Email        │  │  - Metrics      │  │  - Stock-    │ │
│  │  - Push         │  │  - Reports      │  │   Sentiment  │ │
│  │  - WebSocket    │  │  - Dashboard    │  │  - Patterns  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   TimescaleDB   │  │     Redis       │  │   Object     │ │
│  │   - Time Series │  │   - Cache       │  │   Storage    │ │
│  │   - Stock Data  │  │   - Sessions    │  │   - Charts   │ │
│  │   - Sentiment   │  │   - Pub/Sub     │  │   - Reports  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 3. 마이크로서비스 상세 설계

### 3.1 주식 데이터 서비스 (Stock Service)
```yaml
서비스명: stock-service
기술스택: FastAPI, Python, asyncio
포트: 8001
데이터베이스: TimescaleDB
캐시: Redis
주요 기능:
  - Yahoo Finance API 통합
  - 실시간 주식 데이터 수집
  - 기술적 지표 계산
  - 과거 데이터 관리
  - 데이터 정규화 및 검증

API 엔드포인트:
  GET /api/v1/stocks/{symbol}/quote
  GET /api/v1/stocks/{symbol}/history
  GET /api/v1/stocks/{symbol}/indicators
  POST /api/v1/stocks/search
  GET /api/v1/stocks/trending
```

### 3.2 소셜 감성 분석 서비스 (Sentiment Service)
```yaml
서비스명: sentiment-service
기술스택: FastAPI, Python, NLTK/spaCy
포트: 8002
데이터베이스: TimescaleDB
캐시: Redis
주요 기능:
  - Reddit API 데이터 수집
  - Twitter API 데이터 수집
  - 감성 분석 (NLP)
  - 감성 점수 계산
  - 트렌드 분석

API 엔드포인트:
  GET /api/v1/sentiment/{symbol}/current
  GET /api/v1/sentiment/{symbol}/history
  GET /api/v1/sentiment/trending
  POST /api/v1/sentiment/analyze
  GET /api/v1/sentiment/sources
```

### 3.3 사용자 서비스 (User Service)
```yaml
서비스명: user-service
기술스택: FastAPI, Python, SQLAlchemy
포트: 8003
데이터베이스: PostgreSQL
캐시: Redis
주요 기능:
  - 사용자 인증 및 권한 부여
  - 사용자 프로필 관리
  - 왓치리스트 관리
  - 설정 및 환경설정
  - PII 데이터 관리

API 엔드포인트:
  POST /api/v1/auth/login
  POST /api/v1/auth/register
  GET /api/v1/users/profile
  PUT /api/v1/users/profile
  GET /api/v1/users/watchlist
  POST /api/v1/users/watchlist
  DELETE /api/v1/users/watchlist/{symbol}
```

### 3.4 알림 서비스 (Notification Service)
```yaml
서비스명: notification-service
기술스택: FastAPI, Python, WebSocket
포트: 8004
데이터베이스: Redis (Pub/Sub)
주요 기능:
  - 실시간 알림 전송
  - 이메일 알림
  - 푸시 알림
  - WebSocket 연결 관리
  - 알림 템플릿 관리

API 엔드포인트:
  POST /api/v1/notifications/send
  GET /api/v1/notifications/history
  WebSocket /ws/notifications/{user_id}
```

### 3.5 분석 서비스 (Analytics Service)
```yaml
서비스명: analytics-service
기술스택: FastAPI, Python, Pandas
포트: 8005
데이터베이스: TimescaleDB
주요 기능:
  - 사용자 행동 분석
  - 시스템 성능 메트릭
  - 보고서 생성
  - 대시보드 데이터 제공
  - 데이터 집계

API 엔드포인트:
  GET /api/v1/analytics/dashboard
  GET /api/v1/analytics/metrics
  GET /api/v1/analytics/reports
  POST /api/v1/analytics/custom
```

### 3.6 상관관계 분석 서비스 (Correlation Service)
```yaml
서비스명: correlation-service
기술스택: FastAPI, Python, NumPy/SciPy
포트: 8006
데이터베이스: TimescaleDB
캐시: Redis
주요 기능:
  - 주식-감성 상관관계 분석
  - 패턴 인식
  - 예측 모델
  - 통계적 분석
  - 시계열 분석

API 엔드포인트:
  GET /api/v1/correlation/{symbol}/sentiment
  GET /api/v1/correlation/patterns
  POST /api/v1/correlation/analyze
  GET /api/v1/correlation/predictions
```

## 4. 데이터 모델 설계

### 4.1 통합 데이터 모델
```python
# 통합 데이터 모델 기본 클래스
class BaseDataModel:
    id: str
    timestamp: datetime
    source: str
    version: str
    metadata: dict

# 주식 데이터 모델
class StockData(BaseDataModel):
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: float
    indicators: dict  # 기술적 지표

# 감성 데이터 모델
class SentimentData(BaseDataModel):
    symbol: str
    platform: str  # reddit, twitter
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    mention_count: int
    keywords: List[str]
    source_urls: List[str]

# 통합 분석 모델
class IntegratedAnalysis(BaseDataModel):
    symbol: str
    stock_data: StockData
    sentiment_data: List[SentimentData]
    correlation_score: float
    trend_prediction: dict
    risk_indicators: dict
```

### 4.2 데이터베이스 스키마
```sql
-- TimescaleDB 주식 데이터 테이블
CREATE TABLE stock_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    adjusted_close DECIMAL(10,2),
    indicators JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 시계열 하이퍼테이블 생성
SELECT create_hypertable('stock_data', 'timestamp', 'symbol', 4);

-- 감성 데이터 테이블
CREATE TABLE sentiment_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    platform VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(3,2),
    confidence DECIMAL(3,2),
    mention_count INTEGER,
    keywords JSONB,
    source_urls JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('sentiment_data', 'timestamp', 'symbol', 4);

-- 상관관계 데이터 테이블
CREATE TABLE correlation_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    analysis_date DATE NOT NULL,
    correlation_coefficient DECIMAL(5,4),
    p_value DECIMAL(10,8),
    sample_size INTEGER,
    analysis_window INTERVAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 5. API Gateway 설계

### 5.1 라우팅 규칙
```yaml
# API Gateway 라우팅 설정
routes:
  # 주식 관련 API
  - path: /api/v1/stocks/*
    service: stock-service
    port: 8001
    auth_required: false
    rate_limit: 100/minute
    
  # 감성 분석 API
  - path: /api/v1/sentiment/*
    service: sentiment-service
    port: 8002
    auth_required: true
    rate_limit: 50/minute
    
  # 사용자 관련 API
  - path: /api/v1/users/*
    service: user-service
    port: 8003
    auth_required: true
    rate_limit: 30/minute
    
  # 알림 API
  - path: /api/v1/notifications/*
    service: notification-service
    port: 8004
    auth_required: true
    rate_limit: 20/minute
    
  # 분석 API
  - path: /api/v1/analytics/*
    service: analytics-service
    port: 8005
    auth_required: true
    rate_limit: 40/minute
    
  # 상관관계 분석 API
  - path: /api/v1/correlation/*
    service: correlation-service
    port: 8006
    auth_required: true
    rate_limit: 30/minute
```

### 5.2 미들웨어 구성
```python
# API Gateway 미들웨어
class GatewayMiddleware:
    def __init__(self):
        self.auth_service = AuthService()
        self.rate_limiter = RateLimiter()
        self.logger = Logger()
        
    async def authenticate(self, request):
        # JWT 토큰 검증
        # API 키 검증
        # OAuth 토큰 검증
        pass
        
    async def rate_limit(self, request):
        # 사용자별 속도 제한
        # IP별 속도 제한
        # 서비스별 속도 제한
        pass
        
    async def log_request(self, request, response):
        # 요청/응답 로깅
        # 성능 메트릭 수집
        # 에러 추적
        pass
```

## 6. 캐싱 전략

### 6.1 다단계 캐싱 아키텍처
```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   In-Memory     │  │   Local Cache   │  │   Session    │ │
│  │   Cache         │  │   (LRU)         │  │   Cache      │ │
│  │   - Objects     │  │   - Queries     │  │   - User     │ │
│  │   - Results     │  │   - Computed    │  │   - Auth     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Distributed Cache                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │     Redis       │  │   Redis Cluster │  │   CDN        │ │
│  │   - API Cache   │  │   - Shared      │  │   - Static   │ │
│  │   - Sessions    │  │   - Persistent  │  │   - Assets   │ │
│  │   - Pub/Sub     │  │   - Backup      │  │   - Charts   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 캐싱 정책
```python
# 캐싱 정책 설정
CACHE_POLICY = {
    # 주식 데이터 캐싱
    "stock_quote": {
        "ttl": 60,  # 1분
        "strategy": "write-through",
        "invalidation": "time-based"
    },
    "stock_history": {
        "ttl": 300,  # 5분
        "strategy": "write-behind",
        "invalidation": "event-based"
    },
    
    # 감성 데이터 캐싱
    "sentiment_current": {
        "ttl": 180,  # 3분
        "strategy": "write-through",
        "invalidation": "time-based"
    },
    "sentiment_history": {
        "ttl": 600,  # 10분
        "strategy": "write-behind",
        "invalidation": "event-based"
    },
    
    # 분석 결과 캐싱
    "correlation_analysis": {
        "ttl": 1800,  # 30분
        "strategy": "write-behind",
        "invalidation": "event-based"
    },
    "technical_indicators": {
        "ttl": 300,  # 5분
        "strategy": "write-through",
        "invalidation": "time-based"
    }
}
```

## 7. 실시간 데이터 동기화

### 7.1 데이터 파이프라인
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Ingestion     │───▶│   Processing    │
│                 │    │                 │    │                 │
│ • Yahoo Finance │    │ • Kafka Topics  │    │ • Stream        │
│ • Reddit API    │    │ • Event Streams │    │   Processing    │
│ • Twitter API   │    │ • Queue         │    │ • Validation    │
│ • Market Data   │    │ • Buffer        │    │ • Enrichment    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Storage       │◀───│   Analytics     │◀───│   Distribution  │
│                 │    │                 │    │                 │
│ • TimescaleDB   │    │ • Real-time     │    │ • WebSocket     │
│ • Redis Cache   │    │   Analytics     │    │ • Pub/Sub       │
│ • Object Store  │    │ • ML Models     │    │ • Push Notif.   │
│ • Backups       │    │ • Alerting      │    │ • API Streaming│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 7.2 WebSocket 실시간 통신
```python
# WebSocket 연결 관리
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
    async def subscribe(self, user_id: str, symbol: str):
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = set()
        self.subscriptions[symbol].add(user_id)
        
    async def broadcast_to_subscribers(self, symbol: str, data: dict):
        if symbol in self.subscriptions:
            for user_id in self.subscriptions[symbol]:
                if user_id in self.active_connections:
                    await self.active_connections[user_id].send_json(data)
```

## 8. 보안 아키텍처

### 8.1 다계층 보안 모델
```
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   WAF           │  │   DDoS          │  │   SSL/TLS     │ │
│  │   Protection    │  │   Protection    │  │   Encryption  │ │
│  │   - OWASP       │  │   - Rate Limit  │  │   - Cert Mgmt │ │
│  │   - XSS/CSRF    │  │   - IP Blocking │  │   - HSTS      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   AuthN/AuthZ   │  │   API Security  │  │   Data       │ │
│  │   - JWT         │  │   - API Keys    │  │   Encryption │ │
│  │   - OAuth 2.0   │  │   - Rate Limit  │  │   - At Rest  │ │
│  │   - MFA         │  │   - Input Valid.│  │   - In Transit│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Database      │  │   Network       │  │   PII        │ │
│  │   Security      │  │   Security      │  │   Protection │ │
│  │   - Encryption  │  │   - VPC        │  │   - Masking  │ │
│  │   - Access Ctrl │  │   - Firewalls  │  │   - Anonym.  │ │
│  │   - Audit Logs  │  │   - VPN        │  │   - GDPR     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 PII 관리 전략
```python
# PII 데이터 관리
class PIIDataManager:
    def __init__(self):
        self.encryption_key = self.get_encryption_key()
        self pii_fields = ['email', 'phone', 'ssn', 'address']
        
    def encrypt_pii(self, data: dict) -> dict:
        # PII 필드 식별 및 암호화
        encrypted_data = data.copy()
        for field in self.pii_fields:
            if field in encrypted_data:
                encrypted_data[field] = self.encrypt(encrypted_data[field])
        return encrypted_data
        
    def mask_pii(self, data: dict, user_role: str) -> dict:
        # 역할 기반 PII 마스킹
        masked_data = data.copy()
        if user_role not in ['admin', 'support']:
            for field in self.pii_fields:
                if field in masked_data:
                    masked_data[field] = self.mask_value(masked_data[field])
        return masked_data
        
    def audit_pii_access(self, user_id: str, action: str, data_type: str):
        # PII 접근 감사 로그
        audit_log = {
            'user_id': user_id,
            'action': action,
            'data_type': data_type,
            'timestamp': datetime.utcnow(),
            'ip_address': self.get_client_ip()
        }
        self.log_audit_event(audit_log)
```

## 9. 구현 로드맵

### 9.1 1단계: 핵심 마이크로서비스 구현 (4-6주)
- **주간 1-2**: Stock Service 구현
- **주간 3-4**: Sentiment Service 구현
- **주간 5-6**: User Service 및 API Gateway 구현

### 9.2 2단계: 데이터 통합 및 캐싱 (3-4주)
- **주간 1-2**: TimescaleDB 데이터베이스 구축
- **주간 3**: Redis 캐싱 시스템 구현
- **주간 4**: 데이터 동기화 파이프라인 구축

### 9.3 3단계: 고급 기능 구현 (3-4주)
- **주간 1-2**: Notification Service 및 WebSocket 구현
- **주간 3**: Analytics Service 구현
- **주간 4**: Correlation Service 구현

### 9.4 4단계: 보안 및 운영 (2-3주)
- **주간 1**: 보안 아키텍처 구현
- **주간 2**: 모니터링 및 로깅 시스템
- **주간 3**: 성능 최적화 및 테스트

### 9.5 5단계: 프론트엔드 재구현 (3-4주)
- **주간 1-2**: React 기반 프론트엔드 구현
- **주간 3**: 모바일 앱 개발
- **주간 4**: 관리자 UI 구현

## 10. 성공 지표

### 10.1 기술적 지표
- **응답 시간**: API 응답 시간 < 200ms (95%ile)
- **가용성**: 시스템 가용성 > 99.9%
- **확장성**: 동시 사용자 10,000명 지원
- **처리량**: 초당 API 요청 50,000개 처리

### 10.2 비즈니스 지표
- **사용자 만족도**: 사용자 만족도 점수 > 4.5/5
- **기능 완성도**: 스펙 요구사항 충족률 > 95%
- **데이터 정확도**: 데이터 정확도 > 99.5%
- **시스템 안정성**: 장애 시간 < 4.3시간/월

## 11. 결론

본 아키텍처 재설계 계획은 현재 단일 모놀리식 애플리케이션을 스펙 요구사항을 충족하는 확장 가능한 마이크로서비스 아키텍처로 전환하기 위한 포괄적인 접근 방식을 제시합니다. 단계적 구현을 통해 시스템 안정성을 유지하면서 점진적으로 기능을 확장할 수 있으며, 각 단계별 명확한 성공 지표를 통해 진행 상황을 효과적으로 모니터링할 수 있습니다.

이 재설계를 통해 시스템은 다음과 같은 이점을 얻게 됩니다:
- **확장성**: 수평적 확장이 가능한 마이크로서비스 아키텍처
- **신뢰성**: 다중 계층의 보안 및 장애 복구 메커니즘
- **성능**: 다단계 캐싱 및 비동기 처리를 통한 고성능
- **유지보수성**: 모듈화된 서비스 구조로 인한 유지보수 용이성
- **확장성**: 새로운 기능 및 서비스의 용이한 추가