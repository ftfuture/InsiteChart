"""
지능형 캐시 워밍 시스템 모듈
접근 패턴 분석, 예측적 캐시 워밍, 동적 TTL 조정 기능 제공
"""

import asyncio
import time
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging
import redis.asyncio as redis
import json

logger = logging.getLogger(__name__)

@dataclass
class AccessPattern:
    """접근 패턴 모델"""
    key: str
    frequency: str  # low, medium, high
    pattern: str     # random, periodic, burst
    avg_interval: float
    std_dev: float
    last_access: datetime
    access_count: int
    prediction_confidence: float
    
@dataclass
class CacheWarmupTask:
    """캐시 워밍 작업 모델"""
    key: str
    scheduled_time: datetime
    priority: int
    data_loader: str  # 데이터 로더 함수 이름
    params: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class CacheStats:
    """캐시 통계 모델"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    warmup_hits: int = 0
    prediction_accuracy: float = 0.0
    avg_response_time: float = 0.0
    memory_usage: int = 0

class IntelligentCacheManager:
    """지능형 캐시 관리자 클래스"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_pattern_history: int = 100,
        warmup_queue_size: int = 1000
    ):
        self.redis_url = redis_url
        self.max_pattern_history = max_pattern_history
        self.warmup_queue_size = warmup_queue_size
        
        # Redis 클라이언트
        self.redis_client = None
        
        # 접근 패턴 분석
        self.access_patterns: Dict[str, AccessPattern] = {}
        self.access_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_pattern_history))
        
        # 워밍 작업 관리
        self.warmup_queue: List[CacheWarmupTask] = []
        self.warmup_tasks: Dict[str, asyncio.Task] = {}
        
        # 데이터 로더 함수
        self.data_loaders: Dict[str, callable] = {}
        
        # 통계 정보
        self.stats = CacheStats()
        
        # 예측 모델 파라미터
        self.prediction_params = {
            "min_samples": 5,           # 최소 샘플 수
            "pattern_threshold": 0.7,    # 패턴 신뢰도 임계값
            "warmup_threshold": 300,      # 워밍 임계 시간 (초)
            "confidence_decay": 0.95,     # 신뢰도 감소 계수
            "burst_multiplier": 2.0      # 버스트 승수
        }
        
        # 상태 관리
        self.running = False
        
        # 기본 TTL 설정 (초)
        self.default_ttls = {
            "stock_price": 60,      # 1분
            "sentiment": 300,       # 5분
            "profile": 86400,       # 24시간
            "search": 1800,         # 30분
            "market_data": 120      # 2분
        }
    
    async def initialize(self):
        """지능형 캐시 관리자 초기화"""
        try:
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # 기존 패턴 데이터 로드
            await self._load_access_patterns()
            
            logger.info("Intelligent Cache Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Intelligent Cache Manager: {str(e)}")
            raise
    
    async def start(self):
        """지능형 캐시 관리자 시작"""
        if not self.redis_client:
            await self.initialize()
        
        self.running = True
        
        # 워밍 작업 스케줄러 시작
        asyncio.create_task(self._warmup_scheduler())
        
        # 패턴 분석기 시작
        asyncio.create_task(self._pattern_analyzer())
        
        # 통계 수집기 시작
        asyncio.create_task(self._stats_collector())
        
        logger.info("Intelligent Cache Manager started")
    
    async def stop(self):
        """지능형 캐시 관리자 중지"""
        self.running = False
        
        # 모든 워밍 작업 중지
        for task in self.warmup_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 패턴 데이터 저장
        await self._save_access_patterns()
        
        logger.info("Intelligent Cache Manager stopped")
    
    def register_data_loader(self, name: str, loader_func: callable):
        """
        데이터 로더 함수 등록
        
        Args:
            name: 로더 이름
            loader_func: 데이터 로딩 함수
        """
        self.data_loaders[name] = loader_func
        logger.info(f"Registered data loader: {name}")
    
    async def get_with_predictive_warming(
        self,
        key: str,
        data_type: str = "default",
        loader_name: Optional[str] = None,
        loader_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        예측적 워밍과 함께 캐시 조회
        
        Args:
            key: 캐시 키
            data_type: 데이터 타입
            loader_name: 데이터 로더 이름
            loader_params: 로더 파라미터
            
        Returns:
            캐시된 데이터 또는 None
        """
        start_time = time.time()
        
        try:
            # 통계 업데이트
            self.stats.total_requests += 1
            
            # 접근 기록
            await self._record_access(key)
            
            # 캐시 조회
            data = await self._get_from_cache(key)
            
            if data:
                # 캐시 히트
                self.stats.cache_hits += 1
                
                # 접근 패턴 분석 및 예측적 워밍
                pattern = await self._analyze_access_pattern(key)
                if pattern:
                    await self._schedule_predictive_warmup(key, pattern, data_type, loader_name, loader_params)
                
                logger.debug(f"Cache hit for key: {key}")
                return data
            else:
                # 캐시 미스
                self.stats.cache_misses += 1
                
                # 데이터 로드가 있는 경우
                if loader_name and loader_name in self.data_loaders:
                    try:
                        # 데이터 로드
                        data = await self._load_data(loader_name, loader_params or {})
                        
                        if data:
                            # 캐시에 저장
                            ttl = await self._determine_dynamic_ttl(key, data_type)
                            await self._save_to_cache(key, data, ttl)
                            
                            logger.debug(f"Loaded and cached data for key: {key}")
                            return data
                            
                    except Exception as e:
                        logger.error(f"Error loading data for key {key}: {str(e)}")
                
                return None
                
        except Exception as e:
            logger.error(f"Error in get_with_predictive_warming for {key}: {str(e)}")
            return None
        finally:
            # 응답 시간 기록
            response_time = time.time() - start_time
            self._update_response_time(response_time)
    
    async def preload_data(
        self,
        key: str,
        data_type: str,
        loader_name: str,
        loader_params: Optional[Dict[str, Any]] = None,
        priority: int = 1
    ) -> bool:
        """
        데이터 사전 로드
        
        Args:
            key: 캐시 키
            data_type: 데이터 타입
            loader_name: 데이터 로더 이름
            loader_params: 로더 파라미터
            priority: 우선순위
            
        Returns:
            성공 여부
        """
        try:
            if loader_name not in self.data_loaders:
                logger.error(f"Data loader not found: {loader_name}")
                return False
            
            # 데이터 로드
            data = await self._load_data(loader_name, loader_params or {})
            
            if data:
                # 캐시에 저장
                ttl = await self._determine_dynamic_ttl(key, data_type)
                await self._save_to_cache(key, data, ttl)
                
                logger.info(f"Preloaded data for key: {key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error preloading data for {key}: {str(e)}")
            return False
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        캐시 통계 정보 조회
        
        Returns:
            캐시 통계
        """
        hit_rate = (
            self.stats.cache_hits / self.stats.total_requests * 100
            if self.stats.total_requests > 0 else 0
        )
        
        return {
            "total_requests": self.stats.total_requests,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "hit_rate": hit_rate,
            "warmup_hits": self.stats.warmup_hits,
            "prediction_accuracy": self.stats.prediction_accuracy,
            "avg_response_time": self.stats.avg_response_time,
            "memory_usage": self.stats.memory_usage,
            "active_patterns": len(self.access_patterns),
            "warmup_queue_size": len(self.warmup_queue),
            "running": self.running
        }
    
    async def _record_access(self, key: str):
        """접근 기록"""
        try:
            now = datetime.utcnow()
            
            # 접근 이력에 추가
            self.access_history[key].append(now)
            
            # Redis에도 기록 (영속성)
            access_key = f"cache:access:{key}"
            await self.redis_client.lpush(access_key, now.isoformat())
            await self.redis_client.ltrim(access_key, 0, self.max_pattern_history - 1)
            await self.redis_client.expire(access_key, 86400)  # 24시간 유지
            
        except Exception as e:
            logger.error(f"Error recording access for {key}: {str(e)}")
    
    async def _analyze_access_pattern(self, key: str) -> Optional[AccessPattern]:
        """접근 패턴 분석"""
        try:
            # 최소 샘플 수 확인
            if len(self.access_history[key]) < self.prediction_params["min_samples"]:
                return None
            
            # 접근 시간 간격 계산
            access_times = list(self.access_history[key])
            intervals = []
            
            for i in range(1, len(access_times)):
                interval = (access_times[i] - access_times[i-1]).total_seconds()
                intervals.append(interval)
            
            if not intervals:
                return None
            
            # 통계 계산
            avg_interval = statistics.mean(intervals)
            std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            # 빈도 분류
            if avg_interval < 60:  # 1분 미만
                frequency = "high"
            elif avg_interval < 300:  # 5분 미만
                frequency = "medium"
            else:
                frequency = "low"
            
            # 패턴 분류
            if std_dev < avg_interval * 0.2:  # 표준편차가 평균의 20% 미만
                pattern = "periodic"
            elif std_dev < avg_interval * 0.5:  # 표준편차가 평균의 50% 미만
                pattern = "burst"
            else:
                pattern = "random"
            
            # 예측 신뢰도 계산
            sample_ratio = min(len(access_times) / self.max_pattern_history, 1.0)
            pattern_confidence = sample_ratio * (1.0 - std_dev / avg_interval) if avg_interval > 0 else 0.0
            
            access_pattern = AccessPattern(
                key=key,
                frequency=frequency,
                pattern=pattern,
                avg_interval=avg_interval,
                std_dev=std_dev,
                last_access=access_times[-1],
                access_count=len(access_times),
                prediction_confidence=max(0.0, min(1.0, pattern_confidence))
            )
            
            # 패턴 저장
            self.access_patterns[key] = access_pattern
            
            return access_pattern
            
        except Exception as e:
            logger.error(f"Error analyzing access pattern for {key}: {str(e)}")
            return None
    
    async def _schedule_predictive_warmup(
        self,
        key: str,
        pattern: AccessPattern,
        data_type: str,
        loader_name: Optional[str],
        loader_params: Optional[Dict[str, Any]]
    ):
        """예측적 워밍 스케줄링"""
        try:
            # 신뢰도 임계값 확인
            if pattern.prediction_confidence < self.prediction_params["pattern_threshold"]:
                return
            
            # 다음 접근 시간 예측
            next_access_time = await self._predict_next_access(pattern)
            
            if not next_access_time:
                return
            
            # 워밍 시간 계산 (다음 접근 5분 전)
            warmup_time = next_access_time - timedelta(minutes=5)
            
            # 이미 지난 경우
            if warmup_time <= datetime.utcnow():
                return
            
            # 워밍 작업 생성
            priority = self._calculate_warmup_priority(pattern, data_type)
            
            warmup_task = CacheWarmupTask(
                key=key,
                scheduled_time=warmup_time,
                priority=priority,
                data_loader=loader_name or "default",
                params=loader_params or {}
            )
            
            # 워밍 큐에 추가
            await self._add_to_warmup_queue(warmup_task)
            
        except Exception as e:
            logger.error(f"Error scheduling predictive warmup for {key}: {str(e)}")
    
    async def _predict_next_access(self, pattern: AccessPattern) -> Optional[datetime]:
        """다음 접근 시간 예측"""
        try:
            if pattern.pattern == "periodic":
                # 주기적 패턴 - 평균 간격 기반 예측
                next_time = pattern.last_access + timedelta(seconds=pattern.avg_interval)
                return next_time
            
            elif pattern.pattern == "burst":
                # 버스트 패턴 - 다음 버스트까지 예측
                burst_interval = pattern.avg_interval * self.prediction_params["burst_multiplier"]
                next_time = pattern.last_access + timedelta(seconds=burst_interval)
                return next_time
            
            else:
                # 랜덤 패턴 - 예측 불가
                return None
                
        except Exception as e:
            logger.error(f"Error predicting next access: {str(e)}")
            return None
    
    def _calculate_warmup_priority(self, pattern: AccessPattern, data_type: str) -> int:
        """워밍 우선순위 계산"""
        base_priority = 1
        
        # 빈도에 따른 우선순위
        if pattern.frequency == "high":
            base_priority += 3
        elif pattern.frequency == "medium":
            base_priority += 2
        else:
            base_priority += 1
        
        # 데이터 타입에 따른 우선순위
        if data_type in ["stock_price", "market_data"]:
            base_priority += 2
        elif data_type in ["sentiment", "search"]:
            base_priority += 1
        
        # 신뢰도에 따른 가중치
        confidence_weight = int(pattern.prediction_confidence * 2)
        base_priority += confidence_weight
        
        return base_priority
    
    async def _add_to_warmup_queue(self, task: CacheWarmupTask):
        """워밍 큐에 작업 추가"""
        try:
            # 큐 크기 확인
            if len(self.warmup_queue) >= self.warmup_queue_size:
                # 가장 낮은 우선순위 작업 제거
                self.warmup_queue.sort(key=lambda x: x.priority)
                self.warmup_queue.pop(0)
            
            # 작업 추가
            self.warmup_queue.append(task)
            
            # 우선순위순으로 정렬
            self.warmup_queue.sort(key=lambda x: (x.scheduled_time, -x.priority))
            
        except Exception as e:
            logger.error(f"Error adding to warmup queue: {str(e)}")
    
    async def _warmup_scheduler(self):
        """워밍 스케줄러"""
        while self.running:
            try:
                now = datetime.utcnow()
                
                # 실행할 작업 찾기
                tasks_to_execute = []
                remaining_tasks = []
                
                for task in self.warmup_queue:
                    if task.scheduled_time <= now:
                        tasks_to_execute.append(task)
                    else:
                        remaining_tasks.append(task)
                
                self.warmup_queue = remaining_tasks
                
                # 워밍 작업 실행
                for task in tasks_to_execute:
                    await self._execute_warmup_task(task)
                
                # 1분마다 확인
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in warmup scheduler: {str(e)}")
                await asyncio.sleep(60)
    
    async def _execute_warmup_task(self, task: CacheWarmupTask):
        """워밍 작업 실행"""
        try:
            # 데이터 로더 확인
            if task.data_loader not in self.data_loaders:
                logger.warning(f"Data loader not found for warmup task: {task.data_loader}")
                return
            
            # 이미 캐시에 있는지 확인
            cached_data = await self._get_from_cache(task.key)
            if cached_data:
                logger.debug(f"Cache already exists for warmup task: {task.key}")
                return
            
            # 데이터 로드
            data = await self._load_data(task.data_loader, task.params)
            
            if data:
                # 캐시에 저장
                data_type = task.params.get("data_type", "default")
                ttl = await self._determine_dynamic_ttl(task.key, data_type)
                await self._save_to_cache(task.key, data, ttl)
                
                self.stats.warmup_hits += 1
                logger.info(f"Warmup completed for key: {task.key}")
            else:
                # 재시도 로직
                task.retry_count += 1
                if task.retry_count < task.max_retries:
                    # 5분 후 재시도
                    task.scheduled_time = datetime.utcnow() + timedelta(minutes=5)
                    await self._add_to_warmup_queue(task)
                    logger.warning(f"Warmup failed, retrying for key: {task.key}")
                else:
                    logger.error(f"Warmup failed after max retries for key: {task.key}")
                
        except Exception as e:
            logger.error(f"Error executing warmup task for {task.key}: {str(e)}")
    
    async def _determine_dynamic_ttl(self, key: str, data_type: str) -> int:
        """동적 TTL 결정"""
        try:
            # 기본 TTL
            base_ttl = self.default_ttls.get(data_type, 300)
            
            # 접근 패턴에 따른 TTL 조정
            if key in self.access_patterns:
                pattern = self.access_patterns[key]
                
                if pattern.frequency == "high":
                    ttl_multiplier = 1.5  # 50% 증가
                elif pattern.frequency == "medium":
                    ttl_multiplier = 1.2  # 20% 증가
                else:
                    ttl_multiplier = 0.8  # 20% 감소
                
                base_ttl = int(base_ttl * ttl_multiplier)
            
            return base_ttl
            
        except Exception as e:
            logger.error(f"Error determining TTL for {key}: {str(e)}")
            return self.default_ttls.get(data_type, 300)
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        try:
            if not self.redis_client:
                return None
            
            cached_data = await self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    async def _save_to_cache(self, key: str, data: Any, ttl: int):
        """캐시에 데이터 저장"""
        try:
            if not self.redis_client:
                return
            
            await self.redis_client.setex(key, ttl, json.dumps(data))
            
        except Exception as e:
            logger.error(f"Error saving to cache: {str(e)}")
    
    async def _load_data(self, loader_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """데이터 로드"""
        try:
            if loader_name not in self.data_loaders:
                return None
            
            loader_func = self.data_loaders[loader_name]
            
            if asyncio.iscoroutinefunction(loader_func):
                return await loader_func(**params)
            else:
                # 동기 함수는 스레드 풀에서 실행
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, loader_func, **params)
                
        except Exception as e:
            logger.error(f"Error loading data with {loader_name}: {str(e)}")
            return None
    
    def _update_response_time(self, response_time: float):
        """응답 시간 업데이트"""
        if self.stats.total_requests == 0:
            self.stats.avg_response_time = response_time
        else:
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.total_requests - 1) + response_time) /
                self.stats.total_requests
            )
    
    async def _pattern_analyzer(self):
        """패턴 분석기"""
        while self.running:
            try:
                # 모든 키에 대해 패턴 분석
                for key in list(self.access_history.keys()):
                    await self._analyze_access_pattern(key)
                
                # 10분마다 분석
                await asyncio.sleep(600)
                
            except Exception as e:
                logger.error(f"Error in pattern analyzer: {str(e)}")
                await asyncio.sleep(600)
    
    async def _stats_collector(self):
        """통계 수집기"""
        while self.running:
            try:
                # Redis 메모리 사용량 조회
                if self.redis_client:
                    info = await self.redis_client.info("memory")
                    self.stats.memory_usage = info.get("used_memory", 0)
                
                # 5분마다 수집
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in stats collector: {str(e)}")
                await asyncio.sleep(300)
    
    async def _load_access_patterns(self):
        """접근 패턴 로드"""
        try:
            if not self.redis_client:
                return
            
            # Redis에서 패턴 데이터 로드
            pattern_keys = await self.redis_client.keys("cache:pattern:*")
            
            for key in pattern_keys:
                pattern_data = await self.redis_client.get(key)
                if pattern_data:
                    pattern_dict = json.loads(pattern_data)
                    pattern = AccessPattern(**pattern_dict)
                    
                    # 마지막 접근 시간 파싱
                    pattern.last_access = datetime.fromisoformat(pattern.last_access)
                    
                    self.access_patterns[pattern.key] = pattern
            
            logger.info(f"Loaded {len(self.access_patterns)} access patterns")
            
        except Exception as e:
            logger.error(f"Error loading access patterns: {str(e)}")
    
    async def _save_access_patterns(self):
        """접근 패턴 저장"""
        try:
            if not self.redis_client:
                return
            
            for pattern in self.access_patterns.values():
                pattern_key = f"cache:pattern:{pattern.key}"
                pattern_dict = asdict(pattern)
                pattern_dict["last_access"] = pattern.last_access.isoformat()
                
                await self.redis_client.setex(pattern_key, 86400, json.dumps(pattern_dict))
            
            logger.info(f"Saved {len(self.access_patterns)} access patterns")
            
        except Exception as e:
            logger.error(f"Error saving access patterns: {str(e)}")

# 전역 지능형 캐시 관리자 인스턴스
intelligent_cache_manager = IntelligentCacheManager()