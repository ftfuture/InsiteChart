"""
실시간 운영 모니터링 시스템

이 모듈은 시스템 상태를 실시간으로 모니터링하고, 임계값을 기반으로 알림을 생성하며,
자동 복구 기능을 제공합니다.
"""

import asyncio
import time
import json
import psutil
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class OperationalStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"

@dataclass
class OperationalAlert:
    alert_id: str
    severity: AlertSeverity
    message: str
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

@dataclass
class SystemHealthMetrics:
    timestamp: datetime
    status: OperationalStatus
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    cache_hit_rate: float
    api_response_time: float
    error_rate: float
    active_connections: int
    queue_size: int

class OperationalMonitor:
    """운영 모니터링 시스템"""
    
    def __init__(
        self,
        monitoring_interval: int = 30,
        alert_retention_days: int = 7,
        health_retention_hours: int = 24,
        enable_auto_recovery: bool = True
    ):
        self.monitoring_interval = monitoring_interval
        self.alert_retention_days = alert_retention_days
        self.health_retention_hours = health_retention_hours
        self.enable_auto_recovery = enable_auto_recovery
        
        # 상태 관리
        self.current_status = OperationalStatus.HEALTHY
        self.last_status_change = datetime.utcnow()
        
        # 데이터 저장
        self.active_alerts: Dict[str, OperationalAlert] = {}
        self.alert_history: List[OperationalAlert] = []
        self.health_metrics: List[SystemHealthMetrics] = []
        
        # 모니터링 대상
        self.monitored_services: Dict[str, Any] = {}
        self.health_checks: Dict[str, Callable] = {}
        
        # 알림 콜백
        self.alert_callbacks: List[Callable] = []
        self.status_callbacks: List[Callable] = []
        
        # 자동 복구
        self.recovery_actions: Dict[str, Callable] = {}
        
        # 통계
        self.stats = {
            "total_alerts": 0,
            "resolved_alerts": 0,
            "auto_recoveries": 0,
            "status_changes": 0
        }
        
        # 모니터링 상태
        self.is_monitoring = False
        
        # 알림 임계값
        self.alert_thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 80.0,
            "memory_warning": 75.0,
            "memory_critical": 85.0,
            "disk_warning": 85.0,
            "disk_critical": 90.0,
            "network_latency_warning": 50.0,
            "network_latency_critical": 100.0,
            "cache_hit_rate_warning": 70.0,
            "cache_hit_rate_critical": 50.0
        }
        
        # 메트릭 수집기
        self.metrics_collector = None
        
        # 알림 관리자
        self.alert_manager = self
        
        # 메트릭 기록
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self):
        """모니터링 시작"""
        self.logger.info("Starting operational monitor")
        self.is_monitoring = True
        
        # 모니터링 루프 시작
        asyncio.create_task(self._monitoring_loop())
        
        # 상태 확인 루프 시작
        asyncio.create_task(self._health_check_loop())
        
        # 알림 정리 루프 시작
        asyncio.create_task(self._alert_cleanup_loop())
    
    async def start(self):
        """모니터링 시작 (별칭)"""
        await self.start_monitoring()
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.logger.info("Stopping operational monitor")
        self.is_monitoring = False
        # 상태 저장 및 정리 로직
    
    async def stop(self):
        """모니터링 중지 (별칭)"""
        await self.stop_monitoring()
    
    def register_service(self, name: str, service: Any, health_check: Optional[Callable] = None):
        """서비스 등록"""
        self.monitored_services[name] = service
        
        if health_check:
            self.health_checks[name] = health_check
        
        self.logger.info(f"Registered service: {name}")
    
    def register_alert_callback(self, callback: Callable):
        """알림 콜백 등록"""
        self.alert_callbacks.append(callback)
    
    def register_status_callback(self, callback: Callable):
        """상태 변경 콜백 등록"""
        self.status_callbacks.append(callback)
    
    def register_recovery_action(self, alert_type: str, action: Callable):
        """복구 액션 등록"""
        self.recovery_actions[alert_type] = action
        self.logger.info(f"Registered recovery action for: {alert_type}")
    
    async def _monitoring_loop(self):
        """모니터링 루프"""
        while True:
            try:
                await self._collect_metrics()
                await self._analyze_metrics()
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _health_check_loop(self):
        """상태 확인 루프"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(60)  # 1분마다 상태 확인
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {str(e)}")
                await asyncio.sleep(60)
    
    async def _alert_cleanup_loop(self):
        """알림 정리 루프"""
        while True:
            try:
                await self._cleanup_old_alerts()
                await asyncio.sleep(3600)  # 1시간마다 정리
                
            except Exception as e:
                self.logger.error(f"Error in alert cleanup loop: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _collect_metrics(self):
        """메트릭 수집"""
        try:
            # 시스템 메트릭 수집
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 네트워크 지연 측정
            network_latency = await self._measure_network_latency()
            
            # 캐시 성능
            cache_hit_rate = await self._get_cache_hit_rate()
            
            # API 응답 시간
            api_response_time = await self._get_api_response_time()
            
            # 에러율
            error_rate = await self._get_error_rate()
            
            # 활성 연결 수
            active_connections = await self._get_active_connections()
            
            # 큐 크기
            queue_size = await self._get_queue_size()
            
            # 상태 메트릭 생성
            metrics = SystemHealthMetrics(
                timestamp=datetime.utcnow(),
                status=self.current_status,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_latency=network_latency,
                cache_hit_rate=cache_hit_rate,
                api_response_time=api_response_time,
                error_rate=error_rate,
                active_connections=active_connections,
                queue_size=queue_size
            )
            
            # 메트릭 저장
            self.health_metrics.append(metrics)
            
            # 오래된 메트릭 정리
            cutoff_time = datetime.utcnow() - timedelta(hours=self.health_retention_hours)
            self.health_metrics = [
                m for m in self.health_metrics 
                if m.timestamp > cutoff_time
            ]
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {str(e)}")
    
    async def _analyze_metrics(self):
        """메트릭 분석 및 알림 생성"""
        if not self.health_metrics:
            return
        
        latest_metrics = self.health_metrics[-1]
        
        # 임계값 확인 및 알림 생성
        await self._check_cpu_usage(latest_metrics.cpu_usage)
        await self._check_memory_usage(latest_metrics.memory_usage)
        await self._check_disk_usage(latest_metrics.disk_usage)
        await self._check_network_latency(latest_metrics.network_latency)
        await self._check_cache_hit_rate(latest_metrics.cache_hit_rate)
        await self._check_api_response_time(latest_metrics.api_response_time)
        await self._check_error_rate(latest_metrics.error_rate)
        
        # 전체 상태 평가
        new_status = self._evaluate_overall_status(latest_metrics)
        
        if new_status != self.current_status:
            await self._handle_status_change(new_status)
    
    async def _check_cpu_usage(self, cpu_usage: float):
        """CPU 사용량 확인"""
        if cpu_usage > 90:
            await self._create_alert(
                alert_id=f"cpu_high_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                message=f"High CPU usage: {cpu_usage:.1f}%",
                source="system",
                data={"cpu_usage": cpu_usage, "threshold": 90}
            )
        elif cpu_usage > 80:
            await self._create_alert(
                alert_id=f"cpu_warning_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"Elevated CPU usage: {cpu_usage:.1f}%",
                source="system",
                data={"cpu_usage": cpu_usage, "threshold": 80}
            )
    
    async def _check_memory_usage(self, memory_usage: float):
        """메모리 사용량 확인"""
        if memory_usage > 90:
            await self._create_alert(
                alert_id=f"memory_high_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                message=f"High memory usage: {memory_usage:.1f}%",
                source="system",
                data={"memory_usage": memory_usage, "threshold": 90}
            )
        elif memory_usage > 80:
            await self._create_alert(
                alert_id=f"memory_warning_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"Elevated memory usage: {memory_usage:.1f}%",
                source="system",
                data={"memory_usage": memory_usage, "threshold": 80}
            )
    
    async def _check_disk_usage(self, disk_usage: float):
        """디스크 사용량 확인"""
        if disk_usage > 95:
            await self._create_alert(
                alert_id=f"disk_critical_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                message=f"Critical disk usage: {disk_usage:.1f}%",
                source="system",
                data={"disk_usage": disk_usage, "threshold": 95}
            )
        elif disk_usage > 85:
            await self._create_alert(
                alert_id=f"disk_warning_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"High disk usage: {disk_usage:.1f}%",
                source="system",
                data={"disk_usage": disk_usage, "threshold": 85}
            )
    
    async def _check_network_latency(self, network_latency: float):
        """네트워크 지연 확인"""
        if network_latency > 1000:  # 1초
            await self._create_alert(
                alert_id=f"network_high_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"High network latency: {network_latency:.0f}ms",
                source="network",
                data={"network_latency": network_latency, "threshold": 1000}
            )
    
    async def _check_cache_hit_rate(self, cache_hit_rate: float):
        """캐시 적중률 확인"""
        if cache_hit_rate < 50:  # 50%
            await self._create_alert(
                alert_id=f"cache_low_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"Low cache hit rate: {cache_hit_rate:.1f}%",
                source="cache",
                data={"cache_hit_rate": cache_hit_rate, "threshold": 50}
            )
    
    async def _check_api_response_time(self, api_response_time: float):
        """API 응답 시간 확인"""
        if api_response_time > 2000:  # 2초
            await self._create_alert(
                alert_id=f"api_slow_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"Slow API response time: {api_response_time:.0f}ms",
                source="api",
                data={"api_response_time": api_response_time, "threshold": 2000}
            )
        elif api_response_time > 5000:  # 5초
            await self._create_alert(
                alert_id=f"api_critical_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                message=f"Critical API response time: {api_response_time:.0f}ms",
                source="api",
                data={"api_response_time": api_response_time, "threshold": 5000}
            )
    
    async def _check_error_rate(self, error_rate: float):
        """에러율 확인"""
        if error_rate > 10:  # 10%
            await self._create_alert(
                alert_id=f"error_high_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                message=f"High error rate: {error_rate:.1f}%",
                source="application",
                data={"error_rate": error_rate, "threshold": 10}
            )
        elif error_rate > 5:  # 5%
            await self._create_alert(
                alert_id=f"error_warning_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                message=f"Elevated error rate: {error_rate:.1f}%",
                source="application",
                data={"error_rate": error_rate, "threshold": 5}
            )
    
    def _evaluate_overall_status(self, metrics: SystemHealthMetrics) -> OperationalStatus:
        """전체 상태 평가"""
        critical_issues = 0
        warning_issues = 0
        
        if metrics.cpu_usage > 90:
            critical_issues += 1
        elif metrics.cpu_usage > 80:
            warning_issues += 1
        
        if metrics.memory_usage > 90:
            critical_issues += 1
        elif metrics.memory_usage > 80:
            warning_issues += 1
        
        if metrics.disk_usage > 95:
            critical_issues += 1
        elif metrics.disk_usage > 85:
            warning_issues += 1
        
        if metrics.api_response_time > 5000:
            critical_issues += 1
        elif metrics.api_response_time > 2000:
            warning_issues += 1
        
        if metrics.error_rate > 10:
            critical_issues += 1
        elif metrics.error_rate > 5:
            warning_issues += 1
        
        if metrics.cache_hit_rate < 50:
            warning_issues += 1
        
        # 상태 결정
        if critical_issues > 0:
            return OperationalStatus.UNHEALTHY
        elif warning_issues > 2:
            return OperationalStatus.DEGRADED
        else:
            return OperationalStatus.HEALTHY
    
    async def _handle_status_change(self, new_status: OperationalStatus):
        """상태 변경 처리"""
        old_status = self.current_status
        self.current_status = new_status
        self.last_status_change = datetime.utcnow()
        self.stats["status_changes"] += 1
        
        # 상태 변경 알림 생성
        await self._create_alert(
            alert_id=f"status_change_{int(time.time())}",
            severity=AlertSeverity.INFO,
            message=f"System status changed from {old_status.value} to {new_status.value}",
            source="monitor",
            data={
                "old_status": old_status.value,
                "new_status": new_status.value,
                "change_time": self.last_status_change.isoformat()
            }
        )
        
        # 상태 콜백 호출
        for callback in self.status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_status, new_status)
                else:
                    callback(old_status, new_status)
            except Exception as e:
                self.logger.error(f"Error in status callback: {str(e)}")
        
        # 자동 복구 시도
        if self.enable_auto_recovery and new_status in [OperationalStatus.DEGRADED, OperationalStatus.UNHEALTHY]:
            await self._attempt_auto_recovery()
    
    async def _attempt_auto_recovery(self):
        """자동 복구 시도"""
        self.logger.info(f"Attempting auto recovery for status: {self.current_status.value}")
        
        # 활성 알림 확인 및 복구 액션 실행
        for alert_id, alert in self.active_alerts.items():
            if alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
                alert_type = alert.data.get("type", alert.source)
                
                if alert_type in self.recovery_actions:
                    try:
                        await self.recovery_actions[alert_type](alert)
                        self.stats["auto_recoveries"] += 1
                        self.logger.info(f"Auto recovery action executed for: {alert_type}")
                        
                    except Exception as e:
                        self.logger.error(f"Auto recovery failed for {alert_type}: {str(e)}")
    
    async def _create_alert(
        self,
        alert_id: str,
        severity: AlertSeverity,
        message: str,
        source: str,
        data: Dict[str, Any]
    ):
        """알림 생성"""
        # 중복 알림 확인
        if alert_id in self.active_alerts:
            return
        
        alert = OperationalAlert(
            alert_id=alert_id,
            severity=severity,
            message=message,
            source=source,
            timestamp=datetime.utcnow(),
            data=data
        )
        
        # 활성 알림에 추가
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.stats["total_alerts"] += 1
        
        # 알림 콜백 호출
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {str(e)}")
        
        self.logger.warning(f"Alert created: {message}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """알림 확인"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        
        self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """알림 해결"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        
        # 활성 알림에서 제거
        del self.active_alerts[alert_id]
        self.stats["resolved_alerts"] += 1
        
        self.logger.info(f"Alert resolved: {alert_id}")
        return True
    
    async def _perform_health_checks(self):
        """상태 확인 수행"""
        for service_name, health_check in self.health_checks.items():
            try:
                is_healthy = await health_check()
                
                if not is_healthy:
                    await self._create_alert(
                        alert_id=f"health_check_{service_name}_{int(time.time())}",
                        severity=AlertSeverity.WARNING,
                        message=f"Health check failed for service: {service_name}",
                        source="health_check",
                        data={"service": service_name, "healthy": False}
                    )
                
            except Exception as e:
                await self._create_alert(
                    alert_id=f"health_check_error_{service_name}_{int(time.time())}",
                    severity=AlertSeverity.ERROR,
                    message=f"Health check error for service {service_name}: {str(e)}",
                    source="health_check",
                    data={"service": service_name, "error": str(e)}
                )
    
    async def _cleanup_old_alerts(self):
        """오래된 알림 정리"""
        cutoff_time = datetime.utcnow() - timedelta(days=self.alert_retention_days)
        
        # 알림 기록 정리
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
    
    async def _measure_network_latency(self) -> float:
        """네트워크 지연 측정"""
        try:
            start_time = time.time()
            # 간단한 HTTP 요청으로 지연 측정
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://httpbin.org/delay/0', timeout=5) as response:
                    await response.text()
            return (time.time() - start_time) * 1000  # ms로 변환
        except:
            return 0.0
    
    async def _get_cache_hit_rate(self) -> float:
        """캐시 적중률 조회"""
        try:
            # 캐시 관리자에서 통계 조회
            from ..cache.resilient_cache_manager import resilient_cache_manager
            stats = await resilient_cache_manager.get_cache_stats()
            return stats.get("hit_rate", 0.0)
        except:
            return 0.0
    
    async def _get_api_response_time(self) -> float:
        """API 응답 시간 조회"""
        try:
            # 성능 모니터에서 평균 응답 시간 조회
            from .performance_monitor import performance_monitor
            summary = await performance_monitor.get_performance_summary()
            return summary.get("avg_response_time", 0.0) * 1000  # ms로 변환
        except:
            return 0.0
    
    async def _get_error_rate(self) -> float:
        """에러율 조회"""
        try:
            # 성능 모니터에서 에러율 조회
            from .performance_monitor import performance_monitor
            summary = await performance_monitor.get_performance_summary()
            return summary.get("error_rate", 0.0)
        except:
            return 0.0
    
    async def _get_active_connections(self) -> int:
        """활성 연결 수 조회"""
        try:
            # 현재 활성 연결 수 (구현 필요)
            return 0
        except:
            return 0
    
    async def _get_queue_size(self) -> int:
        """큐 크기 조회"""
        try:
            # 현재 큐 크기 (구현 필요)
            return 0
        except:
            return 0
    
    async def get_operational_status(self) -> Dict[str, Any]:
        """운영 상태 조회"""
        return {
            "status": self.current_status.value,
            "last_status_change": self.last_status_change.isoformat(),
            "active_alerts": len(self.active_alerts),
            "total_alerts": self.stats["total_alerts"],
            "resolved_alerts": self.stats["resolved_alerts"],
            "auto_recoveries": self.stats["auto_recoveries"],
            "status_changes": self.stats["status_changes"],
            "monitored_services": list(self.monitored_services.keys()),
            "latest_metrics": asdict(self.health_metrics[-1]) if self.health_metrics else None
        }
    
    async def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """활성 알림 조회"""
        alerts = []
        
        for alert in self.active_alerts.values():
            if severity is None or alert.severity == severity:
                alerts.append(asdict(alert))
        
        # 시간 역순으로 정렬
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        return alerts
    
    def check_system_health(self) -> Dict[str, Any]:
        """시스템 상태 확인"""
        if not self.health_metrics:
            return {
                "status": "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        latest = self.health_metrics[-1]
        
        # 상태 평가
        if latest.cpu_usage > self.alert_thresholds["cpu_critical"] or \
           latest.memory_usage > self.alert_thresholds["memory_critical"] or \
           latest.disk_usage > self.alert_thresholds["disk_critical"] or \
           latest.network_latency > self.alert_thresholds["network_latency_critical"] or \
           latest.cache_hit_rate < self.alert_thresholds["cache_hit_rate_critical"]:
            status = "critical"
        elif latest.cpu_usage > self.alert_thresholds["cpu_warning"] or \
             latest.memory_usage > self.alert_thresholds["memory_warning"] or \
             latest.disk_usage > self.alert_thresholds["disk_warning"] or \
             latest.network_latency > self.alert_thresholds["network_latency_warning"] or \
             latest.cache_hit_rate < self.alert_thresholds["cache_hit_rate_warning"]:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "cpu_usage": latest.cpu_usage,
            "memory_usage": latest.memory_usage,
            "disk_usage": latest.disk_usage,
            "network_latency": latest.network_latency,
            "cache_hit_rate": latest.cache_hit_rate,
            "timestamp": latest.timestamp.isoformat()
        }
    
    def collect_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 수집"""
        if not self.health_metrics:
            return {
                "timestamp": datetime.utcnow().isoformat()
            }
        
        latest = self.health_metrics[-1]
        
        return {
            "cpu_usage": latest.cpu_usage,
            "memory_usage": latest.memory_usage,
            "disk_usage": latest.disk_usage,
            "network_latency": latest.network_latency,
            "cache_hit_rate": latest.cache_hit_rate,
            "database_connections": latest.active_connections,
            "active_requests": latest.queue_size,
            "timestamp": latest.timestamp.isoformat()
        }
    
    def collect_application_metrics(self) -> Dict[str, Any]:
        """애플리케이션 메트릭 수집"""
        # 모의 애플리케이션 메트릭
        return {
            "request_count": 1000,
            "error_rate": 0.05,
            "average_response_time": 150.5,
            "active_users": 250,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def collect_database_metrics(self) -> Dict[str, Any]:
        """데이터베이스 메트릭 수집"""
        # 모의 데이터베이스 메트릭
        return {
            "connection_pool_size": 20,
            "active_connections": 15,
            "query_time_avg": 25.5,
            "query_time_max": 150.2,
            "slow_query_count": 3,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def collect_cache_metrics(self) -> Dict[str, Any]:
        """캐시 메트릭 수집"""
        # 모의 캐시 메트릭
        return {
            "hit_rate": 85.3,
            "miss_rate": 14.7,
            "eviction_count": 125,
            "memory_usage": 256.5,
            "key_count": 10000,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def update_alert_thresholds(self, thresholds: Dict[str, float]):
        """알림 임계값 업데이트"""
        self.alert_thresholds.update(thresholds)
    
    def enable_metrics_history(self, max_history_size: int = 100):
        """메트릭 기록 활성화"""
        self.max_history_size = max_history_size
    
    def collect_and_store_metrics(self):
        """메트릭 수집 및 저장"""
        metrics = self.collect_performance_metrics()
        self.metrics_history.append(metrics)
        
        # 최대 기록 크기 유지
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """메트릭 기록 조회"""
        return self.metrics_history
    
    def aggregate_metrics(
        self,
        start_time: float,
        end_time: float,
        interval: str = "5m"
    ) -> List[Dict[str, Any]]:
        """메트릭 집계"""
        # 필터링된 메트릭
        filtered = [
            m for m in self.metrics_history
            if start_time <= datetime.fromisoformat(m["timestamp"]).timestamp() <= end_time
        ]
        
        if not filtered:
            return []
        
        # 집계 계산
        cpu_values = [m["cpu_usage"] for m in filtered]
        memory_values = [m["memory_usage"] for m in filtered]
        
        return [{
            "timestamp": datetime.fromtimestamp(start_time).isoformat(),
            "interval": interval,
            "cpu_usage_avg": sum(cpu_values) / len(cpu_values),
            "cpu_usage_min": min(cpu_values),
            "cpu_usage_max": max(cpu_values),
            "memory_usage_avg": sum(memory_values) / len(memory_values),
            "memory_usage_min": min(memory_values),
            "memory_usage_max": max(memory_values)
        }]
    
    def add_recovery_handler(self, alert_type: str, handler: Callable):
        """복구 핸들러 추가"""
        self.recovery_actions[alert_type] = handler
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 조회"""
        return {
            "system_health": self.check_system_health(),
            "performance_metrics": self.collect_performance_metrics(),
            "application_metrics": self.collect_application_metrics(),
            "database_metrics": self.collect_database_metrics(),
            "cache_metrics": self.collect_cache_metrics(),
            "recent_alerts": [asdict(alert) for alert in self.alert_history[-5:]],
            "metrics_history": self.metrics_history[-10:]
        }
    
    def create_alert(self, alert_data: Dict[str, Any]):
        """알림 생성 (별칭)"""
        # 실제 구현에서는 비동기 메서드를 사용해야 함
        alert_id = f"manual_{int(time.time())}"
        asyncio.create_task(
            self._create_alert(
                alert_id=alert_id,
                severity=AlertSeverity.WARNING,
                message=alert_data.get("message", "Manual alert"),
                source=alert_data.get("source", "manual"),
                data=alert_data
            )
        )

# 전역 운영 모니터 인스턴스
operational_monitor = OperationalMonitor()