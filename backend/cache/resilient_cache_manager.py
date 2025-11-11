"""
회복력 있는 캐시 관리자

이 모듈은 Redis 연결 안정성 문제를 해결하기 위한 통합 캐시 관리 기능을 제공합니다.
멀티레벨 캐시, 회로 차단기 패턴, 자동 복구 기능을 포함합니다.
"""

import asyncio
import time
import json
import pickle
import logging
from typing import Any, Optional, Dict, List
from dataclasses import dataclass
from .enhanced_redis_cache import EnhancedRedisManager, ConnectionState

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    last_access: float = 0
    
    def is_expired(self) -> bool:
        """만료 확인"""
        return time.time() > (self.timestamp + self.ttl)
    
    def access(self):
        """접근 기록"""
        self.access_count += 1
        self.last_access = time.time()

class ResilientCacheManager:
    """회복력 있는 캐시 관리자"""
    
    def __init__(
        self,
        redis_config: Optional[Dict] = None,
        l1_max_size: int = 1000,
        l1_ttl: int = 60,  # 1분
        l2_ttl: int = 300,  # 5분
        enable_fallback: bool = True,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_timeout: int = 60
    ):
        self.redis_config = redis_config or {}
        self.l1_max_size = l1_max_size
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.enable_fallback = enable_fallback
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        # L1 캐시 (인메모리)
        self.l1_cache: Dict[str, CacheEntry] = {}
        
        # Redis 관리자
        self.redis_manager = None
        
        # 회로 차단기 상태
        self.circuit_breaker_open = False
        self.circuit_breaker_open_time = 0
        self.consecutive_failures = 0
        
        # 통계
        self.stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "circuit_breaker_activations": 0,
            "fallback_operations": 0
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """캐시 관리자 초기화"""
        try:
            # Redis 관리자 초기화
            self.redis_manager = EnhancedRedisManager(**self.redis_config)
            
            # 연결 상태 콜백 등록
            self.redis_manager.add_connection_callback(self._on_redis_connection_change)
            self.redis_manager.add_error_callback(self._on_redis_error)
            
            await self.redis_manager.initialize()
            
            self.logger.info("Resilient cache manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize resilient cache manager: {str(e)}")
            # Redis 실패 시에도 인메모리 캐시로 동작
            self.logger.warning("Operating in memory-only mode due to Redis failure")
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        self.stats["total_operations"] += 1
        
        try:
            # 회로 차단기 확인
            if self._is_circuit_breaker_open():
                self.logger.warning("Circuit breaker is open, using L1 cache only")
                return await self._get_l1_only(key)
            
            # L1 캐시 확인
            value = await self._get_l1(key)
            if value is not None:
                self.stats["l1_hits"] += 1
                return value
            
            self.stats["l1_misses"] += 1
            
            # L2 캐시 확인 (Redis)
            if self.redis_manager and self.redis_manager.connection_state == ConnectionState.CONNECTED:
                try:
                    value = await self._get_l2(key)
                    if value is not None:
                        self.stats["l2_hits"] += 1
                        # L1 캐시에 저장
                        await self._set_l1(key, value, self.l1_ttl)
                        self.consecutive_failures = 0  # 성공 시 실패 카운트 리셋
                        return value
                except Exception as e:
                    self.logger.warning(f"L2 cache error: {str(e)}")
                    self.consecutive_failures += 1
                    
                    # 회로 차단기 확인
                    if self.consecutive_failures >= self.circuit_breaker_threshold:
                        self._open_circuit_breaker()
            
            self.stats["l2_misses"] += 1
            
            # L3 (데이터베이스 또는 폴백)
            if self.enable_fallback:
                self.stats["fallback_operations"] += 1
                return None  # 상위 계층에서 처리
            
            return None
            
        except Exception as e:
            self.stats["failed_operations"] += 1
            self.logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        self.stats["total_operations"] += 1
        
        try:
            if ttl is None:
                ttl = self.l2_ttl
            
            success = True
            
            # L1 캐시에 저장
            await self._set_l1(key, value, min(ttl, self.l1_ttl))
            
            # 회로 차단기 확인
            if self._is_circuit_breaker_open():
                self.logger.warning("Circuit breaker is open, skipping L2 cache write")
                return True
            
            # L2 캐시에 저장 (Redis)
            if self.redis_manager and self.redis_manager.connection_state == ConnectionState.CONNECTED:
                try:
                    await self._set_l2(key, value, ttl)
                    self.consecutive_failures = 0  # 성공 시 실패 카운트 리셋
                except Exception as e:
                    self.logger.warning(f"L2 cache set error: {str(e)}")
                    self.consecutive_failures += 1
                    success = False
                    
                    # 회로 차단기 확인
                    if self.consecutive_failures >= self.circuit_breaker_threshold:
                        self._open_circuit_breaker()
            
            return success
            
        except Exception as e:
            self.stats["failed_operations"] += 1
            self.logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 키 삭제"""
        self.stats["total_operations"] += 1
        
        try:
            success = True
            
            # L1 캐시에서 삭제
            if key in self.l1_cache:
                del self.l1_cache[key]
            
            # 회로 차단기 확인
            if self._is_circuit_breaker_open():
                self.logger.warning("Circuit breaker is open, skipping L2 cache delete")
                return True
            
            # L2 캐시에서 삭제 (Redis)
            if self.redis_manager and self.redis_manager.connection_state == ConnectionState.CONNECTED:
                try:
                    await self._delete_l2(key)
                    self.consecutive_failures = 0  # 성공 시 실패 카운트 리셋
                except Exception as e:
                    self.logger.warning(f"L2 cache delete error: {str(e)}")
                    self.consecutive_failures += 1
                    success = False
                    
                    # 회로 차단기 확인
                    if self.consecutive_failures >= self.circuit_breaker_threshold:
                        self._open_circuit_breaker()
            
            return success
            
        except Exception as e:
            self.stats["failed_operations"] += 1
            self.logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    async def _get_l1(self, key: str) -> Optional[Any]:
        """L1 캐시에서 값 조회"""
        if key not in self.l1_cache:
            return None
        
        entry = self.l1_cache[key]
        
        # 만료 확인
        if entry.is_expired():
            del self.l1_cache[key]
            return None
        
        # 접근 기록
        entry.access()
        return entry.value
    
    async def _get_l1_only(self, key: str) -> Optional[Any]:
        """L1 캐시에서만 값 조회 (회로 차단기 개방 시)"""
        value = await self._get_l1(key)
        if value is not None:
            self.logger.debug(f"L1 cache hit (circuit breaker open): {key}")
        return value
    
    async def _set_l1(self, key: str, value: Any, ttl: int):
        """L1 캐시에 값 저장"""
        # 용량 관리 (LRU)
        if len(self.l1_cache) >= self.l1_max_size:
            await self._evict_l1_lru()
        
        self.l1_cache[key] = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl
        )
    
    async def _evict_l1_lru(self):
        """L1 캐시에서 LRU 기반으로 제거"""
        if not self.l1_cache:
            return
        
        # 가장 오래된 항목 찾기
        oldest_key = min(
            self.l1_cache.keys(),
            key=lambda k: self.l1_cache[k].last_access
        )
        
        del self.l1_cache[oldest_key]
    
    async def _get_l2(self, key: str) -> Optional[Any]:
        """L2 캐시에서 값 조회"""
        if not self.redis_manager or not self.redis_manager.redis_client:
            return None
        
        value = await self.redis_manager.redis_client.get(key)
        
        if value is not None:
            try:
                # 역직렬화 시도
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return pickle.loads(value)
                    except (pickle.PickleError, TypeError):
                        return value.decode('utf-8')
            except Exception as e:
                self.logger.error(f"L2 cache deserialization error: {str(e)}")
                return None
        
        return None
    
    async def _set_l2(self, key: str, value: Any, ttl: int):
        """L2 캐시에 값 저장"""
        if not self.redis_manager or not self.redis_manager.redis_client:
            return False
        
        # 직렬화
        try:
            serialized_value = json.dumps(value, default=str)
        except (TypeError, ValueError):
            serialized_value = pickle.dumps(value)
        
        # TTL 설정
        if ttl > 0:
            await self.redis_manager.redis_client.setex(key, ttl, serialized_value)
        else:
            await self.redis_manager.redis_client.set(key, serialized_value)
        
        return True
    
    async def _delete_l2(self, key: str):
        """L2 캐시에서 키 삭제"""
        if not self.redis_manager or not self.redis_manager.redis_client:
            return False
        
        await self.redis_manager.redis_client.delete(key)
        return True
    
    def _is_circuit_breaker_open(self) -> bool:
        """회로 차단기 개방 여부 확인"""
        if not self.circuit_breaker_open:
            return False
        
        # 타임아웃 확인
        if time.time() - self.circuit_breaker_open_time > self.circuit_breaker_timeout:
            self.logger.info("Circuit breaker timeout, attempting to close")
            self.circuit_breaker_open = False
            self.consecutive_failures = 0
            return False
        
        return True
    
    def _open_circuit_breaker(self):
        """회로 차단기 개방"""
        if not self.circuit_breaker_open:
            self.circuit_breaker_open = True
            self.circuit_breaker_open_time = time.time()
            self.stats["circuit_breaker_activations"] += 1
            self.logger.warning(f"Circuit breaker opened due to {self.consecutive_failures} consecutive failures")
    
    async def _on_redis_connection_change(self, connected: bool, error_message: str = None):
        """Redis 연결 상태 변경 콜백"""
        if connected:
            self.logger.info("Redis reconnected successfully")
            # 연결 복구 시 회로 차단기 닫기 시도
            if self.circuit_breaker_open:
                self.circuit_breaker_open = False
                self.consecutive_failures = 0
                self.logger.info("Circuit breaker closed due to Redis reconnection")
        else:
            self.logger.warning(f"Redis disconnected: {error_message}")
            self.consecutive_failures += 1
            
            # 연결 실패 시 회로 차단기 개방 확인
            if self.consecutive_failures >= self.circuit_breaker_threshold:
                self._open_circuit_breaker()
    
    async def _on_redis_error(self, error_message: str):
        """Redis 에러 콜백"""
        self.logger.error(f"Redis error: {error_message}")
        self.consecutive_failures += 1
        
        # 에러 발생 시 회로 차단기 개방 확인
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self._open_circuit_breaker()
    
    async def health_check(self) -> Dict[str, Any]:
        """상태 확인"""
        health_info = {
            "status": "healthy",
            "timestamp": time.time(),
            "redis": {
                "connected": False,
                "state": "unknown"
            },
            "circuit_breaker": {
                "open": self.circuit_breaker_open,
                "consecutive_failures": self.consecutive_failures
            },
            "cache": {
                "stats": {}
            },
            "operations": self.stats.copy()
        }
        
        # Redis 상태 확인
        if self.redis_manager:
            redis_stats = await self.redis_manager.get_connection_stats()
            health_info["redis"] = {
                "connected": redis_stats["state"] == ConnectionState.CONNECTED.value,
                "state": redis_stats["state"],
                "stats": redis_stats
            }
        
        # 캐시 상태 확인
        health_info["cache"]["stats"] = {
            "l1_size": len(self.l1_cache),
            "l1_max_size": self.l1_max_size,
            "l1_hit_rate": (self.stats["l1_hits"] / max(self.stats["l1_hits"] + self.stats["l1_misses"], 1)) * 100,
            "l2_hit_rate": (self.stats["l2_hits"] / max(self.stats["l2_hits"] + self.stats["l2_misses"], 1)) * 100
        }
        
        # 전체 상태 판단
        if not health_info["redis"]["connected"]:
            health_info["status"] = "degraded"
        
        if self.circuit_breaker_open:
            health_info["status"] = "degraded"
        
        if self.stats["failed_operations"] > self.stats["successful_operations"]:
            health_info["status"] = "unhealthy"
        
        return health_info
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        total_hits = self.stats["l1_hits"] + self.stats["l2_hits"]
        total_requests = self.stats["l1_hits"] + self.stats["l1_misses"] + self.stats["l2_hits"] + self.stats["l2_misses"]
        
        return {
            "total_operations": self.stats["total_operations"],
            "successful_operations": self.stats["successful_operations"],
            "failed_operations": self.stats["failed_operations"],
            "hit_rate": (total_hits / max(total_requests, 1)) * 100,
            "l1_cache": {
                "hits": self.stats["l1_hits"],
                "misses": self.stats["l1_misses"],
                "size": len(self.l1_cache),
                "max_size": self.l1_max_size,
                "hit_rate": (self.stats["l1_hits"] / max(self.stats["l1_hits"] + self.stats["l1_misses"], 1)) * 100
            },
            "l2_cache": {
                "hits": self.stats["l2_hits"],
                "misses": self.stats["l2_misses"],
                "hit_rate": (self.stats["l2_hits"] / max(self.stats["l2_hits"] + self.stats["l2_misses"], 1)) * 100,
                "connected": self.redis_manager.connection_state == ConnectionState.CONNECTED if self.redis_manager else False
            },
            "circuit_breaker": {
                "open": self.circuit_breaker_open,
                "activations": self.stats["circuit_breaker_activations"],
                "consecutive_failures": self.consecutive_failures
            },
            "fallback": {
                "used": self.stats["fallback_operations"],
                "usage_rate": (self.stats["fallback_operations"] / max(self.stats["total_operations"], 1)) * 100
            }
        }
    
    async def clear_all(self) -> bool:
        """모든 캐시 비우기"""
        try:
            # L1 캐시 비우기
            self.l1_cache.clear()
            
            # L2 캐시 비우기
            if self.redis_manager and self.redis_manager.redis_client:
                await self.redis_manager.redis_client.flushdb()
            
            # 통계 초기화
            for key in self.stats:
                self.stats[key] = 0
            
            # 회로 차단기 초기화
            self.circuit_breaker_open = False
            self.consecutive_failures = 0
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    async def close(self):
        """캐시 관리자 종료"""
        try:
            if self.redis_manager:
                await self.redis_manager.disconnect()
            
            self.logger.info("Resilient cache manager closed")
            
        except Exception as e:
            self.logger.error(f"Error closing cache manager: {str(e)}")

# 전역 인스턴스
resilient_cache_manager = ResilientCacheManager()