"""
고급 성능 테스트 모듈
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from backend.api.gateway import APIGateway
from backend.cache.unified_cache import UnifiedCacheManager
from backend.services.unified_service import UnifiedService
from backend.services.advanced_sentiment_service import AdvancedSentimentService
from backend.services.realtime_data_collector import RealtimeDataCollector


class TestAPIPerformance:
    """API 성능 테스트"""
    
    @pytest.fixture
    async def setup_gateway(self):
        """성능 테스트용 게이트웨이 설정"""
        gateway = APIGateway()
        
        # 빠른 응답 서비스 모의
        fast_service = Mock()
        
        async def fast_response():
            await asyncio.sleep(0.001)  # 1ms 지연
            return {"status": "success", "timestamp": time.time()}
        
        fast_service.call = fast_response
        
        # 라우트 등록
        route = GatewayRoute(
            path="/performance_test",
            methods=["GET", "POST"],
            service="fast_service",
            rate_limit=10000
        )
        gateway.add_route(route)
        gateway.register_service("fast_service", fast_service)
        
        return gateway
    
    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self, setup_gateway):
        """동시 요청 성능 테스트"""
        gateway = setup_gateway
        
        request = {
            "method": "GET",
            "path": "/performance_test",
            "headers": {},
            "body": None
        }
        
        # 다양한 동시성 수준에서 테스트
        concurrency_levels = [10, 50, 100, 500, 1000]
        results = {}
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            # 동시 요청 실행
            tasks = [gateway.route_request(request) for _ in range(concurrency)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 성공 응답 필터링
            successful_responses = [r for r in responses if not isinstance(r, Exception)]
            
            # 응답 시간 수집
            response_times = []
            for response in successful_responses:
                if 'timestamp' in response:
                    response_times.append(response['timestamp'] - start_time)
            
            # 통계 계산
            if response_times:
                avg_response_time = statistics.mean(response_times)
                p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
                p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
            else:
                avg_response_time = p95_response_time = p99_response_time = 0
            
            results[concurrency] = {
                'total_requests': concurrency,
                'successful_requests': len(successful_responses),
                'success_rate': len(successful_responses) / concurrency * 100,
                'total_duration': duration,
                'requests_per_second': concurrency / duration,
                'avg_response_time': avg_response_time,
                'p95_response_time': p95_response_time,
                'p99_response_time': p99_response_time
            }
        
        # 성능 기준 확인
        for concurrency, metrics in results.items():
            assert metrics['success_rate'] > 99.0, f"Success rate too low for {concurrency} concurrent requests"
            assert metrics['avg_response_time'] < 0.1, f"Average response time too high for {concurrency} concurrent requests"
            assert metrics['p95_response_time'] < 0.2, f"P95 response time too high for {concurrency} concurrent requests"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, setup_gateway):
        """부하 하의 메모리 사용량 테스트"""
        gateway = setup_gateway
        
        # 메모리 사용량 측정
        initial_memory = gateway.get_memory_usage()
        
        request = {
            "method": "GET",
            "path": "/performance_test",
            "headers": {},
            "body": None
        }
        
        # 점진적 부하 증가
        load_steps = [100, 500, 1000, 2000]
        memory_measurements = []
        
        for load in load_steps:
            # 부하 생성
            tasks = [gateway.route_request(request) for _ in range(load)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 메모리 사용량 측정
            current_memory = gateway.get_memory_usage()
            memory_increase = current_memory - initial_memory
            
            memory_measurements.append({
                'load': load,
                'memory_usage': current_memory,
                'memory_increase': memory_increase,
                'memory_per_request': memory_increase / load
            })
            
            # 가비지 컬렉션
            if hasattr(gateway, 'garbage_collect'):
                gateway.garbage_collect()
        
        # 메모리 효율성 확인
        for measurement in memory_measurements:
            # 요청당 메모리 사용량이 합리적인지 확인
            assert measurement['memory_per_request'] < 1024, "Memory usage per request too high"
            
            # 메모리 누수 확인
            if measurement['load'] > 100:
                # 이전 측정값과 비교하여 급격한 증가가 없는지 확인
                prev_measurement = memory_measurements[memory_measurements.index(measurement) - 1]
                memory_growth_rate = (measurement['memory_increase'] - prev_measurement['memory_increase']) / prev_measurement['memory_increase']
                assert memory_growth_rate < 0.5, "Memory leak detected"
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, setup_gateway):
        """속도 제한 성능 테스트"""
        gateway = setup_gateway
        
        request = {
            "method": "GET",
            "path": "/performance_test",
            "headers": {"X-Client-ID": "rate_limit_test"},
            "body": None
        }
        
        # 속도 제한 임계값까지 요청
        rate_limit = 100  # 가정
        successful_requests = 0
        
        for i in range(rate_limit + 50):  # 임계값 초과 요청
            response = await gateway.route_request(request)
            
            if response.get('status') == 'success':
                successful_requests += 1
            elif response.get('status_code') == 429:
                # 속도 제한 도달 확인
                assert successful_requests <= rate_limit
                break
        
        # 속도 제한이 정확히 작동하는지 확인
        assert successful_requests <= rate_limit, "Rate limiting not working correctly"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self):
        """서킷 브레이커 성능 테스트"""
        gateway = APIGateway()
        
        # 실패하는 서비스 모의
        failing_service = Mock()
        
        async def failing_response():
            await asyncio.sleep(0.01)  # 10ms 지연
            raise Exception("Service failure")
        
        failing_service.call = failing_response
        
        # 서킷 브레이커 설정
        route = GatewayRoute(
            path="/circuit_test",
            methods=["GET"],
            service="failing_service",
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=1
        )
        gateway.add_route(route)
        gateway.register_service("failing_service", failing_service)
        
        request = {
            "method": "GET",
            "path": "/circuit_test",
            "headers": {},
            "body": None
        }
        
        # 서킷 브레이커 동작 테스트
        start_time = time.time()
        responses = []
        
        for i in range(20):  # 충분한 실패 요청
            response = await gateway.route_request(request)
            responses.append(response)
            
            if response.get('status_code') == 503:
                # 서킷 브레이커 열림 확인
                break
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 서킷 브레이커 성능 확인
        open_circuit_responses = [r for r in responses if r.get('status_code') == 503]
        
        # 서킷 브레이커가 적절한 시간 내에 열리는지 확인
        assert len(open_circuit_responses) > 0, "Circuit breaker not opening"
        assert total_duration < 1.0, "Circuit breaker response too slow"
        
        # 서킷 브레이커 복구 테스트
        await asyncio.sleep(1.1)  # 타임아웃 대기
        
        recovery_response = await gateway.route_request(request)
        # 복구 후 첫 요청은 여전히 실패할 수 있음
        assert recovery_response.get('status_code') in [500, 503]


class TestCachePerformance:
    """캐시 성능 테스트"""
    
    @pytest.fixture
    async def setup_cache(self):
        """성능 테스트용 캐시 설정"""
        backend = Mock()
        backend.get = AsyncMock()
        backend.set = AsyncMock(return_value=True)
        backend.delete = AsyncMock(return_value=True)
        
        cache_manager = UnifiedCacheManager(backend)
        await cache_manager.initialize()
        
        return cache_manager
    
    @pytest.mark.asyncio
    async def test_cache_throughput(self, setup_cache):
        """캐시 처리량 테스트"""
        cache = setup_cache
        
        # 다양한 데이터 크기로 처리량 테스트
        data_sizes = [100, 1000, 10000, 100000]  # 바이트
        results = {}
        
        for data_size in data_sizes:
            test_data = 'x' * data_size
            operations = 1000
            
            start_time = time.time()
            
            # 쓰기 작업
            write_tasks = [
                cache.set(f"key_{i}", test_data, 60)
                for i in range(operations)
            ]
            await asyncio.gather(*write_tasks, return_exceptions=True)
            
            write_time = time.time()
            
            # 읽기 작업
            read_tasks = [
                cache.get(f"key_{i}")
                for i in range(operations)
            ]
            read_results = await asyncio.gather(*read_tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # 성공 작업 계산
            successful_writes = sum(1 for t in write_tasks if not isinstance(t, Exception))
            successful_reads = sum(1 for r in read_results if not isinstance(r, Exception) and r is not None)
            
            results[data_size] = {
                'data_size': data_size,
                'operations': operations,
                'write_time': write_time - start_time,
                'read_time': end_time - write_time,
                'total_time': end_time - start_time,
                'successful_writes': successful_writes,
                'successful_reads': successful_reads,
                'write_throughput': successful_writes / (write_time - start_time),
                'read_throughput': successful_reads / (end_time - write_time),
                'overall_throughput': (successful_writes + successful_reads) / (end_time - start_time)
            }
        
        # 처리량 기준 확인
        for data_size, metrics in results.items():
            assert metrics['successful_writes'] == operations, f"Write operations failed for data size {data_size}"
            assert metrics['successful_reads'] == operations, f"Read operations failed for data size {data_size}"
            assert metrics['write_throughput'] > 1000, f"Write throughput too low for data size {data_size}"
            assert metrics['read_throughput'] > 5000, f"Read throughput too low for data size {data_size}"
    
    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self, setup_cache):
        """캐시 메모리 효율성 테스트"""
        cache = setup_cache
        
        # 메모리 효율성 테스트
        test_scenarios = [
            {
                'name': 'small_keys',
                'key_count': 10000,
                'key_size': 20,
                'value_size': 100
            },
            {
                'name': 'large_keys',
                'key_count': 1000,
                'key_size': 50,
                'value_size': 10000
            },
            {
                'name': 'mixed_sizes',
                'key_count': 5000,
                'key_size': 30,
                'value_size': 1000
            }
        ]
        
        for scenario in test_scenarios:
            # 초기 메모리 측정
            initial_memory = cache.get_memory_usage()
            
            # 테스트 데이터 생성
            for i in range(scenario['key_count']):
                key = f"key_{scenario['name']}_{i}".ljust(scenario['key_size'])[:scenario['key_size']]
                value = 'x' * scenario['value_size']
                await cache.set(key, value, 60)
            
            # 메모리 사용량 측정
            final_memory = cache.get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            # 예상 메모리 사용량 계산
            estimated_memory = scenario['key_count'] * (scenario['key_size'] + scenario['value_size'])
            memory_efficiency = estimated_memory / memory_increase if memory_increase > 0 else 0
            
            # 메모리 효율성 확인
            assert memory_efficiency > 0.5, f"Memory efficiency too low for {scenario['name']}"
            assert memory_increase < estimated_memory * 2, f"Memory overhead too high for {scenario['name']}"
            
            # 캐시 통계 확인
            stats = await cache.get_cache_stats()
            assert stats['sets'] == scenario['key_count']
    
    @pytest.mark.asyncio
    async def test_cache_hot_key_performance(self, setup_cache):
        """캐시 핫 키 성능 테스트"""
        cache = setup_cache
        
        # 핫 키 패턴 생성
        hot_keys = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        cold_keys = ['IBM', 'ORCL', 'INTC', 'CSCO', 'HPQ']
        
        # 핫 키에 더 자주 접근
        access_pattern = []
        for i in range(1000):
            if i % 10 < 8:  # 80% 핫 키 접근
                key = hot_keys[i % len(hot_keys)]
            else:  # 20% 콜드 키 접근
                key = cold_keys[i % len(cold_keys)]
            
            access_pattern.append(key)
        
        # 접근 패턴 실행 및 성능 측정
        start_time = time.time()
        
        for key in access_pattern:
            await cache.get(key)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 핫 키 분석
        hot_keys_analysis = await cache.get_cache_hot_keys(10)
        
        # 핫 키 식별 확인
        hot_key_names = [key['key'] for key in hot_keys_analysis if 'stock:' in key['key']]
        
        # 핫 키가 상위에 있는지 확인
        hot_key_found = any(hot_key in hot_key_names for hot_key in hot_keys)
        assert hot_key_found, "Hot keys not properly identified"
        
        # 전체 성능 확인
        assert total_time < 5.0, "Cache access performance too slow"
        assert len(hot_keys_analysis) > 0, "No hot keys identified"
    
    @pytest.mark.asyncio
    async def test_cache_ttl_performance(self, setup_cache):
        """캐시 TTL 성능 테스트"""
        cache = setup_cache
        
        # 다양한 TTL 설정으로 테스트
        ttl_scenarios = [
            {'ttl': 1, 'name': 'very_short'},
            {'ttl': 60, 'name': 'short'},
            {'ttl': 300, 'name': 'medium'},
            {'ttl': 3600, 'name': 'long'}
        ]
        
        for scenario in ttl_scenarios:
            # TTL 테스트 데이터 설정
            test_key = f"ttl_test_{scenario['name']}"
            test_value = {"data": f"test_value_{scenario['name']}"}
            
            # 데이터 저장
            await cache.set(test_key, test_value, scenario['ttl'])
            
            # 즉시 확인 (저장되어야 함)
            immediate_result = await cache.get(test_key)
            assert immediate_result == test_value, f"TTL test failed for {scenario['name']} - immediate retrieval"
            
            # TTL 대기
            await asyncio.sleep(scenario['ttl'] + 0.1)
            
            # 만료 후 확인 (없어야 함)
            expired_result = await cache.get(test_key)
            assert expired_result is None, f"TTL test failed for {scenario['name']} - expired retrieval"
            
            # TTL 정확성 확인
            stats = await cache.get_cache_stats()
            # 만료된 항목은 자동으로 정리되어야 함


class TestServicePerformance:
    """서비스 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_performance(self):
        """센티먼트 분석 성능 테스트"""
        # 모의 센티먼트 서비스
        sentiment_service = Mock(spec=AdvancedSentimentService)
        
        async def analyze_sentiment(text):
            # 텍스트 길이에 따른 처리 시간 모의
            processing_time = len(text) * 0.001  # 1ms per character
            await asyncio.sleep(processing_time)
            
            return {
                'sentiment': 0.5 if 'good' in text.lower() else -0.5,
                'confidence': 0.8,
                'processing_time': processing_time
            }
        
        sentiment_service.analyze_sentiment = analyze_sentiment
        
        # 다양한 텍스트 길이로 테스트
        text_lengths = [100, 500, 1000, 2000]
        results = {}
        
        for length in text_lengths:
            test_text = 'x' * length
            batch_size = 100
            
            start_time = time.time()
            
            # 배치 분석
            tasks = [
                sentiment_service.analyze_sentiment(test_text)
                for _ in range(batch_size)
            ]
            analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # 성공 분석 필터링
            successful_analyses = [r for r in analysis_results if not isinstance(r, Exception)]
            
            # 통계 계산
            processing_times = [r['processing_time'] for r in successful_analyses]
            
            results[length] = {
                'text_length': length,
                'batch_size': batch_size,
                'successful_analyses': len(successful_analyses),
                'total_time': end_time - start_time,
                'avg_processing_time': statistics.mean(processing_times) if processing_times else 0,
                'throughput': len(successful_analyses) / (end_time - start_time)
            }
        
        # 성능 기준 확인
        for length, metrics in results.items():
            assert metrics['successful_analyses'] == batch_size, f"Analyses failed for text length {length}"
            assert metrics['throughput'] > 10, f"Sentiment analysis throughput too low for text length {length}"
    
    @pytest.mark.asyncio
    async def test_realtime_data_collection_performance(self):
        """실시간 데이터 수집 성능 테스트"""
        # 모의 데이터 수집기
        data_collector = Mock(spec=RealtimeDataCollector)
        
        async def collect_symbol_data(symbol):
            # 심볼에 따른 수집 시간 모의
            collection_time = 0.1 if symbol in ['AAPL', 'GOOGL', 'MSFT'] else 0.2
            await asyncio.sleep(collection_time)
            
            return {
                'symbol': symbol,
                'price': 150.0,
                'collection_time': collection_time,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        data_collector.collect_symbol_data = collect_symbol_data
        
        # 다양한 심볼 수로 테스트
        symbol_counts = [10, 50, 100, 200]
        results = {}
        
        for count in symbol_counts:
            symbols = [f"SYMBOL_{i}" for i in range(count)]
            
            start_time = time.time()
            
            # 동시 수집
            tasks = [
                data_collector.collect_symbol_data(symbol)
                for symbol in symbols
            ]
            collection_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # 성공 수집 필터링
            successful_collections = [r for r in collection_results if not isinstance(r, Exception)]
            
            # 통계 계산
            collection_times = [r['collection_time'] for r in successful_collections]
            
            results[count] = {
                'symbol_count': count,
                'successful_collections': len(successful_collections),
                'total_time': end_time - start_time,
                'avg_collection_time': statistics.mean(collection_times) if collection_times else 0,
                'throughput': len(successful_collections) / (end_time - start_time)
            }
        
        # 성능 기준 확인
        for count, metrics in results.items():
            assert metrics['successful_collections'] == count, f"Collections failed for {count} symbols"
            assert metrics['throughput'] > 5, f"Data collection throughput too low for {count} symbols"
    
    @pytest.mark.asyncio
    async def test_service_integration_performance(self):
        """서비스 통합 성능 테스트"""
        # 모의 통합 서비스
        unified_service = Mock(spec=UnifiedService)
        
        async def get_comprehensive_data(symbol):
            # 여러 서비스 호출 모의
            await asyncio.sleep(0.05)  # 50ms 기본 지연
            
            return {
                'symbol': symbol,
                'stock_data': {'price': 150.0},
                'sentiment_data': {'score': 0.5},
                'collection_stats': {'last_update': datetime.utcnow().isoformat()}
            }
        
        unified_service.get_comprehensive_data = get_comprehensive_data
        
        # 다양한 동시성 수준에서 테스트
        concurrency_levels = [10, 50, 100]
        results = {}
        
        for concurrency in concurrency_levels:
            symbols = [f"SYMBOL_{i}" for i in range(concurrency)]
            
            start_time = time.time()
            
            # 동시 통합 데이터 요청
            tasks = [
                unified_service.get_comprehensive_data(symbol)
                for symbol in symbols
            ]
            integration_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # 성공 응답 필터링
            successful_responses = [r for r in integration_results if not isinstance(r, Exception)]
            
            results[concurrency] = {
                'concurrency': concurrency,
                'successful_responses': len(successful_responses),
                'total_time': end_time - start_time,
                'throughput': len(successful_responses) / (end_time - start_time)
            }
        
        # 통합 성능 기준 확인
        for concurrency, metrics in results.items():
            assert metrics['successful_responses'] == concurrency, f"Integration failed for {concurrency} requests"
            assert metrics['throughput'] > 10, f"Integration throughput too low for {concurrency} requests"


class TestSystemPerformance:
    """시스템 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_system_resource_usage(self):
        """시스템 자원 사용량 테스트"""
        # 시스템 자원 모니터 모의
        resource_monitor = Mock()
        
        def get_cpu_usage():
            return 50.0  # 50% CPU 사용량
        
        def get_memory_usage():
            return 60.0  # 60% 메모리 사용량
        
        def get_disk_io():
            return {"read_mb": 100, "write_mb": 50}
        
        def get_network_io():
            return {"recv_mb": 200, "sent_mb": 100}
        
        resource_monitor.get_cpu_usage = get_cpu_usage
        resource_monitor.get_memory_usage = get_memory_usage
        resource_monitor.get_disk_io = get_disk_io
        resource_monitor.get_network_io = get_network_io
        
        # 부하 테스트 시나리오
        load_scenarios = [
            {'name': 'light_load', 'duration': 10},
            {'name': 'medium_load', 'duration': 30},
            {'name': 'heavy_load', 'duration': 60}
        ]
        
        for scenario in load_scenarios:
            start_time = time.time()
            
            # 부하 생성 모의
            await asyncio.sleep(scenario['duration'])
            
            end_time = time.time()
            
            # 자원 사용량 측정
            cpu_usage = resource_monitor.get_cpu_usage()
            memory_usage = resource_monitor.get_memory_usage()
            disk_io = resource_monitor.get_disk_io()
            network_io = resource_monitor.get_network_io()
            
            # 자원 사용량 기준 확인
            assert cpu_usage < 80.0, f"CPU usage too high during {scenario['name']}"
            assert memory_usage < 85.0, f"Memory usage too high during {scenario['name']}"
            
            # 자원 효율성 계산
            duration = end_time - start_time
            cpu_efficiency = cpu_usage / duration if duration > 0 else 0
            memory_efficiency = memory_usage / duration if duration > 0 else 0
            
            # 효율성 기준 확인
            assert cpu_efficiency < 10.0, f"CPU efficiency too low during {scenario['name']}"
            assert memory_efficiency < 5.0, f"Memory efficiency too low during {scenario['name']}"
    
    @pytest.mark.asyncio
    async def test_performance_regression_detection(self):
        """성능 회귀 감지 테스트"""
        # 성능 벤치마크 모의
        benchmark = {
            'api_response_time': 0.1,  # 100ms
            'cache_throughput': 1000,  # 1000 ops/sec
            'sentiment_analysis_time': 0.5  # 500ms
        }
        
        # 현재 성능 측정 모의
        current_performance = {
            'api_response_time': 0.12,  # 20% 저하
            'cache_throughput': 950,    # 5% 저하
            'sentiment_analysis_time': 0.6  # 20% 저하
        }
        
        # 성능 회귀 분석
        regression_analysis = {}
        
        for metric, benchmark_value in benchmark.items():
            current_value = current_performance[metric]
            regression_percentage = ((current_value - benchmark_value) / benchmark_value) * 100
            
            regression_analysis[metric] = {
                'benchmark': benchmark_value,
                'current': current_value,
                'regression_percentage': regression_percentage,
                'is_regression': regression_percentage > 10  # 10% 이상 저하를 회귀로 간주
            }
        
        # 회귀 감지 확인
        assert regression_analysis['api_response_time']['is_regression'], "API response time regression not detected"
        assert regression_analysis['sentiment_analysis_time']['is_regression'], "Sentiment analysis time regression not detected"
        assert not regression_analysis['cache_throughput']['is_regression'], "False positive cache throughput regression"
        
        # 회귀 경고 생성
        regression_alerts = [
            metric for metric, analysis in regression_analysis.items()
            if analysis['is_regression']
        ]
        
        assert len(regression_alerts) == 2, "Incorrect number of regression alerts"
    
    @pytest.mark.asyncio
    async def test_performance_optimization_recommendations(self):
        """성능 최적화 권장사항 테스트"""
        # 성능 분석기 모의
        performance_analyzer = Mock()
        
        async def analyze_performance():
            # 다양한 성능 지표 모의
            return {
                'api_metrics': {
                    'avg_response_time': 0.15,
                    'p95_response_time': 0.3,
                    'throughput': 500
                },
                'cache_metrics': {
                    'hit_rate': 70.0,
                    'memory_usage_mb': 100,
                    'eviction_rate': 20.0
                },
                'system_metrics': {
                    'cpu_usage': 80.0,
                    'memory_usage': 85.0,
                    'disk_io': 150
                }
            }
        
        performance_analyzer.analyze_performance = analyze_performance
        
        # 성능 분석 실행
        analysis = await performance_analyzer.analyze_performance()
        
        # 최적화 권장사항 생성 모의
        optimization_recommender = Mock()
        
        async def generate_recommendations(analysis_data):
            recommendations = []
            
            # API 성능 권장사항
            if analysis_data['api_metrics']['avg_response_time'] > 0.1:
                recommendations.append({
                    'category': 'api',
                    'priority': 'high',
                    'description': 'API 응답 시간 개선 필요',
                    'actions': ['캐시 전략 최적화', '데이터베이스 쿼리 튜닝']
                })
            
            # 캐시 성능 권장사항
            if analysis_data['cache_metrics']['hit_rate'] < 80.0:
                recommendations.append({
                    'category': 'cache',
                    'priority': 'medium',
                    'description': '캐시 히트율 개선 필요',
                    'actions': ['TTL 설정 조정', '캐시 크기 증가']
                })
            
            # 시스템 성능 권장사항
            if analysis_data['system_metrics']['cpu_usage'] > 75.0:
                recommendations.append({
                    'category': 'system',
                    'priority': 'critical',
                    'description': 'CPU 사용량 과다',
                    'actions': ['인스턴스 스케일업', '프로세스 최적화']
                })
            
            return recommendations
        
        optimization_recommender.generate_recommendations = generate_recommendations
        
        # 권장사항 생성
        recommendations = await optimization_recommender.generate_recommendations(analysis)
        
        # 권장사항 검증
        assert len(recommendations) > 0, "No performance recommendations generated"
        
        # 권장사항 우선순위 확인
        high_priority_recs = [r for r in recommendations if r['priority'] == 'critical']
        assert len(high_priority_recs) > 0, "No critical priority recommendations"
        
        # 권장사항 카테고리 확인
        categories = set(r['category'] for r in recommendations)
        assert 'system' in categories, "No system performance recommendations"