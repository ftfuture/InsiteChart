"""
캐시 시스템 성능 테스트

이 모듈은 캐시 시스템의 성능을 측정하고 벤치마킹합니다.
"""

import pytest
import time
import asyncio
import statistics
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from backend.cache.unified_cache import UnifiedCacheManager
from backend.cache.enhanced_redis_cache import EnhancedRedisCacheManager
from backend.cache.resilient_cache_manager import ResilientCacheManager
from backend.models.unified_models import UnifiedStockData, StockType


class TestCachePerformance:
    """캐시 시스템 성능 테스트 클래스"""
    
    @pytest.fixture
    def performance_thresholds(self):
        """성능 임계값 픽스처"""
        return {
            "cache_operations": {
                "set": {
                    "excellent": 1.0,    # 1ms 이하
                    "good": 5.0,         # 5ms 이하
                    "acceptable": 10.0   # 10ms 이하
                },
                "get": {
                    "excellent": 1.0,    # 1ms 이하
                    "good": 5.0,         # 5ms 이하
                    "acceptable": 10.0   # 10ms 이하
                },
                "delete": {
                    "excellent": 1.0,    # 1ms 이하
                    "good": 5.0,         # 5ms 이하
                    "acceptable": 10.0   # 10ms 이하
                }
            },
            "cache_hit_rate": {
                "excellent": 0.95,     # 95% 이상
                "good": 0.90,          # 90% 이상
                "acceptable": 0.80     # 80% 이상
            },
            "concurrent_operations": {
                "excellent": 1000,     # 1000개 동시 작업
                "good": 500,           # 500개 동시 작업
                "acceptable": 200      # 200개 동시 작업
            }
        }
    
    @pytest.fixture
    def sample_stock_data(self):
        """샘플 주식 데이터 픽스처"""
        return {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "current_price": 150.0,
            "previous_close": 145.0,
            "change": 5.0,
            "change_percent": 3.45,
            "volume": 1000000,
            "market_cap": 2500000000000,
            "pe_ratio": 25.5,
            "dividend_yield": 0.5,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "description": "Apple Inc. designs, manufactures",
            "website": "https://www.apple.com",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "timezone": "America/New_York",
            "stock_type": "equity"
        }
    
    def test_memory_cache_performance(self, performance_thresholds, sample_stock_data):
        """메모리 캐시 성능 테스트"""
        from backend.cache.memory_cache import MemoryCacheManager
        
        cache = MemoryCacheManager()
        
        # SET 작업 성능 측정
        set_times = []
        for i in range(100):
            key = f"stock:{i}"
            start_time = time.time()
            cache.set(key, sample_stock_data, ttl=3600)
            end_time = time.time()
            set_times.append((end_time - start_time) * 1000)
        
        avg_set_time = statistics.mean(set_times)
        max_set_time = max(set_times)
        
        # GET 작업 성능 측정
        get_times = []
        for i in range(100):
            key = f"stock:{i}"
            start_time = time.time()
            result = cache.get(key)
            end_time = time.time()
            get_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_get_time = statistics.mean(get_times)
        max_get_time = max(get_times)
        
        # 성능 기준 확인
        assert avg_set_time < performance_thresholds["cache_operations"]["set"]["good"]
        assert avg_get_time < performance_thresholds["cache_operations"]["get"]["excellent"]
        
        print(f"Memory Cache Performance:")
        print(f"  SET - Average: {avg_set_time:.2f}ms, Max: {max_set_time:.2f}ms")
        print(f"  GET - Average: {avg_get_time:.2f}ms, Max: {max_get_time:.2f}ms")
    
    def test_unified_cache_performance(self, performance_thresholds, sample_stock_data):
        """통합 캐시 성능 테스트"""
        cache = UnifiedCacheManager()
        
        # SET 작업 성능 측정
        set_times = []
        for i in range(50):
            key = f"unified_stock:{i}"
            start_time = time.time()
            cache.set(key, sample_stock_data, ttl=3600)
            end_time = time.time()
            set_times.append((end_time - start_time) * 1000)
        
        avg_set_time = statistics.mean(set_times)
        
        # GET 작업 성능 측정
        get_times = []
        for i in range(50):
            key = f"unified_stock:{i}"
            start_time = time.time()
            result = cache.get(key)
            end_time = time.time()
            get_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_get_time = statistics.mean(get_times)
        
        # 캐시 히트률 측정
        hit_count = 0
        total_requests = 100
        
        for i in range(total_requests):
            key = f"unified_stock:{i % 50}"  # 반복적인 키로 캐시 히트 유도
            result = cache.get(key)
            if result is not None:
                hit_count += 1
        
        hit_rate = hit_count / total_requests
        
        # 성능 기준 확인
        assert avg_set_time < performance_thresholds["cache_operations"]["set"]["acceptable"]
        assert avg_get_time < performance_thresholds["cache_operations"]["get"]["acceptable"]
        assert hit_rate >= performance_thresholds["cache_hit_rate"]["acceptable"]
        
        print(f"Unified Cache Performance:")
        print(f"  SET - Average: {avg_set_time:.2f}ms")
        print(f"  GET - Average: {avg_get_time:.2f}ms")
        print(f"  Hit Rate: {hit_rate:.2%}")
    
    @patch('redis.Redis')
    def test_redis_cache_performance(self, mock_redis, performance_thresholds, sample_stock_data):
        """Redis 캐시 성능 테스트"""
        # 모의 Redis 클라이언트 설정
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_client.get.return_value = str(sample_stock_data).encode()
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = 1
        mock_redis.return_value = mock_client
        
        cache = EnhancedRedisCacheManager()
        
        # SET 작업 성능 측정
        set_times = []
        for i in range(50):
            key = f"redis_stock:{i}"
            start_time = time.time()
            cache.set(key, sample_stock_data, ttl=3600)
            end_time = time.time()
            set_times.append((end_time - start_time) * 1000)
        
        avg_set_time = statistics.mean(set_times)
        
        # GET 작업 성능 측정
        get_times = []
        for i in range(50):
            key = f"redis_stock:{i}"
            start_time = time.time()
            result = cache.get(key)
            end_time = time.time()
            get_times.append((end_time - start_time) * 1000)
        
        avg_get_time = statistics.mean(get_times)
        
        # 성능 기준 확인
        assert avg_set_time < performance_thresholds["cache_operations"]["set"]["acceptable"]
        assert avg_get_time < performance_thresholds["cache_operations"]["get"]["acceptable"]
        
        print(f"Redis Cache Performance:")
        print(f"  SET - Average: {avg_set_time:.2f}ms")
        print(f"  GET - Average: {avg_get_time:.2f}ms")
    
    def test_resilient_cache_performance(self, performance_thresholds, sample_stock_data):
        """회복력 있는 캐시 성능 테스트"""
        cache = ResilientCacheManager()
        
        # 정상 상태에서의 성능 측정
        set_times = []
        get_times = []
        
        for i in range(30):
            key = f"resilient_stock:{i}"
            
            # SET 작업
            start_time = time.time()
            cache.set(key, sample_stock_data, ttl=3600)
            end_time = time.time()
            set_times.append((end_time - start_time) * 1000)
            
            # GET 작업
            start_time = time.time()
            result = cache.get(key)
            end_time = time.time()
            get_times.append((end_time - start_time) * 1000)
        
        avg_set_time = statistics.mean(set_times)
        avg_get_time = statistics.mean(get_times)
        
        # 성능 기준 확인
        assert avg_set_time < performance_thresholds["cache_operations"]["set"]["acceptable"]
        assert avg_get_time < performance_thresholds["cache_operations"]["get"]["acceptable"]
        
        print(f"Resilient Cache Performance:")
        print(f"  SET - Average: {avg_set_time:.2f}ms")
        print(f"  GET - Average: {avg_get_time:.2f}ms")
    
    def test_concurrent_cache_operations(self, performance_thresholds, sample_stock_data):
        """동시 캐시 작업 성능 테스트"""
        import threading
        
        cache = UnifiedCacheManager()
        results = {"set": [], "get": []}
        
        def set_operation(thread_id):
            """SET 작업을 수행하는 함수"""
            for i in range(10):
                key = f"concurrent_stock:{thread_id}_{i}"
                start_time = time.time()
                cache.set(key, sample_stock_data, ttl=3600)
                end_time = time.time()
                results["set"].append((end_time - start_time) * 1000)
        
        def get_operation(thread_id):
            """GET 작업을 수행하는 함수"""
            for i in range(10):
                key = f"concurrent_stock:{thread_id}_{i}"
                start_time = time.time()
                result = cache.get(key)
                end_time = time.time()
                results["get"].append((end_time - start_time) * 1000)
        
        # 동시 SET 작업
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=set_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        set_total_time = time.time() - start_time
        
        # 동시 GET 작업
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=get_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        get_total_time = time.time() - start_time
        
        # 성능 분석
        avg_set_time = statistics.mean(results["set"])
        avg_get_time = statistics.mean(results["get"])
        total_operations = len(results["set"]) + len(results["get"])
        
        # 성능 기준 확인
        assert total_operations >= performance_thresholds["concurrent_operations"]["acceptable"]
        assert avg_set_time < performance_thresholds["cache_operations"]["set"]["acceptable"]
        assert avg_get_time < performance_thresholds["cache_operations"]["get"]["acceptable"]
        
        print(f"Concurrent Cache Operations:")
        print(f"  Total Operations: {total_operations}")
        print(f"  SET - Average: {avg_set_time:.2f}ms, Total Time: {set_total_time:.2f}s")
        print(f"  GET - Average: {avg_get_time:.2f}ms, Total Time: {get_total_time:.2f}s")
    
    def test_cache_memory_usage(self, performance_thresholds, sample_stock_data):
        """캐시 메모리 사용량 테스트"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        cache = UnifiedCacheManager()
        
        # 대용량 데이터 캐싱
        large_data = []
        for i in range(1000):
            data = sample_stock_data.copy()
            data["symbol"] = f"STOCK_{i:04d}"
            data["description"] = "x" * 1000  # 대용량 설명
            large_data.append(data)
            
            key = f"large_stock:{i}"
            cache.set(key, data, ttl=3600)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        memory_per_item = memory_increase / 1000
        
        print(f"Cache Memory Usage:")
        print(f"  Initial Memory: {initial_memory:.2f}MB")
        print(f"  Final Memory: {final_memory:.2f}MB")
        print(f"  Memory Increase: {memory_increase:.2f}MB")
        print(f"  Memory per Item: {memory_per_item:.2f}MB")
        
        # 메모리 사용량이 과도하지 않아야 함
        assert memory_increase < 500  # 500MB 이하
        assert memory_per_item < 1.0  # 항목당 1MB 이하
    
    def test_cache_hit_rate_optimization(self, performance_thresholds, sample_stock_data):
        """캐시 히트률 최적화 테스트"""
        cache = UnifiedCacheManager()
        
        # 데이터 미리 캐싱
        popular_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        for symbol in popular_symbols:
            data = sample_stock_data.copy()
            data["symbol"] = symbol
            cache.set(f"stock:{symbol}", data, ttl=3600)
        
        # 인기 있는 데이터에 대한 접근 패턴 시뮬레이션
        hit_count = 0
        total_requests = 200
        
        for i in range(total_requests):
            # 80%의 요청이 인기 있는 데이터로 향함
            if i < total_requests * 0.8:
                symbol = popular_symbols[i % len(popular_symbols)]
            else:
                symbol = f"UNPOPULAR_{i}"
            
            result = cache.get(f"stock:{symbol}")
            if result is not None:
                hit_count += 1
        
        hit_rate = hit_count / total_requests
        
        # 성능 기준 확인
        assert hit_rate >= performance_thresholds["cache_hit_rate"]["good"]
        
        print(f"Cache Hit Rate Optimization:")
        print(f"  Hit Count: {hit_count}/{total_requests}")
        print(f"  Hit Rate: {hit_rate:.2%}")
    
    def test_cache_ttl_performance(self, performance_thresholds, sample_stock_data):
        """캐시 TTL 성능 테스트"""
        cache = UnifiedCacheManager()
        
        # 다양한 TTL 설정으로 성능 측정
        ttl_values = [1, 60, 300, 3600, 86400]  # 1초, 1분, 5분, 1시간, 1일
        performance_results = {}
        
        for ttl in ttl_values:
            set_times = []
            get_times = []
            
            for i in range(20):
                key = f"ttl_test:{ttl}_{i}"
                
                # SET 작업
                start_time = time.time()
                cache.set(key, sample_stock_data, ttl=ttl)
                end_time = time.time()
                set_times.append((end_time - start_time) * 1000)
                
                # GET 작업
                start_time = time.time()
                result = cache.get(key)
                end_time = time.time()
                get_times.append((end_time - start_time) * 1000)
            
            performance_results[ttl] = {
                "avg_set_time": statistics.mean(set_times),
                "avg_get_time": statistics.mean(get_times)
            }
        
        print(f"Cache TTL Performance:")
        for ttl, results in performance_results.items():
            print(f"  TTL {ttl}s - SET: {results['avg_set_time']:.2f}ms, GET: {results['avg_get_time']:.2f}ms")
            
            # 모든 TTL 설정에서 성능 기준 확인
            assert results["avg_set_time"] < performance_thresholds["cache_operations"]["set"]["acceptable"]
            assert results["avg_get_time"] < performance_thresholds["cache_operations"]["get"]["acceptable"]
    
    def test_cache_size_scaling(self, performance_thresholds, sample_stock_data):
        """캐시 크기 확장성 테스트"""
        cache = UnifiedCacheManager()
        
        # 다양한 캐시 크기에서 성능 측정
        cache_sizes = [100, 500, 1000, 5000, 10000]
        performance_results = {}
        
        for size in cache_sizes:
            set_times = []
            get_times = []
            
            # 캐시 채우기
            for i in range(size):
                key = f"scale_test:{i}"
                data = sample_stock_data.copy()
                data["symbol"] = f"STOCK_{i:04d}"
                
                start_time = time.time()
                cache.set(key, data, ttl=3600)
                end_time = time.time()
                set_times.append((end_time - start_time) * 1000)
            
            # 캐시 읽기
            for i in range(min(100, size)):  # 최대 100개만 테스트
                key = f"scale_test:{i}"
                start_time = time.time()
                result = cache.get(key)
                end_time = time.time()
                get_times.append((end_time - start_time) * 1000)
                assert result is not None
            
            performance_results[size] = {
                "avg_set_time": statistics.mean(set_times),
                "avg_get_time": statistics.mean(get_times)
            }
        
        print(f"Cache Size Scaling Performance:")
        for size, results in performance_results.items():
            print(f"  Size {size} - SET: {results['avg_set_time']:.2f}ms, GET: {results['avg_get_time']:.2f}ms")
            
            # 크기가 커져도 성능이 크게 저하되지 않아야 함
            assert results["avg_set_time"] < performance_thresholds["cache_operations"]["set"]["acceptable"]
            assert results["avg_get_time"] < performance_thresholds["cache_operations"]["get"]["acceptable"]
    
    def test_cache_eviction_performance(self, performance_thresholds, sample_stock_data):
        """캐시 제거 성능 테스트"""
        cache = UnifiedCacheManager()
        
        # 캐시 용량 제한 설정 (가정)
        max_cache_size = 100
        
        # 캐시 용량 초과로 제거 발생
        set_times = []
        eviction_times = []
        
        for i in range(max_cache_size + 50):  # 용량 초과
            key = f"eviction_test:{i}"
            data = sample_stock_data.copy()
            data["symbol"] = f"STOCK_{i:04d}"
            
            start_time = time.time()
            cache.set(key, data, ttl=3600)
            end_time = time.time()
            set_times.append((end_time - start_time) * 1000)
            
            # 제거 작업 시간 측정 (가정)
            if i >= max_cache_size:
                eviction_times.append((end_time - start_time) * 1000)
        
        # 제거된 항목 확인
        evicted_count = 0
        for i in range(50):  # 처음 50개 항목 확인
            key = f"eviction_test:{i}"
            result = cache.get(key)
            if result is None:
                evicted_count += 1
        
        avg_set_time = statistics.mean(set_times)
        avg_eviction_time = statistics.mean(eviction_times) if eviction_times else 0
        
        # 성능 기준 확인
        assert avg_set_time < performance_thresholds["cache_operations"]["set"]["acceptable"]
        assert evicted_count > 0  # 제거가 발생했어야 함
        
        print(f"Cache Eviction Performance:")
        print(f"  Average SET Time: {avg_set_time:.2f}ms")
        print(f"  Average Eviction Time: {avg_eviction_time:.2f}ms")
        print(f"  Evicted Items: {evicted_count}/50")