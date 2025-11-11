# 데이터 모델 및 API 엔드포인트 최적화 분석

## 1. 분석 개요

본 문서는 InsiteChart 프로젝트의 데이터 모델과 API 엔드포인트를 심층적으로 분석하여, 성능 최적화와 확장성 향상을 위한 구체적인 개선 방안을 제시합니다.

## 2. 데이터 모델 최적화 분석

### 2.1 현재 데이터 모델 상태 분석

#### 2.1.1 강점
- **완전한 관계형 모델**: User, Stock, StockPrice, SentimentData 등 핵심 엔티티 잘 정의됨
- **적절한 인덱싱**: 성능을 위한 기본 인덱스와 보조 인덱스 전략적 배치
- **정규화**: 데이터 중복 최소화를 위한 제1정규형, 제2정규형 적용
- **감사 추적**: SystemLog, UserActivity 등을 통한 변경 이력 관리

#### 2.1.2 개선 기회
1. **대용량 테이블 파티셔닝 부재**: StockPrice, SentimentData 등 대용량 테이블에 파티셔닝 전략 부족
2. **데이터 아카이빙 정책 부재**: 오래된 데이터 처리 정책 미구현
3. **인덱스 전략 미세화**: 복합 인덱스, 부분 인덱스 등 세부 최적화 부족
4. **데이터 타입 최적화**: 일부 필드의 데이터 타입이 비효율적일 수 있음

### 2.2 데이터 모델 최적화 방안

#### 2.2.1 파티셔닝 전략
```sql
-- 1. 시간 기반 파티셔닝 (StockPrice 테이블)
CREATE TABLE stock_prices_partitioned (
    LIKE stock_prices INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- 월별 파티션 생성
CREATE TABLE stock_prices_2024_01 PARTITION OF stock_prices_partitioned
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE stock_prices_2024_02 PARTITION OF stock_prices_partitioned
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 자동 파티션 관리 함수
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE %I PARTITION OF %I
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, 
                   table_name || '_partitioned',
                   start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- 2. 해시 파티셔닝 (SentimentData 테이블)
CREATE TABLE sentiment_data_partitioned (
    LIKE sentiment_data INCLUDING ALL
) PARTITION BY HASH (stock_id);

-- 4개 해시 파티션 생성
CREATE TABLE sentiment_data_part_0 PARTITION OF sentiment_data_partitioned;
CREATE TABLE sentiment_data_part_1 PARTITION OF sentiment_data_partitioned;
CREATE TABLE sentiment_data_part_2 PARTITION OF sentiment_data_partitioned;
CREATE TABLE sentiment_data_part_3 PARTITION OF sentiment_data_partitioned;
```

#### 2.2.2 인덱스 최적화
```sql
-- 1. 복합 인덱스 추가
CREATE INDEX idx_stock_price_symbol_time 
ON stock_prices(symbol, timestamp DESC);

CREATE INDEX idx_sentiment_stock_source_time 
ON sentiment_data(stock_id, source, timestamp DESC);

-- 2. 부분 인덱스 (조건부 인덱스)
CREATE INDEX idx_active_users 
ON users(id) WHERE is_active = true AND deleted_at IS NULL;

CREATE INDEX idx_recent_sentiments 
ON sentiment_data(timestamp) 
WHERE timestamp >= NOW() - INTERVAL '7 days';

-- 3. 함수 기반 인덱스
CREATE INDEX idx_stock_symbol_upper 
ON stocks(UPPER(symbol));

-- 4. 포함 인덱스 (GIN)
CREATE INDEX idx_user_activity_metadata 
ON user_activities USING GIN (activity_metadata);

-- 5. 인덱스 사용 통계 업데이트
ANALYZE stock_prices;
ANALYZE sentiment_data;
ANALYZE users;
```

#### 2.2.3 데이터 타입 최적화
```sql
-- 1. 더 효율적인 데이터 타입으로 변경
ALTER TABLE stocks 
ALTER COLUMN market_cap TYPE BIGINT,
ALTER COLUMN volume TYPE BIGINT;

-- 2. ENUM 타입 활용
CREATE TYPE stock_type_enum AS ENUM ('EQUITY', 'ETF', 'MUTUAL_FUND', 'CRYPTOCURRENCY', 'INDEX');
CREATE TYPE sentiment_source_enum AS ENUM ('REDDIT', 'TWITTER', 'NEWS', 'DISCORD');

ALTER TABLE stocks 
ALTER COLUMN stock_type TYPE stock_type_enum USING stock_type::stock_type_enum;

ALTER TABLE sentiment_data 
ALTER COLUMN source TYPE sentiment_source_enum USING source::sentiment_source_enum;

-- 3. 배열 타입 활용 (태그 기능)
ALTER TABLE stocks 
ADD COLUMN tags TEXT[];

CREATE INDEX idx_stock_tags 
ON stocks USING GIN (tags);

-- 4. JSONB 타입 활용 (유연한 메타데이터)
ALTER TABLE stocks 
ADD COLUMN metadata JSONB;

CREATE INDEX idx_stock_metadata 
ON stocks USING GIN (metadata);
```

#### 2.2.4 데이터 아카이빙 정책
```sql
-- 1. 아카이빙 테이블 생성
CREATE TABLE stock_prices_archive (
    LIKE stock_prices INCLUDING ALL
);

CREATE TABLE sentiment_data_archive (
    LIKE sentiment_data INCLUDING ALL
);

-- 2. 아카이빙 함수
CREATE OR REPLACE FUNCTION archive_old_data()
RETURNS void AS $$
DECLARE
    archive_date date := CURRENT_DATE - INTERVAL '2 years';
BEGIN
    -- 오래된 주식 가격 데이터 아카이빙
    DELETE FROM stock_prices 
    WHERE timestamp < archive_date
    RETURNING * INTO stock_prices_archive;
    
    -- 오래된 감성 데이터 아카이빙
    DELETE FROM sentiment_data 
    WHERE timestamp < archive_date
    RETURNING * INTO sentiment_data_archive;
    
    -- 로그 기록
    INSERT INTO system_logs (level, component, message, timestamp)
    VALUES ('INFO', 'ARCHIVE', 'Archived data older than ' || archive_date, NOW());
END;
$$ LANGUAGE plpgsql;

-- 3. 자동 아카이빙 스케줄러 (pg_cron 확장)
SELECT cron.schedule(
    '0 2 * * 0',  -- 매주 일요일 새벽 2시
    'SELECT archive_old_data();'
);
```

### 2.3 데이터베이스 성능 최적화

#### 2.3.1 쿼리 최적화
```sql
-- 1. N+1 문제 해결을 위한 조인 쿼리 최적화
-- 기존 (N+1 문제)
SELECT s.*, 
       (SELECT AVG(sp.price) FROM stock_prices sp WHERE sp.stock_id = s.id AND sp.timestamp >= NOW() - INTERVAL '30 days') as avg_price
FROM stocks s;

-- 개선 (조인 활용)
SELECT s.*, AVG(sp.price) as avg_price
FROM stocks s
LEFT JOIN stock_prices sp ON s.id = sp.stock_id AND sp.timestamp >= NOW() - INTERVAL '30 days'
GROUP BY s.id;

-- 2. 윈도우 함수 활용
-- 최신 감성 데이터 조회
SELECT DISTINCT ON (sd.stock_id) 
       sd.stock_id,
       sd.compound_score,
       sd.timestamp,
       ROW_NUMBER() OVER (PARTITION BY sd.stock_id ORDER BY sd.timestamp DESC) as rn
FROM sentiment_data sd
WHERE sd.timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY sd.stock_id, sd.timestamp DESC;

-- 3. CTE (Common Table Expression) 활용
-- 복잡한 쿼리 단순화
WITH recent_sentiments AS (
    SELECT stock_id, 
           AVG(compound_score) as avg_sentiment,
           COUNT(*) as mention_count
    FROM sentiment_data 
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY stock_id
),
stock_info AS (
    SELECT s.*, rs.avg_sentiment, rs.mention_count
    FROM stocks s
    LEFT JOIN recent_sentiments rs ON s.id = rs.stock_id
)
SELECT * FROM stock_info 
WHERE avg_sentiment IS NOT NULL
ORDER BY mention_count DESC;
```

#### 2.3.2 데이터베이스 설정 최적화
```sql
-- 1. 테이블스페이스 최적화
-- 대용량 테이블을 위한 별도 테이블스페이스
CREATE TABLESPACE fast_tablespace LOCATION '/fast/storage/path';
CREATE TABLESPACE archive_tablespace LOCATION '/archive/storage/path';

-- 테이블 생성 시 테이블스페이스 지정
CREATE TABLE stock_prices_large (
    LIKE stock_prices INCLUDING ALL
) TABLESPACE fast_tablespace;

-- 2. 통계 정보 수집 최적화
-- 더 자주 통계 정보 업데이트
ALTER TABLE stock_prices SET (autovacuum_analyze_scale_factor = 0.1);
ALTER TABLE sentiment_data SET (autovacuum_analyze_scale_factor = 0.1);

-- 3. 메모리 설정 최적화
-- 공유 메모리 증가 (postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

-- 4. 연결 풀 최적화
max_connections = 100
shared_preload_libraries = 'pg_stat_statements'
track_activity_query_size = 2048
```

## 3. API 엔드포인트 최적화 분석

### 3.1 현재 API 엔드포인트 상태 분석

#### 3.1.1 강점
- **RESTful 설계**: 표준 HTTP 메서드와 상태 코드 적절히 사용
- **일관된 응답 형식**: success, data, timestamp 구조 일관성 유지
- **의존성 주입**: FastAPI의 의존성 주입 시스템 적극 활용
- **비동기 처리**: asyncio를 통한 비동기 요청 처리

#### 3.1.2 개선 기회
1. **응답 데이터 최적화**: 불필요한 데이터 중복 및 과도한 응답 크기
2. **페이지네이션 부재**: 대용량 데이터에 대한 효율적인 페이지네이션 부족
3. **필터링 및 정렬 제한**: 동적 필터링과 정렬 기능 제한적
4. **캐시 전략 미세화**: 엔드포인트별 캐시 전략 미세화
5. **API 버전 관리**: 향후 버전 호환성 고려 부족

### 3.2 API 엔드포인트 최적화 방안

#### 3.2.1 응답 데이터 최적화
```python
# 1. 필드 선택 기능 추가
class StockRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    fields: Optional[List[str]] = Field(
        None, 
        description="Fields to include in response"
    )

@router.post("/stock")
async def get_stock_data_optimized(request: StockRequest):
    stock_data = await stock_service.get_stock_info(request.symbol)
    
    if not stock_data:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # 요청된 필드만 포함
    if request.fields:
        filtered_data = {field: stock_data.get(field) 
                       for field in request.fields 
                       if field in stock_data}
        stock_data = filtered_data
    
    return {
        "success": True,
        "data": stock_data,
        "timestamp": datetime.utcnow().isoformat()
    }

# 2. 응답 압축
from fastapi.responses import JSONResponse
import gzip
import json

class CompressedJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        # JSON 직렬화
        json_data = json.dumps(content, ensure_ascii=False)
        # gzip 압축
        compressed = gzip.compress(json_data.encode('utf-8'))
        return compressed

@router.post("/stock/compressed")
async def get_stock_data_compressed(request: StockRequest):
    stock_data = await stock_service.get_stock_info(request.symbol)
    
    if not stock_data:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    response_data = {
        "success": True,
        "data": stock_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return CompressedJSONResponse(
        content=response_data,
        headers={
            "Content-Encoding": "gzip",
            "Content-Type": "application/json"
        }
    )

# 3. 데이터 변환기 패턴
class DataTransformer:
    @staticmethod
    def transform_stock_data(data: Dict[str, Any], 
                          transformer: str = "default") -> Dict[str, Any]:
        if transformer == "mobile":
            # 모바일용 경량 데이터
            return {
                "symbol": data.get("symbol"),
                "price": data.get("current_price"),
                "change": data.get("day_change_pct")
            }
        elif transformer == "chart":
            # 차트용 데이터
            return {
                "symbol": data.get("symbol"),
                "prices": data.get("historical_prices", []),
                "volume": data.get("volume")
            }
        else:
            # 기본 데이터
            return data

@router.post("/stock/{transformer}")
async def get_stock_data_transformed(
    request: StockRequest, 
    transformer: str = "default"
):
    stock_data = await stock_service.get_stock_info(request.symbol)
    
    if not stock_data:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    transformed_data = DataTransformer.transform_stock_data(
        stock_data, transformer
    )
    
    return {
        "success": True,
        "data": transformed_data,
        "timestamp": datetime.utcnow().isoformat()
    }
```

#### 3.2.2 페이지네이션 구현
```python
# 1. 페이지네이션 파라미터 모델
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$", description="Sort order")

# 2. 페이지네이션 결과 모델
class PaginatedResponse(BaseModel):
    success: bool
    data: List[Any]
    pagination: Dict[str, Any]
    timestamp: str

# 3. 커서 기반 페이지네이션
class CursorPaginationParams(BaseModel):
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    size: int = Field(20, ge=1, le=100, description="Page size")

class CursorPaginationResponse(BaseModel):
    success: bool
    data: List[Any]
    pagination: Dict[str, Any]
    timestamp: str

@router.get("/stocks/paginated")
async def get_stocks_paginated(
    pagination: PaginationParams = Depends(),
    filters: Dict[str, Any] = Depends()
):
    offset = (pagination.page - 1) * pagination.size
    
    # 데이터베이스 쿼리에 페이지네이션 적용
    stocks, total_count = await stock_service.get_stocks_paginated(
        filters=filters,
        offset=offset,
        limit=pagination.size,
        sort_by=pagination.sort_by,
        sort_order=pagination.sort_order
    )
    
    total_pages = (total_count + pagination.size - 1) // pagination.size
    
    return PaginatedResponse(
        success=True,
        data=stocks,
        pagination={
            "page": pagination.page,
            "size": pagination.size,
            "total": total_count,
            "pages": total_pages,
            "has_next": pagination.page < total_pages,
            "has_prev": pagination.page > 1
        },
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/stocks/cursor")
async def get_stocks_cursor_paginated(
    pagination: CursorPaginationParams = Depends(),
    filters: Dict[str, Any] = Depends()
):
    # 커서 기반 페이지네이션
    stocks, next_cursor, has_more = await stock_service.get_stocks_cursor_paginated(
        filters=filters,
        cursor=pagination.cursor,
        limit=pagination.size
    )
    
    return CursorPaginationResponse(
        success=True,
        data=stocks,
        pagination={
            "cursor": next_cursor,
            "has_more": has_more,
            "size": pagination.size
        },
        timestamp=datetime.utcnow().isoformat()
    )
```

#### 3.2.3 동적 필터링 및 정렬
```python
# 1. 고급 필터 모델
class AdvancedFilterParams(BaseModel):
    symbols: Optional[List[str]] = Field(None, description="Stock symbols filter")
    sectors: Optional[List[str]] = Field(None, description="Sectors filter")
    market_cap_min: Optional[float] = Field(None, ge=0, description="Minimum market cap")
    market_cap_max: Optional[float] = Field(None, ge=0, description="Maximum market cap")
    price_min: Optional[float] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price")
    sentiment_range: Optional[Tuple[float, float]] = Field(None, description="Sentiment score range")
    exchange: Optional[str] = Field(None, description="Exchange filter")
    stock_type: Optional[str] = Field(None, regex="^(EQUITY|ETF|MUTUAL_FUND|CRYPTOCURRENCY|INDEX)$")

# 2. 동적 정렬 모델
class DynamicSortParams(BaseModel):
    sort_by: str = Field("symbol", description="Sort field")
    sort_order: str = Field("asc", regex="^(asc|desc)$", description="Sort order")
    multi_sort: Optional[List[Dict[str, str]]] = Field(
        None, 
        description="Multi-field sorting"
    )

# 3. 필터링 및 정렬 적용
@router.post("/stocks/filtered")
async def get_stocks_filtered(
    filters: AdvancedFilterParams,
    pagination: PaginationParams,
    sort: DynamicSortParams
):
    # 필터링 조건 동적 생성
    filter_conditions = {}
    
    if filters.symbols:
        filter_conditions["symbols"] = filters.symbols
    
    if filters.sectors:
        filter_conditions["sectors"] = filters.sectors
    
    if filters.market_cap_min is not None:
        filter_conditions["market_cap_min"] = filters.market_cap_min
    
    if filters.market_cap_max is not None:
        filter_conditions["market_cap_max"] = filters.market_cap_max
    
    if filters.price_min is not None:
        filter_conditions["price_min"] = filters.price_min
    
    if filters.price_max is not None:
        filter_conditions["price_max"] = filters.price_max
    
    if filters.sentiment_range:
        filter_conditions["sentiment_min"] = filters.sentiment_range[0]
        filter_conditions["sentiment_max"] = filters.sentiment_range[1]
    
    # 정렬 조건 동적 생성
    sort_conditions = []
    
    if sort.multi_sort:
        for sort_field in sort.multi_sort:
            sort_conditions.append({
                "field": sort_field.get("field"),
                "order": sort_field.get("order", "asc")
            })
    else:
        sort_conditions.append({
            "field": sort.sort_by,
            "order": sort.sort_order
        })
    
    # 필터링 및 정렬 적용된 데이터 조회
    stocks, total_count = await stock_service.get_stocks_advanced_filtered(
        filters=filter_conditions,
        sort=sort_conditions,
        offset=(pagination.page - 1) * pagination.size,
        limit=pagination.size
    )
    
    return PaginatedResponse(
        success=True,
        data=stocks,
        pagination={
            "page": pagination.page,
            "size": pagination.size,
            "total": total_count,
            "filters_applied": filter_conditions,
            "sort_applied": sort_conditions
        },
        timestamp=datetime.utcnow().isoformat()
    )
```

#### 3.2.4 캐시 전략 미세화
```python
# 1. 엔드포인트별 캐시 전략
class EndpointCacheStrategy:
    def __init__(self):
        self.strategies = {
            "/stock": {
                "ttl": 300,  # 5분
                "key_pattern": "stock:{symbol}",
                "vary_on": ["symbol", "fields"],
                "invalidate_on": ["stock_price_update"]
            },
            "/stocks/search": {
                "ttl": 180,  # 3분
                "key_pattern": "search:{query_hash}",
                "vary_on": ["query", "filters", "sort"],
                "invalidate_on": ["stock_data_update"]
            },
            "/trending": {
                "ttl": 600,  # 10분
                "key_pattern": "trending:{timeframe}",
                "vary_on": ["timeframe", "limit"],
                "invalidate_on": ["sentiment_update"]
            },
            "/sentiment": {
                "ttl": 120,  # 2분
                "key_pattern": "sentiment:{symbol}",
                "vary_on": ["symbol", "timeframe"],
                "invalidate_on": ["sentiment_update"]
            }
        }
    
    def get_cache_config(self, endpoint: str) -> Dict[str, Any]:
        return self.strategies.get(endpoint, {
            "ttl": 60,  # 기본 1분
            "key_pattern": f"{endpoint}:{{default_hash}}",
            "vary_on": [],
            "invalidate_on": []
        })
    
    def generate_cache_key(self, endpoint: str, **kwargs) -> str:
        config = self.get_cache_config(endpoint)
        key_pattern = config["key_pattern"]
        
        # 캐시 키 생성
        try:
            cache_key = key_pattern.format(**kwargs)
        except KeyError:
            # 기본 해시 사용
            cache_key = f"{endpoint}:{hash(str(kwargs))}"
        
        return cache_key

# 2. 캐시 미들웨어
class CacheMiddleware:
    def __init__(self, cache_manager, strategy: EndpointCacheStrategy):
        self.cache_manager = cache_manager
        self.strategy = strategy
    
    async def __call__(self, request: Request, call_next):
        # 캐시 전략 확인
        endpoint = request.url.path
        cache_config = self.strategy.get_cache_config(endpoint)
        
        # 캐시 키 생성
        cache_key = self.strategy.generate_cache_key(
            endpoint, 
            **request.query_params
        )
        
        # 캐시 확인
        cached_response = await self.cache_manager.get(cache_key)
        if cached_response:
            return JSONResponse(
                content=cached_response,
                headers={
                    "X-Cache": "HIT",
                    "X-Cache-Key": cache_key
                }
            )
        
        # API 호출
        response = await call_next(request)
        
        # 캐시에 저장
        if response.status_code == 200:
            response_data = json.loads(response.body)
            await self.cache_manager.set(
                cache_key, 
                response_data, 
                ttl=cache_config["ttl"]
            )
        
        return response

# 3. 캐시 무효화 전략
class CacheInvalidationService:
    def __init__(self, cache_manager, strategy: EndpointCacheStrategy):
        self.cache_manager = cache_manager
        self.strategy = strategy
    
    async def invalidate_on_event(self, event_type: str, **event_data):
        """이벤트 기반 캐시 무효화"""
        # 영향받는 엔드포인트 확인
        affected_endpoints = []
        
        for endpoint, config in self.strategy.strategies.items():
            if event_type in config.get("invalidate_on", []):
                affected_endpoints.append(endpoint)
        
        # 관련 캐시 무효화
        for endpoint in affected_endpoints:
            config = self.strategy.get_cache_config(endpoint)
            pattern = config["key_pattern"].replace("{", "").replace("}", "")
            
            # 패턴 기반 캐시 삭제
            await self.cache_manager.delete_pattern(f"{pattern}*")
```

#### 3.2.5 API 버전 관리
```python
# 1. API 버전 관리자
class APIVersionManager:
    def __init__(self):
        self.versions = {
            "v1": {
                "deprecated": False,
                "sunset_date": None,
                "features": [
                    "basic_stock_data",
                    "sentiment_analysis",
                    "search",
                    "trending"
                ]
            },
            "v2": {
                "deprecated": False,
                "sunset_date": None,
                "features": [
                    "advanced_stock_data",
                    "real_time_sentiment",
                    "advanced_search",
                    "correlation_analysis"
                ]
            }
        }
        self.default_version = "v1"
    
    def get_version_info(self, version: str = None) -> Dict[str, Any]:
        version = version or self.default_version
        return self.versions.get(version, {})
    
    def is_feature_supported(self, feature: str, version: str = None) -> bool:
        version_info = self.get_version_info(version)
        return feature in version_info.get("features", [])
    
    def get_deprecated_versions(self) -> List[str]:
        return [v for v, info in self.versions.items() 
                if info.get("deprecated", False)]

# 2. 버전 관리 미들웨어
class VersionMiddleware:
    def __init__(self, version_manager: APIVersionManager):
        self.version_manager = version_manager
    
    async def __call__(self, request: Request, call_next):
        # 버전 헤더 확인
        api_version = request.headers.get("API-Version", "v1")
        
        # 버전 유효성 확인
        if api_version not in self.version_manager.versions:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Unsupported API version",
                    "supported_versions": list(self.version_manager.versions.keys())
                }
            )
        
        # 버전 정보 요청에 추가
        request.state.api_version = api_version
        request.state.version_info = self.version_manager.get_version_info(api_version)
        
        # 응답 헤더에 버전 정보 추가
        response = await call_next(request)
        response.headers["API-Version"] = api_version
        
        # 버전 폐기 경고
        version_info = self.version_manager.get_version_info(api_version)
        if version_info.get("deprecated", False):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = version_info.get("sunset_date", "")
        
        return response

# 3. 버전별 라우터
class VersionedRouter:
    def __init__(self, version_manager: APIVersionManager):
        self.version_manager = version_manager
        self.routers = {}
    
    def add_versioned_route(self, path: str, endpoint: Callable, versions: List[str]):
        for version in versions:
            if version not in self.routers:
                self.routers[version] = APIRouter()
            
            # 버전별 경로 추가
            versioned_path = f"/{version}{path}"
            self.routers[version].add_api_route(
                versioned_path,
                endpoint,
                methods=["GET", "POST"]
            )
    
    def get_routers(self) -> Dict[str, APIRouter]:
        return self.routers
```

## 4. 성능 모니터링 및 최적화

### 4.1 API 성능 모니터링
```python
# 1. 성능 모니터링 미들웨어
class PerformanceMonitoringMiddleware:
    def __init__(self):
        self.metrics = {
            "request_counts": defaultdict(int),
            "response_times": defaultdict(list),
            "error_rates": defaultdict(float),
            "slow_queries": defaultdict(list)
        }
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 정보 수집
        endpoint = request.url.path
        method = request.method
        
        try:
            response = await call_next(request)
            
            # 응답 시간 측정
            response_time = time.time() - start_time
            
            # 메트릭 기록
            self.metrics["request_counts"][endpoint] += 1
            self.metrics["response_times"][endpoint].append(response_time)
            
            # 느린 쿼리 기록
            if response_time > 1.0:  # 1초 이상
                self.metrics["slow_queries"][endpoint].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "response_time": response_time,
                    "method": method,
                    "query_params": dict(request.query_params)
                })
            
            # 에러율 계산
            if response.status_code >= 400:
                self.metrics["error_rates"][endpoint] += 1
            
            # 응답 헤더에 성능 정보 추가
            response.headers["X-Response-Time"] = str(response_time)
            response.headers["X-Request-ID"] = str(uuid.uuid4())
            
            return response
            
        except Exception as e:
            # 에러 기록
            self.metrics["error_rates"][endpoint] += 1
            
            # 에러 로깅
            logger.error(f"API Error: {str(e)}", exc_info=True)
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": str(uuid.uuid4())
                }
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 요약"""
        summary = {}
        
        for endpoint in self.metrics["request_counts"]:
            response_times = self.metrics["response_times"][endpoint]
            if response_times:
                summary[endpoint] = {
                    "total_requests": self.metrics["request_counts"][endpoint],
                    "avg_response_time": sum(response_times) / len(response_times),
                    "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
                    "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
                    "error_rate": self.metrics["error_rates"][endpoint] / self.metrics["request_counts"][endpoint],
                    "slow_queries_count": len(self.metrics["slow_queries"][endpoint])
                }
        
        return summary

# 2. 데이터베이스 쿼리 모니터링
class DatabaseQueryMonitor:
    def __init__(self):
        self.query_stats = defaultdict(list)
    
    async def monitor_query(self, query: str, params: Dict[str, Any], 
                        execution_time: float, endpoint: str):
        """데이터베이스 쿼리 모니터링"""
        self.query_stats[endpoint].append({
            "query": query,
            "params": params,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 느린 쿼리 경고
        if execution_time > 2.0:  # 2초 이상
            await self._alert_slow_query(query, params, execution_time, endpoint)
    
    async def _alert_slow_query(self, query: str, params: Dict[str, Any], 
                            execution_time: float, endpoint: str):
        """느린 쿼리 경고"""
        logger.warning(f"Slow query detected: {execution_time:.3f}s on {endpoint}")
        logger.warning(f"Query: {query}")
        logger.warning(f"Params: {params}")
        
        # 알림 시스템에 전송
        await self._send_alert({
            "type": "slow_query",
            "endpoint": endpoint,
            "execution_time": execution_time,
            "query": query[:500] + "..." if len(query) > 500 else query
        })
    
    def get_query_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """쿼리 통계 반환"""
        if endpoint:
            return {"queries": self.query_stats[endpoint]}
        
        return {"queries": dict(self.query_stats)}

# 3. 성능 최적화 제안
class PerformanceOptimizer:
    def __init__(self):
        self.recommendations = []
    
    def analyze_performance(self, metrics: Dict[str, Any], 
                         query_stats: Dict[str, Any]) -> List[str]:
        """성능 분석 및 최적화 제안"""
        recommendations = []
        
        # 응답 시간 분석
        for endpoint, metric in metrics.items():
            if metric["p95_response_time"] > 1.0:
                recommendations.append(
                    f"{endpoint} 엔드포인트의 95% 응답 시간이 1초를 초과합니다. "
                    f"캐시 전략을 검토하거나 쿼리 최적화가 필요합니다."
                )
            
            if metric["error_rate"] > 0.05:  # 5% 이상 에러율
                recommendations.append(
                    f"{endpoint} 엔드포인트의 에러율이 5%를 초과합니다. "
                    f"에러 핸들링 및 입력 검증을 강화해야 합니다."
                )
        
        # 쿼리 분석
        for endpoint, queries in query_stats.items():
            slow_queries = [q for q in queries if q["execution_time"] > 2.0]
            if len(slow_queries) > 5:
                recommendations.append(
                    f"{endpoint} 엔드포인트에서 느린 쿼리가 다수 발생합니다. "
                    f"인덱스 최적화나 쿼리 튜닝이 필요합니다."
                )
        
        return recommendations
```

## 5. 결론 및 우선순위

### 5.1 즉시 실행 필요 (1-2주 내)
1. **데이터베이스 인덱스 최적화**
   - 복합 인덱스 추가
   - 부분 인덱스 구현
   - 인덱스 사용 통계 업데이트

2. **API 응답 데이터 최적화**
   - 필드 선택 기능 추가
   - 응답 압축 구현
   - 데이터 변환기 패턴 도입

3. **페이지네이션 구현**
   - 오프셋 기반 페이지네이션
   - 커서 기반 페이지네이션
   - 페이지네이션 메타데이터 제공

### 5.2 단기 실행 (2-4주 내)
1. **데이터베이스 파티셔닝**
   - 시간 기반 파티셔닝 구현
   - 해시 파티셔닝 구현
   - 자동 파티션 관리

2. **동적 필터링 및 정렬**
   - 고급 필터 모델 구현
   - 다중 필드 정렬 지원
   - 필터링 성능 최적화

3. **캐시 전략 미세화**
   - 엔드포인트별 캐시 전략
   - 캐시 무효화 전략
   - 캐시 성능 모니터링

### 5.3 중장기 실행 (1-2개월 내)
1. **API 버전 관리**
   - 버전 관리 시스템 구현
   - 버전별 라우팅
   - 폐기 버전 관리

2. **성능 모니터링 강화**
   - 실시간 성능 모니터링
   - 자동 최적화 제안
   - 성능 대시보드 구현

3. **데이터 아카이빙**
   - 아카이빙 정책 구현
   - 자동 데이터 아카이빙
   - 아카이브된 데이터 조회

이러한 최적화 방안들을 단계적으로 구현함으로써, InsiteChart API의 성능을 크게 향상시키고 더 나은 사용자 경험을 제공할 수 있습니다.