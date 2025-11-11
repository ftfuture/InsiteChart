"""
API Gateway for InsiteChart platform.

This module implements the API Gateway pattern to provide a single
entry point for all client requests with centralized routing,
authentication, rate limiting, and request/response transformation.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import re

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.unified_models import UnifiedDataRequest
from ..middleware.auth_middleware import require_auth, optional_auth
from ..cache.unified_cache import UnifiedCacheManager


class GatewayRouteType(str, Enum):
    """Gateway route type enumeration."""
    INTERNAL = "internal"
    EXTERNAL = "external"
    PROXY = "proxy"
    AGGREGATE = "aggregate"


class GatewayPriority(str, Enum):
    """Gateway route priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitBreakerState(str, Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


@dataclass
class GatewayRoute:
    """Gateway route configuration."""
    path: str
    method: str
    target_service: str
    target_path: str
    route_type: GatewayRouteType
    priority: GatewayPriority
    auth_required: bool = True
    rate_limit: Optional[int] = None
    timeout: int = 30
    retry_count: int = 0
    circuit_breaker_threshold: int = 5
    cache_ttl: Optional[int] = None
    request_transform: Optional[Callable] = None
    response_transform: Optional[Callable] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'path': self.path,
            'method': self.method,
            'target_service': self.target_service,
            'target_path': self.target_path,
            'route_type': self.route_type,
            'priority': self.priority,
            'auth_required': self.auth_required,
            'rate_limit': self.rate_limit,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'circuit_breaker_threshold': self.circuit_breaker_threshold,
            'cache_ttl': self.cache_ttl,
            'metadata': self.metadata
        }


@dataclass
class ServiceHealth:
    """Service health status."""
    service_name: str
    status: str  # healthy, unhealthy, degraded
    last_check: datetime
    response_time: float
    error_count: int
    success_count: int
    last_error: Optional[str] = None
    circuit_breaker_open: bool = False
    circuit_breaker_opened_at: Optional[datetime] = None


@dataclass
class GatewayMetrics:
    """Gateway performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    requests_per_minute: float = 0.0
    active_connections: int = 0
    cache_hit_rate: float = 0.0
    rate_limited_requests: int = 0
    auth_failures: int = 0


class APIGateway:
    """API Gateway implementation for centralized request routing."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Route registry
        self.routes: Dict[str, List[GatewayRoute]] = {}
        
        # Service health tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting
        self.rate_limiters: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = GatewayMetrics()
        
        # Request tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Service discovery
        self.service_registry: Dict[str, Dict[str, Any]] = {}
        
        # Gateway configuration
        self.config = {
            'default_timeout': 30,
            'max_retries': 3,
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60,  # seconds
            'rate_limit_window': 60,  # seconds
            'health_check_interval': 30,  # seconds
            'metrics_window': 300,  # seconds
            'max_concurrent_requests': 1000
        }
        
        # Initialize default routes
        self._initialize_default_routes()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _initialize_default_routes(self):
        """Initialize default gateway routes."""
        # Stock service routes
        self.register_route(GatewayRoute(
            path="/api/v1/stocks/{symbol}",
            method="GET",
            target_service="stock_service",
            target_path="/stock",
            route_type=GatewayRouteType.PROXY,
            priority=GatewayPriority.NORMAL,
            auth_required=False,
            cache_ttl=300
        ))
        
        self.register_route(GatewayRoute(
            path="/api/v1/stocks/search",
            method="POST",
            target_service="stock_service",
            target_path="/search",
            route_type=GatewayRouteType.PROXY,
            priority=GatewayPriority.NORMAL,
            auth_required=False,
            cache_ttl=180
        ))
        
        # Sentiment service routes
        self.register_route(GatewayRoute(
            path="/api/v1/sentiment/{symbol}",
            method="GET",
            target_service="sentiment_service",
            target_path="/sentiment",
            route_type=GatewayRouteType.PROXY,
            priority=GatewayPriority.NORMAL,
            auth_required=False,
            cache_ttl=120
        ))
        
        # Unified service routes
        self.register_route(GatewayRoute(
            path="/api/v1/unified/stocks/{symbol}",
            method="GET",
            target_service="unified_service",
            target_path="/stock",
            route_type=GatewayRouteType.PROXY,
            priority=GatewayPriority.HIGH,
            auth_required=False,
            cache_ttl=300
        ))
        
        self.register_route(GatewayRoute(
            path="/api/v1/unified/search",
            method="POST",
            target_service="unified_service",
            target_path="/search",
            route_type=GatewayRouteType.PROXY,
            priority=GatewayPriority.HIGH,
            auth_required=False,
            cache_ttl=180
        ))
        
        self.register_route(GatewayRoute(
            path="/api/v1/unified/trending",
            method="GET",
            target_service="unified_service",
            target_path="/trending",
            route_type=GatewayRouteType.PROXY,
            priority=GatewayPriority.HIGH,
            auth_required=False,
            cache_ttl=600
        ))
        
        # Aggregation routes
        self.register_route(GatewayRoute(
            path="/api/v1/market/overview",
            method="GET",
            target_service="unified_service",
            target_path="/market-overview",
            route_type=GatewayRouteType.AGGREGATE,
            priority=GatewayPriority.HIGH,
            auth_required=False,
            cache_ttl=60
        ))
        
        self.register_route(GatewayRoute(
            path="/api/v1/health/gateway",
            method="GET",
            target_service="gateway",
            target_path="/health",
            route_type=GatewayRouteType.INTERNAL,
            priority=GatewayPriority.CRITICAL,
            auth_required=False
        ))
    
    def _start_background_tasks(self):
        """Start background tasks for health checks and metrics."""
        try:
            # Start health check task
            loop = asyncio.get_event_loop()
            if loop and loop.is_running():
                asyncio.create_task(self._health_check_loop())
            
            # Start metrics collection task
            if loop and loop.is_running():
                asyncio.create_task(self._metrics_collection_loop())
            
            # Start cleanup task
            if loop and loop.is_running():
                asyncio.create_task(self._cleanup_loop())
        except RuntimeError:
            # No event loop running, skip background tasks
            pass
    
    def register_route(self, route: GatewayRoute):
        """Register a new route with the gateway."""
        route_key = f"{route.method}:{route.path}"
        
        if route_key not in self.routes:
            self.routes[route_key] = []
        
        # Insert route in priority order
        self.routes[route_key].append(route)
        self.routes[route_key].sort(key=lambda r: self._get_priority_value(r.priority), reverse=True)
        
        # Initialize service health tracking
        if route.target_service not in self.service_health:
            self.service_health[route.target_service] = ServiceHealth(
                service_name=route.target_service,
                status="unknown",
                last_check=datetime.utcnow(),
                response_time=0.0,
                error_count=0,
                success_count=0
            )
        
        # Initialize circuit breaker
        if route.target_service not in self.circuit_breakers:
            self.circuit_breakers[route.target_service] = {
                'state': 'closed',  # closed, open, half-open
                'failure_count': 0,
                'last_failure_time': None,
                'success_count': 0
            }
        
        # Initialize rate limiter
        if route.rate_limit and route.target_service not in self.rate_limiters:
            self.rate_limiters[route.target_service] = {
                'requests': [],
                'limit': route.rate_limit
            }
        
        self.logger.info(f"Registered route: {route.method} {route.path} -> {route.target_service}")
    
    def add_route(self, route: GatewayRoute):
        """Add a route to the gateway (alias for register_route)."""
        self.register_route(route)
    
    def add_middleware(self, middleware_func):
        """Add middleware to the gateway."""
        # This is a placeholder for middleware functionality
        # In a real implementation, this would add middleware to the request processing pipeline
        pass
    
    def _get_priority_value(self, priority: GatewayPriority) -> int:
        """Convert priority enum to numeric value."""
        priority_values = {
            GatewayPriority.LOW: 1,
            GatewayPriority.NORMAL: 2,
            GatewayPriority.HIGH: 3,
            GatewayPriority.CRITICAL: 4
        }
        return priority_values.get(priority, 2)
    
    async def process_request(self, request: Request) -> Response:
        """Process incoming request through gateway."""
        start_time = time.time()
        request_id = self._generate_request_id()
        
        try:
            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.active_connections += 1
            
            # Store request info
            self.active_requests[request_id] = {
                'start_time': start_time,
                'method': request.method,
                'path': request.url.path,
                'client_ip': self._get_client_ip(request)
            }
            
            # Find matching route
            route = self._find_matching_route(request)
            if not route:
                self.metrics.failed_requests += 1
                return self._create_error_response(
                    404,
                    "Route not found",
                    request_id
                )
            
            # Check authentication
            if route.auth_required:
                auth_result = await self._check_authentication(request)
                if not auth_result['success']:
                    self.metrics.auth_failures += 1
                    return self._create_error_response(
                        401,
                        "Authentication required",
                        request_id,
                        {'auth_error': auth_result['error']}
                    )
            
            # Check rate limiting
            if route.rate_limit and not self._check_rate_limit(route):
                self.metrics.rate_limited_requests += 1
                return self._create_error_response(
                    429,
                    "Rate limit exceeded",
                    request_id,
                    {'retry_after': self.config['rate_limit_window']}
                )
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(route.target_service):
                return self._create_error_response(
                    503,
                    "Service temporarily unavailable",
                    request_id,
                    {'circuit_breaker': 'open'}
                )
            
            # Check cache
            if route.cache_ttl:
                cached_response = await self._check_cache(request, route)
                if cached_response:
                    self.metrics.cache_hit_rate = self._update_cache_hit_rate(True)
                    return cached_response
            
            self.metrics.cache_hit_rate = self._update_cache_hit_rate(False)
            
            # Process request
            response = await self._forward_request(request, route, request_id)
            
            # Update metrics
            self._update_request_metrics(start_time, request_id, route.target_service, True)
            
            # Cache response if applicable
            if route.cache_ttl and response.status_code == 200:
                await self._cache_response(request, route, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Gateway error processing request {request_id}: {str(e)}")
            self._update_request_metrics(start_time, request_id, None, False)
            
            return self._create_error_response(
                500,
                "Internal server error",
                request_id,
                {'error': str(e)}
            )
        finally:
            # Clean up request tracking
            if request_id in self.active_requests:
                del self.active_requests[request_id]
            
            self.metrics.active_connections -= 1
    
    def _find_matching_route(self, request: Request) -> Optional[GatewayRoute]:
        """Find matching route for request."""
        method = request.method
        path = request.url.path
        
        # Try exact match first
        route_key = f"{method}:{path}"
        if route_key in self.routes and self.routes[route_key]:
            return self.routes[route_key][0]  # Return highest priority route
        
        # Try pattern matching
        for route_key, route_list in self.routes.items():
            if not route_key.startswith(method + ":"):
                continue
            
            for route in route_list:
                if self._path_matches(route.path, path):
                    return route
        
        return None
    
    def _path_matches(self, route_path: str, request_path: str) -> bool:
        """Check if request path matches route pattern."""
        # Convert route path to regex pattern
        pattern = route_path.replace('{', '(?P<').replace('}', '>[^/]+)')
        pattern = f"^{pattern}$"
        
        return re.match(pattern, request_path) is not None
    
    async def _check_authentication(self, request: Request) -> Dict[str, Any]:
        """Check request authentication."""
        try:
            # Extract authorization header
            auth_header = request.headers.get('authorization')
            if not auth_header:
                return {'success': False, 'error': 'No authorization header'}
            
            # This would integrate with the actual auth middleware
            # For now, just check if header exists
            if auth_header.startswith('Bearer '):
                return {'success': True}
            else:
                return {'success': False, 'error': 'Invalid authorization format'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_rate_limit(self, route: GatewayRoute) -> bool:
        """Check if request is within rate limits."""
        if not route.rate_limit or route.target_service not in self.rate_limiters:
            return True
        
        rate_limiter = self.rate_limiters[route.target_service]
        now = time.time()
        
        # Clean old requests
        rate_limiter['requests'] = [
            req_time for req_time in rate_limiter['requests']
            if now - req_time < self.config['rate_limit_window']
        ]
        
        # Check if under limit
        if len(rate_limiter['requests']) < route.rate_limit:
            rate_limiter['requests'].append(now)
            return True
        
        return False
    
    def _is_circuit_breaker_open(self, service_name: str) -> bool:
        """Check if circuit breaker is open for service."""
        if service_name not in self.circuit_breakers:
            return False
        
        circuit_breaker = self.circuit_breakers[service_name]
        
        if circuit_breaker['state'] == 'open':
            # Check if timeout has passed
            if circuit_breaker['last_failure_time']:
                time_since_failure = time.time() - circuit_breaker['last_failure_time']
                if time_since_failure > self.config['circuit_breaker_timeout']:
                    # Move to half-open state
                    circuit_breaker['state'] = 'half-open'
                    return False
            return True
        
        return False
    
    async def _check_cache(self, request: Request, route: GatewayRoute) -> Optional[Response]:
        """Check if response is cached."""
        try:
            cache_key = self._generate_cache_key(request, route)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                return JSONResponse(
                    content=cached_data,
                    status_code=200,
                    headers={
                        'X-Cache': 'HIT',
                        'X-Cache-Key': cache_key
                    }
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Cache check error: {str(e)}")
            return None
    
    async def _cache_response(self, request: Request, route: GatewayRoute, response: Response):
        """Cache response if applicable."""
        try:
            if route.cache_ttl and response.status_code == 200:
                cache_key = self._generate_cache_key(request, route)
                
                # Extract response data
                if hasattr(response, 'body'):
                    response_data = response.body
                else:
                    # For JSONResponse, get the content
                    if hasattr(response, 'body'):
                        response_data = response.body.decode()
                    else:
                        response_data = json.dumps(response.content)
                
                await self.cache_manager.set(cache_key, response_data, route.cache_ttl)
                
        except Exception as e:
            self.logger.error(f"Cache storage error: {str(e)}")
    
    def _generate_cache_key(self, request: Request, route: GatewayRoute) -> str:
        """Generate cache key for request."""
        # Include method, path, and relevant query parameters
        cache_components = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        
        cache_string = ":".join(cache_components)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    async def _forward_request(self, request: Request, route: GatewayRoute, request_id: str) -> Response:
        """Forward request to target service."""
        try:
            # Extract path parameters
            path_params = self._extract_path_params(request, route)
            
            # Transform request if needed
            if route.request_transform:
                request = await route.request_transform(request)
            
            # Forward to target service
            # This would integrate with the actual service calls
            # For now, simulate the forwarding
            response_data = await self._simulate_service_call(request, route, path_params)
            
            # Transform response if needed
            if route.response_transform:
                response_data = await route.response_transform(response_data)
            
            # Create response
            response = JSONResponse(
                content=response_data,
                status_code=200,
                headers={
                    'X-Request-ID': request_id,
                    'X-Service': route.target_service,
                    'X-Gateway': 'insitechart-gateway'
                }
            )
            
            # Update circuit breaker state on success
            self._update_circuit_breaker(route.target_service, True)
            
            return response
            
        except Exception as e:
            # Update circuit breaker state on failure
            self._update_circuit_breaker(route.target_service, False)
            
            self.logger.error(f"Error forwarding request {request_id}: {str(e)}")
            raise
    
    async def _simulate_service_call(self, request: Request, route: GatewayRoute, path_params: Dict[str, str]) -> Dict[str, Any]:
        """Simulate service call for demonstration."""
        # Check if service is registered and has a mock implementation
        if route.target_service in self.service_registry:
            service_info = self.service_registry[route.target_service]
            if 'instance' in service_info and hasattr(service_info['instance'], 'call'):
                try:
                    # Call the actual service method
                    result = await service_info['instance'].call()
                    return result
                except Exception as e:
                    # Re-raise the exception to trigger circuit breaker
                    raise e
        
        # This would be replaced with actual service calls
        return {
            'success': True,
            'data': {
                'message': f"Simulated response for {route.target_service}",
                'path_params': path_params,
                'query_params': dict(request.query_params),
                'timestamp': datetime.utcnow().isoformat()
            },
            'gateway_processed': True
        }
    
    def _extract_path_params(self, request: Request, route: GatewayRoute) -> Dict[str, str]:
        """Extract path parameters from request."""
        path_params = {}
        
        # Simple parameter extraction for demonstration
        route_parts = route.path.split('/')
        request_parts = request.url.path.split('/')
        
        for i, part in enumerate(route_parts):
            if part.startswith('{') and part.endswith('}'):
                param_name = part[1:-1]
                if i < len(request_parts):
                    path_params[param_name] = request_parts[i]
        
        return path_params
    
    def _update_circuit_breaker(self, service_name: str, success: bool):
        """Update circuit breaker state."""
        if service_name not in self.circuit_breakers:
            return
        
        circuit_breaker = self.circuit_breakers[service_name]
        
        if success:
            circuit_breaker['success_count'] += 1
            if circuit_breaker['state'] == 'half-open':
                # Reset on success in half-open state
                circuit_breaker['state'] = 'closed'
                circuit_breaker['failure_count'] = 0
        else:
            circuit_breaker['failure_count'] += 1
            circuit_breaker['last_failure_time'] = time.time()
            
            # Open circuit if threshold reached
            if circuit_breaker['failure_count'] >= self.config['circuit_breaker_threshold']:
                circuit_breaker['state'] = 'open'
    
    def _update_request_metrics(self, start_time: float, request_id: str, service_name: Optional[str], success: bool):
        """Update request metrics."""
        response_time = time.time() - start_time
        
        # Update gateway metrics
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # Update average response time
        total_requests = self.metrics.successful_requests + self.metrics.failed_requests
        self.metrics.avg_response_time = (
            (self.metrics.avg_response_time * (total_requests - 1) + response_time) / total_requests
        )
        
        # Update service health
        if service_name and service_name in self.service_health:
            health = self.service_health[service_name]
            health.last_check = datetime.utcnow()
            health.response_time = response_time
            
            if success:
                health.success_count += 1
            else:
                health.error_count += 1
    
    def _update_cache_hit_rate(self, is_hit: bool) -> float:
        """Update cache hit rate metric."""
        total_requests = self.metrics.total_requests
        if total_requests == 0:
            return 0.0
        
        # Simple exponential moving average for cache hit rate
        current_rate = self.metrics.cache_hit_rate
        if is_hit:
            new_rate = (current_rate * 0.9) + (1.0 * 0.1)
        else:
            new_rate = (current_rate * 0.9) + (0.0 * 0.1)
        
        return new_rate
    
    def _create_error_response(self, status_code: int, message: str, request_id: str, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """Create standardized error response."""
        error_response = {
            'success': False,
            'error': True,
            'message': message,
            'request_id': request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'gateway': 'insitechart-gateway'
        }
        
        if details:
            error_response['details'] = details
        
        return JSONResponse(
            content=error_response,
            status_code=status_code,
            headers={
                'X-Request-ID': request_id,
                'X-Gateway': 'insitechart-gateway'
            }
        )
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return f"req_{int(time.time() * 1000)}_{hash(str(time.time()))}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded IP
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fall back to client IP
        return request.client.host if request.client else 'unknown'
    
    async def _health_check_loop(self):
        """Background task for service health checks."""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config['health_check_interval'])
            except Exception as e:
                self.logger.error(f"Health check loop error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self):
        """Perform health checks on all registered services."""
        for service_name in self.service_health.keys():
            try:
                # Simulate health check
                start_time = time.time()
                
                # This would be actual health check calls
                # For now, simulate with random success
                import random
                is_healthy = random.random() > 0.1  # 90% success rate
                
                response_time = time.time() - start_time
                
                health = self.service_health[service_name]
                health.last_check = datetime.utcnow()
                health.response_time = response_time
                
                if is_healthy:
                    health.status = 'healthy'
                    health.success_count += 1
                else:
                    health.status = 'unhealthy'
                    health.error_count += 1
                    health.last_error = "Health check failed"
                
            except Exception as e:
                self.logger.error(f"Health check error for {service_name}: {str(e)}")
                if service_name in self.service_health:
                    self.service_health[service_name].status = 'unhealthy'
                    self.service_health[service_name].last_error = str(e)
    
    async def _metrics_collection_loop(self):
        """Background task for metrics collection."""
        while True:
            try:
                await self._collect_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                self.logger.error(f"Metrics collection error: {str(e)}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self):
        """Collect and calculate metrics."""
        now = time.time()
        
        # Calculate requests per minute
        recent_requests = [
            req for req in self.active_requests.values()
            if now - req['start_time'] < 60
        ]
        self.metrics.requests_per_minute = len(recent_requests)
    
    async def _cleanup_loop(self):
        """Background task for cleanup operations."""
        while True:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(300)  # Clean every 5 minutes
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {str(e)}")
                await asyncio.sleep(30)
    
    async def _perform_cleanup(self):
        """Perform cleanup operations."""
        # Clean old rate limit records
        now = time.time()
        for service_name, rate_limiter in self.rate_limiters.items():
            rate_limiter['requests'] = [
                req_time for req_time in rate_limiter['requests']
                if now - req_time < self.config['rate_limit_window']
            ]
    
    async def get_gateway_status(self) -> Dict[str, Any]:
        """Get gateway status and metrics."""
        return {
            'gateway': {
                'status': 'running',
                'version': '1.0.0',
                'uptime': time.time(),  # Simplified uptime
                'active_connections': self.metrics.active_connections,
                'total_routes': sum(len(routes) for routes in self.routes.values())
            },
            'metrics': {
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': (
                    self.metrics.successful_requests / self.metrics.total_requests * 100
                    if self.metrics.total_requests > 0 else 0
                ),
                'avg_response_time': self.metrics.avg_response_time,
                'requests_per_minute': self.metrics.requests_per_minute,
                'cache_hit_rate': self.metrics.cache_hit_rate * 100,
                'rate_limited_requests': self.metrics.rate_limited_requests,
                'auth_failures': self.metrics.auth_failures
            },
            'services': {
                service_name: {
                    'status': health.status,
                    'response_time': health.response_time,
                    'error_count': health.error_count,
                    'success_count': health.success_count,
                    'last_check': health.last_check.isoformat(),
                    'circuit_breaker_open': health.circuit_breaker_open
                }
                for service_name, health in self.service_health.items()
            },
            'circuit_breakers': {
                service_name: {
                    'state': breaker['state'],
                    'failure_count': breaker['failure_count'],
                    'success_count': breaker['success_count']
                }
                for service_name, breaker in self.circuit_breakers.items()
            }
        }
    
    def register_service(self, service_name: str, service_instance: Any):
        """Register a service instance with the gateway."""
        self.service_registry[service_name] = {
            'instance': service_instance,
            'registered_at': datetime.utcnow(),
            'status': 'active'
        }
        self.logger.info(f"Registered service: {service_name}")
    
    def register_service_instances(self, service_name: str, service_instances: List[Any]):
        """Register multiple service instances for load balancing."""
        if service_name not in self.service_registry:
            self.service_registry[service_name] = {
                'instances': [],
                'current_index': 0,
                'registered_at': datetime.utcnow(),
                'status': 'active'
            }
        
        self.service_registry[service_name]['instances'].extend(service_instances)
        self.logger.info(f"Registered {len(service_instances)} instances for service: {service_name}")
    
    async def discover_services(self, services: List[Dict[str, Any]]):
        """Discover and register services from a list."""
        for service in services:
            service_name = service.get('name')
            service_url = service.get('url')
            
            if service_name and service_url:
                self.service_registry[service_name] = {
                    'url': service_url,
                    'registered_at': datetime.utcnow(),
                    'status': 'discovered'
                }
                self.logger.info(f"Discovered service: {service_name} at {service_url}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services."""
        health_status = {
            'gateway': {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            },
            'services': {}
        }
        
        for service_name, health in self.service_health.items():
            health_status['services'][service_name] = {
                'status': health.status,
                'last_check': health.last_check.isoformat(),
                'response_time': health.response_time,
                'error_count': health.error_count,
                'success_count': health.success_count,
                'circuit_breaker_open': health.circuit_breaker_open
            }
        
        return health_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics."""
        return {
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'avg_response_time': self.metrics.avg_response_time,
            'requests_per_minute': self.metrics.requests_per_minute,
            'active_connections': self.metrics.active_connections,
            'cache_hit_rate': self.metrics.cache_hit_rate,
            'rate_limited_requests': self.metrics.rate_limited_requests,
            'auth_failures': self.metrics.auth_failures
        }
    
    def get_or_create_circuit_breaker(self, service_name: str, threshold: int = 5, timeout: int = 60):
        """Get or create a circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                'state': 'closed',
                'failure_count': 0,
                'last_failure_time': None,
                'success_count': 0,
                'threshold': threshold,
                'timeout': timeout
            }
        
        # Create a circuit breaker object with state property
        class CircuitBreaker:
            def __init__(self, data):
                self.state = data['state']
                self.failure_count = data['failure_count']
                self.last_failure_time = data['last_failure_time']
                self.success_count = data['success_count']
                self.threshold = data['threshold']
                self.timeout = data['timeout']
                self._data = data
            
            def trip(self):
                self._data['state'] = 'open'
                self.state = 'open'
                self._data['failure_count'] += 1
                self.failure_count += 1
                self._data['last_failure_time'] = time.time()
                self.last_failure_time = time.time()
            
            def reset(self):
                self._data['state'] = 'closed'
                self.state = 'closed'
                self._data['failure_count'] = 0
                self.failure_count = 0
                self._data['success_count'] = 0
                self.success_count = 0
        
        return CircuitBreaker(self.circuit_breakers[service_name])
    
    async def route_request(self, request: Request) -> Response:
        """Route request to appropriate service (alias for process_request)."""
        return await self.process_request(request)


# Gateway middleware for FastAPI
class GatewayMiddleware(BaseHTTPMiddleware):
    """Gateway middleware for FastAPI applications."""
    
    def __init__(self, app: ASGIApp, gateway: APIGateway):
        super().__init__(app)
        self.gateway = gateway
    
    async def dispatch(self, request: Request, call_next):
        """Process request through gateway."""
        # Check if this is a gateway-managed route
        if self._should_process_through_gateway(request):
            return await self.gateway.process_request(request)
        else:
            # Pass through to normal FastAPI routing
            return await call_next(request)
    
    def _should_process_through_gateway(self, request: Request) -> bool:
        """Determine if request should be processed through gateway."""
        path = request.url.path
        
        # Gateway-managed paths
        gateway_paths = [
            '/api/v1/stocks/',
            '/api/v1/sentiment/',
            '/api/v1/unified/',
            '/api/v1/market/'
        ]
        
        return any(path.startswith(gateway_path) for gateway_path in gateway_paths)


# Global gateway instance
gateway_instance = None

def get_gateway() -> APIGateway:
    """Get global gateway instance."""
    global gateway_instance
    return gateway_instance

def initialize_gateway(cache_manager: UnifiedCacheManager) -> APIGateway:
    """Initialize global gateway instance."""
    global gateway_instance
    gateway_instance = APIGateway(cache_manager)
    return gateway_instance