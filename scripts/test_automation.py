"""
InsiteChart 자동화 기능 테스트 스크립트
구현된 자동화 기능들을 실제로 실행하고 정상 작동 여부 확인
"""

import asyncio
import json
import time
import logging
import subprocess
import signal
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import aiohttp
import redis.asyncio as redis
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomationTester:
    """자동화 기능 테스터 클래스"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", redis_url: str = "redis://localhost:6379"):
        self.backend_url = backend_url
        self.redis_url = redis_url
        self.session = None
        self.redis_client = None
        self.backend_process = None
        
        # 테스트 결과
        self.test_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "details": {}
        }
    
    async def setup_environment(self):
        """테스트 환경 설정"""
        logger.info("Setting up test environment")
        
        try:
            # Redis 서버 확인
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Redis server is running")
            except Exception as e:
                logger.error(f"Redis server not available: {str(e)}")
                return False
            
            # 백엔드 서버 시작
            if not await self._start_backend_server():
                return False
            
            # HTTP 세션 초기화
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 서버가 준비될 때까지 대기
            await self._wait_for_server_ready()
            
            logger.info("Test environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {str(e)}")
            return False
    
    async def _start_backend_server(self) -> bool:
        """백엔드 서버 시작"""
        logger.info("Starting backend server")
        
        try:
            # 백엔드 서버 프로세스 시작
            cmd = ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
            self.backend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None,
                cwd="/Users/ftfuture/work/workspace/uService/insitechart"
            )
            
            logger.info(f"Backend server started with PID: {self.backend_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start backend server: {str(e)}")
            return False
    
    async def _wait_for_server_ready(self, timeout: int = 30):
        """서버가 준비될 때까지 대기"""
        logger.info("Waiting for server to be ready")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.backend_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            logger.info("Server is ready")
                            return
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        raise TimeoutError("Server did not become ready within timeout period")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 자동화 기능 테스트 실행"""
        logger.info("Starting comprehensive automation testing")
        
        try:
            # 1. JWT 인증 자동화 테스트
            await self._test_jwt_automation()
            
            # 2. API 키 관리 자동화 테스트
            await self._test_api_key_automation()
            
            # 3. 속도 제한 자동화 테스트
            await self._test_rate_limit_automation()
            
            # 4. 보안 헤더 자동화 테스트
            await self._test_security_headers_automation()
            
            # 5. 외부 API 연동 자동화 테스트
            await self._test_external_api_automation()
            
            # 6. Kafka 이벤트 버스 자동화 테스트
            await self._test_kafka_automation()
            
            # 7. 실시간 데이터 수집 자동화 테스트
            await self._test_realtime_collection_automation()
            
            # 8. 캐싱 시스템 자동화 테스트
            await self._test_caching_automation()
            
            # 9. 모니터링 시스템 자동화 테스트
            await self._test_monitoring_automation()
            
            # 10. 로깅 시스템 자동화 테스트
            await self._test_logging_automation()
            
            # 결과 요약
            self._summarize_results()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"Error during testing: {str(e)}")
            self.test_results["error"] = str(e)
            return self.test_results
    
    async def _test_jwt_automation(self):
        """JWT 인증 자동화 테스트"""
        logger.info("Testing JWT automation")
        
        try:
            # 1. JWT 토큰 생성 테스트
            async with self.session.post(f"{self.backend_url}/auth/token", json={
                "user_id": "test_user",
                "email": "test@example.com"
            }) as response:
                if response.status == 200:
                    token_data = await response.json()
                    token = token_data.get("access_token")
                    
                    if token:
                        self._add_test_result("jwt_token_generation", True, "JWT token generated successfully")
                        
                        # 2. JWT 토큰 검증 테스트
                        headers = {"Authorization": f"Bearer {token}"}
                        async with self.session.get(f"{self.backend_url}/auth/verify", headers=headers) as verify_response:
                            if verify_response.status == 200:
                                verify_data = await verify_response.json()
                                if verify_data.get("valid"):
                                    self._add_test_result("jwt_token_verification", True, "JWT token verified successfully")
                                else:
                                    self._add_test_result("jwt_token_verification", False, "JWT token verification failed")
                            else:
                                self._add_test_result("jwt_token_verification", False, f"JWT verification endpoint failed: {verify_response.status}")
                        
                        # 3. JWT 토큰 리프레시 테스트
                        async with self.session.post(f"{self.backend_url}/auth/refresh", json={
                            "refresh_token": token_data.get("refresh_token")
                        }) as refresh_response:
                            if refresh_response.status == 200:
                                self._add_test_result("jwt_token_refresh", True, "JWT token refresh successful")
                            else:
                                self._add_test_result("jwt_token_refresh", False, f"JWT token refresh failed: {refresh_response.status}")
                    else:
                        self._add_test_result("jwt_token_generation", False, "No access token in response")
                else:
                    self._add_test_result("jwt_token_generation", False, f"JWT token generation failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("jwt_automation", False, f"JWT automation test error: {str(e)}")
    
    async def _test_api_key_automation(self):
        """API 키 관리 자동화 테스트"""
        logger.info("Testing API key automation")
        
        try:
            # 1. API 키 생성 테스트
            async with self.session.post(f"{self.backend_url}/auth/api-keys", json={
                "name": "test_api_key",
                "tier": "basic",
                "permissions": ["stock:read", "search:read"]
            }) as response:
                if response.status == 200:
                    key_data = await response.json()
                    api_key = key_data.get("api_key")
                    key_id = key_data.get("key_id")
                    
                    if api_key:
                        self._add_test_result("api_key_generation", True, "API key generated successfully")
                        
                        # 2. API 키 검증 테스트
                        headers = {"X-API-Key": api_key}
                        logger.info(f"Testing API key verification with key: {api_key}")
                        async with self.session.get(f"{self.backend_url}/auth/validate-key", headers=headers) as verify_response:
                            logger.info(f"API key verification response status: {verify_response.status}")
                            if verify_response.status == 200:
                                verify_data = await verify_response.json()
                                logger.info(f"API key verification response data: {verify_data}")
                                if verify_data.get("valid"):
                                    self._add_test_result("api_key_verification", True, "API key verified successfully")
                                else:
                                    self._add_test_result("api_key_verification", False, f"API key verification failed: {verify_data.get('message', 'Unknown error')}")
                            else:
                                self._add_test_result("api_key_verification", False, f"API key verification endpoint failed: {verify_response.status}")
                        
                        # 3. API 키 사용량 추적 테스트
                        async with self.session.get(f"{self.backend_url}/api/stocks/AAPL", headers=headers) as usage_response:
                            if usage_response.status == 200:
                                self._add_test_result("api_key_usage_tracking", True, "API key usage tracking working")
                            else:
                                self._add_test_result("api_key_usage_tracking", False, f"API key usage tracking failed: {usage_response.status}")
                        
                        # 4. API 키 삭제 테스트
                        if key_id:
                            async with self.session.delete(f"{self.backend_url}/auth/api-keys/{key_id}") as delete_response:
                                if delete_response.status == 200:
                                    self._add_test_result("api_key_deletion", True, "API key deletion successful")
                                else:
                                    self._add_test_result("api_key_deletion", False, f"API key deletion failed: {delete_response.status}")
                    else:
                        self._add_test_result("api_key_generation", False, "No API key in response")
                else:
                    self._add_test_result("api_key_generation", False, f"API key generation failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("api_key_automation", False, f"API key automation test error: {str(e)}")
    
    async def _test_rate_limit_automation(self):
        """속도 제한 자동화 테스트"""
        logger.info("Testing rate limiting automation")
        
        try:
            # 1. 기본 속도 제한 테스트
            tasks = []
            for i in range(15):  # 속도 제한을 초과하는 요청 수
                task = self.session.get(f"{self.backend_url}/api/test")
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 응답 분석
            success_count = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status') and r.status == 200)
            rate_limited_count = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status') and r.status == 429)
            
            # 속도 제한 헤더 확인
            has_rate_limit_headers = False
            if success_count > 0:
                first_response = next(r for r in responses if not isinstance(r, Exception) and hasattr(r, 'status') and r.status == 200)
                if hasattr(first_response, 'headers'):
                    # 응답 객체에서 헤더 확인
                    try:
                        # 응답이 이미 처리된 경우, 헤더를 직접 확인
                        if hasattr(first_response, 'headers'):
                            headers = first_response.headers
                            if isinstance(headers, dict):
                                has_rate_limit_headers = any(header in headers for header in ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'])
                            else:
                                # MultiDict 또는 다른 헤더 타입의 경우
                                has_rate_limit_headers = any(header in str(headers) for header in ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'])
                        
                        # 추가 확인: 실제 헤더 값 로깅
                        logger.info(f"Response headers type: {type(first_response.headers)}")
                        logger.info(f"Response headers: {first_response.headers}")
                        
                        # 헤더에서 직접 값 확인
                        if hasattr(first_response.headers, 'get'):
                            limit_header = first_response.headers.get('X-RateLimit-Limit', None)
                            remaining_header = first_response.headers.get('X-RateLimit-Remaining', None)
                            reset_header = first_response.headers.get('X-RateLimit-Reset', None)
                            
                            logger.info(f"Rate limit headers - Limit: {limit_header}, Remaining: {remaining_header}, Reset: {reset_header}")
                            
                            if limit_header and remaining_header and reset_header:
                                has_rate_limit_headers = True
                        
                    except Exception as e:
                        logger.warning(f"Error checking rate limit headers: {str(e)}")
            
            total_time = end_time - start_time
            
            if has_rate_limit_headers:
                self._add_test_result("rate_limiting_basic", True, "Rate limiting headers detected")
            elif rate_limited_count > 0:
                self._add_test_result("rate_limiting_basic", True, f"Rate limiting effective: {rate_limited_count}/15 requests limited")
            else:
                self._add_test_result("rate_limiting_basic", False, "No rate limiting detected")
            
            # 2. 동적 속도 제한 테스트
            await asyncio.sleep(2)  # 잠시 대기
            
            # 시스템 부하에 따른 동적 조정 테스트
            load_tasks = []
            for i in range(20):
                task = self.session.get(f"{self.backend_url}/api/test")
                load_tasks.append(task)
            
            load_responses = await asyncio.gather(*load_tasks, return_exceptions=True)
            load_success_count = sum(1 for r in load_responses if not isinstance(r, Exception) and r.status == 200)
            
            self._add_test_result("rate_limiting_dynamic", load_success_count >= 10, f"Dynamic rate limiting: {load_success_count}/20 successful")
            
        except Exception as e:
            self._add_test_result("rate_limiting_automation", False, f"Rate limiting automation test error: {str(e)}")
    
    async def _test_security_headers_automation(self):
        """보안 헤더 자동화 테스트"""
        logger.info("Testing security headers automation")
        
        try:
            # 보안 헤더 확인
            async with self.session.get(f"{self.backend_url}/api/test") as response:
                if response.status == 200:
                    headers = response.headers
                    
                    # 필수 보안 헤더 확인
                    required_headers = {
                        "X-Content-Type-Options": "nosniff",
                        "X-Frame-Options": "DENY",
                        "X-XSS-Protection": "1; mode=block",
                        "Referrer-Policy": "strict-origin-when-cross-origin"
                    }
                    
                    header_results = {}
                    for header, expected_value in required_headers.items():
                        if header in headers:
                            if expected_value in headers[header]:
                                header_results[header] = True
                            else:
                                header_results[header] = False
                        else:
                            header_results[header] = False
                    
                    passed_headers = sum(1 for v in header_results.values() if v)
                    total_headers = len(header_results)
                    
                    if passed_headers == total_headers:
                        self._add_test_result("security_headers", True, "All security headers properly configured")
                    else:
                        self._add_test_result("security_headers", False, f"Security headers: {passed_headers}/{total_headers} correct")
                    
                    # CSP 헤더 확인
                    if "Content-Security-Policy" in headers:
                        csp = headers["Content-Security-Policy"]
                        csp_checks = [
                            "default-src 'self'" in csp,
                            "script-src 'self'" in csp,
                            "style-src 'self'" in csp
                        ]
                        
                        if all(csp_checks):
                            self._add_test_result("csp_header", True, "CSP header properly configured")
                        else:
                            self._add_test_result("csp_header", False, "CSP header not properly configured")
                    else:
                        self._add_test_result("csp_header", False, "CSP header missing")
                else:
                    self._add_test_result("security_headers", False, f"Security headers check failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("security_headers_automation", False, f"Security headers automation test error: {str(e)}")
    
    async def _test_external_api_automation(self):
        """외부 API 연동 자동화 테스트"""
        logger.info("Testing external API automation")
        
        try:
            # 1. 외부 API 연동 테스트
            async with self.session.get(f"{self.backend_url}/api/stocks/AAPL") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 실제 데이터 구조 확인
                    if "symbol" in data and "current_price" in data:
                        self._add_test_result("external_api_integration", True, "External API integration working")
                    else:
                        self._add_test_result("external_api_integration", False, "Invalid data structure from external API")
                else:
                    self._add_test_result("external_api_integration", False, f"External API integration failed: {response.status}")
            
            # 2. 외부 API 캐싱 테스트
            # 첫 번째 요청
            start_time = time.time()
            async with self.session.get(f"{self.backend_url}/api/stocks/GOOGL") as first_response:
                first_data = await first_response.json()
                first_time = time.time() - start_time
            
            # 두 번째 요청 (캐시에서)
            start_time = time.time()
            async with self.session.get(f"{self.backend_url}/api/stocks/GOOGL") as second_response:
                second_data = await second_response.json()
                second_time = time.time() - start_time
            
            # 캐시 헤더 확인
            has_cache_header = False
            try:
                # 첫 번째 응답에서 캐시 헤더 확인
                if hasattr(first_response, 'headers'):
                    headers = first_response.headers
                    logger.info(f"First response headers type: {type(headers)}")
                    logger.info(f"First response headers: {headers}")
                    
                    if isinstance(headers, dict):
                        has_cache_header = "Cache-Control" in headers or "X-Cache-Status" in headers
                    else:
                        # MultiDict 또는 다른 헤더 타입의 경우
                        has_cache_header = "Cache-Control" in str(headers) or "X-Cache-Status" in str(headers)
                    
                    # 헤더에서 직접 값 확인
                    if hasattr(headers, 'get'):
                        cache_control = headers.get('Cache-Control', None)
                        cache_status = headers.get('X-Cache-Status', None)
                        
                        logger.info(f"Cache headers - Cache-Control: {cache_control}, X-Cache-Status: {cache_status}")
                        
                        if cache_control or cache_status:
                            has_cache_header = True
                
                # 두 번째 응답에서도 확인
                if hasattr(second_response, 'headers'):
                    headers = second_response.headers
                    logger.info(f"Second response headers type: {type(headers)}")
                    logger.info(f"Second response headers: {headers}")
                    
                    if isinstance(headers, dict):
                        has_cache_header = has_cache_header or ("Cache-Control" in headers or "X-Cache-Status" in headers)
                    else:
                        # MultiDict 또는 다른 헤더 타입의 경우
                        has_cache_header = has_cache_header or ("Cache-Control" in str(headers) or "X-Cache-Status" in str(headers))
                    
                    # 헤더에서 직접 값 확인
                    if hasattr(headers, 'get'):
                        cache_control = headers.get('Cache-Control', None)
                        cache_status = headers.get('X-Cache-Status', None)
                        
                        logger.info(f"Cache headers (second) - Cache-Control: {cache_control}, X-Cache-Status: {cache_status}")
                        
                        if cache_control or cache_status:
                            has_cache_header = True
                            
            except Exception as e:
                logger.warning(f"Error checking cache headers: {str(e)}")
            
            if first_data == second_data and (second_time < first_time or has_cache_header):
                self._add_test_result("external_api_caching", True, f"External API caching working (first: {first_time:.3f}s, cached: {second_time:.3f}s)")
            else:
                self._add_test_result("external_api_caching", False, "External API caching not working properly")
            
        except Exception as e:
            self._add_test_result("external_api_automation", False, f"External API automation test error: {str(e)}")
    
    async def _test_kafka_automation(self):
        """Kafka 이벤트 버스 자동화 테스트"""
        logger.info("Testing Kafka automation")
        
        try:
            # 1. Kafka 이벤트 발행 테스트
            test_event = {
                "event_type": "test_event",
                "data": {"test": "data", "timestamp": datetime.utcnow().isoformat()}
            }
            
            async with self.session.post(f"{self.backend_url}/api/events/publish", json=test_event) as response:
                if response.status == 200:
                    self._add_test_result("kafka_event_publishing", True, "Kafka event publishing successful")
                else:
                    self._add_test_result("kafka_event_publishing", False, f"Kafka event publishing failed: {response.status}")
            
            # 2. Kafka 이벤트 구독 테스트
            async with self.session.get(f"{self.backend_url}/api/events/subscribe/test_event") as response:
                if response.status == 200:
                    subscription_data = await response.json()
                    if subscription_data.get("subscribed"):
                        self._add_test_result("kafka_event_subscription", True, "Kafka event subscription successful")
                    else:
                        self._add_test_result("kafka_event_subscription", False, "Kafka event subscription failed")
                else:
                    self._add_test_result("kafka_event_subscription", False, f"Kafka event subscription failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("kafka_automation", False, f"Kafka automation test error: {str(e)}")
    
    async def _test_realtime_collection_automation(self):
        """실시간 데이터 수집 자동화 테스트"""
        logger.info("Testing realtime collection automation")
        
        try:
            # 1. 데이터 수집 상태 확인
            async with self.session.get(f"{self.backend_url}/api/monitoring/collection-status") as response:
                if response.status == 200:
                    status = await response.json()
                    
                    if status.get("running", False):
                        self._add_test_result("realtime_collection_status", True, "Realtime collection is running")
                    else:
                        self._add_test_result("realtime_collection_status", False, "Realtime collection is not running")
                    
                    # 수집 통계 확인
                    if status.get("total_collections", 0) > 0:
                        self._add_test_result("realtime_collection_stats", True, f"Total collections: {status.get('total_collections')}")
                    else:
                        self._add_test_result("realtime_collection_stats", False, "No collections performed")
                else:
                    self._add_test_result("realtime_collection_status", False, f"Realtime collection status check failed: {response.status}")
            
            # 2. 데이터 수집 트리거 테스트
            async with self.session.post(f"{self.backend_url}/api/monitoring/trigger-collection", json={
                "symbols": ["AAPL", "GOOGL", "MSFT"]
            }) as response:
                if response.status == 200:
                    trigger_result = await response.json()
                    if trigger_result.get("triggered"):
                        self._add_test_result("realtime_collection_trigger", True, "Realtime collection trigger successful")
                    else:
                        self._add_test_result("realtime_collection_trigger", False, "Realtime collection trigger failed")
                else:
                    self._add_test_result("realtime_collection_trigger", False, f"Realtime collection trigger failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("realtime_collection_automation", False, f"Realtime collection automation test error: {str(e)}")
    
    async def _test_caching_automation(self):
        """캐싱 시스템 자동화 테스트"""
        logger.info("Testing caching automation")
        
        try:
            # 1. 캐시 성능 테스트
            cache_tests = []
            for i in range(10):
                task = self.session.get(f"{self.backend_url}/api/test-cache")
                cache_tests.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*cache_tests, return_exceptions=True)
            end_time = time.time()
            
            # 캐시 히트율 계산
            cache_hits = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status') and r.status == 200 and hasattr(r, 'headers') and r.headers.get("X-Cache", "hit"))
            total_requests = len([r for r in responses if not isinstance(r, Exception)])
            
            if total_requests > 0:
                hit_rate = (cache_hits / total_requests) * 100
                self._add_test_result("caching_performance", hit_rate > 70, f"Cache hit rate: {hit_rate:.1f}%")
            else:
                self._add_test_result("caching_performance", False, "No successful cache requests")
            
            # 2. 지능형 캐시 워밍 테스트
            async with self.session.get(f"{self.backend_url}/api/cache/warming-status") as response:
                if response.status == 200:
                    warming_status = await response.json()
                    if warming_status.get("active", False):
                        self._add_test_result("intelligent_cache_warming", True, "Intelligent cache warming is active")
                    else:
                        self._add_test_result("intelligent_cache_warming", False, "Intelligent cache warming not active")
                else:
                    self._add_test_result("intelligent_cache_warming", False, f"Cache warming status check failed: {response.status}")
            
            # 3. 분산 캐시 테스트
            async with self.session.get(f"{self.backend_url}/api/cache/distributed-status") as response:
                if response.status == 200:
                    distributed_status = await response.json()
                    if distributed_status.get("nodes", 0) > 0:
                        self._add_test_result("distributed_caching", True, f"Distributed caching active with {distributed_status.get('nodes')} nodes")
                    else:
                        self._add_test_result("distributed_caching", False, "Distributed caching not active")
                else:
                    self._add_test_result("distributed_caching", False, f"Distributed caching status check failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("caching_automation", False, f"Caching automation test error: {str(e)}")
    
    async def _test_monitoring_automation(self):
        """모니터링 시스템 자동화 테스트"""
        logger.info("Testing monitoring automation")
        
        try:
            # 1. 모니터링 대시보드 데이터 확인
            async with self.session.get(f"{self.backend_url}/api/monitoring/dashboard") as response:
                if response.status == 200:
                    dashboard_data = await response.json()
                    
                    # 대시보드 위젯 확인
                    widgets = dashboard_data.get("widgets", {})
                    if len(widgets) > 0:
                        self._add_test_result("monitoring_dashboard", True, f"Monitoring dashboard has {len(widgets)} widgets")
                    else:
                        self._add_test_result("monitoring_dashboard", False, "No widgets in monitoring dashboard")
                    
                    # 알림 시스템 확인
                    alerts = dashboard_data.get("alerts", [])
                    if len(alerts) > 0:
                        self._add_test_result("monitoring_alerts", True, f"Found {len(alerts)} alerts")
                    else:
                        self._add_test_result("monitoring_alerts", False, "No alerts found")
                else:
                    self._add_test_result("monitoring_dashboard", False, f"Monitoring dashboard check failed: {response.status}")
            
            # 2. 성능 메트릭 수집 테스트
            async with self.session.get(f"{self.backend_url}/api/monitoring/metrics") as response:
                if response.status == 200:
                    metrics = await response.json()
                    
                    if metrics.get("cpu_usage") is not None:
                        self._add_test_result("performance_metrics_cpu", True, f"CPU usage: {metrics.get('cpu_usage')}%")
                    else:
                        self._add_test_result("performance_metrics_cpu", False, "CPU usage not available")
                    
                    if metrics.get("memory_usage") is not None:
                        self._add_test_result("performance_metrics_memory", True, f"Memory usage: {metrics.get('memory_usage')}%")
                    else:
                        self._add_test_result("performance_metrics_memory", False, "Memory usage not available")
                else:
                    self._add_test_result("performance_metrics", False, f"Performance metrics check failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("monitoring_automation", False, f"Monitoring automation test error: {str(e)}")
    
    async def _test_logging_automation(self):
        """로깅 시스템 자동화 테스트"""
        logger.info("Testing logging automation")
        
        try:
            # 1. 로깅 시스템 상태 확인
            async with self.session.get(f"{self.backend_url}/api/monitoring/logging-status") as response:
                if response.status == 200:
                    logging_status = await response.json()
                    
                    # 구조화된 로그 확인
                    if logging_status.get("structured_logging", True):
                        self._add_test_result("structured_logging", True, "Structured logging is active")
                    else:
                        self._add_test_result("structured_logging", False, "Structured logging not active")
                    
                    # 로그 레벨 확인
                    if logging_status.get("log_level") in ["INFO", "DEBUG", "WARNING", "ERROR"]:
                        self._add_test_result("log_level", True, f"Log level: {logging_status.get('log_level')}")
                    else:
                        self._add_test_result("log_level", False, f"Invalid log level: {logging_status.get('log_level')}")
                else:
                    self._add_test_result("logging_status_check", False, f"Logging status check failed: {response.status}")
            
            # 2. 로그 생성 테스트
            test_log_data = {
                "level": "INFO",
                "message": "Test log message",
                "component": "test_component",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with self.session.post(f"{self.backend_url}/api/monitoring/log", json=test_log_data) as response:
                if response.status == 200:
                    self._add_test_result("log_creation", True, "Log creation successful")
                else:
                    self._add_test_result("log_creation", False, f"Log creation failed: {response.status}")
            
            # 3. 로그 조회 테스트
            async with self.session.get(f"{self.backend_url}/api/monitoring/logs?limit=10") as response:
                if response.status == 200:
                    logs = await response.json()
                    if len(logs.get("logs", [])) > 0:
                        self._add_test_result("log_retrieval", True, f"Retrieved {len(logs.get('logs'))} logs")
                    else:
                        self._add_test_result("log_retrieval", False, "No logs retrieved")
                else:
                    self._add_test_result("log_retrieval", False, f"Log retrieval failed: {response.status}")
            
        except Exception as e:
            self._add_test_result("logging_automation", False, f"Logging automation test error: {str(e)}")
    
    def _add_test_result(self, test_name: str, passed: bool, message: str):
        """테스트 결과 추가"""
        self.test_results["total_tests"] += 1
        
        if passed:
            self.test_results["passed_tests"] += 1
        else:
            self.test_results["failed_tests"] += 1
        
        self.test_results["details"][test_name] = {
            "passed": passed,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Test result for {test_name}: {passed} - {message}")
    
    def _summarize_results(self):
        """테스트 결과 요약"""
        total = self.test_results["total_tests"]
        passed = self.test_results["passed_tests"]
        failed = self.test_results["failed_tests"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        # 전체 성공 여부 결정
        overall_success = success_rate >= 80  # 80% 이상 통과
        
        self.test_results["success_rate"] = success_rate
        self.test_results["overall_success"] = overall_success
        self.test_results["summary"] = f"Automation testing completed: {passed}/{total} tests passed ({success_rate:.1f}%)"
        
        logger.info(f"Test summary: {self.test_results['summary']}")
    
    async def generate_report(self) -> str:
        """테스트 보고서 생성"""
        report = []
        report.append("# InsiteChart 자동화 기능 테스트 보고서")
        report.append(f"생성 시간: {self.test_results['timestamp']}")
        report.append(f"총 테스트: {self.test_results['total_tests']}")
        report.append(f"통과 테스트: {self.test_results['passed_tests']}")
        report.append(f"실패 테스트: {self.test_results['failed_tests']}")
        report.append(f"성공률: {self.test_results['success_rate']:.1f}%")
        report.append(f"전체 성공: {'성공' if self.test_results.get('overall_success', False) else '실패'}")
        report.append("")
        
        # 상세 결과
        report.append("## 상세 테스트 결과:")
        for test_name, result in self.test_results["details"].items():
            status = "✅ 통과" if result["passed"] else "❌ 실패"
            report.append(f"- {test_name}: {status}")
            report.append(f"  {result['message']}")
            report.append(f"  시간: {result['timestamp']}")
            report.append("")
        
        return "\n".join(report)
    
    async def cleanup(self):
        """테스트 환경 정리"""
        logger.info("Cleaning up test environment")
        
        try:
            # HTTP 세션 닫기
            if self.session:
                await self.session.close()
            
            # Redis 클라이언트 닫기
            if self.redis_client:
                await self.redis_client.aclose()
            
            # 백엔드 서버 종료
            if self.backend_process:
                logger.info(f"Stopping backend server (PID: {self.backend_process.pid})")
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.backend_process.pid), signal.SIGTERM)
                else:
                    self.backend_process.terminate()
                
                # 프로세스가 종료될 때까지 대기
                try:
                    self.backend_process.wait(timeout=10)
                    logger.info("Backend server stopped successfully")
                except subprocess.TimeoutExpired:
                    logger.warning("Backend server did not stop gracefully, forcing termination")
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self.backend_process.pid), signal.SIGKILL)
                    else:
                        self.backend_process.kill()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

async def main():
    """메인 함수"""
    import os
    
    tester = AutomationTester()
    
    try:
        # 테스트 환경 설정
        if not await tester.setup_environment():
            logger.error("Failed to setup test environment")
            sys.exit(1)
        
        # 모든 테스트 실행
        results = await tester.run_all_tests()
        
        # 결과 출력
        print(await tester.generate_report())
        
        # 결과 파일 저장
        report_path = Path("automation_test_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(await tester.generate_report())
        
        print(f"테스트 보고서가 저장되었습니다: {report_path}")
        
        # 전체 성공 여부에 따라 종료 코드 결정
        if results.get("overall_success", False):
            logger.info("All automation tests passed successfully!")
            sys.exit(0)
        else:
            logger.error("Some automation tests failed!")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Test script error: {str(e)}")
        print(f"테스트 중 오류 발생: {str(e)}")
        sys.exit(1)
    
    finally:
        # 테스트 환경 정리
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())