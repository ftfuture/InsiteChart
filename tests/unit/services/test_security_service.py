"""
보안 서비스 단위 테스트

이 모듈은 보안 서비스의 개별 기능을 테스트합니다.
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from backend.services.security_service import (
    SecurityService,
    SecurityEvent,
    SecurityRule,
    SecurityEventType,
    SecuritySeverity,
    SecurityAction,
    SecurityMetrics
)


class TestSecurityService:
    """보안 서비스 단위 테스트 클래스"""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """모의 캐시 관리자 픽스처"""
        cache_manager = MagicMock()
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock(return_value=True)
        cache_manager.delete = AsyncMock(return_value=True)
        return cache_manager
    
    @pytest.fixture
    def security_service(self, mock_cache_manager):
        """보안 서비스 픽스처"""
        service = SecurityService(mock_cache_manager)
        return service
    
    @pytest.fixture
    def sample_security_event(self):
        """샘플 보안 이벤트 픽스처"""
        return SecurityEvent(
            id="test_event_001",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            timestamp=datetime.utcnow(),
            source_ip="192.168.1.100",
            user_id="user123",
            user_agent="Mozilla/5.0 (Test Browser)",
            endpoint="/api/stocks",
            request_data={"query": "SELECT * FROM users"},
            description="SQL injection attempt detected",
            metadata={"pattern": "sql_union", "matched_param": "SELECT * FROM users"}
        )
    
    @pytest.fixture
    def sample_security_rule(self):
        """샘플 보안 규칙 픽스처"""
        return SecurityRule(
            id="test_rule_001",
            name="Test SQL Injection Rule",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            conditions={"severity": SecuritySeverity.HIGH},
            actions=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN],
            severity=SecuritySeverity.HIGH,
            enabled=True,
            cooldown_period=300
        )
    
    @pytest.mark.asyncio
    async def test_security_service_initialization(self, security_service):
        """보안 서비스 초기화 테스트"""
        assert security_service.cache_manager is not None
        assert len(security_service.rules) > 0  # 기본 규칙이 있어야 함
        assert len(security_service.events) == 0
        assert len(security_service.blocked_ips) == 0
        assert security_service.metrics.total_events == 0
        assert security_service.injection_patterns is not None
        assert security_service.xss_patterns is not None
        assert security_service.suspicious_user_agents is not None
    
    @pytest.mark.asyncio
    async def test_security_service_start_stop(self, security_service):
        """보안 서비스 시작 및 중지 테스트"""
        # 서비스 시작
        await security_service.start()
        assert security_service.monitoring_task is not None
        assert security_service.cleanup_task is not None
        
        # 서비스 중지
        await security_service.stop()
        assert security_service.monitoring_task.cancelled()
        assert security_service.cleanup_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_analyze_request_injection_attack(self, security_service):
        """SQL 인젝션 공격 분석 테스트"""
        request_data = {
            "query": "SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admin",
            "user_id": "test_user"
        }
        
        events = await security_service.analyze_request(
            request_data=request_data,
            source_ip="192.168.1.100",
            user_id="user123",
            user_agent="Test Browser",
            endpoint="/api/stocks"
        )
        
        assert len(events) > 0
        
        # 인젝션 이벤트 확인
        injection_events = [e for e in events if e.event_type == SecurityEventType.INJECTION_ATTEMPT]
        assert len(injection_events) > 0
        
        injection_event = injection_events[0]
        assert injection_event.source_ip == "192.168.1.100"
        assert injection_event.user_id == "user123"
        assert injection_event.severity == SecuritySeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_analyze_request_xss_attack(self, security_service):
        """XSS 공격 분석 테스트"""
        request_data = {
            "comment": "<script>alert('XSS')</script>",
            "user_id": "test_user"
        }
        
        events = await security_service.analyze_request(
            request_data=request_data,
            source_ip="192.168.1.100",
            user_id="user123",
            user_agent="Test Browser",
            endpoint="/api/comments"
        )
        
        assert len(events) > 0
        
        # XSS 이벤트 확인
        xss_events = [e for e in events if e.event_type == SecurityEventType.XSS_ATTEMPT]
        assert len(xss_events) > 0
        
        xss_event = xss_events[0]
        assert xss_event.source_ip == "192.168.1.100"
        assert xss_event.severity == SecuritySeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_analyze_request_rate_limiting(self, security_service):
        """속도 제한 분석 테스트"""
        source_ip = "192.168.1.100"
        
        # 100개 이상의 요청 생성
        for i in range(101):
            await security_service.analyze_request(
                request_data={"test": f"request_{i}"},
                source_ip=source_ip,
                user_id="user123"
            )
        
        # 속도 제한 이벤트 확인
        rate_limit_events = [e for e in security_service.events if e.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED]
        assert len(rate_limit_events) > 0
        
        rate_limit_event = rate_limit_events[0]
        assert rate_limit_event.source_ip == source_ip
        assert rate_limit_event.severity == SecuritySeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_analyze_request_suspicious_user_agent(self, security_service):
        """의심스러운 사용자 에이전트 분석 테스트"""
        request_data = {"test": "data"}
        
        events = await security_service.analyze_request(
            request_data=request_data,
            source_ip="192.168.1.100",
            user_id="user123",
            user_agent="sqlmap/1.0"
        )
        
        # 의심스러운 요청 이벤트 확인
        suspicious_events = [e for e in events if e.event_type == SecurityEventType.SUSPICIOUS_REQUEST]
        assert len(suspicious_events) > 0
        
        suspicious_event = suspicious_events[0]
        assert suspicious_event.source_ip == "192.168.1.100"
        assert "sqlmap" in suspicious_event.metadata["user_agent"]
    
    @pytest.mark.asyncio
    async def test_add_security_rule(self, security_service, sample_security_rule, mock_cache_manager):
        """보안 규칙 추가 테스트"""
        initial_rule_count = len(security_service.rules)
        
        await security_service.add_security_rule(sample_security_rule)
        
        assert len(security_service.rules) == initial_rule_count + 1
        assert sample_security_rule.id in security_service.rules
        assert security_service.rules[sample_security_rule.id] == sample_security_rule
        
        # 캐시 호출 확인
        mock_cache_manager.set.assert_called_once()
        call_args = mock_cache_manager.set.call_args[0]
        assert call_args[0] == f"security_rule_{sample_security_rule.id}"
    
    @pytest.mark.asyncio
    async def test_update_security_rule(self, security_service, sample_security_rule, mock_cache_manager):
        """보안 규칙 업데이트 테스트"""
        # 먼저 규칙 추가
        await security_service.add_security_rule(sample_security_rule)
        
        # 규칙 업데이트
        updates = {
            "name": "Updated Rule Name",
            "enabled": False,
            "cooldown_period": 600
        }
        
        await security_service.update_security_rule(sample_security_rule.id, updates)
        
        updated_rule = security_service.rules[sample_security_rule.id]
        assert updated_rule.name == "Updated Rule Name"
        assert updated_rule.enabled is False
        assert updated_rule.cooldown_period == 600
        
        # 캐시 호출 확인
        mock_cache_manager.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_block_ip(self, security_service, mock_cache_manager):
        """IP 차단 테스트"""
        ip_address = "192.168.1.100"
        duration_hours = 24
        reason = "Test block"
        
        await security_service.block_ip(ip_address, duration_hours, reason)
        
        # IP 차단 확인
        assert ip_address in security_service.blocked_ips
        expiration = security_service.blocked_ips[ip_address]
        expected_expiration = datetime.utcnow() + timedelta(hours=duration_hours)
        
        # 시간 비교 (초 단위로 허용 오차)
        time_diff = abs((expiration - expected_expiration).total_seconds())
        assert time_diff < 60  # 60초 이내 오차 허용
        
        # 캐시 호출 확인
        mock_cache_manager.set.assert_called_once()
        call_args = mock_cache_manager.set.call_args[0]
        assert call_args[0] == f"blocked_ip_{ip_address}"
        
        # 메트릭 업데이트 확인
        assert security_service.metrics.blocked_ips > 0
    
    @pytest.mark.asyncio
    async def test_unblock_ip(self, security_service, mock_cache_manager):
        """IP 차단 해제 테스트"""
        ip_address = "192.168.1.100"
        
        # 먼저 IP 차단
        await security_service.block_ip(ip_address)
        
        # IP 차단 해제
        await security_service.unblock_ip(ip_address)
        
        # IP 차단 해제 확인
        assert ip_address not in security_service.blocked_ips
        
        # 캐시 호출 확인
        mock_cache_manager.delete.assert_called_with(f"blocked_ip_{ip_address}")
    
    @pytest.mark.asyncio
    async def test_is_ip_blocked(self, security_service, mock_cache_manager):
        """IP 차단 상태 확인 테스트"""
        ip_address = "192.168.1.100"
        
        # 차단되지 않은 상태 확인
        is_blocked = await security_service.is_ip_blocked(ip_address)
        assert is_blocked is False
        
        # IP 차단
        await security_service.block_ip(ip_address)
        
        # 캐시 모의 설정
        mock_cache_manager.get.return_value = {
            "ip": ip_address,
            "blocked_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "reason": "Test block"
        }
        
        # 차단된 상태 확인
        is_blocked = await security_service.is_ip_blocked(ip_address)
        assert is_blocked is True
        
        # 캐시 호출 확인
        mock_cache_manager.get.assert_called_with(f"blocked_ip_{ip_address}")
    
    @pytest.mark.asyncio
    async def test_get_security_metrics(self, security_service):
        """보안 메트릭 가져오기 테스트"""
        # 메트릭 업데이트
        security_service.metrics.total_events = 100
        security_service.metrics.events_by_type["injection_attempt"] = 10
        security_service.metrics.events_by_severity["high"] = 20
        security_service.metrics.false_positives = 5
        
        metrics = await security_service.get_security_metrics()
        
        assert isinstance(metrics, SecurityMetrics)
        assert metrics.total_events == 100
        assert metrics.events_by_type["injection_attempt"] == 10
        assert metrics.events_by_severity["high"] == 20
        assert metrics.false_positives == 5
        assert metrics.detection_accuracy == 0.95  # (100 - 5) / 100
        assert isinstance(metrics.last_updated, datetime)
    
    @pytest.mark.asyncio
    async def test_get_recent_events(self, security_service, sample_security_event):
        """최근 보안 이벤트 가져오기 테스트"""
        # 이벤트 추가
        for i in range(10):
            event = SecurityEvent(
                id=f"event_{i}",
                event_type=SecurityEventType.INJECTION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                source_ip=f"192.168.1.{100 + i}",
                description=f"Test event {i}"
            )
            security_service.events.append(event)
        
        # 모든 이벤트 가져오기
        events = await security_service.get_recent_events(limit=20)
        assert len(events) == 10
        
        # 심각도 필터링
        high_events = await security_service.get_recent_events(
            limit=20, 
            severity=SecuritySeverity.HIGH
        )
        assert len(high_events) == 10
        
        # 이벤트 타입 필터링
        injection_events = await security_service.get_recent_events(
            limit=20,
            event_type=SecurityEventType.INJECTION_ATTEMPT
        )
        assert len(injection_events) == 10
        
        # 제한 확인
        limited_events = await security_service.get_recent_events(limit=5)
        assert len(limited_events) == 5
    
    @pytest.mark.asyncio
    async def test_evaluate_rule_match(self, security_service, sample_security_rule, sample_security_event):
        """보안 규칙 평가 테스트 (일치)"""
        # 규칙 추가
        security_service.rules[sample_security_rule.id] = sample_security_rule
        
        # 규칙 평가
        matches = await security_service._evaluate_rule(sample_security_rule, sample_security_event)
        
        assert matches is True
    
    @pytest.mark.asyncio
    async def test_evaluate_rule_no_match(self, security_service, sample_security_rule):
        """보안 규칙 평가 테스트 (불일치)"""
        # 다른 타입의 이벤트 생성
        different_event = SecurityEvent(
            id="different_event",
            event_type=SecurityEventType.XSS_ATTEMPT,  # 다른 타입
            severity=SecuritySeverity.HIGH,
            timestamp=datetime.utcnow(),
            source_ip="192.168.1.100"
        )
        
        # 규칙 추가
        security_service.rules[sample_security_rule.id] = sample_security_rule
        
        # 규칙 평가
        matches = await security_service._evaluate_rule(sample_security_rule, different_event)
        
        assert matches is False
    
    @pytest.mark.asyncio
    async def test_execute_security_action_block_ip(self, security_service, sample_security_event, mock_cache_manager):
        """보안 액션 실행 테스트 (IP 차단)"""
        rule = SecurityRule(
            id="test_rule",
            name="Test Rule",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            conditions={},
            actions=[SecurityAction.BLOCK_IP],
            severity=SecuritySeverity.HIGH
        )
        
        await security_service._execute_security_action(
            SecurityAction.BLOCK_IP,
            sample_security_event,
            rule
        )
        
        # IP 차단 확인
        assert sample_security_event.source_ip in security_service.blocked_ips
        assert SecurityAction.BLOCK_IP in sample_security_event.response_actions
    
    @pytest.mark.asyncio
    async def test_execute_security_action_alert_admin(self, security_service, sample_security_event):
        """보안 액션 실행 테스트 (관리자 알림)"""
        rule = SecurityRule(
            id="test_rule",
            name="Test Rule",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            conditions={},
            actions=[SecurityAction.ALERT_ADMIN],
            severity=SecuritySeverity.HIGH
        )
        
        await security_service._execute_security_action(
            SecurityAction.ALERT_ADMIN,
            sample_security_event,
            rule
        )
        
        # 알림 액션 확인
        assert SecurityAction.ALERT_ADMIN in sample_security_event.response_actions
    
    @pytest.mark.asyncio
    async def test_detect_brute_force_attacks(self, security_service):
        """무차별 대입 공격 감지 테스트"""
        source_ip = "192.168.1.100"
        
        # 10개 이상의 실패 로그인 이벤트 생성
        for i in range(12):
            event = SecurityEvent(
                id=f"failed_login_{i}",
                event_type=SecurityEventType.FAILED_LOGIN,
                severity=SecuritySeverity.MEDIUM,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                source_ip=source_ip,
                user_id="user123",
                description=f"Failed login attempt {i}"
            )
            security_service.events.append(event)
        
        # 무차별 대입 공격 감지
        await security_service._detect_brute_force_attacks()
        
        # 무차별 대입 공격 이벤트 확인
        brute_force_events = [e for e in security_service.events if e.event_type == SecurityEventType.BRUTE_FORCE]
        assert len(brute_force_events) > 0
        
        brute_force_event = brute_force_events[0]
        assert brute_force_event.source_ip == source_ip
        assert brute_force_event.severity == SecuritySeverity.HIGH
        assert "12 failed attempts" in brute_force_event.description
    
    @pytest.mark.asyncio
    async def test_detect_unusual_traffic(self, security_service):
        """비정상적인 트래픽 감지 테스트"""
        # 정상 트래픽 이벤트 생성
        for i in range(10):
            event = SecurityEvent(
                id=f"normal_traffic_{i}",
                event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                severity=SecuritySeverity.LOW,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                source_ip=f"192.168.1.{100 + i}",
                description="Normal request"
            )
            security_service.events.append(event)
        
        # 비정상적인 트래픽 이벤트 생성 (높은 요청률)
        for i in range(50):
            event = SecurityEvent(
                id=f"high_traffic_{i}",
                event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                severity=SecuritySeverity.LOW,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                source_ip="192.168.1.200",  # 동일 IP에서 많은 요청
                description="High volume request"
            )
            security_service.events.append(event)
        
        # 비정상 트래픽 감지
        await security_service._detect_unusual_traffic()
        
        # 비정상 트래픽 이벤트 확인
        unusual_traffic_events = [e for e in security_service.events if e.event_type == SecurityEventType.UNUSUAL_TRAFFIC]
        assert len(unusual_traffic_events) > 0
        
        unusual_traffic_event = unusual_traffic_events[0]
        assert unusual_traffic_event.source_ip == "192.168.1.200"
        assert unusual_traffic_event.severity == SecuritySeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_detect_system_anomalies(self, security_service):
        """시스템 이상 감지 테스트"""
        # 많은 수의 보안 이벤트 생성 (시스템 이상 시뮬레이션)
        for i in range(300):  # 300개 이상의 이벤트 (50 events/minute * 6 minutes)
            event = SecurityEvent(
                id=f"system_anomaly_{i}",
                event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                severity=SecuritySeverity.LOW,
                timestamp=datetime.utcnow() - timedelta(minutes=i//50),
                source_ip=f"192.168.1.{100 + (i % 10)}",
                description=f"System anomaly test {i}"
            )
            security_service.events.append(event)
        
        # 시스템 이상 감지
        await security_service._detect_system_anomalies()
        
        # 시스템 이상 이벤트 확인
        system_anomaly_events = [e for e in security_service.events if e.event_type == SecurityEventType.SYSTEM_ANOMALY]
        assert len(system_anomaly_events) > 0
        
        system_anomaly_event = system_anomaly_events[0]
        assert system_anomaly_event.source_ip == "system"
        assert system_anomaly_event.severity == SecuritySeverity.HIGH
    
    def test_load_injection_patterns(self, security_service):
        """인젝션 패턴 로드 테스트"""
        patterns = security_service._load_injection_patterns()
        
        assert isinstance(patterns, dict)
        assert "sql_union" in patterns
        assert "sql_comment" in patterns
        assert "sql_drop" in patterns
        assert "sql_insert" in patterns
        assert "sql_update" in patterns
        assert "sql_delete" in patterns
        assert "sql_exec" in patterns
        
        # 패턴 형식 확인
        for pattern_name, pattern in patterns.items():
            assert isinstance(pattern, str)
            assert len(pattern) > 0
    
    def test_load_xss_patterns(self, security_service):
        """XSS 패턴 로드 테스트"""
        patterns = security_service._load_xss_patterns()
        
        assert isinstance(patterns, dict)
        assert "script_tag" in patterns
        assert "javascript" in patterns
        assert "on_event" in patterns
        assert "iframe" in patterns
        assert "object" in patterns
        assert "embed" in patterns
        assert "link" in patterns
        assert "meta" in patterns
        
        # 패턴 형식 확인
        for pattern_name, pattern in patterns.items():
            assert isinstance(pattern, str)
            assert len(pattern) > 0
    
    def test_load_suspicious_user_agents(self, security_service):
        """의심스러운 사용자 에이전트 로드 테스트"""
        user_agents = security_service._load_suspicious_user_agents()
        
        assert isinstance(user_agents, list)
        assert len(user_agents) > 0
        
        # 일반적인 의심스러운 사용자 에이전트 확인
        suspicious_agents = ["sqlmap", "nikto", "dirb", "nmap", "burp", "curl"]
        for agent in suspicious_agents:
            assert any(agent.lower() in ua.lower() for ua in user_agents)
    
    def test_initialize_default_rules(self, security_service):
        """기본 보안 규칙 초기화 테스트"""
        # 기본 규칙 초기화
        security_service._initialize_default_rules()
        
        # 기본 규칙 확인
        assert "brute_force_detection" in security_service.rules
        assert "injection_attack_detection" in security.service.rules
        assert "rate_limit_violation" in security_service.rules
        assert "suspicious_request_detection" in security_service.rules
        
        # 규칙 속성 확인
        brute_force_rule = security_service.rules["brute_force_detection"]
        assert brute_force_rule.event_type == SecurityEventType.BRUTE_FORCE
        assert SecurityAction.BLOCK_IP in brute_force_rule.actions
        assert SecurityAction.ALERT_ADMIN in brute_force_rule.actions
        assert brute_force_rule.severity == SecuritySeverity.HIGH