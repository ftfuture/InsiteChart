# API 레이트리밋 전략 상세화

## 1. 개요

### 1.1 레이트리밋의 중요성

API 레이트리밋은 시스템 안정성, 공정한 자원 분배, 비용 관리, 보안 강화를 위한 필수적인 메커니즘입니다. InsiteChart 플랫폼은 다양한 외부 API(Yahoo Finance, Reddit, Twitter)와 통합되므로, 각 API의 제약 조건을 준수하면서도 사용자에게 일관된 서비스를 제공해야 합니다.

### 1.2 레이트리밋 목표

1. **API 제약 준수**: 외부 API의 호출 제한 준수
2. **시스템 안정성**: 과부하로부터 시스템 보호
3. **공정한 사용**: 모든 사용자에게 공평한 자원 분배
4. **비용 최적화**: API 호출 비용 관리
5. **보안 강화**: 악의적인 사용 방지

## 2. 다계층 레이트리밋 아키텍처

### 2.1 레이트리밋 계층 구조

```python
# rate_limiting/rate_limiter.py
import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import redis.asyncio as redis
import json

class RateLimitType(Enum):
    """레이트리밋 타입"""
    REQUEST_PER_SECOND = "rps"      # 초당 요청 수
    REQUEST_PER_MINUTE = "rpm"      # 분당 요청 수
    REQUEST_PER_HOUR = "rph"        # 시간당 요청 수
    REQUEST_PER_DAY = "rpd"         # 일당 요청 수
    CONCURRENT_REQUESTS = "cr"      # 동시 요청 수

@dataclass
class RateLimitRule:
    """레이트리밋 규칙"""
    name: str
    limit_type: RateLimitType
    limit: int
    window: int = 1  # 시간 창 (초)
    burst: int = 0   # 버스트 허용량 (0이면 비활성화)
    priority: int = 0  # 우선순위 (높을수록 우선)
    
@dataclass
class RateLimitResult:
    """레이트리밋 결과"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit: Optional[int] = None
    window: Optional[int] = None

class RateLimiter:
    """고급 레이트리밋 구현"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
        
        # 기본 규칙 설정
        self.default_rules = {
            'global': [
                RateLimitRule("global_rps", RateLimitType.REQUEST_PER_SECOND, 1000),
                RateLimitRule("global_rpm", RateLimitType.REQUEST_PER_MINUTE, 60000),
            ],
            'user': [
                RateLimitRule("user_rps", RateLimitType.REQUEST_PER_SECOND, 10),
                RateLimitRule("user_rpm", RateLimitType.REQUEST_PER_MINUTE, 1000),
                RateLimitRule("user_rph", RateLimitType.REQUEST_PER_HOUR, 10000),
            ],
            'api_key': [
                RateLimitRule("api_rps", RateLimitType.REQUEST_PER_SECOND, 50),
                RateLimitRule("api_rpm", RateLimitType.REQUEST_PER_MINUTE, 5000),
            ],
            'endpoint': {
                'stock_search': [
                    RateLimitRule("stock_search_rpm", RateLimitType.REQUEST_PER_MINUTE, 100),
                ],
                'sentiment_analysis': [
                    RateLimitRule("sentiment_rpm", RateLimitType.REQUEST_PER_MINUTE, 50),
                ],
                'real_time_data': [
                    RateLimitRule("realtime_rps", RateLimitType.REQUEST_PER_SECOND, 5),
                ],
                'export_data': [
                    RateLimitRule("export_rph", RateLimitType.REQUEST_PER_HOUR, 10),
                ]
            }
        }
        
        # 외부 API별 규칙
        self.external_api_rules = {
            'yahoo_finance': [
                RateLimitRule("yahoo_rps", RateLimitType.REQUEST_PER_SECOND, 2),
                RateLimitRule("yahoo_rpm", RateLimitType.REQUEST_PER_MINUTE, 100),
            ],
            'reddit': [
                RateLimitRule("reddit_rps", RateLimitType.REQUEST_PER_SECOND, 1),
                RateLimitRule("reddit_rpm", RateLimitType.REQUEST_PER_MINUTE, 60),
            ],
            'twitter': [
                RateLimitRule("twitter_rps", RateLimitType.REQUEST_PER_SECOND, 1),
                RateLimitRule("twitter_rpm", RateLimitType.REQUEST_PER_MINUTE, 300),
            ]
        }
    
    async def check_rate_limit(self, 
                             identifier: str, 
                             rule_type: str, 
                             endpoint: Optional[str] = None,
                             api_provider: Optional[str] = None) -> RateLimitResult:
        """레이트리밋 확인"""
        
        # 적용할 규칙 목록 가져오기
        rules = self._get_applicable_rules(rule_type, endpoint, api_provider)
        
        if not rules:
            return RateLimitResult(allowed=True, remaining=-1, reset_time=0)
        
        # 모든 규칙 확인 (가장 제한적인 규칙 적용)
        most_restrictive = None
        
        for rule in rules:
            result = await self._check_single_rule(identifier, rule)
            
            if not result.allowed:
                return result
            
            if most_restrictive is None or result.remaining < most_restrictive.remaining:
                most_restrictive = result
        
        return most_restrictive or RateLimitResult(allowed=True, remaining=-1, reset_time=0)
    
    def _get_applicable_rules(self, 
                             rule_type: str, 
                             endpoint: Optional[str] = None,
                             api_provider: Optional[str] = None) -> List[RateLimitRule]:
        """적용 가능한 규칙 목록 가져오기"""
        rules = []
        
        # 기본 규칙 추가
        if rule_type in self.default_rules:
            rules.extend(self.default_rules[rule_type])
        
        # 엔드포인트별 규칙 추가
        if endpoint and endpoint in self.default_rules.get('endpoint', {}):
            rules.extend(self.default_rules['endpoint'][endpoint])
        
        # 외부 API 규칙 추가
        if api_provider and api_provider in self.external_api_rules:
            rules.extend(self.external_api_rules[api_provider])
        
        # 우선순위별 정렬
        rules.sort(key=lambda x: x.priority, reverse=True)
        
        return rules
    
    async def _check_single_rule(self, identifier: str, rule: RateLimitRule) -> RateLimitResult:
        """단일 규칙 확인"""
        
        if rule.limit_type == RateLimitType.REQUEST_PER_SECOND:
            return await self._check_sliding_window(identifier, rule, 1)
        elif rule.limit_type == RateLimitType.REQUEST_PER_MINUTE:
            return await self._check_sliding_window(identifier, rule, 60)
        elif rule.limit_type == RateLimitType.REQUEST_PER_HOUR:
            return await self._check_sliding_window(identifier, rule, 3600)
        elif rule.limit_type == RateLimitType.REQUEST_PER_DAY:
            return await self._check_sliding_window(identifier, rule, 86400)
        elif rule.limit_type == RateLimitType.CONCURRENT_REQUESTS:
            return await self._check_concurrent_requests(identifier, rule)
        
        return RateLimitResult(allowed=True, remaining=-1, reset_time=0)
    
    async def _check_sliding_window(self, identifier: str, rule: RateLimitRule, window: int) -> RateLimitResult:
        """슬라이딩 윈도우 방식으로 레이트리밋 확인"""
        
        now = int(time.time())
        key = f"rate_limit:{rule.name}:{identifier}"
        
        # 현재 윈도우의 요청 수 확인
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window)
        
        results = await pipe.execute()
        
        current_count = results[1]
        
        if current_count >= rule.limit:
            # 제한 초과
            oldest_request = await self.redis.zrange(key, 0, 0, withscores=True)
            retry_after = int(oldest_request[0][1]) + window - now if oldest_request else window
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + retry_after,
                retry_after=retry_after,
                limit=rule.limit,
                window=window
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=rule.limit - current_count - 1,
            reset_time=now + window,
            limit=rule.limit,
            window=window
        )
    
    async def _check_concurrent_requests(self, identifier: str, rule: RateLimitRule) -> RateLimitResult:
        """동시 요청 수 확인"""
        
        now = int(time.time())
        key = f"concurrent:{rule.name}:{identifier}"
        
        # 현재 동시 요청 수 확인
        current = await self.redis.incr(key)
        
        if current == 1:
            # 첫 요청이면 만료 시간 설정
            await self.redis.expire(key, 300)  # 5분 타임아웃
        
        if current > rule.limit:
            # 제한 초과
            await self.redis.decr(key)
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + 300,
                retry_after=1,
                limit=rule.limit,
                window=300
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=rule.limit - current,
            reset_time=now + 300,
            limit=rule.limit,
            window=300
        )
    
    async def release_concurrent_request(self, identifier: str, rule_name: str):
        """동시 요청 해제"""
        key = f"concurrent:{rule_name}:{identifier}"
        await self.redis.decr(key)
    
    async def get_rate_limit_status(self, 
                                  identifier: str, 
                                  rule_type: str, 
                                  endpoint: Optional[str] = None,
                                  api_provider: Optional[str] = None) -> Dict[str, Any]:
        """레이트리밋 상태 조회"""
        
        rules = self._get_applicable_rules(rule_type, endpoint, api_provider)
        status = {}
        
        for rule in rules:
            if rule.limit_type in [
                RateLimitType.REQUEST_PER_SECOND,
                RateLimitType.REQUEST_PER_MINUTE,
                RateLimitType.REQUEST_PER_HOUR,
                RateLimitType.REQUEST_PER_DAY
            ]:
                window = self._get_window_seconds(rule.limit_type)
                result = await self._check_sliding_window(identifier, rule, window)
                status[rule.name] = {
                    'limit': rule.limit,
                    'remaining': result.remaining,
                    'reset_time': result.reset_time,
                    'window': window
                }
        
        return status
    
    def _get_window_seconds(self, limit_type: RateLimitType) -> int:
        """레이트리밋 타입별 시간 창(초) 반환"""
        mapping = {
            RateLimitType.REQUEST_PER_SECOND: 1,
            RateLimitType.REQUEST_PER_MINUTE: 60,
            RateLimitType.REQUEST_PER_HOUR: 3600,
            RateLimitType.REQUEST_PER_DAY: 86400,
        }
        return mapping.get(limit_type, 1)
    
    async def reset_rate_limit(self, identifier: str, rule_name: Optional[str] = None):
        """레이트리밋 초기화"""
        
        if rule_name:
            # 특정 규칙만 초기화
            pattern = f"rate_limit:{rule_name}:{identifier}"
        else:
            # 모든 규칙 초기화
            pattern = f"rate_limit:*:{identifier}"
        
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
        
        # 동시 요청 카운터도 초기화
        concurrent_pattern = f"concurrent:*:{identifier}"
        concurrent_keys = await self.redis.keys(concurrent_pattern)
        if concurrent_keys:
            await self.redis.delete(*concurrent_keys)
```

### 2.2 API 게이트웨이 레이트리밋 미들웨어

```python
# rate_limiting/middleware.py
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable, Optional
import time
import logging
from .rate_limiter import RateLimiter, RateLimitResult

class RateLimitMiddleware:
    """API 게이트웨이 레이트리밋 미들웨어"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
        
        # 경로별 레이트리밋 규칙 매핑
        self.endpoint_mapping = {
            '/api/v1/stocks/search': 'stock_search',
            '/api/v1/stocks/{symbol}': 'stock_search',
            '/api/v1/sentiment/analyze': 'sentiment_analysis',
            '/api/v1/sentiment/trending': 'sentiment_analysis',
            '/api/v1/data/realtime': 'real_time_data',
            '/api/v1/data/export': 'export_data',
        }
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # 식별자 추출
        identifier = self._extract_identifier(request)
        
        # 엔드포인트 타입 결정
        endpoint_type = self._determine_endpoint_type(request.url.path)
        
        # API 제공자 결정 (외부 API 호출 시)
        api_provider = self._determine_api_provider(request)
        
        # 레이트리밋 확인
        rate_limit_result = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            rule_type='user',  # 기본적으로 사용자별 제한
            endpoint=endpoint_type,
            api_provider=api_provider
        )
        
        # 레이트리밋 응답 헤더 설정
        response_headers = self._build_rate_limit_headers(rate_limit_result)
        
        if not rate_limit_result.allowed:
            self.logger.warning(
                f"Rate limit exceeded for {identifier} on {request.url.path}",
                extra={
                    'identifier': identifier,
                    'endpoint': request.url.path,
                    'limit': rate_limit_result.limit,
                    'window': rate_limit_result.window,
                    'retry_after': rate_limit_result.retry_after
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again in {rate_limit_result.retry_after} seconds.',
                    'retry_after': rate_limit_result.retry_after,
                    'limit': rate_limit_result.limit,
                    'window': rate_limit_result.window
                },
                headers=response_headers
            )
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 헤더에 레이트리밋 정보 추가
        for header, value in response_headers.items():
            response.headers[header] = value
        
        return response
    
    def _extract_identifier(self, request: Request) -> str:
        """요청에서 식별자 추출"""
        
        # 1. API 키 우선
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return f"api_key:{api_key}"
        
        # 2. 사용자 ID (인증된 경우)
        if hasattr(request.state, 'user') and request.state.user:
            user_id = request.state.user.get('user_id')
            if user_id:
                return f"user:{user_id}"
        
        # 3. IP 주소
        client_ip = request.client.host
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        
        return f"ip:{client_ip}"
    
    def _determine_endpoint_type(self, path: str) -> Optional[str]:
        """경로에 따른 엔드포인트 타입 결정"""
        
        for pattern, endpoint_type in self.endpoint_mapping.items():
            # 단순 패턴 매칭 (실제로는 더 정교한 패턴 매칭 필요)
            if pattern.replace('{symbol}', '') in path or path.startswith(pattern.split('{')[0]):
                return endpoint_type
        
        return None
    
    def _determine_api_provider(self, request: Request) -> Optional[str]:
        """요청에 따른 외부 API 제공자 결정"""
        
        # 요청 경로나 파라미터를 기반으로 API 제공자 결정
        path = request.url.path
        
        if '/stocks/' in path:
            return 'yahoo_finance'
        elif '/sentiment/' in path:
            # 실제로는 소셜 미디어 소스에 따라 결정
            return 'reddit'  # 기본값
        elif '/reddit/' in path:
            return 'reddit'
        elif '/twitter/' in path:
            return 'twitter'
        
        return None
    
    def _build_rate_limit_headers(self, result: RateLimitResult) -> Dict[str, str]:
        """레이트리밋 응답 헤더 생성"""
        
        headers = {}
        
        if result.limit is not None:
            headers['X-RateLimit-Limit'] = str(result.limit)
        
        if result.remaining is not None:
            headers['X-RateLimit-Remaining'] = str(result.remaining)
        
        if result.reset_time is not None:
            headers['X-RateLimit-Reset'] = str(result.reset_time)
        
        if result.retry_after is not None:
            headers['Retry-After'] = str(result.retry_after)
        
        return headers

class APIRateLimiter:
    """외부 API 호출별 레이트리밋 관리"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
        
        # API별 호출 큐
        self.api_queues = {}
        
        # API별 동시 요청 제한
        self.concurrent_limits = {
            'yahoo_finance': 5,
            'reddit': 2,
            'twitter': 3
        }
    
    async def acquire_api_call(self, api_provider: str, identifier: str = "system") -> bool:
        """API 호출 권한 획득"""
        
        # 동시 요청 제한 확인
        concurrent_rule = f"concurrent_{api_provider}"
        concurrent_limit = self.concurrent_limits.get(api_provider, 1)
        
        result = await self.rate_limiter.check_rate_limit(
            identifier=f"api_{api_provider}",
            rule_type='api_key',
            api_provider=api_provider
        )
        
        if not result.allowed:
            self.logger.warning(f"API rate limit exceeded for {api_provider}")
            return False
        
        return True
    
    async def release_api_call(self, api_provider: str):
        """API 호출 권한 해제"""
        await self.rate_limiter.release_concurrent_request(
            identifier=f"api_{api_provider}",
            rule_name=f"concurrent_{api_provider}"
        )
    
    async def wait_for_api_slot(self, api_provider: str, max_wait: int = 60) -> bool:
        """API 슬롯이 사용 가능할 때까지 대기"""
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if await self.acquire_api_call(api_provider):
                return True
            
            # 지수 백오프로 대기
            wait_time = min(0.1 * (2 ** (time.time() - start_time)), 1.0)
            await asyncio.sleep(wait_time)
        
        return False
```

## 3. 동적 레이트리밋 정책

### 3.1 적응형 레이트리밋

```python
# rate_limiting/adaptive_rate_limiter.py
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import json
from .rate_limiter import RateLimiter, RateLimitRule, RateLimitType

@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    cpu_usage: float
    memory_usage: float
    request_rate: float
    error_rate: float
    response_time_p95: float
    timestamp: datetime

@dataclass
class AdaptiveRule:
    """적응형 레이트리밋 규칙"""
    base_rule: RateLimitRule
    min_limit: int
    max_limit: int
    adjustment_factor: float
    metric_thresholds: Dict[str, float]
    cooldown_period: int = 300  # 5분

class AdaptiveRateLimiter:
    """적응형 레이트리밋 관리자"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
        
        # 적응형 규칙 설정
        self.adaptive_rules = {
            'global_load': AdaptiveRule(
                base_rule=RateLimitRule("global_adaptive", RateLimitType.REQUEST_PER_SECOND, 1000),
                min_limit=100,
                max_limit=2000,
                adjustment_factor=0.2,
                metric_thresholds={
                    'cpu_usage': 0.8,
                    'memory_usage': 0.85,
                    'error_rate': 0.05,
                    'response_time_p95': 1.0
                }
            ),
            'user_load': AdaptiveRule(
                base_rule=RateLimitRule("user_adaptive", RateLimitType.REQUEST_PER_SECOND, 10),
                min_limit=1,
                max_limit=50,
                adjustment_factor=0.3,
                metric_thresholds={
                    'cpu_usage': 0.7,
                    'memory_usage': 0.8,
                    'error_rate': 0.03,
                    'response_time_p95': 0.5
                }
            )
        }
        
        # 현재 시스템 메트릭
        self.current_metrics: Optional[SystemMetrics] = None
        
        # 규칙 조정 이력
        self.adjustment_history: List[Dict[str, Any]] = []
        
        # 조정 쿨다운 추적
        self.last_adjustment: Dict[str, datetime] = {}
    
    async def update_system_metrics(self, metrics: SystemMetrics):
        """시스템 메트릭 업데이트"""
        self.current_metrics = metrics
        
        # 적응형 규칙 조정 확인
        await self._evaluate_and_adjust_rules()
    
    async def _evaluate_and_adjust_rules(self):
        """시스템 메트릭에 따른 규칙 조정 평가"""
        
        if not self.current_metrics:
            return
        
        for rule_name, adaptive_rule in self.adaptive_rules.items():
            # 쿨다운 기간 확인
            if self._is_in_cooldown(rule_name):
                continue
            
            # 조정 필요 여부 평가
            adjustment = self._calculate_adjustment(adaptive_rule)
            
            if adjustment['adjust']:
                await self._apply_adjustment(rule_name, adaptive_rule, adjustment)
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """쿨다운 기간 확인"""
        if rule_name not in self.last_adjustment:
            return False
        
        last_time = self.last_adjustment[rule_name]
        cooldown_period = self.adaptive_rules[rule_name].cooldown_period
        
        return datetime.now() - last_time < timedelta(seconds=cooldown_period)
    
    def _calculate_adjustment(self, adaptive_rule: AdaptiveRule) -> Dict[str, Any]:
        """조정량 계산"""
        
        metrics = self.current_metrics
        thresholds = adaptive_rule.metric_thresholds
        
        # 시스템 부하 계산 (0-1 스케일)
        load_factors = []
        
        if metrics.cpu_usage > thresholds['cpu_usage']:
            load_factors.append(metrics.cpu_usage)
        
        if metrics.memory_usage > thresholds['memory_usage']:
            load_factors.append(metrics.memory_usage)
        
        if metrics.error_rate > thresholds['error_rate']:
            load_factors.append(metrics.error_rate * 10)  # 에러률 가중치
        
        if metrics.response_time_p95 > thresholds['response_time_p95']:
            load_factors.append(metrics.response_time_p95 / 2.0)
        
        # 평균 부하 계산
        avg_load = sum(load_factors) / len(load_factors) if load_factors else 0
        
        # 조정 방향과 크기 결정
        if avg_load > 0.7:  # 높은 부하
            adjustment_direction = -1  # 제한 강화
            adjustment_magnitude = avg_load * adaptive_rule.adjustment_factor
        elif avg_load < 0.3:  # 낮은 부하
            adjustment_direction = 1   # 제한 완화
            adjustment_magnitude = (1 - avg_load) * adaptive_rule.adjustment_factor
        else:
            return {'adjust': False}
        
        return {
            'adjust': True,
            'direction': adjustment_direction,
            'magnitude': adjustment_magnitude,
            'current_load': avg_load
        }
    
    async def _apply_adjustment(self, 
                              rule_name: str, 
                              adaptive_rule: AdaptiveRule, 
                              adjustment: Dict[str, Any]):
        """레이트리밋 규칙 조정 적용"""
        
        base_limit = adaptive_rule.base_rule.limit
        adjustment_amount = int(base_limit * adjustment['magnitude'])
        
        if adjustment['direction'] == -1:
            # 제한 강화
            new_limit = max(base_limit - adjustment_amount, adaptive_rule.min_limit)
        else:
            # 제한 완화
            new_limit = min(base_limit + adjustment_amount, adaptive_rule.max_limit)
        
        if new_limit == base_limit:
            return  # 조정이 필요 없음
        
        # 규칙 업데이트
        old_limit = base_limit
        adaptive_rule.base_rule.limit = new_limit
        
        # 조정 기록
        adjustment_record = {
            'rule_name': rule_name,
            'old_limit': old_limit,
            'new_limit': new_limit,
            'direction': 'decrease' if adjustment['direction'] == -1 else 'increase',
            'load_factor': adjustment['current_load'],
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'cpu_usage': self.current_metrics.cpu_usage,
                'memory_usage': self.current_metrics.memory_usage,
                'error_rate': self.current_metrics.error_rate,
                'response_time_p95': self.current_metrics.response_time_p95
            }
        }
        
        self.adjustment_history.append(adjustment_record)
        self.last_adjustment[rule_name] = datetime.now()
        
        self.logger.info(
            f"Adjusted rate limit rule {rule_name}: {old_limit} -> {new_limit}",
            extra=adjustment_record
        )
        
        # 레이트리밋 규칙 업데이트 (실제 구현에서는 동적 업데이트 로직 필요)
        await self._update_rate_limiter_rule(rule_name, adaptive_rule.base_rule)
    
    async def _update_rate_limiter_rule(self, rule_name: str, updated_rule: RateLimitRule):
        """레이트리밋 규칙 동적 업데이트"""
        # 실제 구현에서는 rate_limiter의 규칙을 동적으로 업데이트
        # 여기서는 로깅만 수행
        self.logger.info(f"Updated rate limiter rule: {rule_name} with limit {updated_rule.limit}")
    
    def get_adjustment_history(self, 
                             rule_name: Optional[str] = None,
                             time_range: Optional[timedelta] = None) -> List[Dict[str, Any]]:
        """조정 이력 조회"""
        
        history = self.adjustment_history
        
        # 규칙 이름 필터링
        if rule_name:
            history = [h for h in history if h['rule_name'] == rule_name]
        
        # 시간 범위 필터링
        if time_range:
            cutoff_time = datetime.now() - time_range
            history = [h for h in history 
                     if datetime.fromisoformat(h['timestamp']) >= cutoff_time]
        
        return history
    
    def get_current_limits(self) -> Dict[str, int]:
        """현재 레이트리밋 제한 조회"""
        
        return {
            rule_name: adaptive_rule.base_rule.limit
            for rule_name, adaptive_rule in self.adaptive_rules.items()
        }
    
    def reset_to_defaults(self):
        """기본값으로 초기화"""
        
        for rule_name, adaptive_rule in self.adaptive_rules.items():
            # 원래 기본값으로 복원 (실제로는 별도 저장 필요)
            adaptive_rule.base_rule.limit = adaptive_rule.base_rule.limit
        
        self.adjustment_history.clear()
        self.last_adjustment.clear()
        
        self.logger.info("Reset all adaptive rate limits to defaults")
```

## 4. 레이트리밋 모니터링 및 분석

### 4.1 레이트리밋 모니터링

```python
# rate_limiting/monitoring.py
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import logging
from collections import defaultdict, deque

@dataclass
class RateLimitEvent:
    """레이트리밋 이벤트"""
    timestamp: datetime
    identifier: str
    rule_name: str
    endpoint: Optional[str]
    api_provider: Optional[str]
    allowed: bool
    limit: int
    remaining: int
    retry_after: Optional[int] = None

class RateLimitMonitor:
    """레이트리밋 모니터링 시스템"""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.logger = logging.getLogger(__name__)
        
        # 이벤트 저장
        self.events: deque = deque(maxlen=max_events)
        
        # 통계 데이터
        self.hourly_stats: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.daily_stats: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
        # 위반자 목록
        self.violators: Dict[str, Dict[str, Any]] = {}
        
        # API 사용량 추적
        self.api_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    async def record_event(self, event: RateLimitEvent):
        """레이트리밋 이벤트 기록"""
        
        # 이벤트 저장
        self.events.append(event)
        
        # 통계 업데이트
        await self._update_statistics(event)
        
        # 위반자 추적
        if not event.allowed:
            await self._track_violator(event)
        
        # API 사용량 추적
        if event.api_provider:
            await self._track_api_usage(event)
    
    async def _update_statistics(self, event: RateLimitEvent):
        """통계 데이터 업데이트"""
        
        hour_key = event.timestamp.strftime('%Y-%m-%d %H')
        day_key = event.timestamp.strftime('%Y-%m-%d')
        
        # 시간별 통계
        if event.allowed:
            self.hourly_stats['allowed'][int(event.timestamp.hour)] += 1
        else:
            self.hourly_stats['denied'][int(event.timestamp.hour)] += 1
        
        # 일별 통계
        if event.allowed:
            self.daily_stats['allowed'][int(event.timestamp.day)] += 1
        else:
            self.daily_stats['denied'][int(event.timestamp.day)] += 1
    
    async def _track_violator(self, event: RateLimitEvent):
        """위반자 추적"""
        
        if event.identifier not in self.violators:
            self.violators[event.identifier] = {
                'first_violation': event.timestamp,
                'last_violation': event.timestamp,
                'violation_count': 0,
                'rules_violated': set(),
                'endpoints': set(),
                'api_providers': set()
            }
        
        violator = self.violators[event.identifier]
        violator['last_violation'] = event.timestamp
        violator['violation_count'] += 1
        violator['rules_violated'].add(event.rule_name)
        
        if event.endpoint:
            violator['endpoints'].add(event.endpoint)
        
        if event.api_provider:
            violator['api_providers'].add(event.api_provider)
    
    async def _track_api_usage(self, event: RateLimitEvent):
        """API 사용량 추적"""
        
        if event.api_provider and event.allowed:
            self.api_usage[event.api_provider]['requests'] += 1
            self.api_usage[event.api_provider]['last_request'] = event.timestamp
    
    def get_violation_summary(self, time_range: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """위반 요약 정보"""
        
        cutoff_time = datetime.now() - time_range
        
        # 최근 위반자 필터링
        recent_violators = {
            identifier: data
            for identifier, data in self.violators.items()
            if data['last_violation'] >= cutoff_time
        }
        
        # 위반 유형별 그룹화
        violation_types = defaultdict(int)
        top_violators = sorted(
            recent_violators.items(),
            key=lambda x: x[1]['violation_count'],
            reverse=True
        )[:10]
        
        for violator_data in recent_violators.values():
            for rule in violator_data['rules_violated']:
                violation_types[rule] += 1
        
        return {
            'time_range_hours': time_range.total_seconds() / 3600,
            'total_violators': len(recent_violators),
            'violation_types': dict(violation_types),
            'top_violators': [
                {
                    'identifier': identifier,
                    'violation_count': data['violation_count'],
                    'rules_violated': list(data['rules_violated']),
                    'endpoints': list(data['endpoints']),
                    'api_providers': list(data['api_providers'])
                }
                for identifier, data in top_violators
            ]
        }
    
    def get_api_usage_summary(self, time_range: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """API 사용량 요약"""
        
        cutoff_time = datetime.now() - time_range
        
        # 최근 API 사용량 필터링
        recent_usage = {}
        for api_provider, usage_data in self.api_usage.items():
            if usage_data.get('last_request', datetime.min) >= cutoff_time:
                recent_usage[api_provider] = usage_data
        
        return {
            'time_range_hours': time_range.total_seconds() / 3600,
            'api_providers': recent_usage,
            'total_requests': sum(data['requests'] for data in recent_usage.values())
        }
    
    def get_hourly_pattern(self, days: int = 7) -> Dict[str, Any]:
        """시간별 패턴 분석"""
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # 최근 이벤트 필터링
        recent_events = [
            event for event in self.events
            if event.timestamp >= cutoff_time
        ]
        
        # 시간별 패턴 계산
        hourly_pattern = defaultdict(lambda: {'allowed': 0, 'denied': 0})
        
        for event in recent_events:
            hour = event.timestamp.hour
            if event.allowed:
                hourly_pattern[hour]['allowed'] += 1
            else:
                hourly_pattern[hour]['denied'] += 1
        
        # 패턴 정규화
        normalized_pattern = {}
        for hour in range(24):
            if hour in hourly_pattern:
                total = hourly_pattern[hour]['allowed'] + hourly_pattern[hour]['denied']
                if total > 0:
                    normalized_pattern[hour] = {
                        'allowed': hourly_pattern[hour]['allowed'],
                        'denied': hourly_pattern[hour]['denied'],
                        'denial_rate': hourly_pattern[hour]['denied'] / total,
                        'total_requests': total
                    }
                else:
                    normalized_pattern[hour] = {
                        'allowed': 0,
                        'denied': 0,
                        'denial_rate': 0,
                        'total_requests': 0
                    }
        
        return {
            'analysis_period_days': days,
            'hourly_pattern': normalized_pattern,
            'peak_hours': sorted(
                [(hour, data['total_requests']) for hour, data in normalized_pattern.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def export_metrics(self, format: str = 'json') -> str:
        """메트릭 내보내기"""
        
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_events': len(self.events),
            'violation_summary': self.get_violation_summary(),
            'api_usage_summary': self.get_api_usage_summary(),
            'hourly_pattern': self.get_hourly_pattern(),
            'total_violators': len(self.violators)
        }
        
        if format == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
```

## 5. 레이트리밋 정책 관리

### 5.1 정책 관리 API

```python
# rate_limiting/policy_manager.py
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import logging
from .rate_limiter import RateLimiter, RateLimitRule, RateLimitType

@dataclass
class RateLimitPolicy:
    """레이트리밋 정책"""
    name: str
    description: str
    rules: List[RateLimitRule]
    enabled: bool = True
    priority: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    created_by: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class RateLimitPolicyManager:
    """레이트리밋 정책 관리자"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
        
        # 정책 저장소
        self.policies: Dict[str, RateLimitPolicy] = {}
        
        # 기본 정책 초기화
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """기본 정책 초기화"""
        
        # 개발자 정책
        developer_policy = RateLimitPolicy(
            name="developer",
            description="Developer access with higher limits",
            rules=[
                RateLimitRule("dev_rps", RateLimitType.REQUEST_PER_SECOND, 100, priority=10),
                RateLimitRule("dev_rpm", RateLimitType.REQUEST_PER_MINUTE, 10000, priority=10),
                RateLimitRule("dev_rph", RateLimitType.REQUEST_PER_HOUR, 100000, priority=10),
            ],
            priority=100
        )
        
        # 프리미엄 사용자 정책
        premium_policy = RateLimitPolicy(
            name="premium",
            description="Premium user access with elevated limits",
            rules=[
                RateLimitRule("premium_rps", RateLimitType.REQUEST_PER_SECOND, 50, priority=8),
                RateLimitRule("premium_rpm", RateLimitType.REQUEST_PER_MINUTE, 5000, priority=8),
                RateLimitRule("premium_rph", RateLimitType.REQUEST_PER_HOUR, 50000, priority=8),
            ],
            priority=80
        )
        
        # 일반 사용자 정책
        standard_policy = RateLimitPolicy(
            name="standard",
            description="Standard user access with normal limits",
            rules=[
                RateLimitRule("standard_rps", RateLimitType.REQUEST_PER_SECOND, 10, priority=5),
                RateLimitRule("standard_rpm", RateLimitType.REQUEST_PER_MINUTE, 1000, priority=5),
                RateLimitRule("standard_rph", RateLimitType.REQUEST_PER_HOUR, 10000, priority=5),
            ],
            priority=50
        )
        
        # 익명 사용자 정책
        anonymous_policy = RateLimitPolicy(
            name="anonymous",
            description="Anonymous user access with restricted limits",
            rules=[
                RateLimitRule("anon_rps", RateLimitType.REQUEST_PER_SECOND, 5, priority=3),
                RateLimitRule("anon_rpm", RateLimitType.REQUEST_PER_MINUTE, 100, priority=3),
                RateLimitRule("anon_rph", RateLimitType.REQUEST_PER_HOUR, 1000, priority=3),
            ],
            priority=30
        )
        
        # 정책 등록
        for policy in [developer_policy, premium_policy, standard_policy, anonymous_policy]:
            self.policies[policy.name] = policy
    
    def create_policy(self, 
                     name: str,
                     description: str,
                     rules: List[RateLimitRule],
                     priority: int = 0,
                     created_by: str = None) -> RateLimitPolicy:
        """새 정책 생성"""
        
        if name in self.policies:
            raise ValueError(f"Policy '{name}' already exists")
        
        policy = RateLimitPolicy(
            name=name,
            description=description,
            rules=rules,
            priority=priority,
            created_by=created_by
        )
        
        self.policies[name] = policy
        
        self.logger.info(f"Created rate limit policy: {name}")
        
        return policy
    
    def update_policy(self, 
                     name: str,
                     description: Optional[str] = None,
                     rules: Optional[List[RateLimitRule]] = None,
                     priority: Optional[int] = None,
                     enabled: Optional[bool] = None) -> RateLimitPolicy:
        """정책 업데이트"""
        
        if name not in self.policies:
            raise ValueError(f"Policy '{name}' not found")
        
        policy = self.policies[name]
        
        if description is not None:
            policy.description = description
        
        if rules is not None:
            policy.rules = rules
        
        if priority is not None:
            policy.priority = priority
        
        if enabled is not None:
            policy.enabled = enabled
        
        policy.updated_at = datetime.now()
        
        self.logger.info(f"Updated rate limit policy: {name}")
        
        return policy
    
    def delete_policy(self, name: str) -> bool:
        """정책 삭제"""
        
        if name not in self.policies:
            return False
        
        del self.policies[name]
        
        self.logger.info(f"Deleted rate limit policy: {name}")
        
        return True
    
    def get_policy(self, name: str) -> Optional[RateLimitPolicy]:
        """정책 조회"""
        return self.policies.get(name)
    
    def list_policies(self, enabled_only: bool = False) -> List[RateLimitPolicy]:
        """정책 목록 조회"""
        
        policies = list(self.policies.values())
        
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        
        # 우선순위별 정렬
        policies.sort(key=lambda x: x.priority, reverse=True)
        
        return policies
    
    def apply_policy_to_user(self, user_id: str, policy_name: str) -> bool:
        """사용자에게 정책 적용"""
        
        policy = self.get_policy(policy_name)
        if not policy or not policy.enabled:
            return False
        
        # 실제 구현에서는 사용자-정책 매핑 저장
        # 여기서는 로깅만 수행
        self.logger.info(f"Applied policy '{policy_name}' to user '{user_id}'")
        
        return True
    
    def get_user_policy(self, user_id: str) -> Optional[str]:
        """사용자의 정책 조회"""
        
        # 실제 구현에서는 사용자-정책 매핑에서 조회
        # 여기서는 기본 정책 반환
        return "standard"
    
    def analyze_policy_effectiveness(self, 
                                   policy_name: str,
                                   time_range: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """정책 효과 분석"""
        
        policy = self.get_policy(policy_name)
        if not policy:
            raise ValueError(f"Policy '{policy_name}' not found")
        
        # 실제 구현에서는 레이트리밋 모니터링 데이터 분석
        # 여기서는 모의 데이터 반환
        
        return {
            'policy_name': policy_name,
            'analysis_period': time_range.total_seconds() / 86400,  # days
            'total_requests': 10000,
            'blocked_requests': 500,
            'block_rate': 0.05,
            'average_response_time': 0.2,
            'user_satisfaction': 4.2,  # 1-5 scale
            'recommendations': [
                "Consider increasing limits during peak hours",
                "Monitor API usage patterns for optimization"
            ]
        }
    
    def export_policies(self, format: str = 'json') -> str:
        """정책 내보내기"""
        
        policies_data = {
            'export_timestamp': datetime.now().isoformat(),
            'policies': [
                {
                    **asdict(policy),
                    'rules': [asdict(rule) for rule in policy.rules]
                }
                for policy in self.policies.values()
            ]
        }
        
        if format == 'json':
            return json.dumps(policies_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_policies(self, policies_json: str, overwrite: bool = False) -> int:
        """정책 가져오기"""
        
        try:
            policies_data = json.loads(policies_json)
            imported_count = 0
            
            for policy_data in policies_data.get('policies', []):
                name = policy_data['name']
                
                if name in self.policies and not overwrite:
                    continue
                
                # 규칙 재구성
                rules = []
                for rule_data in policy_data['rules']:
                    rule = RateLimitRule(
                        name=rule_data['name'],
                        limit_type=RateLimitType(rule_data['limit_type']),
                        limit=rule_data['limit'],
                        window=rule_data.get('window', 1),
                        burst=rule_data.get('burst', 0),
                        priority=rule_data.get('priority', 0)
                    )
                    rules.append(rule)
                
                # 정책 생성/업데이트
                policy = RateLimitPolicy(
                    name=policy_data['name'],
                    description=policy_data['description'],
                    rules=rules,
                    enabled=policy_data.get('enabled', True),
                    priority=policy_data.get('priority', 0),
                    created_by=policy_data.get('created_by', 'imported')
                )
                
                if name in self.policies:
                    policy.created_at = self.policies[name].created_at
                
                self.policies[name] = policy
                imported_count += 1
            
            self.logger.info(f"Imported {imported_count} rate limit policies")
            
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Failed to import policies: {str(e)}")
            raise
```

## 6. 구현 가이드

### 6.1 단계별 구현 계획

#### 1단계: 기본 레이트리밋 구현 (1-2주)
- Redis 기반 슬라이딩 윈도우 레이트리밋 구현
- 기본 규칙 설정 및 API 게이트웨이 미들웨어 통합
- 단순한 사용자별/IP별 제한 적용

#### 2단계: 외부 API 레이트리밋 (1주)
- Yahoo Finance, Reddit, Twitter API별 제한 구현
- API 호출 큐 관리 시스템 구축
- 동시 요청 제한 기능 추가

#### 3단계: 적응형 레이트리밋 (2-3주)
- 시스템 메트릭 수집 및 분석
- 동적 레이트리밋 조정 로직 구현
- 부하 기반 자동 조정 기능

#### 4단계: 모니터링 및 분석 (1-2주)
- 레이트리밋 이벤트 추적 시스템
- 대시보드 및 알림 기능
- 위반자 분석 및 패턴 인식

#### 5단계: 정책 관리 시스템 (1-2주)
- 정책 CRUD API 구현
- 사용자별 정책 할당 시스템
- 정책 효과 분석 도구

### 6.2 성능 고려사항

1. **Redis 최적화**
   - 파이프라인 사용으로 네트워크 왕복 최소화
   - 적절한 만료 시간 설정
   - 클러스터링 고려한 키 분배

2. **메모리 관리**
   - 이벤트 데이터 크기 제한
   - 주기적인 오래된 데이터 정리
   - 효율적인 데이터 구조 사용

3. **동시성 처리**
   - 비동기 처리로 높은 처리량 보장
   - 락 최소화 설계
   - 원자적 연산 활용

### 6.3 보안 고려사항

1. **식별자 보호**
   - 사용자 ID 해시 처리
   - IP 주소 마스킹
   - 민감 정보 노출 방지

2. **공격 방지**
   - 분산 레이트리밋으로 우회 시도 방지
   - 의심스러운 패턴 탐지
   - 동적 블랙리스트 관리

3. **데이터 무결성**
   - 로그 데이터 위변조 방지
   - 감사 추적 기능
   - 정책 변경 기록

## 7. 결론

본 API 레이트리밋 전략은 InsiteChart 플랫폼의 안정적인 운영을 위한 포괄적인 솔루션을 제공합니다. 다계층 아키텍처, 적응형 조정, 상세한 모니터링을 통해 외부 API 제약을 준수하면서도 사용자에게 최적의 서비스를 제공할 수 있습니다.

단계적인 구현을 통해 시스템 안정성을 점진적으로 강화하고, 실제 운영 데이터를 기반으로 정책을 최적화하여 장기적인 성공을 보장할 수 있습니다.