"""
IntelligentCacheManager 단위 테스트

지능형 캐시 관리자의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque

from backend.services.intelligent_cache_manager import (
    IntelligentCacheManager,
    AccessPattern,
    CacheWarmupTask,
    CacheStats
)


class TestAccessPattern:
    """AccessPattern 모델 테스트 클래스"""
    
    def test_access_pattern_creation(self):
        """AccessPattern 생성 테스트"""
        pattern = AccessPattern(
            key="test-key",
            frequency="high",
            pattern="periodic",
            avg_interval=60.5,
            std_dev=10.2,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.85
        )
        
        assert pattern.key == "test-key"
        assert pattern.frequency == "high"
        assert pattern.pattern == "periodic"
        assert pattern.avg_interval == 60.5
        assert pattern.std_dev == 10.2
        assert pattern.access_count == 10
        assert pattern.prediction_confidence == 0.85


class TestCacheWarmupTask:
    """CacheWarmupTask 모델 테스트 클래스"""
    
    def test_cache_warmup_task_creation(self):
        """CacheWarmupTask 생성 테스트"""
        task = CacheWarmupTask(
            key="test-key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="stock_loader",
            params={"symbol": "AAPL"}
        )
        
        assert task.key == "test-key"
        assert task.priority == 5
        assert task.data_loader == "stock_loader"
        assert task.params == {"symbol": "AAPL"}
        assert task.retry_count == 0
        assert task.max_retries == 3


class TestCacheStats:
    """CacheStats 모델 테스트 클래스"""
    
    def test_cache_stats_creation(self):
        """CacheStats 생성 테스트"""
        stats = CacheStats(
            total_requests=100,
            cache_hits=80,
            cache_misses=20,
            warmup_hits=15,
            prediction_accuracy=0.75,
            avg_response_time=0.25,
            memory_usage=1024
        )
        
        assert stats.total_requests == 100
        assert stats.cache_hits == 80
        assert stats.cache_misses == 20
        assert stats.warmup_hits == 15
        assert stats.prediction_accuracy == 0.75
        assert stats.avg_response_time == 0.25
        assert stats.memory_usage == 1024
    
    def test_cache_stats_defaults(self):
        """기본값 CacheStats 생성 테스트"""
        stats = CacheStats()
        
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.warmup_hits == 0
        assert stats.prediction_accuracy == 0.0
        assert stats.avg_response_time == 0.0
        assert stats.memory_usage == 0


class TestIntelligentCacheManager:
    """IntelligentCacheManager 테스트 클래스"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """모의 Redis 클라이언트"""
        client = AsyncMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.setex.return_value = True
        client.lpush.return_value = True
        client.ltrim.return_value = True
        client.expire.return_value = True
        client.keys.return_value = []
        client.info.return_value = {"used_memory": 1024}
        return client
    
    @pytest.fixture
    def intelligent_cache_manager(self, mock_redis_client):
        """IntelligentCacheManager 인스턴스"""
        return IntelligentCacheManager(
            redis_url="redis://localhost:6379",
            max_pattern_history=50,
            warmup_queue_size=100
        )
    
    @pytest.mark.asyncio
    async def test_initialize(self, intelligent_cache_manager, mock_redis_client):
        """지능형 캐시 관리자 초기화 테스트"""
        with patch('redis.asyncio.from_url', return_value=mock_redis_client):
            with patch.object(intelligent_cache_manager, '_load_access_patterns'):
                # 테스트 실행
                await intelligent_cache_manager.initialize()
                
                # 결과 검증
                assert intelligent_cache_manager.redis_client is not None
                assert intelligent_cache_manager.running is False  # start() 호출 전
                
                # 모의 호출 검증
                mock_redis_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, intelligent_cache_manager):
        """지능형 캐시 관리자 초기화 실패 테스트"""
        with patch('redis.asyncio.from_url', side_effect=Exception("Redis connection failed")):
            # 테스트 실행 및 예외 검증
            with pytest.raises(Exception):
                await intelligent_cache_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_start(self, intelligent_cache_manager):
        """지능형 캐시 관리자 시작 테스트"""
        with patch.object(intelligent_cache_manager, 'initialize'):
            # 테스트 실행
            await intelligent_cache_manager.start()
            
            # 결과 검증
            assert intelligent_cache_manager.running is True
    
    @pytest.mark.asyncio
    async def test_stop(self, intelligent_cache_manager):
        """지능형 캐시 관리자 중지 테스트"""
        # 설정
        intelligent_cache_manager.running = True
        
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        intelligent_cache_manager.warmup_tasks["task1"] = mock_task
        
        with patch.object(intelligent_cache_manager, '_save_access_patterns'):
            # 테스트 실행
            await intelligent_cache_manager.stop()
            
            # 결과 검증
            assert intelligent_cache_manager.running is False
            mock_task.cancel.assert_called_once()
    
    def test_register_data_loader(self, intelligent_cache_manager):
        """데이터 로더 등록 테스트"""
        # 테스트 실행
        def sample_loader(**kwargs):
            return {"data": "test"}
        
        intelligent_cache_manager.register_data_loader("test_loader", sample_loader)
        
        # 결과 검증
        assert "test_loader" in intelligent_cache_manager.data_loaders
        assert intelligent_cache_manager.data_loaders["test_loader"] == sample_loader
    
    @pytest.mark.asyncio
    async def test_get_with_predictive_warming_cache_hit(self, intelligent_cache_manager, mock_redis_client):
        """예측적 워밍과 함께 캐시 조회 (히트) 테스트"""
        # 설정
        mock_redis_client.get.return_value = json.dumps({"symbol": "AAPL", "price": 150.25})
        
        with patch.object(intelligent_cache_manager, '_record_access'):
            with patch.object(intelligent_cache_manager, '_analyze_access_pattern', return_value=None):
                with patch.object(intelligent_cache_manager, '_schedule_predictive_warming'):
                    # 테스트 실행
                    result = await intelligent_cache_manager.get_with_predictive_warming(
                        key="AAPL_stock_data",
                        data_type="stock_price"
                    )
                    
                    # 결과 검증
                    assert result is not None
                    assert result["symbol"] == "AAPL"
                    assert result["price"] == 150.25
                    
                    # 통계 검증
                    assert intelligent_cache_manager.stats.total_requests == 1
                    assert intelligent_cache_manager.stats.cache_hits == 1
                    assert intelligent_cache_manager.stats.cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_get_with_predictive_warming_cache_miss(self, intelligent_cache_manager, mock_redis_client):
        """예측적 워밍과 함께 캐시 조회 (미스) 테스트"""
        # 설정
        mock_redis_client.get.return_value = None
        
        sample_data = {"symbol": "AAPL", "price": 150.25}
        
        def sample_loader(**kwargs):
            return sample_data
        
        intelligent_cache_manager.register_data_loader("stock_loader", sample_loader)
        
        with patch.object(intelligent_cache_manager, '_record_access'):
            with patch.object(intelligent_cache_manager, '_analyze_access_pattern', return_value=None):
                with patch.object(intelligent_cache_manager, '_load_data', return_value=sample_data):
                    with patch.object(intelligent_cache_manager, '_determine_dynamic_ttl', return_value=300):
                        with patch.object(intelligent_cache_manager, '_save_to_cache'):
                            # 테스트 실행
                            result = await intelligent_cache_manager.get_with_predictive_warming(
                                key="AAPL_stock_data",
                                data_type="stock_price",
                                loader_name="stock_loader",
                                loader_params={"symbol": "AAPL"}
                            )
                            
                            # 결과 검증
                            assert result == sample_data
                            
                            # 통계 검증
                            assert intelligent_cache_manager.stats.total_requests == 1
                            assert intelligent_cache_manager.stats.cache_hits == 0
                            assert intelligent_cache_manager.stats.cache_misses == 1
                            
                            # 모의 호출 검증
                            intelligent_cache_manager._load_data.assert_called_once_with("stock_loader", {"symbol": "AAPL"})
                            intelligent_cache_manager._save_to_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_with_predictive_warming_no_loader(self, intelligent_cache_manager, mock_redis_client):
        """데이터 로더 없는 경우 예측적 워밍과 함께 캐시 조회 테스트"""
        # 설정
        mock_redis_client.get.return_value = None
        
        with patch.object(intelligent_cache_manager, '_record_access'):
            with patch.object(intelligent_cache_manager, '_analyze_access_pattern', return_value=None):
                # 테스트 실행
                result = await intelligent_cache_manager.get_with_predictive_warming(
                    key="AAPL_stock_data",
                    data_type="stock_price",
                    loader_name="nonexistent_loader"
                )
                
                # 결과 검증
                assert result is None
                
                # 통계 검증
                assert intelligent_cache_manager.stats.total_requests == 1
                assert intelligent_cache_manager.stats.cache_hits == 0
                assert intelligent_cache_manager.stats.cache_misses == 1
    
    @pytest.mark.asyncio
    async def test_preload_data_success(self, intelligent_cache_manager, mock_redis_client):
        """데이터 사전 로드 성공 테스트"""
        # 설정
        sample_data = {"symbol": "AAPL", "price": 150.25}
        
        def sample_loader(**kwargs):
            return sample_data
        
        intelligent_cache_manager.register_data_loader("stock_loader", sample_loader)
        
        with patch.object(intelligent_cache_manager, '_load_data', return_value=sample_data):
            with patch.object(intelligent_cache_manager, '_determine_dynamic_ttl', return_value=300):
                with patch.object(intelligent_cache_manager, '_save_to_cache'):
                    # 테스트 실행
                    result = await intelligent_cache_manager.preload_data(
                        key="AAPL_stock_data",
                        data_type="stock_price",
                        loader_name="stock_loader",
                        loader_params={"symbol": "AAPL"},
                        priority=2
                    )
                    
                    # 결과 검증
                    assert result is True
                    
                    # 모의 호출 검증
                    intelligent_cache_manager._load_data.assert_called_once_with("stock_loader", {"symbol": "AAPL"})
                    intelligent_cache_manager._save_to_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preload_data_no_loader(self, intelligent_cache_manager):
        """데이터 로더 없는 경우 사전 로드 테스트"""
        # 테스트 실행
        result = await intelligent_cache_manager.preload_data(
            key="AAPL_stock_data",
            data_type="stock_price",
            loader_name="nonexistent_loader"
        )
        
        # 결과 검증
        assert result is False
    
    @pytest.mark.asyncio
    async def test_preload_data_load_failure(self, intelligent_cache_manager, mock_redis_client):
        """데이터 로드 실패 시 사전 로드 테스트"""
        # 설정
        def failing_loader(**kwargs):
            raise Exception("Load failed")
        
        intelligent_cache_manager.register_data_loader("failing_loader", failing_loader)
        
        with patch.object(intelligent_cache_manager, '_load_data', side_effect=Exception("Load failed")):
            # 테스트 실행
            result = await intelligent_cache_manager.preload_data(
                key="AAPL_stock_data",
                data_type="stock_price",
                loader_name="failing_loader"
            )
            
            # 결과 검증
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_cache_statistics(self, intelligent_cache_manager):
        """캐시 통계 조회 테스트"""
        # 설정
        intelligent_cache_manager.stats.total_requests = 100
        intelligent_cache_manager.stats.cache_hits = 80
        intelligent_cache_manager.stats.cache_misses = 20
        intelligent_cache_manager.stats.warmup_hits = 15
        intelligent_cache_manager.stats.prediction_accuracy = 0.75
        intelligent_cache_manager.stats.avg_response_time = 0.25
        intelligent_cache_manager.stats.memory_usage = 1024
        intelligent_cache_manager.running = True
        
        # 테스트 실행
        stats = await intelligent_cache_manager.get_cache_statistics()
        
        # 결과 검증
        assert stats["total_requests"] == 100
        assert stats["cache_hits"] == 80
        assert stats["cache_misses"] == 20
        assert stats["hit_rate"] == 80.0
        assert stats["warmup_hits"] == 15
        assert stats["prediction_accuracy"] == 0.75
        assert stats["avg_response_time"] == 0.25
        assert stats["memory_usage"] == 1024
        assert stats["active_patterns"] == 0
        assert stats["warmup_queue_size"] == 0
        assert stats["running"] is True
    
    @pytest.mark.asyncio
    async def test_record_access(self, intelligent_cache_manager, mock_redis_client):
        """접근 기록 테스트"""
        # 테스트 실행
        await intelligent_cache_manager._record_access("test_key")
        
        # 결과 검증
        assert "test_key" in intelligent_cache_manager.access_history
        assert len(intelligent_cache_manager.access_history["test_key"]) == 1
        
        # 모의 호출 검증
        mock_redis_client.lpush.assert_called_once()
        mock_redis_client.ltrim.assert_called_once()
        mock_redis_client.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_access_pattern_insufficient_samples(self, intelligent_cache_manager):
        """샘플 수 부족 시 접근 패턴 분석 테스트"""
        # 설정
        intelligent_cache_manager.access_history["test_key"] = deque(
            [datetime.utcnow() - timedelta(seconds=i) for i in range(3)],  # 3개 샘플
            maxlen=50
        )
        
        # 테스트 실행
        pattern = await intelligent_cache_manager._analyze_access_pattern("test_key")
        
        # 결과 검증
        assert pattern is None
    
    @pytest.mark.asyncio
    async def test_analyze_access_pattern_periodic(self, intelligent_cache_manager):
        """주기적 접근 패턴 분석 테스트"""
        # 설정
        base_time = datetime.utcnow()
        access_times = [
            base_time - timedelta(seconds=i * 60)  # 1분 간격
            for i in range(10)
        ]
        
        intelligent_cache_manager.access_history["test_key"] = deque(access_times, maxlen=50)
        
        # 테스트 실행
        pattern = await intelligent_cache_manager._analyze_access_pattern("test_key")
        
        # 결과 검증
        assert pattern is not None
        assert pattern.key == "test_key"
        assert pattern.frequency == "medium"  # 1분 간격
        assert pattern.pattern == "periodic"  # 표준편차가 작음
        assert pattern.access_count == 10
        assert pattern.last_access == access_times[-1]
    
    @pytest.mark.asyncio
    async def test_analyze_access_pattern_burst(self, intelligent_cache_manager):
        """버스트 접근 패턴 분석 테스트"""
        # 설정
        base_time = datetime.utcnow()
        access_times = [
            base_time - timedelta(seconds=i * 5)  # 5초 간격
            for i in range(10)
        ]
        
        intelligent_cache_manager.access_history["test_key"] = deque(access_times, maxlen=50)
        
        # 테스트 실행
        pattern = await intelligent_cache_manager._analyze_access_pattern("test_key")
        
        # 결과 검증
        assert pattern is not None
        assert pattern.key == "test_key"
        assert pattern.frequency == "high"  # 5초 간격
        assert pattern.pattern == "burst"  # 표준편차가 작음
        assert pattern.access_count == 10
    
    @pytest.mark.asyncio
    async def test_analyze_access_pattern_random(self, intelligent_cache_manager):
        """불규 접근 패턴 분석 테스트"""
        # 설정
        base_time = datetime.utcnow()
        access_times = [
            base_time - timedelta(seconds=i * 300)  # 5분 간격
            for i in range(10)
        ]
        
        intelligent_cache_manager.access_history["test_key"] = deque(access_times, maxlen=50)
        
        # 테스트 실행
        pattern = await intelligent_cache_manager._analyze_access_pattern("test_key")
        
        # 결과 검증
        assert pattern is not None
        assert pattern.key == "test_key"
        assert pattern.frequency == "low"  # 5분 간격
        assert pattern.pattern == "periodic"  # 표준편차가 작음
    
    @pytest.mark.asyncio
    async def test_predict_next_access_periodic(self, intelligent_cache_manager):
        """주기적 패턴 다음 접근 시간 예측 테스트"""
        # 설정
        pattern = AccessPattern(
            key="test_key",
            frequency="medium",
            pattern="periodic",
            avg_interval=60.0,
            std_dev=5.0,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.8
        )
        
        # 테스트 실행
        next_time = await intelligent_cache_manager._predict_next_access(pattern)
        
        # 결과 검증
        assert next_time is not None
        expected_time = pattern.last_access + timedelta(seconds=60.0)
        assert abs((next_time - expected_time).total_seconds()) < 1.0
    
    @pytest.mark.asyncio
    async def test_predict_next_access_burst(self, intelligent_cache_manager):
        """버스트 패턴 다음 접근 시간 예측 테스트"""
        # 설정
        pattern = AccessPattern(
            key="test_key",
            frequency="high",
            pattern="burst",
            avg_interval=30.0,
            std_dev=5.0,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.8
        )
        
        # 테스트 실행
        next_time = await intelligent_cache_manager._predict_next_access(pattern)
        
        # 결과 검증
        assert next_time is not None
        expected_time = pattern.last_access + timedelta(seconds=60.0)  # burst_multiplier * avg_interval
        assert abs((next_time - expected_time).total_seconds()) < 1.0
    
    @pytest.mark.asyncio
    async def test_predict_next_access_random(self, intelligent_cache_manager):
        """불규 패턴 다음 접근 시간 예측 테스트"""
        # 설정
        pattern = AccessPattern(
            key="test_key",
            frequency="low",
            pattern="random",
            avg_interval=300.0,
            std_dev=100.0,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.8
        )
        
        # 테스트 실행
        next_time = await intelligent_cache_manager._predict_next_access(pattern)
        
        # 결과 검증
        assert next_time is None  # 랜덤 패턴은 예측 불가
    
    def test_calculate_warmup_priority(self, intelligent_cache_manager):
        """워밍 우선순위 계산 테스트"""
        # 설정
        pattern = AccessPattern(
            key="test_key",
            frequency="high",
            pattern="periodic",
            avg_interval=60.0,
            std_dev=5.0,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.8
        )
        
        # 테스트 실행
        priority = intelligent_cache_manager._calculate_warmup_priority(pattern, "stock_price")
        
        # 결과 검증
        # 기본 우선순위: 1
        # 높은 빈도: +3
        # 주식 가격 데이터 타입: +2
        # 신뢰도 가중치: int(0.8 * 2) = 1
        # 총합: 1 + 3 + 2 + 1 = 7
        assert priority == 7
    
    @pytest.mark.asyncio
    async def test_add_to_warmup_queue(self, intelligent_cache_manager):
        """워밍 큐에 작업 추가 테스트"""
        # 설정
        task = CacheWarmupTask(
            key="test_key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="test_loader",
            params={}
        )
        
        # 테스트 실행
        await intelligent_cache_manager._add_to_warmup_queue(task)
        
        # 결과 검증
        assert len(intelligent_cache_manager.warmup_queue) == 1
        assert intelligent_cache_manager.warmup_queue[0] == task
    
    @pytest.mark.asyncio
    async def test_add_to_warmup_queue_full(self, intelligent_cache_manager):
        """워밍 큐가 가득 찬 경우 테스트"""
        # 설정
        intelligent_cache_manager.warmup_queue_size = 2  # 작은 큐 크기
        
        # 큐를 가득 채움
        for i in range(3):
            task = CacheWarmupTask(
                key=f"test_key_{i}",
                scheduled_time=datetime.utcnow(),
                priority=i,
                data_loader="test_loader",
                params={}
            )
            await intelligent_cache_manager._add_to_warmup_queue(task)
        
        # 결과 검증
        assert len(intelligent_cache_manager.warmup_queue) == 2  # 최대 크기 유지
        assert intelligent_cache_manager.warmup_queue[0].priority == 2  # 가장 높은 우선순위 유지
        assert intelligent_cache_manager.warmup_queue[1].priority == 1  # 두 번째 높은 우선순위
    
    @pytest.mark.asyncio
    async def test_determine_dynamic_ttl(self, intelligent_cache_manager):
        """동적 TTL 결정 테스트"""
        # 설정
        pattern = AccessPattern(
            key="test_key",
            frequency="high",
            pattern="periodic",
            avg_interval=60.0,
            std_dev=5.0,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.8
        )
        
        intelligent_cache_manager.access_patterns["test_key"] = pattern
        
        # 테스트 실행
        ttl = await intelligent_cache_manager._determine_dynamic_ttl("test_key", "stock_price")
        
        # 결과 검증
        # 기본 TTL: 60초 (stock_price)
        # 높은 빈도: 1.5배 증가
        # 예상 TTL: 60 * 1.5 = 90초
        assert ttl == 90
    
    @pytest.mark.asyncio
    async def test_determine_dynamic_ttl_no_pattern(self, intelligent_cache_manager):
        """패턴 없는 동적 TTL 결정 테스트"""
        # 테스트 실행
        ttl = await intelligent_cache_manager._determine_dynamic_ttl("test_key", "stock_price")
        
        # 결과 검증
        assert ttl == 60  # 기본 TTL (stock_price)
    
    @pytest.mark.asyncio
    async def test_get_from_cache(self, intelligent_cache_manager, mock_redis_client):
        """캐시에서 데이터 조회 테스트"""
        # 설정
        sample_data = {"symbol": "AAPL", "price": 150.25}
        mock_redis_client.get.return_value = json.dumps(sample_data)
        
        # 테스트 실행
        result = await intelligent_cache_manager._get_from_cache("test_key")
        
        # 결과 검증
        assert result == sample_data
        
        # 모의 호출 검증
        mock_redis_client.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_get_from_cache_miss(self, intelligent_cache_manager, mock_redis_client):
        """캐시 미스 데이터 조회 테스트"""
        # 설정
        mock_redis_client.get.return_value = None
        
        # 테스트 실행
        result = await intelligent_cache_manager._get_from_cache("test_key")
        
        # 결과 검증
        assert result is None
        
        # 모의 호출 검증
        mock_redis_client.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_save_to_cache(self, intelligent_cache_manager, mock_redis_client):
        """캐시에 데이터 저장 테스트"""
        # 설정
        sample_data = {"symbol": "AAPL", "price": 150.25}
        
        # 테스트 실행
        await intelligent_cache_manager._save_to_cache("test_key", sample_data, 300)
        
        # 결과 검증
        mock_redis_client.setex.assert_called_once_with("test_key", 300, json.dumps(sample_data))
    
    @pytest.mark.asyncio
    async def test_load_data_async(self, intelligent_cache_manager):
        """비동기 데이터 로드 테스트"""
        # 설정
        async def async_loader(**kwargs):
            return {"symbol": "AAPL", "price": 150.25}
        
        intelligent_cache_manager.register_data_loader("async_loader", async_loader)
        
        # 테스트 실행
        result = await intelligent_cache_manager._load_data("async_loader", {"symbol": "AAPL"})
        
        # 결과 검증
        assert result == {"symbol": "AAPL", "price": 150.25}
    
    @pytest.mark.asyncio
    async def test_load_data_sync(self, intelligent_cache_manager):
        """동기 데이터 로드 테스트"""
        # 설정
        def sync_loader(**kwargs):
            return {"symbol": "AAPL", "price": 150.25}
        
        intelligent_cache_manager.register_data_loader("sync_loader", sync_loader)
        
        # 테스트 실행
        result = await intelligent_cache_manager._load_data("sync_loader", {"symbol": "AAPL"})
        
        # 결과 검증
        assert result == {"symbol": "AAPL", "price": 150.25}
    
    @pytest.mark.asyncio
    async def test_load_data_not_found(self, intelligent_cache_manager):
        """찾을 수 없는 데이터 로더 테스트"""
        # 테스트 실행
        result = await intelligent_cache_manager._load_data("nonexistent_loader", {})
        
        # 결과 검증
        assert result is None
    
    def test_update_response_time_first_request(self, intelligent_cache_manager):
        """첫 번째 요청 응답 시간 업데이트 테스트"""
        # 테스트 실행
        intelligent_cache_manager._update_response_time(0.5)
        
        # 결과 검증
        assert intelligent_cache_manager.stats.avg_response_time == 0.5
    
    def test_update_response_time_multiple_requests(self, intelligent_cache_manager):
        """여러 요청 응답 시간 업데이트 테스트"""
        # 설정
        intelligent_cache_manager.stats.total_requests = 10
        intelligent_cache_manager.stats.avg_response_time = 0.3
        
        # 테스트 실행
        intelligent_cache_manager._update_response_time(0.5)
        
        # 결과 검증
        # 새 평균 = (0.3 * 9 + 0.5) / 10 = 0.32
        assert abs(intelligent_cache_manager.stats.avg_response_time - 0.32) < 0.001
    
    @pytest.mark.asyncio
    async def test_pattern_analyzer(self, intelligent_cache_manager):
        """패턴 분석기 테스트"""
        # 설정
        intelligent_cache_manager.running = True
        
        with patch.object(intelligent_cache_manager, '_analyze_access_pattern'):
            # 테스트 실행 (짧게 실행 후 중지)
            task = asyncio.create_task(intelligent_cache_manager._pattern_analyzer())
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # 결과 검증
            intelligent_cache_manager._analyze_access_pattern.assert_called()
    
    @pytest.mark.asyncio
    async def test_stats_collector(self, intelligent_cache_manager, mock_redis_client):
        """통계 수집기 테스트"""
        # 설정
        intelligent_cache_manager.running = True
        
        with patch('asyncio.sleep'):  # 실제 대기 방지
            # 테스트 실행
            task = asyncio.create_task(intelligent_cache_manager._stats_collector())
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # 결과 검증
            mock_redis_client.info.assert_called_once_with("memory")
            assert intelligent_cache_manager.stats.memory_usage == 1024
    
    @pytest.mark.asyncio
    async def test_warmup_scheduler(self, intelligent_cache_manager):
        """워밍 스케줄러 테스트"""
        # 설정
        intelligent_cache_manager.running = True
        
        with patch.object(intelligent_cache_manager, '_execute_warmup_task'):
            with patch('asyncio.sleep'):  # 실제 대기 방지
                # 테스트 실행 (짧게 실행 후 중지)
                task = asyncio.create_task(intelligent_cache_manager._warmup_scheduler())
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # 결과 검증
                intelligent_cache_manager._execute_warmup_task.assert_called()
    
    @pytest.mark.asyncio
    async def test_execute_warmup_task_success(self, intelligent_cache_manager, mock_redis_client):
        """워밍 작업 실행 성공 테스트"""
        # 설정
        sample_data = {"symbol": "AAPL", "price": 150.25}
        
        def sample_loader(**kwargs):
            return sample_data
        
        intelligent_cache_manager.register_data_loader("sample_loader", sample_loader)
        
        task = CacheWarmupTask(
            key="test_key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="sample_loader",
            params={"symbol": "AAPL"}
        )
        
        with patch.object(intelligent_cache_manager, '_get_from_cache', return_value=None):
            with patch.object(intelligent_cache_manager, '_load_data', return_value=sample_data):
                with patch.object(intelligent_cache_manager, '_determine_dynamic_ttl', return_value=300):
                    with patch.object(intelligent_cache_manager, '_save_to_cache'):
                        # 테스트 실행
                        await intelligent_cache_manager._execute_warmup_task(task)
                        
                        # 결과 검증
                        assert intelligent_cache_manager.stats.warmup_hits == 1
                        
                        # 모의 호출 검증
                        intelligent_cache_manager._load_data.assert_called_once()
                        intelligent_cache_manager._save_to_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_warmup_task_already_cached(self, intelligent_cache_manager, mock_redis_client):
        """이미 캐시된 데이터 워밍 작업 실행 테스트"""
        # 설정
        sample_data = {"symbol": "AAPL", "price": 150.25}
        
        task = CacheWarmupTask(
            key="test_key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="sample_loader",
            params={"symbol": "AAPL"}
        )
        
        with patch.object(intelligent_cache_manager, '_get_from_cache', return_value=sample_data):
            # 테스트 실행
            await intelligent_cache_manager._execute_warmup_task(task)
            
            # 결과 검증
            assert intelligent_cache_manager.stats.warmup_hits == 0  # 이미 캐시되었으므로 증가하지 않음
    
    @pytest.mark.asyncio
    async def test_execute_warmup_task_no_loader(self, intelligent_cache_manager):
        """데이터 로더 없는 워밍 작업 실행 테스트"""
        # 설정
        task = CacheWarmupTask(
            key="test_key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="nonexistent_loader",
            params={}
        )
        
        # 테스트 실행
        await intelligent_cache_manager._execute_warmup_task(task)
        
        # 결과 검증
        assert intelligent_cache_manager.stats.warmup_hits == 0
    
    @pytest.mark.asyncio
    async def test_execute_warmup_task_load_failure(self, intelligent_cache_manager):
        """데이터 로드 실패 시 워밍 작업 실행 테스트"""
        # 설정
        def failing_loader(**kwargs):
            raise Exception("Load failed")
        
        intelligent_cache_manager.register_data_loader("failing_loader", failing_loader)
        
        task = CacheWarmupTask(
            key="test_key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="failing_loader",
            params={}
        )
        
        # 테스트 실행
        await intelligent_cache_manager._execute_warmup_task(task)
        
        # 결과 검증
        assert intelligent_cache_manager.stats.warmup_hits == 0
    
    @pytest.mark.asyncio
    async def test_execute_warmup_task_with_retry(self, intelligent_cache_manager):
        """재시도 포함 워밍 작업 실행 테스트"""
        # 설정
        task = CacheWarmupTask(
            key="test_key",
            scheduled_time=datetime.utcnow(),
            priority=5,
            data_loader="nonexistent_loader",
            params={}
        )
        
        with patch.object(intelligent_cache_manager, '_add_to_warmup_queue') as mock_add:
            # 테스트 실행
            await intelligent_cache_manager._execute_warmup_task(task)
            
            # 결과 검증
            assert task.retry_count == 1
            
            # 재시도를 위한 큐 추가 확인
            mock_add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_access_patterns(self, intelligent_cache_manager, mock_redis_client):
        """접근 패턴 로드 테스트"""
        # 설정
        pattern_data = {
            "key": "test_key",
            "frequency": "high",
            "pattern": "periodic",
            "avg_interval": 60.0,
            "std_dev": 5.0,
            "last_access": datetime.utcnow().isoformat(),
            "access_count": 10,
            "prediction_confidence": 0.8
        }
        
        mock_redis_client.keys.return_value = ["cache:pattern:test_key"]
        mock_redis_client.get.return_value = json.dumps(pattern_data)
        
        # 테스트 실행
        await intelligent_cache_manager._load_access_patterns()
        
        # 결과 검증
        assert "test_key" in intelligent_cache_manager.access_patterns
        pattern = intelligent_cache_manager.access_patterns["test_key"]
        assert pattern.key == "test_key"
        assert pattern.frequency == "high"
        
        # 모의 호출 검증
        mock_redis_client.keys.assert_called_once_with("cache:pattern:*")
        mock_redis_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_access_patterns(self, intelligent_cache_manager, mock_redis_client):
        """접근 패턴 저장 테스트"""
        # 설정
        pattern = AccessPattern(
            key="test_key",
            frequency="high",
            pattern="periodic",
            avg_interval=60.0,
            std_dev=5.0,
            last_access=datetime.utcnow(),
            access_count=10,
            prediction_confidence=0.8
        )
        
        intelligent_cache_manager.access_patterns["test_key"] = pattern
        
        # 테스트 실행
        await intelligent_cache_manager._save_access_patterns()
        
        # 결과 검증
        mock_redis_client.setex.assert_called_once()
        
        # 호출된 인자 검증
        call_args = mock_redis_client.setex.call_args
        key = call_args[0][0]
        ttl = call_args[0][1]
        pattern_dict = call_args[0][2]
        
        assert key == "cache:pattern:test_key"
        assert ttl == 86400
        assert json.loads(pattern_dict)["key"] == "test_key"