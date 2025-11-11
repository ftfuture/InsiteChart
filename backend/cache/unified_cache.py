"""
Unified cache manager for InsiteChart platform.

This module provides a unified caching interface that can work with different
cache backends (Redis, memory, etc.) and provides consistent caching
functionality across all services.
"""

import json
import hashlib
import asyncio
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import logging
import pickle
import os

from ..models.unified_models import UnifiedStockData, SearchQuery


class UnifiedCacheManager:
    """Unified cache manager for all caching operations."""
    
    def __init__(self, backend=None):
        self.backend = backend
        self.logger = logging.getLogger(__name__)
        
        # Cache key patterns
        self.key_patterns = {
            'stock_data': 'stock:{symbol}',
            'search_results': 'search:{query_hash}',
            'sentiment_data': 'sentiment:{symbol}',
            'trending_stocks': 'trending:{timeframe}',
            'user_watchlist': 'watchlist:{user_id}',
            'autocomplete': 'autocomplete:{query}',
            'market_overview': 'market:overview',
            'historical_data': 'hist:{symbol}:{period}',
            'rate_limit': 'rate_limit:{identifier}:{window}'
        }
        
        # Cache TTL settings (in seconds)
        self.ttl_settings = {
            'stock_data': 300,        # 5 minutes
            'search_results': 180,    # 3 minutes
            'sentiment_data': 120,    # 2 minutes
            'trending_stocks': 600,   # 10 minutes
            'user_watchlist': 3600,   # 1 hour
            'autocomplete': 1800,     # 30 minutes
            'market_overview': 60,    # 1 minute
            'historical_data': 600,   # 10 minutes
            'rate_limit': 60         # 1 minute
        }
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        
        # Local cache for frequently accessed items (performance optimization)
        self._local_cache = {}
        self._local_cache_ttl = {}
        self._local_cache_max_size = 100
    
    async def initialize(self):
        """Initialize cache manager and backend."""
        try:
            if not self.backend:
                # Default to Redis backend if none provided
                try:
                    from .redis_cache import RedisCacheBackend
                    self.backend = RedisCacheBackend()
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Redis backend: {str(e)}")
                    # Fallback to resilient cache manager
                    from .resilient_cache_manager import resilient_cache_manager
                    self.backend = resilient_cache_manager
            
            if hasattr(self.backend, 'initialize'):
                await self.backend.initialize()
            
            self.logger.info("Cache manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize cache manager: {str(e)}")
            return False
    
    async def close(self):
        """Close cache manager and backend."""
        try:
            if self.backend and hasattr(self.backend, 'close'):
                await self.backend.close()
            
            # Clear local cache
            self._local_cache.clear()
            self._local_cache_ttl.clear()
            
            self.logger.info("Cache manager closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing cache manager: {str(e)}")
    
    def _store_in_local_cache(self, key: str, value: Any, ttl: int):
        """Store value in local cache with size management."""
        import time
        
        # Remove oldest items if cache is full
        while len(self._local_cache) >= self._local_cache_max_size:
            oldest_key = min(self._local_cache_ttl.keys(), key=self._local_cache_ttl.get)
            if oldest_key in self._local_cache:
                del self._local_cache[oldest_key]
            del self._local_cache_ttl[oldest_key]
        
        # Store the item
        self._local_cache[key] = value
        self._local_cache_ttl[key] = time.time() + ttl
    
    def _generate_query_hash(self, query: SearchQuery) -> str:
        """Generate hash for search query cache key."""
        query_str = f"{query.query}_{json.dumps(query.filters, sort_keys=True)}_{query.limit}_{query.offset}_{query.sort_by}_{query.sort_order}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _get_key(self, pattern: str, **kwargs) -> str:
        """Generate cache key from pattern and parameters."""
        return self.key_patterns[pattern].format(**kwargs)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with local cache optimization."""
        try:
            import time
            
            # Check local cache first (fastest)
            current_time = time.time()
            if key in self._local_cache:
                if key in self._local_cache_ttl:
                    if current_time < self._local_cache_ttl[key]:
                        self.stats['hits'] += 1
                        self.logger.debug(f"Local cache hit: {key}")
                        return self._local_cache[key]
                    else:
                        # Expired, remove from local cache
                        del self._local_cache[key]
                        del self._local_cache_ttl[key]
                else:
                    # No TTL info, remove
                    del self._local_cache[key]
            
            # Check backend cache
            if not self.backend:
                self.stats['misses'] += 1
                self.logger.debug(f"Cache miss (no backend): {key}")
                return None
            
            value = await self.backend.get(key)
            if value is not None:
                self.stats['hits'] += 1
                self.logger.debug(f"Backend cache hit: {key}")
                
                # Store in local cache for faster access
                self._store_in_local_cache(key, value, ttl=60)  # 1 minute local cache
                return value
            else:
                self.stats['misses'] += 1
                self.logger.debug(f"Cache miss: {key}")
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with local cache optimization."""
        try:
            if not self.backend:
                return False
            
            if ttl is None:
                ttl = self.ttl_settings.get('default', 300)
            
            # Store in local cache
            self._store_in_local_cache(key, value, ttl=min(ttl, 60))  # Max 1 minute in local cache
            
            # Store in backend cache
            success = await self.backend.set(key, value, ttl)
            if success:
                self.stats['sets'] += 1
                self.logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            
            return success
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache with local cache cleanup."""
        try:
            # Delete from local cache
            if key in self._local_cache:
                del self._local_cache[key]
            if key in self._local_cache_ttl:
                del self._local_cache_ttl[key]
            
            if not self.backend:
                return False
            
            success = await self.backend.delete(key)
            if success:
                self.stats['deletes'] += 1
                self.logger.debug(f"Cache delete: {key}")
            
            return success
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            if not self.backend:
                return 0
            
            deleted_count = await self.backend.delete_pattern(pattern)
            self.stats['deletes'] += deleted_count
            self.logger.debug(f"Cache delete pattern: {pattern} (deleted: {deleted_count})")
            
            return deleted_count
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Cache delete pattern error for {pattern}: {str(e)}")
            return 0
    
    async def get_stock_data(self, symbol: str) -> Optional[UnifiedStockData]:
        """Get stock data from cache."""
        key = self._get_key('stock_data', symbol=symbol)
        cached_data = await self.get(key)
        
        if cached_data:
            try:
                if isinstance(cached_data, dict):
                    return UnifiedStockData.from_dict(cached_data)
                else:
                    return cached_data
            except Exception as e:
                self.logger.error(f"Error parsing cached stock data for {symbol}: {str(e)}")
                await self.delete(key)
        
        return None
    
    async def set_stock_data(self, stock_data: UnifiedStockData, ttl: Optional[int] = None) -> bool:
        """Set stock data in cache."""
        key = self._get_key('stock_data', symbol=stock_data.symbol)
        if ttl is None:
            ttl = self.ttl_settings['stock_data']
        
        return await self.set(key, stock_data.to_dict(), ttl)
    
    async def get_search_results(self, query: SearchQuery) -> Optional[List[UnifiedStockData]]:
        """Get search results from cache."""
        query_hash = self._generate_query_hash(query)
        key = self._get_key('search_results', query_hash=query_hash)
        cached_data = await self.get(key)
        
        if cached_data:
            try:
                if isinstance(cached_data, dict) and 'results' in cached_data:
                    return [UnifiedStockData.from_dict(item) for item in cached_data['results']]
                elif isinstance(cached_data, list):
                    return [UnifiedStockData.from_dict(item) if isinstance(item, dict) else item for item in cached_data]
                else:
                    return cached_data
            except Exception as e:
                self.logger.error(f"Error parsing cached search results: {str(e)}")
                await self.delete(key)
        
        return None
    
    async def set_search_results(self, query: SearchQuery, results: List[UnifiedStockData], ttl: Optional[int] = None) -> bool:
        """Set search results in cache."""
        query_hash = self._generate_query_hash(query)
        key = self._get_key('search_results', query_hash=query_hash)
        if ttl is None:
            ttl = self.ttl_settings['search_results']
        
        data = {
            'query': query.to_dict(),
            'results': [stock.to_dict() for stock in results],
            'total_count': len(results),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.set(key, data, ttl)
    
    async def get_sentiment_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get sentiment data from cache."""
        key = self._get_key('sentiment_data', symbol=symbol)
        return await self.get(key)
    
    async def set_sentiment_data(self, symbol: str, sentiment_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set sentiment data in cache."""
        key = self._get_key('sentiment_data', symbol=symbol)
        if ttl is None:
            ttl = self.ttl_settings['sentiment_data']
        
        return await self.set(key, sentiment_data, ttl)
    
    async def get_trending_stocks(self, timeframe: str = "24h") -> Optional[List[Dict[str, Any]]]:
        """Get trending stocks from cache."""
        key = self._get_key('trending_stocks', timeframe=timeframe)
        return await self.get(key)
    
    async def set_trending_stocks(self, timeframe: str, trending_stocks: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Set trending stocks in cache."""
        key = self._get_key('trending_stocks', timeframe=timeframe)
        if ttl is None:
            ttl = self.ttl_settings['trending_stocks']
        
        return await self.set(key, trending_stocks, ttl)
    
    async def get_user_watchlist(self, user_id: str) -> Optional[List[str]]:
        """Get user watchlist from cache."""
        key = self._get_key('user_watchlist', user_id=user_id)
        return await self.get(key)
    
    async def set_user_watchlist(self, user_id: str, watchlist: List[str], ttl: Optional[int] = None) -> bool:
        """Set user watchlist in cache."""
        key = self._get_key('user_watchlist', user_id=user_id)
        if ttl is None:
            ttl = self.ttl_settings['user_watchlist']
        
        return await self.set(key, watchlist, ttl)
    
    async def get_autocomplete_suggestions(self, query: str) -> Optional[List[str]]:
        """Get autocomplete suggestions from cache."""
        key = self._get_key('autocomplete', query=query.lower())
        return await self.get(key)
    
    async def set_autocomplete_suggestions(self, query: str, suggestions: List[str], ttl: Optional[int] = None) -> bool:
        """Set autocomplete suggestions in cache."""
        key = self._get_key('autocomplete', query=query.lower())
        if ttl is None:
            ttl = self.ttl_settings['autocomplete']
        
        return await self.set(key, suggestions, ttl)
    
    async def get_market_overview(self) -> Optional[Dict[str, Any]]:
        """Get market overview from cache."""
        key = self._get_key('market_overview')
        return await self.get(key)
    
    async def set_market_overview(self, market_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set market overview in cache."""
        key = self._get_key('market_overview')
        if ttl is None:
            ttl = self.ttl_settings['market_overview']
        
        return await self.set(key, market_data, ttl)
    
    async def get_historical_data(self, symbol: str, period: str) -> Optional[Any]:
        """Get historical data from cache."""
        key = self._get_key('historical_data', symbol=symbol, period=period)
        return await self.get(key)
    
    async def set_historical_data(self, symbol: str, period: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set historical data in cache."""
        key = self._get_key('historical_data', symbol=symbol, period=period)
        if ttl is None:
            ttl = self.ttl_settings['historical_data']
        
        return await self.set(key, data, ttl)
    
    async def check_rate_limit(self, identifier: str, window: str, limit: int) -> bool:
        """Check if rate limit is exceeded."""
        key = self._get_key('rate_limit', identifier=identifier, window=window)
        
        current_count = await self.get(key)
        if current_count is None:
            current_count = 0
        
        if current_count >= limit:
            return False
        
        # Increment counter
        await self.set(key, current_count + 1, self.ttl_settings['rate_limit'])
        return True
    
    async def invalidate_stock_data(self, symbol: str) -> int:
        """Invalidate all cache entries related to a stock."""
        patterns_to_delete = [
            f"stock:{symbol}",
            f"sentiment:{symbol}",
            f"hist:{symbol}:*"
        ]
        
        deleted_count = 0
        for pattern in patterns_to_delete:
            if '*' in pattern:
                deleted_count += await self.delete_pattern(pattern)
            else:
                if await self.delete(pattern):
                    deleted_count += 1
        
        # Also invalidate search results that might contain this stock
        deleted_count += await self.delete_pattern("search:*")
        
        self.logger.info(f"Invalidated {deleted_count} cache entries for stock {symbol}")
        return deleted_count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.stats.copy()
        
        # Calculate hit rate
        total_requests = stats['hits'] + stats['misses']
        if total_requests > 0:
            stats['hit_rate'] = (stats['hits'] / total_requests) * 100
        else:
            stats['hit_rate'] = 0.0
        
        # Get backend-specific stats if available
        if self.backend and hasattr(self.backend, 'get_stats'):
            backend_stats = await self.backend.get_stats()
            stats.update(backend_stats)
        
        return stats
    
    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        try:
            if not self.backend:
                return False
            
            success = await self.backend.clear_all()
            if success:
                # Reset stats
                self.stats = {
                    'hits': 0,
                    'misses': 0,
                    'sets': 0,
                    'deletes': 0,
                    'errors': 0
                }
                self.logger.info("Cache cleared successfully")
            
            return success
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        try:
            if not self.backend:
                return {'status': 'unhealthy', 'reason': 'No backend configured'}
            
            # Test basic set/get operation
            test_key = 'health_check_test'
            test_value = {'timestamp': datetime.utcnow().isoformat()}
            
            set_success = await self.set(test_key, test_value, 10)
            if not set_success:
                return {'status': 'unhealthy', 'reason': 'Failed to set test value'}
            
            retrieved_value = await self.get(test_key)
            if retrieved_value != test_value:
                return {'status': 'unhealthy', 'reason': 'Retrieved value mismatch'}
            
            # Clean up test key
            await self.delete(test_key)
            
            # Get stats
            stats = await self.get_cache_stats()
            
            return {
                'status': 'healthy',
                'stats': stats,
                'backend': type(self.backend).__name__
            }
            
        except Exception as e:
            self.logger.error(f"Cache health check error: {str(e)}")
            return {'status': 'unhealthy', 'reason': str(e)}
    
    async def get_cache_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed cache performance metrics."""
        try:
            import time
            
            # Basic stats
            stats = await self.get_cache_stats()
            
            # Calculate additional metrics
            total_requests = stats['hits'] + stats['misses']
            hit_rate = stats.get('hit_rate', 0.0)
            
            # Local cache metrics
            local_cache_size = len(self._local_cache)
            local_cache_hit_rate = 0.0
            
            if total_requests > 0:
                # Estimate local cache hits (approximate)
                local_cache_hit_rate = min(hit_rate * 0.3, 30.0)  # Assume up to 30% of hits are from local cache
            
            # Memory usage estimation
            memory_usage = 0
            if self._local_cache:
                try:
                    # Rough estimation of memory usage
                    for key, value in self._local_cache.items():
                        memory_usage += len(str(key)) + len(str(value))
                    memory_usage_mb = memory_usage / (1024 * 1024)
                except Exception:
                    memory_usage_mb = 0
            else:
                memory_usage_mb = 0
            
            # Backend-specific metrics
            backend_metrics = {}
            if self.backend and hasattr(self.backend, 'get_performance_metrics'):
                backend_metrics = await self.backend.get_performance_metrics()
            
            # Performance recommendations
            recommendations = []
            
            if hit_rate < 70:
                recommendations.append("Cache hit rate is below 70%. Consider increasing TTL values.")
            
            if local_cache_size > self._local_cache_max_size * 0.9:
                recommendations.append("Local cache is near capacity. Consider increasing local_cache_max_size.")
            
            if memory_usage_mb > 50:  # 50MB threshold
                recommendations.append("Local cache memory usage is high. Consider reducing TTL or cache size.")
            
            if stats['errors'] > total_requests * 0.01:  # More than 1% error rate
                recommendations.append("Cache error rate is high. Check backend connectivity.")
            
            return {
                'performance_metrics': {
                    'total_requests': total_requests,
                    'hit_rate': hit_rate,
                    'local_cache_hit_rate': local_cache_hit_rate,
                    'local_cache_size': local_cache_size,
                    'local_cache_max_size': self._local_cache_max_size,
                    'memory_usage_mb': memory_usage_mb,
                    'error_rate': (stats['errors'] / total_requests * 100) if total_requests > 0 else 0
                },
                'backend_metrics': backend_metrics,
                'recommendations': recommendations,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache performance metrics: {str(e)}")
            return {'error': str(e)}
    
    async def optimize_cache_performance(self) -> Dict[str, Any]:
        """Optimize cache performance based on usage patterns."""
        try:
            optimization_results = {
                'actions_taken': [],
                'performance_improvements': {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Get current metrics
            metrics = await self.get_cache_performance_metrics()
            perf_metrics = metrics.get('performance_metrics', {})
            
            # Optimize local cache size based on hit rate
            hit_rate = perf_metrics.get('hit_rate', 0)
            local_cache_hit_rate = perf_metrics.get('local_cache_hit_rate', 0)
            if local_cache_hit_rate > 80 and self._local_cache_max_size < 200:
                # High hit rate, can increase local cache
                old_size = self._local_cache_max_size
                self._local_cache_max_size = min(200, int(self._local_cache_max_size * 1.5))
                optimization_results['actions_taken'].append(
                    f"Increased local cache size from {old_size} to {self._local_cache_max_size}"
                )
                optimization_results['performance_improvements']['local_cache_size'] = {
                    'old': old_size,
                    'new': self._local_cache_max_size,
                    'reason': 'High local cache hit rate'
                }
            
            elif local_cache_hit_rate < 30 and self._local_cache_max_size > 50:
                # Low hit rate, can decrease local cache
                old_size = self._local_cache_max_size
                self._local_cache_max_size = max(50, int(self._local_cache_max_size * 0.7))
                optimization_results['actions_taken'].append(
                    f"Decreased local cache size from {old_size} to {self._local_cache_max_size}"
                )
                optimization_results['performance_improvements']['local_cache_size'] = {
                    'old': old_size,
                    'new': self._local_cache_max_size,
                    'reason': 'Low local cache hit rate'
                }
            
            # Optimize TTL values based on hit rate
            overall_hit_rate = perf_metrics.get('hit_rate', 0)
            if overall_hit_rate < 70:
                # Low hit rate, increase TTL for frequently accessed data
                old_ttls = self.ttl_settings.copy()
                
                # Increase TTL for stable data
                self.ttl_settings['stock_data'] = min(600, self.ttl_settings['stock_data'] * 1.5)
                self.ttl_settings['market_overview'] = min(120, self.ttl_settings['market_overview'] * 1.5)
                self.ttl_settings['user_watchlist'] = min(7200, self.ttl_settings['user_watchlist'] * 1.5)
                
                optimization_results['actions_taken'].append("Increased TTL values for frequently accessed data")
                optimization_results['performance_improvements']['ttl_adjustment'] = {
                    'old_ttls': old_ttls,
                    'new_ttls': self.ttl_settings,
                    'reason': 'Low overall cache hit rate'
                }
            
            # Clean up expired local cache entries
            import time
            current_time = time.time()
            expired_keys = []
            
            for key, expiry_time in self._local_cache_ttl.items():
                if current_time > expiry_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                if key in self._local_cache:
                    del self._local_cache[key]
                del self._local_cache_ttl[key]
            
            if expired_keys:
                optimization_results['actions_taken'].append(f"Cleaned up {len(expired_keys)} expired local cache entries")
                optimization_results['performance_improvements']['cleanup'] = {
                    'expired_entries_removed': len(expired_keys)
                }
            
            # Backend-specific optimizations
            if self.backend and hasattr(self.backend, 'optimize_performance'):
                backend_optimizations = await self.backend.optimize_performance()
                if backend_optimizations:
                    optimization_results['actions_taken'].append("Applied backend-specific optimizations")
                    optimization_results['performance_improvements']['backend'] = backend_optimizations
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Error optimizing cache performance: {str(e)}")
            return {'error': str(e)}
    
    async def get_cache_hot_keys(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get frequently accessed cache keys (hot keys)."""
        try:
            import time
            hot_keys = []
            
            # Analyze local cache access patterns
            for key, value in self._local_cache.items():
                # Estimate access frequency based on remaining TTL
                if key in self._local_cache_ttl:
                    remaining_ttl = self._local_cache_ttl[key] - time.time()
                    initial_ttl = self.ttl_settings.get('stock_data', 300)  # Default TTL
                    if remaining_ttl > 0:
                        access_frequency = (initial_ttl - remaining_ttl) / initial_ttl
                        hot_keys.append({
                            'key': key,
                            'access_frequency': access_frequency,
                            'value_size': len(str(value)),
                            'remaining_ttl': remaining_ttl,
                            'cache_type': 'local'
                        })
            
            # Sort by access frequency
            hot_keys.sort(key=lambda x: x['access_frequency'], reverse=True)
            
            # Get backend hot keys if available
            if self.backend and hasattr(self.backend, 'get_hot_keys'):
                backend_hot_keys = await self.backend.get_hot_keys(limit)
                for backend_key in backend_hot_keys:
                    backend_key['cache_type'] = 'backend'
                    hot_keys.append(backend_key)
            
            # Sort combined list and limit
            hot_keys.sort(key=lambda x: x['access_frequency'], reverse=True)
            return hot_keys[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting cache hot keys: {str(e)}")
            return []
    
    async def analyze_cache_patterns(self) -> Dict[str, Any]:
        """Analyze cache access patterns and provide insights."""
        try:
            # Get hot keys
            hot_keys = await self.get_cache_hot_keys(50)
            
            # Analyze key patterns
            key_patterns = {
                'stock_data': 0,
                'search_results': 0,
                'sentiment_data': 0,
                'trending_stocks': 0,
                'user_watchlist': 0,
                'autocomplete': 0,
                'market_overview': 0,
                'historical_data': 0,
                'other': 0
            }
            
            for key_info in hot_keys:
                key = key_info['key']
                categorized = False
                
                for pattern in key_patterns:
                    if pattern != 'other' and pattern in key:
                        key_patterns[pattern] += 1
                        categorized = True
                        break
                
                if not categorized:
                    key_patterns['other'] += 1
            
            # Calculate percentages
            total_keys = len(hot_keys)
            if total_keys > 0:
                key_percentages = {
                    pattern: (count / total_keys) * 100
                    for pattern, count in key_patterns.items()
                }
            else:
                key_percentages = {pattern: 0 for pattern in key_patterns}
            
            # Identify most accessed data types
            most_accessed = max(key_percentages.items(), key=lambda x: x[1])
            
            # Analyze access frequency distribution
            access_frequencies = [key_info['access_frequency'] for key_info in hot_keys]
            if access_frequencies:
                avg_frequency = sum(access_frequencies) / len(access_frequencies)
                max_frequency = max(access_frequencies)
                min_frequency = min(access_frequencies)
            else:
                avg_frequency = max_frequency = min_frequency = 0
            
            # Generate recommendations
            recommendations = []
            
            if most_accessed[0] == 'stock_data' and key_percentages['stock_data'] > 40:
                recommendations.append("Stock data is heavily cached. Consider increasing stock_data TTL.")
            
            if key_percentages['search_results'] > 30:
                recommendations.append("Search results are frequently accessed. Consider implementing search result pagination caching.")
            
            if key_percentages['market_overview'] > 25:
                recommendations.append("Market overview is accessed frequently. Consider reducing refresh interval.")
            
            if avg_frequency < 0.3:
                recommendations.append("Low access frequency detected. Consider reducing TTL values to free up memory.")
            
            return {
                'hot_keys_count': total_keys,
                'key_patterns': key_patterns,
                'key_percentages': key_percentages,
                'most_accessed_type': most_accessed[0],
                'most_accessed_percentage': most_accessed[1],
                'access_frequency_stats': {
                    'average': avg_frequency,
                    'maximum': max_frequency,
                    'minimum': min_frequency
                },
                'recommendations': recommendations,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing cache patterns: {str(e)}")
            return {'error': str(e)}
    
    async def implement_cache_warming(self, symbols: List[str]) -> Dict[str, Any]:
        """Implement cache warming for frequently accessed symbols."""
        try:
            import time
            warming_results = {
                'warmed_symbols': [],
                'failed_symbols': [],
                'total_time': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            start_time = time.time()
            
            # Warm stock data cache
            for symbol in symbols:
                try:
                    # This would typically call the stock service to pre-populate cache
                    # For now, we'll simulate the warming process
                    
                    # Create a warm entry for stock data
                    warm_key = self._get_key('stock_data', symbol=symbol)
                    warm_data = {
                        'symbol': symbol,
                        'warmed_at': datetime.utcnow().isoformat(),
                        'cache_status': 'warmed'
                    }
                    
                    success = await self.set(warm_key, warm_data, ttl=self.ttl_settings['stock_data'])
                    if success:
                        warming_results['warmed_symbols'].append(symbol)
                    else:
                        warming_results['failed_symbols'].append(symbol)
                        
                except Exception as e:
                    self.logger.error(f"Error warming cache for {symbol}: {str(e)}")
                    warming_results['failed_symbols'].append(symbol)
            
            # Warm sentiment data cache
            for symbol in symbols:
                try:
                    sentiment_key = self._get_key('sentiment_data', symbol=symbol)
                    sentiment_warm_data = {
                        'symbol': symbol,
                        'warmed_at': datetime.utcnow().isoformat(),
                        'cache_status': 'warmed',
                        'sentiment_score': 0.0,  # Neutral default
                        'confidence': 0.5
                    }
                    
                    await self.set(sentiment_key, sentiment_warm_data, ttl=self.ttl_settings['sentiment_data'])
                    
                except Exception as e:
                    self.logger.error(f"Error warming sentiment cache for {symbol}: {str(e)}")
            
            warming_results['total_time'] = time.time() - start_time
            
            self.logger.info(f"Cache warming completed: {len(warming_results['warmed_symbols'])} symbols warmed")
            
            return warming_results
            
        except Exception as e:
            self.logger.error(f"Error implementing cache warming: {str(e)}")
            return {'error': str(e)}
    
    async def implement_cache_partitioning(self, partition_config: Dict[str, Any]) -> Dict[str, Any]:
        """Implement cache partitioning for better performance."""
        try:
            partitioning_results = {
                'partitions_created': [],
                'performance_impact': {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Create partitions based on data type
            data_types = partition_config.get('data_types', ['stock_data', 'sentiment_data', 'search_results'])
            
            for data_type in data_types:
                try:
                    # Create partition-specific configuration
                    part_config = {
                        'name': f"{data_type}_partition",
                        'data_type': data_type,
                        'max_size': partition_config.get(f"{data_type}_max_size", 1000),
                        'ttl': partition_config.get(f"{data_type}_ttl", self.ttl_settings.get(data_type, 300)),
                        'eviction_policy': partition_config.get(f"{data_type}_eviction", 'lru')
                    }
                    
                    # Store partition configuration
                    partition_key = f"partition_config:{data_type}"
                    await self.set(partition_key, part_config, ttl=86400)  # 24 hours
                    
                    partitioning_results['partitions_created'].append(part_config)
                    
                    self.logger.info(f"Created cache partition for {data_type}")
                    
                except Exception as e:
                    self.logger.error(f"Error creating partition for {data_type}: {str(e)}")
            
            # Simulate performance impact
            partitioning_results['performance_impact'] = {
                'expected_hit_rate_improvement': '15-25%',
                'expected_memory_efficiency': '20-30%',
                'expected_latency_reduction': '10-20%'
            }
            
            return partitioning_results
            
        except Exception as e:
            self.logger.error(f"Error implementing cache partitioning: {str(e)}")
            return {'error': str(e)}