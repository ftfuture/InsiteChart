# 데이터 모델 일관성 분석 보고서

## 개요

InsiteChart 플랫폼의 데이터 모델 일관성을 분석하고 개선 사항을 식별한 보고서입니다. 이 분석은 SQLAlchemy 데이터베이스 모델과 통합 데이터 모델 간의 일관성, 관계 구조, 데이터 무결성 등을 다룹니다.

## 현재 데이터 모델 아키텍처

### 1. 데이터베이스 모델 (database_models.py)

SQLAlchemy를 사용한 영구 데이터 저장을 위한 모델들:

- **User**: 사용자 정보 관리
- **APIKey**: API 인증 키 관리
- **Stock**: 주식 기본 정보
- **StockPrice**: 주식 가격 데이터
- **SentimentData**: 감성 분석 데이터
- **WatchlistItem**: 사용자 감시 목록
- **SearchHistory**: 검색 기록
- **UserSession**: 사용자 세션
- **SystemLog**: 시스템 로그
- **UserFeedback**: 사용자 피드백
- **UserActivity**: 사용자 활동 추적
- **FeatureUsage**: 기능 사용 통계
- **UserBehavior**: 사용자 행동 분석

### 2. 통합 데이터 모델 (unified_models.py)

서비스 간 데이터 교환을 위한 표준화된 모델들:

- **UnifiedStockData**: 주식 데이터의 통합 모델
- **SentimentResult**: 감성 분석 결과
- **StockMention**: 소셜 미디어 언급 데이터
- **SearchQuery/SearchResult**: 검색 관련 모델
- **APIKey**: API 키 관리
- **다양한 Enum 클래스**: 데이터 표준화

## 강점

### 1. 잘 정의된 관계 구조
- 명확한 외래 키 관계 정의
- 적절한 인덱스 설정으로 성능 최적화
- 계단식 삭제(CASCADE) 설정으로 데이터 무결성 보장

### 2. 포괄적인 데이터 모델
- 사용자 활동 추적을 위한 상세한 모델
- 감성 분석 데이터의 다양한 차원 지원
- 시스템 모니터링을 위한 로깅 모델

### 3. 표준화된 통합 모델
- 서비스 간 데이터 일관성 보장
- 데이터 검증 및 품질 점수 계산
- 유연한 데이터 병합 기능

### 4. 적절한 인덱싱
- 조회 성능 최적화를 위한 복합 인덱스
- 시간 기반 데이터에 대한 효율적 인덱싱
- 검색 성능 향상을 위한 전문 인덱스

## 개선이 필요한 영역

### 1. 모델 간 불일치 (높은 우선순위)

**문제점**:
- 데이터베이스 모델과 통합 모델 간의 필드명 불일치
- 데이터 타입 불일치 (예: Float vs Decimal)
- 감성 점수 범위 불일치 (-1~1 vs -100~100)

**구체적 예시**:
```python
# database_models.py - SentimentData
compound_score = Column(Float, nullable=False)  # -1 to 1 range

# unified_models.py - SentimentResult  
compound_score: float  # -100 to 100 range (standardized)
```

**개선 방안**:
```python
# 통합된 데이터 표준 정의
class DataStandards:
    SENTIMENT_SCORE_RANGE = (-100.0, 100.0)
    PRICE_PRECISION = 4
    VOLUME_PRECISION = 0
    
    @staticmethod
    def normalize_sentiment_score(score: float, source_range: tuple = (-1.0, 1.0)) -> float:
        """감성 점수를 표준 범위로 정규화"""
        source_min, source_max = source_range
        target_min, target_max = DataStandards.SENTIMENT_SCORE_RANGE
        
        # 선형 변환
        normalized = ((score - source_min) / (source_max - source_min)) * (target_max - target_min) + target_min
        return max(target_min, min(target_max, normalized))
```

### 2. 데이터 무결성 제약 부족 (높은 우선순위)

**문제점**:
- 중요 필드에 대한 NOT NULL 제약 부족
- 참조 무결성 검증 부족
- 비즈니스 규칙에 대한 데이터베이스 레벨 제약 부족

**구체적 예시**:
```python
# 현재 모델
class Stock(Base):
    market_cap = Column(Float, nullable=True)  # NULL 허용
    sector = Column(String(100), nullable=True)  # NULL 허용

# 개선된 모델
class Stock(Base):
    market_cap = Column(Float, nullable=False)  # 필수 필드
    sector = Column(String(100), nullable=False)  # 필수 필드
    
    # 비즈니스 규칙 제약
    __table_args__ = (
        CheckConstraint('market_cap >= 0', name='check_market_cap_positive'),
        CheckConstraint("stock_type IN ('EQUITY', 'ETF', 'MUTUAL_FUND', 'CRYPTO', 'INDEX')", 
                     name='check_valid_stock_type'),
    )
```

### 3. 감성 데이터 중복 (중간 우선순위)

**문제점**:
- 여러 모델에서 감성 데이터 중복 정의
- 불일치하는 감성 점수 계산 방식
- 중복된 감성 소스 정의

**개선 방안**:
```python
# 통합된 감성 데이터 모델
class UnifiedSentimentData(Base):
    """통합된 감성 데이터 모델"""
    __tablename__ = "unified_sentiment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    source = Column(Enum(SentimentSource), nullable=False)
    
    # 표준화된 감성 점수 (-100 to 100)
    standardized_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # 원본 점수 보존
    raw_score = Column(Float, nullable=True)
    raw_score_range = Column(String(20), nullable=True)  # "-1,1" or "-100,100"
    
    # 메타데이터
    model_version = Column(String(20), nullable=False)
    processing_timestamp = Column(DateTime, default=func.now())
    
    # 관계 정의
    stock = relationship("Stock", back_populates="sentiment_data")
```

### 4. 시간 데이터 불일치 (중간 우선순위)

**문제점**:
- 여러 모델에서 시간 필드명 불일치
- 타임존 처리 부족
- 시간 정밀도 불일치

**구체적 예시**:
```python
# 불일치하는 시간 필드명
created_at = Column(DateTime, default=func.now())  # 일부 모델
timestamp = Column(DateTime, default=func.now())  # 다른 모델
last_updated = Column(DateTime, default=func.now())  # 또 다른 모델
```

**개선 방안**:
```python
# 표준 시간 필드 믹스인
class TimestampMixin:
    """표준 시간 필드 믹스인"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # 소프트 삭제
    
    # 타임존 표준화
    timezone = Column(String(50), default="UTC", nullable=False)

# 사용 예시
class Stock(Base, TimestampMixin):
    symbol = Column(String(10), unique=True, nullable=False)
    # 다른 필드들...
```

### 5. 데이터 검증 부족 (중간 우선순위)

**문제점**:
- 모델 레벨에서의 데이터 검증 부족
- 잘못된 데이터 형식 허용
- 비즈니스 규칙 검증 부족

**개선 방안**:
```python
# 데이터 검증 데코레이터
def validate_field(validator_func, error_message: str):
    """필드 검증 데코레이터"""
    def decorator(cls):
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            # 필드 검증
            for field_name, value in kwargs.items():
                if not validator_func(field_name, value):
                    raise ValueError(f"{error_message}: {field_name}={value}")
            
            original_init(self, *args, **kwargs)
        
        cls.__init__ = new_init
        return cls
    return decorator

# 사용 예시
@validate_field(
    lambda field, value: field != 'symbol' or (isinstance(value, str) and len(value) <= 10),
    "Invalid symbol format"
)
class Stock(Base):
    symbol = Column(String(10), unique=True, nullable=False)
```

### 6. API 응답 모델 부족 (낮은 우선순위)

**문제점**:
- API 응답을 위한 Pydantic 모델 부족
- 데이터 직렬화 불일치
- API 버전 관리 부족

**개선 방안**:
```python
# API 응답 모델
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class StockResponse(BaseModel):
    """주식 데이터 API 응답 모델"""
    symbol: str = Field(..., description="주식 심볼")
    company_name: str = Field(..., description="회사명")
    current_price: Optional[float] = Field(None, description="현재 가격")
    overall_sentiment: Optional[float] = Field(None, ge=-100, le=100, description="전체 감성 점수")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v) > 10:
            raise ValueError('Invalid symbol format')
        return v.upper()
    
    class Config:
        orm_mode = True  # SQLAlchemy 모델 호환
```

### 7. 마이그레이션 전략 부족 (낮은 우선순위)

**문제점**:
- 데이터베이스 스키마 변경 관리 부족
- 롤백 전략 부족
- 데이터 마이그레이션 스크립트 부족

**개선 방안**:
```python
# 마이그레이션 관리
class MigrationManager:
    """데이터베이스 마이그레이션 관리자"""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.migration_history = []
    
    def apply_migration(self, migration_script):
        """마이그레이션 적용"""
        try:
            # 트랜잭션 시작
            with self.db_session.begin():
                # 마이그레이션 실행
                migration_script.execute(self.db_session)
                
                # 마이그레이션 기록
                self._record_migration(migration_script)
                
        except Exception as e:
            # 롤백
            self.db_session.rollback()
            raise MigrationError(f"Migration failed: {str(e)}")
```

## 우선순위별 개선 계획

### 1단계 (즉시 실행)
1. **데이터 표준화**
   - 감성 점수 범위 통일
   - 필드명 표준화
   - 데이터 타입 일관성 확보

2. **데이터 무결성 강화**
   - 필수 필드에 NOT NULL 제약 추가
   - 비즈니스 규칙 제약 조건 추가
   - 참조 무결성 검증 강화

### 2단계 (단기)
1. **감성 데이터 통합**
   - 중복된 감성 모델 통합
   - 표준화된 감성 데이터 파이프라인
   - 데이터 품질 검증 강화

2. **시간 데이터 표준화**
   - Timestamp 믹스인 도입
   - 타임존 처리 표준화
   - 시간 정밀도 통일

### 3단계 (중기)
1. **데이터 검증 강화**
   - 모델 레벨 검증 추가
   - 데이터 형식 검증 강화
   - 비즈니스 규칙 검증 구현

2. **API 응답 모델 구현**
   - Pydantic 응답 모델 추가
   - API 버전 관리 시스템
   - 데이터 직렬화 표준화

### 4단계 (장기)
1. **마이그레이션 전략**
   - 자동화된 마이그레이션 시스템
   - 롤백 및 복구 전략
   - 데이터 마이그레이션 모니터링

2. **데이터 거버넌스**
   - 데이터 라이프사이클 관리
   - 데이터 품질 모니터링
   - 규정 준수 검증

## 기술적 권장사항

### 1. 데이터 모델 패턴
- **Active Record 패턴**: 간단한 CRUD 작업에 적합
- **Data Mapper 패턴**: 복잡한 비즈니스 로직에 적합
- **Repository 패턴**: 데이터 접근 계층 분리

### 2. 데이터 검증 프레임워크
- **Pydantic**: 데이터 검증 및 직렬화
- **Marshmallow**: 복잡한 데이터 변환
- **SQLAlchemy Events**: 데이터베이스 레벨 검증

### 3. 마이그레이션 도구
- **Alembic**: SQLAlchemy 마이그레이션
- **Flyway**: Java 기반 마이그레이션
- **Liquibase**: 데이터베이스 변경 관리

### 4. 데이터 품질 도구
- **Great Expectations**: 데이터 품질 검증
- **Pandera**: Pandas 데이터 검증
- **Cerberus**: 스키마 검증

## 구현 예시

### 1. 통합된 주식 데이터 모델
```python
class UnifiedStockModel(Base, TimestampMixin):
    """통합된 주식 데이터 모델"""
    __tablename__ = "unified_stocks"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    stock_type = Column(Enum(StockType), nullable=False, default=StockType.EQUITY)
    
    # 가격 정보 (표준화된 정밀도)
    current_price = Column(Numeric(10, 4), nullable=True)
    previous_close = Column(Numeric(10, 4), nullable=True)
    day_change = Column(Numeric(10, 4), nullable=True)
    
    # 감성 정보 (표준화된 범위)
    overall_sentiment = Column(Float, nullable=True)
    sentiment_sources = Column(JSON, nullable=True)
    
    # 데이터 품질
    data_quality_score = Column(Float, default=1.0)
    last_updated = Column(DateTime, default=func.now())
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('current_price >= 0', name='check_price_positive'),
        CheckConstraint('overall_sentiment >= -100 AND overall_sentiment <= 100', 
                     name='check_sentiment_range'),
        Index('idx_stock_symbol', 'symbol'),
        Index('idx_stock_sentiment', 'overall_sentiment'),
    )
```

### 2. 데이터 검증 서비스
```python
class DataValidationService:
    """데이터 검증 서비스"""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def validate_stock_data(self, stock_data: dict) -> tuple[bool, list]:
        """주식 데이터 검증"""
        errors = []
        
        # 필수 필드 검증
        required_fields = ['symbol', 'company_name', 'stock_type']
        for field in required_fields:
            if field not in stock_data or stock_data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # 데이터 형식 검증
        if 'symbol' in stock_data:
            symbol = stock_data['symbol']
            if not isinstance(symbol, str) or len(symbol) > 10:
                errors.append("Invalid symbol format")
        
        # 비즈니스 규칙 검증
        if 'current_price' in stock_data:
            price = stock_data['current_price']
            if price is not None and price <= 0:
                errors.append("Price must be positive")
        
        return len(errors) == 0, errors
    
    def validate_sentiment_data(self, sentiment_data: dict) -> tuple[bool, list]:
        """감성 데이터 검증"""
        errors = []
        
        # 감성 점수 범위 검증
        if 'overall_sentiment' in sentiment_data:
            score = sentiment_data['overall_sentiment']
            if score is not None and (score < -100 or score > 100):
                errors.append("Sentiment score must be between -100 and 100")
        
        return len(errors) == 0, errors
```

## 결론

InsiteChart 플랫폼의 데이터 모델은 포괄적인 기능을 제공하지만, 모델 간 일관성 부족과 데이터 무결성 제약이 개선이 필요합니다. 특히 감성 데이터의 표준화와 데이터 검증 강화가 시급합니다.

단계적인 접근을 통해 데이터 모델 일관성을 개선하고 데이터 품질을 향상시킬 수 있습니다. 이를 통해 시스템의 안정성과 신뢰성을 크게 향상시킬 수 있을 것입니다.

장기적으로는 데이터 거버넌스 체계를 구축하여 데이터 라이프사이클을 체계적으로 관리하고 규정 준수를 보장해야 합니다.