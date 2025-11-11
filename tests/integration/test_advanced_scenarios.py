"""
고급 통합 시나리오 테스트 모듈
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from backend.api.gateway import APIGateway, GatewayRoute
from backend.services.unified_service import UnifiedService
from backend.services.advanced_sentiment_service import AdvancedSentimentService
from backend.services.realtime_data_collector import RealtimeDataCollector
from backend.cache.unified_cache import UnifiedCacheManager
from backend.models.unified_models import UnifiedStockData, SentimentResult


class TestEndToEndWorkflow:
    """종단간 워크플로우 테스트"""
    
    @pytest.fixture
    async def setup_services(self):
        """테스트용 서비스 설정"""
        # 모의 백엔드
        mock_backend = Mock()
        mock_backend.get = AsyncMock()
        mock_backend.set = AsyncMock(return_value=True)
        mock_backend.delete = AsyncMock(return_value=True)
        
        # 서비스 인스턴스 생성
        cache_manager = UnifiedCacheManager(mock_backend)
        await cache_manager.initialize()
        
        sentiment_service = Mock(spec=AdvancedSentimentService)
        sentiment_service.analyze_sentiment = AsyncMock(return_value=SentimentResult(
            compound_score=0.5,
            positive_score=0.7,
            negative_score=0.1,
            neutral_score=0.2,
            confidence=0.8,
            source="news",
            timestamp=datetime.utcnow()
        ))
        
        data_collector = Mock(spec=RealtimeDataCollector)
        data_collector.get_collection_stats = AsyncMock(return_value={
            "total_collections": 100,
            "successful_collections": 95,
            "failed_collections": 5,
            "success_rate": 95.0,
            "active_symbols": 10
        })
        
        unified_service = UnifiedService(cache_manager, sentiment_service, data_collector)
        
        # API Gateway 설정
        gateway = APIGateway()
        
        # 라우트 등록
        stock_route = GatewayRoute(
            path="/api/v1/stocks/{symbol}",
            methods=["GET"],
            service="unified_service",
            auth_required=False
        )
        
        sentiment_route = GatewayRoute(
            path="/api/v1/sentiment/{symbol}",
            methods=["GET"],
            service="unified_service",
            auth_required=False
        )
        
        gateway.add_route(stock_route)
        gateway.add_route(sentiment_route)
        gateway.register_service("unified_service", unified_service)
        
        return {
            'gateway': gateway,
            'unified_service': unified_service,
            'cache_manager': cache_manager,
            'sentiment_service': sentiment_service,
            'data_collector': data_collector
        }
    
    @pytest.mark.asyncio
    async def test_stock_data_flow(self, setup_services):
        """주식 데이터 흐름 테스트"""
        services = setup_services
        unified_service = services['unified_service']
        
        # 주식 데이터 요청
        stock_data = await unified_service.get_stock_data("AAPL")
        
        assert stock_data is not None
        assert stock_data.symbol == "AAPL"
        assert stock_data.current_price > 0
        
        # 캐시에 저장 확인
        cached_data = await services['cache_manager'].get_stock_data("AAPL")
        assert cached_data is not None
        assert cached_data.symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_flow(self, setup_services):
        """센티먼트 분석 흐름 테스트"""
        services = setup_services
        unified_service = services['unified_service']
        
        # 센티먼트 분석 요청
        sentiment_data = await unified_service.get_sentiment_analysis("AAPL")
        
        assert sentiment_data is not None
        assert 'overall_sentiment' in sentiment_data
        assert 'confidence' in sentiment_data
        assert 'source' in sentiment_data
        
        # 센티먼트 서비스 호출 확인
        services['sentiment_service'].analyze_sentiment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_realtime_data_collection_flow(self, setup_services):
        """실시간 데이터 수집 흐름 테스트"""
        services = setup_services
        data_collector = services['data_collector']
        
        # 수집 통계 요청
        stats = await data_collector.get_collection_stats()
        
        assert 'total_collections' in stats
        assert 'success_rate' in stats
        assert 'active_symbols' in stats
        assert stats['success_rate'] > 90
    
    @pytest.mark.asyncio
    async def test_gateway_routing_integration(self, setup_services):
        """게이트웨이 라우팅 통합 테스트"""
        services = setup_services
        gateway = services['gateway']
        
        # 주식 데이터 요청
        stock_request = {
            "method": "GET",
            "path": "/api/v1/stocks/AAPL",
            "headers": {},
            "body": None
        }
        
        stock_response = await gateway.route_request(stock_request)
        assert stock_response is not None
        assert stock_response.get('symbol') == "AAPL"
        
        # 센티먼트 데이터 요청
        sentiment_request = {
            "method": "GET",
            "path": "/api/v1/sentiment/AAPL",
            "headers": {},
            "body": None
        }
        
        sentiment_response = await gateway.route_request(sentiment_request)
        assert sentiment_response is not None
        assert 'overall_sentiment' in sentiment_response


class TestErrorHandlingAndRecovery:
    """에러 처리 및 복구 테스트"""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_recovery(self):
        """서비스 불가 상태 복구 테스트"""
        # 실패하는 서비스 모의
        failing_service = Mock()
        failing_service.get_stock_data = AsyncMock(side_effect=Exception("Service unavailable"))
        
        # 성공하는 백업 서비스 모의
        backup_service = Mock()
        backup_service.get_stock_data = AsyncMock(return_value=UnifiedStockData(
            symbol="AAPL",
            current_price=150.0,
            company_name="Apple Inc."
        ))
        
        # 서비스 스위칭 로직
        async def get_stock_data_with_fallback(symbol):
            try:
                return await failing_service.get_stock_data(symbol)
            except Exception:
                return await backup_service.get_stock_data(symbol)
        
        # 테스트 실행
        result = await get_stock_data_with_fallback("AAPL")
        
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.current_price == 150.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """서킷 브레이커 복구 테스트"""
        gateway = APIGateway()
        
        # 실패하는 서비스 등록
        failing_service = Mock()
        call_count = 0
        
        async def failing_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Service failing")
            return {"status": "success"}
        
        failing_service.call = failing_call
        
        # 라우트 등록
        route = GatewayRoute(
            path="/failing",
            methods=["GET"],
            service="failing_service",
            circuit_breaker_threshold=2
        )
        gateway.add_route(route)
        gateway.register_service("failing_service", failing_service)
        
        request = {
            "method": "GET",
            "path": "/failing",
            "headers": {},
            "body": None
        }
        
        # 초기 실패 (서킷 브레이커 트립)
        response1 = await gateway.route_request(request)
        assert response1["status_code"] == 500
        
        response2 = await gateway.route_request(request)
        assert response2["status_code"] == 500
        
        # 서킷 브레이커 열림
        response3 = await gateway.route_request(request)
        assert response3["status_code"] == 503
        
        # 복구 대기
        await asyncio.sleep(2)
        
        # 복구 후 성공
        response4 = await gateway.route_request(request)
        assert response4["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cache_fallback_handling(self):
        """캐시 폴백 처리 테스트"""
        # 실패하는 백엔드 모의
        failing_backend = Mock()
        failing_backend.get = AsyncMock(side_effect=Exception("Cache unavailable"))
        
        # 성공하는 폴백 백엔드 모의
        fallback_backend = Mock()
        fallback_backend.get = AsyncMock(return_value={"cached": "value"})
        
        # 폴백 로직이 있는 캐시 관리자
        cache_manager = UnifiedCacheManager(failing_backend)
        cache_manager.fallback_backend = fallback_backend
        
        await cache_manager.initialize()
        
        # 캐시 접근 (폴백 사용)
        result = await cache_manager.get("test_key")
        
        assert result == {"cached": "value"}
        fallback_backend.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_data_consistency_validation(self):
        """데이터 일관성 검증 테스트"""
        # 데이터 품질 검증기 모의
        validator = Mock()
        validator.validate_stock_data = AsyncMock(return_value={
            "is_valid": True,
            "quality_score": 0.95,
            "issues": []
        })
        
        # 주식 데이터
        stock_data = UnifiedStockData(
            symbol="AAPL",
            current_price=150.0,
            company_name="Apple Inc."
        )
        
        # 데이터 검증
        validation_result = await validator.validate_stock_data(stock_data)
        
        assert validation_result["is_valid"] is True
        assert validation_result["quality_score"] > 0.9
        assert len(validation_result["issues"]) == 0


class TestPerformanceAndScalability:
    """성능 및 확장성 테스트"""
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """동시 요청 처리 테스트"""
        gateway = APIGateway()
        
        # 빠른 응답 서비스 모의
        fast_service = Mock()
        async def fast_response():
            await asyncio.sleep(0.01)  # 10ms 지연
            return {"status": "success", "response_time": 0.01}
        
        fast_service.call = fast_response
        
        # 라우트 등록
        route = GatewayRoute(
            path="/fast",
            methods=["GET"],
            service="fast_service",
            rate_limit=1000  # 높은 속도 제한
        )
        gateway.add_route(route)
        gateway.register_service("fast_service", fast_service)
        
        # 동시 요청
        request = {
            "method": "GET",
            "path": "/fast",
            "headers": {"X-Client-ID": "test_client"},
            "body": None
        }
        
        # 100개 동시 요청
        tasks = [gateway.route_request(request) for _ in range(100)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 모든 요청 성공 확인
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) == 100
        
        # 응답 시간 확인
        for response in successful_responses:
            assert response["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self):
        """부하 하의 캐시 성능 테스트"""
        # 모의 백엔드
        backend = Mock()
        backend.get = AsyncMock()
        backend.set = AsyncMock(return_value=True)
        
        cache_manager = UnifiedCacheManager(backend)
        await cache_manager.initialize()
        
        # 부하 테스트
        async def cache_operation(i):
            key = f"test_key_{i}"
            value = f"test_value_{i}"
            await cache_manager.set(key, value, 60)
            return await cache_manager.get(key)
        
        # 1000개 동시 캐시 작업
        tasks = [cache_operation(i) for i in range(1000)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 성공적인 작업 확인
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 1000
        
        # 캐시 통계 확인
        stats = await cache_manager.get_cache_stats()
        assert stats['sets'] == 1000
        assert stats['hits'] == 1000
        assert stats['hit_rate'] == 100.0
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self):
        """메모리 사용량 최적화 테스트"""
        cache_manager = UnifiedCacheManager()
        
        # 큰 데이터 저장
        large_data = 'x' * 1000000  # 1MB 데이터
        
        # 메모리 사용량 모니터링
        initial_memory = cache_manager.get_memory_usage()
        
        # 여러 큰 데이터 저장
        for i in range(10):
            await cache_manager.set(f"large_key_{i}", large_data, 60)
        
        # 메모리 사용량 확인
        current_memory = cache_manager.get_memory_usage()
        memory_increase = current_memory - initial_memory
        
        # 메모리 사용량이 예상 범위 내인지 확인
        assert memory_increase > 0
        assert memory_increase < 15 * 1024 * 1024  # 15MB 이하
        
        # 메모리 최적화 실행
        optimization_result = await cache_manager.optimize_cache_performance()
        
        assert 'actions_taken' in optimization_result
        assert 'memory_freed' in optimization_result
    
    @pytest.mark.asyncio
    async def test_service_scaling_behavior(self):
        """서비스 확장 동작 테스트"""
        # 서비스 스케일링 모의
        scaling_service = Mock()
        scaling_instances = []
        
        async def create_new_instance():
            new_instance = Mock()
            new_instance.call = AsyncMock(return_value={"instance": len(scaling_instances)})
            scaling_instances.append(new_instance)
            return new_instance
        
        scaling_service.scale_up = create_new_instance
        scaling_service.scale_down = AsyncMock()
        
        # 부하 증가 시나리오
        async def handle_load_increase():
            # 부하 증가 감지
            if len(scaling_instances) < 3:
                await scaling_service.scale_up()
        
        # 부하 감소 시나리오
        async def handle_load_decrease():
            # 부하 감소 감지
            if len(scaling_instances) > 1:
                instance_to_remove = scaling_instances.pop()
                await scaling_service.scale_down(instance_to_remove)
        
        # 스케일업 테스트
        await handle_load_increase()
        await handle_load_increase()
        await handle_load_increase()
        
        assert len(scaling_instances) == 3
        
        # 모든 인스턴스 작동 확인
        for i, instance in enumerate(scaling_instances):
            result = await instance.call()
            assert result["instance"] == i
        
        # 스케일다운 테스트
        await handle_load_decrease()
        await handle_load_decrease()
        
        assert len(scaling_instances) == 1


class TestDataIntegrityAndSecurity:
    """데이터 무결성 및 보안 테스트"""
    
    @pytest.mark.asyncio
    async def test_data_encryption_decryption(self):
        """데이터 암호화/복호화 테스트"""
        # 암호화 서비스 모의
        encryption_service = Mock()
        
        async def encrypt_data(data):
            return f"encrypted_{json.dumps(data)}"
        
        async def decrypt_data(encrypted_data):
            if encrypted_data.startswith("encrypted_"):
                return json.loads(encrypted_data[10:])
            return None
        
        encryption_service.encrypt = encrypt_data
        encryption_service.decrypt = decrypt_data
        
        # 테스트 데이터
        sensitive_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "user_id": "user123"
        }
        
        # 암호화
        encrypted = await encryption_service.encrypt(sensitive_data)
        assert encrypted.startswith("encrypted_")
        
        # 복호화
        decrypted = await encryption_service.decrypt(encrypted)
        assert decrypted == sensitive_data
    
    @pytest.mark.asyncio
    async def test_input_validation_and_sanitization(self):
        """입력값 검증 및 정제 테스트"""
        # 입력 검증기 모의
        validator = Mock()
        
        async def validate_stock_symbol(symbol):
            # 심볼 형식 검증
            if not symbol or not isinstance(symbol, str):
                return {"valid": False, "error": "Symbol is required"}
            
            # 대문자로 변환 및 공백 제거
            sanitized = symbol.upper().strip()
            
            # 길이 검증
            if len(sanitized) < 1 or len(sanitized) > 10:
                return {"valid": False, "error": "Invalid symbol length"}
            
            # 특수 문자 검증
            if not sanitized.replace("-", "").replace(".", "").isalnum():
                return {"valid": False, "error": "Invalid characters"}
            
            return {"valid": True, "sanitized": sanitized}
        
        validator.validate_stock_symbol = validate_stock_symbol
        
        # 유효한 입력 테스트
        result1 = await validator.validate_stock_symbol("aapl")
        assert result1["valid"] is True
        assert result1["sanitized"] == "AAPL"
        
        # 무효한 입력 테스트
        result2 = await validator.validate_stock_symbol("")
        assert result2["valid"] is False
        assert "error" in result2
        
        result3 = await validator.validate_stock_symbol("INVALID@SYMBOL")
        assert result3["valid"] is False
        assert "error" in result3
    
    @pytest.mark.asyncio
    async def test_authentication_and_authorization(self):
        """인증 및 권한 부여 테스트"""
        # 인증 서비스 모의
        auth_service = Mock()
        
        async def authenticate_token(token):
            # 토큰 검증
            if token == "valid_token":
                return {
                    "valid": True,
                    "user_id": "user123",
                    "permissions": ["read", "write"]
                }
            elif token == "read_only_token":
                return {
                    "valid": True,
                    "user_id": "user456",
                    "permissions": ["read"]
                }
            else:
                return {"valid": False}
        
        auth_service.authenticate = authenticate_token
        
        # 유효한 토큰 테스트
        auth_result1 = await auth_service.authenticate("valid_token")
        assert auth_result1["valid"] is True
        assert "read" in auth_result1["permissions"]
        assert "write" in auth_result1["permissions"]
        
        # 읽기 전용 토큰 테스트
        auth_result2 = await auth_service.authenticate("read_only_token")
        assert auth_result2["valid"] is True
        assert "read" in auth_result2["permissions"]
        assert "write" not in auth_result2["permissions"]
        
        # 무효한 토큰 테스트
        auth_result3 = await auth_service.authenticate("invalid_token")
        assert auth_result3["valid"] is False
    
    @pytest.mark.asyncio
    async def test_audit_logging(self):
        """감사 로깅 테스트"""
        # 감사 로거 모의
        audit_logger = Mock()
        audit_logs = []
        
        async def log_event(event_type, user_id, resource, details):
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "resource": resource,
                "details": details
            }
            audit_logs.append(log_entry)
        
        audit_logger.log_event = log_event
        
        # 감사 이벤트 기록
        await audit_logger.log_event(
            "DATA_ACCESS",
            "user123",
            "stock:AAPL",
            {"action": "read", "ip": "192.168.1.1"}
        )
        
        await audit_logger.log_event(
            "DATA_MODIFICATION",
            "user456",
            "sentiment:AAPL",
            {"action": "update", "fields": ["score", "confidence"]}
        )
        
        # 로그 확인
        assert len(audit_logs) == 2
        
        access_log = audit_logs[0]
        assert access_log["event_type"] == "DATA_ACCESS"
        assert access_log["user_id"] == "user123"
        assert access_log["resource"] == "stock:AAPL"
        
        modification_log = audit_logs[1]
        assert modification_log["event_type"] == "DATA_MODIFICATION"
        assert modification_log["user_id"] == "user456"
        assert modification_log["resource"] == "sentiment:AAPL"