"""
실시간 데이터 수집기 모듈
주기적 데이터 수집, 변환 및 이벤트 발행 기능 제공
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import redis.asyncio as redis
from enum import Enum

from .yahoo_finance_service import yahoo_finance_service, StockData
from .kafka_event_bus import kafka_event_bus, EventType
from .sentiment_service import sentiment_service
from ..models.unified_models import DataSource


class DataSource(Enum):
    """데이터 소스 열거형"""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    REDDIT = "reddit"
    TWITTER = "twitter"
    DISCORD = "discord"


class CollectionStatus(Enum):
    """수집 상태 열거형"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class DataCollectorError(Exception):
    """데이터 수집기 오류"""
    pass


@dataclass
class DataPoint:
    """데이터 포인트 모델"""
    symbol: str
    source: DataSource
    data_type: str
    value: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'symbol': self.symbol,
            'source': self.source.value,
            'data_type': self.data_type,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataPoint':
        """딕셔너리로부터 생성"""
        return cls(
            symbol=data['symbol'],
            source=DataSource(data['source']),
            data_type=data['data_type'],
            value=data['value'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata')
        )


logger = logging.getLogger(__name__)

@dataclass
class CollectionConfig:
    """데이터 수집 설정 모델"""
    symbols: List[str]
    data_types: List[str]
    sources: List[DataSource]
    interval: int = 60  # 초 단위
    batch_size: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 10.0
    
    def __post_init__(self):
        # 기본값 설정을 위한 처리
        # None 값인 경우에만 기본값 설정 (빈 리스트는 그대로 유지)
        if self.symbols is None:
            self.symbols = []
        if self.data_types is None:
            self.data_types = ["stock_price"]
        if self.sources is None:
            self.sources = [DataSource.YAHOO_FINANCE]


@dataclass
class CollectionStats:
    """수집 통계 모델"""
    total_collections: int = 0
    successful_collections: int = 0
    failed_collections: int = 0
    last_collection_time: Optional[datetime] = None
    avg_collection_time: float = 0.0
    active_symbols: int = 0


class RealtimeDataCollector:
    """실시간 데이터 수집기 클래스"""
    
    def __init__(
        self,
        config: CollectionConfig,
        data_sources: Optional[Dict[DataSource, Any]] = None,
        event_bus: Optional[Any] = None
    ):
        self.config = config
        self.data_sources = data_sources or {}
        self.event_bus = event_bus
        
        # 상태 관리
        self.status = CollectionStatus.STOPPED
        self.collection_task: Optional[asyncio.Task] = None
        
        # 통계 정보
        self.total_collections = 0
        self.successful_collections = 0
        self.failed_collections = 0
        self.data_points_collected = 0
        self.start_time: Optional[datetime] = None
        
        # Redis 클라이언트 (호환성을 위해 추가)
        self.redis_client = None
        
        # 로거
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """데이터 수집 시작"""
        if self.status == CollectionStatus.RUNNING:
            return
        
        self.status = CollectionStatus.RUNNING
        self.start_time = datetime.utcnow()
        
        # 수집 루프 시작
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        self.logger.info("Data collection started")
    
    async def stop(self):
        """데이터 수집 중지"""
        if self.status != CollectionStatus.RUNNING:
            return
        
        self.status = CollectionStatus.STOPPED
        
        # 수집 작업 중지
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
            self.collection_task = None
        
        self.logger.info("Data collection stopped")
    
    async def _collection_loop(self):
        """수집 루프"""
        while self.status == CollectionStatus.RUNNING:
            try:
                # 모든 심볼에 대해 데이터 수집
                for symbol in self.config.symbols:
                    if self.status != CollectionStatus.RUNNING:
                        break
                    
                    try:
                        # 데이터 수집
                        data_points = await self._collect_data(
                            symbol, 
                            self.config.data_types, 
                            self.config.sources
                        )
                        
                        # 데이터 포인트 발행
                        if data_points:
                            await self._publish_data_points(data_points)
                            self.data_points_collected += len(data_points)
                            self.successful_collections += 1
                        else:
                            self.failed_collections += 1
                        
                        self.total_collections += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error collecting data for {symbol}: {str(e)}")
                        self.failed_collections += 1
                        self.total_collections += 1
                
                # 대기
                await asyncio.sleep(self.config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in collection loop: {str(e)}")
                await asyncio.sleep(self.config.interval)
    
    async def _collect_data(self, symbol: str, data_types: List[str], sources: List[DataSource]) -> List[DataPoint]:
        """데이터 수집"""
        data_points = []
        
        for source in sources:
            if source not in self.data_sources:
                continue
            
            try:
                # 타임아웃과 함께 데이터 소스에서 데이터 가져오기
                source_data = await asyncio.wait_for(
                    self.data_sources[source].get_realtime_data(symbol, data_types),
                    timeout=self.config.timeout
                )
                
                # 데이터 포인트 생성
                if isinstance(source_data, dict):
                    for data_type in data_types:
                        # 테스트에서 기대하는 값 형식으로 변환
                        if data_type == "stock_price":
                            value = source_data.get("price", 0.0)
                        elif data_type == "volume":
                            value = source_data.get("volume", 0)
                        else:
                            value = source_data.get(data_type, 0.0)
                        
                        data_point = DataPoint(
                            symbol=symbol,
                            source=source,
                            data_type=data_type,
                            value=value,
                            timestamp=datetime.utcnow(),
                            metadata={"source_data": source_data}
                        )
                        data_points.append(data_point)
                else:
                    # 단일 데이터 타입인 경우
                    data_point = DataPoint(
                        symbol=symbol,
                        source=source,
                        data_type=data_types[0] if data_types else "unknown",
                        value=source_data.get("price", 0.0) if isinstance(source_data, dict) else 0.0,
                        timestamp=datetime.utcnow(),
                        metadata={"source_data": source_data}
                    )
                    data_points.append(data_point)
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout collecting data for {symbol} from {source}")
            except Exception as e:
                self.logger.error(f"Error collecting data for {symbol} from {source}: {str(e)}")
        
        return data_points
    
    async def _collect_data_with_retry(self, symbol: str, data_types: List[str], sources: List[DataSource]) -> List[DataPoint]:
        """재시도와 함께 데이터 수집"""
        for attempt in range(self.config.retry_attempts):
            try:
                data_points = await self._collect_data(symbol, data_types, sources)
                if data_points:
                    return data_points
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
        
        return []
    
    async def _publish_data_points(self, data_points: List[DataPoint]):
        """데이터 포인트 발행"""
        if not self.event_bus:
            return
        
        for data_point in data_points:
            try:
                await self.event_bus.publish("data_collected", data_point)
            except Exception as e:
                self.logger.error(f"Error publishing data point: {str(e)}")
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """수집 통계 조회"""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "total_collections": self.total_collections,
            "successful_collections": self.successful_collections,
            "failed_collections": self.failed_collections,
            "success_rate": (
                self.successful_collections / self.total_collections * 100
                if self.total_collections > 0 else 0
            ),
            "data_points_collected": self.data_points_collected,
            "status": self.status.value,
            "uptime_seconds": uptime_seconds
        }
    
    async def update_config(self, new_config: CollectionConfig):
        """설정 업데이트"""
        was_running = self.status == CollectionStatus.RUNNING
        
        # 실행 중이면 중지
        if was_running:
            await self.stop()
        
        # 설정 업데이트
        self.config = new_config
        
        # 실행 중이었으면 다시 시작
        if was_running:
            await self.start()
    
    async def add_symbol(self, symbol: str):
        """심볼 추가"""
        if symbol not in self.config.symbols:
            self.config.symbols.append(symbol)
            self.logger.info(f"Added symbol {symbol} to collection")
    
    async def remove_symbol(self, symbol: str):
        """심볼 제거"""
        if symbol in self.config.symbols:
            self.config.symbols.remove(symbol)
            self.logger.info(f"Removed symbol {symbol} from collection")
    
    async def add_data_type(self, data_type: str):
        """데이터 타입 추가"""
        if data_type not in self.config.data_types:
            self.config.data_types.append(data_type)
    
    async def remove_data_type(self, data_type: str):
        """데이터 타입 제거"""
        if data_type in self.config.data_types:
            self.config.data_types.remove(data_type)
    
    async def get_active_symbols(self) -> List[str]:
        """활성 심볼 조회"""
        return self.config.symbols.copy()
    
    async def get_data_sources_status(self) -> Dict[str, bool]:
        """데이터 소스 상태 조회"""
        status = {}
        for source in self.data_sources:
            try:
                # 데이터 소스 상태 확인
                if hasattr(self.data_sources[source], 'is_healthy'):
                    status[source.value] = await self.data_sources[source].is_healthy()
                else:
                    # 기본적으로 사용 가능으로 간주
                    status[source.value] = True
            except Exception as e:
                self.logger.error(f"Error checking health for {source}: {str(e)}")
                status[source.value] = False
        
        return status
    
    def _validate_config(self, config: CollectionConfig) -> tuple[bool, List[str]]:
        """설정 검증"""
        errors = []
        
        # 심볼 검증
        if not config.symbols:
            errors.append("At least one symbol is required")
        
        # 데이터 타입 검증
        if not config.data_types:
            errors.append("At least one data type is required")
        
        # 간격 검증
        if config.interval <= 0:
            errors.append("Interval must be greater than 0")
        
        return len(errors) == 0, errors


# 전역 실시간 데이터 수집기 인스턴스
realtime_data_collector = RealtimeDataCollector(
    config=CollectionConfig(
        symbols=[],
        data_types=["stock_price"],
        sources=[DataSource.YAHOO_FINANCE]
    )
)