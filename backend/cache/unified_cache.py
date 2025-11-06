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
    
    def _generate_query_hash(self, query: SearchQuery) -> str:
        """Generate hash for search query cache key."""
        query_str = f"{query.query}_{json.dumps(query.filters, sort_keys=True)}_{query.limit}_{query.offset}_{query.sort_by}_{query.sort_order}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _get_key(self, pattern: str, **kwargs) -> str:
        """Generate cache key from pattern and parameters."""
        return self.key_patterns[pattern].format(**kwargs)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if not self.backend:
                return None
            
            value = await self.backend.get(key)
            if value is not None:
                self.stats['hits'] += 1
                self.logger.debug(f"Cache hit: {key}")
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
        """Set value in cache with optional TTL."""
        try:
            if not self.backend:
                return False
            
            if ttl is None:
                ttl = self.ttl_settings.get('default', 300)
            
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
        """Delete key from cache."""
        try:
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