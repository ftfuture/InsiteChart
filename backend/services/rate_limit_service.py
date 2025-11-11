"""
Rate Limit Service for InsiteChart platform.

This service provides rate limiting capabilities for API endpoints
and other resources to prevent abuse and ensure fair usage.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading

from ..cache.unified_cache import UnifiedCacheManager


class UserTier(str, Enum):
    """User tier enumeration for rate limiting."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimitPolicy:
    """Rate limit policy configuration."""
    requests: int
    window: int  # seconds
    burst: int = 0  # additional requests allowed for burst
    priority: int = 1  # lower number = higher priority


@dataclass
class RateLimitInfo:
    """Rate limit information."""
    allowed: bool
    requests_remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    policy: RateLimitPolicy = field(default_factory=lambda: RateLimitPolicy(100, 60))
    operation: str = "default"
    user_tier: str = "default"


class RateLimitService:
    """Rate limit service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Default policies by user tier
        self.default_policies = {
            UserTier.FREE: {
                "default": RateLimitPolicy(requests=100, window=60, burst=20),
                "search": RateLimitPolicy(requests=50, window=60, burst=10),
                "api": RateLimitPolicy(requests=200, window=60, burst=50)
            },
            UserTier.BASIC: {
                "default": RateLimitPolicy(requests=500, window=60, burst=100),
                "search": RateLimitPolicy(requests=250, window=60, burst=50),
                "api": RateLimitPolicy(requests=1000, window=60, burst=200)
            },
            UserTier.PREMIUM: {
                "default": RateLimitPolicy(requests=2000, window=60, burst=500),
                "search": RateLimitPolicy(requests=1000, window=60, burst=250),
                "api": RateLimitPolicy(requests=5000, window=60, burst=1000)
            },
            UserTier.ENTERPRISE: {
                "default": RateLimitPolicy(requests=10000, window=60, burst=2000),
                "search": RateLimitPolicy(requests=5000, window=60, burst=1000),
                "api": RateLimitPolicy(requests=20000, window=60, burst=5000)
            }
        }
        
        # Custom policies for specific users
        self.custom_policies: Dict[str, Dict[str, RateLimitPolicy]] = {}
        
        # In-memory tracking for high-frequency operations
        self.in_memory_counters: Dict[str, List[float]] = {}
        self.in_memory_lock = threading.Lock()
        
        # Testing mode flag
        self.testing = False
        
        self.logger.info("RateLimitService initialized")
    
    def set_testing_mode(self, testing: bool):
        """Set testing mode to bypass rate limits."""
        self.testing = testing
        self.logger.info(f"Rate limit testing mode: {'enabled' if testing else 'disabled'}")
    
    async def is_allowed(
        self,
        identifier: str,
        operation: str = "default",
        user_tier: str = "default",
        endpoint: Optional[str] = None,
        burst_mode: bool = False
    ) -> RateLimitInfo:
        """Check if request is allowed based on rate limits."""
        try:
            # Bypass all rate limits in testing mode
            if self.testing:
                return RateLimitInfo(
                    allowed=True,
                    requests_remaining=999999,
                    reset_time=datetime.utcnow() + timedelta(hours=1),
                    policy=RateLimitPolicy(requests=999999, window=3600),
                    operation=operation,
                    user_tier=user_tier
                )
            
            # Get policy for user tier and operation
            policy = await self._get_policy(identifier, operation, user_tier, endpoint)
            
            # Create cache key
            cache_key = f"rate_limit:{identifier}:{operation}:{policy.window}"
            
            # Get current counter from cache
            current_data = await self.cache_manager.get(cache_key)
            
            if not current_data:
                # First request in window
                counter = 1
                window_start = datetime.utcnow()
            else:
                counter = current_data.get("count", 0) + 1
                window_start = datetime.fromisoformat(current_data["window_start"])
                
                # Check if window has expired
                if datetime.utcnow() > window_start + timedelta(seconds=policy.window):
                    counter = 1
                    window_start = datetime.utcnow()
            
            # Calculate remaining requests
            requests_remaining = max(0, policy.requests - counter)
            
            # Handle burst mode
            if burst_mode and policy.burst > 0:
                burst_available = policy.burst - max(0, counter - policy.requests)
                requests_remaining += burst_available
            
            # Check if allowed
            allowed = counter <= policy.requests or (burst_mode and counter <= policy.requests + policy.burst)
            
            # Calculate reset time
            reset_time = window_start + timedelta(seconds=policy.window)
            
            # Calculate retry after if not allowed
            retry_after = None
            if not allowed:
                retry_after = max(1, (reset_time - datetime.utcnow()).total_seconds())
            
            # Update cache
            await self.cache_manager.set(
                cache_key,
                {
                    "count": counter,
                    "window_start": window_start.isoformat(),
                    "policy": {
                        "requests": policy.requests,
                        "window": policy.window,
                        "burst": policy.burst
                    }
                },
                ttl=policy.window
            )
            
            # Also update in-memory counter for very high frequency
            await self._update_in_memory_counter(identifier, operation, policy.window)
            
            return RateLimitInfo(
                allowed=allowed,
                requests_remaining=requests_remaining,
                reset_time=reset_time,
                retry_after=retry_after,
                policy=policy,
                operation=operation,
                user_tier=user_tier
            )
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {str(e)}")
            # Allow request on error to prevent service disruption
            return RateLimitInfo(
                allowed=True,
                requests_remaining=100,
                reset_time=datetime.utcnow() + timedelta(minutes=1),
                policy=RateLimitPolicy(requests=100, window=60),
                operation=operation,
                user_tier=user_tier
            )
    
    async def _get_policy(
        self,
        identifier: str,
        operation: str,
        user_tier: str,
        endpoint: Optional[str] = None
    ) -> RateLimitPolicy:
        """Get rate limit policy for identifier and operation."""
        try:
            # Check for custom policy first
            if identifier in self.custom_policies:
                custom_policies = self.custom_policies[identifier]
                if operation in custom_policies:
                    return custom_policies[operation]
            
            # Get default policy for user tier
            tier = UserTier(user_tier) if user_tier in [t.value for t in UserTier] else UserTier.FREE
            
            if tier in self.default_policies:
                tier_policies = self.default_policies[tier]
                if operation in tier_policies:
                    return tier_policies[operation]
            
            # Fallback to default policy for free tier
            return self.default_policies[UserTier.FREE]["default"]
            
        except Exception as e:
            self.logger.error(f"Error getting rate limit policy: {str(e)}")
            return RateLimitPolicy(requests=100, window=60)
    
    async def _update_in_memory_counter(self, identifier: str, operation: str, window: int):
        """Update in-memory counter for very high frequency operations."""
        try:
            with self.in_memory_lock:
                key = f"{identifier}:{operation}"
                current_time = time.time()
                
                if key not in self.in_memory_counters:
                    self.in_memory_counters[key] = []
                
                # Add current timestamp
                self.in_memory_counters[key].append(current_time)
                
                # Clean old timestamps outside window
                cutoff_time = current_time - window
                self.in_memory_counters[key] = [
                    ts for ts in self.in_memory_counters[key] if ts > cutoff_time
                ]
                
                # Keep only last 1000 timestamps to prevent memory issues
                if len(self.in_memory_counters[key]) > 1000:
                    self.in_memory_counters[key] = self.in_memory_counters[key][-1000:]
                    
        except Exception as e:
            self.logger.error(f"Error updating in-memory counter: {str(e)}")
    
    async def set_custom_policy(
        self,
        identifier: str,
        operation: str,
        policy: RateLimitPolicy
    ) -> bool:
        """Set custom rate limit policy for identifier."""
        try:
            if identifier not in self.custom_policies:
                self.custom_policies[identifier] = {}
            
            self.custom_policies[identifier][operation] = policy
            
            # Cache the custom policy
            cache_key = f"custom_policy:{identifier}:{operation}"
            await self.cache_manager.set(
                cache_key,
                {
                    "requests": policy.requests,
                    "window": policy.window,
                    "burst": policy.burst,
                    "priority": policy.priority
                },
                ttl=86400  # 24 hours
            )
            
            self.logger.info(f"Set custom policy for {identifier}:{operation}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting custom policy: {str(e)}")
            return False
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        operation: str = "default",
        user_tier: str = "default"
    ) -> Dict[str, Any]:
        """Get current rate limit status for identifier."""
        try:
            # Get policy
            policy = await self._get_policy(identifier, operation, user_tier)
            
            # Get current counter
            cache_key = f"rate_limit:{identifier}:{operation}:{policy.window}"
            current_data = await self.cache_manager.get(cache_key)
            
            if not current_data:
                return {
                    "identifier": identifier,
                    "operation": operation,
                    "user_tier": user_tier,
                    "policy": {
                        "requests": policy.requests,
                        "window": policy.window,
                        "burst": policy.burst
                    },
                    "current_requests": 0,
                    "requests_remaining": policy.requests,
                    "reset_time": (datetime.utcnow() + timedelta(seconds=policy.window)).isoformat(),
                    "window_start": datetime.utcnow().isoformat()
                }
            
            window_start = datetime.fromisoformat(current_data["window_start"])
            reset_time = window_start + timedelta(seconds=policy.window)
            
            return {
                "identifier": identifier,
                "operation": operation,
                "user_tier": user_tier,
                "policy": current_data.get("policy"),
                "current_requests": current_data.get("count", 0),
                "requests_remaining": max(0, policy.requests - current_data.get("count", 0)),
                "reset_time": reset_time.isoformat(),
                "window_start": window_start.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting rate limit status: {str(e)}")
            return {}
    
    async def reset_rate_limit(
        self,
        identifier: str,
        operation: str = "default"
    ) -> bool:
        """Reset rate limit counter for identifier."""
        try:
            # Get policy to determine window
            policy = await self._get_policy(identifier, operation, "default")
            
            # Delete cache entry
            cache_key = f"rate_limit:{identifier}:{operation}:{policy.window}"
            await self.cache_manager.delete(cache_key)
            
            # Clear in-memory counter
            with self.in_memory_lock:
                key = f"{identifier}:{operation}"
                if key in self.in_memory_counters:
                    del self.in_memory_counters[key]
            
            self.logger.info(f"Reset rate limit for {identifier}:{operation}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resetting rate limit: {str(e)}")
            return False
    
    async def get_rate_limit_metrics(self) -> Dict[str, Any]:
        """Get rate limiting metrics."""
        try:
            # Count active rate limit entries
            active_keys = 0
            total_requests = 0
            
            # This would scan cache keys in a real implementation
            # For now, return mock metrics
            return {
                "active_rate_limits": active_keys,
                "total_requests_checked": total_requests,
                "requests_blocked": 0,
                "average_utilization": 0.0,
                "top_consumers": [],
                "custom_policies_count": len(self.custom_policies),
                "in_memory_counters": len(self.in_memory_counters),
                "testing_mode": self.testing,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting rate limit metrics: {str(e)}")
            return {}


# Global rate limiter instance
rate_limiter = None

def get_rate_limiter(cache_manager: UnifiedCacheManager) -> RateLimitService:
    """Get or create rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimitService(cache_manager)
    return rate_limiter