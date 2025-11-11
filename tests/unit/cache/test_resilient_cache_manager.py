"""
ResilientCacheManager 단위 테스트

이 모듈은 ResilientCacheManager의 개별 기능을 독립적으로 테스트합니다.
특히 회로 차단기 패턴과 멀티레벨 캐시 기능을 집중적으로 테스트합니다.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from backend.cache.resilient_cache_manager import ResilientCacheManager, CacheEntry
from backend.cache.enhanced_redis_cache import EnhancedRedisManager, ConnectionState


class TestResilientCacheManager:
    """ResilientCacheManager 단위 테스트 클래스"""
    
    @pytest.fixture
    def cache_manager(self):
        """ResilientCacheManager 픽스처"""
        return ResilientCacheManager(
            l1_max_size=10,
            l1_ttl=60,
            l2_ttl=300,
            enable_fallback=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=60
        )
    
    @pytest.fixture
    def mock_redis_manager(self):
        """모의 Redis 관리자 픽스처"""
        redis_manager = Mock(spec=EnhancedRedisManager)
        redis_manager.connection_state = ConnectionState.CONNECTED
        redis_manager.redis_client = AsyncMock()
        redis_manager.get_connection_stats.return_value = {
            "state": ConnectionState.CONNECTED.value,
            "stats": {
                "total_connections": 1,
                "successful_connections": 1,
                "failed_connections": 0
            }
        }
        return redis_manager
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, cache_manager, mock_redis_manager):
        """성공적인 초기화 테스트"""
        with patch('backend.cache.resilient_cache_manager.EnhancedRedisManager') as mock_redis_class:
            mock_redis_class.return_value = mock_redis_manager
            
            # 테스트 실행
            await cache_manager.initialize()
            
            # 검증
            assert cache_manager.redis_manager == mock_redis_manager
            mock_redis_class.assert_called_once_with(redis_config={})
            mock_redis_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, cache_manager):
        """초기화 실패 시 메모리 전용 모드 테스트"""
        with patch('backend.cache.resilient_cache_manager.EnhancedRedisManager') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis connection failed")
            
            # 테스트 실행
            await cache_manager.initialize()
            
            # 검증
            assert cache_manager.redis_manager is None
            assert cache_manager.enable_fallback is True
    
    @pytest.mark.asyncio
    async def test_get_l1_hit(self, cache_manager):
        """L1 캐시 히트 테스트"""
        # L1 캐시에 데이터 저장
        test_key = "test_key"
        test_value = {"data": "test_value"}
        cache_manager.l1_cache[test_key] = CacheEntry(
            value=test_value,
            timestamp=time.time(),
            ttl=60
        )
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result == test_value
        assert cache_manager.stats["l1_hits"] == 1
        assert cache_manager.stats["l1_misses"] == 0
        assert cache_manager.stats["total_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_get_l1_miss_l2_hit(self, cache_manager, mock_redis_manager):
        """L1 미스, L2 히트 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # L2 캐시에 데이터 설정
        mock_redis_manager.redis_client.get.return_value = json.dumps(test_value)
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result == test_value
        assert cache_manager.stats["l1_misses"] == 1
        assert cache_manager.stats["l2_hits"] == 1
        assert cache_manager.stats["total_operations"] == 1
        
        # L1 캐시에 저장되었는지 확인
        assert test_key in cache_manager.l1_cache
    
    @pytest.mark.asyncio
    async def test_get_l1_l2_miss(self, cache_manager, mock_redis_manager):
        """L1, L2 모두 미스 테스트"""
        test_key = "test_key"
        
        # L2 캐시에 데이터 없음 설정
        mock_redis_manager.redis_client.get.return_value = None
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result is None
        assert cache_manager.stats["l1_misses"] == 1
        assert cache_manager.stats["l2_misses"] == 1
        assert cache_manager.stats["total_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_get_circuit_breaker_open(self, cache_manager, mock_redis_manager):
        """회로 차단기 개방 시 테스트"""
        test_key = "test_key"
        
        # 회로 차단기 개방 설정
        cache_manager.circuit_breaker_open = True
        cache_manager.circuit_breaker_open_time = time.time() - 30  # 30초 전 개방
        
        # L1 캐시에 데이터 저장
        test_value = {"data": "test_value"}
        cache_manager.l1_cache[test_key] = CacheEntry(
            value=test_value,
            timestamp=time.time(),
            ttl=60
        )
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result == test_value
        assert cache_manager.stats["l1_hits"] == 1
        assert cache_manager.stats["l2_hits"] == 0  # L2는 호출되지 않음
        
        # Redis 호출되지 않았는지 확인
        mock_redis_manager.redis_client.get.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_circuit_breaker_timeout(self, cache_manager, mock_redis_manager):
        """회로 차단기 타임아웃 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # 회로 차단기 개방 설정 (타임아웃 초과)
        cache_manager.circuit_breaker_open = True
        cache_manager.circuit_breaker_open_time = time.time() - 70  # 70초 전 개방 (60초 타임아웃 초과)
        
        # L2 캐시에 데이터 설정
        mock_redis_manager.redis_client.get.return_value = json.dumps(test_value)
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result == test_value
        assert cache_manager.stats["l1_misses"] == 1
        assert cache_manager.stats["l2_hits"] == 1
        
        # 회로 차단기 닫혔는지 확인
        assert cache_manager.circuit_breaker_open is False
        assert cache_manager.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_set_success(self, cache_manager, mock_redis_manager):
        """성공적인 설정 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # Redis 성공 설정
        mock_redis_manager.redis_client.set.return_value = True
        mock_redis_manager.redis_client.setex.return_value = True
        
        # 테스트 실행
        result = await cache_manager.set(test_key, test_value, 300)
        
        # 검증
        assert result is True
        assert cache_manager.stats["total_operations"] == 1
        assert cache_manager.stats["successful_operations"] == 1
        
        # L1 캐시에 저장되었는지 확인
        assert test_key in cache_manager.l1_cache
        
        # L2 캐시에 저장되었는지 확인
        mock_redis_manager.redis_client.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_circuit_breaker_open(self, cache_manager, mock_redis_manager):
        """회로 차단기 개방 시 설정 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # 회로 차단기 개방 설정
        cache_manager.circuit_breaker_open = True
        cache_manager.circuit_breaker_open_time = time.time()
        
        # 테스트 실행
        result = await cache_manager.set(test_key, test_value, 300)
        
        # 검증
        assert result is True  # L1에만 저장되므로 성공
        assert cache_manager.stats["total_operations"] == 1
        assert cache_manager.stats["successful_operations"] == 1
        
        # L1 캐시에 저장되었는지 확인
        assert test_key in cache_manager.l1_cache
        
        # Redis 호출되지 않았는지 확인
        mock_redis_manager.redis_client.setex.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_set_redis_error(self, cache_manager, mock_redis_manager):
        """Redis 오류 시 설정 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # Redis 오류 설정
        mock_redis_manager.redis_client.setex.side_effect = Exception("Redis error")
        
        # 테스트 실행
        result = await cache_manager.set(test_key, test_value, 300)
        
        # 검증
        assert result is False
        assert cache_manager.stats["total_operations"] == 1
        assert cache_manager.stats["failed_operations"] == 1
        assert cache_manager.consecutive_failures == 1
        
        # 회로 차단기 개방 확인
        assert cache_manager.circuit_breaker_open is True
    
    @pytest.mark.asyncio
    async def test_set_circuit_breaker_activation(self, cache_manager, mock_redis_manager):
        """회로 차단기 활성화 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # Redis 오류 설정 (연속 실패)
        mock_redis_manager.redis_client.setex.side_effect = Exception("Redis error")
        
        # 회로 차단기 임계값까지 반복
        for i in range(cache_manager.circuit_breaker_threshold):
            await cache_manager.set(f"{test_key}_{i}", test_value, 300)
        
        # 검증
        assert cache_manager.consecutive_failures == cache_manager.circuit_breaker_threshold
        assert cache_manager.circuit_breaker_open is True
        assert cache_manager.stats["circuit_breaker_activations"] == 1
    
    @pytest.mark.asyncio
    async def test_delete_success(self, cache_manager, mock_redis_manager):
        """성공적인 삭제 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # L1 캐시에 데이터 저장
        cache_manager.l1_cache[test_key] = CacheEntry(
            value=test_value,
            timestamp=time.time(),
            ttl=60
        )
        
        # Redis 성공 설정
        mock_redis_manager.redis_client.delete.return_value = 1
        
        # 테스트 실행
        result = await cache_manager.delete(test_key)
        
        # 검증
        assert result is True
        assert test_key not in cache_manager.l1_cache
        
        # Redis 삭제 호출 확인
        mock_redis_manager.redis_client.delete.assert_called_once_with(test_key)
    
    @pytest.mark.asyncio
    async def test_delete_circuit_breaker_open(self, cache_manager, mock_redis_manager):
        """회로 차단기 개방 시 삭제 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # L1 캐시에 데이터 저장
        cache_manager.l1_cache[test_key] = CacheEntry(
            value=test_value,
            timestamp=time.time(),
            ttl=60
        )
        
        # 회로 차단기 개방 설정
        cache_manager.circuit_breaker_open = True
        cache_manager.circuit_breaker_open_time = time.time()
        
        # 테스트 실행
        result = await cache_manager.delete(test_key)
        
        # 검증
        assert result is True
        assert test_key not in cache_manager.l1_cache
        
        # Redis 호출되지 않았는지 확인
        mock_redis_manager.redis_client.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_evict_l1_lru(self, cache_manager):
        """L1 캐시 LRU 제거 테스트"""
        # 최대 크기만큼 데이터 저장
        for i in range(cache_manager.l1_max_size):
            cache_manager.l1_cache[f"key_{i}"] = CacheEntry(
                value=f"value_{i}",
                timestamp=time.time() - i,  # 오래된 데이터일수록 더 작은 타임스탬프
                ttl=60
            )
        
        # 최대 크기 초과하여 새 데이터 추가
        await cache_manager._evict_l1_lru()
        
        # 검증
        assert len(cache_manager.l1_cache) == cache_manager.l1_max_size - 1
        
        # 가장 오래된 데이터가 제거되었는지 확인
        assert "key_0" not in cache_manager.l1_cache  # 가장 오래된 데이터
        assert "key_9" in cache_manager.l1_cache   # 가장 최신 데이터
    
    @pytest.mark.asyncio
    async def test_get_l2_deserialization_json(self, cache_manager, mock_redis_manager):
        """L2 캐시 JSON 역직렬화 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value", "number": 123}
        
        # JSON 데이터 설정
        mock_redis_manager.redis_client.get.return_value = json.dumps(test_value)
        
        # 테스트 실행
        result = await cache_manager._get_l2(test_key)
        
        # 검증
        assert result == test_value
    
    @pytest.mark.asyncio
    async def test_get_l2_deserialization_pickle(self, cache_manager, mock_redis_manager):
        """L2 캐시 Pickle 역직렬화 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value", "number": 123}
        
        # Pickle 데이터 설정
        import pickle
        mock_redis_manager.redis_client.get.return_value = pickle.dumps(test_value)
        
        # JSON 역직렬화 실패 설정
        with patch('json.loads', side_effect=json.JSONDecodeError("Not JSON")):
            # 테스트 실행
            result = await cache_manager._get_l2(test_key)
            
            # 검증
            assert result == test_value
    
    @pytest.mark.asyncio
    async def test_get_l2_deserialization_failure(self, cache_manager, mock_redis_manager):
        """L2 캐시 역직렬화 실패 테스트"""
        test_key = "test_key"
        
        # 잘못된 데이터 설정
        mock_redis_manager.redis_client.get.return_value = "invalid_data"
        
        # JSON과 Pickle 모두 실패 설정
        with patch('json.loads', side_effect=json.JSONDecodeError("Not JSON")), \
             patch('pickle.loads', side_effect=pickle.PickleError("Not Pickle")):
            
            # 테스트 실행
            result = await cache_manager._get_l2(test_key)
            
            # 검증
            assert result is None
    
    @pytest.mark.asyncio
    async def test_set_l2_serialization_json(self, cache_manager, mock_redis_manager):
        """L2 캐시 JSON 직렬화 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value", "number": 123}
        
        # Redis 성공 설정
        mock_redis_manager.redis_client.setex.return_value = True
        
        # 테스트 실행
        await cache_manager._set_l2(test_key, test_value, 300)
        
        # 검증
        mock_redis_manager.redis_client.setex.assert_called_once()
        call_args = mock_redis_manager.redis_client.setex.call_args
        assert call_args[0][0] == test_key
        assert call_args[0][1] == 300
        assert call_args[0][2] == json.dumps(test_value)
    
    @pytest.mark.asyncio
    async def test_set_l2_serialization_pickle(self, cache_manager, mock_redis_manager):
        """L2 캐시 Pickle 직렬화 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value", "number": 123, "object": object()}  # JSON으로 직렬화 불가능한 객체
        
        # Redis 성공 설정
        mock_redis_manager.redis_client.setex.return_value = True
        
        # 테스트 실행
        await cache_manager._set_l2(test_key, test_value, 300)
        
        # 검증
        mock_redis_manager.redis_client.setex.assert_called_once()
        call_args = mock_redis_manager.redis_client.setex.call_args
        assert call_args[0][0] == test_key
        assert call_args[0][1] == 300
        
        # Pickle로 직렬화되었는지 확인
        import pickle
        assert call_args[0][2] == pickle.dumps(test_value)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache_manager, mock_redis_manager):
        """상태 확인 - 건강한 상태 테스트"""
        # 건강한 상태 설정
        cache_manager.l1_cache["test"] = CacheEntry(
            value="test_value",
            timestamp=time.time(),
            ttl=60
        )
        cache_manager.stats = {
            "total_operations": 100,
            "successful_operations": 90,
            "failed_operations": 10,
            "l1_hits": 60,
            "l1_misses": 20,
            "l2_hits": 15,
            "l2_misses": 5
        }
        
        # Redis 상태 설정
        mock_redis_manager.connection_state = ConnectionState.CONNECTED
        mock_redis_manager.get_connection_stats.return_value = {
            "state": ConnectionState.CONNECTED.value,
            "stats": {"total_connections": 10, "successful_connections": 10}
        }
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result["status"] == "healthy"
        assert result["redis"]["connected"] is True
        assert result["redis"]["state"] == ConnectionState.CONNECTED.value
        assert result["circuit_breaker"]["open"] is False
        assert result["cache"]["stats"]["l1_size"] == 1
        assert result["cache"]["stats"]["l1_hit_rate"] == 75.0  # 60 / (60 + 20) * 100
        assert result["cache"]["stats"]["l2_hit_rate"] == 75.0  # 15 / (15 + 5) * 100
    
    @pytest.mark.asyncio
    async def test_health_check_degraded_redis(self, cache_manager, mock_redis_manager):
        """상태 확인 - Redis 연결 끊김 테스트"""
        # Redis 연결 끊김 설정
        mock_redis_manager.connection_state = ConnectionState.DISCONNECTED
        mock_redis_manager.get_connection_stats.return_value = {
            "state": ConnectionState.DISCONNECTED.value,
            "stats": {"total_connections": 10, "successful_connections": 5}
        }
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result["status"] == "degraded"
        assert result["redis"]["connected"] is False
        assert result["redis"]["state"] == ConnectionState.DISCONNECTED.value
    
    @pytest.mark.asyncio
    async def test_health_check_circuit_breaker_open(self, cache_manager):
        """상태 확인 - 회로 차단기 개방 테스트"""
        # 회로 차단기 개방 설정
        cache_manager.circuit_breaker_open = True
        cache_manager.consecutive_failures = 5
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result["status"] == "degraded"
        assert result["circuit_breaker"]["open"] is True
        assert result["circuit_breaker"]["consecutive_failures"] == 5
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, cache_manager):
        """상태 확인 - 비건강한 상태 테스트"""
        # 실패 운영 많음 설정
        cache_manager.stats = {
            "total_operations": 100,
            "successful_operations": 30,
            "failed_operations": 70  # 성공보다 실패가 많음
        }
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_manager, mock_redis_manager):
        """캐시 통계 조회 테스트"""
        # 통계 설정
        cache_manager.stats = {
            "total_operations": 100,
            "successful_operations": 90,
            "failed_operations": 10,
            "l1_hits": 60,
            "l1_misses": 20,
            "l2_hits": 15,
            "l2_misses": 5,
            "circuit_breaker_activations": 2,
            "fallback_operations": 3
        }
        
        # Redis 상태 설정
        mock_redis_manager.connection_state = ConnectionState.CONNECTED
        
        # 테스트 실행
        result = await cache_manager.get_cache_stats()
        
        # 검증
        assert result["total_operations"] == 100
        assert result["successful_operations"] == 90
        assert result["failed_operations"] == 10
        assert result["hit_rate"] == 75.0  # (60 + 15) / (60 + 20 + 15 + 5) * 100
        assert result["l1_cache"]["hits"] == 60
        assert result["l1_cache"]["misses"] == 20
        assert result["l1_cache"]["hit_rate"] == 75.0
        assert result["l2_cache"]["hits"] == 15
        assert result["l2_cache"]["misses"] == 5
        assert result["l2_cache"]["hit_rate"] == 75.0
        assert result["l2_cache"]["connected"] is True
        assert result["circuit_breaker"]["open"] is False
        assert result["circuit_breaker"]["activations"] == 2
        assert result["circuit_breaker"]["consecutive_failures"] == 0
        assert result["fallback"]["used"] == 3
        assert result["fallback"]["usage_rate"] == 3.0
    
    @pytest.mark.asyncio
    async def test_clear_all_success(self, cache_manager, mock_redis_manager):
        """전체 삭제 성공 테스트"""
        # L1 캐시에 데이터 저장
        cache_manager.l1_cache["test1"] = CacheEntry(
            value="value1",
            timestamp=time.time(),
            ttl=60
        )
        cache_manager.l1_cache["test2"] = CacheEntry(
            value="value2",
            timestamp=time.time(),
            ttl=60
        )
        
        # Redis 성공 설정
        mock_redis_manager.redis_client.flushdb.return_value = True
        
        # 테스트 실행
        result = await cache_manager.clear_all()
        
        # 검증
        assert result is True
        assert len(cache_manager.l1_cache) == 0
        assert cache_manager.stats["total_operations"] == 0
        assert cache_manager.stats["successful_operations"] == 0
        assert cache_manager.stats["failed_operations"] == 0
        assert cache_manager.circuit_breaker_open is False
        assert cache_manager.consecutive_failures == 0
        
        # Redis 전체 삭제 호출 확인
        mock_redis_manager.redis_client.flushdb.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_redis_connection_change_connected(self, cache_manager):
        """Redis 연결 상태 변경 콜백 - 연결됨 테스트"""
        # 회로 차단기 개방 상태 설정
        cache_manager.circuit_breaker_open = True
        cache_manager.consecutive_failures = 5
        
        # 테스트 실행
        await cache_manager._on_redis_connection_change(True)
        
        # 검증
        assert cache_manager.circuit_breaker_open is False
        assert cache_manager.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_on_redis_connection_change_disconnected(self, cache_manager):
        """Redis 연결 상태 변경 콜백 - 연결 끊김 테스트"""
        # 초기 상태 설정
        cache_manager.consecutive_failures = 2
        
        # 테스트 실행
        await cache_manager._on_redis_connection_change(False, "Connection lost")
        
        # 검증
        assert cache_manager.consecutive_failures == 3
    
    @pytest.mark.asyncio
    async def test_on_redis_error(self, cache_manager):
        """Redis 에러 콜백 테스트"""
        # 초기 상태 설정
        cache_manager.consecutive_failures = 2
        
        # 테스트 실행
        await cache_manager._on_redis_error("Redis timeout")
        
        # 검증
        assert cache_manager.consecutive_failures == 3
    
    @pytest.mark.asyncio
    async def test_close(self, cache_manager, mock_redis_manager):
        """종료 테스트"""
        # 테스트 실행
        await cache_manager.close()
        
        # 검증
        mock_redis_manager.disconnect.assert_called_once()
        assert cache_manager.redis_manager is None


class TestCacheEntry:
    """CacheEntry 단위 테스트 클래스"""
    
    def test_is_expired_false(self):
        """만료되지 않은 엔트리 테스트"""
        entry = CacheEntry(
            value="test_value",
            timestamp=time.time(),
            ttl=60
        )
        
        # 검증
        assert entry.is_expired() is False
    
    def test_is_expired_true(self):
        """만료된 엔트리 테스트"""
        entry = CacheEntry(
            value="test_value",
            timestamp=time.time() - 120,  # 2분 전
            ttl=60  # 1분 TTL
        )
        
        # 검증
        assert entry.is_expired() is True
    
    def test_access(self):
        """접근 테스트"""
        entry = CacheEntry(
            value="test_value",
            timestamp=time.time() - 10,
            ttl=60
        )
        
        # 초기 상태 확인
        assert entry.access_count == 0
        assert entry.last_access == 0
        
        # 접근 실행
        entry.access()
        
        # 검증
        assert entry.access_count == 1
        assert entry.last_access > time.time() - 1  # 최근 1초 내