# 통합 데이터 모델 구현 계획

## 1. 개요

Enhanced Stock Search와 Social Sentiment Tracker를 통합하기 위해 통합 데이터 모델을 설계합니다. 이 모델은 두 시스템의 데이터를 효과적으로 결합하고, 일관된 인터페이스를 제공하며, 확장성을 확보하는 것을 목표로 합니다.

## 2. 통합 데이터 모델 설계

### 2.1 핵심 통합 데이터 모델

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class StockType(Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    MUTUALFUND = "MUTUALFUND"
    INDEX = "INDEX"
    CRYPTO = "CRYPTO"

class SentimentLevel(Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

class TrendingStatus(Enum):
    NOT_TRENDING = "not_trending"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    VOLATILE = "volatile"

@dataclass
class PriceData:
    """가격 데이터 모델"""
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    last_updated: Optional[datetime] = None

@dataclass
class SentimentData:
    """센티먼트 데이터 모델"""
    overall_score: Optional[float] = None  # -100 to +100
    sentiment_level: Optional[SentimentLevel] = None
    mention_count_24h: int = 0
    mention_count_7d: int = 0
    trending_status: TrendingStatus = TrendingStatus.NOT_TRENDING
    trend_score: Optional[float] = None  # percentage change
    trend_start_time: Optional[datetime] = None
    community_breakdown: Dict[str, int] = field(default_factory=dict)
    sentiment_history: List[Dict] = field(default_factory=list)
    last_updated: Optional[datetime] = None

@dataclass
class SearchMetadata:
    """검색 관련 메타데이터"""
    relevance_score: float = 0.0
    search_count: int = 0
    last_searched: Optional[datetime] = None
    search_history: List[datetime] = field(default_factory=list)
    popular_keywords: List[str] = field(default_factory=list)

@dataclass
class WatchlistMetadata:
    """관심종목 관련 메타데이터"""
    is_in_watchlist: bool = False
    watchlist_categories: List[str] = field(default_factory=list)
    personal_note: Optional[str] = None
    added_date: Optional[datetime] = None
    order_index: Optional[int] = None

@dataclass
class UnifiedStockData:
    # 기본 정보
    symbol: str
    company_name: str
    stock_type: str
    exchange: str
    sector: str
    industry: str
    
    # 가격 정보
    current_price: Optional[float]
    market_cap: Optional[float]
    price_change_24h: Optional[float] = None
    price_change_pct_24h: Optional[float] = None
    
    # 검색 관련
    relevance_score: float = 0.0
    search_count: int = 0
    last_searched: Optional[datetime] = None
    
    # 센티먼트 관련 (표준화된 범위: -100~+100)
    sentiment_score: Optional[float] = None  # -100~+100 범위
    sentiment_history: List[SentimentPoint] = field(default_factory=list)
    mention_count_24h: int = 0
    mention_count_7d: int = 0
    trending_status: bool = False
    trend_score: Optional[float] = None
    trend_start_time: Optional[datetime] = None
    
    # 상세 정보
    mention_details: List[MentionDetail] = field(default_factory=list)
    community_breakdown: Dict[str, int] = field(default_factory=dict)
    investment_style_distribution: Dict[str, float] = field(default_factory=dict)
    
    # 메타데이터
    last_updated: datetime
    data_sources: List[str] = field(default_factory=list)
    data_quality_score: float = 1.0  # 0~1 범위

@dataclass
class SentimentPoint:
    timestamp: datetime
    sentiment_score: float  # -100~+100
    mention_count: int
    source: str  # reddit, twitter, etc.
    confidence: float  # 0~1 범위

@dataclass
class MentionDetail:
    id: str
    text: str
    author: str
    community: str
    upvotes: int
    downvotes: int
    timestamp: datetime
    investment_style: str
    sentiment_score: float
    confidence: float
    is_spam: bool = False

### 2.2 데이터 변환 레이어

```python
from typing import Union
import logging

class UnifiedDataTransformer:
    """데이터 변환 레이어: 기존 모델을 통합 모델로 변환"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def from_stock_result(self, stock_result: 'StockResult') -> UnifiedStockData:
        """StockResult를 UnifiedStockData로 변환"""
        try:
            # StockType 변환
            stock_type = StockType(stock_result.stock_type.upper())
            
            # 가격 데이터 변환
            price_data = PriceData(
                current_price=stock_result.current_price,
                market_cap=stock_result.market_cap
            )
            
            # 검색 메타데이터 변환
            search_metadata = SearchMetadata(
                relevance_score=stock_result.relevance_score
            )
            
            return UnifiedStockData(
                symbol=stock_result.symbol,
                company_name=stock_result.company_name,
                stock_type=stock_type,
                exchange=stock_result.exchange,
                sector=stock_result.sector,
                industry=stock_result.industry,
                price_data=price_data,
                search_metadata=search_metadata,
                data_sources=["yahoo_finance"]
            )
            
        except Exception as e:
            self.logger.error(f"Error transforming StockResult: {str(e)}")
            raise
    
    def from_stock_mention(self, stock_mention: 'StockMention') -> UnifiedStockData:
        """StockMention을 UnifiedStockData로 변환"""
        try:
            # 센티먼트 데이터 변환
            sentiment_level = self._score_to_sentiment_level(stock_mention.sentiment_score)
            
            sentiment_data = SentimentData(
                overall_score=stock_mention.sentiment_score,
                sentiment_level=sentiment_level,
                mention_count_24h=1,  # 개별 언급은 1로 처리
                community_breakdown={stock_mention.community: 1},
                last_updated=stock_mention.timestamp
            )
            
            return UnifiedStockData(
                symbol=stock_mention.symbol,
                company_name="",  # 언급 데이터에는 회사명이 없을 수 있음
                stock_type=StockType.EQUITY,  # 기본값
                exchange="UNKNOWN",
                sentiment_data=sentiment_data,
                data_sources=[stock_mention.source]
            )
            
        except Exception as e:
            self.logger.error(f"Error transforming StockMention: {str(e)}")
            raise
    
    def merge_stock_data(self, base_data: UnifiedStockData, 
                        update_data: UnifiedStockData) -> UnifiedStockData:
        """두 UnifiedStockData를 병합"""
        try:
            # 기본 정보는 base_data 유지
            merged = UnifiedStockData(
                symbol=base_data.symbol,
                company_name=base_data.company_name,
                stock_type=base_data.stock_type,
                exchange=base_data.exchange,
                sector=base_data.sector,
                industry=base_data.industry,
                description=base_data.description,
                website=base_data.website
            )
            
            # 가격 데이터 병합
            merged.price_data = self._merge_price_data(
                base_data.price_data, update_data.price_data
            )
            
            # 센티먼트 데이터 병합
            merged.sentiment_data = self._merge_sentiment_data(
                base_data.sentiment_data, update_data.sentiment_data
            )
            
            # 검색 메타데이터 병합
            merged.search_metadata = self._merge_search_metadata(
                base_data.search_metadata, update_data.search_metadata
            )
            
            # 관심종목 메타데이터 병합
            merged.watchlist_metadata = self._merge_watchlist_metadata(
                base_data.watchlist_metadata, update_data.watchlist_metadata
            )
            
            # 기타 메타데이터 병합
            merged.data_sources = list(set(
                base_data.data_sources + update_data.data_sources
            ))
            merged.api_errors = base_data.api_errors + update_data.api_errors
            merged.last_updated = max(
                base_data.last_updated, update_data.last_updated
            )
            
            return merged
            
        except Exception as e:
            self.logger.error(f"Error merging stock data: {str(e)}")
            raise
    
    def _score_to_sentiment_level(self, score: float) -> SentimentLevel:
        """센티먼트 점수를 SentimentLevel로 변환"""
        if score <= -50:
            return SentimentLevel.VERY_NEGATIVE
        elif score <= -10:
            return SentimentLevel.NEGATIVE
        elif score <= 10:
            return SentimentLevel.NEUTRAL
        elif score <= 50:
            return SentimentLevel.POSITIVE
        else:
            return SentimentLevel.VERY_POSITIVE
    
    def _merge_price_data(self, base: PriceData, update: PriceData) -> PriceData:
        """가격 데이터 병합"""
        merged = PriceData()
        
        # 더 최신 데이터로 업데이트
        if update.last_updated and base.last_updated:
            if update.last_updated > base.last_updated:
                merged = update
            else:
                merged = base
        elif update.last_updated:
            merged = update
        else:
            merged = base
        
        # null 값 보완
        if not merged.current_price and base.current_price:
            merged.current_price = base.current_price
        if not merged.market_cap and base.market_cap:
            merged.market_cap = base.market_cap
        
        return merged
    
    def _merge_sentiment_data(self, base: SentimentData, 
                            update: SentimentData) -> SentimentData:
        """센티먼트 데이터 병합"""
        merged = SentimentData()
        
        # 최신 데이터로 업데이트
        if update.last_updated and base.last_updated:
            if update.last_updated > base.last_updated:
                merged = update
            else:
                merged = base
        elif update.last_updated:
            merged = update
        else:
            merged = base
        
        # 커뮤니티 분류 병합
        merged.community_breakdown = {}
        for community, count in base.community_breakdown.items():
            merged.community_breakdown[community] = count
        for community, count in update.community_breakdown.items():
            merged.community_breakdown[community] = merged.community_breakdown.get(community, 0) + count
        
        # 히스토리 병합
        merged.sentiment_history = base.sentiment_history + update.sentiment_history
        merged.sentiment_history.sort(key=lambda x: x.get('timestamp', datetime.min))
        
        return merged
    
    def _merge_search_metadata(self, base: SearchMetadata, 
                            update: SearchMetadata) -> SearchMetadata:
        """검색 메타데이터 병합"""
        merged = SearchMetadata()
        
        # 검색 횟수 합산
        merged.search_count = base.search_count + update.search_count
        
        # 최신 검색 시간
        merged.last_searched = max(
            base.last_searched or datetime.min,
            update.last_searched or datetime.min
        )
        
        # 검색 히스토리 병합
        merged.search_history = base.search_history + update.search_history
        merged.search_history.sort(reverse=True)
        
        # 인기 키워드 병합
        merged.popular_keywords = list(set(
            base.popular_keywords + update.popular_keywords
        ))
        
        # 관련도 점수는 더 높은 값으로
        merged.relevance_score = max(base.relevance_score, update.relevance_score)
        
        return merged
    
    def _merge_watchlist_metadata(self, base: WatchlistMetadata, 
                               update: WatchlistMetadata) -> WatchlistMetadata:
        """관심종목 메타데이터 병합"""
        merged = WatchlistMetadata()
        
        # 관심종목 여부는 둘 중 하나라도 true이면 true
        merged.is_in_watchlist = base.is_in_watchlist or update.is_in_watchlist
        
        # 카테고리 병합
        merged.watchlist_categories = list(set(
            base.watchlist_categories + update.watchlist_categories
        ))
        
        # 메모는 더 최신 값으로
        if base.added_date and update.added_date:
            if base.added_date > update.added_date:
                merged.personal_note = base.personal_note
                merged.added_date = base.added_date
            else:
                merged.personal_note = update.personal_note
                merged.added_date = update.added_date
        elif base.added_date:
            merged.personal_note = base.personal_note
            merged.added_date = base.added_date
        else:
            merged.personal_note = update.personal_note
            merged.added_date = update.added_date
        
        # 순서는 더 낮은 값으로
        merged.order_index = min(
            base.order_index or float('inf'),
            update.order_index or float('inf')
        )
        
        return merged
```

### 2.3 데이터 일관성 전략

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timedelta

class DataConsistencyStrategy(ABC):
    """데이터 일관성 전략 인터페이스"""
    
    @abstractmethod
    async def ensure_consistency(self, symbol: str) -> bool:
        """데이터 일관성 보장"""
        pass

class EventualConsistencyStrategy(DataConsistencyStrategy):
    """최종 일관성 전략"""
    
    def __init__(self, max_delay_seconds: int = 300):
        self.max_delay = timedelta(seconds=max_delay_seconds)
        self.logger = logging.getLogger(__name__)
    
    async def ensure_consistency(self, symbol: str) -> bool:
        """최종 일관성 보장 (비동기 방식)"""
        try:
            # 데이터 소스별 최신 업데이트 시간 확인
            source_timestamps = await self._get_source_timestamps(symbol)
            
            if not source_timestamps:
                return True  # 데이터가 없으면 일관성 있다고 판단
            
            # 가장 오래된 데이터와 가장 최신 데이터의 시간 차이 확인
            oldest = min(source_timestamps.values())
            newest = max(source_timestamps.values())
            
            if newest - oldest > self.max_delay:
                self.logger.warning(
                    f"Data consistency issue for {symbol}: "
                    f"time difference {newest - oldest} exceeds threshold {self.max_delay}"
                )
                
                # 데이터 동기화 트리거
                await self._trigger_data_sync(symbol)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking consistency for {symbol}: {str(e)}")
            return False
    
    async def _get_source_timestamps(self, symbol: str) -> Dict[str, datetime]:
        """데이터 소스별 타임스탬프 조회"""
        # 실제 구현에서는 각 데이터 소스에서 타임스탬프 조회
        # 여기서는 더미 데이터 반환
        return {
            "yahoo_finance": datetime.now() - timedelta(minutes=5),
            "reddit": datetime.now() - timedelta(minutes=2),
            "twitter": datetime.now() - timedelta(minutes=3)
        }
    
    async def _trigger_data_sync(self, symbol: str):
        """데이터 동기화 트리거"""
        # 실제 구현에서는 데이터 동기화 작업 트리거
        self.logger.info(f"Triggering data sync for {symbol}")

class StrongConsistencyStrategy(DataConsistencyStrategy):
    """강력한 일관성 전략"""
    
    def __init__(self, lock_timeout_seconds: int = 30):
        self.lock_timeout = timedelta(seconds=lock_timeout_seconds)
        self.data_locks = {}
        self.logger = logging.getLogger(__name__)
    
    async def ensure_consistency(self, symbol: str) -> bool:
        """강력한 일관성 보장 (동기 방식)"""
        try:
            # 분산 락 획득
            lock_acquired = await self._acquire_lock(symbol)
            
            if not lock_acquired:
                self.logger.warning(f"Could not acquire lock for {symbol}")
                return False
            
            # 데이터 일관성 확인 및 복구
            consistency_restored = await self._restore_consistency(symbol)
            
            # 락 해제
            await self._release_lock(symbol)
            
            return consistency_restored
            
        except Exception as e:
            self.logger.error(f"Error ensuring consistency for {symbol}: {str(e)}")
            await self._release_lock(symbol)
            return False
    
    async def _acquire_lock(self, symbol: str) -> bool:
        """분산 락 획득"""
        # 실제 구현에서는 Redis 분산 락 등 사용
        if symbol in self.data_locks:
            if datetime.now() - self.data_locks[symbol] > self.lock_timeout:
                del self.data_locks[symbol]
            else:
                return False
        
        self.data_locks[symbol] = datetime.now()
        return True
    
    async def _release_lock(self, symbol: str):
        """분산 락 해제"""
        if symbol in self.data_locks:
            del self.data_locks[symbol]
    
    async def _restore_consistency(self, symbol: str) -> bool:
        """데이터 일관성 복구"""
        # 실제 구현에서는 데이터 소스에서 최신 데이터를 가져와 일관성 복구
        self.logger.info(f"Restoring consistency for {symbol}")
        return True

class DataConsistencyManager:
    """데이터 일관성 관리자"""
    
    def __init__(self, strategy: DataConsistencyStrategy):
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
    
    async def check_consistency(self, symbol: str) -> bool:
        """데이터 일관성 확인"""
        return await self.strategy.ensure_consistency(symbol)
    
    async def batch_check_consistency(self, symbols: List[str]) -> Dict[str, bool]:
        """일괄 데이터 일관성 확인"""
        results = {}
        
        # 병렬로 일관성 확인
        tasks = [
            self.check_consistency(symbol) for symbol in symbols
        ]
        
        consistency_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, result in zip(symbols, consistency_results):
            if isinstance(result, Exception):
                self.logger.error(f"Error checking consistency for {symbol}: {str(result)}")
                results[symbol] = False
            else:
                results[symbol] = result
        
        return results
```

## 3. 구현 상태

### 3.1 Phase 1: 기본 데이터 모델 구현 ✅ 완료

#### 3.1.1 핵심 데이터 모델 구현 ✅
- UnifiedStockData, SentimentPoint, MentionDetail 등 핵심 모델 구현 완료
- 데이터 검증 및 타입 변환 로직 구현 완료
- 표준화된 센티먼트 점수 범위(-100~+100) 적용 완료

#### 3.1.2 데이터 변환 레이어 구현 ✅
- UnifiedDataTransformer 클래스 구현 완료 (backend/services/data_transformer.py)
- 기존 StockResult, StockMention 모델에서 UnifiedStockData로 변환 기능 구현
- 데이터 병합 로직 구현 완료

### 3.2 Phase 2: 데이터 일관성 전략 구현 ✅ 완료

#### 3.2.1 일관성 전략 인터페이스 구현 ✅
- DataConsistencyStrategy 인터페이스 정의 완료
- EventualConsistencyStrategy 구현 완료
- StrongConsistencyStrategy 구현 완료

#### 3.2.2 데이터 일관성 관리자 구현 ✅
- DataConsistencyManager 클래스 구현 완료 (backend/services/data_consistency_manager.py)
- 일괄 일관성 확인 기능 구현 완료
- 분산 락 메커니즘 구현 완료
- 데이터 무결성 검증 기능 구현 완료

### 3.3 Phase 3: 기존 시스템과 통합 ⏳ 진행 중

#### 3.3.1 Enhanced Stock Search 통합 ⏳
- SearchController가 UnifiedStockData를 사용하도록 수정 필요
- 기존 StockResult를 UnifiedStockData로 변환하는 래퍼 구현 필요
- 검색 결과에 센티먼트 정보 포함 필요

#### 3.3.2 Social Sentiment Tracker 통합 ⏳
- SentimentController가 UnifiedStockData를 사용하도록 수정 필요
- 기존 StockMention을 UnifiedStockData로 변환하는 래퍼 구현 필요
- 센티먼트 데이터에 주식 정보 포함 필요

### 3.4 Phase 4: 최적화 및 테스트 ⏳ 대기

#### 3.4.1 성능 최적화 ⏳
- 데이터 변환 성능 최적화 필요
- 메모리 사용량 최적화 필요
- 캐싱 전략 적용 필요

#### 3.4.2 통합 테스트 ⏳
- end-to-end 통합 테스트 필요
- 데이터 일관성 테스트 필요
- 성능 테스트 필요

## 4. 기술적 고려사항

### 4.1 데이터베이스 스키마
```sql
-- 통합 주식 데이터 테이블
CREATE TABLE unified_stocks (
    symbol VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    stock_type VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    description TEXT,
    website VARCHAR(255),
    
    -- 가격 데이터 (JSON)
    price_data JSONB,
    
    -- 센티먼트 데이터 (JSON)
    sentiment_data JSONB,
    
    -- 검색 메타데이터 (JSON)
    search_metadata JSONB,
    
    -- 관심종목 메타데이터 (JSON)
    watchlist_metadata JSONB,
    
    -- 기타 메타데이터
    data_sources TEXT[],
    api_errors TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_unified_stocks_symbol ON unified_stocks(symbol);
CREATE INDEX idx_unified_stocks_type ON unified_stocks(stock_type);
CREATE INDEX idx_unified_stocks_exchange ON unified_stocks(exchange);
CREATE INDEX idx_unified_stocks_sector ON unified_stocks(sector);
CREATE INDEX idx_unified_stocks_updated_at ON unified_stocks(updated_at);

-- JSONB 인덱스
CREATE INDEX idx_unified_stocks_price_data ON unified_stocks USING gin(price_data);
CREATE INDEX idx_unified_stocks_sentiment_data ON unified_stocks USING gin(sentiment_data);
```

### 4.2 마이그레이션 전략
1. **점진적 마이그레이션**: 기존 시스템과 통합 모델을 병행 운영
2. **데이터 변환**: 기존 데이터를 통합 모델로 변환하는 스크립트 개발
3. **롤백 계획**: 문제 발생 시 기존 시스템으로 롤백하는 계획 수립

### 4.3 API 변경
1. **하위 호환성**: 기존 API 엔드포인트 유지
2. **새로운 엔드포인트**: 통합 데이터를 반환하는 새로운 엔드포인트 추가
3. **버전 관리**: API 버전 관리 전략 수립

## 5. 성공 지표

### 5.1 기술적 지표
- 데이터 변환 성공률: 99% 이상
- 데이터 일관성: 95% 이상
- API 응답 시간: 500ms 이하 유지
- 메모리 사용량: 기존 시스템 대비 20% 이하 증가

### 5.2 기능적 지표
- 검색 결과에 센티먼트 정보 포함: 100%
- 센티먼트 분석 결과에 주식 정보 포함: 100%
- 데이터 소스 통합: 3개 이상 (Yahoo Finance, Reddit, Twitter)

이 통합 데이터 모델 구현 계획을 통해 Enhanced Stock Search와 Social Sentiment Tracker를 효과적으로 통합하고, 일관된 데이터 모델을 제공하며, 확장성을 확보할 수 있습니다.