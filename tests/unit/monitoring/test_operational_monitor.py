"""
운영 모니터링 단위 테스트

이 모듈은 운영 모니터링 시스템의 개별 기능을 테스트합니다.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from backend.monitoring.operational_monitor import OperationalMonitor


class TestOperationalMonitor:
    """운영 모니터링 단위 테스트 클래스"""
    
    @pytest.fixture
    def operational_monitor(self):
        """운영 모니터링 픽스처"""
        return OperationalMonitor()
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """모의 메트릭 수집기 픽스처"""
        collector = MagicMock()
        collector.get_cpu_usage.return_value = 45.5
        collector.get_memory_usage.return_value = 60.2
        collector.get_disk_usage.return_value = 30.8
        collector.get_network_latency.return_value = 25.5
        collector.get_cache_hit_rate.return_value = 85.3
        collector.get_database_connections.return_value = 15
        collector.get_active_requests.return_value = 25
        return collector
    
    def test_monitor_initialization(self, operational_monitor):
        """모니터 초기화 테스트"""
        assert operational_monitor is not None
        assert hasattr(operational_monitor, 'metrics_collector')
        assert hasattr(operational_monitor, 'alert_manager')
        assert hasattr(operational_monitor, 'health_checker')
        assert hasattr(operational_monitor, 'start_monitoring')
        assert hasattr(operational_monitor, 'stop_monitoring')
    
    def test_system_health_check_healthy(self, operational_monitor, mock_metrics_collector):
        """정상 시스템 상태 확인 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 정상 상태 메트릭 설정
        mock_metrics_collector.get_cpu_usage.return_value = 45.5  # < 80%
        mock_metrics_collector.get_memory_usage.return_value = 60.2  # < 85%
        mock_metrics_collector.get_disk_usage.return_value = 30.8  # < 90%
        mock_metrics_collector.get_network_latency.return_value = 25.5  # < 100ms
        mock_metrics_collector.get_cache_hit_rate.return_value = 85.3  # > 70%
        
        health_status = operational_monitor.check_system_health()
        
        assert health_status["status"] == "healthy"
        assert health_status["cpu_usage"] == 45.5
        assert health_status["memory_usage"] == 60.2
        assert health_status["disk_usage"] == 30.8
        assert health_status["network_latency"] == 25.5
        assert health_status["cache_hit_rate"] == 85.3
    
    def test_system_health_check_warning(self, operational_monitor, mock_metrics_collector):
        """경고 시스템 상태 확인 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 경고 상태 메트릭 설정
        mock_metrics_collector.get_cpu_usage.return_value = 75.5  # 70-80%
        mock_metrics_collector.get_memory_usage.return_value = 75.2  # 70-85%
        mock_metrics_collector.get_network_latency.return_value = 85.5  # 50-100ms
        mock_metrics_collector.get_cache_hit_rate.return_value = 65.3  # 50-70%
        
        health_status = operational_monitor.check_system_health()
        
        assert health_status["status"] == "warning"
        assert health_status["cpu_usage"] == 75.5
        assert health_status["memory_usage"] == 75.2
        assert health_status["network_latency"] == 85.5
        assert health_status["cache_hit_rate"] == 65.3
    
    def test_system_health_check_critical(self, operational_monitor, mock_metrics_collector):
        """심각 시스템 상태 확인 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 심각 상태 메트릭 설정
        mock_metrics_collector.get_cpu_usage.return_value = 85.5  # > 80%
        mock_metrics_collector.get_memory_usage.return_value = 90.2  # > 85%
        mock_metrics_collector.get_disk_usage.return_value = 95.8  # > 90%
        mock_metrics_collector.get_network_latency.return_value = 150.5  # > 100ms
        mock_metrics_collector.get_cache_hit_rate.return_value = 35.3  # < 50%
        
        health_status = operational_monitor.check_system_health()
        
        assert health_status["status"] == "critical"
        assert health_status["cpu_usage"] == 85.5
        assert health_status["memory_usage"] == 90.2
        assert health_status["disk_usage"] == 95.8
        assert health_status["network_latency"] == 150.5
        assert health_status["cache_hit_rate"] == 35.3
    
    def test_alert_creation(self, operational_monitor, mock_metrics_collector):
        """알림 생성 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 알림 조건 설정
        mock_metrics_collector.get_cpu_usage.return_value = 85.5  # > 80%
        
        # 알림 관리자 모의
        operational_monitor.alert_manager = MagicMock()
        
        # 시스템 상태 확인
        operational_monitor.check_system_health()
        
        # 알림 생성 확인
        operational_monitor.alert_manager.create_alert.assert_called()
        
        # 알림 인자 확인
        call_args = operational_monitor.alert_manager.create_alert.call_args
        assert call_args is not None
        alert_data = call_args[0][0] if call_args[0] else call_args[1]
        
        assert alert_data["type"] == "performance"
        assert "cpu" in alert_data["message"].lower()
        assert alert_data["severity"] == "critical"
    
    def test_performance_metrics_collection(self, operational_monitor, mock_metrics_collector):
        """성능 메트릭 수집 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        metrics = operational_monitor.collect_performance_metrics()
        
        # 메트릭 수집 확인
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "disk_usage" in metrics
        assert "network_latency" in metrics
        assert "cache_hit_rate" in metrics
        assert "database_connections" in metrics
        assert "active_requests" in metrics
        assert "timestamp" in metrics
        
        # 메트릭 값 확인
        assert metrics["cpu_usage"] == 45.5
        assert metrics["memory_usage"] == 60.2
        assert metrics["disk_usage"] == 30.8
        assert metrics["network_latency"] == 25.5
        assert metrics["cache_hit_rate"] == 85.3
        assert metrics["database_connections"] == 15
        assert metrics["active_requests"] == 25
    
    def test_application_metrics_collection(self, operational_monitor):
        """애플리케이션 메트릭 수집 테스트"""
        with patch('backend.monitoring.operational_monitor.get_application_metrics') as mock_app_metrics:
            mock_app_metrics.return_value = {
                "request_count": 1000,
                "error_rate": 0.05,
                "average_response_time": 150.5,
                "active_users": 250
            }
            
            app_metrics = operational_monitor.collect_application_metrics()
            
            assert app_metrics["request_count"] == 1000
            assert app_metrics["error_rate"] == 0.05
            assert app_metrics["average_response_time"] == 150.5
            assert app_metrics["active_users"] == 250
    
    def test_database_metrics_collection(self, operational_monitor):
        """데이터베이스 메트릭 수집 테스트"""
        with patch('backend.monitoring.operational_monitor.get_database_metrics') as mock_db_metrics:
            mock_db_metrics.return_value = {
                "connection_pool_size": 20,
                "active_connections": 15,
                "query_time_avg": 25.5,
                "query_time_max": 150.2,
                "slow_query_count": 3
            }
            
            db_metrics = operational_monitor.collect_database_metrics()
            
            assert db_metrics["connection_pool_size"] == 20
            assert db_metrics["active_connections"] == 15
            assert db_metrics["query_time_avg"] == 25.5
            assert db_metrics["query_time_max"] == 150.2
            assert db_metrics["slow_query_count"] == 3
    
    def test_cache_metrics_collection(self, operational_monitor):
        """캐시 메트릭 수집 테스트"""
        with patch('backend.monitoring.operational_monitor.get_cache_metrics') as mock_cache_metrics:
            mock_cache_metrics.return_value = {
                "hit_rate": 85.3,
                "miss_rate": 14.7,
                "eviction_count": 125,
                "memory_usage": 256.5,
                "key_count": 10000
            }
            
            cache_metrics = operational_monitor.collect_cache_metrics()
            
            assert cache_metrics["hit_rate"] == 85.3
            assert cache_metrics["miss_rate"] == 14.7
            assert cache_metrics["eviction_count"] == 125
            assert cache_metrics["memory_usage"] == 256.5
            assert cache_metrics["key_count"] == 10000
    
    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, operational_monitor):
        """모니터링 시작/중지 테스트"""
        # 모니터링 시작
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task
            
            await operational_monitor.start_monitoring()
            
            # 모니터링 태스크 생성 확인
            mock_create_task.assert_called()
            
            # 모니터링 상태 확인
            assert operational_monitor.is_monitoring is True
        
        # 모니터링 중지
        await operational_monitor.stop_monitoring()
        
        # 모니터링 상태 확인
        assert operational_monitor.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_continuous_monitoring(self, operational_monitor, mock_metrics_collector):
        """연속 모니터링 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 모니터링 간격 단축 (테스트용)
        operational_monitor.monitoring_interval = 0.1
        
        # 모니터링 실행 횟수 추적
        monitoring_calls = []
        
        original_check_health = operational_monitor.check_system_health
        def track_health_check():
            monitoring_calls.append(time.time())
            return original_check_health()
        
        operational_monitor.check_system_health = track_health_check
        
        # 모니터링 시작
        monitor_task = await operational_monitor.start_monitoring()
        
        # 0.5초 대기 (약 5번의 모니터링 실행)
        await asyncio.sleep(0.5)
        
        # 모니터링 중지
        await operational_monitor.stop_monitoring()
        
        # 모니터링 실행 횟수 확인
        assert len(monitoring_calls) >= 3  # 최소 3번 실행
        
        # 모니터링 간격 확인
        if len(monitoring_calls) >= 2:
            interval = monitoring_calls[1] - monitoring_calls[0]
            assert 0.08 <= interval <= 0.15  # 약간의 오차 허용
    
    def test_alert_threshold_configuration(self, operational_monitor):
        """알림 임계값 구성 테스트"""
        # 사용자 정의 임계값 설정
        custom_thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 75.0,
            "memory_critical": 90.0,
            "disk_warning": 80.0,
            "disk_critical": 95.0,
            "network_latency_warning": 50.0,
            "network_latency_critical": 150.0,
            "cache_hit_rate_warning": 60.0,
            "cache_hit_rate_critical": 40.0
        }
        
        operational_monitor.update_alert_thresholds(custom_thresholds)
        
        # 임계값 업데이트 확인
        assert operational_monitor.alert_thresholds["cpu_warning"] == 70.0
        assert operational_monitor.alert_thresholds["cpu_critical"] == 90.0
        assert operational_monitor.alert_thresholds["memory_warning"] == 75.0
        assert operational_monitor.alert_thresholds["memory_critical"] == 90.0
        assert operational_monitor.alert_thresholds["disk_warning"] == 80.0
        assert operational_monitor.alert_thresholds["disk_critical"] == 95.0
        assert operational_monitor.alert_thresholds["network_latency_warning"] == 50.0
        assert operational_monitor.alert_thresholds["network_latency_critical"] == 150.0
        assert operational_monitor.alert_thresholds["cache_hit_rate_warning"] == 60.0
        assert operational_monitor.alert_thresholds["cache_hit_rate_critical"] == 40.0
    
    def test_metrics_history_tracking(self, operational_monitor, mock_metrics_collector):
        """메트릭 기록 추적 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 메트릭 기록 활성화
        operational_monitor.enable_metrics_history(max_history_size=10)
        
        # 여러 번의 메트릭 수집
        for i in range(5):
            mock_metrics_collector.get_cpu_usage.return_value = 40.0 + i * 5
            operational_monitor.collect_and_store_metrics()
            time.sleep(0.01)  # 작은 지연
        
        # 메트릭 기록 확인
        history = operational_monitor.get_metrics_history()
        
        assert len(history) == 5
        assert history[0]["cpu_usage"] == 40.0
        assert history[4]["cpu_usage"] == 60.0
        
        # 모든 기록에 타임스탬프가 있는지 확인
        for record in history:
            assert "timestamp" in record
    
    def test_metrics_aggregation(self, operational_monitor):
        """메트릭 집계 테스트"""
        # 샘플 메트릭 기록 생성
        sample_metrics = [
            {"cpu_usage": 40.0, "memory_usage": 60.0, "timestamp": time.time() - 300},
            {"cpu_usage": 45.0, "memory_usage": 62.0, "timestamp": time.time() - 240},
            {"cpu_usage": 50.0, "memory_usage": 65.0, "timestamp": time.time() - 180},
            {"cpu_usage": 55.0, "memory_usage": 68.0, "timestamp": time.time() - 120},
            {"cpu_usage": 60.0, "memory_usage": 70.0, "timestamp": time.time() - 60}
        ]
        
        operational_monitor.metrics_history = sample_metrics
        
        # 시간 범위 집계
        aggregated = operational_monitor.aggregate_metrics(
            start_time=time.time() - 300,
            end_time=time.time(),
            interval="5m"
        )
        
        assert len(aggregated) == 1  # 5분 간격으로 1개 집계 결과
        
        # 집계 값 확인
        avg_cpu = sum(m["cpu_usage"] for m in sample_metrics) / len(sample_metrics)
        avg_memory = sum(m["memory_usage"] for m in sample_metrics) / len(sample_metrics)
        
        assert aggregated[0]["cpu_usage_avg"] == avg_cpu
        assert aggregated[0]["memory_usage_avg"] == avg_memory
        assert aggregated[0]["cpu_usage_min"] == 40.0
        assert aggregated[0]["cpu_usage_max"] == 60.0
    
    def test_auto_recovery_trigger(self, operational_monitor, mock_metrics_collector):
        """자동 복구 트리거 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 심각 상태 메트릭 설정
        mock_metrics_collector.get_memory_usage.return_value = 95.0  # > 85%
        
        # 자동 복구 핸들러 모의
        recovery_handler = MagicMock()
        operational_monitor.add_recovery_handler("memory_pressure", recovery_handler)
        
        # 시스템 상태 확인
        health_status = operational_monitor.check_system_health()
        
        # 심각 상태 확인
        assert health_status["status"] == "critical"
        
        # 자동 복구 핸들러 호출 확인
        recovery_handler.assert_called_once()
        
        # 복구 핸들러 인자 확인
        call_args = recovery_handler.call_args
        assert call_args is not None
        recovery_data = call_args[0][0] if call_args[0] else call_args[1]
        
        assert recovery_data["metric"] == "memory_usage"
        assert recovery_data["value"] == 95.0
        assert recovery_data["threshold"] == 85.0
        assert recovery_data["severity"] == "critical"
    
    def test_monitoring_dashboard_data(self, operational_monitor, mock_metrics_collector):
        """모니터링 대시보드 데이터 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 대시보드 데이터 생성
        dashboard_data = operational_monitor.get_dashboard_data()
        
        # 필수 필드 확인
        assert "system_health" in dashboard_data
        assert "performance_metrics" in dashboard_data
        assert "application_metrics" in dashboard_data
        assert "database_metrics" in dashboard_data
        assert "cache_metrics" in dashboard_data
        assert "recent_alerts" in dashboard_data
        assert "metrics_history" in dashboard_data
        
        # 시스템 상태 확인
        system_health = dashboard_data["system_health"]
        assert "status" in system_health
        assert "timestamp" in system_health
        
        # 성능 메트릭 확인
        performance_metrics = dashboard_data["performance_metrics"]
        assert "cpu_usage" in performance_metrics
        assert "memory_usage" in performance_metrics
        assert "disk_usage" in performance_metrics
        assert "network_latency" in performance_metrics
    
    def test_monitoring_error_handling(self, operational_monitor):
        """모니터링 오류 처리 테스트"""
        # 메트릭 수집 오류 시뮬레이션
        operational_monitor.metrics_collector = MagicMock()
        operational_monitor.metrics_collector.get_cpu_usage.side_effect = Exception("Metrics collection error")
        
        # 오류가 발생해도 모니터링이 계속되어야 함
        try:
            health_status = operational_monitor.check_system_health()
            
            # 오류 상태 반환 확인
            assert health_status["status"] == "error"
            assert "error" in health_status
            assert "Metrics collection error" in health_status["error"]
        except Exception:
            pytest.fail("Monitoring should handle errors gracefully")
    
    def test_monitoring_performance_impact(self, operational_monitor, mock_metrics_collector):
        """모니터링 성능 영향 테스트"""
        operational_monitor.metrics_collector = mock_metrics_collector
        
        # 성능 측정
        start_time = time.time()
        
        # 여러 번의 모니터링 실행
        for _ in range(100):
            operational_monitor.check_system_health()
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_check = total_time / 100
        
        # 모니터링이 성능에 큰 영향을 주지 않아야 함
        assert avg_time_per_check < 0.01  # 확인당 10ms 이하
        
        print(f"Monitoring Performance Impact:")
        print(f"  Total Time: {total_time:.4f}s")
        print(f"  Average Time per Check: {avg_time_per_check:.6f}s")