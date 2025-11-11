"""
실시간 모니터링 대시보드 모듈
실시간 성능 지표 표시, 알림 및 경고 시스템, 대화형 데이터 시각화 기능 제공
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import redis.asyncio as redis

from .performance_monitor import performance_monitor
from .cache_monitor import cache_performance_monitor

logger = logging.getLogger(__name__)

@dataclass
class DashboardWidget:
    """대시보드 위젯 모델"""
    widget_id: str
    widget_type: str  # chart, metric, alert, table
    title: str
    data_source: str
    config: Dict[str, Any]
    refresh_interval: int  # 초
    last_updated: Optional[datetime] = None
    data: Optional[Any] = None

@dataclass
class ChartData:
    """차트 데이터 모델"""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    chart_type: str  # line, bar, pie, gauge
    options: Optional[Dict[str, Any]] = None

@dataclass
class AlertItem:
    """알림 아이템 모델"""
    alert_id: str
    title: str
    message: str
    severity: str
    timestamp: datetime
    acknowledged: bool = False
    data: Optional[Dict[str, Any]] = None

class MonitoringDashboard:
    """모니터링 대시보드 클래스"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        refresh_interval: int = 30,
        max_alerts: int = 100
    ):
        self.redis_url = redis_url
        self.refresh_interval = refresh_interval
        self.max_alerts = max_alerts
        
        # Redis 클라이언트
        self.redis_client = None
        
        # 위젯 관리
        self.widgets: Dict[str, DashboardWidget] = {}
        self.widget_data: Dict[str, Any] = {}
        
        # 알림 관리
        self.alerts: deque = deque(maxlen=max_alerts)
        self.alert_callbacks: List[Callable] = []
        
        # 상태 관리
        self.running = False
        self.last_refresh = datetime.utcnow()
        
        # 기본 위젯 설정
        self._setup_default_widgets()
    
    async def initialize(self):
        """모니터링 대시보드 초기화"""
        try:
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # 기존 알림 로드
            await self._load_alerts()
            
            logger.info("Monitoring Dashboard initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Monitoring Dashboard: {str(e)}")
            raise
    
    async def start(self):
        """모니터링 대시보드 시작"""
        if not self.redis_client:
            await self.initialize()
        
        self.running = True
        
        # 데이터 업데이트 루프 시작
        asyncio.create_task(self._data_update_loop())
        
        # 알림 처리기 시작
        asyncio.create_task(self._alert_processor())
        
        logger.info("Monitoring Dashboard started")
    
    async def stop(self):
        """모니터링 대시보드 중지"""
        self.running = False
        
        # 알림 저장
        await self._save_alerts()
        
        logger.info("Monitoring Dashboard stopped")
    
    def add_widget(self, widget: DashboardWidget) -> bool:
        """
        위젯 추가
        
        Args:
            widget: 대시보드 위젯
            
        Returns:
            성공 여부
        """
        try:
            self.widgets[widget.widget_id] = widget
            logger.info(f"Added widget: {widget.widget_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add widget {widget.widget_id}: {str(e)}")
            return False
    
    def remove_widget(self, widget_id: str) -> bool:
        """
        위젯 제거
        
        Args:
            widget_id: 위젯 ID
            
        Returns:
            성공 여부
        """
        try:
            if widget_id in self.widgets:
                del self.widgets[widget_id]
                if widget_id in self.widget_data:
                    del self.widget_data[widget_id]
                
                logger.info(f"Removed widget: {widget_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove widget {widget_id}: {str(e)}")
            return False
    
    def add_alert_callback(self, callback: Callable):
        """
        알림 콜백 함수 추가
        
        Args:
            callback: 콜백 함수
        """
        self.alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """
        대시보드 데이터 조회
        
        Returns:
            대시보드 데이터
        """
        try:
            # 기본 정보
            dashboard_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "refresh_interval": self.refresh_interval,
                "widgets": {},
                "alerts": [],
                "summary": await self._generate_summary()
            }
            
            # 위젯 데이터
            for widget_id, widget in self.widgets.items():
                widget_data = await self._get_widget_data(widget)
                dashboard_data["widgets"][widget_id] = {
                    "widget_id": widget.widget_id,
                    "widget_type": widget.widget_type,
                    "title": widget.title,
                    "data": widget_data,
                    "last_updated": widget.last_updated.isoformat() if widget.last_updated else None,
                    "config": widget.config
                }
            
            # 알림 데이터
            dashboard_data["alerts"] = [
                asdict(alert) for alert in self.alerts
            ]
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return {"error": str(e)}
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        알림 확인
        
        Args:
            alert_id: 알림 ID
            
        Returns:
            성공 여부
        """
        try:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"Alert acknowledged: {alert_id}")
                    
                    # 콜백 호출
                    await self._trigger_alert_callbacks(alert)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            return False
    
    async def create_custom_chart(
        self,
        chart_id: str,
        title: str,
        chart_type: str,
        data_source: str,
        time_range: str = "1h",
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        사용자 정의 차트 생성
        
        Args:
            chart_id: 차트 ID
            title: 차트 제목
            chart_type: 차트 타입
            data_source: 데이터 소스
            time_range: 시간 범위
            config: 추가 설정
            
        Returns:
            성공 여부
        """
        try:
            widget = DashboardWidget(
                widget_id=chart_id,
                widget_type="chart",
                title=title,
                data_source=data_source,
                config={
                    "chart_type": chart_type,
                    "time_range": time_range,
                    **(config or {})
                },
                refresh_interval=60
            )
            
            return self.add_widget(widget)
            
        except Exception as e:
            logger.error(f"Failed to create custom chart {chart_id}: {str(e)}")
            return False
    
    def _setup_default_widgets(self):
        """기본 위젯 설정"""
        # 시스템 상태 요약
        self.widgets["system_summary"] = DashboardWidget(
            widget_id="system_summary",
            widget_type="metric",
            title="시스템 상태 요약",
            data_source="system",
            config={},
            refresh_interval=30
        )
        
        # 응답 시간 차트
        self.widgets["response_time_chart"] = DashboardWidget(
            widget_id="response_time_chart",
            widget_type="chart",
            title="API 응답 시간",
            data_source="performance",
            config={
                "chart_type": "line",
                "time_range": "1h",
                "metrics": ["avg_response_time", "p95_response_time", "p99_response_time"]
            },
            refresh_interval=60
        )
        
        # 요청량 차트
        self.widgets["request_rate_chart"] = DashboardWidget(
            widget_id="request_rate_chart",
            widget_type="chart",
            title="요청량",
            data_source="performance",
            config={
                "chart_type": "bar",
                "time_range": "1h",
                "metric": "requests_per_second"
            },
            refresh_interval=60
        )
        
        # 캐시 적중률
        self.widgets["cache_hit_rate"] = DashboardWidget(
            widget_id="cache_hit_rate",
            widget_type="gauge",
            title="캐시 적중률",
            data_source="cache",
            config={
                "min": 0,
                "max": 100,
                "thresholds": [
                    {"value": 70, "color": "red"},
                    {"value": 85, "color": "yellow"},
                    {"value": 95, "color": "green"}
                ]
            },
            refresh_interval=30
        )
        
        # 에러율 차트
        self.widgets["error_rate_chart"] = DashboardWidget(
            widget_id="error_rate_chart",
            widget_type="chart",
            title="에러율",
            data_source="performance",
            config={
                "chart_type": "line",
                "time_range": "1h",
                "metric": "error_rate"
            },
            refresh_interval=60
        )
        
        # 활성 알림
        self.widgets["active_alerts"] = DashboardWidget(
            widget_id="active_alerts",
            widget_type="alert",
            title="활성 알림",
            data_source="alerts",
            config={
                "max_alerts": 10,
                "severity_filter": ["critical", "error", "warning"]
            },
            refresh_interval=30
        )
        
        # 시스템 리소스 사용량
        self.widgets["system_resources"] = DashboardWidget(
            widget_id="system_resources",
            widget_type="chart",
            title="시스템 리소스 사용량",
            data_source="system",
            config={
                "chart_type": "line",
                "time_range": "1h",
                "metrics": ["cpu_percent", "memory_percent", "disk_percent"]
            },
            refresh_interval=30
        )
    
    async def _data_update_loop(self):
        """데이터 업데이트 루프"""
        while self.running:
            try:
                # 모든 위젯 데이터 업데이트
                for widget_id, widget in self.widgets.items():
                    if widget.last_updated is None or \
                       (datetime.utcnow() - widget.last_updated).total_seconds() >= widget.refresh_interval:
                        
                        data = await self._get_widget_data(widget)
                        self.widget_data[widget_id] = data
                        widget.last_updated = datetime.utcnow()
                
                # 마지막 업데이트 시간 기록
                self.last_refresh = datetime.utcnow()
                
                # 새로고 간격만큼 대기
                await asyncio.sleep(self.refresh_interval)
                
            except Exception as e:
                logger.error(f"Error in data update loop: {str(e)}")
                await asyncio.sleep(self.refresh_interval)
    
    async def _alert_processor(self):
        """알림 처리기"""
        while self.running:
            try:
                # 새로운 알림 확인
                new_alerts = await self._get_new_alerts()
                
                for alert_data in new_alerts:
                    alert = AlertItem(
                        alert_id=alert_data.get("alert_id"),
                        title=alert_data.get("title", "알림"),
                        message=alert_data.get("message"),
                        severity=alert_data.get("severity", "info"),
                        timestamp=datetime.fromisoformat(alert_data.get("timestamp")),
                        acknowledged=False,
                        data=alert_data.get("data")
                    )
                    
                    self.alerts.append(alert)
                    
                    # 콜백 호출
                    await self._trigger_alert_callbacks(alert)
                
                # 1분마다 확인
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in alert processor: {str(e)}")
                await asyncio.sleep(60)
    
    async def _get_widget_data(self, widget: DashboardWidget) -> Any:
        """위젯 데이터 조회"""
        try:
            if widget.data_source == "system":
                return await self._get_system_widget_data(widget)
            elif widget.data_source == "performance":
                return await self._get_performance_widget_data(widget)
            elif widget.data_source == "cache":
                return await self._get_cache_widget_data(widget)
            elif widget.data_source == "alerts":
                return await self._get_alerts_widget_data(widget)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting widget data for {widget.widget_id}: {str(e)}")
            return None
    
    async def _get_system_widget_data(self, widget: DashboardWidget) -> Any:
        """시스템 위젯 데이터 조회"""
        try:
            if widget.widget_type == "metric":
                # 시스템 상태 요약
                system_metrics = await performance_monitor.get_system_metrics()
                
                if system_metrics:
                    latest_metric = system_metrics[-1] if system_metrics else {}
                    
                    return {
                        "cpu_percent": latest_metric.get("cpu_percent", 0),
                        "memory_percent": latest_metric.get("memory_percent", 0),
                        "disk_percent": latest_metric.get("disk_percent", 0),
                        "uptime": (datetime.utcnow() - performance_monitor.start_time).total_seconds()
                    }
                
            elif widget.widget_type == "chart":
                # 시스템 리소스 차트
                config = widget.config
                time_range = config.get("time_range", "1h")
                metrics = config.get("metrics", ["cpu_percent"])
                
                # 시간 범위 계산
                end_time = datetime.utcnow()
                if time_range == "1h":
                    start_time = end_time - timedelta(hours=1)
                elif time_range == "24h":
                    start_time = end_time - timedelta(hours=24)
                else:
                    start_time = end_time - timedelta(hours=1)
                
                system_metrics = await performance_monitor.get_system_metrics(start_time, end_time)
                
                # 차트 데이터 변환
                labels = [m["timestamp"] for m in system_metrics]
                datasets = []
                
                for metric in metrics:
                    data = [m.get(metric, 0) for m in system_metrics]
                    datasets.append({
                        "label": metric.replace("_percent", " %"),
                        "data": data,
                        "borderColor": self._get_metric_color(metric),
                        "backgroundColor": self._get_metric_color(metric, 0.2)
                    })
                
                return ChartData(
                    labels=labels,
                    datasets=datasets,
                    chart_type=config.get("chart_type", "line")
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting system widget data: {str(e)}")
            return None
    
    async def _get_performance_widget_data(self, widget: DashboardWidget) -> Any:
        """성능 위젯 데이터 조회"""
        try:
            config = widget.config
            time_range = config.get("time_range", "1h")
            
            # 시간 범위 계산
            end_time = datetime.utcnow()
            if time_range == "1h":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "24h":
                start_time = end_time - timedelta(hours=24)
            else:
                start_time = end_time - timedelta(hours=1)
            
            # 성능 요약 조회
            summary = await performance_monitor.get_performance_summary(start_time, end_time)
            
            if widget.widget_type == "chart":
                if widget.widget_id == "response_time_chart":
                    # 응답 시간 차트
                    metrics = config.get("metrics", ["avg_response_time"])
                    
                    # 시간별 데이터 그룹화
                    time_buckets = self._group_by_time_interval(
                        summary.get("time_series_data", []),
                        interval_minutes=5
                    )
                    
                    labels = list(time_buckets.keys())
                    datasets = []
                    
                    for metric in metrics:
                        if metric == "avg_response_time":
                            data = [bucket.get("avg_response_time", 0) for bucket in time_buckets.values()]
                        elif metric == "p95_response_time":
                            data = [bucket.get("p95_response_time", 0) for bucket in time_buckets.values()]
                        elif metric == "p99_response_time":
                            data = [bucket.get("p99_response_time", 0) for bucket in time_buckets.values()]
                        else:
                            data = [0] * len(labels)
                        
                        datasets.append({
                            "label": metric.replace("_response_time", " 응답 시간"),
                            "data": data,
                            "borderColor": self._get_metric_color(metric),
                            "backgroundColor": self._get_metric_color(metric, 0.2)
                        })
                    
                    return ChartData(
                        labels=labels,
                        datasets=datasets,
                        chart_type="line"
                    )
                
                elif widget.widget_id == "request_rate_chart":
                    # 요청량 차트
                    return ChartData(
                        labels=["요청량"],
                        datasets=[{
                            "label": "RPS",
                            "data": [summary.get("requests_per_second", 0)],
                            "backgroundColor": ["rgba(54, 162, 235, 0.8)"]
                        }],
                        chart_type="bar"
                    )
                
                elif widget.widget_id == "error_rate_chart":
                    # 에러율 차트
                    return ChartData(
                        labels=["에러율"],
                        datasets=[{
                            "label": "에러율 (%)",
                            "data": [summary.get("error_rate", 0)],
                            "backgroundColor": ["rgba(255, 99, 132, 0.8)"]
                        }],
                        chart_type="line"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting performance widget data: {str(e)}")
            return None
    
    async def _get_cache_widget_data(self, widget: DashboardWidget) -> Any:
        """캐시 위젯 데이터 조회"""
        try:
            if widget.widget_type == "gauge":
                # 캐시 적중률 게이지
                cache_stats = await cache_performance_monitor.get_current_metrics()
                
                if cache_stats:
                    hit_rate = cache_stats.get("hit_rate", 0)
                    
                    return {
                        "value": hit_rate,
                        "min": widget.config.get("min", 0),
                        "max": widget.config.get("max", 100),
                        "thresholds": widget.config.get("thresholds", []),
                        "unit": "%"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache widget data: {str(e)}")
            return None
    
    async def _get_alerts_widget_data(self, widget: DashboardWidget) -> Any:
        """알림 위젯 데이터 조회"""
        try:
            config = widget.config
            max_alerts = config.get("max_alerts", 10)
            severity_filter = config.get("severity_filter", [])
            
            # 알림 필터링
            filtered_alerts = []
            for alert in self.alerts:
                if not severity_filter or alert.severity in severity_filter:
                    filtered_alerts.append(asdict(alert))
                
                if len(filtered_alerts) >= max_alerts:
                    break
            
            return filtered_alerts[:max_alerts]
            
        except Exception as e:
            logger.error(f"Error getting alerts widget data: {str(e)}")
            return []
    
    async def _get_new_alerts(self) -> List[Dict[str, Any]]:
        """새로운 알림 조회"""
        try:
            if not self.redis_client:
                return []
            
            # Redis에서 알림 조회
            alert_key = "performance:alerts"
            alerts_data = await self.redis_client.lrange(alert_key, 0, -1)
            
            new_alerts = []
            for alert_data in alerts_data:
                try:
                    alert = json.loads(alert_data)
                    alert_timestamp = datetime.fromisoformat(alert.get("timestamp"))
                    
                    # 마지막 확인 이후의 알림만 필터링
                    if alert_timestamp > self.last_refresh:
                        new_alerts.append(alert)
                        
                except Exception as e:
                    logger.error(f"Error parsing alert data: {str(e)}")
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Error getting new alerts: {str(e)}")
            return []
    
    async def _generate_summary(self) -> Dict[str, Any]:
        """대시보드 요약 생성"""
        try:
            # 성능 요약
            performance_summary = await performance_monitor.get_performance_summary()
            
            # 캐시 요약
            cache_summary = await cache_performance_monitor.get_current_metrics()
            
            # 알림 요약
            critical_alerts = len([a for a in self.alerts if a.severity == "critical"])
            warning_alerts = len([a for a in self.alerts if a.severity == "warning"])
            
            return {
                "performance": {
                    "avg_response_time": performance_summary.get("avg_response_time", 0),
                    "error_rate": performance_summary.get("error_rate", 0),
                    "requests_per_second": performance_summary.get("requests_per_second", 0)
                },
                "cache": {
                    "hit_rate": cache_summary.get("hit_rate", 0),
                    "active_nodes": cache_summary.get("active_nodes", 0)
                },
                "alerts": {
                    "critical_count": critical_alerts,
                    "warning_count": warning_alerts,
                    "total_count": len(self.alerts)
                },
                "system_health": self._calculate_system_health(
                    performance_summary,
                    cache_summary,
                    critical_alerts,
                    warning_alerts
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {}
    
    def _calculate_system_health(
        self,
        performance_summary: Dict[str, Any],
        cache_summary: Dict[str, Any],
        critical_alerts: int,
        warning_alerts: int
    ) -> str:
        """시스템 건강 상태 계산"""
        try:
            # 기준점수
            health_score = 100
            
            # 응답 시간 점수
            avg_response_time = performance_summary.get("avg_response_time", 0)
            if avg_response_time > 2.0:  # 2초 이상
                health_score -= 30
            elif avg_response_time > 1.0:  # 1초 이상
                health_score -= 15
            elif avg_response_time > 0.5:  # 0.5초 이상
                health_score -= 5
            
            # 에러율 점수
            error_rate = performance_summary.get("error_rate", 0)
            if error_rate > 10:  # 10% 이상
                health_score -= 40
            elif error_rate > 5:  # 5% 이상
                health_score -= 20
            elif error_rate > 1:  # 1% 이상
                health_score -= 10
            
            # 캐시 적중률 점수
            hit_rate = cache_summary.get("hit_rate", 0)
            if hit_rate < 50:  # 50% 미만
                health_score -= 20
            elif hit_rate < 70:  # 70% 미만
                health_score -= 10
            elif hit_rate < 85:  # 85% 미만
                health_score -= 5
            
            # 알림 점수
            health_score -= critical_alerts * 20
            health_score -= warning_alerts * 10
            
            # 건강 상태 결정
            if health_score >= 80:
                return "excellent"
            elif health_score >= 60:
                return "good"
            elif health_score >= 40:
                return "warning"
            else:
                return "critical"
                
        except Exception as e:
            logger.error(f"Error calculating system health: {str(e)}")
            return "unknown"
    
    def _get_metric_color(self, metric: str, alpha: float = 1.0) -> str:
        """메트릭 색상 반환"""
        colors = {
            "cpu_percent": f"rgba(255, 99, 132, {alpha})",
            "memory_percent": f"rgba(54, 162, 235, {alpha})",
            "disk_percent": f"rgba(255, 206, 86, {alpha})",
            "avg_response_time": f"rgba(75, 192, 192, {alpha})",
            "p95_response_time": f"rgba(255, 159, 64, {alpha})",
            "p99_response_time": f"rgba(255, 99, 132, {alpha})",
            "error_rate": f"rgba(255, 99, 132, {alpha})"
        }
        
        return colors.get(metric, f"rgba(156, 163, 175, {alpha})")
    
    def _group_by_time_interval(
        self,
        data: List[Dict[str, Any]],
        interval_minutes: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """시간 간격별로 데이터 그룹화"""
        try:
            if not data:
                return {}
            
            time_buckets = {}
            
            for item in data:
                timestamp = item.get("timestamp")
                if not timestamp:
                    continue
                
                # 시간 간격 계산
                dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
                
                # 버킷 키 생성 (시간 간격별)
                bucket_time = dt.replace(
                    minute=(dt.minute // interval_minutes) * interval_minutes,
                    second=0,
                    microsecond=0
                )
                
                bucket_key = bucket_time.isoformat()
                
                # 버킷에 데이터 추가
                if bucket_key not in time_buckets:
                    time_buckets[bucket_key] = {
                        "count": 0,
                        "avg_response_time": 0,
                        "p95_response_time": 0,
                        "p99_response_time": 0,
                        "error_rate": 0,
                        "response_times": []
                    }
                
                bucket = time_buckets[bucket_key]
                bucket["count"] += 1
                
                # 메트릭 누적
                if "response_time" in item:
                    bucket["response_times"].append(item["response_time"])
                
                # 에러율 계산을 위한 카운트
                if item.get("status_code", 200) >= 400:
                    bucket["error_count"] = bucket.get("error_count", 0) + 1
            
            # 각 버킷의 통계 계산
            for bucket in time_buckets.values():
                if bucket["response_times"]:
                    sorted_times = sorted(bucket["response_times"])
                    bucket["avg_response_time"] = sum(bucket["response_times"]) / len(bucket["response_times"])
                    bucket["p95_response_time"] = sorted_times[int(len(sorted_times) * 0.95)]
                    bucket["p99_response_time"] = sorted_times[int(len(sorted_times) * 0.99)]
                
                # 에러율 계산
                if "error_count" in bucket:
                    bucket["error_rate"] = (bucket["error_count"] / bucket["count"]) * 100
                else:
                    bucket["error_rate"] = 0
            
            return time_buckets
            
        except Exception as e:
            logger.error(f"Error grouping data by time interval: {str(e)}")
            return {}
    
    async def _trigger_alert_callbacks(self, alert: AlertItem):
        """알림 콜백 트리거"""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    # 동기 함수는 스레드 풀에서 실행
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, alert)
                    
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
    
    async def _load_alerts(self):
        """알림 로드"""
        try:
            if not self.redis_client:
                return
            
            # Redis에서 알림 조회
            alert_key = "performance:alerts"
            alerts_data = await self.redis_client.lrange(alert_key, 0, -1)
            
            for alert_data in alerts_data:
                try:
                    alert_dict = json.loads(alert_data)
                    alert = AlertItem(
                        alert_id=alert_dict.get("alert_id"),
                        title=alert_dict.get("title", "알림"),
                        message=alert_dict.get("message"),
                        severity=alert_dict.get("severity", "info"),
                        timestamp=datetime.fromisoformat(alert_dict.get("timestamp")),
                        acknowledged=alert_dict.get("acknowledged", False),
                        data=alert_dict.get("data")
                    )
                    
                    self.alerts.append(alert)
                    
                except Exception as e:
                    logger.error(f"Error parsing alert data: {str(e)}")
            
            logger.info(f"Loaded {len(self.alerts)} alerts from storage")
            
        except Exception as e:
            logger.error(f"Error loading alerts: {str(e)}")
    
    async def _save_alerts(self):
        """알림 저장"""
        try:
            if not self.redis_client:
                return
            
            # 확인된 알림만 저장
            acknowledged_alerts = [alert for alert in self.alerts if alert.acknowledged]
            
            if acknowledged_alerts:
                alert_key = "performance:alerts:acknowledged"
                
                for alert in acknowledged_alerts:
                    alert_data = asdict(alert)
                    alert_data["timestamp"] = alert.timestamp.isoformat()
                    
                    await self.redis_client.lpush(alert_key, json.dumps(alert_data))
                
                # 최근 1000개만 유지
                await self.redis_client.ltrim(alert_key, 0, 999)
                
                # 만료 시간 설정 (30일)
                await self.redis_client.expire(alert_key, 2592000)
            
        except Exception as e:
            logger.error(f"Error saving alerts: {str(e)}")

# 전역 모니터링 대시보드 인스턴스
monitoring_dashboard = MonitoringDashboard()