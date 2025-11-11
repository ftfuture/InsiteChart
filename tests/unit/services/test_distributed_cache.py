"""
분산 캐시 서비스 단위 테스트

이 모듈은 분산 캐시 서비스의 개별 기능을 테스트합니다.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from backend.services.distributed_cache import DistributedCacheService
from backend.models.unified_models import CacheNode, CacheStatus


class TestDistributedCacheService:
    """분산 캐시 서비스 단위 테스트 클래스"""
    
    @pytest.fixture
    def distributed_cache_service(self):
        """분산 캐시 서비스 픽스처"""
        return DistributedCacheService()
    
    @pytest.fixture
    def mock_cache_nodes(self):
        """모의 캐시 노드 픽스처"""
        return [
            CacheNode(
                node_id="node1",
                host="localhost",
                port=7001,
                status=CacheStatus.ACTIVE,
                last_heartbeat=time.time(),
                memory_usage=60.5,
                cpu_usage=45.2,
                cache_size=1024 * 1024 * 512,  # 512MB
                hit_rate=85.3
            ),
            CacheNode(
                node_id="node2",
                host="localhost",
                port=7002,
                status=CacheStatus.ACTIVE,
                last_heartbeat=time.time(),
                memory_usage=55.8,
                cpu_usage=40.1,
                cache_size=1024 * 1024 * 768,  # 768MB
                hit_rate=82.7
            ),
            CacheNode(
                node_id="node3",
                host="localhost",
                port=7003,
                status=CacheStatus.INACTIVE,  # 비활성 노드
                last_heartbeat=time.time() - 300,  # 5분 전
                memory_usage=0.0,
                cpu_usage=0.0,
                cache_size=0,
                hit_rate=0.0
            )
        ]
    
    @pytest.mark.asyncio
    async def test_distributed_cache_initialization(self, distributed_cache_service):
        """분산 캐시 초기화 테스트"""
        with patch('backend.services.distributed_cache.discover_cache_nodes') as mock_discover:
            mock_discover.return_value = []
            
            await distributed_cache_service.initialize()
            
            assert distributed_cache_service.is_initialized is True
            assert len(distributed_cache_service.cache_nodes) >= 0
            assert distributed_cache_service.consistent_hash_ring is not None
            assert distributed_cache_service.node_selector is not None
    
    @pytest.mark.asyncio
    async def test_cache_node_discovery(self, distributed_cache_service, mock_cache_nodes):
        """캐시 노드 발견 테스트"""
        with patch('backend.services.distributed_cache.discover_cache_nodes') as mock_discover:
            mock_discover.return_value = mock_cache_nodes
            
            discovered_nodes = await distributed_cache_service.discover_nodes()
            
            assert len(discovered_nodes) == 3
            assert discovered_nodes[0].node_id == "node1"
            assert discovered_nodes[1].node_id == "node2"
            assert discovered_nodes[2].node_id == "node3"
            assert discovered_nodes[0].status == CacheStatus.ACTIVE
            assert discovered_nodes[2].status == CacheStatus.INACTIVE
    
    @pytest.mark.asyncio
    async def test_consistent_hash_key_distribution(self, distributed_cache_service, mock_cache_nodes):
        """일관성 해시 키 분배 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        # 다양한 테스트 키
        test_keys = [
            "user:12345",
            "stock:AAPL",
            "sentiment:analysis:123",
            "cache:session:abc123",
            "api:response:xyz789"
        ]
        
        key_distribution = {}
        
        for key in test_keys:
            node = distributed_cache_service._get_node_for_key(key)
            node_id = node.node_id
            key_distribution[node_id] = key_distribution.get(node_id, 0) + 1
        
        # 키가 활성 노드에만 분배되는지 확인
        assert "node1" in key_distribution
        assert "node2" in key_distribution
        assert "node3" not in key_distribution  # 비활성 노드에는 분배되지 않아야 함
        
        # 분배가 비교적 균등한지 확인
        total_keys = sum(key_distribution.values())
        for node_id, count in key_distribution.items():
            ratio = count / total_keys
            assert 0.3 <= ratio <= 0.7  # 30-70% 범위 내
    
    @pytest.mark.asyncio
    async def test_distributed_cache_set_operation(self, distributed_cache_service, mock_cache_nodes):
        """분산 캐시 SET 작업 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True, "node_id": "node1"}
            
            result = await distributed_cache_service.set(
                key="test_key",
                value={"data": "test_value", "timestamp": time.time()},
                ttl=3600
            )
            
            assert result is True
            mock_send.assert_called_once()
            
            # 호출된 노드 확인
            call_args = mock_send.call_args[0][0]
            assert call_args["command"] == "SET"
            assert call_args["key"] == "test_key"
            assert call_args["value"] == {"data": "test_value", "timestamp": time.time()}
            assert call_args["ttl"] == 3600
    
    @pytest.mark.asyncio
    async def test_distributed_cache_get_operation_hit(self, distributed_cache_service, mock_cache_nodes):
        """분산 캐시 GET 작업 히트 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {
                "success": True,
                "node_id": "node1",
                "value": {"data": "cached_value", "timestamp": time.time()},
                "found": True
            }
            
            result = await distributed_cache_service.get("test_key")
            
            assert result is not None
            assert result["data"] == "cached_value"
            assert result["found"] is True
            mock_send.assert_called_once()
            
            # 호출된 노드 확인
            call_args = mock_send.call_args[0][0]
            assert call_args["command"] == "GET"
            assert call_args["key"] == "test_key"
    
    @pytest.mark.asyncio
    async def test_distributed_cache_get_operation_miss(self, distributed_cache_service, mock_cache_nodes):
        """분산 캐시 GET 작업 미스 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {
                "success": True,
                "node_id": "node1",
                "found": False
            }
            
            result = await distributed_cache_service.get("nonexistent_key")
            
            assert result is None
            mock_send.assert_called_once()
            
            # 호출된 노드 확인
            call_args = mock_send.call_args[0][0]
            assert call_args["command"] == "GET"
            assert call_args["key"] == "nonexistent_key"
    
    @pytest.mark.asyncio
    async def test_distributed_cache_delete_operation(self, distributed_cache_service, mock_cache_nodes):
        """분산 캐시 DELETE 작업 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True, "node_id": "node1"}
            
            result = await distributed_cache_service.delete("test_key")
            
            assert result is True
            mock_send.assert_called_once()
            
            # 호출된 노드 확인
            call_args = mock_send.call_args[0][0]
            assert call_args["command"] == "DELETE"
            assert call_args["key"] == "test_key"
    
    @pytest.mark.asyncio
    async def test_node_failure_handling(self, distributed_cache_service, mock_cache_nodes):
        """노드 장애 처리 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            # 첫 번째 노드 실패
            mock_send.side_effect = [
                {"success": False, "error": "Connection timeout", "node_id": "node1"},
                {"success": True, "node_id": "node2"}  # 두 번째 노드 성공
            ]
            
            result = await distributed_cache_service.set("test_key", "test_value")
            
            assert result is True
            assert mock_send.call_count == 2
            
            # 두 번째 호출에서 성공한 노드 확인
            second_call_args = mock_send.call_args_list[1][0]
            assert second_call_args["command"] == "SET"
            assert second_call_args["key"] == "test_key"
            assert second_call_args["value"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_cache_replication(self, distributed_cache_service, mock_cache_nodes):
        """캐시 복제 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True, "node_id": "node1"}
            
            # 복제 인자로 SET 작업
            result = await distributed_cache_service.set(
                key="replicated_key",
                value="replicated_value",
                ttl=3600,
                replicate_to=2  # 2개 노드에 복제
            )
            
            assert result is True
            assert mock_send.call_count == 2  # 원본 + 복제
            
            # 복제 호출 확인
            for call_args in mock_send.call_args_list:
                assert call_args[0]["command"] == "SET"
                assert call_args[0]["key"] == "replicated_key"
                assert call_args[0]["value"] == "replicated_value"
    
    @pytest.mark.asyncio
    async def test_cache_consistency_check(self, distributed_cache_service, mock_cache_nodes):
        """캐시 일관성 확인 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            # 다른 노드에서 다른 값 반환
            mock_send.side_effect = [
                {"success": True, "node_id": "node1", "value": "value1", "found": True},
                {"success": True, "node_id": "node2", "value": "value2", "found": True}
            ]
            
            # 일관성 확인
            consistency_result = await distributed_cache_service.check_consistency("test_key")
            
            assert consistency_result is not None
            assert consistency_result["is_consistent"] is False
            assert consistency_result["conflict_count"] == 2
            assert "value1" in consistency_result["values"]
            assert "value2" in consistency_result["values"]
    
    @pytest.mark.asyncio
    async def test_cache_node_addition(self, distributed_cache_service, mock_cache_nodes):
        """캐시 노드 추가 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        initial_node_count = len(distributed_cache_service.cache_nodes)
        
        # 새 노드 추가
        new_node = CacheNode(
            node_id="node4",
            host="localhost",
            port=7004,
            status=CacheStatus.ACTIVE,
            last_heartbeat=time.time(),
            memory_usage=50.0,
            cpu_usage=35.0,
            cache_size=1024 * 1024 * 1024,  # 1GB
            hit_rate=90.0
        )
        
        with patch('backend.services.distributed_cache.add_node_to_ring') as mock_add:
            mock_add.return_value = True
            
            result = await distributed_cache_service.add_node(new_node)
            
            assert result is True
            assert len(distributed_cache_service.cache_nodes) == initial_node_count + 1
            assert new_node in distributed_cache_service.cache_nodes
            mock_add.assert_called_once_with(new_node)
    
    @pytest.mark.asyncio
    async def test_cache_node_removal(self, distributed_cache_service, mock_cache_nodes):
        """캐시 노드 제거 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        initial_node_count = len(distributed_cache_service.cache_nodes)
        
        with patch('backend.services.distributed_cache.remove_node_from_ring') as mock_remove:
            mock_remove.return_value = True
            
            result = await distributed_cache_service.remove_node("node1")
            
            assert result is True
            assert len(distributed_cache_service.cache_nodes) == initial_node_count - 1
            assert not any(node.node_id == "node1" for node in distributed_cache_service.cache_nodes)
            mock_remove.assert_called_once_with("node1")
    
    @pytest.mark.asyncio
    async def test_cache_node_health_monitoring(self, distributed_cache_service, mock_cache_nodes):
        """캐시 노드 상태 모니터링 테스트"""
        distributed_cache_service.cache_nodes = mock_cache_nodes
        
        with patch('backend.services.distributed_cache.check_node_health') as mock_health:
            # 노드 상태 반환
            mock_health.side_effect = [
                {"node_id": "node1", "status": CacheStatus.ACTIVE, "response_time": 25.5},
                {"node_id": "node2", "status": CacheStatus.ACTIVE, "response_time": 30.2},
                {"node_id": "node3", "status": CacheStatus.INACTIVE, "response_time": None}
            ]
            
            health_status = await distributed_cache_service.monitor_node_health()
            
            assert health_status is not None
            assert len(health_status["nodes"]) == 3
            assert health_status["nodes"][0]["node_id"] == "node1"
            assert health_status["nodes"][0]["status"] == CacheStatus.ACTIVE
            assert health_status["nodes"][1]["node_id"] == "node2"
            assert health_status["nodes"][1]["status"] == CacheStatus.ACTIVE
            assert health_status["nodes"][2]["node_id"] == "node3"
            assert health_status["nodes"][2]["status"] == CacheStatus.INACTIVE
            assert health_status["active_nodes"] == 2
            assert health_status["inactive_nodes"] == 1
    
    @pytest.mark.asyncio
    async def test_cache_load_balancing(self, distributed_cache_service, mock_cache_nodes):
        """캐시 부하 분산 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        # 노드별 부하 정보 설정
        distributed_cache_service.cache_nodes[0].current_load = 0.7  # 70% 부하
        distributed_cache_service.cache_nodes[1].current_load = 0.3  # 30% 부하
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True, "node_id": "node2"}
            
            # 부하이 낮은 노드로 자동 라우팅
            result = await distributed_cache_service.set("load_balanced_key", "test_value")
            
            assert result is True
            mock_send.assert_called_once()
            
            # 부하이 낮은 노드로 라우팅되었는지 확인
            call_args = mock_send.call_args[0][0]
            assert call_args["node_id"] == "node2"  # 부하이 낮은 노드
    
    @pytest.mark.asyncio
    async def test_cache_statistics_aggregation(self, distributed_cache_service, mock_cache_nodes):
        """캐시 통계 집계 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        
        with patch('backend.services.distributed_cache.get_node_statistics') as mock_stats:
            mock_stats.side_effect = [
                {
                    "node_id": "node1",
                    "hit_rate": 85.3,
                    "miss_rate": 14.7,
                    "total_requests": 10000,
                    "memory_usage": 60.5,
                    "cpu_usage": 45.2
                },
                {
                    "node_id": "node2",
                    "hit_rate": 82.7,
                    "miss_rate": 17.3,
                    "total_requests": 8000,
                    "memory_usage": 55.8,
                    "cpu_usage": 40.1
                }
            ]
            
            stats = await distributed_cache_service.get_aggregated_statistics()
            
            assert stats is not None
            assert stats["total_nodes"] == 2
            assert stats["average_hit_rate"] == (85.3 + 82.7) / 2
            assert stats["average_miss_rate"] == (14.7 + 17.3) / 2
            assert stats["total_requests"] == 18000
            assert stats["average_memory_usage"] == (60.5 + 55.8) / 2
            assert stats["average_cpu_usage"] == (45.2 + 40.1) / 2
    
    @pytest.mark.asyncio
    async def test_cache_warmup(self, distributed_cache_service, mock_cache_nodes):
        """캐시 웜업 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        
        warmup_data = [
            {"key": f"warmup_key_{i}", "value": f"warmup_value_{i}"}
            for i in range(100)
        ]
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True}
            
            result = await distributed_cache_service.warmup_cache(warmup_data)
            
            assert result is True
            assert mock_send.call_count == 200  # 100 keys * 2 nodes (replication)
            
            # 모든 웜업 데이터가 설정되었는지 확인
            set_keys = set()
            for call_args in mock_send.call_args_list:
                if call_args[0]["command"] == "SET":
                    set_keys.add(call_args[0]["key"])
            
            for i in range(100):
                assert f"warmup_key_{i}" in set_keys
    
    @pytest.mark.asyncio
    async def test_cache_eviction_policy(self, distributed_cache_service, mock_cache_nodes):
        """캐시 제거 정책 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True}
            
            # LRU 제거 정책으로 테스트
            result = await distributed_cache_service.set(
                key="eviction_test_key",
                value="eviction_test_value",
                ttl=3600,
                eviction_policy="LRU"
            )
            
            assert result is True
            mock_send.assert_called_once()
            
            # 제거 정책이 설정되었는지 확인
            call_args = mock_send.call_args[0][0]
            assert call_args["eviction_policy"] == "LRU"
    
    @pytest.mark.asyncio
    async def test_cache_backup_and_restore(self, distributed_cache_service, mock_cache_nodes):
        """캐시 백업 및 복원 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        
        with patch('backend.services.distributed_cache.create_cache_backup') as mock_backup, \
             patch('backend.services.distributed_cache.restore_cache_backup') as mock_restore:
            
            mock_backup.return_value = {
                "success": True,
                "backup_id": "backup_123",
                "timestamp": time.time(),
                "node_count": 2
            }
            
            mock_restore.return_value = {
                "success": True,
                "restored_keys": 50,
                "backup_id": "backup_123"
            }
            
            # 백업 생성
            backup_result = await distributed_cache_service.create_backup()
            
            assert backup_result is True
            assert backup_result["success"] is True
            assert backup_result["backup_id"] == "backup_123"
            mock_backup.assert_called_once()
            
            # 백업 복원
            restore_result = await distributed_cache_service.restore_backup("backup_123")
            
            assert restore_result is True
            assert restore_result["success"] is True
            assert restore_result["restored_keys"] == 50
            mock_restore.assert_called_once_with("backup_123")
    
    @pytest.mark.asyncio
    async def test_cache_performance_monitoring(self, distributed_cache_service, mock_cache_nodes):
        """캐시 성능 모니터링 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        
        with patch('backend.services.distributed_cache.measure_operation_latency') as mock_latency:
            mock_latency.side_effect = [
                15.5,  # node1
                20.2,  # node1
                12.8,  # node1
                18.3,  # node2
                25.1   # node2
            ]
            
            # 성능 측정
            performance_data = await distributed_cache_service.measure_performance(
                operations=100,
                operation_type="GET"
            )
            
            assert performance_data is not None
            assert performance_data["total_operations"] == 100
            assert performance_data["average_latency"] == (15.5 + 20.2 + 12.8 + 18.3 + 25.1) / 5
            assert performance_data["min_latency"] == 12.8
            assert performance_data["max_latency"] == 25.1
            assert performance_data["p95_latency"] is not None
            assert performance_data["p99_latency"] is not None
    
    def test_consistent_hash_ring_rebalancing(self, distributed_cache_service, mock_cache_nodes):
        """일관성 해시 링 리밸런싱 테스트"""
        # 초기 노드 설정
        initial_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service.cache_nodes = initial_nodes
        distributed_cache_service._build_consistent_hash_ring()
        
        initial_ring_size = len(distributed_cache_service.consistent_hash_ring)
        
        # 노드 추가
        new_node = CacheNode(
            node_id="node4",
            host="localhost",
            port=7004,
            status=CacheStatus.ACTIVE,
            last_heartbeat=time.time(),
            memory_usage=50.0,
            cpu_usage=35.0,
            cache_size=1024 * 1024 * 1024,  # 1GB
            hit_rate=90.0
        )
        
        distributed_cache_service.add_node_to_ring(new_node)
        
        # 리밸런싱 후 링 크기 확인
        assert len(distributed_cache_service.consistent_hash_ring) > initial_ring_size
        
        # 키 분배 확인
        test_keys = ["key1", "key2", "key3", "key4", "key5"]
        new_distribution = {}
        
        for key in test_keys:
            node = distributed_cache_service._get_node_for_key(key)
            node_id = node.node_id
            new_distribution[node_id] = new_distribution.get(node_id, 0) + 1
        
        # 새 노드로 일부 키가 재분배되었는지 확인
        assert "node4" in new_distribution
        assert new_distribution["node4"] > 0
    
    @pytest.mark.asyncio
    async def test_distributed_cache_concurrent_operations(self, distributed_cache_service, mock_cache_nodes):
        """분산 캐시 동시 작업 테스트"""
        distributed_cache_service.cache_nodes = [node for node in mock_cache_nodes if node.status == CacheStatus.ACTIVE]
        distributed_cache_service._build_consistent_hash_ring()
        
        with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
            mock_send.return_value = {"success": True}
            
            # 동시 작업 실행
            async def concurrent_operation(key_suffix):
                return await distributed_cache_service.set(
                    f"concurrent_key_{key_suffix}",
                    f"concurrent_value_{key_suffix}",
                    ttl=3600
                )
            
            # 50개 동시 작업
            tasks = [concurrent_operation(i) for i in range(50)]
            results = await asyncio.gather(*tasks)
            
            # 모든 작업이 성공했는지 확인
            assert all(results) is True
            assert mock_send.call_count == 50
            
            # 키 분배 확인
            node_distribution = {}
            for call_args in mock_send.call_args_list:
                node_id = call_args[0]["node_id"]
                node_distribution[node_id] = node_distribution.get(node_id, 0) + 1
            
            # 분배가 비교적 균등한지 확인
            total_operations = sum(node_distribution.values())
            for node_id, count in node_distribution.items():
                ratio = count / total_operations
                assert 0.3 <= ratio <= 0.7  # 30-70% 범위 내
    
    def test_distributed_cache_configuration(self, distributed_cache_service):
        """분산 캐시 구성 테스트"""
        # 사용자 정의 구성
        config = {
            "replication_factor": 2,
            "consistency_level": "EVENTUAL",
            "eviction_policy": "LRU",
            "max_memory_per_node": 1024 * 1024 * 1024,  # 1GB
            "health_check_interval": 30,
            "node_timeout": 5,
            "retry_attempts": 3,
            "retry_delay": 0.1
        }
        
        distributed_cache_service.configure(config)
        
        assert distributed_cache_service.config["replication_factor"] == 2
        assert distributed_cache_service.config["consistency_level"] == "EVENTUAL"
        assert distributed_cache_service.config["eviction_policy"] == "LRU"
        assert distributed_cache_service.config["max_memory_per_node"] == 1024 * 1024 * 1024
        assert distributed_cache_service.config["health_check_interval"] == 30
        assert distributed_cache_service.config["node_timeout"] == 5
        assert distributed_cache_service.config["retry_attempts"] == 3
        assert distributed_cache_service.config["retry_delay"] == 0.1
    
    def test_distributed_cache_error_handling(self, distributed_cache_service):
        """분산 캐시 오류 처리 테스트"""
        # 다양한 오류 시나리오
        error_scenarios = [
            {"error": "Connection timeout", "retryable": True},
            {"error": "Node not found", "retryable": False},
            {"error": "Memory limit exceeded", "retryable": True},
            {"error": "Invalid key format", "retryable": False}
        ]
        
        for scenario in error_scenarios:
            with patch('backend.services.distributed_cache.send_cache_command') as mock_send:
                mock_send.return_value = {
                    "success": False,
                    "error": scenario["error"],
                    "retryable": scenario["retryable"]
                }
                
                # 오류 처리 확인
                error_result = distributed_cache_service._handle_cache_error(scenario)
                
                if scenario["retryable"]:
                    assert error_result["should_retry"] is True
                    assert error_result["retry_delay"] > 0
                else:
                    assert error_result["should_retry"] is False
                    assert error_result["retry_delay"] == 0