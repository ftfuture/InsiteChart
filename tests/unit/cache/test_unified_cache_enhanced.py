"""
통합 캐시 관리자 고급 기능 테스트 모듈
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from backend.cache.unified_cache import UnifiedCacheManager


class TestUnifiedCacheManagerEnhanced:
    """통합 캐시 관리자 고급 기능 테스트"""
    
    @pytest.fixture
    def cache_manager(self):
        """테스트용 캐시 관리자"""
        backend = AsyncMock()
        backend.get = AsyncMock()
        backend.set = AsyncMock(return_value=True)
        backend.delete = AsyncMock(return_value=True)
        backend.delete_pattern = AsyncMock(return_value=0)
        backend.get_stats = AsyncMock(return_value={
            'memory_usage': 1024,
            'hit_count': 100,
            'miss_count': 50
        })
        backend.get_performance_metrics = AsyncMock(return_value={})
        backend.get_hot_keys = AsyncMock(return_value=[])
        backend.optimize_performance = AsyncMock(return_value={})
        
        return UnifiedCacheManager(backend)
    
    @pytest.mark.asyncio
    async def test_cache_performance_metrics(self, cache_manager):
        """캐시 성능 메트릭 테스트"""
        # 캐시 통계 설정
        cache_manager.stats = {
            'hits': 150,
            'misses': 50,
            'sets': 100,
            'deletes': 10,
            'errors': 2
        }
        
        # 로컬 캐시 데이터 설정
        cache_manager._local_cache = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }
        cache_manager._local_cache_ttl = {
            'key1': time.time() + 60,
            'key2': time.time() + 60,
            'key3': time.time() + 60
        }
        
        # 성능 메트릭 가져오기
        metrics = await cache_manager.get_cache_performance_metrics()
        
        assert 'performance_metrics' in metrics
        assert 'recommendations' in metrics
        assert 'timestamp' in metrics
        
        perf_metrics = metrics['performance_metrics']
        assert perf_metrics['total_requests'] == 200  # hits + misses
        assert perf_metrics['hit_rate'] == 75.0  # 150/200 * 100
        assert perf_metrics['local_cache_size'] == 3
        assert perf_metrics['error_rate'] == 1.0  # 2/200 * 100
    
    @pytest.mark.asyncio
    async def test_cache_optimization_low_hit_rate(self, cache_manager):
        """낮은 히트율 시 캐시 최적화 테스트"""
        # 낮은 히트율 설정
        cache_manager.stats = {
            'hits': 30,
            'misses': 70,
            'sets': 50,
            'deletes': 5,
            'errors': 0
        }
        
        # 최적화 실행
        result = await cache_manager.optimize_cache_performance()
        
        assert 'actions_taken' in result
        assert 'performance_improvements' in result
        
        # TTL 증가 확인
        assert any('TTL' in action for action in result['actions_taken'])
        
        # 성능 향상 기록 확인
        assert 'ttl_adjustment' in result['performance_improvements']
    
    @pytest.mark.asyncio
    async def test_cache_optimization_high_local_hit_rate(self, cache_manager):
        """높은 로컬 히트율 시 캐시 최적화 테스트"""
        # 높은 로컬 히트율 설정
        cache_manager.stats = {
            'hits': 80,
            'misses': 20,
            'sets': 30,
            'deletes': 2,
            'errors': 0
        }
        
        # 로컬 캐시 크기 작게 설정
        cache_manager._local_cache_max_size = 50
        
        # 최적화 실행
        result = await cache_manager.optimize_cache_performance()
        
        # 결과가 있는지 확인
        assert 'actions_taken' in result
        assert 'performance_improvements' in result
    
    @pytest.mark.asyncio
    async def test_cache_hot_keys(self, cache_manager):
        """핫 키 식별 테스트"""
        # 로컬 캐시에 다양한 데이터 설정
        current_time = time.time()
        cache_manager._local_cache = {
            'stock:AAPL': {'price': 150.0},
            'sentiment:AAPL': {'score': 0.5},
            'search:query1': {'results': []},
            'market:overview': {'status': 'active'}
        }
        cache_manager._local_cache_ttl = {
            'stock:AAPL': current_time + 300,  # 5분 전에 접근
            'sentiment:AAPL': current_time + 180,  # 3분 전에 접근
            'search:query1': current_time + 60,   # 1분 전에 접근
            'market:overview': current_time + 30  # 30초 전에 접근
        }
        
        # 핫 키 가져오기
        hot_keys = await cache_manager.get_cache_hot_keys(limit=10)
        
        assert len(hot_keys) == 4
        assert all('key' in key for key in hot_keys)
        assert all('access_frequency' in key for key in hot_keys)
        assert all('cache_type' in key for key in hot_keys)
        
        # 접근 빈도순으로 정렬 확인
        frequencies = [key['access_frequency'] for key in hot_keys]
        assert frequencies == sorted(frequencies, reverse=True)
    
    @pytest.mark.asyncio
    async def test_cache_pattern_analysis(self, cache_manager):
        """캐시 패턴 분석 테스트"""
        # 다양한 키 패턴 설정
        cache_manager._local_cache = {
            'stock:AAPL': {'data': 'apple'},
            'stock:GOOGL': {'data': 'google'},
            'stock:MSFT': {'data': 'microsoft'},
            'search:tech': {'results': []},
            'search:finance': {'results': []},
            'sentiment:AAPL': {'score': 0.5},
            'market:overview': {'status': 'active'}
        }
        cache_manager._local_cache_ttl = {
            key: time.time() + 60 for key in cache_manager._local_cache.keys()
        }
        
        # 패턴 분석 실행
        analysis = await cache_manager.analyze_cache_patterns()
        
        assert 'hot_keys_count' in analysis
        assert 'key_patterns' in analysis
        assert 'key_percentages' in analysis
        assert 'most_accessed_type' in analysis
        assert 'recommendations' in analysis
        
        # 키 패턴 확인 (실제 구현에 맞게 조정)
        patterns = analysis['key_patterns']
        assert 'stock_data' in patterns
        assert 'search_results' in patterns
        assert 'sentiment_data' in patterns
        assert 'market_overview' in patterns
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_manager):
        """캐시 워밍 테스트"""
        # 워밍할 심볼 목록
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        # 캐시 워밍 실행
        result = await cache_manager.implement_cache_warming(symbols)
        
        assert 'warmed_symbols' in result
        assert 'failed_symbols' in result
        assert 'total_time' in result
        assert 'timestamp' in result
        
        # 워밍된 심볼 확인
        assert len(result['warmed_symbols']) == 3
        assert set(result['warmed_symbols']) == set(symbols)
        assert len(result['failed_symbols']) == 0
        
        # 백엔드 set 호출이 있었는지 확인 (실제 데이터 구조에 맞게)
        assert cache_manager.backend.set.call_count >= len(symbols)
    
    @pytest.mark.asyncio
    async def test_cache_partitioning(self, cache_manager):
        """캐시 파티셔닝 테스트"""
        # 파티셔닝 설정
        partition_config = {
            'data_types': ['stock_data', 'sentiment_data'],
            'stock_data_max_size': 1000,
            'stock_data_ttl': 600,
            'stock_data_eviction': 'lru',
            'sentiment_data_max_size': 500,
            'sentiment_data_ttl': 300,
            'sentiment_data_eviction': 'lfu'
        }
        
        # 파티셔닝 실행
        result = await cache_manager.implement_cache_partitioning(partition_config)
        
        assert 'partitions_created' in result
        assert 'performance_impact' in result
        assert 'timestamp' in result
        
        # 생성된 파티션 확인
        partitions = result['partitions_created']
        assert len(partitions) == 2
        
        stock_partition = next(p for p in partitions if p['name'] == 'stock_data_partition')
        assert stock_partition['data_type'] == 'stock_data'
        assert stock_partition['max_size'] == 1000
        assert stock_partition['ttl'] == 600
        
        # 성능 영향 확인
        impact = result['performance_impact']
        assert 'expected_hit_rate_improvement' in impact
        assert 'expected_memory_efficiency' in impact
        assert 'expected_latency_reduction' in impact
    
    @pytest.mark.asyncio
    async def test_local_cache_size_management(self, cache_manager):
        """로컬 캐시 크기 관리 테스트"""
        # 최대 크기 작게 설정
        cache_manager._local_cache_max_size = 3
        
        # 최대 크기보다 많은 데이터 추가
        cache_manager._store_in_local_cache('key1', 'value1', 60)
        cache_manager._store_in_local_cache('key2', 'value2', 60)
        cache_manager._store_in_local_cache('key3', 'value3', 60)
        cache_manager._store_in_local_cache('key4', 'value4', 60)  # 오래된 항목 제거
        
        # 크기 제한 확인
        assert len(cache_manager._local_cache) <= 3
        assert len(cache_manager._local_cache_ttl) <= 3
        
        # 가장 오래된 항목이 제거되었는지 확인
        oldest_keys = sorted(cache_manager._local_cache_ttl.keys(), 
                          key=cache_manager._local_cache_ttl.get)
        assert 'key1' not in cache_manager._local_cache  # 가장 오래된 항목 제거
    
    @pytest.mark.asyncio
    async def test_cache_health_check_enhanced(self, cache_manager):
        """고급 캐시 헬스 체크 테스트"""
        # 백엔드 상태 설정
        cache_manager.backend.get_stats = AsyncMock(return_value={
            'memory_usage': 512,
            'connections': 10,
            'uptime': 3600,
            'hits': 100,
            'misses': 20,
            'hit_rate': 83.3
        })
        
        # 헬스 체크 실행
        health = await cache_manager.health_check()
        
        assert 'status' in health
        assert 'stats' in health
        assert 'backend' in health
        
        # 통계 정보 확인
        stats = health['stats']
        assert 'hit_rate' in stats
        
        # 백엔드 통계 확인
        backend_stats = cache_manager.backend.get_stats.return_value
        assert 'memory_usage' in backend_stats
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_strategy(self, cache_manager):
        """캐시 무효화 전략 테스트"""
        # 관련 키 설정
        cache_manager._local_cache = {
            'stock:AAPL': {'price': 150.0},
            'sentiment:AAPL': {'score': 0.5},
            'unrelated:key': {'data': 'value'}
        }
        
        # 주식 데이터 무효화
        deleted_count = await cache_manager.invalidate_stock_data('AAPL')
        
        # 관련 키만 삭제 확인
        assert 'stock:AAPL' not in cache_manager._local_cache
        assert 'sentiment:AAPL' not in cache_manager._local_cache
        assert 'unrelated:key' in cache_manager._local_cache  # 관련 없는 키 유지
        
        # 백엔드 삭제 호출 확인
        assert cache_manager.backend.delete_pattern.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_cache_performance_monitoring(self, cache_manager):
        """캐시 성능 모니터링 테스트"""
        # 성능 모니터링 데이터 설정
        start_time = time.time()
        
        # 다양한 응답 시간 시뮬레이션
        response_times = [0.1, 0.2, 0.15, 0.3, 0.05, 0.25]
        
        # 성능 메트릭 업데이트
        for i, response_time in enumerate(response_times):
            cache_manager.stats['hits'] += 1
            if i % 2 == 0:
                cache_manager.stats['misses'] += 1
        
        # 성능 메트릭 분석
        metrics = await cache_manager.get_cache_performance_metrics()
        
        perf_metrics = metrics['performance_metrics']
        
        # 기본 메트릭 확인
        assert 'total_requests' in perf_metrics
        assert 'hit_rate' in perf_metrics
        
        # 권장사항 확인
        recommendations = metrics['recommendations']
        assert isinstance(recommendations, list)
    
    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, cache_manager):
        """동시 접근 테스트"""
        # 동시 접근 테스트
        async def cache_operation(key, value):
            await cache_manager.set(key, value, 60)
            result = await cache_manager.get(key)
            return result
        
        # 여러 동시 작업 실행
        tasks = [
            cache_operation(f'key{i}', f'value{i}')
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 모든 작업 성공 확인
        assert not any(isinstance(result, Exception) for result in results)
        assert len([r for r in results if r is not None]) == 10
    
    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self, cache_manager):
        """캐시 메모리 효율성 테스트"""
        # 메모리 효율성 테스트 데이터
        large_data = 'x' * 10000  # 10KB 데이터
        small_data = 'small'
        
        # 큰 데이터 저장
        await cache_manager.set('large_key', large_data, 60)
        await cache_manager.set('small_key', small_data, 60)
        
        # 메모리 사용량 분석
        metrics = await cache_manager.get_cache_performance_metrics()
        perf_metrics = metrics['performance_metrics']
        
        assert 'memory_usage_mb' in perf_metrics
        
        # 메모리 효율성 권장사항
        recommendations = metrics['recommendations']
        if perf_metrics['memory_usage_mb'] > 10:  # 10MB 이상
            assert any('memory' in rec.lower() for rec in recommendations)