"""
In-memory cache backend for InsiteChart platform.

This module provides a simple in-memory cache implementation for development
and testing purposes, or for small-scale deployments.
"""

import asyncio
import time
from typing import Any, Optional, Dict, List
import logging
import threading
from datetime import datetime, timedelta


class MemoryCacheBackend:
    """In-memory cache backend implementation."""
    
    def __init__(self, max_size: int = 1000, cleanup_interval: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'size': 0
        }
        
        # Start cleanup task
        self._cleanup_task = None
        self._running = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check if expired
                if entry['expires_at'] and datetime.utcnow() > entry['expires_at']:
                    del self.cache[key]
                    self.stats['misses'] += 1
                    self.stats['size'] = len(self.cache)
                    return None
                
                # Update access time
                entry['last_accessed'] = datetime.utcnow()
                self.stats['hits'] += 1
                
                return entry['value']
            else:
                self.stats['misses'] += 1
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        with self._lock:
            # Calculate expiration time
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            # Check if eviction is needed
            if key not in self.cache and len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Set value
            self.cache[key] = {
                'value': value,
                'created_at': datetime.utcnow(),
                'last_accessed': datetime.utcnow(),
                'expires_at': expires_at,
                'ttl': ttl
            }
            
            self.stats['sets'] += 1
            self.stats['size'] = len(self.cache)
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['deletes'] += 1
                self.stats['size'] = len(self.cache)
                return True
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        import fnmatch
        
        with self._lock:
            keys_to_delete = []
            for key in self.cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.cache[key]
            
            deleted_count = len(keys_to_delete)
            self.stats['deletes'] += deleted_count
            self.stats['size'] = len(self.cache)
            
            return deleted_count
    
    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.stats['size'] = 0
            return True
    
    def _evict_lru(self):
        """Evict least recently used entries."""
        if not self.cache:
            return
        
        # Find LRU entry
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k]['last_accessed'])
        del self.cache[lru_key]
        self.stats['evictions'] += 1
        self.logger.debug(f"Evicted LRU key: {lru_key}")
    
    async def cleanup_expired(self):
        """Clean up expired entries."""
        with self._lock:
            now = datetime.utcnow()
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry['expires_at'] and now > entry['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                self.stats['size'] = len(self.cache)
                self.logger.debug(f"Cleaned up {len(expired_keys)} expired keys")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            stats = self.stats.copy()
            
            # Calculate hit rate
            total_requests = stats['hits'] + stats['misses']
            if total_requests > 0:
                stats['hit_rate'] = (stats['hits'] / total_requests) * 100
            else:
                stats['hit_rate'] = 0.0
            
            # Memory usage estimation
            stats['max_size'] = self.max_size
            stats['utilization'] = (stats['size'] / self.max_size) * 100
            
            return stats
    
    def start_cleanup_task(self):
        """Start the cleanup task."""
        if self._running:
            return
        
        self._running = True
        
        async def cleanup_loop():
            while self._running:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self.cleanup_expired()
                except Exception as e:
                    self.logger.error(f"Cleanup task error: {str(e)}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        self.logger.info("Memory cache cleanup task started")
    
    def stop_cleanup_task(self):
        """Stop the cleanup task."""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self._cleanup_task)
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Memory cache cleanup task stopped")


class MemoryCacheManager:
    """Memory cache manager that wraps the backend."""
    
    def __init__(self, max_size: int = 1000, cleanup_interval: int = 60):
        self.backend = MemoryCacheBackend(max_size, cleanup_interval)
        self.logger = logging.getLogger(__name__)
        
        # Start cleanup task
        self.backend.start_cleanup_task()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        return await self.backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return await self.backend.delete(key)
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        return await self.backend.delete_pattern(pattern)
    
    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        return await self.backend.clear_all()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.backend.get_stats()
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.backend.stop_cleanup_task()
        except:
            pass