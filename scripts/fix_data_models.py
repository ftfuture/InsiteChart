#!/usr/bin/env python3
"""
데이터 모델 표준화 자동 수정 스크립트
"""

import os
import re
from pathlib import Path

def fix_unified_stock_data_model(content: str) -> str:
    """UnifiedStockData 모델 표준화"""
    # 기존 클래스 정의 찾기
    class_pattern = r'@dataclass\s*\nclass UnifiedStockData:.*?(?=\n\n|\nclass|\Z)'
    
    # 새로운 표준화된 클래스 정의
    new_class = '''@dataclass
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
    is_spam: bool = False'''
    
    # 기존 클래스를 새로운 클래스로 교체
    modified_content = re.sub(class_pattern, new_class, content, flags=re.DOTALL)
    
    return modified_content

def fix_file(file_path: str):
    """파일 수정"""
    print(f"수정 중: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 백업 파일 생성
    backup_path = f"{file_path}.backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"백업 생성: {backup_path}")
    
    # 내용 수정
    modified_content = fix_unified_stock_data_model(content)
    
    # 수정된 내용 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"수정 완료: {file_path}")
    return True

if __name__ == "__main__":
    # 수정 대상 파일
    target_files = [
        "docs/spec/11-integrated-data-model.md",
        "docs/spec/16-correlation-analysis.md", 
        "docs/spec/18-spec-compatibility-analysis.md"
    ]
    
    # 각 파일 수정
    for file_path in target_files:
        if os.path.exists(file_path):
            fix_file(file_path)
        else:
            print(f"파일을 찾을 수 없음: {file_path}")
    
    print("데이터 모델 표준화 수정 완료!")