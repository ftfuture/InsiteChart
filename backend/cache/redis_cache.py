"""
Redis cache backend for InsiteChart platform.

This module provides a Redis-based cache implementation for production
deployments with distributed caching needs.
"""

import asyncio
import json
import pickle
import logging
from typing import Any, Optional, Dict, List
import redis.asyncio as redis
from datetime import datetime, timedelta


class RedisCacheBackend:
    """Redis cache backend implementation."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 max_connections: int = 10, socket_timeout: int = 5):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.logger = logging.getLogger(__name__)
        
        self.redis_client = None
        self.connection_pool = None
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'reconnections': 0
        }
    
    async def connect(self):
        """Establish Redis connection."""
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
        
        if self.connection_pool:
            await self.connection_pool.disconnect()
        
        self.logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if not self.redis_client:
                await self.connect()
            
            value = await self.redis_client.get(key)
            
            if value is not None:
                self.stats['hits'] += 1
                
                # Try to deserialize
                try:
                    # First try JSON
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        # Then try pickle
                        return pickle.loads(value)
                    except (pickle.PickleError, TypeError):
                        # Return as string if both fail
                        return value.decode('utf-8')
            else:
                self.stats['misses'] += 1
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis get error for key {key}: {str(e)}")
            
            # Try to reconnect
            await self._handle_connection_error()
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Serialize value
            try:
                # Try JSON first (more efficient)
                serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                serialized_value = pickle.dumps(value)
            
            # Set with TTL if provided
            if ttl:
                result = await self.redis_client.setex(key, ttl, serialized_value)
            else:
                result = await self.redis_client.set(key, serialized_value)
            
            if result:
                self.stats['sets'] += 1
            
            return bool(result)
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis set error for key {key}: {str(e)}")
            
            # Try to reconnect
            await self._handle_connection_error()
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if not self.redis_client:
                await self.connect()
            
            result = await self.redis_client.delete(key)
            
            if result:
                self.stats['deletes'] += 1
            
            return bool(result)
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis delete error for key {key}: {str(e)}")
            
            # Try to reconnect
            await self._handle_connection_error()
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Find matching keys
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                # Delete in batches to avoid blocking
                batch_size = 100
                deleted_count = 0
                
                for i in range(0, len(keys), batch_size):
                    batch = keys[i:i + batch_size]
                    result = await self.redis_client.delete(*batch)
                    deleted_count += result
                
                self.stats['deletes'] += deleted_count
                return deleted_count
            
            return 0
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis delete pattern error for {pattern}: {str(e)}")
            
            # Try to reconnect
            await self._handle_connection_error()
            return 0
    
    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Use FLUSHDB to clear current database
            result = await self.redis_client.flushdb()
            return bool(result)
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis clear all error: {str(e)}")
            
            # Try to reconnect
            await self._handle_connection_error()
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Get Redis info
            info = await self.redis_client.info()
            
            # Calculate hit rate
            total_requests = self.stats['hits'] + self.stats['misses']
            if total_requests > 0:
                hit_rate = (self.stats['hits'] / total_requests) * 100
            else:
                hit_rate = 0.0
            
            stats = self.stats.copy()
            stats.update({
                'hit_rate': hit_rate,
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'uptime_in_seconds': info.get('uptime_in_seconds'),
                'redis_hit_rate': info.get('keyspace_hits', 0) / max(
                    info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1
                ) * 100
            })
            
            return stats
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis get stats error: {str(e)}")
            return self.stats.copy()
    
    async def _handle_connection_error(self):
        """Handle Redis connection errors."""
        try:
            await self.disconnect()
            await self.connect()
            self.stats['reconnections'] += 1
            self.logger.info("Redis reconnection successful")
        except Exception as e:
            self.logger.error(f"Redis reconnection failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check."""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Test basic operations
            test_key = 'health_check_test'
            test_value = {'timestamp': datetime.utcnow().isoformat()}
            
            # Set test value
            await self.redis_client.setex(test_key, 10, json.dumps(test_value))
            
            # Get test value
            retrieved = await self.redis_client.get(test_key)
            
            # Clean up
            await self.redis_client.delete(test_key)
            
            # Verify
            if retrieved and json.loads(retrieved) == test_value:
                return {'status': 'healthy', 'backend': 'Redis'}
            else:
                return {'status': 'unhealthy', 'reason': 'Test value mismatch'}
                
        except Exception as e:
            return {'status': 'unhealthy', 'reason': str(e)}


class RedisCacheManager:
    """Redis cache manager that wraps the backend."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 max_connections: int = 10, socket_timeout: int = 5):
        self.backend = RedisCacheBackend(
            host=host, port=port, db=db, password=password,
            max_connections=max_connections, socket_timeout=socket_timeout
        )
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Establish Redis connection."""
        await self.backend.connect()
    
    async def disconnect(self):
        """Close Redis connection."""
        await self.backend.disconnect()
    
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
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        return await self.backend.health_check()