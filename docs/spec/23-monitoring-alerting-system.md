# 모니터링 및 알림 시스템 설계

## 1. 개요

### 1.1 모니터링의 중요성

InsiteChart 플랫폼은 실시간 금융 데이터, 사용자 활동, 시스템 성능 등 다양한 요소를 모니터링해야 합니다. 포괄적인 모니터링 시스템은 시스템 안정성, 성능 최적화, 사전 장애 감지, 사용자 경험 개선에 필수적입니다.

### 1.2 모니터링 목표

1. **시스템 가용성**: 99.9% 이상 서비스 가용성 보장
2. **성능 모니터링**: 응답 시간, 처리량, 자원 사용률 추적
3. **사용자 경험**: 실제 사용자 경험 기반 모니터링
4. **사전 장애 감지**: 잠재적 문제 조기 발견 및 알림
5. **비즈니스 인사이트**: 사용자 행동, 비즈니스 메트릭 분석

## 2. 모니터링 아키텍처

### 2.1 다계층 모니터링 구조

```python
# monitoring/monitoring_manager.py
import asyncio
import time
import psutil
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import aiohttp
import redis.asyncio as redis

class MetricType(Enum):
    """메트릭 타입"""
    COUNTER = "counter"       # 카운터 (누적)
    GAUGE = "gauge"          # 게이지 (현재값)
    HISTOGRAM = "histogram"   # 히스토그램 (분포)
    SUMMARY = "summary"       # 요약 (통계)

class MetricUnit(Enum):
    """메트릭 단위"""
    COUNT = "count"          # 개수
    BYTES = "bytes"          # 바이트
    SECONDS = "seconds"      # 초
    MILLISECONDS = "ms"      # 밀리초
    PERCENT = "percent"      # 백분율
    REQUESTS_PER_SECOND = "rps"  # 초당 요청수

@dataclass
class MetricDefinition:
    """메트릭 정의"""
    name: str
    metric_type: MetricType
    unit: MetricUnit
    description: str
    labels: List[str] = None
    enabled: bool = True

@dataclass
class MetricValue:
    """메트릭 값"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = None
    metric_type: MetricType = MetricType.GAUGE

class MonitoringManager:
    """모니터링 관리자"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
        
        # 메트릭 정의
        self.metric_definitions = {
            # 시스템 메트릭
            'system_cpu_usage': MetricDefinition(
                name='system_cpu_usage',
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.PERCENT,
                description='System CPU usage percentage',
                labels=['host', 'core']
            ),
            'system_memory_usage': MetricDefinition(
                name='system_memory_usage',
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.PERCENT,
                description='System memory usage percentage',
                labels=['host']
            ),
            'system_disk_usage': MetricDefinition(
                name='system_disk_usage',
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.PERCENT,
                description='System disk usage percentage',
                labels=['host', 'mount_point']
            ),
            
            # 애플리케이션 메트릭
            'http_requests_total': MetricDefinition(
                name='http_requests_total',
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description='Total HTTP requests',
                labels=['method', 'endpoint', 'status_code']
            ),
            'http_request_duration': MetricDefinition(
                name='http_request_duration',
                metric_type=MetricType.HISTOGRAM,
                unit=MetricUnit.MILLISECONDS,
                description='HTTP request duration in milliseconds',
                labels=['method', 'endpoint']
            ),
            'active_connections': MetricDefinition(
                name='active_connections',
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.COUNT,
                description='Number of active connections',
                labels=['service']
            ),
            
            # 비즈니스 메트릭
            'users_active': MetricDefinition(
                name='users_active',
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.COUNT,
                description='Number of active users',
                labels=['time_window']
            ),
            'stock_searches_total': MetricDefinition(
                name='stock_searches_total',
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description='Total stock searches',
                labels=['symbol', 'source']
            ),
            'sentiment_analyses_total': MetricDefinition(
                name='sentiment_analyses_total',
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description='Total sentiment analyses',
                labels=['symbol', 'source', 'sentiment']
            ),
            
            # 데이터베이스 메트릭
            'db_connections_active': MetricDefinition(
                name='db_connections_active',
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.COUNT,
                description='Active database connections',
                labels=['database']
            ),
            'db_query_duration': MetricDefinition(
                name='db_query_duration',
                metric_type=MetricType.HISTOGRAM,
                unit=MetricUnit.MILLISECONDS,
                description='Database query duration',
                labels=['database', 'query_type']
            ),
            
            # 캐시 메트릭
            'cache_hits_total': MetricDefinition(
                name='cache_hits_total',
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description='Total cache hits',
                labels=['cache_type', 'key_prefix']
            ),
            'cache_misses_total': MetricDefinition(
                name='cache_misses_total',
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description='Total cache misses',
                labels=['cache_type', 'key_prefix']
            ),
            
            # 외부 API 메트릭
            'external_api_requests_total': MetricDefinition(
                name='external_api_requests_total',
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                description='Total external API requests',
                labels=['api_provider', 'endpoint', 'status']
            ),
            'external_api_response_time': MetricDefinition(
                name='external_api_response_time',
                metric_type=MetricType.HISTOGRAM,
                unit=MetricUnit.MILLISECONDS,
                description='External API response time',
                labels=['api_provider', 'endpoint']
            )
        }
        
        # 메트릭 수집기 등록
        self.collectors = {
            'system': SystemMetricsCollector(),
            'application': ApplicationMetricsCollector(),
            'business': BusinessMetricsCollector(),
            'database': DatabaseMetricsCollector(),
            'cache': CacheMetricsCollector(),
            'external_api': ExternalAPIMetricsCollector()
        }
        
        # 메트릭 저장소
        self.metrics_store = MetricsStore(self.redis)
        
        # 수집 작업 상태
        self.collection_tasks = {}
        self.collection_intervals = {
            'system': 30,      # 30초
            'application': 15,  # 15초
            'business': 60,      # 1분
            'database': 30,      # 30초
            'cache': 30,         # 30초
            'external_api': 60   # 1분
        }
    
    async def start_collection(self):
        """메트릭 수집 시작"""
        
        self.logger.info("Starting metrics collection")
        
        for collector_name, collector in self.collectors.items():
            interval = self.collection_intervals.get(collector_name, 60)
            
            task = asyncio.create_task(
                self._collect_metrics_loop(collector_name, collector, interval)
            )
            
            self.collection_tasks[collector_name] = task
    
    async def stop_collection(self):
        """메트릭 수집 중지"""
        
        self.logger.info("Stopping metrics collection")
        
        for task in self.collection_tasks.values():
            task.cancel()
        
        # 모든 작업 완료 대기
        await asyncio.gather(*self.collection_tasks.values(), return_exceptions=True)
        
        self.collection_tasks.clear()
    
    async def _collect_metrics_loop(self, 
                                   collector_name: str, 
                                   collector, 
                                   interval: int):
        """메트릭 수집 루프"""
        
        while True:
            try:
                # 메트릭 수집
                metrics = await collector.collect_metrics()
                
                # 메트릭 저장
                for metric in metrics:
                    await self.metrics_store.store_metric(metric)
                
                self.logger.debug(f"Collected {len(metrics)} metrics from {collector_name}")
                
            except Exception as e:
                self.logger.error(f"Error collecting metrics from {collector_name}: {str(e)}")
            
            # 다음 수집까지 대기
            await asyncio.sleep(interval)
    
    def record_metric(self, 
                     name: str, 
                     value: float, 
                     labels: Dict[str, str] = None,
                     timestamp: datetime = None):
        """메트릭 기록"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        metric = MetricValue(
            name=name,
            value=value,
            timestamp=timestamp,
            labels=labels or {}
        )
        
        asyncio.create_task(self.metrics_store.store_metric(metric))
    
    def increment_counter(self, 
                        name: str, 
                        value: float = 1.0, 
                        labels: Dict[str, str] = None):
        """카운터 증가"""
        
        self.record_metric(name, value, labels)
    
    def set_gauge(self, 
                  name: str, 
                  value: float, 
                  labels: Dict[str, str] = None):
        """게이지 설정"""
        
        self.record_metric(name, value, labels)
    
    def record_histogram(self, 
                       name: str, 
                       value: float, 
                       labels: Dict[str, str] = None):
        """히스토그램 기록"""
        
        # 실제 구현에서는 버킷에 값 분배
        self.record_metric(name, value, labels)
    
    async def get_metrics(self, 
                        name: str, 
                        start_time: datetime, 
                        end_time: datetime,
                        labels: Dict[str, str] = None) -> List[MetricValue]:
        """메트릭 조회"""
        
        return await self.metrics_store.get_metrics(name, start_time, end_time, labels)
    
    async def get_metric_summary(self, 
                               name: str, 
                               start_time: datetime, 
                               end_time: datetime,
                               aggregation: str = 'avg') -> Dict[str, Any]:
        """메트릭 요약 조회"""
        
        metrics = await self.get_metrics(name, start_time, end_time)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        if aggregation == 'avg':
            return {'value': sum(values) / len(values), 'count': len(values)}
        elif aggregation == 'min':
            return {'value': min(values), 'count': len(values)}
        elif aggregation == 'max':
            return {'value': max(values), 'count': len(values)}
        elif aggregation == 'sum':
            return {'value': sum(values), 'count': len(values)}
        else:
            return {'value': sum(values) / len(values), 'count': len(values)}

class MetricsStore:
    """메트릭 저장소"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        
        # 메트릭 보관 기간 (초)
        self.retention_periods = {
            'system': 7 * 24 * 3600,      # 7일
            'application': 30 * 24 * 3600,  # 30일
            'business': 90 * 24 * 3600,    # 90일
            'database': 30 * 24 * 3600,    # 30일
            'cache': 7 * 24 * 3600,        # 7일
            'external_api': 30 * 24 * 3600  # 30일
        }
    
    async def store_metric(self, metric: MetricValue):
        """메트릭 저장"""
        
        try:
            # 메트릭 타입 결정
            metric_type = self._determine_metric_type(metric.name)
            
            # 키 생성
            key = f"metrics:{metric_type}:{metric.name}"
            
            # 레이블 포함 키 생성
            if metric.labels:
                label_str = ','.join(f"{k}={v}" for k, v in sorted(metric.labels.items()))
                key += f":{label_str}"
            
            # Redis에 저장
            await self.redis.zadd(
                key,
                {str(metric.value): metric.timestamp.timestamp()}
            )
            
            # 만료 시간 설정
            retention = self.retention_periods.get(metric_type, 7 * 24 * 3600)
            await self.redis.expire(key, retention)
            
        except Exception as e:
            self.logger.error(f"Error storing metric {metric.name}: {str(e)}")
    
    def _determine_metric_type(self, metric_name: str) -> str:
        """메트릭 타입 결정"""
        
        if 'system_' in metric_name:
            return 'system'
        elif 'http_' in metric_name or 'active_connections' in metric_name:
            return 'application'
        elif 'users_' in metric_name or 'stock_' in metric_name or 'sentiment_' in metric_name:
            return 'business'
        elif 'db_' in metric_name:
            return 'database'
        elif 'cache_' in metric_name:
            return 'cache'
        elif 'external_api_' in metric_name:
            return 'external_api'
        
        return 'application'  # 기본값
    
    async def get_metrics(self, 
                        name: str, 
                        start_time: datetime, 
                        end_time: datetime,
                        labels: Dict[str, str] = None) -> List[MetricValue]:
        """메트릭 조회"""
        
        try:
            # 메트릭 타입 결정
            metric_type = self._determine_metric_type(name)
            
            # 키 생성
            key = f"metrics:{metric_type}:{name}"
            
            # 레이블 포함 키 생성
            if labels:
                label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
                key += f":{label_str}"
            
            # 시간 범위로 메트릭 조회
            start_timestamp = start_time.timestamp()
            end_timestamp = end_time.timestamp()
            
            results = await self.redis.zrangebyscore(
                key, 
                start_timestamp, 
                end_timestamp, 
                withscores=True
            )
            
            # MetricValue 객체로 변환
            metrics = []
            for value_str, timestamp in results:
                try:
                    value = float(value_str)
                    metric_time = datetime.fromtimestamp(timestamp)
                    
                    metric = MetricValue(
                        name=name,
                        value=value,
                        timestamp=metric_time,
                        labels=labels or {}
                    )
                    
                    metrics.append(metric)
                except (ValueError, TypeError):
                    continue
            
            return sorted(metrics, key=lambda x: x.timestamp)
            
        except Exception as e:
            self.logger.error(f"Error retrieving metrics {name}: {str(e)}")
            return []

class SystemMetricsCollector:
    """시스템 메트릭 수집기"""
    
    async def collect_metrics(self) -> List[MetricValue]:
        """시스템 메트릭 수집"""
        
        metrics = []
        hostname = psutil.os.uname().nodename
        timestamp = datetime.now()
        
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(MetricValue(
                name='system_cpu_usage',
                value=cpu_percent,
                timestamp=timestamp,
                labels={'host': hostname}
            ))
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            metrics.append(MetricValue(
                name='system_memory_usage',
                value=memory.percent,
                timestamp=timestamp,
                labels={'host': hostname}
            ))
            
            # 디스크 사용률
            disk_partitions = psutil.disk_partitions()
            for partition in disk_partitions:
                try:
                    disk_usage = psutil.disk_usage(partition.mountpoint)
                    metrics.append(MetricValue(
                        name='system_disk_usage',
                        value=(disk_usage.used / disk_usage.total) * 100,
                        timestamp=timestamp,
                        labels={
                            'host': hostname,
                            'mount_point': partition.mountpoint
                        }
                    ))
                except (PermissionError, OSError):
                    continue
            
            # 네트워크 I/O
            network_io = psutil.net_io_counters()
            metrics.append(MetricValue(
                name='system_network_bytes_sent',
                value=network_io.bytes_sent,
                timestamp=timestamp,
                labels={'host': hostname}
            ))
            metrics.append(MetricValue(
                name='system_network_bytes_recv',
                value=network_io.bytes_recv,
                timestamp=timestamp,
                labels={'host': hostname}
            ))
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error collecting system metrics: {str(e)}")
        
        return metrics

class ApplicationMetricsCollector:
    """애플리케이션 메트릭 수집기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self.request_durations = []
        self.active_connections = 0
    
    async def collect_metrics(self) -> List[MetricValue]:
        """애플리케이션 메트릭 수집"""
        
        metrics = []
        timestamp = datetime.now()
        
        # 요청 카운터
        metrics.append(MetricValue(
            name='http_requests_total',
            value=self.request_count,
            timestamp=timestamp
        ))
        
        # 활성 연결 수
        metrics.append(MetricValue(
            name='active_connections',
            value=self.active_connections,
            timestamp=timestamp,
            labels={'service': 'api_gateway'}
        ))
        
        # 요청 지연 시간 히스토그램
        if self.request_durations:
            avg_duration = sum(self.request_durations) / len(self.request_durations)
            metrics.append(MetricValue(
                name='http_request_duration',
                value=avg_duration,
                timestamp=timestamp,
                labels={'method': 'ALL', 'endpoint': 'ALL'}
            ))
            
            # 히스토그램 데이터 초기화
            self.request_durations = []
        
        return metrics
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """요청 기록"""
        
        self.request_count += 1
        self.request_durations.append(duration)
    
    def increment_connections(self):
        """연결 증가"""
        self.active_connections += 1
    
    def decrement_connections(self):
        """연결 감소"""
        self.active_connections = max(0, self.active_connections - 1)

class BusinessMetricsCollector:
    """비즈니스 메트릭 수집기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_users = set()
        self.stock_searches = {}
        self.sentiment_analyses = {}
    
    async def collect_metrics(self) -> List[MetricValue]:
        """비즈니스 메트릭 수집"""
        
        metrics = []
        timestamp = datetime.now()
        
        # 활성 사용자 수
        metrics.append(MetricValue(
            name='users_active',
            value=len(self.active_users),
            timestamp=timestamp,
            labels={'time_window': 'current'}
        ))
        
        # 주식 검색 수
        total_searches = sum(self.stock_searches.values())
        metrics.append(MetricValue(
            name='stock_searches_total',
            value=total_searches,
            timestamp=timestamp
        ))
        
        # 감성 분석 수
        total_analyses = sum(self.sentiment_analyses.values())
        metrics.append(MetricValue(
            name='sentiment_analyses_total',
            value=total_analyses,
            timestamp=timestamp
        ))
        
        return metrics
    
    def record_user_activity(self, user_id: str):
        """사용자 활동 기록"""
        self.active_users.add(user_id)
    
    def record_stock_search(self, symbol: str, source: str = 'api'):
        """주식 검색 기록"""
        key = f"{symbol}:{source}"
        self.stock_searches[key] = self.stock_searches.get(key, 0) + 1
    
    def record_sentiment_analysis(self, symbol: str, source: str, sentiment: str):
        """감성 분석 기록"""
        key = f"{symbol}:{source}:{sentiment}"
        self.sentiment_analyses[key] = self.sentiment_analyses.get(key, 0) + 1

class DatabaseMetricsCollector:
    """데이터베이스 메트릭 수집기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection_pool = None
    
    async def collect_metrics(self) -> List[MetricValue]:
        """데이터베이스 메트릭 수집"""
        
        metrics = []
        timestamp = datetime.now()
        
        try:
            if self.connection_pool:
                # 활성 연결 수
                active_connections = len(self.connection_pool._pool)
                metrics.append(MetricValue(
                    name='db_connections_active',
                    value=active_connections,
                    timestamp=timestamp,
                    labels={'database': 'postgresql'}
                ))
                
                # 연결 풀 상태
                pool_size = self.connection_pool.size
                metrics.append(MetricValue(
                    name='db_connection_pool_size',
                    value=pool_size,
                    timestamp=timestamp,
                    labels={'database': 'postgresql'}
                ))
        
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {str(e)}")
        
        return metrics

class CacheMetricsCollector:
    """캐시 메트릭 수집기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.cache_hits = 0
        self.cache_misses = 0
    
    async def collect_metrics(self) -> List[MetricValue]:
        """캐시 메트릭 수집"""
        
        metrics = []
        timestamp = datetime.now()
        
        try:
            if self.redis_client:
                # Redis 정보 조회
                info = await self.redis_client.info()
                
                # 메모리 사용량
                used_memory = info.get('used_memory', 0)
                metrics.append(MetricValue(
                    name='cache_memory_usage_bytes',
                    value=used_memory,
                    timestamp=timestamp,
                    labels={'cache_type': 'redis'}
                ))
                
                # 연결 수
                connected_clients = info.get('connected_clients', 0)
                metrics.append(MetricValue(
                    name='cache_connections',
                    value=connected_clients,
                    timestamp=timestamp,
                    labels={'cache_type': 'redis'}
                ))
                
                # 캐시 적중률
                total_requests = self.cache_hits + self.cache_misses
                if total_requests > 0:
                    hit_rate = (self.cache_hits / total_requests) * 100
                    metrics.append(MetricValue(
                        name='cache_hit_rate',
                        value=hit_rate,
                        timestamp=timestamp,
                        labels={'cache_type': 'redis'}
                    ))
        
        except Exception as e:
            self.logger.error(f"Error collecting cache metrics: {str(e)}")
        
        return metrics
    
    def record_cache_hit(self, key_prefix: str = 'default'):
        """캐시 적중 기록"""
        self.cache_hits += 1
    
    def record_cache_miss(self, key_prefix: str = 'default'):
        """캐시 미스 기록"""
        self.cache_misses += 1

class ExternalAPIMetricsCollector:
    """외부 API 메트릭 수집기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_requests = {}
        self.api_response_times = {}
    
    async def collect_metrics(self) -> List[MetricValue]:
        """외부 API 메트릭 수집"""
        
        metrics = []
        timestamp = datetime.now()
        
        # API별 요청 수
        for api_key, count in self.api_requests.items():
            api_provider, endpoint = api_key.split(':', 1)
            metrics.append(MetricValue(
                name='external_api_requests_total',
                value=count,
                timestamp=timestamp,
                labels={
                    'api_provider': api_provider,
                    'endpoint': endpoint
                }
            ))
        
        # API별 응답 시간
        for api_key, times in self.api_response_times.items():
            if times:
                api_provider, endpoint = api_key.split(':', 1)
                avg_time = sum(times) / len(times)
                metrics.append(MetricValue(
                    name='external_api_response_time',
                    value=avg_time,
                    timestamp=timestamp,
                    labels={
                        'api_provider': api_provider,
                        'endpoint': endpoint
                    }
                ))
        
        return metrics
    
    def record_api_request(self, api_provider: str, endpoint: str, status: str, response_time: float):
        """API 요청 기록"""
        
        key = f"{api_provider}:{endpoint}"
        
        # 요청 수 증가
        self.api_requests[key] = self.api_requests.get(key, 0) + 1
        
        # 응답 시간 기록
        if key not in self.api_response_times:
            self.api_response_times[key] = []
        
        self.api_response_times[key].append(response_time)
        
        # 최근 100개만 유지
        if len(self.api_response_times[key]) > 100:
            self.api_response_times[key] = self.api_response_times[key][-100:]
```

### 2.2 알림 시스템

```python
# monitoring/alerting_system.py
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json
import aiohttp

class AlertSeverity(Enum):
    """알림 심각도"""
    INFO = "info"           # 정보
    WARNING = "warning"       # 경고
    ERROR = "error"          # 에러
    CRITICAL = "critical"    # 치명적

class AlertStatus(Enum):
    """알림 상태"""
    FIRING = "firing"        # 발생 중
    RESOLVED = "resolved"    # 해결됨

@dataclass
class AlertRule:
    """알림 규칙"""
    name: str
    description: str
    metric_name: str
    condition: str  # 조건 표현식
    threshold: float
    severity: AlertSeverity
    duration: int  # 지속 시간 (초)
    enabled: bool = True
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None

@dataclass
class Alert:
    """알림"""
    id: str
    rule_name: str
    status: AlertStatus
    severity: AlertSeverity
    message: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    start_time: datetime
    end_time: Optional[datetime] = None
    fingerprint: str = None

@dataclass
class NotificationChannel:
    """알림 채널"""
    name: str
    type: str  # email, slack, webhook, sms
    config: Dict[str, Any]
    enabled: bool = True

class AlertManager:
    """알림 관리자"""
    
    def __init__(self, monitoring_manager):
        self.monitoring_manager = monitoring_manager
        self.logger = logging.getLogger(__name__)
        
        # 알림 규칙
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # 활성 알림
        self.active_alerts: Dict[str, Alert] = {}
        
        # 알림 채널
        self.notification_channels: Dict[str, NotificationChannel] = {}
        
        # 알림 핸들러
        self.notification_handlers = {
            'email': EmailNotificationHandler(),
            'slack': SlackNotificationHandler(),
            'webhook': WebhookNotificationHandler(),
            'sms': SMSNotificationHandler()
        }
        
        # 알림 상태 추적
        self.alert_states: Dict[str, Dict] = {}
        
        # 기본 규칙 초기화
        self._initialize_default_rules()
        
        # 기본 알림 채널 초기화
        self._initialize_default_channels()
    
    def _initialize_default_rules(self):
        """기본 알림 규칙 초기화"""
        
        # 시스템 CPU 사용률 알림
        cpu_rule = AlertRule(
            name="high_cpu_usage",
            description="High CPU usage detected",
            metric_name="system_cpu_usage",
            condition=">=",
            threshold=80.0,
            severity=AlertSeverity.WARNING,
            duration=300,  # 5분
            labels={'component': 'system'},
            annotations={'summary': 'CPU usage is above 80% for 5 minutes'}
        )
        
        # 시스템 메모리 사용률 알림
        memory_rule = AlertRule(
            name="high_memory_usage",
            description="High memory usage detected",
            metric_name="system_memory_usage",
            condition=">=",
            threshold=85.0,
            severity=AlertSeverity.WARNING,
            duration=300,  # 5분
            labels={'component': 'system'},
            annotations={'summary': 'Memory usage is above 85% for 5 minutes'}
        )
        
        # 디스크 사용률 알림
        disk_rule = AlertRule(
            name="high_disk_usage",
            description="High disk usage detected",
            metric_name="system_disk_usage",
            condition=">=",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
            duration=600,  # 10분
            labels={'component': 'system'},
            annotations={'summary': 'Disk usage is above 90% for 10 minutes'}
        )
        
        # HTTP 에러율 알림
        http_error_rule = AlertRule(
            name="high_http_error_rate",
            description="High HTTP error rate detected",
            metric_name="http_requests_total",
            condition=">=",
            threshold=100.0,  # 5분 동안 100개 이상의 5xx 에러
            severity=AlertSeverity.ERROR,
            duration=300,  # 5분
            labels={'component': 'application'},
            annotations={'summary': 'HTTP error rate is high'}
        )
        
        # 데이터베이스 연결 알림
        db_connection_rule = AlertRule(
            name="database_connection_failure",
            description="Database connection failure",
            metric_name="db_connections_active",
            condition="==",
            threshold=0.0,
            severity=AlertSeverity.CRITICAL,
            duration=60,  # 1분
            labels={'component': 'database'},
            annotations={'summary': 'No active database connections'}
        )
        
        # 캐시 적중률 알림
        cache_hit_rate_rule = AlertRule(
            name="low_cache_hit_rate",
            description="Low cache hit rate detected",
            metric_name="cache_hit_rate",
            condition="<=",
            threshold=70.0,
            severity=AlertSeverity.WARNING,
            duration=600,  # 10분
            labels={'component': 'cache'},
            annotations={'summary': 'Cache hit rate is below 70%'}
        )
        
        # 외부 API 응답 시간 알림
        api_response_time_rule = AlertRule(
            name="slow_external_api",
            description="Slow external API response",
            metric_name="external_api_response_time",
            condition=">=",
            threshold=5000.0,  # 5초
            severity=AlertSeverity.WARNING,
            duration=300,  # 5분
            labels={'component': 'external_api'},
            annotations={'summary': 'External API response time is above 5 seconds'}
        )
        
        self.alert_rules = {
            "high_cpu_usage": cpu_rule,
            "high_memory_usage": memory_rule,
            "high_disk_usage": disk_rule,
            "high_http_error_rate": http_error_rule,
            "database_connection_failure": db_connection_rule,
            "low_cache_hit_rate": cache_hit_rate_rule,
            "slow_external_api": api_response_time_rule
        }
    
    def _initialize_default_channels(self):
        """기본 알림 채널 초기화"""
        
        # 이메일 채널
        email_channel = NotificationChannel(
            name="email",
            type="email",
            config={
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "alerts@insitechart.com",
                "password": "password",
                "from_address": "alerts@insitechart.com",
                "to_addresses": ["admin@insitechart.com", "devops@insitechart.com"]
            }
        )
        
        # Slack 채널
        slack_channel = NotificationChannel(
            name="slack",
            type="slack",
            config={
                "webhook_url": "https://hooks.slack.com/services/...",
                "channel": "#alerts",
                "username": "InsiteChart Bot"
            }
        )
        
        # 웹훅 채널
        webhook_channel = NotificationChannel(
            name="webhook",
            type="webhook",
            config={
                "url": "https://api.insitechart.com/webhooks/alerts",
                "headers": {"Authorization": "Bearer token"}
            }
        )
        
        self.notification_channels = {
            "email": email_channel,
            "slack": slack_channel,
            "webhook": webhook_channel
        }
    
    async def start_monitoring(self):
        """알림 모니터링 시작"""
        
        self.logger.info("Starting alert monitoring")
        
        # 알림 평가 루프
        while True:
            try:
                await self._evaluate_alert_rules()
                await asyncio.sleep(60)  # 1분마다 평가
            except Exception as e:
                self.logger.error(f"Error in alert monitoring: {str(e)}")
                await asyncio.sleep(60)
    
    async def _evaluate_alert_rules(self):
        """알림 규칙 평가"""
        
        current_time = datetime.now()
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            try:
                # 규칙 상태 초기화
                if rule_name not in self.alert_states:
                    self.alert_states[rule_name] = {
                        'last_evaluation': current_time,
                        'condition_met_since': None,
                        'alert_sent': False
                    }
                
                rule_state = self.alert_states[rule_name]
                
                # 메트릭 조회
                end_time = current_time
                start_time = current_time - timedelta(seconds=rule.duration)
                
                # 최신 메트릭 값 조회
                metrics = await self.monitoring_manager.get_metrics(
                    rule.metric_name,
                    start_time,
                    end_time,
                    rule.labels
                )
                
                if not metrics:
                    continue
                
                # 조건 평가
                latest_metric = metrics[-1]
                condition_met = self._evaluate_condition(
                    latest_metric.value, 
                    rule.condition, 
                    rule.threshold
                )
                
                # 알림 상태 결정
                if condition_met:
                    if rule_state['condition_met_since'] is None:
                        rule_state['condition_met_since'] = current_time
                    
                    # 지속 시간 확인
                    condition_duration = (current_time - rule_state['condition_met_since']).total_seconds()
                    
                    if condition_duration >= rule.duration and not rule_state['alert_sent']:
                        # 알림 발생
                        await self._fire_alert(rule, latest_metric)
                        rule_state['alert_sent'] = True
                
                else:
                    # 조건이 만족되지 않으면 상태 초기화
                    rule_state['condition_met_since'] = None
                    
                    if rule_state['alert_sent']:
                        # 알림 해결
                        await self._resolve_alert(rule_name)
                        rule_state['alert_sent'] = False
                
                rule_state['last_evaluation'] = current_time
                
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule_name}: {str(e)}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """조건 평가"""
        
        if condition == ">=":
            return value >= threshold
        elif condition == ">":
            return value > threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "==":
            return abs(value - threshold) < 0.001  # 부동소수점 비교
        elif condition == "!=":
            return abs(value - threshold) >= 0.001
        
        return False
    
    async def _fire_alert(self, rule: AlertRule, metric):
        """알림 발생"""
        
        alert_id = f"{rule.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 알림 생성
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            status=AlertStatus.FIRING,
            severity=rule.severity,
            message=f"{rule.description}: {metric.value} {rule.condition} {rule.threshold}",
            labels=rule.labels or {},
            annotations=rule.annotations or {},
            start_time=datetime.now(),
            fingerprint=self._generate_fingerprint(rule, metric)
        )
        
        # 활성 알림에 추가
        self.active_alerts[alert_id] = alert
        
        # 알림 전송
        await self._send_notifications(alert)
        
        self.logger.warning(f"Alert fired: {alert_id} - {alert.message}")
    
    async def _resolve_alert(self, rule_name: str):
        """알림 해결"""
        
        # 해당 규칙의 활성 알림 찾기
        resolved_alerts = [
            alert for alert in self.active_alerts.values()
            if alert.rule_name == rule_name and alert.status == AlertStatus.FIRING
        ]
        
        for alert in resolved_alerts:
            # 알림 상태 업데이트
            alert.status = AlertStatus.RESOLVED
            alert.end_time = datetime.now()
            
            # 해결 알림 전송
            await self._send_notifications(alert)
            
            self.logger.info(f"Alert resolved: {alert.id}")
    
    async def _send_notifications(self, alert: Alert):
        """알림 전송"""
        
        for channel_name, channel in self.notification_channels.items():
            if not channel.enabled:
                continue
            
            handler = self.notification_handlers.get(channel.type)
            
            if handler:
                try:
                    await handler.send_notification(alert, channel.config)
                except Exception as e:
                    self.logger.error(f"Error sending notification via {channel_name}: {str(e)}")
    
    def _generate_fingerprint(self, rule: AlertRule, metric) -> str:
        """알림 지문 생성"""
        
        # 규칙 이름과 레이블로 지문 생성
        fingerprint_data = {
            'rule_name': rule.name,
            'labels': rule.labels or {}
        }
        
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        
        import hashlib
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def get_active_alerts(self) -> List[Alert]:
        """활성 알림 조회"""
        
        return [
            alert for alert in self.active_alerts.values()
            if alert.status == AlertStatus.FIRING
        ]
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """알림 이력 조회"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.active_alerts.values()
            if alert.start_time >= cutoff_time
        ]
    
    def add_alert_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        
        self.alert_rules[rule.name] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def update_alert_rule(self, rule_name: str, **kwargs):
        """알림 규칙 업데이트"""
        
        if rule_name not in self.alert_rules:
            raise ValueError(f"Alert rule not found: {rule_name}")
        
        rule = self.alert_rules[rule_name]
        
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self.logger.info(f"Updated alert rule: {rule_name}")
    
    def delete_alert_rule(self, rule_name: str):
        """알림 규칙 삭제"""
        
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            
            # 관련 상태 정리
            if rule_name in self.alert_states:
                del self.alert_states[rule_name]
            
            self.logger.info(f"Deleted alert rule: {rule_name}")
    
    def add_notification_channel(self, channel: NotificationChannel):
        """알림 채널 추가"""
        
        self.notification_channels[channel.name] = channel
        self.logger.info(f"Added notification channel: {channel.name}")
    
    def delete_notification_channel(self, channel_name: str):
        """알림 채널 삭제"""
        
        if channel_name in self.notification_channels:
            del self.notification_channels[channel_name]
            self.logger.info(f"Deleted notification channel: {channel_name}")

class EmailNotificationHandler:
    """이메일 알림 핸들러"""
    
    async def send_notification(self, alert: Alert, config: Dict[str, Any]):
        """이메일 알림 전송"""
        
        try:
            # 이메일 내용 생성
            subject = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            if alert.status == AlertStatus.FIRING:
                body = f"""
Alert: {alert.message}
Severity: {alert.severity.value}
Time: {alert.start_time}
Labels: {alert.labels}
Annotations: {alert.annotations}
"""
            else:
                body = f"""
Alert Resolved: {alert.rule_name}
Time: {alert.start_time} - {alert.end_time}
Duration: {alert.end_time - alert.start_time}
"""
            
            # 이메일 전송
            msg = MIMEMultipart()
            msg['From'] = config['from_address']
            msg['To'] = ', '.join(config['to_addresses'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP 서버 연결 및 전송
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            
            text = msg.as_string()
            server.sendmail(config['from_address'], config['to_addresses'], text)
            server.quit()
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending email notification: {str(e)}")

class SlackNotificationHandler:
    """Slack 알림 핸들러"""
    
    async def send_notification(self, alert: Alert, config: Dict[str, Any]):
        """Slack 알림 전송"""
        
        try:
            # Slack 메시지 생성
            color = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.ERROR: "danger",
                AlertSeverity.CRITICAL: "danger"
            }.get(alert.severity, "warning")
            
            if alert.status == AlertStatus.FIRING:
                text = f"🚨 Alert: {alert.message}"
            else:
                text = f"✅ Resolved: {alert.rule_name}"
            
            payload = {
                "channel": config.get('channel', '#alerts'),
                "username": config.get('username', 'AlertBot'),
                "attachments": [
                    {
                        "color": color,
                        "title": alert.rule_name,
                        "text": text,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            }
                        ],
                        "footer": "InsiteChart Alerts",
                        "ts": int(alert.start_time.timestamp())
                    }
                ]
            }
            
            # 웹훅 전송
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config['webhook_url'],
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Slack webhook failed: {response.status}")
        
        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending Slack notification: {str(e)}")

class WebhookNotificationHandler:
    """웹훅 알림 핸들러"""
    
    async def send_notification(self, alert: Alert, config: Dict[str, Any]):
        """웹훅 알림 전송"""
        
        try:
            # 페이로드 생성
            payload = {
                "alert_id": alert.id,
                "rule_name": alert.rule_name,
                "status": alert.status.value,
                "severity": alert.severity.value,
                "message": alert.message,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "start_time": alert.start_time.isoformat(),
                "end_time": alert.end_time.isoformat() if alert.end_time else None
            }
            
            # 웹훅 전송
            headers = config.get('headers', {})
            headers['Content-Type'] = 'application/json'
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config['url'],
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status not in [200, 201, 202]:
                        raise Exception(f"Webhook failed: {response.status}")
        
        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending webhook notification: {str(e)}")

class SMSNotificationHandler:
    """SMS 알림 핸들러"""
    
    async def send_notification(self, alert: Alert, config: Dict[str, Any]):
        """SMS 알림 전송"""
        
        try:
            # SMS 메시지 생성
            if alert.status == AlertStatus.FIRING:
                message = f"[{alert.severity.value.upper()}] {alert.rule_name}: {alert.message}"
            else:
                message = f"[RESOLVED] {alert.rule_name}"
            
            # SMS API 호출 (실제 구현에서는 Twilio 등 사용)
            # 여기서는 로그만 출력
            logging.getLogger(__name__).info(f"SMS would be sent: {message}")
        
        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending SMS notification: {str(e)}")
```

## 3. 대시보드 시스템

### 3.1 모니터링 대시보드

```python
# monitoring/dashboard.py
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
from .monitoring_manager import MonitoringManager
from .alerting_system import AlertManager

@dataclass
class DashboardWidget:
    """대시보드 위젯"""
    id: str
    type: str  # metric_chart, alert_list, system_status, etc.
    title: str
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    refresh_interval: int  # 초

@dataclass
class Dashboard:
    """대시보드"""
    id: str
    name: str
    description: str
    widgets: List[DashboardWidget]
    layout: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class MonitoringDashboard:
    """모니터링 대시보드"""
    
    def __init__(self, monitoring_manager: MonitoringManager, alert_manager: AlertManager):
        self.monitoring_manager = monitoring_manager
        self.alert_manager = alert_manager
        self.logger = logging.getLogger(__name__)
        
        # 대시보드 저장소
        self.dashboards: Dict[str, Dashboard] = {}
        
        # 기본 대시보드 초기화
        self._initialize_default_dashboards()
    
    def _initialize_default_dashboards(self):
        """기본 대시보드 초기화"""
        
        # 시스템 개요 대시보드
        system_overview_widgets = [
            DashboardWidget(
                id="cpu_usage",
                type="metric_chart",
                title="CPU Usage",
                config={
                    "metric_name": "system_cpu_usage",
                    "chart_type": "line",
                    "time_range": "1h",
                    "aggregation": "avg",
                    "threshold": 80
                },
                position={"x": 0, "y": 0, "width": 6, "height": 4},
                refresh_interval=30
            ),
            DashboardWidget(
                id="memory_usage",
                type="metric_chart",
                title="Memory Usage",
                config={
                    "metric_name": "system_memory_usage",
                    "chart_type": "line",
                    "time_range": "1h",
                    "aggregation": "avg",
                    "threshold": 85
                },
                position={"x": 6, "y": 0, "width": 6, "height": 4},
                refresh_interval=30
            ),
            DashboardWidget(
                id="disk_usage",
                type="metric_chart",
                title="Disk Usage",
                config={
                    "metric_name": "system_disk_usage",
                    "chart_type": "bar",
                    "time_range": "1h",
                    "aggregation": "avg",
                    "threshold": 90
                },
                position={"x": 0, "y": 4, "width": 6, "height": 4},
                refresh_interval=60
            ),
            DashboardWidget(
                id="active_alerts",
                type="alert_list",
                title="Active Alerts",
                config={
                    "severity_filter": ["error", "critical"],
                    "max_items": 10
                },
                position={"x": 6, "y": 4, "width": 6, "height": 4},
                refresh_interval=30
            )
        ]
        
        system_overview = Dashboard(
            id="system_overview",
            name="System Overview",
            description="Overall system status and metrics",
            widgets=system_overview_widgets,
            layout={"columns": 12},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 애플리케이션 성능 대시보드
        app_performance_widgets = [
            DashboardWidget(
                id="http_requests",
                type="metric_chart",
                title="HTTP Requests",
                config={
                    "metric_name": "http_requests_total",
                    "chart_type": "line",
                    "time_range": "1h",
                    "aggregation": "rate"
                },
                position={"x": 0, "y": 0, "width": 6, "height": 4},
                refresh_interval=30
            ),
            DashboardWidget(
                id="response_time",
                type="metric_chart",
                title="Response Time",
                config={
                    "metric_name": "http_request_duration",
                    "chart_type": "line",
                    "time_range": "1h",
                    "aggregation": "p95",
                    "threshold": 1000  # 1초
                },
                position={"x": 6, "y": 0, "width": 6, "height": 4},
                refresh_interval=30
            ),
            DashboardWidget(
                id="active_users",
                type="metric_chart",
                title="Active Users",
                config={
                    "metric_name": "users_active",
                    "chart_type": "line",
                    "time_range": "24h",
                    "aggregation": "avg"
                },
                position={"x": 0, "y": 4, "width": 6, "height": 4},
                refresh_interval=60
            ),
            DashboardWidget(
                id="error_rate",
                type="metric_chart",
                title="Error Rate",
                config={
                    "metric_name": "http_requests_total",
                    "chart_type": "line",
                    "time_range": "1h",
                    "aggregation": "error_rate",
                    "threshold": 5  # 5%
                },
                position={"x": 6, "y": 4, "width": 6, "height": 4},
                refresh_interval=30
            )
        ]
        
        app_performance = Dashboard(
            id="app_performance",
            name="Application Performance",
            description="Application performance metrics",
            widgets=app_performance_widgets,
            layout={"columns": 12},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 비즈니스 메트릭 대시보드
        business_metrics_widgets = [
            DashboardWidget(
                id="stock_searches",
                type="metric_chart",
                title="Stock Searches",
                config={
                    "metric_name": "stock_searches_total",
                    "chart_type": "line",
                    "time_range": "24h",
                    "aggregation": "rate"
                },
                position={"x": 0, "y": 0, "width": 6, "height": 4},
                refresh_interval=60
            ),
            DashboardWidget(
                id="sentiment_analyses",
                type="metric_chart",
                title="Sentiment Analyses",
                config={
                    "metric_name": "sentiment_analyses_total",
                    "chart_type": "line",
                    "time_range": "24h",
                    "aggregation": "rate"
                },
                position={"x": 6, "y": 0, "width": 6, "height": 4},
                refresh_interval=60
            ),
            DashboardWidget(
                id="top_symbols",
                type="top_n_table",
                title="Top Searched Symbols",
                config={
                    "metric_name": "stock_searches_total",
                    "time_range": "24h",
                    "limit": 10,
                    "group_by": "symbol"
                },
                position={"x": 0, "y": 4, "width": 12, "height": 4},
                refresh_interval=300  # 5분
            )
        ]
        
        business_metrics = Dashboard(
            id="business_metrics",
            name="Business Metrics",
            description="Business and user engagement metrics",
            widgets=business_metrics_widgets,
            layout={"columns": 12},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.dashboards = {
            "system_overview": system_overview,
            "app_performance": app_performance,
            "business_metrics": business_metrics
        }
    
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """대시보드 데이터 조회"""
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard not found: {dashboard_id}")
        
        dashboard = self.dashboards[dashboard_id]
        widget_data = {}
        
        # 각 위젯 데이터 조회
        for widget in dashboard.widgets:
            try:
                if widget.type == "metric_chart":
                    data = await self._get_metric_chart_data(widget)
                elif widget.type == "alert_list":
                    data = await self._get_alert_list_data(widget)
                elif widget.type == "top_n_table":
                    data = await self._get_top_n_table_data(widget)
                else:
                    data = {"error": f"Unknown widget type: {widget.type}"}
                
                widget_data[widget.id] = data
                
            except Exception as e:
                self.logger.error(f"Error getting data for widget {widget.id}: {str(e)}")
                widget_data[widget.id] = {"error": str(e)}
        
        return {
            "dashboard": asdict(dashboard),
            "widget_data": widget_data,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_metric_chart_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """메트릭 차트 데이터 조회"""
        
        config = widget.config
        metric_name = config["metric_name"]
        time_range = config["time_range"]
        aggregation = config.get("aggregation", "avg")
        threshold = config.get("threshold")
        
        # 시간 범위 계산
        end_time = datetime.now()
        
        if time_range == "1h":
            start_time = end_time - timedelta(hours=1)
        elif time_range == "6h":
            start_time = end_time - timedelta(hours=6)
        elif time_range == "24h":
            start_time = end_time - timedelta(days=1)
        elif time_range == "7d":
            start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(hours=1)
        
        # 메트릭 데이터 조회
        metrics = await self.monitoring_manager.get_metrics(
            metric_name, start_time, end_time
        )
        
        if not metrics:
            return {"data": [], "threshold": threshold}
        
        # 데이터 집계
        if aggregation == "rate":
            # 시간당 비율 계산
            data_points = self._calculate_rate(metrics, time_range)
        elif aggregation == "p95":
            # 95번째 백분위수 계산
            data_points = self._calculate_percentile(metrics, 95)
        elif aggregation == "error_rate":
            # 에러율 계산
            data_points = await self._calculate_error_rate(metrics, time_range)
        else:
            # 평균 계산
            data_points = self._calculate_average(metrics, time_range)
        
        return {
            "data": data_points,
            "threshold": threshold,
            "unit": self._get_metric_unit(metric_name)
        }
    
    async def _get_alert_list_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """알림 목록 데이터 조회"""
        
        config = widget.config
        severity_filter = config.get("severity_filter", [])
        max_items = config.get("max_items", 10)
        
        # 활성 알림 조회
        active_alerts = self.alert_manager.get_active_alerts()
        
        # 심각도 필터링
        if severity_filter:
            active_alerts = [
                alert for alert in active_alerts
                if alert.severity.value in severity_filter
            ]
        
        # 최신 알림 정렬 및 제한
        active_alerts.sort(key=lambda x: x.start_time, reverse=True)
        active_alerts = active_alerts[:max_items]
        
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "start_time": alert.start_time.isoformat(),
                    "labels": alert.labels,
                    "annotations": alert.annotations
                }
                for alert in active_alerts
            ]
        }
    
    async def _get_top_n_table_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Top N 테이블 데이터 조회"""
        
        config = widget.config
        metric_name = config["metric_name"]
        time_range = config["time_range"]
        limit = config.get("limit", 10)
        group_by = config.get("group_by")
        
        # 시간 범위 계산
        end_time = datetime.now()
        
        if time_range == "1h":
            start_time = end_time - timedelta(hours=1)
        elif time_range == "24h":
            start_time = end_time - timedelta(days=1)
        else:
            start_time = end_time - timedelta(days=1)
        
        # 메트릭 데이터 조회
        metrics = await self.monitoring_manager.get_metrics(
            metric_name, start_time, end_time
        )
        
        if not metrics:
            return {"data": []}
        
        # 그룹별 집계
        grouped_data = {}
        
        for metric in metrics:
            group_key = None
            
            if group_by == "symbol" and metric.labels:
                group_key = metric.labels.get("symbol", "unknown")
            else:
                group_key = "total"
            
            if group_key not in grouped_data:
                grouped_data[group_key] = []
            
            grouped_data[group_key].append(metric.value)
        
        # 그룹별 합계 계산 및 정렬
        top_data = []
        for group_key, values in grouped_data.items():
            total_value = sum(values)
            top_data.append({
                "group": group_key,
                "value": total_value
            })
        
        top_data.sort(key=lambda x: x["value"], reverse=True)
        top_data = top_data[:limit]
        
        return {"data": top_data}
    
    def _calculate_rate(self, metrics: List, time_range: str) -> List[Dict]:
        """시간당 비율 계산"""
        
        if not metrics:
            return []
        
        # 시간 간격 결정
        if time_range == "1h":
            interval = timedelta(minutes=5)
        elif time_range == "6h":
            interval = timedelta(minutes=30)
        elif time_range == "24h":
            interval = timedelta(hours=1)
        else:
            interval = timedelta(minutes=5)
        
        # 시간 간격별 데이터 집계
        data_points = []
        current_time = metrics[0].timestamp
        
        while current_time <= metrics[-1].timestamp:
            end_time = current_time + interval
            
            # 간격 내 메트릭 필터링
            interval_metrics = [
                m for m in metrics
                if current_time <= m.timestamp < end_time
            ]
            
            if interval_metrics:
                # 카운터 메트릭인 경우 증가량 계산
                if len(interval_metrics) >= 2:
                    rate = interval_metrics[-1].value - interval_metrics[0].value
                else:
                    rate = interval_metrics[0].value
                
                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "value": rate
                })
            
            current_time = end_time
        
        return data_points
    
    def _calculate_percentile(self, metrics: List, percentile: int) -> List[Dict]:
        """백분위수 계산"""
        
        if not metrics:
            return []
        
        # 시간 간격별 데이터 그룹화
        data_points = []
        interval = timedelta(minutes=5)
        current_time = metrics[0].timestamp
        
        while current_time <= metrics[-1].timestamp:
            end_time = current_time + interval
            
            # 간격 내 메트릭 필터링
            interval_metrics = [
                m for m in metrics
                if current_time <= m.timestamp < end_time
            ]
            
            if interval_metrics:
                values = [m.value for m in interval_metrics]
                values.sort()
                
                # 백분위수 계산
                index = int(len(values) * percentile / 100)
                if index >= len(values):
                    index = len(values) - 1
                
                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "value": values[index]
                })
            
            current_time = end_time
        
        return data_points
    
    async def _calculate_error_rate(self, metrics: List, time_range: str) -> List[Dict]:
        """에러율 계산"""
        
        if not metrics:
            return []
        
        # 시간 간격별 데이터 그룹화
        data_points = []
        interval = timedelta(minutes=5)
        current_time = metrics[0].timestamp
        
        while current_time <= metrics[-1].timestamp:
            end_time = current_time + interval
            
            # 간격 내 메트릭 필터링
            interval_metrics = [
                m for m in metrics
                if current_time <= m.timestamp < end_time
            ]
            
            if interval_metrics:
                # 상태 코드별 그룹화
                status_counts = {}
                total_requests = 0
                
                for metric in interval_metrics:
                    status_code = metric.labels.get("status_code", "unknown")
                    status_counts[status_code] = status_counts.get(status_code, 0) + metric.value
                    total_requests += metric.value
                
                # 에러율 계산 (5xx 상태 코드)
                error_count = sum(
                    count for status, count in status_counts.items()
                    if status.startswith("5")
                )
                
                error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
                
                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "value": error_rate
                })
            
            current_time = end_time
        
        return data_points
    
    def _calculate_average(self, metrics: List, time_range: str) -> List[Dict]:
        """평균 계산"""
        
        if not metrics:
            return []
        
        # 시간 간격별 데이터 그룹화
        data_points = []
        interval = timedelta(minutes=5)
        current_time = metrics[0].timestamp
        
        while current_time <= metrics[-1].timestamp:
            end_time = current_time + interval
            
            # 간격 내 메트릭 필터링
            interval_metrics = [
                m for m in metrics
                if current_time <= m.timestamp < end_time
            ]
            
            if interval_metrics:
                values = [m.value for m in interval_metrics]
                average = sum(values) / len(values)
                
                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "value": average
                })
            
            current_time = end_time
        
        return data_points
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """메트릭 단위 조회"""
        
        if "cpu" in metric_name or "memory" in metric_name or "disk" in metric_name:
            return "%"
        elif "bytes" in metric_name:
            return "bytes"
        elif "duration" in metric_name or "response_time" in metric_name:
            return "ms"
        elif "requests" in metric_name:
            return "count"
        else:
            return ""
```

## 4. 구현 가이드

### 4.1 단계별 구현 계획

#### 1단계: 기본 메트릭 수집 (2-3주)
- 시스템 메트릭 수집기 구현
- 애플리케이션 메트릭 수집기 구현
- Redis 기반 메트릭 저장소 구축
- 기본 대시보드 위젯 개발

#### 2단계: 알림 시스템 (2-3주)
- 알림 규칙 엔진 구현
- 다양한 알림 채널 핸들러 개발
- 알림 상태 관리 시스템 구축
- 알림 템플릿 및 포맷팅

#### 3단계: 고급 모니터링 (2-3주)
- 비즈니스 메트릭 수집기 구현
- 외부 API 모니터링 기능 추가
- 데이터베이스 및 캐시 모니터링 강화
- 분산 추적 시스템 통합

#### 4단계: 대시보드 고도화 (2-3주)
- 실시간 대시보드 업데이트
- 대화형 차트 및 필터링
- 사용자별 대시보드 설정
- 모바일 대응 대시보드

#### 5단계: 분석 및 예측 (3-4주)
- 메트릭 기반 이상 감지
- 성능 추세 분석
- 용량 계획 지원
- 자동화된 성능 최적화 제안

### 4.2 성능 고려사항

1. **메트릭 수집 성능**
   - 비동기 처리로 애플리케이션 영향 최소화
   - 배치 처리로 네트워크 오버헤드 감소
   - 샘플링으로 고빈도 메트릭 제어

2. **저장소 최적화**
   - 적절한 데이터 보관 기간 설정
   - 시계열 데이터베이스 고려
   - 압축 및 인덱싱 전략

3. **대시보드 성능**
   - 클라이언트 측 캐싱
   - 데이터 프리페칭
   - 실시간 업데이트 최적화

### 4.3 보안 고려사항

1. **메트릭 데이터 보안**
   - 민감 정보 포함 여부 검토
   - 접근 제어 및 인증
   - 데이터 전송 암호화

2. **알림 보안**
   - 알림 채널 보안 강화
   - 개인정보 포함 제어
   - 알림 위변조 방지

3. **대시보드 보안**
   - 사용자별 접근 권한
   - 데이터 필터링 및 마스킹
   - 감사 로그 기록

## 5. 결론

본 모니터링 및 알림 시스템 설계는 InsiteChart 플랫폼의 안정적인 운영과 성능 최적화를 위한 포괄적인 솔루션을 제공합니다. 다계층 모니터링, 지능형 알림, 실시간 대시보드를 통해 시스템 상태를 실시간으로 파악하고 잠재적 문제를 사전에 대응할 수 있습니다.

단계적인 구현을 통해 시스템 안정성을 점진적으로 강화하고, 실제 운영 데이터를 기반으로 모니터링 정책을 최적화하여 장기적인 성공을 보장할 수 있습니다.