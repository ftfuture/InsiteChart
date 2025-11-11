# API 게이트웨이 및 라우팅 구현 계획

## 1. 개요

Enhanced Stock Search와 Social Sentiment Tracker를 통합하기 위한 API 게이트웨이를 설계합니다. 이 게이트웨이는 단일 진입점을 제공하고, 요청을 적절한 서비스로 라우팅하며, 인증, 속도 제한, 로깅 등의 공통 기능을 처리합니다.

## 2. API 게이트웨이 아키텍처

### 2.1 고수준 아키텍처

```mermaid
graph TB
    A[Client] --> B[API Gateway]
    
    B --> C[Authentication Service]
    B --> D[Rate Limiting Service]
    B --> E[Logging Service]
    B --> F[Request Router]
    
    F --> G[Stock Search Service]
    F --> H[Sentiment Service]
    F --> I[Unified Service]
    
    G --> J[Yahoo Finance API]
    H --> K[Reddit API]
    H --> L[Twitter API]
    
    I --> M[Unified Data Store]
    I --> N[Cache Layer]
    
    subgraph "API Gateway Components"
        C
        D
        E
        F
    end
    
    subgraph "Backend Services"
        G
        H
        I
    end
    
    subgraph "External APIs"
        J
        K
        L
    end
    
    subgraph "Data Layer"
        M
        N
    end
```

### 2.2 요청 처리 흐름

```mermaid
sequenceDiagram
    participant C as Client
    participant AG as API Gateway
    participant AU as Auth Service
    participant RL as Rate Limiter
    participant RS as Router Service
    participant SS as Stock Search
    participant ST as Sentiment Service
    participant US as Unified Service
    
    C->>AG: API Request
    AG->>AU: Authentication Check
    AU-->>AG: Auth Result
    
    alt Auth Success
        AG->>RL: Rate Limiting Check
        RL-->>AG: Rate Limit Result
        
        alt Within Limits
            AG->>RS: Route Request
            RS->>SS: Forward to Stock Search
            SS-->>RS: Response
            RS-->>AG: Response
            AG-->>C: API Response
        else Rate Limited
            AG-->>C: 429 Too Many Requests
        end
    else Auth Failed
        AG-->>C: 401 Unauthorized
    end
```

## 3. API 게이트웨이 구현

### 3.1 핵심 게이트웨이 컴포넌트

```python
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime, timedelta
import json
import redis.asyncio as redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

class APIGateway:
    """API 게이트웨이 메인 클래스"""
    
    def __init__(self, redis_url: str):
        self.app = FastAPI(
            title="InsiteChart API Gateway",
            description="Unified API Gateway for Stock Search and Social Sentiment",
            version="1.0.0"
        )
        
        # 의존성 초기화
        self.auth_service = AuthenticationService()
        self.rate_limiter = RateLimitingService(redis_url)
        self.logger_service = LoggingService()
        self.router_service = RouterService()
        
        # 미들웨어 설정
        self._setup_middleware()
        
        # 라우트 등록
        self._register_routes()
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_middleware(self):
        """미들웨어 설정"""
        # CORS 미들웨어
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 실제 운영에서는 특정 도메인으로 제한
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 요청 로깅 미들웨어
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = datetime.now()
            
            # 요청 정보 로깅
            self.logger_service.log_request(request)
            
            # 요청 처리
            response = await call_next(request)
            
            # 응답 정보 로깅
            process_time = (datetime.now() - start_time).total_seconds()
            self.logger_service.log_response(request, response, process_time)
            
            # 응답 헤더에 처리 시간 추가
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        
        # 에러 핸들링 미들웨어
        @self.app.middleware("http")
        async def handle_errors(request: Request, call_next):
            try:
                return await call_next(request)
            except Exception as e:
                self.logger.error(f"Unhandled error: {str(e)}")
                return self._create_error_response(500, "Internal Server Error")
    
    def _register_routes(self):
        """라우트 등록"""
        
        # 헬스 체크
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # API 버전 정보
        @self.app.get("/api/v1/info")
        async def api_info():
            return {
                "name": "InsiteChart API Gateway",
                "version": "1.0.0",
                "services": ["stock-search", "sentiment", "unified"],
                "timestamp": datetime.now().isoformat()
            }
        
        # 통합 검색 엔드포인트
        @self.app.get("/api/v1/stocks/search")
        async def search_stocks(
            request: Request,
            q: str,
            limit: int = 10,
            filters: Optional[str] = None,
            include_sentiment: bool = False
        ):
            """통합 주식 검색"""
            
            # 인증 확인
            auth_result = await self.auth_service.authenticate(request)
            if not auth_result.success:
                raise HTTPException(status_code=401, detail=auth_result.message)
            
            # 속도 제한 확인
            rate_limit_result = await self.rate_limiter.check_limit(
                auth_result.user_id, "search"
            )
            if not rate_limit_result.allowed:
                raise HTTPException(
                    status_code=429, 
                    detail=rate_limit_result.message
                )
            
            # 요청 라우팅
            route_request = RouteRequest(
                path="/stocks/search",
                method="GET",
                params={
                    "query": q,
                    "limit": limit,
                    "filters": filters,
                    "include_sentiment": include_sentiment
                },
                user_id=auth_result.user_id
            )
            
            response = await self.router_service.route(route_request)
            return response.data
        
        # 주식 상세 정보 엔드포인트
        @self.app.get("/api/v1/stocks/{symbol}")
        async def get_stock_details(
            request: Request,
            symbol: str,
            include_sentiment: bool = True
        ):
            """주식 상세 정보 (센티먼트 포함)"""
            
            # 인증 확인
            auth_result = await self.auth_service.authenticate(request)
            if not auth_result.success:
                raise HTTPException(status_code=401, detail=auth_result.message)
            
            # 속도 제한 확인
            rate_limit_result = await self.rate_limiter.check_limit(
                auth_result.user_id, "stock_details"
            )
            if not rate_limit_result.allowed:
                raise HTTPException(
                    status_code=429, 
                    detail=rate_limit_result.message
                )
            
            # 요청 라우팅
            route_request = RouteRequest(
                path=f"/stocks/{symbol}",
                method="GET",
                params={
                    "symbol": symbol,
                    "include_sentiment": include_sentiment
                },
                user_id=auth_result.user_id
            )
            
            response = await self.router_service.route(route_request)
            return response.data
        
        # 센티먼트 데이터 엔드포인트
        @self.app.get("/api/v1/sentiment/{symbol}")
        async def get_sentiment_data(
            request: Request,
            symbol: str,
            timeframe: str = "24h"
        ):
            """센티먼트 데이터 조회"""
            
            # 인증 확인
            auth_result = await self.auth_service.authenticate(request)
            if not auth_result.success:
                raise HTTPException(status_code=401, detail=auth_result.message)
            
            # 속도 제한 확인
            rate_limit_result = await self.rate_limiter.check_limit(
                auth_result.user_id, "sentiment"
            )
            if not rate_limit_result.allowed:
                raise HTTPException(
                    status_code=429, 
                    detail=rate_limit_result.message
                )
            
            # 요청 라우팅
            route_request = RouteRequest(
                path=f"/sentiment/{symbol}",
                method="GET",
                params={
                    "symbol": symbol,
                    "timeframe": timeframe
                },
                user_id=auth_result.user_id
            )
            
            response = await self.router_service.route(route_request)
            return response.data
        
        # 트렌딩 주식 엔드포인트
        @self.app.get("/api/v1/trending")
        async def get_trending_stocks(
            request: Request,
            limit: int = 20,
            timeframe: str = "24h"
        ):
            """트렌딩 주식 조회"""
            
            # 인증 확인
            auth_result = await self.auth_service.authenticate(request)
            if not auth_result.success:
                raise HTTPException(status_code=401, detail=auth_result.message)
            
            # 속도 제한 확인
            rate_limit_result = await self.rate_limiter.check_limit(
                auth_result.user_id, "trending"
            )
            if not rate_limit_result.allowed:
                raise HTTPException(
                    status_code=429, 
                    detail=rate_limit_result.message
                )
            
            # 요청 라우팅
            route_request = RouteRequest(
                path="/trending",
                method="GET",
                params={
                    "limit": limit,
                    "timeframe": timeframe
                },
                user_id=auth_result.user_id
            )
            
            response = await self.router_service.route(route_request)
            return response.data
    
    def _create_error_response(self, status_code: int, message: str) -> Response:
        """에러 응답 생성"""
        error_data = {
            "error": {
                "code": status_code,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        }
        return Response(
            content=json.dumps(error_data),
            status_code=status_code,
            media_type="application/json"
        )
    
    def get_app(self) -> FastAPI:
        """FastAPI 애플리케이션 반환"""
        return self.app
```

### 3.2 인증 서비스

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
import jwt
from datetime import datetime, timedelta
import bcrypt

@dataclass
class AuthResult:
    """인증 결과"""
    success: bool
    user_id: Optional[str] = None
    message: Optional[str] = None
    permissions: List[str] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

class AuthenticationService(ABC):
    """인증 서비스 인터페이스"""
    
    @abstractmethod
    async def authenticate(self, request: Request) -> AuthResult:
        """요청 인증"""
        pass

class JWTAuthenticationService(AuthenticationService):
    """JWT 기반 인증 서비스"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry = timedelta(hours=24)
        self.logger = logging.getLogger(__name__)
    
    async def authenticate(self, request: Request) -> AuthResult:
        """JWT 토큰으로 요청 인증"""
        try:
            # Authorization 헤더에서 토큰 추출
            authorization = request.headers.get("Authorization")
            if not authorization:
                return AuthResult(
                    success=False,
                    message="Missing Authorization header"
                )
            
            # Bearer 토큰 파싱
            parts = authorization.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return AuthResult(
                    success=False,
                    message="Invalid Authorization header format"
                )
            
            token = parts[1]
            
            # JWT 토큰 검증
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # 토큰 만료 확인
            if payload.get("exp") < datetime.utcnow().timestamp():
                return AuthResult(
                    success=False,
                    message="Token expired"
                )
            
            # 사용자 정보 추출
            user_id = payload.get("user_id")
            permissions = payload.get("permissions", [])
            
            return AuthResult(
                success=True,
                user_id=user_id,
                permissions=permissions
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                message="Token expired"
            )
        except jwt.InvalidTokenError as e:
            self.logger.error(f"Invalid token: {str(e)}")
            return AuthResult(
                success=False,
                message="Invalid token"
            )
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return AuthResult(
                success=False,
                message="Authentication failed"
            )
    
    def generate_token(self, user_id: str, permissions: List[str] = None) -> str:
        """JWT 토큰 생성"""
        payload = {
            "user_id": user_id,
            "permissions": permissions or [],
            "exp": datetime.utcnow() + self.token_expiry,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )

class APIKeyAuthenticationService(AuthenticationService):
    """API 키 기반 인증 서비스"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
    
    async def authenticate(self, request: Request) -> AuthResult:
        """API 키로 요청 인증"""
        try:
            # API 키 추출
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                return AuthResult(
                    success=False,
                    message="Missing API key"
                )
            
            # Redis에서 API 키 정보 조회
            key_data = await self.redis.get(f"api_key:{api_key}")
            if not key_data:
                return AuthResult(
                    success=False,
                    message="Invalid API key"
                )
            
            key_info = json.loads(key_data)
            
            # API 키 만료 확인
            if key_info.get("expires_at"):
                expires_at = datetime.fromisoformat(key_info["expires_at"])
                if datetime.utcnow() > expires_at:
                    return AuthResult(
                        success=False,
                        message="API key expired"
                    )
            
            return AuthResult(
                success=True,
                user_id=key_info["user_id"],
                permissions=key_info.get("permissions", [])
            )
            
        except Exception as e:
            self.logger.error(f"API key authentication error: {str(e)}")
            return AuthResult(
                success=False,
                message="Authentication failed"
            )
```

### 3.3 속도 제한 서비스

```python
from dataclasses import dataclass
from typing import Dict, Optional
import asyncio
import redis.asyncio as redis

@dataclass
class RateLimitResult:
    """속도 제한 결과"""
    allowed: bool
    remaining: int
    reset_time: datetime
    message: Optional[str] = None

class RateLimitingService:
    """속도 제한 서비스"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
        
        # 기본 속도 제한 정책
        self.default_policies = {
            "search": {"requests": 100, "window": 3600},  # 100 requests/hour
            "stock_details": {"requests": 200, "window": 3600},  # 200 requests/hour
            "sentiment": {"requests": 150, "window": 3600},  # 150 requests/hour
            "trending": {"requests": 50, "window": 3600}  # 50 requests/hour
        }
    
    async def check_limit(self, user_id: str, operation: str) -> RateLimitResult:
        """속도 제한 확인"""
        try:
            # 정책 조회
            policy = self.default_policies.get(operation)
            if not policy:
                # 기본 정책 적용
                policy = {"requests": 100, "window": 3600}
            
            # Redis 키 생성
            key = f"rate_limit:{user_id}:{operation}"
            
            # 현재 요청 수 확인
            current_count = await self.redis.get(key)
            current_count = int(current_count) if current_count else 0
            
            # 속도 제한 확인
            if current_count >= policy["requests"]:
                # 재설정 시간 계산
                ttl = await self.redis.ttl(key)
                reset_time = datetime.now() + timedelta(seconds=ttl)
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=reset_time,
                    message=f"Rate limit exceeded for {operation}. Try again later."
                )
            
            # 요청 수 증가
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, policy["window"])
            await pipe.execute()
            
            # 업데이트된 요청 수 확인
            new_count = await self.redis.get(key)
            new_count = int(new_count)
            
            # 남은 요청 수 계산
            remaining = policy["requests"] - new_count
            
            # 재설정 시간 계산
            ttl = await self.redis.ttl(key)
            reset_time = datetime.now() + timedelta(seconds=ttl)
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_time=reset_time
            )
            
        except Exception as e:
            self.logger.error(f"Rate limiting error: {str(e)}")
            # 에러 발생 시 요청 허용
            return RateLimitResult(
                allowed=True,
                remaining=100,
                reset_time=datetime.now() + timedelta(hours=1)
            )
    
    async def reset_limit(self, user_id: str, operation: str):
        """속도 제한 재설정"""
        try:
            key = f"rate_limit:{user_id}:{operation}"
            await self.redis.delete(key)
            self.logger.info(f"Reset rate limit for user {user_id}, operation {operation}")
        except Exception as e:
            self.logger.error(f"Error resetting rate limit: {str(e)}")
    
    async def get_usage_stats(self, user_id: str, operation: str) -> Dict:
        """사용량 통계 조회"""
        try:
            key = f"rate_limit:{user_id}:{operation}"
            current_count = await self.redis.get(key)
            current_count = int(current_count) if current_count else 0
            
            policy = self.default_policies.get(operation)
            if not policy:
                policy = {"requests": 100, "window": 3600}
            
            ttl = await self.redis.ttl(key)
            reset_time = datetime.now() + timedelta(seconds=ttl)
            
            return {
                "operation": operation,
                "current_usage": current_count,
                "limit": policy["requests"],
                "remaining": max(0, policy["requests"] - current_count),
                "reset_time": reset_time.isoformat(),
                "window_seconds": policy["window"]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting usage stats: {str(e)}")
            return {}
```

### 3.4 라우팅 서비스

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import asyncio
import httpx
from enum import Enum

class ServiceType(Enum):
    STOCK_SEARCH = "stock_search"
    SENTIMENT = "sentiment"
    UNIFIED = "unified"

@dataclass
class RouteRequest:
    """라우팅 요청"""
    path: str
    method: str
    params: Dict[str, Any]
    user_id: str
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

@dataclass
class RouteResponse:
    """라우팅 응답"""
    success: bool
    data: Any
    status_code: int
    headers: Dict[str, str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

class RouterService:
    """라우팅 서비스"""
    
    def __init__(self):
        self.service_registry = {
            ServiceType.STOCK_SEARCH: {
                "base_url": "http://stock-search-service:8000",
                "health_endpoint": "/health"
            },
            ServiceType.SENTIMENT: {
                "base_url": "http://sentiment-service:8000",
                "health_endpoint": "/health"
            },
            ServiceType.UNIFIED: {
                "base_url": "http://unified-service:8000",
                "health_endpoint": "/health"
            }
        }
        
        # 라우팅 규칙 정의
        self.routing_rules = [
            {
                "path_pattern": r"/stocks/search",
                "method": "GET",
                "service": ServiceType.UNIFIED,
                "endpoint": "/api/v1/search",
                "transform_params": self._transform_search_params
            },
            {
                "path_pattern": r"/stocks/([^/]+)",
                "method": "GET",
                "service": ServiceType.UNIFIED,
                "endpoint": "/api/v1/stocks/{symbol}",
                "transform_params": self._transform_stock_params
            },
            {
                "path_pattern": r"/sentiment/([^/]+)",
                "method": "GET",
                "service": ServiceType.SENTIMENT,
                "endpoint": "/api/v1/sentiment/{symbol}",
                "transform_params": self._transform_sentiment_params
            },
            {
                "path_pattern": r"/trending",
                "method": "GET",
                "service": ServiceType.SENTIMENT,
                "endpoint": "/api/v1/trending",
                "transform_params": self._transform_trending_params
            }
        ]
        
        self.logger = logging.getLogger(__name__)
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def route(self, request: RouteRequest) -> RouteResponse:
        """요청 라우팅"""
        try:
            # 라우팅 규칙 찾기
            rule = self._find_routing_rule(request.path, request.method)
            if not rule:
                return RouteResponse(
                    success=False,
                    data=None,
                    status_code=404,
                    error_message=f"No routing rule found for {request.method} {request.path}"
                )
            
            # 서비스 상태 확인
            service_healthy = await self._check_service_health(rule["service"])
            if not service_healthy:
                # 폴백 서비스 찾기
                fallback_rule = self._find_fallback_rule(request.path, request.method)
                if fallback_rule:
                    rule = fallback_rule
                    self.logger.warning(f"Using fallback service for {request.path}")
                else:
                    return RouteResponse(
                        success=False,
                        data=None,
                        status_code=503,
                        error_message="Service unavailable"
                    )
            
            # 파라미터 변환
            transformed_params = rule["transform_params"](request.params)
            
            # 요청 URL 생성
            url = self._build_url(rule["service"], rule["endpoint"], transformed_params)
            
            # 요청 헤더 준비
            headers = {
                "X-User-ID": request.user_id,
                "X-Request-ID": self._generate_request_id(),
                **request.headers
            }
            
            # 서비스로 요청 전송
            response = await self._send_request(
                method=request.method,
                url=url,
                params=transformed_params,
                headers=headers
            )
            
            return RouteResponse(
                success=response.status_code < 400,
                data=response.json() if response.content else None,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except Exception as e:
            self.logger.error(f"Routing error: {str(e)}")
            return RouteResponse(
                success=False,
                data=None,
                status_code=500,
                error_message="Internal routing error"
            )
    
    def _find_routing_rule(self, path: str, method: str) -> Optional[Dict]:
        """라우팅 규칙 찾기"""
        import re
        
        for rule in self.routing_rules:
            if rule["method"] != method:
                continue
            
            if re.match(rule["path_pattern"], path):
                return rule
        
        return None
    
    def _find_fallback_rule(self, path: str, method: str) -> Optional[Dict]:
        """폴백 라우팅 규칙 찾기"""
        # 간단한 폴백 로직: 모든 요청을 통합 서비스로 라우팅
        if method == "GET":
            return {
                "path_pattern": r".*",
                "method": "GET",
                "service": ServiceType.UNIFIED,
                "endpoint": "/api/v1/fallback" + path,
                "transform_params": lambda params: params
            }
        
        return None
    
    async def _check_service_health(self, service_type: ServiceType) -> bool:
        """서비스 상태 확인"""
        try:
            service_config = self.service_registry[service_type]
            health_url = service_config["base_url"] + service_config["health_endpoint"]
            
            response = await self.http_client.get(health_url)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Health check error for {service_type}: {str(e)}")
            return False
    
    def _build_url(self, service_type: ServiceType, endpoint: str, params: Dict) -> str:
        """요청 URL 빌드"""
        import re
        
        service_config = self.service_registry[service_type]
        base_url = service_config["base_url"]
        
        # 경로 파라미터 치환
        for key, value in params.items():
            if f"{{{key}}}" in endpoint:
                endpoint = endpoint.replace(f"{{{key}}}", str(value))
        
        return base_url + endpoint
    
    async def _send_request(self, method: str, url: str, params: Dict, headers: Dict) -> httpx.Response:
        """HTTP 요청 전송"""
        if method == "GET":
            return await self.http_client.get(url, params=params, headers=headers)
        elif method == "POST":
            return await self.http_client.post(url, json=params, headers=headers)
        elif method == "PUT":
            return await self.http_client.put(url, json=params, headers=headers)
        elif method == "DELETE":
            return await self.http_client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    def _transform_search_params(self, params: Dict) -> Dict:
        """검색 파라미터 변환"""
        return {
            "q": params.get("query"),
            "limit": params.get("limit", 10),
            "filters": params.get("filters"),
            "include_sentiment": params.get("include_sentiment", False)
        }
    
    def _transform_stock_params(self, params: Dict) -> Dict:
        """주식 파라미터 변환"""
        return {
            "symbol": params.get("symbol"),
            "include_sentiment": params.get("include_sentiment", True)
        }
    
    def _transform_sentiment_params(self, params: Dict) -> Dict:
        """센티먼트 파라미터 변환"""
        return {
            "symbol": params.get("symbol"),
            "timeframe": params.get("timeframe", "24h")
        }
    
    def _transform_trending_params(self, params: Dict) -> Dict:
        """트렌딩 파라미터 변환"""
        return {
            "limit": params.get("limit", 20),
            "timeframe": params.get("timeframe", "24h")
        }
    
    def _generate_request_id(self) -> str:
        """요청 ID 생성"""
        import uuid
        return str(uuid.uuid4())
```

## 4. 구현 계획

### 4.1 Phase 1: 기본 게이트웨이 구현 (1주일)

#### 4.1.1 핵심 게이트웨이 컴포넌트 구현
- APIGateway 기본 클래스 구현
- 기본 미들웨어 설정 (CORS, 로깅, 에러 핸들링)
- 헬스 체크 및 API 정보 엔드포인트 구현

#### 4.1.2 인증 서비스 구현
- JWTAuthenticationService 구현
- APIKeyAuthenticationService 구현
- 인증 미들웨어 통합

### 4.2 Phase 2: 속도 제한 및 라우팅 (1주일)

#### 4.2.1 속도 제한 서비스 구현
- RateLimitingService 구현
- Redis 기반 속도 제한 로직
- 속도 제한 미들웨어 통합

#### 4.2.2 라우팅 서비스 구현
- RouterService 구현
- 라우팅 규칙 정의 및 적용
- 서비스 상태 확인 및 폴백 메커니즘

### 4.3 Phase 3: API 엔드포인트 통합 (1주일)

#### 4.3.1 통합 검색 엔드포인트
- /api/v1/stocks/search 엔드포인트 구현
- 검색 파라미터 처리 및 라우팅
- 응답 형식 표준화

#### 4.3.2 주식 상세 정보 엔드포인트
- /api/v1/stocks/{symbol} 엔드포인트 구현
- 센티먼트 데이터 통합
- 캐싱 전략 적용

#### 4.3.3 센티먼트 및 트렌딩 엔드포인트
- /api/v1/sentiment/{symbol} 엔드포인트 구현
- /api/v1/trending 엔드포인트 구현
- 실시간 데이터 처리

### 4.4 Phase 4: 고도화 및 테스트 (1주일)

#### 4.4.1 고급 기능 구현
- 요청 추적 및 모니터링
- 동적 라우팅 규칙 관리
- 서비스 디스커버리 메커니즘

#### 4.4.2 통합 테스트
- end-to-end API 테스트
- 부하 테스트 및 성능 최적화
- 보안 테스트

## 5. 기술적 고려사항

### 5.1 성능 최적화
1. **연결 풀링**: HTTP 클라이언트 연결 풀 사용
2. **요청 캐싱**: 자주 요청되는 데이터 캐싱
3. **비동기 처리**: 모든 I/O 작업 비동기 처리

### 5.2 모니터링 및 로깅
1. **요청 추적**: 모든 API 요청에 고유 ID 부여
2. **성능 메트릭**: 응답 시간, 에러율 등 수집
3. **구조화된 로깅**: JSON 형식의 구조화된 로그

### 5.3 보안
1. **HTTPS 적용**: 모든 API 통신에 HTTPS 적용
2. **입력 검증**: 모든 입력 데이터 검증 및 정제
3. **보안 헤더**: 보안 관련 HTTP 헤더 설정

### 5.4 확장성
1. **수평적 확장**: 여러 인스턴스에서 실행 가능한 구조
2. **동적 구성**: 런타임에 라우팅 규칙 변경 가능
3. **서비스 디스커버리**: 새로운 서비스 자동 등록

## 6. 성공 지표

### 6.1 기술적 지표
- API 응답 시간: 95%의 요청이 200ms 이내 응답
- 가용성: 99.9% 이상의 서비스 가용성
- 처리량: 초당 1,000개 이상의 요청 처리
- 에러율: 0.1% 이하의 API 에러율

### 6.2 기능적 지표
- 라우팅 정확도: 100%의 요청이 올바른 서비스로 라우팅
- 인증 성공률: 99% 이상의 유효한 인증 요청 성공
- 속도 제한 정확도: 99% 이상의 속도 제한 정확한 적용

이 API 게이트웨이 및 라우팅 구현 계획을 통해 Enhanced Stock Search와 Social Sentiment Tracker를 효과적으로 통합하고, 단일 진입점을 제공하며, 확장성과 안정성을 확보할 수 있습니다.