"""Rate limiting middleware."""

import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Requests per minute limit
            requests_per_hour: Requests per hour limit
            requests_per_day: Requests per day limit
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day

        # Store request timestamps per user/IP
        # Format: {identifier: [(timestamp, window_type), ...]}
        self.requests: Dict[str, list] = defaultdict(list)

    def _cleanup_old_requests(self, identifier: str, current_time: float):
        """Remove old request records outside time windows.

        Args:
            identifier: User/IP identifier
            current_time: Current timestamp
        """
        if identifier not in self.requests:
            return

        # Keep requests from last 24 hours
        cutoff_time = current_time - (24 * 3600)
        self.requests[identifier] = [
            (timestamp, window) for timestamp, window in self.requests[identifier]
            if timestamp > cutoff_time
        ]

    def is_allowed(
        self,
        identifier: str,
        current_time: Optional[float] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """Check if request is allowed under rate limits.

        Args:
            identifier: User/IP identifier
            current_time: Current timestamp (optional, uses time.time())

        Returns:
            Tuple of (allowed: bool, info: dict with limit info)
        """
        if current_time is None:
            current_time = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(identifier, current_time)

        # Calculate time windows
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400

        # Get requests in each window
        minute_requests = [
            ts for ts, _ in self.requests[identifier]
            if ts > minute_ago
        ]
        hour_requests = [
            ts for ts, _ in self.requests[identifier]
            if ts > hour_ago
        ]
        day_requests = [
            ts for ts, _ in self.requests[identifier]
            if ts > day_ago
        ]

        # Check limits
        minute_allowed = len(minute_requests) < self.requests_per_minute
        hour_allowed = len(hour_requests) < self.requests_per_hour
        day_allowed = len(day_requests) < self.requests_per_day

        allowed = minute_allowed and hour_allowed and day_allowed

        # Calculate reset times
        minute_reset = None
        hour_reset = None
        day_reset = None

        if minute_requests:
            minute_reset = datetime.fromtimestamp(
                min(minute_requests) + 60
            )
        if hour_requests:
            hour_reset = datetime.fromtimestamp(
                min(hour_requests) + 3600
            )
        if day_requests:
            day_reset = datetime.fromtimestamp(
                min(day_requests) + 86400
            )

        info = {
            "allowed": allowed,
            "minute": {
                "limit": self.requests_per_minute,
                "used": len(minute_requests),
                "remaining": max(0, self.requests_per_minute - len(minute_requests)),
                "reset": minute_reset
            },
            "hour": {
                "limit": self.requests_per_hour,
                "used": len(hour_requests),
                "remaining": max(0, self.requests_per_hour - len(hour_requests)),
                "reset": hour_reset
            },
            "day": {
                "limit": self.requests_per_day,
                "used": len(day_requests),
                "remaining": max(0, self.requests_per_day - len(day_requests)),
                "reset": day_reset
            }
        }

        return allowed, info

    def record_request(
        self,
        identifier: str,
        current_time: Optional[float] = None
    ):
        """Record a request for an identifier.

        Args:
            identifier: User/IP identifier
            current_time: Current timestamp (optional)
        """
        if current_time is None:
            current_time = time.time()

        self.requests[identifier].append((current_time, "request"))


class RateLimitMiddleware:
    """Rate limiting middleware."""

    def __init__(
        self,
        rate_limiter: RateLimiter,
        get_identifier_func=None
    ):
        """Initialize rate limit middleware.

        Args:
            rate_limiter: RateLimiter instance
            get_identifier_func: Function to extract identifier from request
        """
        self.rate_limiter = rate_limiter
        self.get_identifier_func = get_identifier_func or self._get_default_identifier

    def _get_default_identifier(self, request: Request) -> str:
        """Get default identifier from request (user or IP).

        Args:
            request: HTTP request

        Returns:
            Identifier string
        """
        # Try to get user from request state
        user = getattr(request.state, "user", None)
        if user:
            return f"user_{user}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip_{client_ip}"

    async def check_rate_limit(self, request: Request) -> Dict[str, any]:
        """Check rate limit for request.

        Args:
            request: HTTP request

        Returns:
            Rate limit info dict

        Raises:
            HTTPException: If rate limit exceeded
        """
        identifier = self.get_identifier_func(request)

        # Check if allowed
        allowed, info = self.rate_limiter.is_allowed(identifier)

        # Store info in request state
        request.state.rate_limit_info = info

        if not allowed:
            # Determine which limit was exceeded
            if info["minute"]["remaining"] == 0:
                limit_type = "minute"
            elif info["hour"]["remaining"] == 0:
                limit_type = "hour"
            else:
                limit_type = "day"

            logger.warning(
                f"Rate limit exceeded for {identifier} ({limit_type}): "
                f"used {info[limit_type]['used']}/{info[limit_type]['limit']}"
            )

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({limit_type}). "
                       f"Reset at {info[limit_type]['reset']}"
            )

        # Record the request
        self.rate_limiter.record_request(identifier)

        return info


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    requests_per_day: int = 10000
) -> RateLimiter:
    """Get global rate limiter instance.

    Args:
        requests_per_minute: Requests per minute
        requests_per_hour: Requests per hour
        requests_per_day: Requests per day

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day
        )
    return _rate_limiter


def get_rate_limit_middleware(
    rate_limiter: Optional[RateLimiter] = None
) -> RateLimitMiddleware:
    """Get rate limit middleware instance.

    Args:
        rate_limiter: Optional RateLimiter instance

    Returns:
        RateLimitMiddleware instance
    """
    if rate_limiter is None:
        rate_limiter = get_rate_limiter()

    return RateLimitMiddleware(rate_limiter)
