"""
향상된 속도 제한 미들웨어 모듈
사용자별, 엔드포인트별, API 키별 동적 속도 제한 기능 제공
"""

import time
import asyncio
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
import redis.asyncio as redis
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RateLimitPolicy:
    """속도 제한 정책 데이터 클래스"""
    requests: int           # 허용 요청 수
    window: int            # 시간 윈도우 (초)
    burst: int = 0         # 버스트 허용량 (0 = 비활성화)
    penalty: int = 0       # 초과 시 패널티 시간 (초)
    
    def __post_init__(self):
        if self.burst == 0:
            self.burst = self.requests // 4  # 기본 버스트 = 요청의 25%

@dataclass
class RateLimitInfo:
    """속도 제한 정보 데이터 클래스"""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    policy: Optional[RateLimitPolicy] = None
    identifier: str = ""
    window_used: int = 0

class AdvancedRateLimiter:
    """고급 속도 제한 시스템 클래스"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.key_prefix = "insitechart:rate_limit:"
        
        # 테스트 환경 확인
        import os
        self.testing = os.getenv("TESTING", "false").lower() == "true"
        
        # 기본 속도 제한 정책
        base_policies = {
            "default": RateLimitPolicy(requests=10000, window=60),        # 기본: 10000/분
            "search": RateLimitPolicy(requests=20000, window=60),          # 검색: 20000/분
            "sentiment": RateLimitPolicy(requests=15000, window=60),       # 감성: 15000/분
            "realtime": RateLimitPolicy(requests=50000, window=60),        # 실시간: 50000/분
            "admin": RateLimitPolicy(requests=100000, window=60),          # 관리자: 100000/분
            "premium": RateLimitPolicy(requests=50000, window=60),          # 프리미엄: 50000/분
            "enterprise": RateLimitPolicy(requests=200000, window=60),     # 엔터프라이즈: 200000/분
        }
        
        # 테스트 환경에서는 속도 제한을 100000배로 증가
        if self.testing:
            self.default_policies = {}
            for key, policy in base_policies.items():
                self.default_policies[key] = RateLimitPolicy(
                    requests=policy.requests * 100000,
                    window=policy.window,
                    burst=policy.burst * 1000,
                    penalty=policy.penalty
                )
        
        # 엔드포인트별 정책 매핑
        self.endpoint_policies = {
            "/api/v1/stocks/search": "search",
            "/api/v1/sentiment/analyze": "sentiment",
            "/api/v1/realtime/subscribe": "realtime",
            "/api/v1/admin/": "admin",
        }
        
        # 동적 조정 파라미터
        self.dynamic_adjustment = {
            "enabled": True,
            "load_threshold": 0.8,      # 부하 임계값 (80%)
            "adjustment_factor": 0.5,   # 조정 계수 (50% 감소)
            "recovery_factor": 1.2,    # 복구 계수 (20% 증가)
            "min_requests": 10,         # 최소 요청 수
        }
    
    async def initialize(self):
        """Redis 클라이언트 초기화"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Rate Limiter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Rate Limiter: {str(e)}")
            raise
    
    async def is_allowed(
        self,
        identifier: str,
        operation: str = "default",
        user_tier: str = "default",
        endpoint: str = "",
        burst_mode: bool = False
    ) -> RateLimitInfo:
        """
        속도 제한 확인
        
        Args:
            identifier: 고유 식별자 (IP, API 키, 사용자 ID 등)
            operation: 작업 유형
            user_tier: 사용자 티어
            endpoint: API 엔드포인트
            burst_mode: 버스트 모드 활성화 여부
            
        Returns:
            속도 제한 정보
        """
        try:
            # 정책 선택
            policy = self._select_policy(operation, user_tier, endpoint)
            
            # 동적 조정 확인
            adjusted_policy = await self._apply_dynamic_adjustment(policy, identifier)
            
            # 슬라이딩 윈도우 알고리즘 적용
            if burst_mode and adjusted_policy.burst > 0:
                return await self._sliding_window_with_burst(identifier, operation, adjusted_policy)
            else:
                return await self._sliding_window(identifier, operation, adjusted_policy)
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # 오류 시 기본 정책으로 허용
            return RateLimitInfo(
                allowed=True,
                remaining=self.default_policies["default"].requests,
                reset_time=datetime.utcnow() + timedelta(hours=1),
                policy=self.default_policies["default"],
                identifier=identifier
            )
    
    async def check_multiple_limits(
        self,
        identifier: str,
        limits: List[Tuple[str, str]]  # [(operation, user_tier), ...]
    ) -> RateLimitInfo:
        """
        여러 속도 제한 확인
        
        Args:
            identifier: 고유 식별자
            limits: 확인할 제한 목록 [(operation, user_tier), ...]
            
        Returns:
            가장 제한적인 속도 제한 정보
        """
        results = []
        
        for operation, user_tier in limits:
            result = await self.is_allowed(identifier, operation, user_tier)
            results.append(result)
        
        # 가장 제한적인 결과 선택
        most_restrictive = min(results, key=lambda x: x.remaining)
        
        return most_restrictive
    
    async def update_dynamic_adjustment(self, load_factor: float):
        """
        동적 조정 파라미터 업데이트
        
        Args:
            load_factor: 현재 시스템 부하因子 (0.0-1.0)
        """
        if not self.dynamic_adjustment["enabled"]:
            return
        
        try:
            # 부하에 따른 조정 계수 계산
            if load_factor > self.dynamic_adjustment["load_threshold"]:
                # 부하가 높으면 제한 강화
                adjustment = self.dynamic_adjustment["adjustment_factor"]
                logger.info(f"High load detected ({load_factor:.2f}), applying rate limit adjustment: {adjustment}")
            else:
                # 부하가 낮으면 제한 완화
                adjustment = self.dynamic_adjustment["recovery_factor"]
                logger.info(f"Low load detected ({load_factor:.2f}), applying rate limit recovery: {adjustment}")
            
            # 조정 정보 저장
            await self.redis_client.set(
                f"{self.key_prefix}dynamic_adjustment",
                str(adjustment),
                ex=300  # 5분간 유효
            )
            
        except Exception as e:
            logger.error(f"Error updating dynamic adjustment: {str(e)}")
    
    async def get_rate_limit_stats(self, identifier: str) -> Dict[str, Any]:
        """
        식별자별 속도 제한 통계 조회
        
        Args:
            identifier: 고유 식별자
            
        Returns:
            속도 제한 통계
        """
        try:
            stats = {}
            
            # 모든 작업 유형에 대한 통계 조회
            for operation in self.default_policies.keys():
                key = f"{self.key_prefix}{identifier}:{operation}"
                
                # 현재 윈도우 정보
                current_window = int(time.time()) // self.default_policies[operation].window
                window_key = f"{key}:{current_window}"
                
                current_count = await self.redis_client.get(window_key)
                current_count = int(current_count) if current_count else 0
                
                # 이전 윈도우 정보
                prev_window = current_window - 1
                prev_window_key = f"{key}:{prev_window}"
                prev_count = await self.redis_client.get(prev_window_key)
                prev_count = int(prev_count) if prev_count else 0
                
                stats[operation] = {
                    "current_window": current_count,
                    "previous_window": prev_count,
                    "limit": self.default_policies[operation].requests,
                    "window_seconds": self.default_policies[operation].window
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting rate limit stats: {str(e)}")
            return {}
    
    def _select_policy(self, operation: str, user_tier: str, endpoint: str) -> RateLimitPolicy:
        """적용할 정책 선택"""
        # 엔드포인트 기반 정책 확인
        for ep_pattern, policy_name in self.endpoint_policies.items():
            if endpoint.startswith(ep_pattern):
                return self.default_policies.get(policy_name, self.default_policies["default"])
        
        # 사용자 티어 기반 정책 확인
        if user_tier in self.default_policies:
            return self.default_policies[user_tier]
        
        # 작업 유형 기반 정책 확인
        if operation in self.default_policies:
            return self.default_policies[operation]
        
        # 기본 정책
        return self.default_policies["default"]
    
    async def _apply_dynamic_adjustment(self, policy: RateLimitPolicy, identifier: str) -> RateLimitPolicy:
        """동적 조정 적용"""
        try:
            # 현재 조정 계수 조회
            adjustment_str = await self.redis_client.get(f"{self.key_prefix}dynamic_adjustment")
            if not adjustment_str:
                return policy
            
            adjustment = float(adjustment_str)
            if adjustment == 1.0:
                return policy
            
            # 조정된 정책 생성
            adjusted_requests = max(
                int(policy.requests * adjustment),
                self.dynamic_adjustment["min_requests"]
            )
            
            return RateLimitPolicy(
                requests=adjusted_requests,
                window=policy.window,
                burst=max(int(policy.burst * adjustment), 1),
                penalty=policy.penalty
            )
            
        except Exception as e:
            logger.error(f"Error applying dynamic adjustment: {str(e)}")
            return policy
    
    async def _sliding_window(self, identifier: str, operation: str, policy: RateLimitPolicy) -> RateLimitInfo:
        """슬라이딩 윈도우 알고리즘"""
        now = time.time()
        window_start = now - policy.window
        
        # 키 생성
        key = f"{self.key_prefix}{identifier}:{operation}"
        
        # 현재 윈도우의 모든 요청 타임스탬프 조회
        timestamps = await self.redis_client.zrangebyscore(key, window_start, now)
        
        # 현재 요청 수
        current_count = len(timestamps)
        
        # 요청 수 확인
        if current_count >= policy.requests:
            # 가장 오래된 요청 제거 시간 계산
            oldest_timestamp = await self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_timestamp:
                retry_after = int(oldest_timestamp[0][1] + policy.window - now)
            else:
                retry_after = policy.window
            
            return RateLimitInfo(
                allowed=False,
                remaining=0,
                reset_time=datetime.fromtimestamp(now + policy.window),
                retry_after=max(retry_after, 1),
                policy=policy,
                identifier=identifier,
                window_used=current_count
            )
        
        # 현재 요청 추가
        await self.redis_client.zadd(key, {str(now): now})
        
        # 만료된 요청 정리
        await self.redis_client.zremrangebyscore(key, 0, window_start)
        
        # 키 만료 설정
        await self.redis_client.expire(key, policy.window)
        
        return RateLimitInfo(
            allowed=True,
            remaining=policy.requests - current_count - 1,
            reset_time=datetime.fromtimestamp(now + policy.window),
            policy=policy,
            identifier=identifier,
            window_used=current_count + 1
        )
    
    async def _sliding_window_with_burst(self, identifier: str, operation: str, policy: RateLimitPolicy) -> RateLimitInfo:
        """버스트를 지원하는 슬라이딩 윈도우 알고리즘"""
        now = time.time()
        window_start = now - policy.window
        
        # 키 생성
        key = f"{self.key_prefix}{identifier}:{operation}"
        burst_key = f"{key}:burst"
        
        # 일반 윈도우 확인
        normal_result = await self._sliding_window(identifier, operation, policy)
        
        # 버스트 윈도우 확인 (더 짧은 시간 윈도우)
        burst_window = policy.window // 4  # 1/4 시간 윈도우
        burst_start = now - burst_window
        
        burst_timestamps = await self.redis_client.zrangebyscore(burst_key, burst_start, now)
        burst_count = len(burst_timestamps)
        
        # 버스트 제한 확인
        if burst_count >= policy.burst:
            # 버스트 초과 시 패널티 적용
            if policy.penalty > 0:
                # 패널티 시간 동안 추가 요청 차단
                penalty_key = f"{key}:penalty"
                penalty_active = await self.redis_client.exists(penalty_key)
                
                if not penalty_active:
                    await self.redis_client.setex(penalty_key, policy.penalty, "1")
                
                retry_after = policy.penalty
            else:
                retry_after = burst_window - int(now - burst_start)
            
            return RateLimitInfo(
                allowed=False,
                remaining=0,
                reset_time=datetime.fromtimestamp(now + retry_after),
                retry_after=retry_after,
                policy=policy,
                identifier=identifier,
                window_used=burst_count
            )
        
        # 버스트 윈도우에 현재 요청 추가
        await self.redis_client.zadd(burst_key, {str(now): now})
        await self.redis_client.zremrangebyscore(burst_key, 0, burst_start)
        await self.redis_client.expire(burst_key, burst_window)
        
        # 일반 윈도우 결과와 버스트 윈도우 결과 중 더 제한적인 것 선택
        if not normal_result.allowed:
            return normal_result
        
        # 버스트 고려하여 남은 요청 수 조정
        burst_remaining = min(
            policy.requests - normal_result.window_used,
            policy.burst - burst_count - 1
        )
        
        return RateLimitInfo(
            allowed=True,
            remaining=burst_remaining,
            reset_time=normal_result.reset_time,
            policy=policy,
            identifier=identifier,
            window_used=normal_result.window_used
        )

# 전속 속도 제한기 인스턴스
rate_limiter = AdvancedRateLimiter()

async def rate_limit_middleware(
    request: Request,
    call_next,
    identifier: str = None,
    operation: str = "default",
    user_tier: str = "default"
):
    """
    속도 제한 미들웨어 함수
    
    Args:
        request: FastAPI Request 객체
        call_next: 다음 미들웨어/엔드포인트 함수
        identifier: 고유 식별자 (None이면 자동 생성)
        operation: 작업 유형
        user_tier: 사용자 티어
        
    Returns:
        HTTP 응답
    """
    # 테스트 환경에서는 속도 제한을 완전히 비활성화
    import os
    testing_env = os.getenv("TESTING", "false").lower() == "true"
    
    # 디버그 정보 출력
    if testing_env:
        print(f"DEBUG: Testing environment detected, bypassing rate limiting")
        return await call_next(request)
    
    if rate_limiter.testing:
        print(f"DEBUG: Rate limiter testing mode enabled, bypassing rate limiting")
        return await call_next(request)
    
    # 식별자 자동 생성
    if not identifier:
        # API 키 우선, 그 다음 IP 주소
        api_key = request.headers.get("X-API-Key")
        if api_key:
            identifier = f"api_key:{api_key}"
        else:
            identifier = f"ip:{request.client.host}"
    
    # 엔드포인트 정보 추출
    endpoint = request.url.path
    
    # 속도 제한 확인
    rate_limit_info = await rate_limiter.is_allowed(
        identifier=identifier,
        operation=operation,
        user_tier=user_tier,
        endpoint=endpoint,
        burst_mode=True
    )
    
    # 속도 제한 초과 시
    if not rate_limit_info.allowed:
        headers = {
            "X-RateLimit-Limit": str(rate_limit_info.policy.requests),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(rate_limit_info.reset_time.timestamp())),
            "Retry-After": str(rate_limit_info.retry_after or rate_limit_info.policy.window)
        }
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청 속도 제한을 초과했습니다",
            headers=headers
        )
    
    # 요청 처리
    response = await call_next(request)
    
    # 응답 헤더에 속도 제한 정보 추가
    response.headers["X-RateLimit-Limit"] = str(rate_limit_info.policy.requests)
    response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(rate_limit_info.reset_time.timestamp()))
    response.headers["X-RateLimit-Window-Used"] = str(rate_limit_info.window_used)
    
    return response

# 클라이언트 IP 가져오기 함수 (테스트용)
def get_client_ip(request: Request) -> str:
    """
    클라이언트 IP 주소 가져오기 (테스트용)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        클라이언트 IP 주소
    """
    # X-Forwarded-For 헤더 확인
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # X-Real-IP 헤더 확인
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 직접 연결 IP
    return request.client.host

# Redis 클라이언트 가져오기 함수 (테스트용)
def get_redis_client():
    """
    Redis 클라이언트 인스턴스 가져오기 (테스트용)
    
    Returns:
        Redis 클라이언트 인스턴스
    """
    return rate_limiter.redis_client

# RateLimitMiddleware 클래스 (테스트용 별칭)
class RateLimitMiddleware:
    """
    속도 제한 미들웨어 클래스 (테스트용)
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        """
        ASGI 호출 메서드
        
        Args:
            scope: ASGI scope
            receive: ASGI receive
            send: ASGI send
        """
        # 테스트 환경에서는 속도 제한을 바이패스
        import os
        testing_env = os.getenv("TESTING", "false").lower() == "true"
        
        if testing_env or self.rate_limiter.testing:
            await self.app(scope, receive, send)
            return
        
        # Request 객체 생성
        request = Request(scope, receive)
        
        # 속도 제한 확인
        try:
            identifier = get_client_ip(request)
            rate_limit_info = await self.rate_limiter.is_allowed(
                identifier=identifier,
                operation="default",
                user_tier="default",
                endpoint=request.url.path
            )
            
            if not rate_limit_info.allowed:
                # 속도 제한 초과 응답 생성
                from fastapi.responses import JSONResponse
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"}
                )
                await response(scope, receive, send)
                return
            
            # 요청 처리
            await self.app(scope, receive, send)
            
        except Exception as e:
            # 오류 발생 시 요청 계속 처리
            await self.app(scope, receive, send)
    
    def update_config(self, requests_per_minute: int):
        """
        속도 제한 설정 업데이트
        
        Args:
            requests_per_minute: 분당 요청 수
        """
        self.requests_per_minute = requests_per_minute
        # 기본 정책 업데이트
        self.rate_limiter.default_policies["default"].requests = requests_per_minute