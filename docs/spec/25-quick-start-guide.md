# InsiteChart 스펙 문서 수정 빠른 시작 가이드

## 1. 개요

본 가이드는 InsiteChart 프로젝트 스펙 문서 수정 작업을 즉시 시작할 수 있도록 구체적인 시작 단계와 첫 번째 수정 작업을 안내합니다. [`23-implementation-guide.md`](23-implementation-guide.md)의 상세 가이드를 요약하고, 바로 실행할 수 있는 명령어와 스크립트를 제공합니다.

## 2. 시작 전 준비 사항

### 2.1 환경 설정
```bash
# 1. 작업 디렉토리 이동
cd docs/spec

# 2. 백업 디렉토리 생성
mkdir -p backup/$(date +%Y%m%d)
cp *.md backup/$(date +%Y%m%d)/

# 3. 작업 브랜치 생성 (Git 사용 시)
git checkout -b spec-modifications
git add backup/$(date +%Y%m%d)/
git commit -m "Backup original spec files before modifications"
```

### 2.2 필요 도구 설치
```bash
# Python 환경 확인
python --version

# 필요한 라이브러리 설치
pip install requests beautifulsoup4 markdown

# 검증 스크립트 실행 권한 부여
chmod +x scripts/validate_*.py
```

## 3. 첫 번째 수정 작업: 데이터 모델 표준화

### 3.1 수정 대상 파일 확인
```bash
# 수정 대상 파일 목록 확인
ls -la 11-integrated-data-model.md 16-correlation-analysis.md 18-spec-compatibility-analysis.md
```

### 3.2 자동화된 수정 스크립트 실행

#### Step 1: 데이터 모델 표준화 스크립트 생성
```bash
# 스크립트 디렉토리 생성
mkdir -p scripts

# 데이터 모델 수정 스크립트 생성
cat > scripts/fix_data_models.py << 'EOF'
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
        "11-integrated-data-model.md",
        "16-correlation-analysis.md", 
        "18-spec-compatibility-analysis.md"
    ]
    
    # 각 파일 수정
    for file_path in target_files:
        if os.path.exists(file_path):
            fix_file(file_path)
        else:
            print(f"파일을 찾을 수 없음: {file_path}")
    
    print("데이터 모델 표준화 수정 완료!")
EOF

# 스크립트 실행 권한 부여
chmod +x scripts/fix_data_models.py
```

#### Step 2: 데이터 모델 수정 스크립트 실행
```bash
# 스크립트 실행
python scripts/fix_data_models.py

# 수정 결과 확인
diff backup/$(date +%Y%m%d)/11-integrated-data-model.md 11-integrated-data-model.md
```

### 3.3 수동 수정 가이드 (자동화 스크립트 실패 시)

#### 11-integrated-data-model.md 수동 수정
```bash
# 1. 파일 열기
vim 11-integrated-data-model.md

# 2. UnifiedStockData 클래스 찾기 (검색: /class UnifiedStockData)

# 3. 기존 클래스 정의를 다음으로 교체:
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

# 4. SentimentPoint 및 MentionDetail 클래스 추가 (없는 경우)
# 5. 저장 및 종료 (:wq)
```

## 4. 수정 검증

### 4.1 자동화된 검증 스크립트 실행
```bash
# 검증 스크립트 생성
cat > scripts/validate_fixes.py << 'EOF'
#!/usr/bin/env python3
"""
수정 내용 검증 스크립트
"""

import os
import re
from pathlib import Path

def validate_unified_stock_data(file_path: str) -> bool:
    """UnifiedStockData 모델 검증"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 필수 필드 확인
    required_fields = [
        'symbol', 'company_name', 'stock_type', 'exchange',
        'sector', 'industry', 'current_price', 'market_cap',
        'sentiment_score', 'last_updated', 'data_sources'
    ]
    
    missing_fields = []
    for field in required_fields:
        if f'{field}:' not in content:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"누락된 필드: {missing_fields}")
        return False
    
    # 새로운 필드 확인
    new_fields = [
        'price_change_24h', 'price_change_pct_24h', 'search_count',
        'last_searched', 'sentiment_history', 'mention_count_7d',
        'trend_start_time', 'mention_details', 'community_breakdown',
        'investment_style_distribution', 'data_quality_score'
    ]
    
    found_new_fields = []
    for field in new_fields:
        if f'{field}:' in content:
            found_new_fields.append(field)
    
    print(f"추가된 새 필드: {found_new_fields}")
    
    # 센티먼트 점수 범위 주석 확인
    if '-100~+100 범위' not in content:
        print("경고: 센티먼트 점수 범위 주석을 추가하세요")
        return False
    
    print(f"✅ {file_path} 검증 통과")
    return True

if __name__ == "__main__":
    target_files = [
        "11-integrated-data-model.md",
        "16-correlation-analysis.md",
        "18-spec-compatibility-analysis.md"
    ]
    
    all_valid = True
    for file_path in target_files:
        if os.path.exists(file_path):
            if not validate_unified_stock_data(file_path):
                all_valid = False
        else:
            print(f"파일을 찾을 수 없음: {file_path}")
            all_valid = False
    
    if all_valid:
        print("🎉 모든 파일 검증 통과!")
    else:
        print("❌ 검증 실패: 수정이 필요합니다")
EOF

# 검증 스크립트 실행
python scripts/validate_fixes.py
```

### 4.2 수동 검증 체크리스트
```bash
# 각 파일에 대해 다음 항목 확인:
echo "=== 11-integrated-data-model.md 검증 ==="
echo "✅ UnifiedStockData 클래스에 모든 필드 포함?"
echo "✅ SentimentPoint 클래스 정의 포함?"
echo "✅ MentionDetail 클래스 정의 포함?"
echo "✅ 센티먼트 점수 범위 주석 (-100~+100) 포함?"
echo "✅ data_quality_score 필드 포함?"

echo ""
echo "=== 16-correlation-analysis.md 검증 ==="
echo "✅ TimeSeriesData.to_unified_stock_data() 메서드 포함?"
echo "✅ 센티먼트 점수 범위 표준화 적용?"

echo ""
echo "=== 18-spec-compatibility-analysis.md 검증 ==="
echo "✅ 표준화된 UnifiedStockData 모델 적용?"
echo "✅ 데이터 변환 규칙 포함?"
```

## 5. 다음 단계: 성능 목표 재설정

### 5.1 성능 목표 수정 스크립트
```bash
# 성능 목표 수정 스크립트 생성
cat > scripts/fix_performance_targets.py << 'EOF'
#!/usr/bin/env python3
"""
성능 목표 재설정 스크립트
"""

import os
import re

def fix_performance_targets(file_path: str) -> bool:
    """성능 목표 수정"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 백업 생성
    backup_path = f"{file_path}.backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 성능 목표 표 수정
    old_patterns = [
        (r'API 응답 시간:\s*200ms', 'API 응답 시간: 500ms'),
        (r'동시 사용자:\s*1000명', '동시 사용자: 1000명'),
        (r'상관관계 분석:\s*5초', '상관관계 분석: 5000ms'),
    ]
    
    modified_content = content
    for old_pattern, new_text in old_patterns:
        modified_content = re.sub(old_pattern, new_text, modified_content)
    
    # 단계별 성능 목표 추가
    if '단계별 성능 목표' not in modified_content:
        performance_section = '''
## 3. 단계별 성능 목표

### 3.1 MVP 단계 성능 목표
- API 응답 시간: 1000ms 이하
- 동시 사용자: 50명 지원
- 시스템 가용성: 99% 이상
- 데이터 신선도: 5분 이내

### 3.2 베타 단계 성능 목표
- API 응답 시간: 700ms 이하
- 동시 사용자: 200명 지원
- 시스템 가용성: 99.5% 이상
- 데이터 신선도: 3분 이내

### 3.3 정식 버전 성능 목표
- API 응답 시간: 500ms 이하
- 동시 사용자: 1000명 지원
- 시스템 가용성: 99.9% 이상
- 데이터 신선도: 1분 이내
'''
        
        # 적절한 위치에 삽입
        if '## 3.' in modified_content:
            modified_content = re.sub(r'## 3\.', performance_section + '\n\n## 3.', modified_content)
        else:
            modified_content += '\n\n' + performance_section
    
    # 수정된 내용 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"수정 완료: {file_path}")
    return True

if __name__ == "__main__":
    target_files = [
        "04-performance-scalability.md",
        "12-api-gateway-routing.md",
        "17-final-implementation-roadmap.md"
    ]
    
    for file_path in target_files:
        if os.path.exists(file_path):
            fix_performance_targets(file_path)
        else:
            print(f"파일을 찾을 수 없음: {file_path}")
    
    print("성능 목표 재설정 완료!")
EOF

# 스크립트 실행
python scripts/fix_performance_targets.py
```

## 6. 진행 상황 추적

### 6.1 진행 상황 기록
```bash
# 진행 상황 파일 생성
cat > progress.md << 'EOF'
# InsiteChart 스펙 문서 수정 진행 상황

## 완료된 작업
- [x] 스펙 문서 전면 검토 (2024-11-05)
- [x] 핵심 문제점 식별
- [x] 수정 보완 방안 수립
- [x] 실행 계획 수립

## 현재 진행 중
- [ ] 데이터 모델 표준화 (1순위)
  - [x] 11-integrated-data-model.md 수정
  - [ ] 16-correlation-analysis.md 수정
  - [ ] 18-spec-compatibility-analysis.md 수정

## 다음 단계
- [ ] 성능 목표 재설정 (1숨위)
- [ ] 구현 일정 현실화 (1숨위)
- [ ] 기능 단순화 (2숨위)

## 문제점 및 해결 방안
### 현재 문제점
- 없음

### 해결 방안
- 없음

## 노트
- 2024-11-07: 데이터 모델 표준화 시작
EOF
```

### 6.2 Git 커밋 템플릿
```bash
# 커밋 메시지 템플릿
cat > .gitmessage << 'EOF'
feat: 데이터 모델 표준화

- UnifiedStockData 모델 표준화 완료
- SentimentPoint 및 MentionDetail 클래스 추가
- 센티먼트 점수 범위를 -100~+100으로 표준화
- 데이터 품질 점수 필드 추가

Closes #ISSUE-NUMBER
EOF

# Git 설정
git config commit.template .gitmessage
```

## 7. 자주 묻는 질문 (FAQ)

### Q1: 수정 중 오류가 발생하면 어떻게 하나요?
A1: 백업 파일에서 복원하세요.
```bash
# 백업에서 복원
cp backup/$(date +%Y%m%d)/11-integrated-data-model.md.backup 11-integrated-data-model.md
```

### Q2: 수정 내용을 어떻게 확인하나요?
A2: diff 명령어로 확인하세요.
```bash
# 수정 내용 확인
diff backup/$(date +%Y%m%d)/11-integrated-data-model.md 11-integrated-data-model.md
```

### Q3: 여러 파일을 한 번에 수정할 수 있나요?
A3: 네, 제공된 스크립트를 사용하면 여러 파일을 한 번에 수정할 수 있습니다.
```bash
# 모든 수정 스크립트 실행
python scripts/fix_data_models.py
python scripts/fix_performance_targets.py
```

### Q4: 검증은 어떻게 하나요?
A4: 제공된 검증 스크립트를 실행하세요.
```bash
# 검증 스크립트 실행
python scripts/validate_fixes.py
```

## 8. 다음 단계 안내

### 8.1 1순위 수정 완료 후
1. **성능 목표 재설정**: [`scripts/fix_performance_targets.py`](scripts/fix_performance_targets.py) 실행
2. **구현 일정 현실화**: [`scripts/fix_timeline.py`](scripts/fix_timeline.py) 실행
3. **통합 검증**: [`scripts/validate_all.py`](scripts/validate_all.py) 실행

### 8.2 2순위 수정 준비
1. **기능 단순화**: 상관관계 분석, 실시간 동기화, 캐싱 시스템 단순화
2. **아키텍처 단순화**: 시스템 아키텍처, API 게이트웨이 단순화

### 8.3 지속적인 개선
1. **피드백 수집**: 팀원들의 피드백 수집 및 반영
2. **지속적 검증**: 수정 후 반드시 검증 수행
3. **문서화**: 모든 수정 사항을 변경 이력으로 기록

## 9. 연락 정보

- **프로젝트 매니저**: [이름] ([이메일])
- **아키텍트**: [이름] ([이메일])
- **기술 지원**: [이름] ([이메일])

---

*본 가이드는 InsiteChart 프로젝트 스펙 문서 수정을 위한 빠른 시작 안내이며, 상세한 내용은 [`23-implementation-guide.md`](23-implementation-guide.md)를 참고하세요.*