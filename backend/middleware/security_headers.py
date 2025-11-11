"""
보안 헤더 미들웨어 모듈
HTTP 보안 헤더 설정 및 CSP(Content Security Policy) 관리
"""

import os
from typing import Dict, List, Optional, Set
from fastapi import Request, Response
try:
    from fastapi.middleware import BaseHTTPMiddleware
except ImportError:
    from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 미들웨어 클래스"""
    
    def __init__(
        self,
        app,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        enable_cors: bool = True,
        custom_csp: Optional[str] = None,
        trusted_origins: Optional[List[str]] = None,
        x_frame_options: Optional[str] = None,
        x_content_type_options: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(app)
        
        # 환경 설정
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.enable_cors = enable_cors
        self.is_production = os.getenv("ENVIRONMENT", "development") == "production"
        
        # 신뢰할 수 있는 출처 목록
        self.trusted_origins = trusted_origins or [
            "https://insitechart.com",
            "https://www.insitechart.com",
            "https://app.insitechart.com"
        ]
        
        # 개발 환경에서 로컬 출처 추가
        if not self.is_production:
            self.trusted_origins.extend([
                "http://localhost:3000",
                "http://localhost:8000",
                "http://localhost:8501",  # Streamlit 기본 포트
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8501"
            ])
        
        # CSP(Content Security Policy) 설정
        self.csp_policies = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:", "https:", "http:"],
            "connect-src": ["'self'"],
            "frame-src": ["'none'"],
            "object-src": ["'none'"],
            "media-src": ["'self'"],
            "manifest-src": ["'self'"],
            "worker-src": ["'self'"],
            "child-src": ["'none'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "upgrade-insecure-requests": []
        }
        
        # 개발 환경에서 완화된 CSP 정책
        if not self.is_production:
            self.csp_policies["script-src"].extend([
                "http://localhost:*",
                "http://127.0.0.1:*",
                "ws://localhost:*",
                "ws://127.0.0.1:*"
            ])
            self.csp_policies["connect-src"].extend([
                "http://localhost:*",
                "http://127.0.0.1:*",
                "ws://localhost:*",
                "ws://127.0.0.1:*"
            ])
        
        # 사용자 정의 CSP가 있는 경우 적용
        if custom_csp:
            self.custom_csp = custom_csp
        else:
            self.custom_csp = self._build_csp()
        
        # CORS 설정
        self.cors_origins = self.trusted_origins.copy()
        if not self.is_production:
            self.cors_origins.extend(["*"])  # 개발 환경에서는 모든 출처 허용
        
        # 사용자 정의 헤더 설정
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.custom_headers = custom_headers or {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        요청 처리 및 보안 헤더 추가
        
        Args:
            request: FastAPI Request 객체
            call_next: 다음 미들웨어/엔드포인트 함수
            
        Returns:
            보안 헤더가 추가된 응답
        """
        response = await call_next(request)
        
        # 기본 보안 헤더 추가
        self._add_security_headers(response)
        
        # CSP 헤더 추가
        if self.enable_csp:
            self._add_csp_headers(response, request)
        
        # HSTS 헤더 추가
        if self.enable_hsts and self.is_production:
            self._add_hsts_headers(response)
        
        # 추가 보안 헤더
        self._add_additional_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """기본 보안 헤더 추가"""
        # X-Content-Type-Options
        if self.x_content_type_options is None:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        if self.x_frame_options is None:
            response.headers["X-Frame-Options"] = "DENY"
        else:
            response.headers["X-Frame-Options"] = self.x_frame_options
        
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = self._build_permissions_policy()
        
        # 사용자 정의 헤더 추가
        for header_name, header_value in self.custom_headers.items():
            response.headers[header_name] = header_value
    
    def _add_csp_headers(self, response: Response, request: Request):
        """CSP 헤더 추가"""
        # 요청에 따라 동적 CSP 생성
        dynamic_csp = self._build_dynamic_csp(request)
        
        response.headers["Content-Security-Policy"] = dynamic_csp
        response.headers["X-Content-Security-Policy"] = dynamic_csp  # 레거시 브라우저 지원
    
    def _add_hsts_headers(self, response: Response):
        """HSTS 헤더 추가"""
        # 프로덕션 환경에서만 HSTS 적용
        max_age = 31536000  # 1년
        include_subdomains = True
        preload = True
        
        hsts_value = f"max-age={max_age}"
        if include_subdomains:
            hsts_value += "; includeSubDomains"
        if preload:
            hsts_value += "; preload"
        
        response.headers["Strict-Transport-Security"] = hsts_value
    
    def _add_additional_security_headers(self, response: Response):
        """추가 보안 헤더 추가"""
        # 클라이언트 측 캐싱 제어
        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
            # HTML 응답에 대해서만 캐싱 제어
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # 서버 정보 숨기기
        response.headers["Server"] = "InsiteChart"
        
        # X-DNS-Prefetch-Control
        response.headers["X-DNS-Prefetch-Control"] = "off"
        
        # X-Download-Options
        response.headers["X-Download-Options"] = "noopen"
        
        # X-Permitted-Cross-Domain-Policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # X-Rendered-By
        response.headers["X-Rendered-By"] = "InsiteChart Security Middleware"
    
    def _build_csp(self) -> str:
        """기본 CSP 정책 빌드"""
        directives = []
        
        for directive, sources in self.csp_policies.items():
            if sources:
                directives.append(f"{directive} {' '.join(sources)}")
            else:
                directives.append(directive)
        
        return "; ".join(directives)
    
    def _build_dynamic_csp(self, request: Request) -> str:
        """요청에 따른 동적 CSP 정책 빌드"""
        # 기본 CSP 복사
        dynamic_policies = {k: v.copy() for k, v in self.csp_policies.items()}
        
        # 요청 경로에 따른 CSP 조정
        path = request.url.path
        
        # API 엔드포인트에 대한 CSP 완화
        if path.startswith("/api/"):
            dynamic_policies["script-src"] = ["'self'"]
            dynamic_policies["connect-src"] = ["'self'"]
        
        # WebSocket 연결을 위한 CSP 조정
        if path.startswith("/ws/") or path.startswith("/websocket/"):
            dynamic_policies["connect-src"].extend([
                "ws://localhost:*",
                "wss://insitechart.com:*"
            ])
        
        # 외부 리소스가 필요한 페이지에 대한 CSP 조정
        if path.startswith("/admin/"):
            # 관리자 페이지에서는 더 엄격한 CSP
            dynamic_policies["script-src"] = ["'self'"]
            dynamic_policies["style-src"] = ["'self'", "'unsafe-inline'"]
        
        # 동적 CSP 빌드
        directives = []
        for directive, sources in dynamic_policies.items():
            if sources:
                directives.append(f"{directive} {' '.join(sources)}")
            else:
                directives.append(directive)
        
        return "; ".join(directives)
    
    def _build_permissions_policy(self) -> str:
        """Permissions-Policy 헤더 빌드"""
        # 비활성화할 기능 목록
        disabled_features = [
            "geolocation",
            "microphone",
            "camera",
            "payment",
            "usb",
            "magnetometer",
            "gyroscope",
            "accelerometer",
            "ambient-light-sensor",
            "autoplay",
            "encrypted-media",
            "fullscreen",
            "picture-in-picture",
            "speaker-selection"
        ]
        
        # 개발 환경에서는 일부 기능 허용
        if not self.is_production:
            allowed_features = ["autoplay", "fullscreen"]
            disabled_features = [f for f in disabled_features if f not in allowed_features]
        
        return ", ".join([f"{feature}=()" for feature in disabled_features])
    
    def update_csp_policy(self, directive: str, sources: List[str]):
        """CSP 정책 업데이트"""
        self.csp_policies[directive] = sources
        self.custom_csp = self._build_csp()
        logger.info(f"CSP policy updated for {directive}: {sources}")
    
    def add_trusted_origin(self, origin: str):
        """신뢰할 수 있는 출처 추가"""
        if origin not in self.trusted_origins:
            self.trusted_origins.append(origin)
            self.cors_origins.append(origin)
            logger.info(f"Added trusted origin: {origin}")
    
    def remove_trusted_origin(self, origin: str):
        """신뢰할 수 있는 출처 제거"""
        if origin in self.trusted_origins:
            self.trusted_origins.remove(origin)
            self.cors_origins.remove(origin)
            logger.info(f"Removed trusted origin: {origin}")

class CORSSecurityMiddleware(CORSMiddleware):
    """CORS 보안 미들웨어 클래스"""
    
    def __init__(
        self,
        app,
        allow_origins: Optional[List[str]] = None,
        allow_credentials: bool = True,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        max_age: int = 86400
    ):
        # 기본값 설정
        allow_origins = allow_origins or [
            "https://insitechart.com",
            "https://www.insitechart.com",
            "https://app.insitechart.com"
        ]
        
        # 개발 환경에서 로컬 출처 추가
        if os.getenv("ENVIRONMENT", "development") != "production":
            allow_origins.extend([
                "http://localhost:3000",
                "http://localhost:8000",
                "http://localhost:8501",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8501"
            ])
        
        allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        allow_headers = allow_headers or [
            "accept",
            "accept-language",
            "content-language",
            "content-type",
            "authorization",
            "x-api-key",
            "x-request-id"
        ]
        
        super().__init__(
            app,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            max_age=max_age
        )

def create_security_middleware(app, **kwargs) -> SecurityHeadersMiddleware:
    """
    보안 미들웨어 생성 함수
    
    Args:
        app: FastAPI 애플리케이션
        **kwargs: 미들웨어 설정 파라미터
        
    Returns:
        보안 헤더 미들웨어 인스턴스
    """
    return SecurityHeadersMiddleware(app, **kwargs)

def create_cors_middleware(app, **kwargs) -> CORSSecurityMiddleware:
    """
    CORS 미들웨어 생성 함수
    
    Args:
        app: FastAPI 애플리케이션
        **kwargs: 미들웨어 설정 파라미터
        
    Returns:
        CORS 보안 미들웨어 인스턴스
    """
    return CORSSecurityMiddleware(app, **kwargs)

# 기본 보안 헤더 설정
DEFAULT_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-DNS-Prefetch-Control": "off",
    "X-Download-Options": "noopen",
    "X-Permitted-Cross-Domain-Policies": "none"
}

# 개발 환경용 완화된 보안 헤더
DEV_SECURITY_HEADERS = {
    **DEFAULT_SECURITY_HEADERS,
    "X-Frame-Options": "SAMEORIGIN"  # 개발 환경에서는 sameorigin 허용
}

def get_security_headers(is_production: bool = True) -> Dict[str, str]:
    """
    환경에 따른 보안 헤더 반환
    
    Args:
        is_production: 프로덕션 환경 여부
        
    Returns:
        보안 헤더 딕셔너리
    """
    return DEFAULT_SECURITY_HEADERS if is_production else DEV_SECURITY_HEADERS

# RateLimitMiddleware 클래스에 __call__ 메서드 추가 (테스트용)
class RateLimitMiddleware:
    """
    속도 제한 미들웨어 클래스 (테스트용)
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        # Import rate_limiter lazily to avoid circular imports
        from ..services.rate_limit_service import rate_limiter
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        """
        ASGI 호출 메서드
        
        Args:
            scope: ASGI scope
            receive: ASGI receive
            send: ASGI send
        """
        # 비동기 처리를 위한 내부 함수
        async def app():
            try:
                # Request 객체 생성
                request = Request(scope, receive)
                
                # 테스트 환경에서는 속도 제한을 완전히 비활성화
                import os
                testing_env = os.getenv("TESTING", "false").lower() == "true"
                
                if testing_env or self.rate_limiter.testing:
                    await self.app(scope, receive, send)
                    return
                
                # 식별자 자동 생성
                identifier = None
                api_key = request.headers.get("X-API-Key")
                if api_key:
                    identifier = f"api_key:{api_key}"
                else:
                    identifier = f"ip:{request.client.host}"
                
                # 엔드포인트 정보 추출
                endpoint = request.url.path
                
                # 속도 제한 확인
                rate_limit_info = await self.rate_limiter.is_allowed(
                    identifier=identifier,
                    operation="default",
                    user_tier="default",
                    endpoint=endpoint,
                    burst_mode=True
                )
                
                # 속도 제한 초과 시
                if not rate_limit_info.allowed:
                    from fastapi import HTTPException, status
                    from fastapi.responses import JSONResponse
                    
                    headers = {
                        "X-RateLimit-Limit": str(rate_limit_info.policy.requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(rate_limit_info.reset_time.timestamp())),
                        "Retry-After": str(rate_limit_info.retry_after or rate_limit_info.policy.window)
                    }
                    
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "요청 속도 제한을 초과했습니다"},
                        headers=headers
                    )
                    await response(scope, receive, send)
                    return
                
                # 요청 처리
                await self.app(scope, receive, send)
                
            except Exception as e:
                # 오류 발생 시에도 다음 미들웨어로 전달
                await self.app(scope, receive, send)
        
        # 비동기 함수 실행
        import asyncio
        return asyncio.create_task(app())
    
    def update_config(self, requests_per_minute: int):
        """
        속도 제한 설정 업데이트
        
        Args:
            requests_per_minute: 분당 요청 수
        """
        self.requests_per_minute = requests_per_minute
        # 기본 정책 업데이트
        self.rate_limiter.default_policies["default"].requests = requests_per_minute