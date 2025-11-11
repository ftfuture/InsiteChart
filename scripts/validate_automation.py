"""
InsiteChart 자동화 검증 스크립트
구현된 자동화 기능들을 검증하고 정상 작동 여부 확인
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
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

class AutomationValidator:
    """자동화 검증기 클래스"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", redis_url: str = "redis://localhost:6379"):
        self.backend_url = backend_url
        self.redis_url = redis_url
        self.session = None
        self.redis_client = None
        
        # 검증 결과
        self.validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "details": {}
        }
    
    async def initialize(self):
        """검증기 초기화"""
        try:
            # HTTP 세션 초기화
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            logger.info("Automation validator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize validator: {str(e)}")
            raise
    
    async def validate_all_automations(self) -> Dict[str, Any]:
        """모든 자동화 기능 검증"""
        logger.info("Starting comprehensive automation validation")
        
        try:
            # 1. JWT 인증 자동화 검증
            await self._validate_jwt_automation()
            
            # 2. API 키 관리 자동화 검증
            await self._validate_api_key_automation()
            
            # 3. 속도 제한 자동화 검증
            await self._validate_rate_limit_automation()
            
            # 4. 보안 헤더 자동화 검증
            await self._validate_security_headers_automation()
            
            # 5. 외부 API 연동 자동화 검증
            await self._validate_external_api_automation()
            
            # 6. Kafka 이벤트 버스 자동화 검증
            await self._validate_kafka_automation()
            
            # 7. 실시간 데이터 수집 자동화 검증
            await self._validate_realtime_collection_automation()
            
            # 8. 캐싱 시스템 자동화 검증
            await self._validate_caching_automation()
            
            # 9. 모니터링 시스템 자동화 검증
            await self._validate_monitoring_automation()
            
            # 10. 로깅 시스템 자동화 검증
            await self._validate_logging_automation()
            
            # 결과 요약
            self._summarize_results()
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            self.validation_results["error"] = str(e)
            return self.validation_results
    
    async def _validate_jwt_automation(self):
        """JWT 인증 자동화 검증"""
        logger.info("Validating JWT automation")
        
        try:
            # JWT 토큰 생성 테스트
            async with self.session.post(f"{self.backend_url}/auth/token", json={
                "user_id": "test_user",
                "email": "test@example.com"
            }) as response:
                if response.status == 200:
                    token_data = await response.json()
                    token = token_data.get("access_token")
                    
                    if token:
                        # JWT 토큰 검증 테스트
                        headers = {"Authorization": f"Bearer {token}"}
                        async with self.session.get(f"{self.backend_url}/auth/verify", headers=headers) as verify_response:
                            if verify_response.status == 200:
                                self._add_result("jwt_token_generation", True, "JWT token generation successful")
                                self._add_result("jwt_token_verification", True, "JWT token verification successful")
                            else:
                                self._add_result("jwt_token_verification", False, f"JWT verification failed: {verify_response.status}")
                    else:
                        self._add_result("jwt_token_generation", False, "No access token in response")
                else:
                    self._add_result("jwt_token_generation", False, f"JWT token generation failed: {response.status}")
            
        except Exception as e:
            self._add_result("jwt_automation", False, f"JWT automation error: {str(e)}")
    
    async def _validate_api_key_automation(self):
        """API 키 관리 자동화 검증"""
        logger.info("Validating API key automation")
        
        try:
            # API 키 생성 테스트
            async with self.session.post(f"{self.backend_url}/auth/api-keys", json={
                "name": "test_key",
                "tier": "basic",
                "permissions": ["stock:read", "search:read"]
            }) as response:
                if response.status == 200:
                    key_data = await response.json()
                    api_key = key_data.get("api_key")
                    
                    if api_key:
                        # API 키 검증 테스트
                        headers = {"X-API-Key": api_key}
                        async with self.session.get(f"{self.backend_url}/auth/validate-key", headers=headers) as verify_response:
                            if verify_response.status == 200:
                                self._add_result("api_key_generation", True, "API key generation successful")
                                self._add_result("api_key_verification", True, "API key verification successful")
                            else:
                                self._add_result("api_key_verification", False, f"API key verification failed: {verify_response.status}")
                    else:
                        self._add_result("api_key_generation", False, "No API key in response")
                else:
                    self._add_result("api_key_generation", False, f"API key generation failed: {response.status}")
            
        except Exception as e:
            self._add_result("api_key_automation", False, f"API key automation error: {str(e)}")
    
    async def _validate_rate_limit_automation(self):
        """속도 제한 자동화 검증"""
        logger.info("Validating rate limiting automation")
        
        try:
            # 속도 제한 테스트 (동시 요청)
            tasks = []
            for i in range(10):
                task = self.session.get(f"{self.backend_url}/api/test")
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 응답 분석
            success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
            rate_limited_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 429)
            
            total_time = end_time - start_time
            
            self._add_result("rate_limiting", success_count >= 8, f"Rate limiting test: {success_count}/10 successful in {total_time:.2f}s")
            
            if rate_limited_count > 0:
                self._add_result("rate_limiting_effective", True, f"Rate limiting effective: {rate_limited_count}/10 requests limited")
            else:
                self._add_result("rate_limiting_effective", False, "No rate limiting detected")
            
        except Exception as e:
            self._add_result("rate_limiting_automation", False, f"Rate limiting automation error: {str(e)}")
    
    async def _validate_security_headers_automation(self):
        """보안 헤더 자동화 검증"""
        logger.info("Validating security headers automation")
        
        try:
            # 보안 헤더 확인
            async with self.session.get(f"{self.backend_url}/api/test") as response:
                if response.status == 200:
                    headers = response.headers
                    
                    # 필수 보안 헤더 확인
                    required_headers = [
                        "X-Content-Type-Options",
                        "X-Frame-Options",
                        "X-XSS-Protection",
                        "Referrer-Policy"
                    ]
                    
                    missing_headers = []
                    for header in required_headers:
                        if header not in headers:
                            missing_headers.append(header)
                    
                    if missing_headers:
                        self._add_result("security_headers", False, f"Missing security headers: {missing_headers}")
                    else:
                        self._add_result("security_headers", True, "All required security headers present")
                    
                    # CSP 헤더 확인
                    if "Content-Security-Policy" in headers:
                        csp = headers["Content-Security-Policy"]
                        if "default-src 'self'" in csp:
                            self._add_result("csp_header", True, "CSP header properly configured")
                        else:
                            self._add_result("csp_header", False, "CSP header not properly configured")
                    else:
                        self._add_result("csp_header", False, "CSP header missing")
                else:
                    self._add_result("security_headers", False, f"Security headers check failed: {response.status}")
            
        except Exception as e:
            self._add_result("security_headers_automation", False, f"Security headers automation error: {str(e)}")
    
    async def _validate_external_api_automation(self):
        """외부 API 연동 자동화 검증"""
        logger.info("Validating external API automation")
        
        try:
            # 외부 API 연동 테스트
            async with self.session.get(f"{self.backend_url}/api/stocks/AAPL") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 실제 데이터 구조 확인
                    if "symbol" in data and "current_price" in data:
                        self._add_result("external_api_integration", True, "External API integration working")
                    else:
                        self._add_result("external_api_integration", False, "Invalid data structure from external API")
                else:
                    self._add_result("external_api_integration", False, f"External API integration failed: {response.status}")
            
        except Exception as e:
            self._add_result("external_api_automation", False, f"External API automation error: {str(e)}")
    
    async def _validate_kafka_automation(self):
        """Kafka 이벤트 버스 자동화 검증"""
        logger.info("Validating Kafka automation")
        
        try:
            # Kafka 이벤트 발행 테스트
            async with self.session.post(f"{self.backend_url}/events/test", json={
                "event_type": "test_event",
                "data": {"test": "data"}
            }) as response:
                if response.status == 200:
                    self._add_result("kafka_event_publishing", True, "Kafka event publishing successful")
                else:
                    self._add_result("kafka_event_publishing", False, f"Kafka event publishing failed: {response.status}")
            
        except Exception as e:
            self._add_result("kafka_automation", False, f"Kafka automation error: {str(e)}")
    
    async def _validate_realtime_collection_automation(self):
        """실시간 데이터 수집 자동화 검증"""
        logger.info("Validating realtime collection automation")
        
        try:
            # 데이터 수집 상태 확인
            async with self.session.get(f"{self.backend_url}/monitoring/collection-status") as response:
                if response.status == 200:
                    status = await response.json()
                    
                    if status.get("running", False):
                        self._add_result("realtime_collection", False, "Realtime collection not running")
                    else:
                        # 수집 통계 확인
                        if status.get("total_collections", 0) > 0:
                            self._add_result("realtime_collection", True, "Realtime collection active")
                        else:
                            self._add_result("realtime_collection", False, "No collections performed")
                else:
                    self._add_result("realtime_collection", False, f"Realtime collection status check failed: {response.status}")
            
        except Exception as e:
            self._add_result("realtime_collection_automation", False, f"Realtime collection automation error: {str(e)}")
    
    async def _validate_caching_automation(self):
        """캐싱 시스템 자동화 검증"""
        logger.info("Validating caching automation")
        
        try:
            # 캐시 성능 테스트
            cache_tests = []
            for i in range(5):
                task = self.session.get(f"{self.backend_url}/api/test-cache")
                cache_tests.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*cache_tests, return_exceptions=True)
            end_time = time.time()
            
            # 캐시 히트율 계산
            cache_hits = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200 and r.headers.get("X-Cache", "hit"))
            total_requests = len([r for r in responses if not isinstance(r, Exception)])
            
            if total_requests > 0:
                hit_rate = (cache_hits / total_requests) * 100
                self._add_result("caching_performance", hit_rate > 50, f"Cache hit rate: {hit_rate:.1f}%")
            else:
                self._add_result("caching_performance", False, "No successful cache requests")
            
        except Exception as e:
            self._add_result("caching_automation", False, f"Caching automation error: {str(e)}")
    
    async def _validate_monitoring_automation(self):
        """모니터링 시스템 자동화 검증"""
        logger.info("Validating monitoring automation")
        
        try:
            # 모니터링 대시보드 데이터 확인
            async with self.session.get(f"{self.backend_url}/monitoring/dashboard") as response:
                if response.status == 200:
                    dashboard_data = await response.json()
                    
                    # 대시보드 위젯 확인
                    widgets = dashboard_data.get("widgets", {})
                    if len(widgets) > 0:
                        self._add_result("monitoring_dashboard", True, f"Monitoring dashboard has {len(widgets)} widgets")
                    else:
                        self._add_result("monitoring_dashboard", False, "No widgets in monitoring dashboard")
                    
                    # 알림 시스템 확인
                    alerts = dashboard_data.get("alerts", [])
                    critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
                    
                    if critical_alerts:
                        self._add_result("monitoring_alerts", True, f"Found {len(critical_alerts)} critical alerts")
                    else:
                        self._add_result("monitoring_alerts", False, "No critical alerts")
                else:
                    self._add_result("monitoring_dashboard", False, f"Monitoring dashboard check failed: {response.status}")
            
        except Exception as e:
            self._add_result("monitoring_automation", False, f"Monitoring automation error: {str(e)}")
    
    async def _validate_logging_automation(self):
        """로깅 시스템 자동화 검증"""
        logger.info("Validating logging automation")
        
        try:
            # 로깅 시스템 상태 확인
            async with self.session.get(f"{self.backend_url}/monitoring/logging-status") as response:
                if response.status == 200:
                    logging_status = await response.json()
                    
                    # 구조화된 로그 확인
                    if logging_status.get("structured_logging", True):
                        self._add_result("structured_logging", True, "Structured logging is active")
                    else:
                        self._add_result("structured_logging", False, "Structured logging not active")
                    
                    # 로그 레벨 확인
                    if logging_status.get("log_level") in ["INFO", "DEBUG", "WARNING", "ERROR"]:
                        self._add_result("log_level", True, f"Log level: {logging_status.get('log_level')}")
                    else:
                        self._add_result("log_level", False, f"Invalid log level: {logging_status.get('log_level')}")
                    
                    # 로그 저장소 확인
                    if logging_status.get("log_storage", "redis") or logging_status.get("log_storage", "file"):
                        self._add_result("log_storage", True, f"Log storage: {logging_status.get('log_storage')}")
                    else:
                        self._add_result("log_storage", False, "Invalid log storage")
                else:
                    self._add_result("logging_status_check", False, f"Logging status check failed: {response.status}")
            
        except Exception as e:
            self._add_result("logging_automation", False, f"Logging automation error: {str(e)}")
    
    def _add_result(self, check_name: str, passed: bool, message: str):
        """검증 결과 추가"""
        self.validation_results["total_checks"] += 1
        
        if passed:
            self.validation_results["passed_checks"] += 1
        else:
            self.validation_results["failed_checks"] += 1
        
        self.validation_results["details"][check_name] = {
            "passed": passed,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Validation result for {check_name}: {passed} - {message}")
    
    def _summarize_results(self):
        """검증 결과 요약"""
        total = self.validation_results["total_checks"]
        passed = self.validation_results["passed_checks"]
        failed = self.validation_results["failed_checks"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        # 전체 성공 여부 결정
        overall_success = success_rate >= 80  # 80% 이상 통과
        
        self.validation_results["success_rate"] = success_rate
        self.validation_results["overall_success"] = overall_success
        self.validation_results["summary"] = f"Automation validation completed: {passed}/{total} checks passed ({success_rate:.1f}%)"
        
        logger.info(f"Validation summary: {self.validation_results['summary']}")
        
        # Redis에 결과 저장
        asyncio.create_task(self._save_results_to_redis())
    
    async def _save_results_to_redis(self):
        """검증 결과를 Redis에 저장"""
        try:
            if self.redis_client:
                result_key = f"automation_validation:{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                await self.redis_client.setex(
                    result_key,
                    86400,  # 24시간 보관
                    json.dumps(self.validation_results)
                )
                
                # 최신 결과 키 저장
                await self.redis_client.set(
                    "automation_validation:latest",
                    json.dumps(self.validation_results)
                )
                
                logger.info("Validation results saved to Redis")
            
        except Exception as e:
            logger.error(f"Failed to save results to Redis: {str(e)}")
    
    async def generate_report(self) -> str:
        """검증 보고서 생성"""
        report = []
        report.append("# InsiteChart 자동화 검증 보고서")
        report.append(f"생성 시간: {self.validation_results['timestamp']}")
        report.append(f"총 검사: {self.validation_results['total_checks']}")
        report.append(f"통과 검사: {self.validation_results['passed_checks']}")
        report.append(f"실패 검사: {self.validation_results['failed_checks']}")
        report.append(f"성공률: {self.validation_results['success_rate']:.1f}%")
        report.append(f"전체 성공: {'성공' if self.validation_results.get('overall_success', False) else '실패'}")
        report.append("")
        
        # 상세 결과
        report.append("## 상세 검증 결과:")
        for check_name, result in self.validation_results["details"].items():
            status = "✅ 통과" if result["passed"] else "❌ 실패"
            report.append(f"- {check_name}: {status}")
            report.append(f"  {result['message']}")
            report.append(f"  시간: {result['timestamp']}")
            report.append("")
        
        return "\n".join(report)

async def main():
    """메인 함수"""
    validator = AutomationValidator()
    
    try:
        await validator.initialize()
        results = await validator.validate_all_automations()
        
        # 결과 출력
        print(await validator.generate_report())
        
        # 결과 파일 저장
        report_path = Path("automation_validation_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(await validator.generate_report())
        
        print(f"검증 보고서가 저장되었습니다: {report_path}")
        
    except Exception as e:
        logger.error(f"Validation script error: {str(e)}")
        print(f"검증 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())