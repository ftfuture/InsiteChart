# 성능 및 확장성 고려사항

## 성능 목표

### 단계별 성능 목표 (현실적 목표로 재설정)
- **MVP 단계**: API 응답 시간 1500ms 이하 (기존 1000ms에서 50% 증가)
- **베타 단계**: API 응답 시간 1200ms 이하 (기존 700ms에서 71% 증가)
- **정식 버전**: API 응답 시간 800ms 이하 (기존 500ms에서 60% 증가)

### 세부 성능 지표 (현실적 목표로 재설정)
- **API 응답 시간**: 90%의 요청이 단계별 목표 시간 내 응답 (기존 95%에서 5% 감소)
- **데이터베이스 쿼리**: 90%의 쿼리가 300ms 이내 완료 (기존 95%에서 5% 감소, 200ms에서 50% 증가)
- **캐시 응답 시간**: 90%의 캐시 요청이 100ms 이내 응답 (기존 95%에서 5% 감소, 50ms에서 100% 증가)
- **외부 API 호출**: 85%의 외부 API 호출이 500ms 이내 완료 (기존 95%에서 10% 감소, 300ms에서 67% 증가)

### 성능 목표 재설정 근거
1. **외부 API 의존성**: 야후 파이낸스, Reddit, Twitter 등 외부 API 응답 시간 예측 불가
2. **데이터 복잡성**: 센티먼트 분석, 상관관계 계산 등 복잡한 처리 로직
3. **인프라 제약**: 클라우드 리소스 비용과 성능 간의 트레이드오프
4. **개발 리소스**: 최적화 작업에 필요한 개발 시간 현실적 고려
5. **단계적 개선**: 초기에는 기능 안정화, 후반에는 성능 최적화 집중


## 1. 성능 최적화 전략

### 1.1 데이터베이스 최적화

#### 1.1.1 PostgreSQL 성능 튜닝
```sql
-- PostgreSQL 설정 최적화 (postgresql.conf)

# 메모리 설정
shared_buffers = 256MB                    # 전체 메모리의 25%
effective_cache_size = 1GB                 # 전체 메모리의 75%
work_mem = 4MB                             # 정렬 및 해시 작업 메모리
maintenance_work_mem = 64MB                # 유지보수 작업 메모리

# 연결 설정
max_connections = 100                      # 최대 연결 수
shared_preload_libraries = 'pg_stat_statements'  # 성능 모니터링 라이브러리

# WAL 설정
wal_buffers = 16MB                         # WAL 버퍼
checkpoint_completion_target = 0.9         # 체크포인트 완료 목표
wal_writer_delay = 200ms                   # WAL 작성자 지연

# 쿼리 최적화
random_page_cost = 1.1                     # SSD 환경에 맞춘 비용
effective_io_concurrency = 200             # SSD 동시 I/O 수

# 로그 설정
log_min_duration_statement = 1000          # 1초 이상 쿼리 로깅
log_checkpoints = on                       # 체크포인트 로깅
log_connections = on                       # 연결 로깅
log_disconnections = on                    # 연결 해제 로깅
```

#### 1.1.2 인덱스 전략
```sql
-- 주식 데이터 인덱스
CREATE INDEX CONCURRENTLY idx_stocks_symbol ON stocks(symbol);
CREATE INDEX CONCURRENTLY idx_stocks_exchange ON stocks(exchange);
CREATE INDEX CONCURRENTLY idx_stocks_sector ON stocks(sector);

-- 가격 데이터 인덱스 (TimescaleDB 하이퍼테이블)
CREATE INDEX CONCURRENTLY idx_stock_prices_symbol_time 
ON stock_prices (symbol, "time" DESC);

-- 센티먼트 데이터 인덱스
CREATE INDEX CONCURRENTLY idx_sentiment_symbol_time 
ON sentiment_data (symbol, "timestamp" DESC);

-- 언급 데이터 인덱스
CREATE INDEX CONCURRENTLY idx_mentions_symbol_source_time 
ON stock_mentions (symbol, source, "timestamp" DESC);

-- 사용자 활동 인덱스
CREATE INDEX CONCURRENTLY idx_user_activities_user_time 
ON user_activities (user_id, "timestamp" DESC);

-- 복합 인덱스 (자주 함께 조회되는 필드)
CREATE INDEX CONCURRENTLY idx_stock_mentions_composite 
ON stock_mentions (symbol, "timestamp" DESC, source);

-- 부분 인덱스 (특정 조건만)
CREATE INDEX CONCURRENTLY idx_active_users 
ON users (id) WHERE is_active = true;

-- 함수 기반 인덱스
CREATE INDEX CONCURRENTLY idx_mentions_text_search 
ON stock_mentions USING gin(to_tsvector('english', text));
```

#### 1.1.3 쿼리 최적화
```sql
-- 파티셔닝을 활용한 대용량 데이터 조회
EXPLAIN (ANALYZE, BUFFERS) 
SELECT symbol, close, volume 
FROM stock_prices 
WHERE "time" >= NOW() - INTERVAL '30 days'
AND symbol = 'AAPL'
ORDER BY "time" DESC;

-- CTE(Common Table Expression)를 활용한 복잡 쿼리 최적화
WITH recent_mentions AS (
  SELECT 
    symbol,
    COUNT(*) as mention_count,
    AVG(sentiment_score) as avg_sentiment,
    "timestamp"::date as mention_date
  FROM stock_mentions 
  WHERE "timestamp" >= NOW() - INTERVAL '7 days'
  GROUP BY symbol, "timestamp"::date
),
daily_price_changes AS (
  SELECT 
    symbol,
    "timestamp"::date as price_date,
    (close - LAG(close) OVER (PARTITION BY symbol ORDER BY "timestamp")) / LAG(close) OVER (PARTITION BY symbol ORDER BY "timestamp") as price_change
  FROM stock_prices
  WHERE "timestamp" >= NOW() - INTERVAL '7 days'
)
SELECT 
  rm.symbol,
  rm.mention_date,
  rm.mention_count,
  rm.avg_sentiment,
  dpc.price_change
FROM recent_mentions rm
LEFT JOIN daily_price_changes dpc ON rm.symbol = dpc.symbol AND rm.mention_date = dpc.price_date
WHERE rm.mention_count > 10
ORDER BY rm.mention_count DESC;

-- 윈도우 함수를 활용한 순위 계산 최적화
SELECT 
  symbol,
  mention_count,
  sentiment_score,
  RANK() OVER (ORDER BY mention_count DESC) as mention_rank,
  RANK() OVER (ORDER BY sentiment_score DESC) as sentiment_rank
FROM (
  SELECT 
    symbol,
    COUNT(*) as mention_count,
    AVG(sentiment_score) as sentiment_score
  FROM stock_mentions
  WHERE "timestamp" >= NOW() - INTERVAL '24 hours'
  GROUP BY symbol
) ranked_data
WHERE mention_count > 5
ORDER BY mention_rank;
```

### 1.2 캐싱 전략

#### 1.2.1 Redis 캐싱 아키텍처
```python
# cache/redis_manager.py
import json
import pickle
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

class RedisCacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
        
        # 캐시 설정
        self.default_ttl = 300  # 5분
        self.long_ttl = 3600    # 1시간
        self.short_ttl = 60     # 1분
        
        # 캐시 키 접두사
        self.key_prefixes = {
            'stock': 'stock:',
            'user': 'user:',
            'sentiment': 'sentiment:',
            'mentions': 'mentions:',
            'trending': 'trending:'
        }
    
    def _generate_cache_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """캐시 키 생성"""
        # 기본 키
        cache_key = f"{self.key_prefixes.get(prefix, prefix)}{identifier}"
        
        # 추가 파라미터가 있는 경우 해시 추가
        if kwargs:
            params_str = json.dumps(kwargs, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            cache_key = f"{cache_key}:{params_hash}"
        
        return cache_key
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        try:
            data = await self.redis.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """캐시에 데이터 저장"""
        try:
            ttl = ttl or self.default_ttl
            serialized_data = pickle.dumps(value)
            await self.redis.setex(key, ttl, serialized_data)
            return True
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시 데이터 삭제"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """패턴에 맞는 캐시 데이터 삭제"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            self.logger.error(f"Cache invalidate pattern error: {str(e)}")
            return 0
    
    async def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """주식 데이터 캐시 조회"""
        cache_key = self._generate_cache_key('stock', symbol)
        return await self.get(cache_key)
    
    async def set_stock_data(self, symbol: str, data: Dict, ttl: int = None) -> bool:
        """주식 데이터 캐시 저장"""
        cache_key = self._generate_cache_key('stock', symbol)
        return await self.set(cache_key, data, ttl or self.short_ttl)
    
    async def get_user_session(self, user_id: str) -> Optional[Dict]:
        """사용자 세션 캐시 조회"""
        cache_key = self._generate_cache_key('user', f"session:{user_id}")
        return await self.get(cache_key)
    
    async def set_user_session(self, user_id: str, session_data: Dict) -> bool:
        """사용자 세션 캐시 저장"""
        cache_key = self._generate_cache_key('user', f"session:{user_id}")
        return await self.set(cache_key, session_data, self.long_ttl)
    
    async def get_trending_stocks(self) -> Optional[List[Dict]]:
        """트렌딩 주식 캐시 조회"""
        cache_key = self._generate_cache_key('trending', 'stocks')
        return await self.get(cache_key)
    
    async def set_trending_stocks(self, stocks: List[Dict]) -> bool:
        """트렌딩 주식 캐시 저장"""
        cache_key = self._generate_cache_key('trending', 'stocks')
        return await self.set(cache_key, stocks, self.short_ttl)
    
    async def get_sentiment_data(self, symbol: str, timeframe: str = '24h') -> Optional[Dict]:
        """센티먼트 데이터 캐시 조회"""
        cache_key = self._generate_cache_key('sentiment', symbol, timeframe=timeframe)
        return await self.get(cache_key)
    
    async def set_sentiment_data(self, symbol: str, sentiment_data: Dict, 
                                timeframe: str = '24h') -> bool:
        """센티먼트 데이터 캐시 저장"""
        cache_key = self._generate_cache_key('sentiment', symbol, timeframe=timeframe)
        return await self.set(cache_key, sentiment_data, self.short_ttl)
    
    async def get_mentions_count(self, symbol: str, timeframe: str = '24h') -> Optional[int]:
        """언급 횟수 캐시 조회"""
        cache_key = self._generate_cache_key('mentions', f"count:{symbol}", timeframe=timeframe)
        return await self.get(cache_key)
    
    async def increment_mentions_count(self, symbol: str, timeframe: str = '24h') -> int:
        """언급 횟수 증가"""
        cache_key = self._generate_cache_key('mentions', f"count:{symbol}", timeframe=timeframe)
        try:
            count = await self.redis.incr(cache_key)
            # TTL 설정 (첫 설정 시에만)
            ttl = await self.redis.ttl(cache_key)
            if ttl == -1:  # TTL이 설정되지 않은 경우
                await self.redis.expire(cache_key, self.short_ttl)
            return count
        except Exception as e:
            self.logger.error(f"Increment mentions count error: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict:
        """캐시 통계 정보"""
        try:
            info = await self.redis.info()
            keyspace_info = await self.redis.info('keyspace')
            
            return {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'total_connections_received': info.get('total_connections_received', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
                'connected_clients': info.get('connected_clients', 0),
                'total_keys': sum(db.get('keys', 0) for db in keyspace_info.values()),
                'databases': len(keyspace_info)
            }
        except Exception as e:
            self.logger.error(f"Cache stats error: {str(e)}")
            return {}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """캐시 적중률 계산"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        
        if hits + misses == 0:
            return 0.0
        
        return (hits / (hits + misses)) * 100
    
    async def warm_up_cache(self) -> bool:
        """캐시 워밍업"""
        try:
            # 인기 주식 데이터 미리 로드
            popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
            
            for symbol in popular_symbols:
                # 실제 구현에서는 데이터베이스에서 조회하여 캐시에 저장
                # 여기서는 더미 데이터 사용
                stock_data = {
                    'symbol': symbol,
                    'price': 100.0,
                    'change': 1.5,
                    'change_percent': 1.5,
                    'timestamp': datetime.now().isoformat()
                }
                await self.set_stock_data(symbol, stock_data)
            
            self.logger.info("Cache warmed up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Cache warm up error: {str(e)}")
            return False
```

#### 1.2.2 다단계 캐싱 전략
```python
# cache/multi_level_cache.py
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import logging

class MultiLevelCache:
    def __init__(self, l1_cache, l2_cache, l3_cache=None):
        self.l1_cache = l1_cache  # 메모리 캐시 (가장 빠름)
        self.l2_cache = l2_cache  # Redis 캐시 (중간)
        self.l3_cache = l3_cache  # 데이터베이스 쿼리 캐시 (가장 느림)
        self.logger = logging.getLogger(__name__)
    
    async def get(self, key: str) -> Optional[Any]:
        """다단계 캐시에서 데이터 조회"""
        # L1 캐시 확인
        data = await self.l1_cache.get(key)
        if data is not None:
            self.logger.debug(f"Cache hit: L1 for key {key}")
            return data
        
        # L2 캐시 확인
        data = await self.l2_cache.get(key)
        if data is not None:
            self.logger.debug(f"Cache hit: L2 for key {key}")
            # L1 캐시에 저장
            await self.l1_cache.set(key, data)
            return data
        
        # L3 캐시 확인 (있는 경우)
        if self.l3_cache:
            data = await self.l3_cache.get(key)
            if data is not None:
                self.logger.debug(f"Cache hit: L3 for key {key}")
                # L2 및 L1 캐시에 저장
                await self.l2_cache.set(key, data)
                await self.l1_cache.set(key, data)
                return data
        
        self.logger.debug(f"Cache miss for key {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """다단계 캐시에 데이터 저장"""
        success = True
        
        # 모든 레벨에 저장
        try:
            await self.l1_cache.set(key, value, ttl)
        except Exception as e:
            self.logger.error(f"L1 cache set error: {str(e)}")
            success = False
        
        try:
            await self.l2_cache.set(key, value, ttl)
        except Exception as e:
            self.logger.error(f"L2 cache set error: {str(e)}")
            success = False
        
        if self.l3_cache:
            try:
                await self.l3_cache.set(key, value, ttl)
            except Exception as e:
                self.logger.error(f"L3 cache set error: {str(e)}")
                success = False
        
        return success
    
    async def invalidate(self, key: str) -> bool:
        """다단계 캐시 데이터 무효화"""
        success = True
        
        try:
            await self.l1_cache.delete(key)
        except Exception as e:
            self.logger.error(f"L1 cache delete error: {str(e)}")
            success = False
        
        try:
            await self.l2_cache.delete(key)
        except Exception as e:
            self.logger.error(f"L2 cache delete error: {str(e)}")
            success = False
        
        if self.l3_cache:
            try:
                await self.l3_cache.delete(key)
            except Exception as e:
                self.logger.error(f"L3 cache delete error: {str(e)}")
                success = False
        
        return success
    
    async def get_cache_stats(self) -> Dict:
        """캐시 통계 정보"""
        stats = {
            'l1': await self.l1_cache.get_stats() if hasattr(self.l1_cache, 'get_stats') else {},
            'l2': await self.l2_cache.get_stats() if hasattr(self.l2_cache, 'get_stats') else {},
            'l3': await self.l3_cache.get_stats() if self.l3_cache and hasattr(self.l3_cache, 'get_stats') else {}
        }
        
        return stats

# L1 캐시 (메모리)
class MemoryCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
        self.logger = logging.getLogger(__name__)
    
    async def get(self, key: str) -> Optional[Any]:
        """메모리 캐시 조회"""
        if key in self.cache:
            self.access_times[key] = datetime.now()
            return self.cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """메모리 캐시 저장"""
        try:
            # 최대 크기 확인
            if len(self.cache) >= self.max_size and key not in self.cache:
                # LRU(Least Recently Used) 기반 삭제
                self._evict_lru()
            
            self.cache[key] = value
            self.access_times[key] = datetime.now()
            return True
        except Exception as e:
            self.logger.error(f"Memory cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """메모리 캐시 삭제"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            return True
        return False
    
    def _evict_lru(self):
        """LRU 기반 캐시 항목 삭제"""
        if not self.access_times:
            return
        
        # 가장 오래된 항목 찾기
        oldest_key = min(self.access_times, key=self.access_times.get)
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    async def get_stats(self) -> Dict:
        """메모리 캐시 통계"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'usage_percent': (len(self.cache) / self.max_size) * 100
        }
```

### 1.3 API 성능 최적화

#### 1.3.1 비동기 API 처리
```python
# api/async_handlers.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 비동기 작업 큐
class AsyncTaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.workers = []
        self.logger = logging.getLogger(__name__)
    
    async def start_workers(self, num_workers: int = 5):
        """작업자 시작"""
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
    
    async def stop_workers(self):
        """작업자 종료"""
        # 큐에 종료 신호 전송
        for _ in self.workers:
            await self.queue.put(None)
        
        # 작업자 종료 대기
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
    
    async def add_task(self, coro):
        """작업 추가"""
        await self.queue.put(coro)
    
    async def _worker(self, name: str):
        """작업자 처리"""
        self.logger.info(f"Worker {name} started")
        
        while True:
            task = await self.queue.get()
            
            # 종료 신호 확인
            if task is None:
                self.logger.info(f"Worker {name} stopping")
                break
            
            try:
                await task
            except Exception as e:
                self.logger.error(f"Worker {name} error: {str(e)}")
            finally:
                self.queue.task_done()
        
        self.logger.info(f"Worker {name} stopped")

# API 애플리케이션 설정
task_queue = AsyncTaskQueue()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    # 시작 시 작업자 시작
    await task_queue.start_workers()
    yield
    # 종료 시 작업자 종료
    await task_queue.stop_workers()

app = FastAPI(
    title="InsiteChart API",
    description="Stock Search and Social Sentiment Tracker API",
    version="1.0.0",
    lifespan=lifespan
)

# 미들웨어 추가
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 비동기 API 엔드포인트
@app.get("/api/v1/stocks/{symbol}/details")
async def get_stock_details(symbol: str, background_tasks: BackgroundTasks):
    """주식 상세 정보 조회 (비동기 처리)"""
    try:
        # 캐시 확인
        cached_data = await cache_manager.get_stock_data(symbol)
        
        if cached_data:
            return cached_data
        
        # 비동기 작업으로 데이터 로드
        task = asyncio.create_task(load_stock_data_async(symbol))
        data = await asyncio.wait_for(task, timeout=10.0)
        
        # 백그라운드에서 캐시 업데이트
        background_tasks.add_task(update_stock_cache, symbol, data)
        
        return data
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def load_stock_data_async(symbol: str) -> Dict:
    """비동기 주식 데이터 로드"""
    # 여러 API 병렬 호출
    tasks = [
        yahoo_client.get_stock_info(symbol),
        reddit_client.get_mentions_for_symbol(symbol, timeframe="24h"),
        twitter_client.get_mentions_for_symbol(symbol, timeframe="24h")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    stock_info = results[0] if not isinstance(results[0], Exception) else {}
    reddit_mentions = results[1] if not isinstance(results[1], Exception) else []
    twitter_mentions = results[2] if not isinstance(results[2], Exception) else []
    
    # 데이터 결합
    combined_data = {
        'symbol': symbol,
        'stock_info': stock_info,
        'social_mentions': {
            'reddit': reddit_mentions,
            'twitter': twitter_mentions
        },
        'last_updated': datetime.now().isoformat()
    }
    
    return combined_data

async def update_stock_cache(symbol: str, data: Dict):
    """주식 데이터 캐시 업데이트 (백그라운드 작업)"""
    try:
        await cache_manager.set_stock_data(symbol, data)
    except Exception as e:
        logger.error(f"Cache update error for {symbol}: {str(e)}")

# 배치 API 엔드포인트
@app.post("/api/v1/stocks/batch")
async def get_batch_stocks(symbols: List[str], background_tasks: BackgroundTasks):
    """여러 주식 정보 일괄 조회"""
    try:
        # 병렬 처리
        tasks = [load_stock_data_async(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 결합
        batch_data = {}
        for i, symbol in enumerate(symbols):
            if not isinstance(results[i], Exception):
                batch_data[symbol] = results[i]
            else:
                batch_data[symbol] = {'error': str(results[i])}
        
        # 백그라운드에서 캐시 업데이트
        for symbol, data in batch_data.items():
            if 'error' not in data:
                background_tasks.add_task(update_stock_cache, symbol, data)
        
        return batch_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 2. 확장성 전략

### 2.1 수평적 확장

#### 2.1.1 마이크로서비스 스케일링
```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  # API 게이트웨이 (로드 밸런싱)
  api-gateway:
    image: kong:latest
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /kong/declarative/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
    volumes:
      - ./kong/kong.yml:/kong/declarative/kong.yml
    ports:
      - "8000:8000"
      - "8001:8001"
    networks:
      - app-network

  # 주식 검색 서비스 (확장 가능)
  stock-search-service:
    build: ./services/stock-search
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq
    networks:
      - app-network
    deploy:
      replicas: 3  # 3개 인스턴스로 확장
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  # 소셜 센티먼트 서비스 (확장 가능)
  sentiment-service:
    build: ./services/sentiment
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq
    networks:
      - app-network
    deploy:
      replicas: 2  # 2개 인스턴스로 확장
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  # 데이터 수집 서비스 (확장 가능)
  data-collection-service:
    build: ./services/data-collection
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq
    networks:
      - app-network
    deploy:
      replicas: 2  # 2개 인스턴스로 확장
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  # 데이터베이스 (읽기 복제본)
  postgres-replica:
    image: timescale/timescaledb:latest-pg14
    environment:
      - POSTGRES_DB=insitechart
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_MASTER_SERVICE=postgres
    depends_on:
      - postgres
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

#### 2.1.2 데이터베이스 샤딩
```python
# database/sharding_manager.py
import asyncio
from typing import Dict, List, Optional, Any
import hashlib
import logging

class DatabaseShardingManager:
    def __init__(self, shard_configs: List[Dict]):
        self.shard_configs = shard_configs
        self.shards = {}
        self.logger = logging.getLogger(__name__)
        
        # 샤드 연결 초기화
        asyncio.create_task(self._initialize_shards())
    
    async def _initialize_shards(self):
        """샤드 연결 초기화"""
        for config in self.shard_configs:
            shard_id = config['shard_id']
            connection_string = config['connection_string']
            
            # 실제 구현에서는 데이터베이스 연결 풀 생성
            self.shards[shard_id] = {
                'connection_string': connection_string,
                'connection': None  # 실제 연결 객체
            }
            
            self.logger.info(f"Initialized shard {shard_id}")
    
    def _get_shard_id(self, key: str) -> str:
        """키에 해당하는 샤드 ID 계산"""
        # 해시 기반 샤딩
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        shard_index = hash_value % len(self.shard_configs)
        return self.shard_configs[shard_index]['shard_id']
    
    async def execute_query(self, query: str, params: Dict = None, shard_key: str = None):
        """쿼리 실행 (샤드 선택)"""
        if shard_key:
            # 특정 샤드에 쿼리 실행
            shard_id = self._get_shard_id(shard_key)
            return await self._execute_on_shard(shard_id, query, params)
        else:
            # 모든 샤드에 쿼리 실행 (결과 병합)
            results = await asyncio.gather(*[
                self._execute_on_shard(shard_id, query, params)
                for shard_id in self.shards
            ], return_exceptions=True)
            
            # 결과 병합
            return self._merge_results(results)
    
    async def _execute_on_shard(self, shard_id: str, query: str, params: Dict = None):
        """특정 샤드에 쿼리 실행"""
        shard = self.shards.get(shard_id)
        if not shard:
            raise ValueError(f"Shard {shard_id} not found")
        
        # 실제 구현에서는 데이터베이스 연결을 통해 쿼리 실행
        self.logger.debug(f"Executing query on shard {shard_id}: {query}")
        
        # 더미 결과 반환
        return {'shard_id': shard_id, 'data': []}
    
    def _merge_results(self, results: List[Any]) -> Any:
        """샤드 결과 병합"""
        merged_data = []
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Shard query error: {str(result)}")
                continue
            
            if isinstance(result, dict) and 'data' in result:
                merged_data.extend(result['data'])
        
        return {'merged_data': merged_data}
    
    async def insert_data(self, table: str, data: Dict, shard_key: str):
        """데이터 삽입 (샤드 선택)"""
        shard_id = self._get_shard_id(shard_key)
        
        # 실제 구현에서는 해당 샤드에 데이터 삽입
        self.logger.info(f"Inserting data into shard {shard_id}")
        
        return True
    
    async def get_shard_stats(self) -> Dict:
        """샤드 통계 정보"""
        stats = {}
        
        for shard_id, shard in self.shards.items():
            # 실제 구현에서는 샤드별 통계 조회
            stats[shard_id] = {
                'connection_status': 'connected',  # 실제로는 연결 상태 확인
                'data_size': 'unknown',           # 실제로는 데이터 크기 조회
                'query_count': 0                  # 실제로는 쿼리 수 카운트
            }
        
        return stats

# 샤드 설정 예시
shard_configs = [
    {
        'shard_id': 'shard_0',
        'connection_string': 'postgresql://user:password@shard0:5432/insitechart'
    },
    {
        'shard_id': 'shard_1',
        'connection_string': 'postgresql://user:password@shard1:5432/insitechart'
    },
    {
        'shard_id': 'shard_2',
        'connection_string': 'postgresql://user:password@shard2:5432/insitechart'
    }
]
```

### 2.2 오토 스케일링

#### 2.2.1 Kubernetes 오토 스케일링 설정
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stock-search-hpa
  namespace: insitechart
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stock-search-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentiment-service-hpa
  namespace: insitechart
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentiment-service
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: data-collection-hpa
  namespace: insitechart
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-collection-service
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 2.2.2 클라우드 오토 스케일링 정책
```python
# cloud/auto_scaling_manager.py
import asyncio
import boto3
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

class CloudAutoScalingManager:
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        self.autoscaling_client = boto3.client('autoscaling', region_name=region)
        self.logger = logging.getLogger(__name__)
        
        # 오토 스케일링 그룹 이름
        self.asg_names = {
            'stock-search': 'insitechart-stock-search-asg',
            'sentiment': 'insitechart-sentiment-asg',
            'data-collection': 'insitechart-data-collection-asg'
        }
    
    async def setup_auto_scaling(self):
        """오토 스케일링 설정"""
        for service_name, asg_name in self.asg_names.items():
            await self._setup_service_auto_scaling(service_name, asg_name)
    
    async def _setup_service_auto_scaling(self, service_name: str, asg_name: str):
        """서비스별 오토 스케일링 설정"""
        try:
            # CPU 사용률 기반 스케일링 정책
            await self._create_cpu_scaling_policy(asg_name, service_name)
            
            # 메모리 사용률 기반 스케일링 정책
            await self._create_memory_scaling_policy(asg_name, service_name)
            
            # 커스텀 메트릭 기반 스케일링 정책
            await self._create_custom_metrics_scaling_policy(asg_name, service_name)
            
            self.logger.info(f"Auto scaling setup completed for {service_name}")
            
        except Exception as e:
            self.logger.error(f"Auto scaling setup error for {service_name}: {str(e)}")
    
    async def _create_cpu_scaling_policy(self, asg_name: str, service_name: str):
        """CPU 사용률 기반 스케일링 정책"""
        policy_name = f"{service_name}-cpu-scaling-policy"
        
        # 스케일아웃 정책
        self.autoscaling_client.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=f"{policy_name}-scale-out",
            PolicyType='SimpleScaling',
            AdjustmentType='ChangeInCapacity',
            ScalingAdjustment=1,  # 1개 인스턴스 추가
            Cooldown=300  # 5분 쿨다운
        )
        
        # 스케일인 정책
        self.autoscaling_client.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=f"{policy_name}-scale-in",
            PolicyType='SimpleScaling',
            AdjustmentType='ChangeInCapacity',
            ScalingAdjustment=-1,  # 1개 인스턴스 제거
            Cooldown=600  # 10분 쿨다운
        )
        
        # CloudWatch 알람 설정
        self.cloudwatch_client.put_metric_alarm(
            AlarmName=f"{service_name}-high-cpu",
            AlarmDescription='High CPU usage',
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Statistic='Average',
            Period=300,  # 5분
            EvaluationPeriods=2,  # 2개 기간
            Threshold=70.0,  # 70%
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=[
                self.autoscaling_client.describe_policies(
                    AutoScalingGroupName=asg_name,
                    PolicyNames=[f"{policy_name}-scale-out"]
                )['ScalingPolicies'][0]['PolicyARN']
            ]
        )
        
        self.cloudwatch_client.put_metric_alarm(
            AlarmName=f"{service_name}-low-cpu",
            AlarmDescription='Low CPU usage',
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Statistic='Average',
            Period=300,  # 5분
            EvaluationPeriods=3,  # 3개 기간
            Threshold=30.0,  # 30%
            ComparisonOperator='LessThanThreshold',
            AlarmActions=[
                self.autoscaling_client.describe_policies(
                    AutoScalingGroupName=asg_name,
                    PolicyNames=[f"{policy_name}-scale-in"]
                )['ScalingPolicies'][0]['PolicyARN']
            ]
        )
    
    async def _create_memory_scaling_policy(self, asg_name: str, service_name: str):
        """메모리 사용률 기반 스케일링 정책"""
        policy_name = f"{service_name}-memory-scaling-policy"
        
        # 스케일아웃 정책
        self.autoscaling_client.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=f"{policy_name}-scale-out",
            PolicyType='SimpleScaling',
            AdjustmentType='ChangeInCapacity',
            ScalingAdjustment=1,  # 1개 인스턴스 추가
            Cooldown=300  # 5분 쿨다운
        )
        
        # CloudWatch 알람 설정
        self.cloudwatch_client.put_metric_alarm(
            AlarmName=f"{service_name}-high-memory",
            AlarmDescription='High memory usage',
            MetricName='MemoryUtilization',
            Namespace='System/Linux',
            Statistic='Average',
            Period=300,  # 5분
            EvaluationPeriods=2,  # 2개 기간
            Threshold=80.0,  # 80%
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=[
                self.autoscaling_client.describe_policies(
                    AutoScalingGroupName=asg_name,
                    PolicyNames=[f"{policy_name}-scale-out"]
                )['ScalingPolicies'][0]['PolicyARN']
            ]
        )
    
    async def _create_custom_metrics_scaling_policy(self, asg_name: str, service_name: str):
        """커스텀 메트릭 기반 스케일링 정책"""
        policy_name = f"{service_name}-custom-scaling-policy"
        
        # 요청 큐 길이 기반 스케일링
        self.autoscaling_client.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=f"{policy_name}-queue-scale-out",
            PolicyType='SimpleScaling',
            AdjustmentType='ChangeInCapacity',
            ScalingAdjustment=2,  # 2개 인스턴스 추가
            Cooldown=180  # 3분 쿨다운
        )
        
        # CloudWatch 커스텀 메트릭 알람
        self.cloudwatch_client.put_metric_alarm(
            AlarmName=f"{service_name}-high-queue-length",
            AlarmDescription='High request queue length',
            MetricName='RequestQueueLength',
            Namespace='InsiteChart/Application',
            Statistic='Average',
            Period=60,  # 1분
            EvaluationPeriods=1,  # 1개 기간
            Threshold=100.0,  # 100개 요청
            ComparisonOperator='GreaterThanThreshold',
            AlarmActions=[
                self.autoscaling_client.describe_policies(
                    AutoScalingGroupName=asg_name,
                    PolicyNames=[f"{policy_name}-queue-scale-out"]
                )['ScalingPolicies'][0]['PolicyARN']
            ]
        )
    
    async def get_scaling_activities(self, asg_name: str, hours: int = 24) -> List[Dict]:
        """스케일링 활동 기록 조회"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            response = self.autoscaling_client.describe_scaling_activities(
                AutoScalingGroupName=asg_name,
                StartTime=start_time,
                EndTime=end_time
            )
            
            return response['Activities']
            
        except Exception as e:
            self.logger.error(f"Failed to get scaling activities: {str(e)}")
            return []
    
    async def get_asg_metrics(self, asg_name: str) -> Dict:
        """오토 스케일링 그룹 메트릭 조회"""
        try:
            # ASG 정보
            asg_response = self.autoscaling_client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
            
            if not asg_response['AutoScalingGroups']:
                return {}
            
            asg = asg_response['AutoScalingGroups'][0]
            
            # CloudWatch 메트릭
            cpu_metrics = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[
                    {
                        'Name': 'AutoScalingGroupName',
                        'Value': asg_name
                    }
                ],
                StartTime=datetime.now() - timedelta(hours=1),
                EndTime=datetime.now(),
                Period=300,  # 5분
                Statistics=['Average']
            )
            
            # 메트릭 평균 계산
            avg_cpu = 0
            if cpu_metrics['Datapoints']:
                avg_cpu = sum(dp['Average'] for dp in cpu_metrics['Datapoints']) / len(cpu_metrics['Datapoints'])
            
            return {
                'asg_name': asg_name,
                'desired_capacity': asg['DesiredCapacity'],
                'min_size': asg['MinSize'],
                'max_size': asg['MaxSize'],
                'current_capacity': len(asg['Instances']),
                'instances': [
                    {
                        'instance_id': instance['InstanceId'],
                        'instance_type': instance['InstanceType'],
                        'lifecycle_state': instance['LifecycleState'],
                        'health_status': instance['HealthStatus']
                    }
                    for instance in asg['Instances']
                ],
                'average_cpu_utilization': round(avg_cpu, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get ASG metrics: {str(e)}")
            return {}
```

## 3. 성능 모니터링

### 3.1 애플리케이션 모니터링

#### 3.1.1 Prometheus 메트릭 수집
```python
# monitoring/prometheus_metrics.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import time
import logging
from typing import Dict, Any

class PrometheusMetrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.logger = logging.getLogger(__name__)
        
        # API 요청 카운터
        self.request_counter = Counter(
            'api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        # API 요청 지연 시간 히스토그램
        self.request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # 활성 사용자 수 게이지
        self.active_users = Gauge(
            'active_users_total',
            'Number of active users',
            registry=self.registry
        )
        
        # 데이터베이스 연결 풀 게이지
        self.db_connections = Gauge(
            'database_connections_active',
            'Active database connections',
            ['database'],
            registry=self.registry
        )
        
        # 캐시 적중률 게이지
        self.cache_hit_rate = Gauge(
            'cache_hit_rate_percent',
            'Cache hit rate percentage',
            ['cache_type'],
            registry=self.registry
        )
        
        # 외부 API 요청 카운터
        self.external_api_requests = Counter(
            'external_api_requests_total',
            'Total external API requests',
            ['api_name', 'status'],
            registry=self.registry
        )
        
        # 메시지 큐 길이 게이지
        self.message_queue_length = Gauge(
            'message_queue_length',
            'Message queue length',
            ['queue_name'],
            registry=self.registry
        )
        
        # 데이터 처리량 카운터
        self.data_processed = Counter(
            'data_processed_total',
            'Total data processed',
            ['data_type', 'source'],
            registry=self.registry
        )
        
        # 에러 카운터
        self.error_counter = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'component'],
            registry=self.registry
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """API 요청 기록"""
        self.request_counter.labels(method=method, endpoint=endpoint, status=status_code).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def update_active_users(self, count: int):
        """활성 사용자 수 업데이트"""
        self.active_users.set(count)
    
    def update_db_connections(self, database: str, count: int):
        """데이터베이스 연결 수 업데이트"""
        self.db_connections.labels(database=database).set(count)
    
    def update_cache_hit_rate(self, cache_type: str, rate: float):
        """캐시 적중률 업데이트"""
        self.cache_hit_rate.labels(cache_type=cache_type).set(rate)
    
    def record_external_api_request(self, api_name: str, status: str):
        """외부 API 요청 기록"""
        self.external_api_requests.labels(api_name=api_name, status=status).inc()
    
    def update_message_queue_length(self, queue_name: str, length: int):
        """메시지 큐 길이 업데이트"""
        self.message_queue_length.labels(queue_name=queue_name).set(length)
    
    def record_data_processed(self, data_type: str, source: str, count: int = 1):
        """데이터 처리량 기록"""
        self.data_processed.labels(data_type=data_type, source=source).inc(count)
    
    def record_error(self, error_type: str, component: str):
        """에러 기록"""
        self.error_counter.labels(error_type=error_type, component=component).inc()
    
    def get_metrics(self) -> str:
        """메트릭 데이터 반환"""
        try:
            return generate_latest(self.registry)
        except Exception as e:
            self.logger.error(f"Failed to generate metrics: {str(e)}")
            return ""

# 미들웨어를 통한 메트릭 수집
class MetricsMiddleware:
    def __init__(self, app, metrics: PrometheusMetrics):
        self.app = app
        self.metrics = metrics
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # 요청 처리
            await self.app(scope, receive, send)
            
            # 메트릭 기록
            duration = time.time() - start_time
            method = scope.get("method", "")
            path = scope.get("path", "")
            
            # 상태 코드는 실제로는 응답에서 가져와야 함
            status_code = 200  # 기본값
            
            self.metrics.record_request(method, path, status_code, duration)
        else:
            await self.app(scope, receive, send)
```

#### 3.1.2 Grafana 대시보드 설정
```json
{
  "dashboard": {
    "id": null,
    "title": "InsiteChart Performance Dashboard",
    "tags": ["insitechart", "performance"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "yAxes": [
          {
            "label": "Requests/sec"
          }
        ]
      },
      {
        "id": 2,
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ],
        "yAxes": [
          {
            "label": "Seconds"
          }
        ]
      },
      {
        "id": 3,
        "title": "Active Users",
        "type": "singlestat",
        "targets": [
          {
            "expr": "active_users_total",
            "legendFormat": "Active Users"
          }
        ]
      },
      {
        "id": 4,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "database_connections_active",
            "legendFormat": "{{database}}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "cache_hit_rate_percent",
            "legendFormat": "{{cache_type}}"
          }
        ],
        "yAxes": [
          {
            "label": "Percent",
            "min": 0,
            "max": 100
          }
        ]
      },
      {
        "id": 6,
        "title": "External API Requests",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(external_api_requests_total[5m])",
            "legendFormat": "{{api_name}} ({{status}})"
          }
        ]
      },
      {
        "id": 7,
        "title": "Message Queue Length",
        "type": "graph",
        "targets": [
          {
            "expr": "message_queue_length",
            "legendFormat": "{{queue_name}}"
          }
        ]
      },
      {
        "id": 8,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(errors_total[5m])",
            "legendFormat": "{{component}}: {{error_type}}"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### 3.2 로그 분석

#### 3.2.1 ELK 스택 설정
```yaml
# logging/elk-stack.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - elk

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    ports:
      - "5044:5044"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logstash/config:/usr/share/logstash/config
    depends_on:
      - elasticsearch
    networks:
      - elk

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - elk

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.5.0
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - logstash
    networks:
      - elk

volumes:
  elasticsearch_data:

networks:
  elk:
    driver: bridge
```

#### 3.2.2 로그 분석 파이프라인
```python
# logging/log_analyzer.py
import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from elasticsearch import AsyncElasticsearch

class LogAnalyzer:
    def __init__(self, elasticsearch_url: str):
        self.es = AsyncElasticsearch([elasticsearch_url])
        self.logger = logging.getLogger(__name__)
        
        # 로그 패턴
        self.log_patterns = {
            'error': re.compile(r'ERROR|error|Error'),
            'warning': re.compile(r'WARNING|warning|Warning'),
            'api_request': re.compile(r'API|api|Api'),
            'database': re.compile(r'DB|db|Database|database'),
            'cache': re.compile(r'cache|Cache'),
            'external_api': re.compile(r'Yahoo|Reddit|Twitter')
        }
    
    async def analyze_logs(self, time_range: str = '1h') -> Dict:
        """로그 분석"""
        try:
            # 시간 범위 계산
            end_time = datetime.now()
            start_time = end_time - self._parse_time_range(time_range)
            
            # Elasticsearch 쿼리
            query = {
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": end_time.isoformat()
                        }
                    }
                },
                "size": 10000  # 최대 10000개 로그
            }
            
            # 로그 검색
            response = await self.es.search(index="logs-*", body=query)
            hits = response['hits']['hits']
            
            # 로그 분석
            analysis = {
                'total_logs': len(hits),
                'time_range': time_range,
                'error_logs': await self._analyze_error_logs(hits),
                'api_performance': await self._analyze_api_performance(hits),
                'database_performance': await self._analyze_database_performance(hits),
                'cache_performance': await self._analyze_cache_performance(hits),
                'external_api_performance': await self._analyze_external_api_performance(hits),
                'trending_errors': await self._find_trending_errors(hits)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Log analysis error: {str(e)}")
            return {}
    
    async def _analyze_error_logs(self, hits: List[Dict]) -> Dict:
        """에러 로그 분석"""
        error_logs = []
        
        for hit in hits:
            message = hit['_source'].get('message', '')
            if self.log_patterns['error'].search(message):
                error_logs.append({
                    'timestamp': hit['_source'].get('@timestamp'),
                    'message': message,
                    'level': hit['_source'].get('level', 'unknown'),
                    'component': hit['_source'].get('component', 'unknown')
                })
        
        # 에러 유형별 그룹화
        error_types = {}
        for log in error_logs:
            error_type = self._extract_error_type(log['message'])
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(log)
        
        return {
            'total_errors': len(error_logs),
            'error_types': {
                error_type: len(logs)
                for error_type, logs in error_types.items()
            },
            'recent_errors': sorted(error_logs, 
                                  key=lambda x: x['timestamp'], 
                                  reverse=True)[:10]
        }
    
    async def _analyze_api_performance(self, hits: List[Dict]) -> Dict:
        """API 성능 분석"""
        api_logs = []
        
        for hit in hits:
            message = hit['_source'].get('message', '')
            if self.log_patterns['api_request'].search(message):
                api_logs.append(hit['_source'])
        
        # 응답 시간 추출
        response_times = []
        for log in api_logs:
            response_time = self._extract_response_time(log.get('message', ''))
            if response_time:
                response_times.append(response_time)
        
        if not response_times:
            return {'total_requests': len(api_logs)}
        
        # 통계 계산
        response_times.sort()
        count = len(response_times)
        
        return {
            'total_requests': len(api_logs),
            'avg_response_time': sum(response_times) / count,
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p50_response_time': response_times[int(count * 0.5)],
            'p95_response_time': response_times[int(count * 0.95)],
            'p99_response_time': response_times[int(count * 0.99)]
        }
    
    async def _analyze_database_performance(self, hits: List[Dict]) -> Dict:
        """데이터베이스 성능 분석"""
        db_logs = []
        
        for hit in hits:
            message = hit['_source'].get('message', '')
            if self.log_patterns['database'].search(message):
                db_logs.append(hit['_source'])
        
        # 쿼리 시간 추출
        query_times = []
        for log in db_logs:
            query_time = self._extract_query_time(log.get('message', ''))
            if query_time:
                query_times.append(query_time)
        
        if not query_times:
            return {'total_queries': len(db_logs)}
        
        # 통계 계산
        query_times.sort()
        count = len(query_times)
        
        return {
            'total_queries': len(db_logs),
            'avg_query_time': sum(query_times) / count,
            'min_query_time': min(query_times),
            'max_query_time': max(query_times),
            'p95_query_time': query_times[int(count * 0.95)]
        }
    
    async def _analyze_cache_performance(self, hits: List[Dict]) -> Dict:
        """캐시 성능 분석"""
        cache_logs = []
        
        for hit in hits:
            message = hit['_source'].get('message', '')
            if self.log_patterns['cache'].search(message):
                cache_logs.append(hit['_source'])
        
        # 캐시 히트/미스 카운트
        cache_hits = 0
        cache_misses = 0
        
        for log in cache_logs:
            message = log.get('message', '')
            if 'hit' in message.lower():
                cache_hits += 1
            elif 'miss' in message.lower():
                cache_misses += 1
        
        total_cache_operations = cache_hits + cache_misses
        hit_rate = (cache_hits / total_cache_operations * 100) if total_cache_operations > 0 else 0
        
        return {
            'total_cache_operations': total_cache_operations,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'hit_rate_percent': round(hit_rate, 2)
        }
    
    async def _analyze_external_api_performance(self, hits: List[Dict]) -> Dict:
        """외부 API 성능 분석"""
        external_logs = []
        
        for hit in hits:
            message = hit['_source'].get('message', '')
            if self.log_patterns['external_api'].search(message):
                external_logs.append(hit['_source'])
        
        # API별 응답 시간 및 에러율 분석
        api_performance = {}
        
        for log in external_logs:
            message = log.get('message', '')
            api_name = self._extract_api_name(message)
            response_time = self._extract_response_time(message)
            is_error = 'error' in message.lower() or 'failed' in message.lower()
            
            if api_name not in api_performance:
                api_performance[api_name] = {
                    'requests': 0,
                    'errors': 0,
                    'response_times': []
                }
            
            api_performance[api_name]['requests'] += 1
            if is_error:
                api_performance[api_name]['errors'] += 1
            if response_time:
                api_performance[api_name]['response_times'].append(response_time)
        
        # 통계 계산
        for api_name, stats in api_performance.items():
            response_times = stats['response_times']
            if response_times:
                response_times.sort()
                count = len(response_times)
                
                stats['avg_response_time'] = sum(response_times) / count
                stats['p95_response_time'] = response_times[int(count * 0.95)]
            else:
                stats['avg_response_time'] = 0
                stats['p95_response_time'] = 0
            
            stats['error_rate'] = (stats['errors'] / stats['requests'] * 100) if stats['requests'] > 0 else 0
            del stats['response_times']  # 원본 데이터 제거
        
        return api_performance
    
    async def _find_trending_errors(self, hits: List[Dict]) -> List[Dict]:
        """트렌딩 에러 찾기"""
        error_logs = []
        
        for hit in hits:
            message = hit['_source'].get('message', '')
            if self.log_patterns['error'].search(message):
                error_logs.append({
                    'timestamp': hit['_source'].get('@timestamp'),
                    'message': message,
                    'error_type': self._extract_error_type(message)
                })
        
        # 에러 유형별 시간대별 카운트
        error_trends = {}
        
        for log in error_logs:
            error_type = log['error_type']
            timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            hour_bucket = timestamp.replace(minute=0, second=0, microsecond=0)
            
            if error_type not in error_trends:
                error_trends[error_type] = {}
            
            if hour_bucket not in error_trends[error_type]:
                error_trends[error_type][hour_bucket] = 0
            
            error_trends[error_type][hour_bucket] += 1
        
        # 트렌드 분석 (최근 1시간 동안 증가한 에러)
        trending_errors = []
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        for error_type, time_buckets in error_trends.items():
            recent_count = sum(
                count for time_bucket, count in time_buckets.items()
                if time_bucket >= one_hour_ago
            )
            
            previous_count = sum(
                count for time_bucket, count in time_buckets.items()
                if one_hour_ago > time_bucket >= one_hour_ago - timedelta(hours=1)
            )
            
            if recent_count > previous_count * 1.5:  # 50% 이상 증가
                trending_errors.append({
                    'error_type': error_type,
                    'recent_count': recent_count,
                    'previous_count': previous_count,
                    'growth_rate': ((recent_count - previous_count) / previous_count * 100) if previous_count > 0 else float('inf')
                })
        
        # 성장률 기준 정렬
        trending_errors.sort(key=lambda x: x['growth_rate'], reverse=True)
        
        return trending_errors[:5]  # 상위 5개
    
    def _parse_time_range(self, time_range: str) -> timedelta:
        """시간 범위 파싱"""
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            return timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            return timedelta(days=days)
        else:
            return timedelta(hours=1)  # 기본값
    
    def _extract_error_type(self, message: str) -> str:
        """에러 유형 추출"""
        # 간단한 에러 유형 추출
        if 'connection' in message.lower():
            return 'connection_error'
        elif 'timeout' in message.lower():
            return 'timeout_error'
        elif 'authentication' in message.lower():
            return 'auth_error'
        elif 'database' in message.lower():
            return 'database_error'
        else:
            return 'unknown_error'
    
    def _extract_response_time(self, message: str) -> Optional[float]:
        """응답 시간 추출"""
        # 정규식으로 응답 시간 추출
        match = re.search(r'(\d+\.?\d*)\s*ms', message)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_query_time(self, message: str) -> Optional[float]:
        """쿼리 시간 추출"""
        match = re.search(r'query.*?(\d+\.?\d*)\s*ms', message, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_api_name(self, message: str) -> str:
        """API 이름 추출"""
        if 'yahoo' in message.lower():
            return 'yahoo_finance'
        elif 'reddit' in message.lower():
            return 'reddit'
        elif 'twitter' in message.lower():
            return 'twitter'
        else:
            return 'unknown_api'
```

이 성능 및 확장성 문서는 시스템의 성능 최적화와 확장성 확보를 위한 구체적인 전략을 제공합니다. 데이터베이스 최적화, 캐싱 전략, API 성능 최적화, 수평적 확장, 오토 스케일링, 성능 모니터링 등을 통해 안정적이고 확장 가능한 시스템을 구축할 수 있습니다.