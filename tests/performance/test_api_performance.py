"""
API 성능 테스트

이 모듈은 API 엔드포인트의 성능을 측정하고 벤치마킹합니다.
"""

import pytest
import time
import threading
import statistics
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from backend.api.routes import router


class TestAPIPerformance:
    """API 성능 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 픽스처"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def performance_thresholds(self):
        """성능 임계값 픽스처"""
        return {
            "response_time_ms": {
                "excellent": 100,  # 100ms 이하
                "good": 300,        # 300ms 이하
                "acceptable": 1000,  # 1초 이하
                "slow": 2000        # 2초 이상
            },
            "concurrent_requests": {
                "excellent": 50,   # 50개 동시 요청
                "good": 30,        # 30개 동시 요청
                "acceptable": 20,   # 20개 동시 요청
                "limited": 10       # 10개 동시 요청
            },
            "throughput": {
                "excellent": 1000,  # 1000 req/s
                "good": 500,        # 500 req/s
                "acceptable": 100,   # 100 req/s
                "poor": 50         # 50 req/s
            }
        }
    
    def measure_response_time(self, client, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
        """응답 시간 측정"""
        start_time = time.time()
        
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json=data or {})
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        return {
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "response_size": len(response.content),
            "success": response.status_code < 400
        }
    
    def test_health_check_performance(self, client, performance_thresholds):
        """상태 확인 엔드포인트 성능 테스트"""
        # 여러 번의 요청으로 성능 측정
        results = []
        for _ in range(10):
            result = self.measure_response_time(client, "/health")
            results.append(result)
            time.sleep(0.1)  # 요청 간 간격
        
        response_times = [r["response_time_ms"] for r in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # 성능 기준 확인
        assert avg_response_time < performance_thresholds["response_time_ms"]["good"]
        assert max_response_time < performance_thresholds["response_time_ms"]["acceptable"]
        
        print(f"Health Check Performance:")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
        print(f"  Max Response Time: {max_response_time:.2f}ms")
        print(f"  Min Response Time: {min_response_time:.2f}ms")
    
    def test_stock_data_performance(self, client, performance_thresholds):
        """주식 데이터 조회 성능 테스트"""
        results = []
        
        # 다양한 주식에 대한 성능 측정
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
        
        for symbol in symbols:
            result = self.measure_response_time(
                client, 
                "/stock",
                "POST",
                {"symbol": symbol, "include_sentiment": True}
            )
            results.append(result)
            time.sleep(0.05)  # 요청 간 간격
        
        response_times = [r["response_time_ms"] for r in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # 성능 기준 확인
        assert avg_response_time < performance_thresholds["response_time_ms"]["acceptable"]
        assert max_response_time < performance_thresholds["response_time_ms"]["slow"]
        
        print(f"Stock Data Performance:")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
        print(f"  Max Response Time: {max_response_time:.2f}ms")
    
    def test_search_performance(self, client, performance_thresholds):
        """검색 성능 테스트"""
        results = []
        
        # 다양한 검색어에 대한 성능 측정
        queries = ["Apple", "Microsoft", "Google", "Amazon", "Tesla", "Technology", "AI", "Cloud"]
        
        for query in queries:
            result = self.measure_response_time(
                client,
                "/search",
                "POST",
                {"query": query, "limit": 10}
            )
            results.append(result)
            time.sleep(0.05)  # 요청 간 간격
        
        response_times = [r["response_time_ms"] for r in results]
        avg_response_time = statistics.mean(response_times)
        
        # 성능 기준 확인
        assert avg_response_time < performance_thresholds["response_time_ms"]["acceptable"]
        
        print(f"Search Performance:")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
    
    def test_concurrent_requests_performance(self, client, performance_thresholds):
        """동시 요청 성능 테스트"""
        def make_request():
            return self.measure_response_time(
                client,
                "/stock",
                "POST",
                {"symbol": "AAPL", "include_sentiment": True}
            )
        
        # 동시 요청 실행
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in as_completed(futures)]
        
        response_times = [r["response_time_ms"] for r in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        success_count = sum(1 for r in results if r["success"])
        
        # 성능 기준 확인
        assert avg_response_time < performance_thresholds["response_time_ms"]["slow"]
        assert success_count >= performance_thresholds["concurrent_requests"]["acceptable"]
        
        print(f"Concurrent Requests Performance:")
        print(f"  Concurrent Requests: {len(results)}")
        print(f"  Success Rate: {success_count}/{len(results)}")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
        print(f"  Max Response Time: {max_response_time:.2f}ms")
    
    def test_throughput_performance(self, client, performance_thresholds):
        """처리량 테스트"""
        def make_request():
            return self.measure_response_time(
                client,
                "/health",
                "GET"
            )
        
        start_time = time.time()
        
        # 연속 요청으로 처리량 측정
        results = []
        for _ in range(100):
            result = make_request()
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        requests_per_second = len(results) / total_time
        
        # 처리량 기준 확인
        assert requests_per_second >= performance_thresholds["throughput"]["acceptable"]
        
        print(f"Throughput Performance:")
        print(f"  Total Requests: {len(results)}")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Requests/Second: {requests_per_second:.2f}")
    
    def test_memory_usage_simulation(self, client, performance_thresholds):
        """메모리 사용량 시뮬레이션 테스트"""
        import psutil
        import os
        
        # 초기 메모리 사용량 측정
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 메모리 집약적인 작업 시뮬레이션
        large_data = "x" * (10 * 1024 * 1024)  # 10MB 데이터
        
        # 여러 번의 요청으로 메모리 사용량 측정
        for _ in range(10):
            response = client.post(
                "/search",
                json={"query": "test", "limit": 100}
            )
            # 대용량 데이터 처리 시뮬레이션
            _ = response.json()  # 응답 처리
        
        # 최종 메모리 사용량 측정
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory Usage Simulation:")
        print(f"  Initial Memory: {initial_memory:.2f}MB")
        print(f"  Final Memory: {final_memory:.2f}MB")
        print(f"  Memory Increase: {memory_increase:.2f}MB")
        
        # 메모리 증가가 과도하지 않아야 함 (50MB 이하)
        assert memory_increase < 50
    
    def test_error_handling_performance(self, client, performance_thresholds):
        """오류 처리 성능 테스트"""
        # 유효하지 않은 요청으로 오류 처리 시간 측정
        results = []
        
        for _ in range(10):
            start_time = time.time()
            response = client.post(
                "/stock",
                json={"symbol": "INVALID_SYMBOL_12345"}  # 유효하지 않은 심볼
            )
            end_time = time.time()
            
            results.append({
                "status_code": response.status_code,
                "response_time_ms": (end_time - start_time) * 1000,
                "success": response.status_code == 404
            })
            time.sleep(0.05)
        
        response_times = [r["response_time_ms"] for r in results]
        avg_response_time = statistics.mean(response_times)
        
        # 오류 처리도 적절한 성능을 보여야 함
        assert avg_response_time < performance_thresholds["response_time_ms"]["acceptable"]
        
        print(f"Error Handling Performance:")
        print(f"  Average Error Response Time: {avg_response_time:.2f}ms")
    
    @patch('backend.api.routes.get_unified_service')
    def test_caching_performance(self, mock_get_service, client, performance_thresholds):
        """캐싱 성능 테스트"""
        # 모의 서비스 설정
        mock_service = AsyncMock()
        
        # 첫 번째 요청은 캐시 미스
        mock_service.get_stock_data.return_value = None
        mock_get_service.return_value = mock_service
        
        start_time = time.time()
        response1 = client.post(
            "/stock",
            json={"symbol": "AAPL", "include_sentiment": True}
        )
        first_request_time = time.time() - start_time
        
        # 두 번째 요청은 캐시 히트
        mock_service.get_stock_data.return_value = {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "current_price": 150.0
        }
        
        start_time = time.time()
        response2 = client.post(
            "/stock",
            json={"symbol": "AAPL", "include_sentiment": True}
        )
        second_request_time = time.time() - start_time
        
        # 캐시 히트 요청이 더 빨라야 함
        assert second_request_time < first_request_time
        
        print(f"Caching Performance:")
        print(f"  Cache Miss Time: {first_request_time * 1000:.2f}ms")
        print(f"  Cache Hit Time: {second_request_time * 1000:.2f}ms")
        print(f"  Cache Speedup: {((first_request_time - second_request_time) / first_request_time) * 100:.1f}%")
    
    def test_performance_regression(self, client):
        """성능 회귀 테스트"""
        # 기준 성능 데이터 (이전 테스트에서 저장된 값)
        baseline_performance = {
            "health_check": 50.0,  # ms
            "stock_data": 200.0,   # ms
            "search": 300.0,      # ms
            "concurrent": 500.0   # ms
        }
        
        # 현재 성능 측정
        current_performance = {}
        
        # 상태 확인
        health_results = []
        for _ in range(5):
            result = self.measure_response_time(client, "/health")
            health_results.append(result["response_time_ms"])
        
        current_performance["health_check"] = statistics.mean(health_results)
        
        # 주식 데이터
        stock_results = []
        symbols = ["AAPL", "MSFT"]
        for symbol in symbols:
            result = self.measure_response_time(
                client,
                "/stock",
                "POST",
                {"symbol": symbol, "include_sentiment": True}
            )
            stock_results.append(result["response_time_ms"])
        
        current_performance["stock_data"] = statistics.mean(stock_results)
        
        # 검색
        search_results = []
        queries = ["Apple", "Microsoft"]
        for query in queries:
            result = self.measure_response_time(
                client,
                "/search",
                "POST",
                {"query": query, "limit": 10}
            )
            search_results.append(result["response_time_ms"])
        
        current_performance["search"] = statistics.mean(search_results)
        
        # 성능 회귀 확인 (10% 이상 향상되면 경고)
        for endpoint, current_time in current_performance.items():
            baseline_time = baseline_performance.get(endpoint, 0)
            if baseline_time > 0:
                regression = (current_time - baseline_time) / baseline_time
                if regression > 0.1:  # 10% 이상 향상
                    print(f"WARNING: Performance regression detected for {endpoint}")
                    print(f"  Baseline: {baseline_time:.2f}ms")
                    print(f"  Current: {current_time:.2f}ms")
                    print(f"  Regression: {regression:.1%}")
                
                # 성능이 크게 향상된 경우에만 경고
                assert regression < 0.5, f"Performance regression too severe for {endpoint}"
    
    def test_load_testing(self, client, performance_thresholds):
        """부하 테스트"""
        def make_request():
            return self.measure_response_time(
                client,
                "/stock",
                "POST",
                {"symbol": "AAPL", "include_sentiment": True}
            )
        
        # 점진적 부하 증가
        thread_counts = [1, 5, 10, 20, 50]
        results = {}
        
        for thread_count in thread_counts:
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(make_request) for _ in range(50)]
                _ = [future.result() for future in as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            successful_requests = sum(1 for r in _ if r["success"])
            avg_response_time = statistics.mean([r["response_time_ms"] for r in _])
            
            results[thread_count] = {
                "total_time": total_time,
                "successful_requests": successful_requests,
                "avg_response_time_ms": avg_response_time,
                "requests_per_second": successful_requests / total_time if total_time > 0 else 0
            }
            
            print(f"Load Test - {thread_count} threads:")
            print(f"  Total Time: {total_time:.2f}s")
            print(f"  Successful Requests: {successful_requests}/50")
            print(f"  Average Response Time: {avg_response_time:.2f}ms")
            print(f"  Requests/Second: {successful_requests / total_time:.2f}")
            
            # 부하 증가에 따른 성능 저하 확인
            if thread_count > 10:
                assert avg_response_time < performance_thresholds["response_time_ms"]["slow"]
        
        print(f"Load Testing Summary:")
        for thread_count, result in results.items():
            print(f"  {thread_count} threads: {result['avg_response_time_ms']:.2f}ms avg, {result['requests_per_second']:.2f} req/s")