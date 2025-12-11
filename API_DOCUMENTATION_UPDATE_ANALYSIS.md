# API 문서 업데이트 분석 보고서

## 1. 개요

본 보고서는 InsiteChart 프로젝트의 API 문서 상태를 분석하고, 실제 구현과의 일관성을 확보하기 위한 개선 방안을 제시합니다. 기존 문서와 현재 백엔드 구현을 비교 분석하여 문서화 격차를 식별하고 통합된 API 스펙을 제안합니다.

## 2. 현재 API 문서 상태 분석

### 2.1 기존 문서 구조

#### 2.1.1 API 통합 스펙 (docs/spec/03-api-integration.md)
- **범위**: 외부 API 연동 전략 중심
- **주요 내용**: 
  - API 클라이언트 팩토리 패턴
  - Yahoo Finance, Reddit, Twitter API 연동
  - 데이터 품질 관리
  - 실시간 데이터 스트리밍
- **문제점**: 내부 API 엔드포인트 스펙 부재

#### 2.1.2 API 게이트웨이 라우팅 (docs/spec/12-api-gateway-routing.md)
- **범위**: 단순화된 API 게이트웨이 구현
- **주요 내용**:
  - 기본 게이트웨이 컴포넌트
  - 인증 및 속도 제한 서비스
  - 라우팅 서비스
- **문제점**: 실제 구현과의 차이 존재

#### 2.1.3 통합 API 스펙 (docs/spec/api-spec-unified.md)
- **범위**: 표준 API 응답 형식 및 엔드포인트 목록
- **주요 내용**:
  - 표준 응답 형식 정의
  - 인증 API, 데이터 소스 API, 분석 API 등
  - 에러 코드 정의
- **문제점**: 실제 구현된 엔드포인트와 불일치

### 2.2 실제 백엔드 구현 분석

#### 2.2.1 메인 애플리케이션 구조 (backend/api/main_app.py)
```python
# 실제 라우터 구조
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(stock_router, prefix="/api/v1/stocks", tags=["Stocks"])
app.include_router(sentiment_router, prefix="/api/v1/sentiment", tags=["Sentiment"])
app.include_router(unified_router, prefix="/api/v1", tags=["Unified"])
app.include_router(correlation_router, prefix="/api/v1", tags=["Correlation"])
app.include_router(ml_trend_router, prefix="/api/v1", tags=["ML Trend"])
app.include_router(auto_scaling_router, prefix="/api/v1", tags=["Auto Scaling"])
app.include_router(monitoring_router, prefix="/api/v1", tags=["Monitoring"])
app.include_router(resource_optimization_router, prefix="/api/v1", tags=["Resource Optimization"])
app.include_router(gdpr_router, prefix="/api/v1", tags=["GDPR"])
app.include_router(threat_detection_router, prefix="/api/v1", tags=["Threat Detection"])
app.include_router(data_encryption_router, prefix="/api/v1", tags=["Data Encryption"])
app.include_router(distributed_data_collector_router, prefix="/api/v1", tags=["Distributed Data Collection"])
app.include_router(timescale_router, prefix="/api/v1", tags=["TimescaleDB"])
app.include_router(automated_test_router, prefix="/api/v1", tags=["Automated Testing"])
app.include_router(i18n_router, prefix="/api/v1", tags=["Internationalization"])
```

#### 2.2.2 통합 라우트 엔드포인트 (backend/api/routes.py)
```python
# 실제 구현된 주요 엔드포인트
@router.get("/health")
@router.post("/stock")
@router.post("/search")
@router.get("/trending")
@router.get("/market/indices")
@router.get("/market/sentiment")
@router.get("/market/statistics")
@router.post("/compare")
@router.post("/sentiment")
@router.post("/correlation")
@router.get("/watchlist/{user_id}")
@router.post("/watchlist")
@router.get("/insights")
@router.get("/quality")
@router.get("/cache/stats")
@router.post("/cache/clear")
```

## 3. 문서와 구현 간 격차 분석

### 3.1 엔드포인트 불일치

#### 3.1.1 누락된 엔드포인트 (문서에는 있으나 구현되지 않음)
| 문서상 엔드포인트 | 실제 구현 상태 | 우선순위 |
|------------------|------------------|----------|
| `POST /api/v1/auth/login` | 구현됨 (auth_router) | 낮음 |
| `POST /api/v1/auth/refresh` | 구현됨 (auth_router) | 낮음 |
| `GET /api/v1/datasources` | 미구현 | 높음 |
| `POST /api/v1/datasources` | 미구현 | 높음 |
| `POST /api/v1/analysis/sentiment` | 부분 구현 (`/sentiment`) | 중간 |
| `GET /api/v1/dashboard/data` | 미구현 | 높음 |
| `WebSocket /ws/realtime` | 미구현 | 중간 |

#### 3.1.2 추가된 엔드포인트 (구현되었으나 문서에 없음)
| 실제 엔드포인트 | 기능 | 문서화 필요성 |
|------------------|------|----------------|
| `GET /api/v1/market/indices` | 시장 지수 데이터 | 높음 |
| `GET /api/v1/market/sentiment` | 시장 감성 분석 | 높음 |
| `GET /api/v1/market/statistics` | 시장 통계 | 높음 |
| `POST /api/v1/compare` | 주식 비교 분석 | 중간 |
| `POST /api/v1/correlation` | 상관관계 분석 | 중간 |
| `GET /api/v1/watchlist/{user_id}` | 관심종목 조회 | 높음 |
| `POST /api/v1/watchlist` | 관심종목 추가 | 높음 |
| `GET /api/v1/insights` | 시장 인사이트 | 중간 |
| `GET /api/v1/quality` | 데이터 품질 리포트 | 중간 |
| `GET /api/v1/cache/stats` | 캐시 통계 | 낮음 |
| `POST /api/v1/cache/clear` | 캐시 삭제 | 낮음 |

### 3.2 응답 형식 불일치

#### 3.2.1 표준 응답 형식
**문서상 형식:**
```json
{
  "success": true,
  "data": { /* 응답 데이터 */ },
  "message": "요청이 성공적으로 처리되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**실제 구현 형식:**
```python
return {
    "success": True,
    "data": stock_data.to_dict(),
    "timestamp": datetime.utcnow().isoformat()
}
```
- **차이점**: `message` 필드 누락

#### 3.2.2 에러 응답 형식
**문서상 형식:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지",
    "details": { /* 상세 에러 정보 */ }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**실제 구현 형식:**
```python
return JSONResponse(
    status_code=exc.status_code,
    content={
        "error": True,
        "message": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat()
    }
)
```
- **차이점**: `error.code`, `error.details` 필드 누락

### 3.3 인증 방식 불일치

#### 3.3.1 문서상 인증
- JWT 토큰 기반 인증
- Bearer 토큰 방식
- API 키 관리 기능

#### 3.3.2 실제 구현
- JWT 토큰 기반 인증 (구현됨)
- `require_auth`, `optional_auth` 미들웨어 사용
- API 키 관리 (부분적으로 구현됨)

### 3.4 레이트 리밋 정책 불일치

#### 3.4.1 문서상 정책
| 엔드포인트 그룹 | 제한 | 시간 윈도우 |
|------------------|------|-------------|
| 인증 API | 5회/IP | 1분 |
| 데이터 API | 100회/사용자 | 1분 |
| 분석 API | 50회/사용자 | 1분 |
| 실시간 API | 10연결/사용자 | 동시 |

#### 3.4.2 실제 구현
- 기본 레이트 리밋 미들웨어 구현됨
- Redis 기반 속도 제한
- 세부 정책은 문서와 불일치 가능성

## 4. API 문서 개선 방안

### 4.1 통합 API 스펙 재구성

#### 4.1.1 새로운 문서 구조 제안
```
docs/spec/
├── api-spec-unified-v2.md          # 통합 API 스펙 (개정판)
├── api-endpoints/                   # 엔드포인트별 상세 스펙
│   ├── authentication.md           # 인증 API
│   ├── stocks.md                   # 주식 API
│   ├── sentiment.md                # 감성 분석 API
│   ├── market.md                   # 시장 데이터 API
│   ├── watchlist.md                # 관심종목 API
│   ├── analysis.md                 # 분석 API
│   ├── monitoring.md               # 모니터링 API
│   └── realtime.md                # 실시간 API
├── api-guides/                     # API 사용 가이드
│   ├── getting-started.md          # 시작 가이드
│   ├── authentication.md           # 인증 가이드
│   ├── error-handling.md           # 에러 처리 가이드
│   └── rate-limiting.md           # 레이트 리밋 가이드
└── api-reference/                  # API 레퍼런스
    ├── openapi.yaml               # OpenAPI 3.0 스펙
    ├── postman-collection.json     # Postman 컬렉션
    └── sdk-examples/              # SDK 예제 코드
```

### 4.2 표준 응답 형식 통일

#### 4.2.1 성공 응답 표준
```python
# 표준 응답 데코레이터
def standard_response(success_msg: str = None):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return {
                "success": True,
                "data": result,
                "message": success_msg or "요청이 성공적으로 처리되었습니다.",
                "timestamp": datetime.utcnow().isoformat()
            }
        return wrapper
    return decorator
```

#### 4.2.2 에러 응답 표준
```python
# 표준 에러 응답 클래스
class APIError(Exception):
    def __init__(self, code: str, message: str, details: Dict = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
    
    def to_response(self):
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            },
            "timestamp": datetime.utcnow().isoformat()
        }
```

### 4.3 OpenAPI 3.0 스펙 자동 생성

#### 4.3.1 FastAPI 자동 문서화 활용
```python
# main_app.py에 추가
app = FastAPI(
    title="InsiteChart API",
    description="Financial analysis and social sentiment platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 커스텀 OpenAPI 스펙
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="InsiteChart API",
        version="2.0.0",
        description="Comprehensive financial analysis and social sentiment platform API",
        routes=app.routes,
    )
    
    # 보안 스킴 추가
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # 전역 보안 요구사항
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### 4.4 API 버전 관리 전략

#### 4.4.1 버전 관리 정책
- **URL 경로 기반**: `/api/v1/`, `/api/v2/`
- **하위 호환성**: 6개월 보장
- **마이그레이션 가이드**: 3개월 전 사전 공지
- **디프리케이션 헤더**: `X-API-Deprecated`, `X-API-Sunset`

#### 4.4.2 버전 마이그레이션 구현
```python
# 버전 마이그레이션 미들웨어
@app.middleware("http")
async def api_version_middleware(request: Request, call_next):
    # v1 요청에 대한 마이그레이션 안내
    if request.url.path.startswith("/api/v1/"):
        response = await call_next(request)
        response.headers["X-API-Deprecated"] = "true"
        response.headers["X-API-Sunset"] = "2025-06-01"
        response.headers["X-API-Migration-Guide"] = "https://docs.insitechart.com/api/v2/migration"
        return response
    
    return await call_next(request)
```

## 5. 구체적인 엔드포인트 스펙 업데이트

### 5.1 주식 API 엔드포인트

#### 5.1.1 주식 데이터 조회
```yaml
/api/v1/stocks/stock:
  post:
    summary: 주식 상세 정보 조회
    description: 특정 주식의 종합 정보와 감성 분석 데이터를 제공합니다.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              symbol:
                type: string
                description: 주식 심볼 (예: AAPL)
                example: "AAPL"
              include_sentiment:
                type: boolean
                description: 감성 분석 포함 여부
                default: true
    responses:
      '200':
        description: 성공 응답
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  $ref: '#/components/schemas/StockData'
                message:
                  type: string
                  example: "주식 정보가 성공적으로 조회되었습니다."
                timestamp:
                  type: string
                  format: date-time
      '404':
        $ref: '#/components/responses/NotFound'
      '500':
        $ref: '#/components/responses/InternalServerError'
```

#### 5.1.2 주식 검색
```yaml
/api/v1/stocks/search:
  post:
    summary: 주식 검색
    description: 통합 주식 검색 기능을 제공합니다.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              query:
                type: string
                description: 검색어
                example: "Apple"
              filters:
                type: object
                description: 검색 필터
                properties:
                  sector:
                    type: string
                    example: "Technology"
                  market_cap:
                    type: string
                    enum: [small, mid, large]
              limit:
                type: integer
                minimum: 1
                maximum: 100
                default: 10
    responses:
      '200':
        description: 성공 응답
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  $ref: '#/components/schemas/SearchResult'
                message:
                  type: string
                  example: "검색이 성공적으로 완료되었습니다."
                timestamp:
                  type: string
                  format: date-time
```

### 5.2 시장 데이터 API 엔드포인트

#### 5.2.1 시장 지수
```yaml
/api/v1/market/indices:
  get:
    summary: 주요 시장 지수 조회
    description: S&P 500, NASDAQ, Dow Jones 등 주요 시장 지수 데이터를 제공합니다.
    responses:
      '200':
        description: 성공 응답
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  type: object
                  properties:
                    indices:
                      type: array
                      items:
                        $ref: '#/components/schemas/MarketIndex'
                    last_updated:
                      type: string
                      format: date-time
                message:
                  type: string
                  example: "시장 지수가 성공적으로 조회되었습니다."
                timestamp:
                  type: string
                  format: date-time
```

#### 5.2.2 시장 감성 분석
```yaml
/api/v1/market/sentiment:
  get:
    summary: 전체 시장 감성 분석
    description: 시장 전체의 감성 분석 결과를 제공합니다.
    responses:
      '200':
        description: 성공 응답
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  $ref: '#/components/schemas/MarketSentiment'
                message:
                  type: string
                  example: "시장 감성 분석이 성공적으로 완료되었습니다."
                timestamp:
                  type: string
                  format: date-time
```

### 5.3 관심종목 API 엔드포인트

#### 5.3.1 관심종목 조회
```yaml
/api/v1/watchlist/{user_id}:
  get:
    summary: 사용자 관심종목 조회
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
      - name: include_sentiment
        in: query
        schema:
          type: boolean
          default: true
      - name: include_alerts
        in: query
        schema:
          type: boolean
          default: true
    security:
      - BearerAuth: []
    responses:
      '200':
        description: 성공 응답
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  $ref: '#/components/schemas/Watchlist'
                message:
                  type: string
                  example: "관심종목이 성공적으로 조회되었습니다."
                timestamp:
                  type: string
                  format: date-time
      '401':
        $ref: '#/components/responses/Unauthorized'
```

## 6. 실시간 API 문서화

### 6.1 WebSocket 연동 스펙

#### 6.1.1 연결 및 인증
```yaml
/ws/realtime:
  get:
    summary: 실시간 데이터 WebSocket 연결
    description: 실시간 주식 데이터, 감성 분석 업데이트를 위한 WebSocket 연결을 제공합니다.
    tags:
      - Realtime
    responses:
      '101':
        description: WebSocket 연결 성공
        content:
          text/plain:
            schema:
              type: string
              example: "WebSocket Protocol Handshake"
    x-websocket:
      connection:
        url: ws://localhost:8000/ws/realtime
        protocol: ws
      authentication:
        type: bearer
        token: JWT_ACCESS_TOKEN
      messages:
        - type: auth
          description: 인증 메시지
          schema:
            type: object
            properties:
              type:
                type: string
                enum: [auth]
              token:
                type: string
                description: JWT 액세스 토큰
        - type: subscribe
          description: 채널 구독
          schema:
            type: object
            properties:
              type:
                type: string
                enum: [subscribe]
              channels:
                type: array
                items:
                  type: string
                  enum: [stock_updates, sentiment_changes, trending_alerts, price_alerts]
```

#### 6.1.2 실시간 데이터 형식
```yaml
RealtimeMessage:
  type: object
  properties:
    type:
      type: string
      enum: [stock_update, sentiment_change, trending_alert, price_alert]
    channel:
      type: string
      description: 메시지 채널
    data:
      type: object
      description: 채널별 데이터
    timestamp:
      type: string
      format: date-time
  required:
    - type
    - channel
    - data
    - timestamp

StockUpdateMessage:
  allOf:
    - $ref: '#/components/schemas/RealtimeMessage'
    - type: object
      properties:
        type:
          const: stock_update
        data:
          $ref: '#/components/schemas/StockUpdateData'

SentimentChangeMessage:
  allOf:
    - $ref: '#/components/schemas/RealtimeMessage'
    - type: object
      properties:
        type:
          const: sentiment_change
        data:
          $ref: '#/components/schemas/SentimentChangeData'
```

## 7. 에러 처리 표준화

### 7.1 에러 코드 체계

#### 7.1.1 인증 에러
| 코드 | HTTP 상태 | 메시지 | 설명 |
|------|-----------|---------|------|
| AUTH_001 | 401 | 인증 토큰이 유효하지 않습니다. | 만료되거나 위조된 토큰 |
| AUTH_002 | 403 | 권한이 없습니다. | 리소스 접근 권한 부족 |
| AUTH_003 | 401 | 로그인 정보가 올바르지 않습니다. | 사용자 이름 또는 비밀번호 오류 |
| AUTH_004 | 429 | 인증 시도 횟수를 초과했습니다. | 과도한 인증 시도 |

#### 7.1.2 데이터 에러
| 코드 | HTTP 상태 | 메시지 | 설명 |
|------|-----------|---------|------|
| DATA_001 | 404 | 데이터를 찾을 수 없습니다. | 요청한 데이터가 존재하지 않음 |
| DATA_002 | 400 | 데이터 형식이 올바르지 않습니다. | 요청 데이터 형식 오류 |
| DATA_003 | 500 | 데이터 처리 중 오류가 발생했습니다. | 서버 내부 데이터 처리 오류 |
| DATA_004 | 422 | 데이터 검증에 실패했습니다. | 입력값 검증 오류 |

#### 7.1.3 비즈니스 로직 에러
| 코드 | HTTP 상태 | 메시지 | 설명 |
|------|-----------|---------|------|
| BIZ_001 | 400 | 주식 심볼이 유효하지 않습니다. | 존재하지 않는 주식 심볼 |
| BIZ_002 | 400 | 분석 기간이 유효하지 않습니다. | 지원되지 않는 기간 설정 |
| BIZ_003 | 429 | API 요청 한도를 초과했습니다. | 레이트 리밋 초과 |
| BIZ_004 | 503 | 외부 데이터 소스를 사용할 수 없습니다. | 외부 API 장애 |

### 7.2 에러 응답 구현

#### 7.2.1 커스텀 에러 핸들러
```python
# api/error_handlers.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(self, code: str, message: str, details: Dict = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code

class AuthenticationError(APIError):
    def __init__(self, code: str, message: str, details: Dict = None):
        super().__init__(code, message, details, 401)

class DataNotFoundError(APIError):
    def __init__(self, resource: str):
        super().__init__(
            "DATA_001",
            f"{resource} 데이터를 찾을 수 없습니다.",
            {"resource": resource},
            404
        )

class RateLimitExceededError(APIError):
    def __init__(self, limit: int, window: int):
        super().__init__(
            "BIZ_003",
            "API 요청 한도를 초과했습니다.",
            {"limit": limit, "window": window},
            429
        )

def setup_error_handlers(app):
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        logger.error(f"API Error: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response()
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "details": {}
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## 8. API 테스트 및 검증

### 8.1 자동화된 API 테스트

#### 8.1.1 Postman 컬렉션 생성
```json
{
  "info": {
    "name": "InsiteChart API v2",
    "description": "Comprehensive API testing collection",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api/v2"
    },
    {
      "key": "access_token",
      "value": ""
    }
  ],
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"test_user\",\n  \"password\": \"test_password\"\n}"
            },
            "url": {
              "raw": "{{base_url}}/auth/login",
              "host": ["{{base_url}}"],
              "path": ["auth", "login"]
            }
          },
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "if (pm.response.code === 200) {",
                  "    const response = pm.response.json();",
                  "    pm.collectionVariables.set('access_token', response.data.access_token);",
                  "}"
                ]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

#### 8.1.2 자동화된 API 테스트 스위트
```python
# tests/api/test_api_compliance.py
import pytest
from fastapi.testclient import TestClient
from backend.api.main_app import app

client = TestClient(app)

class TestAPICompliance:
    """API 스펙 준수 테스트"""
    
    def test_standard_response_format(self):
        """표준 응답 형식 준수 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # 필수 필드 확인
        assert "success" in data
        assert "data" in data
        assert "timestamp" in data
        
        # 타입 확인
        assert isinstance(data["success"], bool)
        assert isinstance(data["timestamp"], str)
    
    def test_error_response_format(self):
        """에러 응답 형식 준수 테스트"""
        response = client.post("/api/v1/stocks/stock", json={"symbol": "INVALID"})
        
        assert response.status_code in [404, 400]
        data = response.json()
        
        # 필수 필드 확인
        assert "success" in data
        assert data["success"] == False
        assert "error" in data
        assert "timestamp" in data
        
        # 에러 객체 필드 확인
        assert "code" in data["error"]
        assert "message" in data["error"]
    
    def test_authentication_required(self):
        """인증 필요 엔드포인트 테스트"""
        response = client.get("/api/v1/watchlist/test_user")
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] in ["AUTH_001", "HTTP_401"]
    
    def test_rate_limiting(self):
        """레이트 리밋 테스트"""
        # 다수의 요청 전송
        for _ in range(10):
            response = client.get("/health")
        
        # 레이트 리밋 확인
        response = client.get("/health")
        # 실제 구현에 따라 조정 필요
        assert response.status_code in [200, 429]
```

### 8.2 API 스펙 검증 체크리스트

#### 8.2.1 문서화 품질 체크리스트
- [ ] 모든 엔드포인트가 OpenAPI 3.0 스펙으로 정의되었는가?
- [ ] 요청/응답 스키마가 상세하게 정의되었는가?
- [ ] 에러 응답이 모든 시나리오를 포함하는가?
- [ ] 인증 방식이 명확하게 문서화되었는가?
- [ ] 레이트 리밋 정책이 명시되었는가?
- [ ] 예제 코드와 사용법이 제공되는가?

#### 8.2.2 구현 일관성 체크리스트
- [ ] 모든 엔드포인트가 표준 응답 형식을 따르는가?
- [ ] 에러 코드가 일관되게 사용되는가?
- [ ] 인증 미들웨어가 올바르게 적용되는가?
- [ ] 레이트 리밋이 문서대로 동작하는가?
- [ ] 버전 관리 정책이 준수되는가?

## 9. 구현 로드맵

### 9.1 단계별 구현 계획

#### 9.1.1 1단계: 기본 스펙 정비 (1주)
- **목표**: 현재 구현된 엔드포인트의 정확한 문서화
- **작업**:
  - 실제 구현된 엔드포인트 목록화
  - OpenAPI 3.0 스펙 자동 생성 설정
  - 표준 응답 형식 통일
  - 기본 에러 처리 개선

#### 9.1.2 2단계: 누락된 기능 문서화 (1주)
- **목표**: 문서에만 존재하는 기능의 구현 또는 제거
- **작업**:
  - 데이터 소스 API 엔드포인트 구현 또는 문서 제거
  - 대시보드 API 엔드포인트 구현 또는 문서 제거
  - 실시간 WebSocket API 구현 또는 문서 제거
  - API 키 관리 기능 완성

#### 9.1.3 3단계: 고급 기능 문서화 (2주)
- **목표**: 복잡한 기능의 상세 문서화
- **작업**:
  - 상관관계 분석 API 상세 스펙
  - ML 트렌드 감지 API 문서화
  - 자동 스케일링 API 문서화
  - 보안 관련 API 문서화

#### 9.1.4 4단계: 개발자 도구 제공 (1주)
- **목표**: API 사용 편의성 향상
- **작업**:
  - Postman 컬렉션 완성
  - SDK 예제 코드 제공
  - 인터랙티브 API 문서 개선
  - API 테스트 자동화

### 9.2 성공 지표

#### 9.2.1 문서화 품질 지표
- **커버리지**: 95% 이상의 엔드포인트가 문서화
- **정확성**: 100%의 문서화된 엔드포인트가 실제 구현과 일치
- **완성도**: 모든 엔드포인트가 요청/응답 스키마 포함
- **사용성**: 개발자 만족도 90% 이상

#### 9.2.2 개발자 경험 지표
- **온보딩 시간**: 신규 개발자 API 적응 시간 50% 감소
- **지원 요청**: API 관련 문의 30% 감소
- **에러율**: API 사용 오류 40% 감소
- **개발 속도**: API 통합 개발 시간 25% 단축

## 10. 결론 및 권장 사항

### 10.1 핵심 문제점 요약

1. **문서-구현 불일치**: 기존 문서와 실제 구현 간 상당한 격차 존재
2. **표준화 부족**: 응답 형식, 에러 처리 등 표준화 미흡
3. **누락된 기능**: 문서에만 존재하는 기능 다수 발견
4. **개발자 경험**: API 사용 편의성을 위한 도구 부족

### 10.2 우선순위별 개선 방안

#### 10.2.1 즉시 실행 (High Priority)
1. **표준 응답 형식 통일**: 모든 엔드포인트의 응답 형식 표준화
2. **OpenAPI 3.0 스펙 자동화**: FastAPI의 자동 문서화 기능 활용
3. **실제 구현 기반 문서화**: 현재 구현된 엔드포인트 중심으로 문서 재구성

#### 10.2.2 단기 실행 (Medium Priority)
1. **누락된 엔드포인트 구현**: 문서에만 존재하는 기능 구현 또는 제거
2. **에러 처리 표준화**: 통합된 에러 코드 및 응답 형식 적용
3. **인증 시스템 완성**: JWT 기반 인증 및 API 키 관리 기능 완성

#### 10.2.3 장기 실행 (Low Priority)
1. **고급 기능 문서화**: ML, 자동화, 보안 관련 기능 상세 문서화
2. **개발자 도구 제공**: SDK, 예제 코드, 테스트 도구 제공
3. **실시간 API 구현**: WebSocket 기반 실시간 데이터 전송 기능 구현

### 10.3 최종 권장 사항

1. **단계적 접근**: 현재 구현된 기능부터 문서화하여 즉각적인 가치 창출
2. **자동화 강화**: OpenAPI 스펙 자동 생성으로 문서-구현 동기화 보장
3. **개발자 중심**: API 사용 편의성을 최우선으로 고려한 문서화 전략
4. **지속적 개선**: 정기적인 API 스펙 검토 및 업데이트 프로세스 수립

이러한 개선 방안을 통해 InsiteChart API는 개발자에게 일관되고 신뢰성 높은 인터페이스를 제공하여 플랫폼의 성공적인 확장에 기여할 수 있을 것입니다.