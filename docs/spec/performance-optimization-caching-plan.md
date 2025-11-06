# 성능 최적화 및 캐싱 시스템 구현 계획

## 1. 개요

본 문서는 주식 차트 분석 애플리케이션의 성능 최적화 및 다단계 캐싱 시스템 구현을 위한 상세한 계획을 제시합니다. Redis 기반의 분산 캐싱, 데이터베이스 최적화, API 성능 개선, 프론트엔드 최적화 등 다양한 측면에서의 성능 향상 전략을 다룹니다.

## 2. 성능 최적화 아키텍처

### 2.1 다단계 캐싱 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   In-Memory    │  │   Local Cache   │  │   Session    │ │
│  │   Cache         │  │   (LRU)        │  │   Cache      │ │
│  │   - Objects     │  │   - Queries    │  │   - User     │ │
│  │   - Results     │  │   - Computed   │  │   - Auth     │ │
│  │   - Temporary   │  │   - Processed  │  │   - State    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Distributed Cache                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │     Redis       │  │   Redis Cluster │  │   CDN        │ │
│  │   - Primary    │  │   - Shared      │  │   - Static   │ │
│  │   - Hot Data   │  │   - Persistent  │  │   - Assets   │ │
│  │   - Sessions   │  │   - Backup      │  │   - Charts   │ │
│  │   - Pub/Sub    │  │   - Analytics   │  │   - Reports  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   TimescaleDB   │  │   Read Replicas │  │   Connection │ │
│  │   - Primary     │  │   - Analytics   │  │   Pool       │ │
│  │   - Time Series │  │   - Reporting   │  │   - Query    │ │
│  │   - Hot Data    │  │   - Backup      │  │   - Cache    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 캐싱 전략 계층

```mermaid
graph TD
    A[User Request] --> B{Cache Check}
    B -->|Hit| C[Return Cached Data]
    B -->|Miss| D[Process Request]
    D --> E[Database Query]
    E --> F[Process Data]
    F --> G[Store in Cache]
    G --> H[Return Response]
    
    I[Cache Invalidation] --> J{Invalidation Type}
    J -->|Time-based| K[Auto Expire]
    J -->|Event-based| L[Manual Clear]
    J -->|Write-through| M[Immediate Update]
    J -->|Write-behind| M
```

## 3. Redis 기반 분산 캐싱 시스템

### 3.1 Redis 클러스터 설정
```yaml
# docker-compose.redis.yml
version: '3.8'
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes --replica-read-only no
    ports:
      - "6379:6379"
    volumes:
      - redis_master_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    networks:
      - redis-network
    
  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --appendonly yes --replicaof redis-master 6379
    ports:
      - "6380:6379"
    volumes:
      - redis_replica1_data:/data
    depends_on:
      - redis-master
    networks:
      - redis-network
    
  redis-replica-2:
    image: redis:7-alpine
    command: redis-server --appendonly yes --replicaof redis-master 6379
    ports:
      - "6381:6379"
    volumes:
      - redis_replica2_data:/data
    depends_on:
      - redis-master
    networks:
      - redis-network
    
  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    ports:
      - "26379:26379"
    volumes:
      - ./redis/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
      - redis-replica-1
      - redis-replica-2
    networks:
      - redis-network

volumes:
  redis_master_data:
  redis_replica1_data:
  redis_replica2_data:

networks:
  redis-network:
    driver: bridge
```

### 3.2 Redis 설정 최적화
```conf
# redis/redis.conf
# 메모리 최적화
maxmemory 2gb
maxmemory-policy allkeys-lru

# 지속성 설정
save 900 1
save 300 10
save 60 10000

# AOF 설정
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# 네트워크 최적화
tcp-keepalive 300
timeout 0

# 클라이언트 최적화
maxclients 10000

# 메모리 정책
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes

# 압축
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64

# 보안
requirepass your_redis_password
```

### 3.3 캐시 관리자 구현
```python
# cache/cache_manager.py
import redis
import json
import pickle
import asyncio
from typing import Any, Optional, Union, List, Dict
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import logging
from dataclasses import dataclass
from enum import Enum

class CacheStrategy(Enum):
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    WRITE_AROUND = "write_around"
    REFRESH_AHEAD = "refresh_ahead"

@dataclass
class CacheConfig:
    ttl: int  # Time to live in seconds
    strategy: CacheStrategy
    max_size: Optional[int] = None
    refresh_ratio: float = 0.8  # Refresh when 80% of TTL passed
    compression: bool = True
    serialization: str = "json"  # json, pickle, msgpack

class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=False)
        self.logger = logging.getLogger(__name__)
        
        # 캐시 설정
        self.cache_configs = {
            "stock_quote": CacheConfig(
                ttl=60,
                strategy=CacheStrategy.WRITE_THROUGH,
                max_size=1000
            ),
            "stock_history": CacheConfig(
                ttl=300,
                strategy=CacheStrategy.WRITE_BEHIND,
                max_size=500
            ),
            "sentiment_current": CacheConfig(
                ttl=180,
                strategy=CacheStrategy.WRITE_THROUGH,
                max_size=200
            ),
            "sentiment_history": CacheConfig(
                ttl=600,
                strategy=CacheStrategy.WRITE_BEHIND,
                max_size=100
            ),
            "technical_indicators": CacheConfig(
                ttl=300,
                strategy=CacheStrategy.WRITE_THROUGH,
                max_size=300
            ),
            "user_session": CacheConfig(
                ttl=3600,
                strategy=CacheStrategy.WRITE_THROUGH,
                max_size=1000
            ),
            "correlation_analysis": CacheConfig(
                ttl=1800,
                strategy=CacheStrategy.WRITE_BEHIND,
                max_size=50
            ),
            "prediction_results": CacheConfig(
                ttl=900,
                strategy=CacheStrategy.REFRESH_AHEAD,
                max_size=100
            )
        }
        
        # 캐시 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_parts = [prefix]
        
        # 위치 인자 추가
        for arg in args:
            if isinstance(arg, (dict, list, tuple)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(arg))
        
        # 키워드 인자 추가
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(json.dumps(sorted_kwargs, sort_keys=True))
        
        # 키 해싱 (긴 키 방지)
        key_string = ":".join(key_parts)
        if len(key_string) > 200:
            key_string = f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
        
        return key_string
    
    def _serialize(self, data: Any, config: CacheConfig) -> bytes:
        """데이터 직렬화"""
        if config.serialization == "pickle":
            return pickle.dumps(data)
        elif config.serialization == "msgpack":
            import msgpack
            return msgpack.packb(data)
        else:  # json
            return json.dumps(data).encode('utf-8')
    
    def _deserialize(self, data: bytes, config: CacheConfig) -> Any:
        """데이터 역직렬화"""
        if config.serialization == "pickle":
            return pickle.loads(data)
        elif config.serialization == "msgpack":
            import msgpack
            return msgpack.unpackb(data, raw=False)
        else:  # json
            return json.loads(data.decode('utf-8'))
    
    async def get(self, cache_type: str, *args, **kwargs) -> Optional[Any]:
        """캐시에서 데이터 가져오기"""
        try:
            config = self.cache_configs.get(cache_type)
            if not config:
                self.logger.warning(f"Unknown cache type: {cache_type}")
                return None
            
            key = self._generate_key(cache_type, *args, **kwargs)
            
            # 캐시 확인
            cached_data = self.redis.get(key)
            if cached_data is None:
                self.stats["misses"] += 1
                return None
            
            # 데이터 역직렬화
            data = self._deserialize(cached_data, config)
            
            # TTL 확인 및 자동 새로고침
            ttl = self.redis.ttl(key)
            if config.strategy == CacheStrategy.REFRESH_AHEAD and ttl < config.ttl * config.refresh_ratio:
                asyncio.create_task(self._refresh_cache(cache_type, key, args, kwargs))
            
            self.stats["hits"] += 1
            return data
            
        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
            self.stats["errors"] += 1
            return None
    
    async def set(self, cache_type: str, data: Any, *args, **kwargs) -> bool:
        """캐시에 데이터 저장"""
        try:
            config = self.cache_configs.get(cache_type)
            if not config:
                self.logger.warning(f"Unknown cache type: {cache_type}")
                return False
            
            key = self._generate_key(cache_type, *args, **kwargs)
            
            # 데이터 직렬화
            serialized_data = self._serialize(data, config)
            
            # 캐시 크기 제한 확인
            if config.max_size:
                await self._enforce_size_limit(cache_type, config.max_size)
            
            # 캐시 저장
            self.redis.setex(key, config.ttl, serialized_data)
            
            # 전략별 추가 처리
            if config.strategy == CacheStrategy.WRITE_BEHIND:
                # 비동기 백그라운드 저장
                asyncio.create_task(self._background_persist(cache_type, key, data))
            
            self.stats["sets"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Cache set error: {e}")
            self.stats["errors"] += 1
            return False
    
    async def delete(self, cache_type: str, *args, **kwargs) -> bool:
        """캐시 데이터 삭제"""
        try:
            key = self._generate_key(cache_type, *args, **kwargs)
            result = self.redis.delete(key)
            
            if result > 0:
                self.stats["deletes"] += 1
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Cache delete error: {e}")
            self.stats["errors"] += 1
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """패턴으로 캐시 삭제"""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                result = self.redis.delete(*keys)
                self.stats["deletes"] += result
                return result
            return 0
            
        except Exception as e:
            self.logger.error(f"Cache clear pattern error: {e}")
            self.stats["errors"] += 1
            return 0
    
    async def _enforce_size_limit(self, cache_type: str, max_size: int):
        """캐시 크기 제한 적용"""
        pattern = f"{cache_type}:*"
        keys = self.redis.keys(pattern)
        
        if len(keys) >= max_size:
            # LRU 정책으로 오래된 키 삭제
            key_ttl_pairs = []
            for key in keys:
                ttl = self.redis.ttl(key)
                key_ttl_pairs.append((key, ttl))
            
            # TTL이 가장 짧은 키부터 정렬
            key_ttl_pairs.sort(key=lambda x: x[1])
            
            # 초과분 삭제
            excess_count = len(keys) - max_size + 1
            keys_to_delete = [key for key, _ in key_ttl_pairs[:excess_count]]
            
            if keys_to_delete:
                self.redis.delete(*keys_to_delete)
    
    async def _refresh_cache(self, cache_type: str, key: str, args: tuple, kwargs: dict):
        """캐시 자동 새로고침"""
        try:
            # 여기에 새로운 데이터 가져오는 로직 구현
            # 예: await self._fetch_fresh_data(cache_type, *args, **kwargs)
            pass
        except Exception as e:
            self.logger.error(f"Cache refresh error: {e}")
    
    async def _background_persist(self, cache_type: str, key: str, data: Any):
        """백그라운드 영구 저장"""
        try:
            # 여기에 데이터베이스 저장 로직 구현
            pass
        except Exception as e:
            self.logger.error(f"Background persist error: {e}")
    
    def get_stats(self) -> Dict:
        """캐시 통계 가져오기"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }
    
    def reset_stats(self):
        """캐시 통계 초기화"""
        for key in self.stats:
            self.stats[key] = 0

# 캐시 데코레이터
def cache_result(cache_type: str, ttl: Optional[int] = None):
    """캐시 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성 (함수 이름과 인자 사용)
            cache_key = f"{func.__name__}"
            
            # 캐시 확인
            cache_manager = CacheManager()
            cached_result = await cache_manager.get(cache_type, cache_key, *args, **kwargs)
            
            if cached_result is not None:
                return cached_result
            
            # 함수 실행
            result = await func(*args, **kwargs)
            
            # 캐시 저장
            await cache_manager.set(cache_type, result, cache_key, *args, **kwargs)
            
            return result
        return wrapper
    return decorator
```

### 3.4 분산 캐시 동기화
```python
# cache/cache_sync.py
import asyncio
import json
import time
from typing import Dict, List, Any
import redis
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CacheEvent:
    event_type: str  # SET, DELETE, CLEAR
    cache_type: str
    key: str
    value: Any = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class CacheSynchronizer:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
        self.subscribers = {}
        self.event_queue = asyncio.Queue()
        
    async def start_sync(self):
        """캐시 동기화 시작"""
        # 채널 구독
        await self.pubsub.subscribe("cache_events")
        
        # 이벤트 처리 루프
        asyncio.create_task(self._process_events())
        asyncio.create_task(self._handle_sync_events())
    
    async def publish_event(self, event: CacheEvent):
        """캐시 이벤트 발행"""
        event_data = {
            "event_type": event.event_type,
            "cache_type": event.cache_type,
            "key": event.key,
            "value": event.value,
            "timestamp": event.timestamp
        }
        
        self.redis.publish("cache_events", json.dumps(event_data))
    
    async def _process_events(self):
        """이벤트 처리 루프"""
        while True:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    event_data = json.loads(message['data'])
                    await self.event_queue.put(event_data)
            except Exception as e:
                print(f"Event processing error: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_sync_events(self):
        """동기화 이벤트 처리"""
        while True:
            try:
                event_data = await self.event_queue.get()
                
                # 이벤트 타입별 처리
                if event_data['event_type'] == 'SET':
                    await self._handle_set_event(event_data)
                elif event_data['event_type'] == 'DELETE':
                    await self._handle_delete_event(event_data)
                elif event_data['event_type'] == 'CLEAR':
                    await self._handle_clear_event(event_data)
                
            except Exception as e:
                print(f"Sync event handling error: {e}")
    
    async def _handle_set_event(self, event_data: Dict):
        """SET 이벤트 처리"""
        cache_type = event_data['cache_type']
        key = event_data['key']
        value = event_data['value']
        
        # 여기에 로컬 캐시 업데이트 로직
        print(f"Sync SET: {cache_type}:{key}")
    
    async def _handle_delete_event(self, event_data: Dict):
        """DELETE 이벤트 처리"""
        cache_type = event_data['cache_type']
        key = event_data['key']
        
        # 여기에 로컬 캐시 삭제 로직
        print(f"Sync DELETE: {cache_type}:{key}")
    
    async def _handle_clear_event(self, event_data: Dict):
        """CLEAR 이벤트 처리"""
        cache_type = event_data['cache_type']
        
        # 여기에 로컬 캐시 클리어 로직
        print(f"Sync CLEAR: {cache_type}")
```

## 4. 데이터베이스 성능 최적화

### 4.1 TimescaleDB 최적화
```sql
-- 데이터베이스 성능 최적화 스크립트

-- 1. 하이퍼테이블 최적화
SELECT add_compression_policy('stock_data', INTERVAL '7 days');
SELECT add_retention_policy('stock_data', INTERVAL '2 years');

-- 2. 인덱스 최적화
CREATE INDEX CONCURRENTLY idx_stock_data_symbol_time_desc 
ON stock_data (symbol, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_stock_data_timestamp 
ON stock_data (timestamp DESC);

-- 3. 부분 인덱스 (최신 데이터)
CREATE INDEX CONCURRENTLY idx_stock_data_recent 
ON stock_data (symbol, timestamp) 
WHERE timestamp > NOW() - INTERVAL '30 days';

-- 4. 다중 칼럼 인덱스
CREATE INDEX CONCURRENTLY idx_sentiment_symbol_time_score 
ON sentiment_data (symbol, timestamp DESC, sentiment_score);

-- 5. 압축 설정
ALTER TABLE stock_data SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'symbol'
);

ALTER TABLE sentiment_data SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'symbol'
);

-- 6. 통계 업데이트
ANALYZE stock_data;
ANALYZE sentiment_data;

-- 7. 설정 최적화
ALTER SYSTEM SET shared_preload_libraries = 'timescaledb';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

### 4.2 데이터베이스 연결 풀
```python
# database/connection_pool.py
import asyncpg
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
import logging

class DatabasePool:
    def __init__(self, dsn: str, min_size: int = 5, max_size: int = 20):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """연결 풀 초기화"""
        self.pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=self.min_size,
            max_size=self.max_size,
            command_timeout=60,
            server_settings={
                'application_name': 'stock_analysis_app',
                'jit': 'off'  # 간단한 쿼리에 JIT 비활성화
            }
        )
        self.logger.info(f"Database pool initialized: {self.min_size}-{self.max_size}")
    
    async def close(self):
        """연결 풀 닫기"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """연결 획득 컨텍스트 매니저"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            await self.pool.release(conn)
    
    async def execute(self, query: str, *args):
        """쿼리 실행"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """단일 행 조회"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """여러 행 조회"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetch_val(self, query: str, *args):
        """단일 값 조회"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

# 전역 데이터베이스 풀 인스턴스
db_pool = DatabasePool(
    dsn="postgresql://admin:password@timescaledb:5432/stockdb",
    min_size=10,
    max_size=50
)
```

### 4.3 쿼리 최적화
```python
# database/query_optimizer.py
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncpg
from .connection_pool import db_pool

class QueryOptimizer:
    def __init__(self):
        self.query_cache = {}
        self.prepared_statements = {}
    
    async def get_stock_data_optimized(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """최적화된 주식 데이터 조회"""
        
        # 쿼리 캐시 키
        cache_key = f"stock_data_{symbol}_{start_date}_{end_date}_{limit}"
        
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        # 최적화된 쿼리
        query = """
            SELECT 
                timestamp,
                open,
                high,
                low,
                close,
                volume,
                adjusted_close
            FROM stock_data
            WHERE symbol = $1 
                AND timestamp >= $2 
                AND timestamp <= $3
            ORDER BY timestamp DESC
        """
        
        params = [symbol, start_date, end_date]
        
        if limit:
            query += " LIMIT $4"
            params.append(limit)
        
        # 준비된 문제 사용
        async with db_pool.acquire() as conn:
            if query not in self.prepared_statements:
                self.prepared_statements[query] = await conn.prepare(query)
            
            stmt = self.prepared_statements[query]
            results = await stmt.fetch(*params)
            
            # 결과 변환
            data = [dict(row) for row in results]
            
            # 캐시 저장
            self.query_cache[cache_key] = data
            
            return data
    
    async def get_aggregated_stock_data(
        self,
        symbol: str,
        interval: str,  # '1min', '5min', '1hour', '1day'
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """집계된 주식 데이터 조회"""
        
        # 인터벌에 따른 그룹화 설정
        if interval == '1min':
            time_bucket = "time_bucket('1 minute', timestamp)"
        elif interval == '5min':
            time_bucket = "time_bucket('5 minutes', timestamp)"
        elif interval == '1hour':
            time_bucket = "time_bucket('1 hour', timestamp)"
        else:  # 1day
            time_bucket = "time_bucket('1 day', timestamp)"
        
        query = f"""
            SELECT 
                {time_bucket} as timestamp,
                first(open, timestamp) as open,
                max(high) as high,
                min(low) as low,
                last(close, timestamp) as close,
                sum(volume) as volume
            FROM stock_data
            WHERE symbol = $1 
                AND timestamp >= $2 
                AND timestamp <= $3
            GROUP BY {time_bucket}
            ORDER BY timestamp DESC
        """
        
        async with db_pool.acquire() as conn:
            results = await conn.fetch(query, symbol, start_date, end_date)
            return [dict(row) for row in results]
    
    async def get_sentiment_aggregation(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        aggregation: str = 'hourly'  # 'hourly', 'daily'
    ) -> List[Dict]:
        """집계된 감성 데이터 조회"""
        
        if aggregation == 'hourly':
            time_bucket = "time_bucket('1 hour', timestamp)"
        else:  # daily
            time_bucket = "time_bucket('1 day', timestamp)"
        
        query = f"""
            SELECT 
                {time_bucket} as timestamp,
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as mention_count,
                AVG(confidence) as avg_confidence,
                STDDEV(sentiment_score) as sentiment_stddev
            FROM sentiment_data
            WHERE symbol = $1 
                AND timestamp >= $2 
                AND timestamp <= $3
            GROUP BY {time_bucket}
            ORDER BY timestamp DESC
        """
        
        async with db_pool.acquire() as conn:
            results = await conn.fetch(query, symbol, start_date, end_date)
            return [dict(row) for row in results]
    
    async def batch_insert_stock_data(self, data: List[Dict]) -> None:
        """대량 주식 데이터 삽입"""
        if not data:
            return
        
        # COPY 명령을 사용한 대량 삽입
        query = """
            COPY stock_data (symbol, timestamp, open, high, low, close, volume, adjusted_close)
            FROM STDIN
        """
        
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.copy_into_table(
                    'stock_data',
                    records=data,
                    columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'adjusted_close']
                )
    
    async def get_correlation_data_optimized(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """최적화된 상관관계 데이터 조회"""
        
        query = """
            WITH stock_daily AS (
                SELECT 
                    DATE(timestamp) as date,
                    last(close, timestamp) as close_price,
                    last(close, timestamp) / LAG(last(close, timestamp)) OVER (ORDER BY DATE(timestamp)) - 1 as daily_return
                FROM stock_data
                WHERE symbol = $1 
                    AND timestamp >= $2 
                    AND timestamp <= $3
                GROUP BY DATE(timestamp)
            ),
            sentiment_daily AS (
                SELECT 
                    DATE(timestamp) as date,
                    AVG(sentiment_score) as avg_sentiment,
                    COUNT(*) as mention_count
                FROM sentiment_data
                WHERE symbol = $1 
                    AND timestamp >= $2 
                    AND timestamp <= $3
                GROUP BY DATE(timestamp)
            )
            SELECT 
                s.date,
                s.close_price,
                s.daily_return,
                coalesce(sent.avg_sentiment, 0) as avg_sentiment,
                coalesce(sent.mention_count, 0) as mention_count
            FROM stock_daily s
            LEFT JOIN sentiment_daily sent ON s.date = sent.date
            ORDER BY s.date DESC
        """
        
        async with db_pool.acquire() as conn:
            results = await conn.fetch(query, symbol, start_date, end_date)
            return [dict(row) for row in results]
```

## 5. API 성능 최적화

### 5.1 비동기 API 처리
```python
# api/async_handler.py
import asyncio
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
from .cache_manager import CacheManager, cache_result

class AsyncAPIHandler:
    def __init__(self):
        self.cache_manager = CacheManager()
        self.logger = logging.getLogger(__name__)
        
    def setup_middleware(self, app: FastAPI):
        """미들웨어 설정"""
        # Gzip 압축
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # 신뢰할 수 있는 호스트
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=["*"]  # 프로덕션에서는 특정 호스트로 제한
        )
        
        # 성능 미들웨어
        @app.middleware("http")
        async def add_performance_headers(request, call_next):
            start_time = time.time()
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            
            # 성능 헤더 추가
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Cache-Status"] = "HIT" if hasattr(request.state, "cache_hit") else "MISS"
            
            return response
    
    @cache_result("stock_quote", ttl=60)
    async def get_stock_quote_async(self, symbol: str) -> Dict[str, Any]:
        """비동기 주식 현재가 조회"""
        # 병렬로 여러 데이터 소스 조회
        tasks = [
            self._fetch_basic_quote(symbol),
            self._fetch_technical_indicators(symbol),
            self._fetch_market_sentiment(symbol)
        ]
        
        try:
            basic_quote, technical_indicators, market_sentiment = await asyncio.gather(
                *tasks, return_exceptions=True
            )
            
            # 결과 조합
            result = {
                "symbol": symbol,
                "timestamp": time.time(),
                "basic_quote": basic_quote if not isinstance(basic_quote, Exception) else None,
                "technical_indicators": technical_indicators if not isinstance(technical_indicators, Exception) else None,
                "market_sentiment": market_sentiment if not isinstance(market_sentiment, Exception) else None
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching stock quote for {symbol}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch stock data")
    
    async def _fetch_basic_quote(self, symbol: str) -> Dict[str, Any]:
        """기본 주식 정보 조회"""
        # 여기에 yfinance API 호출 로직
        await asyncio.sleep(0.1)  # 시뮬레이션
        return {
            "price": 150.25,
            "change": 2.50,
            "change_percent": 1.69,
            "volume": 1000000
        }
    
    async def _fetch_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """기술적 지표 조회"""
        # 여기에 기술적 지표 계산 로직
        await asyncio.sleep(0.2)  # 시뮬레이션
        return {
            "rsi": 65.5,
            "macd": 1.25,
            "bb_upper": 155.0,
            "bb_lower": 145.0
        }
    
    async def _fetch_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """시장 감성 조회"""
        # 여기에 감성 분석 API 호출 로직
        await asyncio.sleep(0.15)  # 시뮬레이션
        return {
            "sentiment_score": 0.15,
            "mention_count": 250,
            "confidence": 0.75
        }
    
    async def batch_stock_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """배치 주식 현재가 조회"""
        # 동시에 여러 심볼 조회
        tasks = [self.get_stock_quote_async(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 필터링
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error fetching quote for {symbols[i]}: {result}")
                valid_results.append({
                    "symbol": symbols[i],
                    "error": str(result)
                })
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def get_stock_history_stream(
        self, 
        symbol: str, 
        period: str
    ):
        """스트리밍 주식 과거 데이터"""
        # 데이터 청크 크기
        chunk_size = 1000
        
        # 총 데이터 수 계산
        total_count = await self._get_data_count(symbol, period)
        
        # 청크별로 데이터 전송
        for offset in range(0, total_count, chunk_size):
            chunk = await self._get_data_chunk(symbol, period, offset, chunk_size)
            
            if chunk:
                yield {
                    "data": chunk,
                    "offset": offset,
                    "total": total_count,
                    "progress": min(offset + chunk_size, total_count) / total_count
                }
            
            # 작은 지연으로 다른 요청 처리
            await asyncio.sleep(0.01)
    
    async def _get_data_count(self, symbol: str, period: str) -> int:
        """데이터 총 수 조회"""
        # 여기에 데이터 수 조회 로직
        return 10000  # 예시
    
    async def _get_data_chunk(
        self, 
        symbol: str, 
        period: str, 
        offset: int, 
        limit: int
    ) -> List[Dict]:
        """데이터 청크 조회"""
        # 여기에 청크 데이터 조회 로직
        await asyncio.sleep(0.05)  # 시뮬레이션
        return [{"timestamp": i, "price": 150 + i * 0.1} for i in range(offset, offset + limit)]
```

### 5.2 API 응답 최적화
```python
# api/response_optimizer.py
import json
import gzip
import asyncio
from typing import Any, Dict, List, Optional
from fastapi import Response
from fastapi.responses import JSONResponse
import orjson  # 더 빠른 JSON 라이브러리

class ResponseOptimizer:
    def __init__(self):
        self.compression_threshold = 1024  # 1KB 이상은 압축
    
    def create_optimized_response(
        self, 
        data: Any, 
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        compress: bool = True
    ) -> Response:
        """최적화된 응답 생성"""
        
        # JSON 직렬화
        if isinstance(data, (dict, list)):
            # orjson 사용 (더 빠름)
            content = orjson.dumps(data)
        else:
            content = str(data).encode('utf-8')
        
        # 압축 결정
        should_compress = compress and len(content) > self.compression_threshold
        
        if should_compress:
            content = gzip.compress(content)
            content_encoding = "gzip"
        else:
            content_encoding = "identity"
        
        # 응답 헤더 설정
        response_headers = {
            "Content-Type": "application/json",
            "Content-Encoding": content_encoding,
            "Content-Length": str(len(content)),
            "Cache-Control": "public, max-age=300",  # 5분 캐시
            "Vary": "Accept-Encoding"
        }
        
        if headers:
            response_headers.update(headers)
        
        return Response(
            content=content,
            status_code=status_code,
            headers=response_headers
        )
    
    async def create_streaming_response(
        self, 
        data_generator,
        compress: bool = True
    ):
        """스트리밍 응답 생성"""
        
        async def generate():
            async for chunk in data_generator:
                # JSON 직렬화
                chunk_data = orjson.dumps(chunk)
                
                # 압축
                if compress and len(chunk_data) > self.compression_threshold:
                    chunk_data = gzip.compress(chunk_data)
                
                yield chunk_data
        
        headers = {
            "Content-Type": "application/json",
            "Content-Encoding": "gzip" if compress else "identity",
            "Transfer-Encoding": "chunked",
            "Cache-Control": "no-cache"
        }
        
        return Response(
            content=generate(),
            headers=headers,
            media_type="application/json"
        )
    
    def create_cached_response(
        self, 
        data: Any, 
        etag: str,
        max_age: int = 300
    ) -> Response:
        """캐시된 응답 생성"""
        
        # JSON 직렬화
        content = orjson.dumps(data)
        
        # ETag 계산
        if not etag:
            import hashlib
            etag = f'"{hashlib.md5(content).hexdigest()}"'
        
        headers = {
            "Content-Type": "application/json",
            "ETag": etag,
            "Cache-Control": f"public, max-age={max_age}",
            "Vary": "Accept-Encoding"
        }
        
        return Response(
            content=content,
            headers=headers
        )
    
    def create_error_response(
        self, 
        error_code: str, 
        message: str, 
        status_code: int = 400
    ) -> Response:
        """에러 응답 생성"""
        
        error_data = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        return self.create_optimized_response(
            data=error_data,
            status_code=status_code,
            headers={"Cache-Control": "no-cache"}
        )
```

## 6. 프론트엔드 성능 최적화

### 6.1 React 성능 최적화
```typescript
// frontend/src/utils/performance.ts
import { memo, useMemo, useCallback, useRef, useEffect } from 'react';
import { debounce, throttle } from 'lodash';

// 메모이제이션된 차트 컴포넌트
export const MemoizedChart = memo(({ data, config }: ChartProps) => {
  // 데이터 처리 메모이제이션
  const processedData = useMemo(() => {
    return data.map(item => ({
      ...item,
      timestamp: new Date(item.timestamp),
      formattedValue: formatCurrency(item.value)
    }));
  }, [data]);

  // 차트 렌더링
  return <Chart data={processedData} config={config} />;
}, (prevProps, nextProps) => {
  // 커스텀 비교 함수
  return (
    prevProps.data.length === nextProps.data.length &&
    prevProps.config.type === nextProps.config.type
  );
});

// 디바운스된 검색 함수
export const useDebounceSearch = (searchFunction: Function, delay: number = 300) => {
  const debouncedSearch = useMemo(
    () => debounce(searchFunction, delay),
    [searchFunction, delay]
  );

  useEffect(() => {
    return () => {
      debouncedSearch.cancel();
    };
  }, [debouncedSearch]);

  return debouncedSearch;
};

// 스로틀된 스크롤 핸들러
export const useThrottledScroll = (scrollHandler: Function, delay: number = 100) => {
  const throttledHandler = useMemo(
    () => throttle(scrollHandler, delay),
    [scrollHandler, delay]
  );

  useEffect(() => {
    return () => {
      throttledHandler.cancel();
    };
  }, [throttledHandler]);

  return throttledHandler;
};

// 가상화된 리스트 컴포넌트
export const VirtualizedList = memo(({ items, itemHeight, containerHeight }: VirtualizedListProps) => {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // 보이는 아이템 계산
  const visibleItems = useMemo(() => {
    const startIndex = Math.floor(scrollTop / itemHeight);
    const endIndex = Math.min(
      startIndex + Math.ceil(containerHeight / itemHeight) + 1,
      items.length
    );

    return items.slice(startIndex, endIndex).map((item, index) => ({
      ...item,
      index: startIndex + index
    }));
  }, [items, itemHeight, containerHeight, scrollTop]);

  // 스크롤 핸들러
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ height: containerHeight, overflow: 'auto' }}
      onScroll={handleScroll}
    >
      <div style={{ height: items.length * itemHeight, position: 'relative' }}>
        {visibleItems.map(item => (
          <div
            key={item.id}
            style={{
              position: 'absolute',
              top: item.index * itemHeight,
              height: itemHeight,
              width: '100%'
            }}
          >
            <ListItem data={item} />
          </div>
        ))}
      </div>
    </div>
  );
});

// 이미지 지연 로딩 컴포넌트
export const LazyImage = memo(({ src, alt, placeholder, ...props }: LazyImageProps) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={imgRef} {...props}>
      {isInView ? (
        <img
          src={src}
          alt={alt}
          onLoad={() => setIsLoaded(true)}
          style={{
            opacity: isLoaded ? 1 : 0,
            transition: 'opacity 0.3s ease'
          }}
        />
      ) : (
        <div style={{ backgroundColor: '#f0f0f0', ...props.style }}>
          {placeholder}
        </div>
      )}
    </div>
  );
});

// 데이터 프리페칭 훅
export const useDataPrefetch = (url: string, dependencies: any[] = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const prefetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(url);
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    prefetchData();
  }, dependencies);

  return { data, loading, error };
};

// 웹 워커를 이용한 무거운 계산
export const useWebWorker = (workerScript: string) => {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const executeWorker = useCallback((data: any) => {
    setLoading(true);
    
    const worker = new Worker(workerScript);
    
    worker.postMessage(data);
    
    worker.onmessage = (e) => {
      setResult(e.data);
      setLoading(false);
      worker.terminate();
    };
    
    worker.onerror = (error) => {
      console.error('Worker error:', error);
      setLoading(false);
      worker.terminate();
    };
  }, [workerScript]);

  return { result, loading, executeWorker };
};
```

### 6.2 번들 최적화
```javascript
// frontend/webpack.optimization.js
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');
const CompressionPlugin = require('compression-webpack-plugin');
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  optimization: {
    // 코드 분할
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // 벤더 라이브러리 분리
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
          priority: 10
        },
        // 차트 라이브러리 분리
        charts: {
          test: /[\\/]node_modules[\\/](chart\.js|plotly\.js)[\\/]/,
          name: 'charts',
          chunks: 'all',
          priority: 20
        },
        // 공통 모듈 분리
        common: {
          name: 'common',
          minChunks: 2,
          chunks: 'all',
          priority: 5,
          reuseExistingChunk: true
        }
      }
    },
    
    // 미니파이
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          compress: {
            drop_console: true, // 콘솔 로그 제거
            drop_debugger: true // 디버거 제거
          }
        }
      })
    ],
    
    // 런타임 최적화
    runtimeChunk: {
      name: 'runtime'
    }
  },
  
  // 압축 플러그인
  plugins: [
    new CompressionPlugin({
      algorithm: 'gzip',
      test: /\.(js|css|html|svg)$/,
      threshold: 10240,
      minRatio: 0.8
    }),
    
    // 번들 분석기 (개발 모드에서만)
    ...(process.env.NODE_ENV === 'development' ? [
      new BundleAnalyzerPlugin({
        analyzerMode: 'static',
        openAnalyzer: false
      })
    ] : [])
  ],
  
  // 모듈 해석 최적화
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@utils': path.resolve(__dirname, 'src/utils'),
      '@hooks': path.resolve(__dirname, 'src/hooks')
    },
    extensions: ['.js', '.jsx', '.ts', '.tsx'],
    modules: ['node_modules', 'src']
  },
  
  // 모듈 캐싱
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'babel-loader',
            options: {
              cacheDirectory: true, // babel 캐시 활성화
              cacheCompression: false
            }
          }
        ]
      },
      {
        test: /\.css$/,
        use: [
          'style-loader',
          {
            loader: 'css-loader',
            options: {
              importLoaders: 1,
              modules: {
                localIdentName: '[name]__[local]___[hash:base64:5]'
              }
            }
          }
        ]
      },
      {
        test: /\.(png|jpg|jpeg|gif|svg)$/,
        use: [
          {
            loader: 'url-loader',
            options: {
              limit: 8192, // 8KB 이하는 Data URL로 변환
              name: 'images/[name].[hash].[ext]'
            }
          }
        ]
      }
    ]
  }
};
```

## 7. 모니터링 및 성능 분석

### 7.1 성능 모니터링 시스템
```python
# monitoring/performance_monitor.py
import time
import asyncio
import psutil
import prometheus_client
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

@dataclass
class PerformanceMetrics:
    timestamp: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    response_time: float
    request_count: int
    error_count: int
    cache_hit_rate: float

class PerformanceMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Prometheus 메트릭
        self.request_count = prometheus_client.Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = prometheus_client.Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        self.cache_hit_rate = prometheus_client.Gauge(
            'cache_hit_rate',
            'Cache hit rate',
            ['cache_type']
        )
        
        self.system_cpu = prometheus_client.Gauge('system_cpu_usage', 'System CPU usage')
        self.system_memory = prometheus_client.Gauge('system_memory_usage', 'System memory usage')
        
        # 성능 데이터 저장
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 1000
    
    async def start_monitoring(self, interval: int = 60):
        """성능 모니터링 시작"""
        while True:
            try:
                metrics = await self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # 히스토리 크기 제한
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size:]
                
                # Prometheus 메트릭 업데이트
                self.update_prometheus_metrics(metrics)
                
                # 성능 경고 확인
                await self.check_performance_alerts(metrics)
                
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
            
            await asyncio.sleep(interval)
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """성능 메트릭 수집"""
        
        # 시스템 메트릭
        cpu_usage = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        network_info = psutil.net_io_counters()
        
        # 애플리케이션 메트릭
        # 여기에 애플리케이션 특정 메트릭 수집 로직 추가
        
        return PerformanceMetrics(
            timestamp=time.time(),
            cpu_usage=cpu_usage,
            memory_usage=memory_info.percent,
            disk_usage=disk_info.percent,
            network_io={
                'bytes_sent': network_info.bytes_sent,
                'bytes_recv': network_info.bytes_recv
            },
            response_time=0.0,  # 실제로는 평균 응답 시간
            request_count=0,    # 실제로는 총 요청 수
            error_count=0,      # 실제로는 총 에러 수
            cache_hit_rate=0.0  # 실제로는 캐시 적중률
        )
    
    def update_prometheus_metrics(self, metrics: PerformanceMetrics):
        """Prometheus 메트릭 업데이트"""
        self.system_cpu.set(metrics.cpu_usage)
        self.system_memory.set(metrics.memory_usage)
        self.cache_hit_rate.set(metrics.cache_hit_rate)
    
    async def check_performance_alerts(self, metrics: PerformanceMetrics):
        """성능 경고 확인"""
        
        # CPU 사용량 경고
        if metrics.cpu_usage > 80:
            await self.send_alert(
                "HIGH_CPU_USAGE",
                f"CPU usage is {metrics.cpu_usage:.1f}%",
                "warning"
            )
        
        # 메모리 사용량 경고
        if metrics.memory_usage > 85:
            await self.send_alert(
                "HIGH_MEMORY_USAGE",
                f"Memory usage is {metrics.memory_usage:.1f}%",
                "warning"
            )
        
        # 디스크 사용량 경고
        if metrics.disk_usage > 90:
            await self.send_alert(
                "HIGH_DISK_USAGE",
                f"Disk usage is {metrics.disk_usage:.1f}%",
                "critical"
            )
        
        # 응답 시간 경고
        if metrics.response_time > 2.0:
            await self.send_alert(
                "SLOW_RESPONSE",
                f"Response time is {metrics.response_time:.2f}s",
                "warning"
            )
        
        # 캐시 적중률 경고
        if metrics.cache_hit_rate < 0.5:
            await self.send_alert(
                "LOW_CACHE_HIT_RATE",
                f"Cache hit rate is {metrics.cache_hit_rate:.1%}",
                "warning"
            )
    
    async def send_alert(self, alert_type: str, message: str, severity: str):
        """경고 전송"""
        self.logger.warning(f"ALERT [{alert_type}]: {message}")
        
        # 여기에 알림 시스템 연동 로직 (Slack, Email 등)
        alert_data = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 알림 전송 로직
        # await notification_service.send_alert(alert_data)
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """성능 요약 가져오기"""
        
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # 평균 계산
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        # 최대값 계산
        max_cpu = max(m.cpu_usage for m in recent_metrics)
        max_memory = max(m.memory_usage for m in recent_metrics)
        max_response_time = max(m.response_time for m in recent_metrics)
        
        return {
            "period_hours": hours,
            "metrics_count": len(recent_metrics),
            "averages": {
                "cpu_usage": avg_cpu,
                "memory_usage": avg_memory,
                "response_time": avg_response_time,
                "cache_hit_rate": avg_cache_hit_rate
            },
            "maximums": {
                "cpu_usage": max_cpu,
                "memory_usage": max_memory,
                "response_time": max_response_time
            },
            "total_requests": sum(m.request_count for m in recent_metrics),
            "total_errors": sum(m.error_count for m in recent_metrics)
        }
```

## 8. 결론

본 성능 최적화 및 캐싱 시스템 구현 계획은 다단계 캐싱, 데이터베이스 최적화, API 성능 개선, 프론트엔드 최적화 등 다양한 측면에서의 포괄적인 성능 향상 전략을 제시합니다.

주요 특징:
1. **다단계 캐싱**: 인메모리, 로컬, 분산 캐시 계층 구현
2. **Redis 클러스터**: 고가용성 및 성능 확장
3. **데이터베이스 최적화**: TimescaleDB 튜닝 및 연결 풀
4. **비동기 API 처리**: 병렬 처리 및 스트리밍
5. **프론트엔드 최적화**: 메모이제이션, 가상화, 코드 분할
6. **성능 모니터링**: 실시간 메트릭 수집 및 경고 시스템

이 시스템을 통해 애플리케이션의 응답 시간을 크게 개선하고, 대규모 트래픽을 효과적으로 처리할 수 있으며, 사용자 경험을 향상시킬 수 있습니다. 특히 캐싱 시스템을 통한 데이터 접근 속도 향상과 비동기 처리를 통한 동시성 개선이 핵심적인 성능 개선 요소가 될 것입니다.