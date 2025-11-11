"""
분산 캐시 시스템 모듈
일관성 해시 링, 노드 간 데이터 분산, 장애 조치 및 복구 기능 제공
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import redis.asyncio as redis
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class CacheNode:
    """캐시 노드 모델"""
    node_id: str
    host: str
    port: int
    weight: int = 1
    status: str = "active"  # active, inactive, failed
    last_health_check: Optional[datetime] = None
    failure_count: int = 0
    max_failures: int = 3
    
    def __post_init__(self):
        if not self.last_health_check:
            self.last_health_check = datetime.utcnow()

@dataclass
class CacheStats:
    """분산 캐시 통계 모델"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    node_failures: int = 0
    data_replications: int = 0
    avg_response_time: float = 0.0
    active_nodes: int = 0
    total_nodes: int = 0

class DistributedCacheManager:
    """분산 캐시 관리자 클래스"""
    
    def __init__(
        self,
        redis_nodes: List[str],
        replication_factor: int = 2,
        virtual_nodes: int = 160,
        health_check_interval: int = 30
    ):
        self.redis_nodes = redis_nodes
        self.replication_factor = replication_factor
        self.virtual_nodes = virtual_nodes
        self.health_check_interval = health_check_interval
        
        # 노드 관리
        self.nodes: Dict[str, CacheNode] = {}
        self.node_clients: Dict[str, redis.Redis] = {}
        
        # 일관성 해시 링
        self.hash_ring: Dict[int, str] = {}
        self.sorted_hashes: List[int] = []
        
        # 상태 관리
        self.running = False
        self.lock = asyncio.Lock()
        
        # 통계 정보
        self.stats = CacheStats()
        
        # 장애 조치 설정
        self.failure_threshold = 3
        self.recovery_timeout = 300  # 5분
        
        # 데이터 일관성 설정
        self.consistency_level = "eventual"  # eventual, strong
        self.read_preference = "master"  # master, nearest, any
    
    async def initialize(self):
        """분산 캐시 관리자 초기화"""
        try:
            # 노드 초기화
            await self._initialize_nodes()
            
            # 해시 링 생성
            self._create_consistent_hash_ring()
            
            # 상태 확인
            await self._perform_initial_health_check()
            
            logger.info("Distributed Cache Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Distributed Cache Manager: {str(e)}")
            raise
    
    async def start(self):
        """분산 캐시 관리자 시작"""
        if not self.nodes:
            await self.initialize()
        
        self.running = True
        
        # 상태 확인 스케줄러 시작
        asyncio.create_task(self._health_check_scheduler())
        
        # 통계 수집기 시작
        asyncio.create_task(self._stats_collector())
        
        logger.info("Distributed Cache Manager started")
    
    async def stop(self):
        """분산 캐시 관리자 중지"""
        self.running = False
        
        # 모든 Redis 클라이언트 종료
        for client in self.node_clients.values():
            await client.close()
        
        self.node_clients.clear()
        
        logger.info("Distributed Cache Manager stopped")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        분산 캐시에서 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        start_time = time.time()
        
        try:
            async with self.lock:
                self.stats.total_requests += 1
            
            # 노드 선택
            nodes = await self._get_nodes_for_key(key)
            
            if not nodes:
                logger.warning(f"No available nodes for key: {key}")
                self.stats.cache_misses += 1
                return None
            
            # 읽기 전략에 따른 노드 선택
            read_nodes = await self._select_read_nodes(nodes)
            
            # 노드에서 데이터 조회
            for node_id in read_nodes:
                try:
                    data = await self._get_from_node(node_id, key)
                    if data:
                        self.stats.cache_hits += 1
                        
                        # 응답 시간 기록
                        response_time = time.time() - start_time
                        self._update_response_time(response_time)
                        
                        logger.debug(f"Cache hit for key {key} from node {node_id}")
                        return data
                        
                except Exception as e:
                    logger.error(f"Error getting key {key} from node {node_id}: {str(e)}")
                    await self._handle_node_failure(node_id)
            
            # 모든 노드에서 조회 실패
            self.stats.cache_misses += 1
            logger.debug(f"Cache miss for key: {key}")
            
            # 응답 시간 기록
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in distributed get for {key}: {str(e)}")
            self.stats.cache_misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        분산 캐시에 데이터 저장
        
        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초)
            
        Returns:
            성공 여부
        """
        try:
            # 노드 선택
            nodes = await self._get_nodes_for_key(key)
            
            if not nodes:
                logger.error(f"No available nodes for key: {key}")
                return False
            
            # 복제 전략에 따른 저장
            success_count = 0
            required_success = min(len(nodes), self.replication_factor)
            
            for node_id in nodes[:required_success]:
                try:
                    success = await self._set_to_node(node_id, key, value, ttl)
                    if success:
                        success_count += 1
                        self.stats.data_replications += 1
                    else:
                        await self._handle_node_failure(node_id)
                        
                except Exception as e:
                    logger.error(f"Error setting key {key} to node {node_id}: {str(e)}")
                    await self._handle_node_failure(node_id)
            
            # 성공 여부 확인
            if success_count >= required_success:
                logger.debug(f"Successfully set key {key} to {success_count} nodes")
                return True
            else:
                logger.error(f"Failed to set key {key} to required nodes ({success_count}/{required_success})")
                return False
                
        except Exception as e:
            logger.error(f"Error in distributed set for {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        분산 캐시에서 데이터 삭제
        
        Args:
            key: 캐시 키
            
        Returns:
            성공 여부
        """
        try:
            # 노드 선택
            nodes = await self._get_nodes_for_key(key)
            
            if not nodes:
                logger.error(f"No available nodes for key: {key}")
                return False
            
            # 모든 노드에서 삭제
            success_count = 0
            
            for node_id in nodes:
                try:
                    success = await self._delete_from_node(node_id, key)
                    if success:
                        success_count += 1
                    else:
                        await self._handle_node_failure(node_id)
                        
                except Exception as e:
                    logger.error(f"Error deleting key {key} from node {node_id}: {str(e)}")
                    await self._handle_node_failure(node_id)
            
            # 성공 여부 확인
            if success_count > 0:
                logger.debug(f"Successfully deleted key {key} from {success_count} nodes")
                return True
            else:
                logger.error(f"Failed to delete key {key} from any node")
                return False
                
        except Exception as e:
            logger.error(f"Error in distributed delete for {key}: {str(e)}")
            return False
    
    async def add_node(self, node_id: str, host: str, port: int, weight: int = 1) -> bool:
        """
        캐시 노드 추가
        
        Args:
            node_id: 노드 ID
            host: 호스트 주소
            port: 포트
            weight: 가중치
            
        Returns:
            성공 여부
        """
        try:
            async with self.lock:
                if node_id in self.nodes:
                    logger.warning(f"Node {node_id} already exists")
                    return False
                
                # 노드 생성
                node = CacheNode(
                    node_id=node_id,
                    host=host,
                    port=port,
                    weight=weight
                )
                
                # Redis 클라이언트 생성
                redis_url = f"redis://{host}:{port}"
                client = redis.from_url(redis_url)
                
                # 연결 테스트
                await client.ping()
                
                # 노드 및 클라이언트 저장
                self.nodes[node_id] = node
                self.node_clients[node_id] = client
                
                # 해시 링 업데이트
                self._add_node_to_hash_ring(node)
                
                logger.info(f"Added node {node_id} ({host}:{port})")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add node {node_id}: {str(e)}")
            return False
    
    async def remove_node(self, node_id: str) -> bool:
        """
        캐시 노드 제거
        
        Args:
            node_id: 노드 ID
            
        Returns:
            성공 여부
        """
        try:
            async with self.lock:
                if node_id not in self.nodes:
                    logger.warning(f"Node {node_id} not found")
                    return False
                
                # Redis 클라이언트 종료
                if node_id in self.node_clients:
                    await self.node_clients[node_id].close()
                    del self.node_clients[node_id]
                
                # 노드 제거
                del self.nodes[node_id]
                
                # 해시 링 업데이트
                self._remove_node_from_hash_ring(node_id)
                
                logger.info(f"Removed node {node_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove node {node_id}: {str(e)}")
            return False
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        분산 캐시 통계 정보 조회
        
        Returns:
            캐시 통계
        """
        async with self.lock:
            hit_rate = (
                self.stats.cache_hits / self.stats.total_requests * 100
                if self.stats.total_requests > 0 else 0
            )
            
            active_nodes = len([
                node for node in self.nodes.values()
                if node.status == "active"
            ])
            
            return {
                "total_requests": self.stats.total_requests,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses,
                "hit_rate": hit_rate,
                "node_failures": self.stats.node_failures,
                "data_replications": self.stats.data_replications,
                "avg_response_time": self.stats.avg_response_time,
                "active_nodes": active_nodes,
                "total_nodes": len(self.nodes),
                "replication_factor": self.replication_factor,
                "virtual_nodes": self.virtual_nodes,
                "running": self.running
            }
    
    async def _initialize_nodes(self):
        """노드 초기화"""
        for node_config in self.redis_nodes:
            try:
                # 노드 설정 파싱
                if isinstance(node_config, str):
                    # "host:port" 형식
                    host, port = node_config.split(":")
                    node_id = f"{host}:{port}"
                    weight = 1
                elif isinstance(node_config, dict):
                    # 딕셔너리 형식
                    node_id = node_config["node_id"]
                    host = node_config["host"]
                    port = node_config["port"]
                    weight = node_config.get("weight", 1)
                else:
                    continue
                
                # 노드 추가
                await self.add_node(node_id, host, port, weight)
                
            except Exception as e:
                logger.error(f"Failed to initialize node {node_config}: {str(e)}")
    
    def _create_consistent_hash_ring(self):
        """일관성 해시 링 생성"""
        self.hash_ring = {}
        
        for node in self.nodes.values():
            self._add_node_to_hash_ring(node)
        
        # 해시 정렬
        self.sorted_hashes = sorted(self.hash_ring.keys())
    
    def _add_node_to_hash_ring(self, node: CacheNode):
        """노드를 해시 링에 추가"""
        for i in range(self.virtual_nodes):
            # 가상 노드 이름 생성
            virtual_node_name = f"{node.node_id}:{i}"
            
            # 해시 계산
            hash_value = int(hashlib.md5(virtual_node_name.encode()).hexdigest(), 16)
            
            # 해시 링에 추가
            self.hash_ring[hash_value] = node.node_id
        
        # 해시 정렬
        self.sorted_hashes = sorted(self.hash_ring.keys())
    
    def _remove_node_from_hash_ring(self, node_id: str):
        """노드를 해시 링에서 제거"""
        # 해당 노드의 모든 가상 노드 제거
        hashes_to_remove = []
        
        for hash_value, node in self.hash_ring.items():
            if node == node_id:
                hashes_to_remove.append(hash_value)
        
        for hash_value in hashes_to_remove:
            del self.hash_ring[hash_value]
        
        # 해시 정렬
        self.sorted_hashes = sorted(self.hash_ring.keys())
    
    async def _get_nodes_for_key(self, key: str) -> List[str]:
        """키에 대한 노드 목록 가져오기"""
        try:
            if not self.sorted_hashes:
                return []
            
            # 키 해시 계산
            key_hash = int(hashlib.md5(key.encode()).hexdigest(), 16)
            
            # 시계 방향으로 다음 노드 찾기
            for hash_value in self.sorted_hashes:
                if hash_value >= key_hash:
                    node_id = self.hash_ring[hash_value]
                    if node_id in self.nodes and self.nodes[node_id].status == "active":
                        return await self._get_replication_nodes(node_id)
            
            # 랩어라운드
            first_hash = self.sorted_hashes[0]
            node_id = self.hash_ring[first_hash]
            
            if node_id in self.nodes and self.nodes[node_id].status == "active":
                return await self._get_replication_nodes(node_id)
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting nodes for key {key}: {str(e)}")
            return []
    
    async def _get_replication_nodes(self, primary_node_id: str) -> List[str]:
        """복제 노드 목록 가져오기"""
        nodes = [primary_node_id]
        
        # 복제 팩터만큼 추가 노드 선택
        current_index = self.sorted_hashes.index(
            next(h for h in self.sorted_hashes 
                  if self.hash_ring[h] == primary_node_id)
        )
        
        added_nodes = 0
        checked_nodes = set([primary_node_id])
        
        while added_nodes < self.replication_factor - 1:
            current_index = (current_index + 1) % len(self.sorted_hashes)
            hash_value = self.sorted_hashes[current_index]
            node_id = self.hash_ring[hash_value]
            
            # 활성 노드이고 아직 추가되지 않은 경우
            if (node_id in self.nodes and 
                self.nodes[node_id].status == "active" and 
                node_id not in checked_nodes):
                
                nodes.append(node_id)
                checked_nodes.add(node_id)
                added_nodes += 1
            
            # 모든 노드를 확인한 경우
            if len(checked_nodes) >= len(self.nodes):
                break
        
        return nodes
    
    async def _select_read_nodes(self, nodes: List[str]) -> List[str]:
        """읽기 전략에 따른 노드 선택"""
        if self.read_preference == "master":
            # 첫 번째 노드만 사용
            return [nodes[0]] if nodes else []
        elif self.read_preference == "nearest":
            # 가장 가까운 노드 (현재는 첫 번째 노드)
            return [nodes[0]] if nodes else []
        else:  # any
            # 모든 노드 사용
            return nodes
    
    async def _get_from_node(self, node_id: str, key: str) -> Optional[Any]:
        """특정 노드에서 데이터 조회"""
        try:
            if node_id not in self.node_clients:
                return None
            
            client = self.node_clients[node_id]
            data = await client.get(key)
            
            if data:
                return json.loads(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting from node {node_id}: {str(e)}")
            raise
    
    async def _set_to_node(self, node_id: str, key: str, value: Any, ttl: int) -> bool:
        """특정 노드에 데이터 저장"""
        try:
            if node_id not in self.node_clients:
                return False
            
            client = self.node_clients[node_id]
            serialized_value = json.dumps(value)
            
            await client.setex(key, ttl, serialized_value)
            return True
            
        except Exception as e:
            logger.error(f"Error setting to node {node_id}: {str(e)}")
            raise
    
    async def _delete_from_node(self, node_id: str, key: str) -> bool:
        """특정 노드에서 데이터 삭제"""
        try:
            if node_id not in self.node_clients:
                return False
            
            client = self.node_clients[node_id]
            result = await client.delete(key)
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting from node {node_id}: {str(e)}")
            raise
    
    async def _perform_initial_health_check(self):
        """초기 상태 확인"""
        for node_id in list(self.nodes.keys()):
            await self._check_node_health(node_id)
    
    async def _health_check_scheduler(self):
        """상태 확인 스케줄러"""
        while self.running:
            try:
                for node_id in list(self.nodes.keys()):
                    await self._check_node_health(node_id)
                
                # 상태 확인 간격만큼 대기
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check scheduler: {str(e)}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _check_node_health(self, node_id: str):
        """노드 상태 확인"""
        try:
            if node_id not in self.node_clients:
                return
            
            client = self.node_clients[node_id]
            await client.ping()
            
            # 상태 업데이트
            node = self.nodes[node_id]
            node.status = "active"
            node.last_health_check = datetime.utcnow()
            node.failure_count = 0
            
        except Exception as e:
            logger.error(f"Health check failed for node {node_id}: {str(e)}")
            await self._handle_node_failure(node_id)
    
    async def _handle_node_failure(self, node_id: str):
        """노드 장애 처리"""
        try:
            if node_id not in self.nodes:
                return
            
            node = self.nodes[node_id]
            node.failure_count += 1
            node.last_health_check = datetime.utcnow()
            
            # 장애 임계값 확인
            if node.failure_count >= self.failure_threshold:
                node.status = "failed"
                self.stats.node_failures += 1
                
                logger.warning(f"Node {node_id} marked as failed after {node.failure_count} failures")
                
                # 해시 링에서 제거
                self._remove_node_from_hash_ring(node_id)
                
                # 복구 스케줄링
                asyncio.create_task(self._schedule_node_recovery(node_id))
            
        except Exception as e:
            logger.error(f"Error handling node failure for {node_id}: {str(e)}")
    
    async def _schedule_node_recovery(self, node_id: str):
        """노드 복구 스케줄링"""
        try:
            # 복구 시간만큼 대기
            await asyncio.sleep(self.recovery_timeout)
            
            if not self.running:
                return
            
            # 복구 시도
            await self._attempt_node_recovery(node_id)
            
        except Exception as e:
            logger.error(f"Error in node recovery scheduling for {node_id}: {str(e)}")
    
    async def _attempt_node_recovery(self, node_id: str):
        """노드 복구 시도"""
        try:
            if node_id not in self.nodes:
                return
            
            # 상태 확인
            await self._check_node_health(node_id)
            
            node = self.nodes[node_id]
            if node.status == "active":
                # 복구 성공
                self._add_node_to_hash_ring(node)
                logger.info(f"Node {node_id} recovered and added back to hash ring")
            else:
                # 복구 실패, 재시도
                await self._schedule_node_recovery(node_id)
                
        except Exception as e:
            logger.error(f"Error in node recovery attempt for {node_id}: {str(e)}")
    
    def _update_response_time(self, response_time: float):
        """응답 시간 업데이트"""
        if self.stats.total_requests == 0:
            self.stats.avg_response_time = response_time
        else:
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.total_requests - 1) + response_time) /
                self.stats.total_requests
            )
    
    async def _stats_collector(self):
        """통계 수집기"""
        while self.running:
            try:
                async with self.lock:
                    active_nodes = len([
                        node for node in self.nodes.values()
                        if node.status == "active"
                    ])
                    
                    self.stats.active_nodes = active_nodes
                    self.stats.total_nodes = len(self.nodes)
                
                # 1분마다 수집
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in stats collector: {str(e)}")
                await asyncio.sleep(60)

# 전역 분산 캐시 관리자 인스턴스
distributed_cache_manager = DistributedCacheManager([])


class DistributedCacheService:
    """분산 캐시 서비스 클래스"""
    
    def __init__(self, cache_manager: DistributedCacheManager = None):
        self.cache_manager = cache_manager or distributed_cache_manager
    
    async def get(self, key: str) -> Optional[Any]:
        """분산 캐시에서 데이터 조회"""
        return await self.cache_manager.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """분산 캐시에 데이터 저장"""
        return await self.cache_manager.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """분산 캐시에서 데이터 삭제"""
        return await self.cache_manager.delete(key)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """분산 캐시 통계 정보 조회"""
        return await self.cache_manager.get_cache_statistics()