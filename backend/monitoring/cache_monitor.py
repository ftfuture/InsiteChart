"""
캐시 성능 모니터링 모듈
캐시 적중률, 메모리 사용량, 성능 메트릭 수집 및 알림 기능 제공
"""

import asyncio
import time
import psutil
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import redis.asyncio as redis
import json

from .intelligent_cache_manager import intelligent_cache_manager
from .distributed_cache import distributed_cache_manager

logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """캐시 메트릭 모델"""
    timestamp: datetime
    cache_type: str  # local, distributed, intelligent
    hit_rate: float
    miss_rate: float
    avg_response_time: float
    memory_usage: int
    key_count: int
    eviction_count: int
    connection_count: int
    error_rate: float

@dataclass
class PerformanceAlert:
    """성능 알림 모델"""
    alert_id: str
    alert_type: str  # hit_rate_low, memory_high, response_time_high, error_rate_high
    severity: str    # info, warning, error, critical
    message: str
    cache_type: str
    current_value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class MonitoringConfig:
    """모니터링 설정 모델"""
    hit_rate_threshold: float = 70.0      # 적중률 임계값 (%)
    memory_usage_threshold: float = 80.0   # 메모리 사용량 임계값 (%)
    response_time_threshold: float = 100.0  # 응답 시간 임계값 (ms)
    error_rate_threshold: float = 5.0      # 에러율 임계값 (%)
    monitoring_interval: int = 60           # 모니터링 간격 (초)
    metrics_retention_days: int = 7         # 메트릭 보관 기간 (일)
    alert_cooldown_minutes: int = 30        # 알림 쿨다운 (분)
    enable_auto_tuning: bool = True         # 자동 튜닝 활성화

class CachePerformanceMonitor:
    """캐시 성능 모니터링 클래스"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: Optional[MonitoringConfig] = None
    ):
        self.redis_url = redis_url
        self.config = config or MonitoringConfig()
        
        # Redis 클라이언트
        self.redis_client = None
        
        # 메트릭 수집
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10080))  # 7일 * 24시간 * 60분
        self.current_metrics: Dict[str, CacheMetrics] = {}
        
        # 알림 관리
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.last_alert_times: Dict[str, datetime] = {}
        
        # 상태 관리
        self.running = False
        self.lock = asyncio.Lock()
        
        # 자동 튜닝 파라미터
        self.tuning_params = {
            "min_hit_rate": 60.0,           # 최소 적중률
            "max_memory_usage": 85.0,        # 최대 메모리 사용량
            "max_response_time": 200.0,       # 최대 응답 시간
            "tuning_interval": 300,          # 튜닝 간격 (초)
            "adjustment_factor": 0.1           # 조정 계수
        }
    
    async def initialize(self):
        """캐시 성능 모니터링 초기화"""
        try:
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # 기존 메트릭 로드
            await self._load_metrics_history()
            
            # 기존 알림 로드
            await self._load_alert_history()
            
            logger.info("Cache Performance Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cache Performance Monitor: {str(e)}")
            raise
    
    async def start(self):
        """캐시 성능 모니터링 시작"""
        if not self.redis_client:
            await self.initialize()
        
        self.running = True
        
        # 메트릭 수집기 시작
        asyncio.create_task(self._metrics_collector())
        
        # 알림 처리기 시작
        asyncio.create_task(self._alert_processor())
        
        # 자동 튜너 시작
        if self.config.enable_auto_tuning:
            asyncio.create_task(self._auto_tuner())
        
        logger.info("Cache Performance Monitor started")
    
    async def stop(self):
        """캐시 성능 모니터링 중지"""
        self.running = False
        
        # 메트릭 저장
        await self._save_metrics_history()
        
        # 알림 저장
        await self._save_alert_history()
        
        logger.info("Cache Performance Monitor stopped")
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """
        현재 메트릭 정보 조회
        
        Returns:
            현재 메트릭 딕셔너리
        """
        try:
            # 모든 캐시 타입에 대한 메트릭 수집
            metrics = {}
            
            # 로컬 캐시 메트릭
            local_metrics = await self._collect_local_cache_metrics()
            if local_metrics:
                metrics["local"] = asdict(local_metrics)
            
            # 분산 캐시 메트릭
            distributed_metrics = await self._collect_distributed_cache_metrics()
            if distributed_metrics:
                metrics["distributed"] = asdict(distributed_metrics)
            
            # 지능형 캐시 메트릭
            intelligent_metrics = await self._collect_intelligent_cache_metrics()
            if intelligent_metrics:
                metrics["intelligent"] = asdict(intelligent_metrics)
            
            # 시스템 메트릭
            system_metrics = await self._collect_system_metrics()
            metrics["system"] = system_metrics
            
            # 활성 알림
            metrics["active_alerts"] = {
                alert_id: asdict(alert) for alert_id, alert in self.active_alerts.items()
            }
            
            # 요약 정보
            metrics["summary"] = await self._generate_metrics_summary(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting current metrics: {str(e)}")
            return {}
    
    async def get_historical_metrics(
        self,
        cache_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        과거 메트릭 정보 조회
        
        Args:
            cache_type: 캐시 타입
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            과거 메트릭 목록
        """
        try:
            if cache_type not in self.metrics_history:
                return []
            
            history = self.metrics_history[cache_type]
            
            # 시간 필터링
            filtered_metrics = []
            for metrics in history:
                if start_time and metrics.timestamp < start_time:
                    continue
                if end_time and metrics.timestamp > end_time:
                    continue
                
                filtered_metrics.append(asdict(metrics))
            
            return filtered_metrics
            
        except Exception as e:
            logger.error(f"Error getting historical metrics: {str(e)}")
            return []
    
    async def get_alert_history(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        알림 기록 조회
        
        Args:
            alert_type: 알림 타입
            severity: 심각도
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            알림 기록 목록
        """
        try:
            filtered_alerts = []
            
            for alert in self.alert_history:
                # 필터링 조건 확인
                if alert_type and alert.alert_type != alert_type:
                    continue
                if severity and alert.severity != severity:
                    continue
                if start_time and alert.timestamp < start_time:
                    continue
                if end_time and alert.timestamp > end_time:
                    continue
                
                filtered_alerts.append(asdict(alert))
            
            # 시간 역순으로 정렬
            filtered_alerts.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return filtered_alerts
            
        except Exception as e:
            logger.error(f"Error getting alert history: {str(e)}")
            return []
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        알림 확인
        
        Args:
            alert_id: 알림 ID
            
        Returns:
            성공 여부
        """
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                
                # 활성 알림에서 제거
                del self.active_alerts[alert_id]
                
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            return False
    
    async def update_config(self, config: MonitoringConfig) -> bool:
        """
        모니터링 설정 업데이트
        
        Args:
            config: 새 설정
            
        Returns:
            성공 여부
        """
        try:
            self.config = config
            
            # 설정 저장
            await self._save_config()
            
            logger.info("Monitoring configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating config: {str(e)}")
            return False
    
    async def _metrics_collector(self):
        """메트릭 수집기"""
        while self.running:
            try:
                async with self.lock:
                    # 모든 캐시 타입에 대한 메트릭 수집
                    await self._collect_all_cache_metrics()
                
                # 모니터링 간격만큼 대기
                await asyncio.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collector: {str(e)}")
                await asyncio.sleep(self.config.monitoring_interval)
    
    async def _collect_all_cache_metrics(self):
        """모든 캐시 타입에 대한 메트릭 수집"""
        try:
            # 로컬 캐시 메트릭
            local_metrics = await self._collect_local_cache_metrics()
            if local_metrics:
                self.current_metrics["local"] = local_metrics
                self.metrics_history["local"].append(local_metrics)
            
            # 분산 캐시 메트릭
            distributed_metrics = await self._collect_distributed_cache_metrics()
            if distributed_metrics:
                self.current_metrics["distributed"] = distributed_metrics
                self.metrics_history["distributed"].append(distributed_metrics)
            
            # 지능형 캐시 메트릭
            intelligent_metrics = await self._collect_intelligent_cache_metrics()
            if intelligent_metrics:
                self.current_metrics["intelligent"] = intelligent_metrics
                self.metrics_history["intelligent"].append(intelligent_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {str(e)}")
    
    async def _collect_local_cache_metrics(self) -> Optional[CacheMetrics]:
        """로컬 캐시 메트릭 수집"""
        try:
            if not self.redis_client:
                return None
            
            # Redis 정보 조회
            info = await self.redis_client.info()
            
            # 기본 메트릭
            total_commands = info.get("total_commands_processed", 0)
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            
            # 비율 계산
            hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0.0
            miss_rate = 100.0 - hit_rate
            
            # 메모리 정보
            memory_info = info.get("memory", {})
            memory_usage = memory_info.get("used_memory", 0)
            
            # 키 수
            db_info = info.get("db", {})
            key_count = 0
            for db in db_info.values():
                if isinstance(db, dict):
                    key_count += db.get("keys", 0)
            
            # 기타 정보
            eviction_count = info.get("keyspace_misses", 0)  # 단순화
            connection_count = info.get("connected_clients", 0)
            
            return CacheMetrics(
                timestamp=datetime.utcnow(),
                cache_type="local",
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                avg_response_time=0.0,  # Redis에서 직접 제공하지 않음
                memory_usage=memory_usage,
                key_count=key_count,
                eviction_count=eviction_count,
                connection_count=connection_count,
                error_rate=0.0  # 별도 수집 필요
            )
            
        except Exception as e:
            logger.error(f"Error collecting local cache metrics: {str(e)}")
            return None
    
    async def _collect_distributed_cache_metrics(self) -> Optional[CacheMetrics]:
        """분산 캐시 메트릭 수집"""
        try:
            # 분산 캐시 관리자 통계 조회
            if hasattr(distributed_cache_manager, 'get_cache_statistics'):
                stats = await distributed_cache_manager.get_cache_statistics()
                
                return CacheMetrics(
                    timestamp=datetime.utcnow(),
                    cache_type="distributed",
                    hit_rate=stats.get("hit_rate", 0.0),
                    miss_rate=100.0 - stats.get("hit_rate", 0.0),
                    avg_response_time=stats.get("avg_response_time", 0.0),
                    memory_usage=0,  # 분산 캐시는 개별 노드 메모리 필요
                    key_count=0,  # 분산 캐시는 전체 키 수 계산 복잡
                    eviction_count=0,
                    connection_count=stats.get("active_nodes", 0),
                    error_rate=0.0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error collecting distributed cache metrics: {str(e)}")
            return None
    
    async def _collect_intelligent_cache_metrics(self) -> Optional[CacheMetrics]:
        """지능형 캐시 메트릭 수집"""
        try:
            # 지능형 캐시 관리자 통계 조회
            if hasattr(intelligent_cache_manager, 'get_cache_statistics'):
                stats = await intelligent_cache_manager.get_cache_statistics()
                
                return CacheMetrics(
                    timestamp=datetime.utcnow(),
                    cache_type="intelligent",
                    hit_rate=stats.get("hit_rate", 0.0),
                    miss_rate=100.0 - stats.get("hit_rate", 0.0),
                    avg_response_time=stats.get("avg_response_time", 0.0),
                    memory_usage=stats.get("memory_usage", 0),
                    key_count=0,  # 지능형 캐시는 키 수 추적 복잡
                    eviction_count=0,
                    connection_count=0,
                    error_rate=0.0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error collecting intelligent cache metrics: {str(e)}")
            return None
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용량
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용량
            memory = psutil.virtual_memory()
            
            # 디스크 사용량
            disk = psutil.disk_usage('/')
            
            # 네트워크 I/O
            network = psutil.net_io_counters()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "memory_used": memory.used,
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free": disk.free,
                "disk_used": disk.used,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}
    
    async def _alert_processor(self):
        """알림 처리기"""
        while self.running:
            try:
                # 모든 메트릭에 대한 알림 확인
                for cache_type, metrics in self.current_metrics.items():
                    await self._check_alerts(cache_type, metrics)
                
                # 1분마다 확인
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in alert processor: {str(e)}")
                await asyncio.sleep(60)
    
    async def _check_alerts(self, cache_type: str, metrics: CacheMetrics):
        """알림 조건 확인"""
        try:
            # 적중률 알림
            if metrics.hit_rate < self.config.hit_rate_threshold:
                await self._create_alert(
                    alert_type="hit_rate_low",
                    severity="warning" if metrics.hit_rate > 50 else "error",
                    message=f"Cache hit rate is low: {metrics.hit_rate:.2f}%",
                    cache_type=cache_type,
                    current_value=metrics.hit_rate,
                    threshold=self.config.hit_rate_threshold
                )
            
            # 응답 시간 알림
            if metrics.avg_response_time > self.config.response_time_threshold:
                await self._create_alert(
                    alert_type="response_time_high",
                    severity="warning" if metrics.avg_response_time < self.config.response_time_threshold * 2 else "error",
                    message=f"Cache response time is high: {metrics.avg_response_time:.2f}ms",
                    cache_type=cache_type,
                    current_value=metrics.avg_response_time,
                    threshold=self.config.response_time_threshold
                )
            
            # 에러율 알림
            if metrics.error_rate > self.config.error_rate_threshold:
                await self._create_alert(
                    alert_type="error_rate_high",
                    severity="warning" if metrics.error_rate < self.config.error_rate_threshold * 2 else "error",
                    message=f"Cache error rate is high: {metrics.error_rate:.2f}%",
                    cache_type=cache_type,
                    current_value=metrics.error_rate,
                    threshold=self.config.error_rate_threshold
                )
            
        except Exception as e:
            logger.error(f"Error checking alerts for {cache_type}: {str(e)}")
    
    async def _create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        cache_type: str,
        current_value: float,
        threshold: float
    ):
        """알림 생성"""
        try:
            alert_id = f"{cache_type}_{alert_type}_{int(time.time())}"
            
            # 쿨다운 확인
            cooldown_key = f"{cache_type}_{alert_type}"
            current_time = datetime.utcnow()
            
            if (cooldown_key in self.last_alert_times and 
                (current_time - self.last_alert_times[cooldown_key]).total_seconds() < 
                self.config.alert_cooldown_minutes * 60):
                return
            
            # 알림 생성
            alert = PerformanceAlert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                cache_type=cache_type,
                current_value=current_value,
                threshold=threshold,
                timestamp=current_time
            )
            
            # 알림 저장
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            self.last_alert_times[cooldown_key] = current_time
            
            # 로그 기록
            logger.warning(f"Cache alert created: {message}")
            
            # 외부 알림 시스템 호출 (필요시 구현)
            await self._send_alert_notification(alert)
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
    
    async def _send_alert_notification(self, alert: PerformanceAlert):
        """외부 알림 시스템으로 알림 전송"""
        try:
            # 실제 구현에서는 Slack, 이메일, SMS 등으로 알림 전송
            notification_data = {
                "alert_id": alert.alert_id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "cache_type": alert.cache_type,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat()
            }
            
            # 알림 전송 로직 (예: 웹훅, 메시지 큐 등)
            logger.info(f"Alert notification sent: {notification_data}")
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {str(e)}")
    
    async def _auto_tuner(self):
        """자동 튜너"""
        while self.running:
            try:
                # 튜닝 간격만큼 대기
                await asyncio.sleep(self.tuning_params["tuning_interval"])
                
                # 모든 캐시 타입에 대한 튜닝 수행
                for cache_type, metrics in self.current_metrics.items():
                    await self._tune_cache_performance(cache_type, metrics)
                
            except Exception as e:
                logger.error(f"Error in auto tuner: {str(e)}")
    
    async def _tune_cache_performance(self, cache_type: str, metrics: CacheMetrics):
        """캐시 성능 튜닝"""
        try:
            adjustments = []
            
            # 적중률 튜닝
            if metrics.hit_rate < self.tuning_params["min_hit_rate"]:
                adjustments.append(f"Increase cache size for {cache_type}")
            
            # 응답 시간 튜닝
            if metrics.avg_response_time > self.tuning_params["max_response_time"]:
                adjustments.append(f"Optimize cache operations for {cache_type}")
            
            # 튜닝 적용
            for adjustment in adjustments:
                logger.info(f"Auto-tuning recommendation: {adjustment}")
                # 실제 튜닝 로직은 캐시 타입에 따라 다름
                
        except Exception as e:
            logger.error(f"Error tuning cache performance for {cache_type}: {str(e)}")
    
    async def _generate_metrics_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """메트릭 요약 생성"""
        try:
            summary = {
                "overall_health": "good",
                "total_alerts": len(self.active_alerts),
                "critical_alerts": len([
                    alert for alert in self.active_alerts.values()
                    if alert.severity == "critical"
                ]),
                "warning_alerts": len([
                    alert for alert in self.active_alerts.values()
                    if alert.severity == "warning"
                ]),
                "cache_types": list(metrics.keys()),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # 전체 상태 평가
            if summary["critical_alerts"] > 0:
                summary["overall_health"] = "critical"
            elif summary["warning_alerts"] > 0:
                summary["overall_health"] = "warning"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating metrics summary: {str(e)}")
            return {"overall_health": "unknown", "error": str(e)}
    
    async def _save_metrics_history(self):
        """메트릭 기록 저장"""
        try:
            if not self.redis_client:
                return
            
            # Redis에 메트릭 저장
            for cache_type, history in self.metrics_history.items():
                key = f"cache:metrics:{cache_type}"
                
                # 최근 메트릭만 저장
                recent_metrics = list(history)[-100:]  # 최근 100개만
                
                for metrics in recent_metrics:
                    await self.redis_client.lpush(
                        key,
                        json.dumps(asdict(metrics))
                    )
                
                # 오래된 데이터 제거
                await self.redis_client.ltrim(key, 0, 999)
                
                # 만료 시간 설정
                await self.redis_client.expire(key, self.config.metrics_retention_days * 86400)
            
        except Exception as e:
            logger.error(f"Error saving metrics history: {str(e)}")
    
    async def _load_metrics_history(self):
        """메트릭 기록 로드"""
        try:
            if not self.redis_client:
                return
            
            # Redis에서 메트릭 로드
            cache_types = ["local", "distributed", "intelligent"]
            
            for cache_type in cache_types:
                key = f"cache:metrics:{cache_type}"
                metrics_data = await self.redis_client.lrange(key, 0, -1)
                
                for data in metrics_data:
                    try:
                        metrics_dict = json.loads(data)
                        metrics = CacheMetrics(**metrics_dict)
                        
                        # 타임스탬프 파싱
                        if isinstance(metrics.timestamp, str):
                            metrics.timestamp = datetime.fromisoformat(metrics.timestamp)
                        
                        self.metrics_history[cache_type].append(metrics)
                        
                    except Exception as e:
                        logger.error(f"Error parsing metrics data: {str(e)}")
            
            logger.info(f"Loaded metrics history for {len(cache_types)} cache types")
            
        except Exception as e:
            logger.error(f"Error loading metrics history: {str(e)}")
    
    async def _save_alert_history(self):
        """알림 기록 저장"""
        try:
            if not self.redis_client:
                return
            
            # Redis에 알림 저장
            key = "cache:alerts:history"
            
            for alert in self.alert_history:
                await self.redis_client.lpush(
                    key,
                    json.dumps(asdict(alert))
                )
            
            # 오래된 알림 제거
            await self.redis_client.ltrim(key, 0, 999)
            
            # 만료 시간 설정
            await self.redis_client.expire(key, self.config.metrics_retention_days * 86400)
            
        except Exception as e:
            logger.error(f"Error saving alert history: {str(e)}")
    
    async def _load_alert_history(self):
        """알림 기록 로드"""
        try:
            if not self.redis_client:
                return
            
            # Redis에서 알림 로드
            key = "cache:alerts:history"
            alerts_data = await self.redis_client.lrange(key, 0, -1)
            
            for data in alerts_data:
                try:
                    alert_dict = json.loads(data)
                    alert = PerformanceAlert(**alert_dict)
                    
                    # 타임스탬프 파싱
                    if isinstance(alert.timestamp, str):
                        alert.timestamp = datetime.fromisoformat(alert.timestamp)
                    
                    if alert.resolved_at and isinstance(alert.resolved_at, str):
                        alert.resolved_at = datetime.fromisoformat(alert.resolved_at)
                    
                    self.alert_history.append(alert)
                    
                    # 미해결 알림은 활성 알림에 추가
                    if not alert.resolved:
                        self.active_alerts[alert.alert_id] = alert
                        
                except Exception as e:
                    logger.error(f"Error parsing alert data: {str(e)}")
            
            logger.info(f"Loaded {len(self.alert_history)} alerts from history")
            
        except Exception as e:
            logger.error(f"Error loading alert history: {str(e)}")
    
    async def _save_config(self):
        """설정 저장"""
        try:
            if not self.redis_client:
                return
            
            config_key = "cache:monitoring:config"
            await self.redis_client.setex(
                config_key,
                86400,  # 24시간
                json.dumps(asdict(self.config))
            )
            
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")

# 전역 캐시 성능 모니터 인스턴스
cache_performance_monitor = CachePerformanceMonitor()