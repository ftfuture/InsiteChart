"""
성능 모니터링 시스템 모듈
API 응답 시간 추적, 시스템 리소스 모니터링, 성능 메트릭 수집 기능 제공
"""

import asyncio
import time
import psutil
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """성능 메트릭 모델"""
    timestamp: datetime
    metric_type: str  # response_time, cpu, memory, disk, network
    value: float
    unit: str
    tags: Dict[str, str]
    source: str

@dataclass
class RequestMetric:
    """요청 메트릭 모델"""
    request_id: str
    method: str
    endpoint: str
    status_code: int
    response_time: float
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    error: Optional[str] = None

@dataclass
class SystemMetric:
    """시스템 메트릭 모델"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int
    memory_used: int
    disk_percent: float
    disk_free: int
    disk_used: int
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: Optional[List[float]] = None

@dataclass
class AlertThreshold:
    """알림 임계값 모델"""
    metric_type: str
    threshold: float
    operator: str  # gt, lt, eq
    severity: str  # info, warning, error, critical
    cooldown_minutes: int = 5
    enabled: bool = True

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        monitoring_interval: int = 60,
        metrics_retention_hours: int = 24,
        max_metrics_per_type: int = 1000
    ):
        self.redis_url = redis_url
        self.monitoring_interval = monitoring_interval
        self.metrics_retention_hours = metrics_retention_hours
        self.max_metrics_per_type = max_metrics_per_type
        
        # Redis 클라이언트
        self.redis_client = None
        
        # 메트릭 저장
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_per_type))
        self.request_metrics: deque = deque(maxlen=10000)
        
        # 알림 설정
        self.alert_thresholds = self._default_alert_thresholds()
        self.active_alerts: Dict[str, datetime] = {}
        
        # 상태 관리
        self.running = False
        self.start_time = datetime.utcnow()
        
        # 통계 정보
        self.stats = {
            "total_requests": 0,
            "total_errors": 0,
            "avg_response_time": 0.0,
            "p95_response_time": 0.0,
            "p99_response_time": 0.0,
            "requests_per_second": 0.0,
            "error_rate": 0.0
        }
        
        # 콜백 함수
        self.metric_callbacks: List[Callable] = []
    
    async def initialize(self):
        """성능 모니터링 초기화"""
        try:
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # 기존 메트릭 로드
            await self._load_metrics_history()
            
            logger.info("Performance Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Performance Monitor: {str(e)}")
            raise
    
    async def start(self):
        """성능 모니터링 시작"""
        if not self.redis_client:
            await self.initialize()
        
        self.running = True
        
        # 시스템 메트릭 수집기 시작
        asyncio.create_task(self._system_metrics_collector())
        
        # 통계 계산기 시작
        asyncio.create_task(self._statistics_calculator())
        
        # 알림 처리기 시작
        asyncio.create_task(self._alert_processor())
        
        logger.info("Performance Monitor started")
    
    async def stop(self):
        """성능 모니터링 중지"""
        self.running = False
        
        # 메트릭 저장
        await self._save_metrics_history()
        
        logger.info("Performance Monitor stopped")
    
    def add_metric_callback(self, callback: Callable):
        """
        메트릭 콜백 함수 추가
        
        Args:
            callback: 콜백 함수
        """
        self.metric_callbacks.append(callback)
        logger.info(f"Added metric callback: {callback.__name__}")
    
    async def record_request(
        self,
        request_id: str,
        method: str,
        endpoint: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        요청 메트릭 기록
        
        Args:
            request_id: 요청 ID
            method: HTTP 메서드
            endpoint: 엔드포인트
            status_code: 상태 코드
            response_time: 응답 시간 (초)
            user_id: 사용자 ID
            ip_address: IP 주소
            user_agent: 사용자 에이전트
            error: 에러 정보
        """
        try:
            metric = RequestMetric(
                request_id=request_id,
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                error=error
            )
            
            # 메트릭 저장
            self.request_metrics.append(metric)
            
            # 통계 업데이트
            self._update_request_stats(metric)
            
            # 콜백 호출
            await self._trigger_metric_callbacks(metric)
            
            # 알림 확인
            await self._check_request_alerts(metric)
            
        except Exception as e:
            logger.error(f"Error recording request metric: {str(e)}")
    
    async def record_custom_metric(
        self,
        metric_type: str,
        value: float,
        unit: str,
        tags: Optional[Dict[str, str]] = None,
        source: str = "application"
    ):
        """
        사용자 정의 메트릭 기록
        
        Args:
            metric_type: 메트릭 타입
            value: 메트릭 값
            unit: 단위
            tags: 태그
            source: 소스
        """
        try:
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                metric_type=metric_type,
                value=value,
                unit=unit,
                tags=tags or {},
                source=source
            )
            
            # 메트릭 저장
            self.metrics_history[metric_type].append(metric)
            
            # 콜백 호출
            await self._trigger_metric_callbacks(metric)
            
            # 알림 확인
            await self._check_metric_alerts(metric)
            
        except Exception as e:
            logger.error(f"Error recording custom metric: {str(e)}")
    
    async def get_performance_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        성능 요약 정보 조회
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            성능 요약 정보
        """
        try:
            # 기본 시간 범위 설정
            if not end_time:
                end_time = datetime.utcnow()
            if not start_time:
                start_time = end_time - timedelta(hours=1)
            
            # 요청 메트릭 필터링
            filtered_requests = [
                req for req in self.request_metrics
                if start_time <= req.timestamp <= end_time
            ]
            
            if not filtered_requests:
                return {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "total_requests": 0,
                    "error_rate": 0.0,
                    "avg_response_time": 0.0,
                    "p95_response_time": 0.0,
                    "p99_response_time": 0.0,
                    "requests_per_second": 0.0
                }
            
            # 통계 계산
            total_requests = len(filtered_requests)
            error_count = len([req for req in filtered_requests if req.status_code >= 400])
            response_times = [req.response_time for req in filtered_requests]
            
            # 정렬된 응답 시간
            sorted_times = sorted(response_times)
            
            # 백분위수 계산
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
            p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
            
            # 시간 범위 (초)
            time_range = (end_time - start_time).total_seconds()
            
            return {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_requests": total_requests,
                "error_count": error_count,
                "error_rate": (error_count / total_requests * 100) if total_requests > 0 else 0.0,
                "avg_response_time": sum(response_times) / len(response_times) if response_times else 0.0,
                "p95_response_time": p95_response_time,
                "p99_response_time": p99_response_time,
                "requests_per_second": total_requests / time_range if time_range > 0 else 0.0,
                "status_distribution": self._calculate_status_distribution(filtered_requests),
                "endpoint_distribution": self._calculate_endpoint_distribution(filtered_requests)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {"error": str(e)}
    
    async def get_system_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        시스템 메트릭 조회
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            시스템 메트릭 목록
        """
        try:
            # 기본 시간 범위 설정
            if not end_time:
                end_time = datetime.utcnow()
            if not start_time:
                start_time = end_time - timedelta(hours=1)
            
            # 시스템 메트릭 필터링
            system_metrics = self.metrics_history.get("system", [])
            
            filtered_metrics = [
                asdict(metric) for metric in system_metrics
                if start_time <= metric.timestamp <= end_time
            ]
            
            return filtered_metrics
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return []
    
    async def get_alerts(
        self,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        알림 목록 조회
        
        Args:
            severity: 심각도
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            알림 목록
        """
        try:
            # Redis에서 알림 조회
            if not self.redis_client:
                return []
            
            alert_key = "performance:alerts"
            alerts_data = await self.redis_client.lrange(alert_key, 0, -1)
            
            alerts = []
            for alert_data in alerts_data:
                try:
                    alert = json.loads(alert_data)
                    
                    # 필터링
                    if severity and alert.get("severity") != severity:
                        continue
                    if start_time and datetime.fromisoformat(alert.get("timestamp")) < start_time:
                        continue
                    if end_time and datetime.fromisoformat(alert.get("timestamp")) > end_time:
                        continue
                    
                    alerts.append(alert)
                    
                except Exception as e:
                    logger.error(f"Error parsing alert data: {str(e)}")
            
            # 시간 역순으로 정렬
            alerts.sort(key=lambda x: x.get("timestamp"), reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            return []
    
    def _default_alert_thresholds(self) -> Dict[str, AlertThreshold]:
        """기본 알림 임계값 설정"""
        return {
            "response_time_high": AlertThreshold(
                metric_type="response_time",
                threshold=1.0,  # 1초
                operator="gt",
                severity="warning"
            ),
            "response_time_critical": AlertThreshold(
                metric_type="response_time",
                threshold=2.0,  # 2초
                operator="gt",
                severity="critical"
            ),
            "error_rate_high": AlertThreshold(
                metric_type="error_rate",
                threshold=5.0,  # 5%
                operator="gt",
                severity="warning"
            ),
            "cpu_usage_high": AlertThreshold(
                metric_type="cpu_percent",
                threshold=80.0,  # 80%
                operator="gt",
                severity="warning"
            ),
            "memory_usage_high": AlertThreshold(
                metric_type="memory_percent",
                threshold=85.0,  # 85%
                operator="gt",
                severity="warning"
            ),
            "disk_usage_high": AlertThreshold(
                metric_type="disk_percent",
                threshold=90.0,  # 90%
                operator="gt",
                severity="critical"
            )
        }
    
    def _update_request_stats(self, metric: RequestMetric):
        """요청 통계 업데이트"""
        self.stats["total_requests"] += 1
        
        if metric.status_code >= 400:
            self.stats["total_errors"] += 1
        
        # 응답 시간 업데이트
        if self.stats["total_requests"] == 1:
            self.stats["avg_response_time"] = metric.response_time
        else:
            self.stats["avg_response_time"] = (
                (self.stats["avg_response_time"] * (self.stats["total_requests"] - 1) + metric.response_time) /
                self.stats["total_requests"]
            )
        
        # 에러율 계산
        self.stats["error_rate"] = (
            self.stats["total_errors"] / self.stats["total_requests"] * 100
        )
        
        # RPS 계산 (최근 1분)
        recent_requests = [
            req for req in self.request_metrics
            if req.timestamp > datetime.utcnow() - timedelta(minutes=1)
        ]
        self.stats["requests_per_second"] = len(recent_requests) / 60.0
    
    async def _system_metrics_collector(self):
        """시스템 메트릭 수집기"""
        while self.running:
            try:
                # 시스템 메트릭 수집
                metric = await self._collect_system_metrics()
                
                # 메트릭 저장
                self.metrics_history["system"].append(metric)
                
                # 콜백 호출
                await self._trigger_metric_callbacks(metric)
                
                # 알림 확인
                await self._check_system_alerts(metric)
                
                # 모니터링 간격만큼 대기
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in system metrics collector: {str(e)}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _statistics_calculator(self):
        """통계 계산기"""
        while self.running:
            try:
                # 요청 메트릭에서 통계 계산
                if self.request_metrics:
                    response_times = [req.response_time for req in self.request_metrics]
                    
                    # 백분위수 계산
                    sorted_times = sorted(response_times)
                    p95_index = int(len(sorted_times) * 0.95)
                    p99_index = int(len(sorted_times) * 0.99)
                    
                    self.stats["p95_response_time"] = sorted_times[min(p95_index, len(sorted_times) - 1)]
                    self.stats["p99_response_time"] = sorted_times[min(p99_index, len(sorted_times) - 1)]
                
                # 1분마다 계산
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in statistics calculator: {str(e)}")
                await asyncio.sleep(60)
    
    async def _alert_processor(self):
        """알림 처리기"""
        while self.running:
            try:
                # 활성 알림 확인 및 쿨다운 해제
                current_time = datetime.utcnow()
                expired_alerts = []
                
                for alert_id, alert_time in self.active_alerts.items():
                    cooldown_minutes = 5  # 기본 쿨다운 5분
                    
                    # 해당 알림 타입의 임계값 확인
                    for threshold in self.alert_thresholds.values():
                        if alert_id.startswith(threshold.metric_type):
                            cooldown_minutes = threshold.cooldown_minutes
                            break
                    
                    if (current_time - alert_time).total_seconds() > cooldown_minutes * 60:
                        expired_alerts.append(alert_id)
                
                # 만료된 알림 제거
                for alert_id in expired_alerts:
                    del self.active_alerts[alert_id]
                
                # 1분마다 확인
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in alert processor: {str(e)}")
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self) -> SystemMetric:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용량
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 정보
            memory = psutil.virtual_memory()
            
            # 디스크 정보
            disk = psutil.disk_usage('/')
            
            # 네트워크 I/O
            network = psutil.net_io_counters()
            
            # 시스템 로드 평균 (Linux/Unix)
            load_average = None
            try:
                load_average = list(psutil.getloadavg())
            except (AttributeError, OSError):
                pass
            
            return SystemMetric(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available=memory.available,
                memory_used=memory.used,
                disk_percent=(disk.used / disk.total) * 100,
                disk_free=disk.free,
                disk_used=disk.used,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                load_average=load_average
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            # 기본 메트릭 반환
            return SystemMetric(
                timestamp=datetime.utcnow(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available=0,
                memory_used=0,
                disk_percent=0.0,
                disk_free=0,
                disk_used=0,
                network_bytes_sent=0,
                network_bytes_recv=0
            )
    
    async def _trigger_metric_callbacks(self, metric):
        """메트릭 콜백 트리거"""
        for callback in self.metric_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(metric)
                else:
                    # 동기 함수는 스레드 풀에서 실행
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, metric)
                    
            except Exception as e:
                logger.error(f"Error in metric callback: {str(e)}")
    
    async def _check_request_alerts(self, metric: RequestMetric):
        """요청 알림 확인"""
        # 응답 시간 알림
        if metric.response_time > self.alert_thresholds["response_time_critical"].threshold:
            await self._create_alert(
                "response_time_critical",
                f"Critical response time: {metric.response_time:.3f}s",
                {
                    "request_id": metric.request_id,
                    "endpoint": metric.endpoint,
                    "response_time": metric.response_time
                }
            )
        elif metric.response_time > self.alert_thresholds["response_time_high"].threshold:
            await self._create_alert(
                "response_time_high",
                f"High response time: {metric.response_time:.3f}s",
                {
                    "request_id": metric.request_id,
                    "endpoint": metric.endpoint,
                    "response_time": metric.response_time
                }
            )
        
        # 에러율 알림
        if self.stats["error_rate"] > self.alert_thresholds["error_rate_high"].threshold:
            await self._create_alert(
                "error_rate_high",
                f"High error rate: {self.stats['error_rate']:.2f}%",
                {
                    "error_rate": self.stats["error_rate"],
                    "total_errors": self.stats["total_errors"],
                    "total_requests": self.stats["total_requests"]
                }
            )
    
    async def _check_metric_alerts(self, metric: PerformanceMetric):
        """메트릭 알림 확인"""
        # 해당 메트릭 타입의 임계값 확인
        for threshold_name, threshold in self.alert_thresholds.items():
            if threshold.metric_type == metric.metric_type and threshold.enabled:
                # 알림 ID 생성
                alert_id = f"{threshold.metric_type}_{threshold_name}"
                
                # 쿨다운 확인
                if alert_id in self.active_alerts:
                    continue
                
                # 임계값 비교
                triggered = False
                if threshold.operator == "gt" and metric.value > threshold.threshold:
                    triggered = True
                elif threshold.operator == "lt" and metric.value < threshold.threshold:
                    triggered = True
                elif threshold.operator == "eq" and metric.value == threshold.threshold:
                    triggered = True
                
                if triggered:
                    await self._create_alert(
                        alert_id,
                        f"{threshold.metric_type} threshold exceeded: {metric.value}{metric.unit}",
                        {
                            "metric_type": metric.metric_type,
                            "value": metric.value,
                            "unit": metric.unit,
                            "threshold": threshold.threshold,
                            "tags": metric.tags
                        }
                    )
    
    async def _check_system_alerts(self, metric: SystemMetric):
        """시스템 알림 확인"""
        # CPU 알림
        await self._check_metric_alerts(PerformanceMetric(
            timestamp=metric.timestamp,
            metric_type="cpu_percent",
            value=metric.cpu_percent,
            unit="%",
            tags={},
            source="system"
        ))
        
        # 메모리 알림
        await self._check_metric_alerts(PerformanceMetric(
            timestamp=metric.timestamp,
            metric_type="memory_percent",
            value=metric.memory_percent,
            unit="%",
            tags={},
            source="system"
        ))
        
        # 디스크 알림
        await self._check_metric_alerts(PerformanceMetric(
            timestamp=metric.timestamp,
            metric_type="disk_percent",
            value=metric.disk_percent,
            unit="%",
            tags={},
            source="system"
        ))
    
    async def _create_alert(self, alert_id: str, message: str, data: Dict[str, Any]):
        """알림 생성"""
        try:
            # 알림 데이터 생성
            alert_data = {
                "alert_id": alert_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "warning",
                "data": data
            }
            
            # 심각도 결정
            for threshold in self.alert_thresholds.values():
                if alert_id.startswith(threshold.metric_type):
                    alert_data["severity"] = threshold.severity
                    break
            
            # 활성 알림에 추가
            self.active_alerts[alert_id] = datetime.utcnow()
            
            # Redis에 저장
            if self.redis_client:
                alert_key = "performance:alerts"
                await self.redis_client.lpush(alert_key, json.dumps(alert_data))
                
                # 최근 1000개만 유지
                await self.redis_client.ltrim(alert_key, 0, 999)
                
                # 만료 시간 설정 (7일)
                await self.redis_client.expire(alert_key, 604800)
            
            # 로그 기록
            logger.warning(f"Performance alert: {message}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
    
    def _calculate_status_distribution(self, requests: List[RequestMetric]) -> Dict[str, int]:
        """상태 코드 분포 계산"""
        distribution = defaultdict(int)
        
        for request in requests:
            status_category = self._categorize_status(request.status_code)
            distribution[status_category] += 1
        
        return dict(distribution)
    
    def _calculate_endpoint_distribution(self, requests: List[RequestMetric]) -> Dict[str, int]:
        """엔드포인트 분포 계산"""
        distribution = defaultdict(int)
        
        for request in requests:
            endpoint = request.endpoint
            distribution[endpoint] += 1
        
        return dict(distribution)
    
    def _categorize_status(self, status_code: int) -> str:
        """상태 코드 분류"""
        if 200 <= status_code < 300:
            return "2xx_success"
        elif 300 <= status_code < 400:
            return "3xx_redirect"
        elif 400 <= status_code < 500:
            return "4xx_client_error"
        elif 500 <= status_code < 600:
            return "5xx_server_error"
        else:
            return "unknown"
    
    async def _save_metrics_history(self):
        """메트릭 기록 저장"""
        try:
            if not self.redis_client:
                return
            
            # 각 메트릭 타입별로 저장
            for metric_type, metrics in self.metrics_history.items():
                key = f"performance:metrics:{metric_type}"
                
                # 메트릭 데이터 직렬화 및 저장
                for metric in metrics:
                    await self.redis_client.lpush(key, json.dumps(asdict(metric)))
                
                # 최근 메트릭만 유지
                await self.redis_client.ltrim(key, 0, self.max_metrics_per_type - 1)
                
                # 만료 시간 설정
                await self.redis_client.expire(key, self.metrics_retention_hours * 3600)
            
            # 요청 메트릭 저장
            request_key = "performance:requests"
            for request in self.request_metrics:
                await self.redis_client.lpush(request_key, json.dumps(asdict(request)))
            
            await self.redis_client.ltrim(request_key, 0, 9999)
            await self.redis_client.expire(request_key, self.metrics_retention_hours * 3600)
            
        except Exception as e:
            logger.error(f"Error saving metrics history: {str(e)}")
    
    async def _load_metrics_history(self):
        """메트릭 기록 로드"""
        try:
            if not self.redis_client:
                return
            
            # 시스템 메트릭 로드
            system_key = "performance:metrics:system"
            system_metrics_data = await self.redis_client.lrange(system_key, 0, -1)
            
            for data in system_metrics_data:
                try:
                    metric_dict = json.loads(data)
                    metric = SystemMetric(**metric_dict)
                    
                    # 타임스탬프 파싱
                    if isinstance(metric.timestamp, str):
                        metric.timestamp = datetime.fromisoformat(metric.timestamp)
                    
                    self.metrics_history["system"].append(metric)
                    
                except Exception as e:
                    logger.error(f"Error parsing system metric data: {str(e)}")
            
            logger.info(f"Loaded {len(system_metrics_data)} system metrics from history")
            
        except Exception as e:
            logger.error(f"Error loading metrics history: {str(e)}")

# 전역 성능 모니터 인스턴스
performance_monitor = PerformanceMonitor()