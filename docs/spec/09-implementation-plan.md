# 구현 계획

## 1. 프로젝트 로드맵

### 1.1 개발 단계 계획

```mermaid
gantt
    title InsiteChart 프로젝트 로드맵
    dateFormat  YYYY-MM-DD
    section 1단계: 기반 구축
    프로젝트 설정           :done, setup, 2024-01-01, 2024-01-07
    데이터베이스 설계       :done, db-design, 2024-01-08, 2024-01-21
    API 아키텍처 구축    :done, api-arch, 2024-01-15, 2024-01-28
    기본 UI 프레임워크    :done, ui-framework, 2024-01-22, 2024-02-04
    
    section 2단계: 핵심 기능
    주식 검색 엔진       :active, stock-search, 2024-01-29, 2024-02-25
    데이터 수집 파이프라인 :data-pipeline, after stock-search, 2024-02-05, 2024-03-04
    센티먼트 분석        :sentiment, after data-pipeline, 2024-02-19, 2024-03-18
    사용자 인증 시스템    :auth, after stock-search, 2024-02-12, 2024-03-11
    
    section 3단계: 고급 기능
    실시간 알림          :realtime, 2024-03-11, 2024-04-08
    포트폴리오 관리       :portfolio, after sentiment, 2024-03-25, 2024-04-22
    고급 분석 도구        :analytics, after portfolio, 2024-04-01, 2024-04-29
    모바일 앱              :mobile, after analytics, 2024-04-15, 2024-05-27
    
    section 4단계: 최적화
    성능 최적화           :perf-opt, after mobile, 2024-05-13, 2024-06-10
    보안 강화              :security, after perf-opt, 2024-05-20, 2024-06-17
    접근성 개선           :a11y, after security, 2024-06-03, 2024-06-24
    테스트 자동화          :testing, after a11y, 2024-06-10, 2024-07-01
    
    section 5단계: 배포
    베타 배포              :beta, after testing, 2024-06-24, 2024-07-15
    사용자 테스트           :user-testing, after beta, 2024-07-08, 2024-07-22
    프로덕션 배포          :production, after user-testing, 2024-07-16, 2024-07-29
    모니터링 설정           :monitoring, after production, 2024-07-23, 2024-08-05
```

### 1.2 마일스톤 정의

#### 1.2.1 기술적 마일스톤
- **MVP (Minimum Viable Product)**: 기본 주식 검색 및 간단한 센티먼트 표시
- **Alpha 버전**: 전체 기능 구현, 내부 테스트 가능
- **Beta 버전**: 외부 테스터 대상, 안정성 확보
- **정식 버전**: 프로덕션 환경 배포, 일반 사용자 대상

#### 1.2.2 비즈니스 마일스톤
- **사용자 100명 달성**: 초기 사용자 확보
- **데이터 소스 5개 연동**: 다양한 데이터 소스 통합
- **실시간 처리 1,000 TPS**: 시스템 성능 목표 달성
- **모바일 앱 출시**: 모바일 플랫폼 지원

## 2. 개발 팀 구성

### 2.1 팀 역할 및 책임

```typescript
// team/organization.ts
export interface TeamMember {
  id: string;
  name: string;
  role: TeamRole;
  responsibilities: string[];
  skills: string[];
  experience: number;
}

export type TeamRole = 
  | 'project-manager'
  | 'frontend-lead'
  | 'backend-lead'
  | 'fullstack-developer'
  | 'ui-ux-designer'
  | 'data-scientist'
  | 'devops-engineer'
  | 'qa-engineer'
  | 'security-specialist';

export const teamStructure: TeamMember[] = [
  {
    id: 'pm-001',
    name: '김프로젝트',
    role: 'project-manager',
    responsibilities: [
      '프로젝트 일정 관리',
      '팀 간 조율',
      '이해관계자 커뮤니케이션',
      '위험 관리'
    ],
    skills: ['Agile', 'Scrum', 'JIRA', 'Risk Management'],
    experience: 8
  },
  {
    id: 'fe-001',
    name: '이프론트',
    role: 'frontend-lead',
    responsibilities: [
      '프론트엔드 아키텍처 설계',
      'UI 컴포넌트 라이브러리 개발',
      '반응형 디자인 구현',
      '프론트엔드 팀 멤버 관리'
    ],
    skills: ['React', 'TypeScript', 'CSS-in-JS', 'Accessibility'],
    experience: 6
  },
  {
    id: 'be-001',
    name: '백백엔드',
    role: 'backend-lead',
    responsibilities: [
      '백엔드 아키텍처 설계',
      'API 개발 및 문서화',
      '데이터베이스 설계',
      '백엔드 팀 멤버 관리'
    ],
    skills: ['Python', 'FastAPI', 'PostgreSQL', 'Redis', 'Docker'],
    experience: 7
  },
  {
    id: 'fs-001',
    name: '최풀스택',
    role: 'fullstack-developer',
    responsibilities: [
      '주식 검색 기능 개발',
      '센티먼트 분석 API 개발',
      '사용자 인증 시스템 구현',
      '프론트엔드-백엔드 연동'
    ],
    skills: ['React', 'Python', 'PostgreSQL', 'REST API'],
    experience: 4
  },
  {
    id: 'ux-001',
    name: '디UX디자이너',
    role: 'ui-ux-designer',
    responsibilities: [
      '사용자 경험 설계',
      'UI/UX 디자인',
      '프로토타이핑',
      '디자인 시스템 구축'
    ],
    skills: ['Figma', 'Adobe XD', 'Prototyping', 'User Research'],
    experience: 5
  },
  {
    id: 'ds-001',
    name: '데이터사이언티스트',
    role: 'data-scientist',
    responsibilities: [
      '센티먼트 분석 알고리즘 개발',
      '데이터 모델링',
      '머신러닝 파이프라인 구축',
      '분석 결과 시각화'
    ],
    skills: ['Python', 'NLP', 'Machine Learning', 'Data Analysis'],
    experience: 6
  },
  {
    id: 'devops-001',
    name: '데브옵스엔지니어',
    role: 'devops-engineer',
    responsibilities: [
      'CI/CD 파이프라인 구축',
      '인프라 자동화',
      '모니터링 시스템 구축',
      '배포 및 운영'
    ],
    skills: ['Docker', 'Kubernetes', 'AWS', 'CI/CD', 'Monitoring'],
    experience: 5
  },
  {
    id: 'qa-001',
    name: 'QA엔지니어',
    role: 'qa-engineer',
    responsibilities: [
      '테스트 계획 수립',
      '자동화 테스트 구축',
      '결함 관리',
      '품질 보증'
    ],
    skills: ['Selenium', 'Cypress', 'Test Automation', 'Agile Testing'],
    experience: 4
  },
  {
    id: 'sec-001',
    name: '보안전문가',
    role: 'security-specialist',
    responsibilities: [
      '보안 아키텍처 설계',
      '취약점 분석',
      '보안 정책 수립',
      '보안 감사'
    ],
    skills: ['OWASP', 'Penetration Testing', 'Security Auditing', 'Cryptography'],
    experience: 6
  }
];

// 팀 협업 방식
export const collaborationMethods = {
  dailyStandup: {
    time: '09:30',
    duration: 15,
    participants: ['project-manager', 'frontend-lead', 'backend-lead'],
    agenda: [
      '어제 작업 현황 공유',
      '오늘 작업 계획',
      '장애/이슈 논의'
    ]
  },
  weeklySprint: {
    day: '월요일',
    time: '10:00',
    duration: 60,
    participants: 'all',
    agenda: [
      '지난 스프린트 회고',
      '새 스프린트 계획',
      '백로그 정리',
      '팀별 목표 설정'
    ]
  },
  biweeklyDemo: {
    day: '금요일',
    time: '16:00',
    duration: 90,
    participants: 'all',
    agenda: [
      '최신 기능 시연',
      '사용자 피드백 논의',
      '기술적 도전 과제 공유',
      '다음 스프린트 목표 조정'
    ]
  }
};
```

### 2.2 개발 방법론

#### 2.2.1 애자일 개발 프로세스
```typescript
// development/agileProcess.ts
export interface Sprint {
  id: string;
  name: string;
  startDate: Date;
  endDate: Date;
  duration: number; // days
  goals: string[];
  backlog: UserStory[];
  team: string[];
}

export interface UserStory {
  id: string;
  title: string;
  description: string;
  acceptanceCriteria: string[];
  storyPoints: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'backlog' | 'in-progress' | 'testing' | 'done';
  assignee?: string;
  dependencies: string[];
}

export interface Epic {
  id: string;
  name: string;
  description: string;
  stories: string[];
  priority: number;
}

// 스프린트 계획 예시
export const sprintPlan: Sprint = {
  id: 'sprint-001',
  name: '1주차: 기반 구축',
  startDate: new Date('2024-01-29'),
  endDate: new Date('2024-02-09'),
  duration: 10,
  goals: [
    '프로젝트 기반 환경 구축',
    '데이터베이스 스키마 설계',
    '기본 API 엔드포인트 개발',
    'UI 프레임워크 설정'
  ],
  backlog: [
    {
      id: 'story-001',
      title: '데이터베이스 스키마 설계',
      description: '주식, 센티먼트, 사용자 데이터를 저장할 데이터베이스 스키마 설계',
      acceptanceCriteria: [
        '주식 정보 저장을 위한 테이블 설계',
        '센티먼트 데이터 저장을 위한 테이블 설계',
        '사용자 정보 저장을 위한 테이블 설계',
        '테이블 간 관계 정의',
        '인덱스 설계'
      ],
      storyPoints: 8,
      priority: 'critical',
      status: 'backlog',
      dependencies: []
    },
    {
      id: 'story-002',
      title: 'API 기본 구조 설계',
      description: 'RESTful API 기본 구조와 공통 컴포넌트 설계',
      acceptanceCriteria: [
        'API 라우팅 구조 설계',
        '요청/응답 모델 정의',
        '에러 핸들링 구조 설계',
        '인증/인가 미들웨어 설계',
        '로깅 시스템 구축'
      ],
      storyPoints: 5,
      priority: 'critical',
      status: 'backlog',
      dependencies: ['story-001']
    },
    {
      id: 'story-003',
      title: 'React 프로젝트 설정',
      description: 'React 기반 프론트엔드 프로젝트 초기 설정',
      acceptanceCriteria: [
        '프로젝트 구조 설정',
        '상태 관리 라이브러리 통합',
        '라우팅 설정',
        '기본 컴포넌트 구조',
        '스타일 시스템 설정'
      ],
      storyPoints: 3,
      priority: 'high',
      status: 'backlog',
      dependencies: []
    }
  ],
  team: ['frontend-lead', 'backend-lead', 'fullstack-developer']
};

// 에픽 정의 예시
export const epics: Epic[] = [
  {
    id: 'epic-001',
    name: '주식 검색 기능',
    description: '사용자가 주식을 검색하고 상세 정보를 조회하는 기능',
    stories: ['story-004', 'story-005', 'story-006'],
    priority: 1
  },
  {
    id: 'epic-002',
    name: '센티먼트 분석',
    description: '소셜 미디어 데이터를 분석하여 주식 센티먼트를 제공',
    stories: ['story-007', 'story-008', 'story-009'],
    priority: 2
  },
  {
    id: 'epic-003',
    name: '사용자 관리',
    description: '사용자 가입, 로그인, 프로필 관리 기능',
    stories: ['story-010', 'story-011', 'story-012'],
    priority: 3
  }
];

// 개발 워크플로우
export const developmentWorkflow = {
  planning: {
    description: '스프린트 계획 회의',
    activities: [
      '백로그 리뷰',
      '스토리 포인트 추정',
      '스프린트 목표 설정',
      '역할 분담'
    ],
    outputs: ['스프린트 백로그', '팀별 목표']
  },
  development: {
    description: '개발 단계',
    activities: [
      '피처 브랜치 생성',
      '개발 및 단위 테스트',
      '코드 리뷰',
      '통합 테스트'
    ],
    outputs: ['완료된 기능', '테스트 결과']
  },
  review: {
    description: '검토 단계',
    activities: [
      '기능 시연',
      '코드 품질 검토',
      '사용자 스토리 충족 여부 확인',
      '수용 기준 평가'
    ],
    outputs: ['검토 의견', '수정 사항']
  },
  deployment: {
    description: '배포 단계',
    activities: [
      '메인 브랜치 머지',
      'CI/CD 파이프라인 실행',
      '스테이징 환경 배포',
      '프로덕션 환경 배포'
    ],
    outputs: ['배포된 버전', '배포 보고서']
  },
  retrospective: {
    description: '회고 단계',
    activities: [
      '잘된 점 논의',
      '개선할 점 논의',
      '실행 계약 수립',
      '다음 스프린트 적용'
    ],
    outputs: ['회고 보고서', '개선 계획']
  }
};
```

## 3. 기술 스택 구현

### 3.1 프론트엔드 기술 스택

#### 3.1.1 React 프로젝트 설정
```bash
# 프로젝트 생성
npx create-react-app insitechart-frontend --template typescript
cd insitechart-frontend

# 필수 의존성 설치
npm install @reduxjs/toolkit react-redux react-router-dom
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material @mui/x-charts
npm install axios react-query
npm install react-hook-form @hookform/resolvers yup
npm install date-fns
npm install recharts
npm install react-i18next i18next
npm install @testing-library/jest-dom @testing-library/user-event

# 개발 의존성 설치
npm install -D @types/node
npm install -D eslint-config-prettier prettier
npm install -D husky lint-staged
npm install -D @storybook/react-builder storybook
```

#### 3.1.2 프로젝트 구조
```
src/
├── components/           # 재사용 가능한 컴포넌트
│   ├── common/         # 공통 컴포넌트
│   ├── forms/          # 폼 컴포넌트
│   ├── charts/         # 차트 컴포넌트
│   └── layout/         # 레이아웃 컴포넌트
├── pages/              # 페이지 컴포넌트
│   ├── Dashboard/
│   ├── StockSearch/
│   ├── Sentiment/
│   └── Profile/
├── hooks/              # 커스텀 훅
├── services/           # API 서비스
├── store/              # Redux 상태 관리
├── utils/              # 유틸리티 함수
├── types/              # TypeScript 타입 정의
├── constants/          # 상수 정의
├── styles/             # 스타일 파일
├── assets/             # 정적 자산
├── locales/            # 다국어 파일
└── tests/              # 테스트 파일
```

### 3.2 백엔드 기술 스택

#### 3.2.1 FastAPI 프로젝트 설정
```bash
# 프로젝트 생성
mkdir insitechart-backend
cd insitechart-backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필수 의존성 설치
pip install fastapi uvicorn
pip install sqlalchemy alembic psycopg2-binary asyncpg
pip install redis celery
pip install pydantic python-jose[cryptography] passlib[bcrypt]
pip install python-multipart aiofiles
pip install httpx
pip install pytest pytest-asyncio pytest-cov
pip install black isort flake8 mypy

# 프로젝트 구조 생성
mkdir -p app/{api,core,db,models,schemas,services,utils}
mkdir -p tests/{unit,integration,e2e}
```

#### 3.2.2 프로젝트 구조
```
insitechart-backend/
├── app/
│   ├── api/              # API 라우트
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   └── api.py
│   │   └── deps.py       # 의존성 주입
│   ├── core/              # 핵심 설정
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── db/                # 데이터베이스
│   │   ├── session.py
│   │   ├── base.py
│   │   └── init_db.py
│   ├── models/            # 데이터 모델
│   │   ├── stock.py
│   │   ├── sentiment.py
│   │   └── user.py
│   ├── schemas/           # Pydantic 스키마
│   │   ├── stock.py
│   │   ├── sentiment.py
│   │   └── user.py
│   ├── services/          # 비즈니스 로직
│   │   ├── stock_service.py
│   │   ├── sentiment_service.py
│   │   └── user_service.py
│   └── utils/             # 유틸리티
│       ├── auth.py
│       ├── cache.py
│       └── helpers.py
├── alembic/              # 데이터베이스 마이그레이션
├── tests/                 # 테스트
├── requirements.txt        # 프로덕션 의존성
├── requirements-dev.txt    # 개발 의존성
└── main.py               # 애플리케이션 진입점
```

## 4. 데이터베이스 구현

### 4.1 PostgreSQL 스키마

#### 4.1.1 테이블 생성 스크립트
```sql
-- 01_create_users_table.sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- 02_create_stocks_table.sql
CREATE TABLE stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    stock_type VARCHAR(50),
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    description TEXT,
    website VARCHAR(255),
    country VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 03_create_stock_prices_table.sql
CREATE TABLE stock_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    open_price DECIMAL(10, 2) NOT NULL,
    high_price DECIMAL(10, 2) NOT NULL,
    low_price DECIMAL(10, 2) NOT NULL,
    close_price DECIMAL(10, 2) NOT NULL,
    adjusted_close_price DECIMAL(10, 2),
    volume BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TimescaleDB 하이퍼테이블 생성
SELECT create_hypertable('stock_prices', 'price_date', chunk_time_interval => INTERVAL '1 day');

-- 04_create_sentiment_data_table.sql
CREATE TABLE sentiment_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    overall_sentiment DECIMAL(3, 2) NOT NULL, -- -1.00 to 1.00
    reddit_sentiment DECIMAL(3, 2),
    twitter_sentiment DECIMAL(3, 2),
    mention_count INTEGER DEFAULT 0,
    positive_mentions INTEGER DEFAULT 0,
    negative_mentions INTEGER DEFAULT 0,
    neutral_mentions INTEGER DEFAULT 0,
    confidence_score DECIMAL(3, 2),
    analysis_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TimescaleDB 하이퍼테이블 생성
SELECT create_hypertable('sentiment_data', 'analysis_date', chunk_time_interval => INTERVAL '1 day');

-- 05_create_stock_mentions_table.sql
CREATE TABLE stock_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL, -- 'reddit', 'twitter', 'news'
    community VARCHAR(100),
    author VARCHAR(100),
    text TEXT NOT NULL,
    url TEXT,
    upvotes INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    sentiment_score DECIMAL(3, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TimescaleDB 하이퍼테이블 생성
SELECT create_hypertable('stock_mentions', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- 06_create_user_watchlists_table.sql
CREATE TABLE user_watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, stock_id)
);

-- 07_create_user_alerts_table.sql
CREATE TABLE user_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- 'price', 'sentiment', 'volume'
    condition VARCHAR(50) NOT NULL, -- 'above', 'below', 'change_percent'
    threshold_value DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 08_create_user_sessions_table.sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 09_create_audit_log_table.sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_stocks_exchange ON stocks(exchange);
CREATE INDEX idx_stocks_sector ON stocks(sector);

CREATE INDEX idx_stock_prices_stock_id_date ON stock_prices(stock_id, price_date DESC);

CREATE INDEX idx_sentiment_data_stock_id_date ON sentiment_data(stock_id, analysis_date DESC);

CREATE INDEX idx_stock_mentions_stock_id_timestamp ON stock_mentions(stock_id, timestamp DESC);
CREATE INDEX idx_stock_mentions_source ON stock_mentions(source);

CREATE INDEX idx_user_watchlists_user_id ON user_watchlists(user_id);
CREATE INDEX idx_user_watchlists_stock_id ON user_watchlists(stock_id);

CREATE INDEX idx_user_alerts_user_id ON user_alerts(user_id);
CREATE INDEX idx_user_alerts_stock_id ON user_alerts(stock_id);

CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

### 4.2 Alembic 마이그레이션

#### 4.2.1 Alembic 설정
```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.config import settings
from app.db.base import Base
from app.models import *  # 모든 모델 임포트

# Alembic Config 객체
config = context.config

# 데이터베이스 URL 설정
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

# 해석된 객체 설정
target_metadata = Base.metadata

def run_migrations_offline():
    """오프라인 모드에서 마이그레이션 실행"""
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """온라인 모드에서 마이그레이션 실행"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

## 5. CI/CD 파이프라인 구축

### 5.1 GitHub Actions 워크플로우

#### 5.1.1 프론트엔드 CI/CD
```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI/CD

on:
  push:
    branches: [ main, develop ]
    paths: [ 'frontend/**' ]
  pull_request:
    branches: [ main ]
    paths: [ 'frontend/**' ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Run linting
      working-directory: ./frontend
      run: |
        npm run lint
        npm run lint:style
    
    - name: Run type checking
      working-directory: ./frontend
      run: npm run type-check
    
    - name: Run unit tests
      working-directory: ./frontend
      run: npm run test:unit
    
    - name: Run integration tests
      working-directory: ./frontend
      run: npm run test:integration
    
    - name: Build application
      working-directory: ./frontend
      run: npm run build
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./frontend/coverage/lcov.info
        flags: frontend
        name: frontend-coverage

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Build application
      working-directory: ./frontend
      run: npm run build
    
    - name: Deploy to staging
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.STAGING_HOST }}
        username: ${{ secrets.STAGING_USER }}
        key: ${{ secrets.STAGING_SSH_KEY }}
        script: |
          cd /var/www/insitechart-staging
          git pull origin develop
          npm ci
          npm run build
          pm2 restart insitechart-frontend

  deploy-production:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Build application
      working-directory: ./frontend
      run: npm run build
    
    - name: Deploy to production
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.PRODUCTION_HOST }}
        username: ${{ secrets.PRODUCTION_USER }}
        key: ${{ secrets.PRODUCTION_SSH_KEY }}
        script: |
          cd /var/www/insitechart
          git pull origin main
          npm ci
          npm run build
          pm2 restart insitechart-frontend
```

#### 5.1.2 백엔드 CI/CD
```yaml
# .github/workflows/backend-ci.yml
name: Backend CI/CD

on:
  push:
    branches: [ main, develop ]
    paths: [ 'backend/**' ]
  pull_request:
    branches: [ main ]
    paths: [ 'backend/**' ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_insitechart
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      working-directory: ./backend
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Run linting
      working-directory: ./backend
      run: |
        flake8 app tests
        black --check app tests
        isort --check-only app tests
    
    - name: Run type checking
      working-directory: ./backend
      run: mypy app
    
    - name: Run security checks
      working-directory: ./backend
      run: |
        bandit -r app
        safety check
    
    - name: Run unit tests
      working-directory: ./backend
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        pytest tests/unit -v --cov=app --cov-report=xml --cov-report=html
    
    - name: Run integration tests
      working-directory: ./backend
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
        YAHOO_API_KEY: ${{ secrets.YAHOO_API_KEY }}
        REDDIT_API_KEY: ${{ secrets.REDDIT_API_KEY }}
        TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
      run: pytest tests/integration -v
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        flags: backend
        name: backend-coverage

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      working-directory: ./backend
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Deploy to staging
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.STAGING_HOST }}
        username: ${{ secrets.STAGING_USER }}
        key: ${{ secrets.STAGING_SSH_KEY }}
        script: |
          cd /var/www/insitechart-staging
          git pull origin develop
          pip install -r requirements.txt
          alembic upgrade head
          pm2 restart insitechart-backend

  deploy-production:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      working-directory: ./backend
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Deploy to production
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.PRODUCTION_HOST }}
        username: ${{ secrets.PRODUCTION_USER }}
        key: ${{ secrets.PRODUCTION_SSH_KEY }}
        script: |
          cd /var/www/insitechart
          git pull origin main
          pip install -r requirements.txt
          alembic upgrade head
          pm2 restart insitechart-backend
```

## 6. 모니터링 및 운영

### 6.1 모니터링 시스템 구축

#### 6.1.1 Prometheus + Grafana 설정
```yaml
# monitoring/docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    networks:
      - monitoring
    depends_on:
      - prometheus

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    networks:
      - monitoring

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      - DATA_SOURCE_NAME=postgres
      - DATA_SOURCE_URI=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/insitechart?sslmode=disable
    ports:
      - "9187:9187"
    networks:
      - monitoring
    depends_on:
      - postgres

  redis-exporter:
    image: oliver006/redis_exporter:latest
    environment:
      - REDIS_ADDR=redis://redis:6379
    ports:
      - "9121:9121"
    networks:
      - monitoring
    depends_on:
      - redis

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
```

### 6.2 로깅 시스템

#### 6.2.1 ELK 스택 설정
```yaml
# logging/docker-compose.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - xpack.security.enabled=false
      - xpack.security.enrollment.enabled=false
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - logging

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    ports:
      - "5044:5044"
      - "5000:5000/tcp"
      - "5000:5000/udp"
      - "9600:9600"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
      - ./logstash/config:/usr/share/logstash/config:ro
    networks:
      - logging
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - logging
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.5.0
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/log:/var/log:ro
    networks:
      - logging
    depends_on:
      - logstash

volumes:
  elasticsearch_data:

networks:
  logging:
    driver: bridge
```

## 7. Streamlit 기반 즉시 적용 가능한 구현 세부사항

### 7.1 현재 앱 개선을 위한 구체적인 코드 예시

#### 7.1.1 향상된 검색 기능 구현
```python
# enhanced_search.py
import streamlit as st
import requests
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

@dataclass
class StockSuggestion:
    symbol: str
    company_name: str
    stock_type: str
    exchange: str
    sector: str
    industry: str
    relevance_score: float
    current_price: Optional[float] = None
    market_cap: Optional[float] = None

class EnhancedSearchEngine:
    def __init__(self):
        self.cache = {}
        self.debounce_timer = None
        self.cache_ttl = 300  # 5분
        self.max_cache_size = 1000
    
    def _calculate_relevance_score(self, stock: Dict[str, Any], query: str) -> float:
        """관련도 점수 계산"""
        query = query.lower()
        symbol = stock.get('symbol', '').lower()
        name = stock.get('shortname', '').lower()
        longname = stock.get('longname', '').lower()
        
        score = 0
        
        # 심볼 정확 일치
        if symbol == query:
            score += 100
        # 심볼 시작 일치
        elif symbol.startswith(query):
            score += 80
        # 회사명 시작 일치
        elif name.startswith(query) or longname.startswith(query):
            score += 60
        # 심볼 부분 일치
        elif query in symbol:
            score += 40
        # 회사명 부분 일치
        elif query in name or query in longname:
            score += 20
        
        return score
    
    async def get_suggestions(self, query: str, max_results: int = 10) -> List[StockSuggestion]:
        """자동완성 제안 생성"""
        if not query or len(query) < 2:
            return []
        
        # 캐시 확인
        cache_key = f"search_{query}_{max_results}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
        
        try:
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {
                "q": query,
                "quotes_count": max_results * 2,  # 더 많은 결과 가져와서 필터링
                "country": "United States"
            }
            
            response = requests.get(
                url=url,
                params=params,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                suggestions = []
                
                for quote in data.get('quotes', []):
                    # 관련도 점수 계산
                    relevance_score = self._calculate_relevance_score(quote, query)
                    
                    suggestion = StockSuggestion(
                        symbol=quote.get('symbol', ''),
                        company_name=quote.get('shortname') or quote.get('longname', ''),
                        stock_type=quote.get('quoteType', ''),
                        exchange=quote.get('exchange', ''),
                        sector=quote.get('sector', ''),
                        industry=quote.get('industry', ''),
                        relevance_score=relevance_score
                    )
                    suggestions.append(suggestion)
                
                # 관련도 순으로 정렬
                suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
                suggestions = suggestions[:max_results]
                
                # 캐시 저장
                self.cache[cache_key] = (suggestions, time.time())
                self._cleanup_cache()
                
                return suggestions
            else:
                return []
        except Exception as e:
            st.error(f"검색 오류: {str(e)}")
            return []
    
    def _cleanup_cache(self):
        """오래된 캐시 정리"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        # 캐시 크기 제한
        if len(self.cache) > self.max_cache_size:
            oldest_keys = sorted(
                self.cache.items(),
                key=lambda x: x[1][1]
            )[:len(self.cache) - self.max_cache_size]
            for key, _ in oldest_keys:
                del self.cache[key]

class FilterSystem:
    def __init__(self):
        self.active_filters = {}
    
    def add_filter(self, filter_type: str, value: Any):
        """필터 추가"""
        self.active_filters[filter_type] = value
    
    def remove_filter(self, filter_type: str):
        """필터 제거"""
        if filter_type in self.active_filters:
            del self.active_filters[filter_type]
    
    def apply_filters(self, suggestions: List[StockSuggestion]) -> List[StockSuggestion]:
        """필터 적용"""
        filtered = suggestions
        
        # 주식 유형 필터
        if 'stock_type' in self.active_filters:
            filtered = [
                s for s in filtered
                if s.stock_type == self.active_filters['stock_type']
            ]
        
        # 거래소 필터
        if 'exchange' in self.active_filters:
            filtered = [
                s for s in filtered
                if s.exchange == self.active_filters['exchange']
            ]
        
        # 섹터 필터
        if 'sector' in self.active_filters:
            filtered = [
                s for s in filtered
                if self.active_filters['sector'].lower() in s.sector.lower()
            ]
        
        return filtered
    
    def get_available_filter_values(self, suggestions: List[StockSuggestion]) -> Dict[str, List[str]]:
        """사용 가능한 필터 값 목록"""
        stock_types = list(set(s.stock_type for s in suggestions if s.stock_type))
        exchanges = list(set(s.exchange for s in suggestions if s.exchange))
        sectors = list(set(s.sector for s in suggestions if s.sector))
        
        return {
            'stock_type': sorted(stock_types),
            'exchange': sorted(exchanges),
            'sector': sorted(sectors)
        }

class SearchHistoryManager:
    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        if 'search_history' not in st.session_state:
            st.session_state.search_history = []
    
    def add_to_history(self, symbol: str, company_name: str):
        """검색 기록 추가"""
        history_item = {
            'symbol': symbol,
            'company_name': company_name,
            'search_time': datetime.now(),
            'search_count': 1
        }
        
        # 기존 기록 확인
        history = st.session_state.search_history
        for i, item in enumerate(history):
            if item['symbol'] == symbol:
                history[i]['search_time'] = datetime.now()
                history[i]['search_count'] += 1
                # 최신 순으로 정렬
                history.sort(key=lambda x: x['search_time'], reverse=True)
                return
        
        # 새 항목 추가
        history.append(history_item)
        history.sort(key=lambda x: x['search_time'], reverse=True)
        
        # 최대 개수 유지
        if len(history) > self.max_history:
            st.session_state.search_history = history[:self.max_history]
        else:
            st.session_state.search_history = history
    
    def get_history(self) -> List[Dict[str, Any]]:
        """검색 기록 가져오기"""
        return st.session_state.get('search_history', [])

# Streamlit UI 통합
def enhanced_search_ui():
    """향상된 검색 UI"""
    st.markdown("### 🔍 Enhanced Stock Search")
    
    # 검색 엔진 초기화
    if 'search_engine' not in st.session_state:
        st.session_state.search_engine = EnhancedSearchEngine()
        st.session_state.filter_system = FilterSystem()
        st.session_state.history_manager = SearchHistoryManager()
    
    search_engine = st.session_state.search_engine
    filter_system = st.session_state.filter_system
    history_manager = st.session_state.history_manager
    
    # 검색 입력
    col_search, col_clear = st.columns([4, 1])
    
    with col_search:
        search_query = st.text_input(
            "Search stocks...",
            placeholder="Enter symbol or company name...",
            key="enhanced_search_input"
        )
    
    with col_clear:
        st.write("")
        if st.button("Clear", key="clear_search"):
            st.session_state.search_suggestions = []
            st.session_state.search_query = ""
            st.rerun()
    
    # 검색 결과 표시
    if search_query and search_query != st.session_state.get('search_query', ''):
        with st.spinner("Searching..."):
            suggestions = await search_engine.get_suggestions(search_query)
            st.session_state.search_suggestions = suggestions
            st.session_state.search_query = search_query
    
    # 필터 UI
    if 'search_suggestions' in st.session_state and st.session_state.search_suggestions:
        suggestions = st.session_state.search_suggestions
        available_filters = filter_system.get_available_filter_values(suggestions)
        
        with st.expander("🔧 Filters", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                stock_type = st.selectbox(
                    "Stock Type",
                    ["All"] + available_filters['stock_type'],
                    key="filter_stock_type"
                )
                if stock_type != "All":
                    filter_system.add_filter('stock_type', stock_type)
                else:
                    filter_system.remove_filter('stock_type')
            
            with col2:
                exchange = st.selectbox(
                    "Exchange",
                    ["All"] + available_filters['exchange'],
                    key="filter_exchange"
                )
                if exchange != "All":
                    filter_system.add_filter('exchange', exchange)
                else:
                    filter_system.remove_filter('exchange')
            
            with col3:
                sector = st.selectbox(
                    "Sector",
                    ["All"] + available_filters['sector'],
                    key="filter_sector"
                )
                if sector != "All":
                    filter_system.add_filter('sector', sector)
                else:
                    filter_system.remove_filter('sector')
        
        # 필터링된 결과
        filtered_suggestions = filter_system.apply_filters(suggestions)
        
        # 검색 결과 표시
        st.markdown("#### Search Results")
        
        if filtered_suggestions:
            for suggestion in filtered_suggestions:
                col_symbol, col_name, col_info, col_action = st.columns([1, 3, 2, 1])
                
                with col_symbol:
                    st.markdown(f"**{suggestion.symbol}**")
                
                with col_name:
                    st.markdown(suggestion.company_name)
                
                with col_info:
                    st.markdown(f"{suggestion.stock_type} • {suggestion.exchange}")
                
                with col_action:
                    if st.button("Select", key=f"select_{suggestion.symbol}"):
                        # 검색 기록 추가
                        history_manager.add_to_history(suggestion.symbol, suggestion.company_name)
                        # 현재 선택된 주식 설정
                        st.session_state.current_ticker = suggestion.symbol
                        # 관심종목에 추가 (선택적)
                        if suggestion.symbol not in st.session_state.watchlist:
                            st.session_state.watchlist.append(suggestion.symbol)
                        st.rerun()
        else:
            st.info("No results match your filters.")
    
    # 검색 기록 표시
    history = history_manager.get_history()
    if history:
        st.markdown("#### Recent Searches")
        
        for item in history[:5]:  # 최근 5개만 표시
            col_hist_symbol, col_hist_name, col_hist_action = st.columns([1, 3, 1])
            
            with col_hist_symbol:
                st.markdown(f"**{item['symbol']}**")
            
            with col_hist_name:
                st.markdown(item['company_name'])
            
            with col_hist_action:
                if st.button("View", key=f"history_{item['symbol']}"):
                    st.session_state.current_ticker = item['symbol']
                    st.rerun()
```

#### 7.1.2 통합 데이터 모델 구현
```python
# unified_data.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
import yfinance as yf
import requests

@dataclass
class UnifiedStockData:
    """통합 주식 데이터 모델"""
    # 기본 정보
    symbol: str
    company_name: str
    stock_type: str
    exchange: str
    sector: str
    industry: str
    
    # 가격 정보
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    
    # 검색 관련
    relevance_score: float = 0.0
    search_count: int = 0
    
    # 센티먼트 관련
    sentiment_score: Optional[float] = None
    mention_count_24h: int = 0
    trending_status: bool = False
    trend_score: Optional[float] = None
    
    # 기술 지표
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    
    # 메타데이터
    last_updated: datetime = None
    data_sources: List[str] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.data_sources is None:
            self.data_sources = []

class UnifiedDataService:
    """통합 데이터 서비스"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5분
    
    async def get_stock_with_all_data(self, symbol: str) -> UnifiedStockData:
        """모든 데이터가 통합된 주식 정보 가져오기"""
        # 캐시 확인
        cache_key = f"unified_{symbol}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return cached_data
        
        try:
            # 병렬로 데이터 수집
            stock_info, sentiment_data = await asyncio.gather(
                self._get_stock_info(symbol),
                self._get_sentiment_data(symbol)
            )
            
            # 데이터 통합
            unified_data = self._merge_data(stock_info, sentiment_data)
            
            # 캐시 저장
            self.cache[cache_key] = (unified_data, datetime.now())
            
            return unified_data
        except Exception as e:
            st.error(f"데이터 가져오기 오류: {str(e)}")
            return None
    
    async def _get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """주식 기본 정보 가져오기"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName', ''),
                'stock_type': info.get('quoteType', ''),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'previous_close': info.get('previousClose'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'volume': info.get('volume'),
                'market_cap': info.get('marketCap'),
                'data_sources': ['yahoo_finance']
            }
        except Exception as e:
            st.error(f"주식 정보 가져오기 오류: {str(e)}")
            return {}
    
    async def _get_sentiment_data(self, symbol: str) -> Dict[str, Any]:
        """센티먼트 데이터 가져오기 (예시)"""
        # 실제 구현에서는 Reddit, Twitter API 등에서 데이터 가져오기
        try:
            # 여기서는 예시 데이터 반환
            return {
                'sentiment_score': 0.65,
                'mention_count_24h': 1247,
                'trending_status': True,
                'trend_score': 2.5,
                'data_sources': ['reddit', 'twitter']
            }
        except Exception as e:
            return {
                'sentiment_score': 0.0,
                'mention_count_24h': 0,
                'trending_status': False,
                'trend_score': 0.0,
                'data_sources': []
            }
    
    def _merge_data(self, stock_info: Dict[str, Any], sentiment_data: Dict[str, Any]) -> UnifiedStockData:
        """데이터 통합"""
        return UnifiedStockData(
            symbol=stock_info.get('symbol', ''),
            company_name=stock_info.get('company_name', ''),
            stock_type=stock_info.get('stock_type', ''),
            exchange=stock_info.get('exchange', ''),
            sector=stock_info.get('sector', ''),
            industry=stock_info.get('industry', ''),
            current_price=stock_info.get('current_price'),
            previous_close=stock_info.get('previous_close'),
            day_high=stock_info.get('day_high'),
            day_low=stock_info.get('day_low'),
            volume=stock_info.get('volume'),
            market_cap=stock_info.get('market_cap'),
            sentiment_score=sentiment_data.get('sentiment_score'),
            mention_count_24h=sentiment_data.get('mention_count_24h'),
            trending_status=sentiment_data.get('trending_status'),
            trend_score=sentiment_data.get('trend_score'),
            data_sources=list(set(
                stock_info.get('data_sources', []) +
                sentiment_data.get('data_sources', [])
            ))
        )

# Streamlit UI 통합
def unified_stock_display(symbol: str):
    """통합 주식 정보 표시"""
    if 'unified_service' not in st.session_state:
        st.session_state.unified_service = UnifiedDataService()
    
    unified_service = st.session_state.unified_service
    
    with st.spinner(f"Loading {symbol} data..."):
        unified_data = await unified_service.get_stock_with_all_data(symbol)
    
    if unified_data:
        # 기본 정보 표시
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Price", f"${unified_data.current_price:.2f}")
        
        with col2:
            if unified_data.previous_close:
                change = unified_data.current_price - unified_data.previous_close
                change_pct = (change / unified_data.previous_close) * 100
                st.metric("Change", f"${change:.2f}", f"{change_pct:.2f}%")
        
        with col3:
            st.metric("Volume", f"{unified_data.volume:,}")
        
        with col4:
            if unified_data.market_cap:
                st.metric("Market Cap", f"${unified_data.market_cap/1e9:.1f}B")
        
        # 센티먼트 정보 표시
        if unified_data.sentiment_score is not None:
            st.markdown("### Social Sentiment")
            
            sentiment_col1, sentiment_col2, sentiment_col3 = st.columns(3)
            
            with sentiment_col1:
                sentiment_color = "🟢" if unified_data.sentiment_score > 0.1 else "🔴" if unified_data.sentiment_score < -0.1 else "⚪"
                st.metric("Sentiment", f"{sentiment_color} {unified_data.sentiment_score:.2f}")
            
            with sentiment_col2:
                st.metric("Mentions (24h)", unified_data.mention_count_24h)
            
            with sentiment_col3:
                if unified_data.trending_status:
                    st.metric("Trending", "🔥 Yes", delta=f"+{unified_data.trend_score:.1f}")
                else:
                    st.metric("Trending", "❌ No")
        
        # 데이터 소스 표시
        st.markdown("### Data Sources")
        sources = ", ".join(unified_data.data_sources)
        st.info(f"Data from: {sources}")
```

#### 7.1.3 향상된 관심종목 관리
```python
# enhanced_watchlist.py
import streamlit as st
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

@dataclass
class WatchlistItem:
    """관심종목 아이템"""
    symbol: str
    company_name: str
    category: str = "Default"
    note: str = ""
    added_date: datetime = None
    order_index: int = 0
    alert_enabled: bool = False
    alert_price_above: Optional[float] = None
    alert_price_below: Optional[float] = None
    
    def __post_init__(self):
        if self.added_date is None:
            self.added_date = datetime.now()

class EnhancedWatchlistManager:
    """향상된 관심종목 관리자"""
    
    def __init__(self):
        if 'enhanced_watchlist' not in st.session_state:
            st.session_state.enhanced_watchlist = []
        if 'watchlist_categories' not in st.session_state:
            st.session_state.watchlist_categories = ["Default", "Tech", "Finance", "Healthcare"]
    
    def add_to_watchlist(self, symbol: str, company_name: str, category: str = "Default"):
        """관심종목 추가"""
        # 중복 확인
        for item in st.session_state.enhanced_watchlist:
            if item.symbol == symbol:
                st.warning(f"{symbol} is already in your watchlist.")
                return False
        
        # 새 아이템 생성
        new_item = WatchlistItem(
            symbol=symbol,
            company_name=company_name,
            category=category,
            order_index=len(st.session_state.enhanced_watchlist)
        )
        
        st.session_state.enhanced_watchlist.append(new_item)
        self._save_to_local_storage()
        return True
    
    def remove_from_watchlist(self, symbol: str):
        """관심종목 제거"""
        st.session_state.enhanced_watchlist = [
            item for item in st.session_state.enhanced_watchlist
            if item.symbol != symbol
        ]
        self._save_to_local_storage()
    
    def update_watchlist_item(self, symbol: str, **kwargs):
        """관심종목 아이템 업데이트"""
        for item in st.session_state.enhanced_watchlist:
            if item.symbol == symbol:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                break
        self._save_to_local_storage()
    
    def get_watchlist(self, category: Optional[str] = None) -> List[WatchlistItem]:
        """관심종목 목록 가져오기"""
        watchlist = st.session_state.enhanced_watchlist
        
        if category and category != "All":
            watchlist = [item for item in watchlist if item.category == category]
        
        # 정렬
        return sorted(watchlist, key=lambda x: x.order_index)
    
    def get_categories(self) -> List[str]:
        """카테고리 목록 가져오기"""
        return st.session_state.watchlist_categories
    
    def add_category(self, category: str):
        """카테고리 추가"""
        if category not in st.session_state.watchlist_categories:
            st.session_state.watchlist_categories.append(category)
    
    def reorder_watchlist(self, symbols: List[str]):
        """관심종목 순서 변경"""
        for i, symbol in enumerate(symbols):
            self.update_watchlist_item(symbol, order_index=i)
    
    def _save_to_local_storage(self):
        """로컬 스토리지에 저장"""
        # Streamlit에서는 파일 기반 저장 또는 세션 상태 활용
        watchlist_data = []
        for item in st.session_state.enhanced_watchlist:
            watchlist_data.append({
                'symbol': item.symbol,
                'company_name': item.company_name,
                'category': item.category,
                'note': item.note,
                'added_date': item.added_date.isoformat(),
                'order_index': item.order_index,
                'alert_enabled': item.alert_enabled,
                'alert_price_above': item.alert_price_above,
                'alert_price_below': item.alert_price_below
            })
        
        # 실제 구현에서는 파일이나 데이터베이스에 저장
        # 여기서는 세션 상태에만 저장
        st.session_state.watchlist_data = watchlist_data

# Streamlit UI 통합
def enhanced_watchlist_ui():
    """향상된 관심종목 UI"""
    st.markdown("### 📊 Enhanced Watchlist")
    
    if 'watchlist_manager' not in st.session_state:
        st.session_state.watchlist_manager = EnhancedWatchlistManager()
    
    manager = st.session_state.watchlist_manager
    
    # 카테고리 선택
    categories = ["All"] + manager.get_categories()
    selected_category = st.selectbox("Category", categories, key="watchlist_category")
    
    # 관심종목 목록 표시
    watchlist = manager.get_watchlist(selected_category if selected_category != "All" else None)
    
    if watchlist:
        for item in watchlist:
            with st.expander(f"{item.symbol} - {item.company_name}", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**Category:** {item.category}")
                    st.markdown(f"**Added:** {item.added_date.strftime('%Y-%m-%d')}")
                
                with col2:
                    if item.note:
                        st.markdown(f"**Note:** {item.note}")
                    
                    # 알림 설정
                    alert_enabled = st.checkbox(
                        "Enable Price Alert",
                        value=item.alert_enabled,
                        key=f"alert_{item.symbol}"
                    )
                    if alert_enabled != item.alert_enabled:
                        manager.update_watchlist_item(item.symbol, alert_enabled=alert_enabled)
                    
                    if alert_enabled:
                        col_alert1, col_alert2 = st.columns(2)
                        with col_alert1:
                            alert_above = st.number_input(
                                "Alert Above",
                                value=item.alert_price_above or 0.0,
                                key=f"alert_above_{item.symbol}"
                            )
                        with col_alert2:
                            alert_below = st.number_input(
                                "Alert Below",
                                value=item.alert_price_below or 0.0,
                                key=f"alert_below_{item.symbol}"
                            )
                        
                        manager.update_watchlist_item(
                            item.symbol,
                            alert_price_above=alert_above if alert_above > 0 else None,
                            alert_price_below=alert_below if alert_below > 0 else None
                        )
                
                with col3:
                    # 메모 수정
                    new_note = st.text_area(
                        "Note",
                        value=item.note,
                        key=f"note_{item.symbol}",
                        height=50
                    )
                    if new_note != item.note:
                        manager.update_watchlist_item(item.symbol, note=new_note)
                    
                    # 삭제 버튼
                    if st.button("Remove", key=f"remove_{item.symbol}"):
                        manager.remove_from_watchlist(item.symbol)
                        st.rerun()
    else:
        st.info("No stocks in watchlist.")
    
    # 새 주식 추가
    st.markdown("#### Add New Stock")
    col_add1, col_add2, col_add3 = st.columns(3)
    
    with col_add1:
        new_symbol = st.text_input("Symbol", key="new_watchlist_symbol").upper()
    
    with col_add2:
        new_category = st.selectbox(
            "Category",
            manager.get_categories(),
            key="new_watchlist_category"
        )
    
    with col_add3:
        st.write("")
        st.write("")
        if st.button("Add to Watchlist", key="add_to_watchlist"):
            if new_symbol:
                # 여기서는 회사명을 간단히 심볼로 설정
                # 실제로는 API에서 회사명 가져오기
                if manager.add_to_watchlist(new_symbol, new_symbol, new_category):
                    st.success(f"{new_symbol} added to watchlist!")
                    st.rerun()
            else:
                st.error("Please enter a symbol.")
```

### 7.2 현재 Streamlit 앱에 통합하는 방법

#### 7.2.1 기존 app.py에 통합
```python
# 기존 app.py 파일에 다음 코드를 추가

# 파일 상단에 임포트 추가
import asyncio
from enhanced_search import enhanced_search_ui
from unified_data import unified_stock_display
from enhanced_watchlist import enhanced_watchlist_ui

# 기존 탭 구조를 수정
tab1, tab2, tab3 = st.tabs(["📊 Chart Analysis", "📉 Compare Stocks", "🔍 Enhanced Search"])

# 기존 탭 1, 2는 그대로 유지

# 새로운 탭 3 추가
with tab3:
    # 향상된 검색 UI
    enhanced_search_ui()
    
    st.markdown("---")
    
    # 관심종목 관리
    enhanced_watchlist_ui()
    
    st.markdown("---")
    
    # 선택된 주식이 있으면 통합 정보 표시
    if 'current_ticker' in st.session_state:
        st.markdown("### Selected Stock Details")
        unified_stock_display(st.session_state.current_ticker)
```

#### 7.2.2 성능 최적화를 위한 캐싱
```python
# caching.py
import streamlit as st
import time
from functools import wraps
from typing import Any, Callable

def cached(ttl: int = 300, max_size: int = 100):
    """Streamlit 캐싱 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # 캐시 확인
            if 'custom_cache' not in st.session_state:
                st.session_state.custom_cache = {}
            
            cache = st.session_state.custom_cache
            
            if cache_key in cache:
                data, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return data
            
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 캐시 저장
            cache[cache_key] = (result, time.time())
            
            # 캐시 크기 제한
            if len(cache) > max_size:
                oldest_key = min(
                    cache.items(),
                    key=lambda x: x[1][1]
                )[0]
                del cache[oldest_key]
            
            return result
        return wrapper
    return decorator

# 사용 예시
@cached(ttl=300, max_size=50)
def get_stock_data(symbol: str):
    """주식 데이터 가져오기 (캐싱 적용)"""
    # 기존 get_stock_info 함수 로직
    pass
```

### 7.3 단계적 구현 가이드

#### 7.3.1 1단계: 기본 기능 통합
1. **향상된 검색 기능 추가**
   - `enhanced_search.py` 파일 생성
   - 기존 검색 UI를 향상된 검색으로 교체
   - 자동완성 및 필터링 기능 테스트

2. **통합 데이터 모델 적용**
   - `unified_data.py` 파일 생성
   - 기존 주식 정보 표시를 통합 모델로 변경
   - 센티먼트 데이터 기본 표시

#### 7.3.2 2단계: 고급 기능 추가
1. **관심종목 관리 개선**
   - `enhanced_watchlist.py` 파일 생성
   - 카테고리별 관리, 메모, 알림 기능 추가

2. **성능 최적화**
   - 캐싱 시스템 도입
   - 비동기 처리 적용

#### 7.3.3 3단계: 소셜 센티먼트 연동
1. **소셜 데이터 수집**
   - Reddit, Twitter API 연동
   - 실시간 센티먼트 분석

2. **차트 통합**
   - 센티먼트 데이터 차트 오버레이
   - 상관관계 분석 표시

## 8. 상세 구현 태스크 목록

### 8.1 Enhanced Stock Search 구현 태스크

#### 8.1.1 프로젝트 구조 설정 및 핵심 인터페이스
```python
# tasks/enhanced_search_tasks.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

@dataclass
class ImplementationTask:
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int
    priority: str
    dependencies: List[str]
    status: TaskStatus = TaskStatus.PENDING
    assignee: Optional[str] = None

# Enhanced Stock Search 태스크 정의
ENHANCED_SEARCH_TASKS = [
    ImplementationTask(
        id="ES-001",
        title="프로젝트 구조 설정 및 핵심 인터페이스 구현",
        description="새로운 검색 시스템을 위한 모듈 구조 생성 및 핵심 데이터 모델 정의",
        acceptance_criteria=[
            "검색 시스템을 위한 모듈 구조 생성 완료",
            "StockResult, SearchHistoryItem, WatchlistItem 데이터클래스 구현",
            "타입 힌트 및 검증 로직 포함",
            "SearchController 기본 클래스 구현 완료"
        ],
        story_points=8,
        priority="critical",
        dependencies=[]
    ),
    ImplementationTask(
        id="ES-002",
        title="AutocompleteEngine 구현",
        description="실시간 자동완성 기능의 핵심 로직 구현",
        acceptance_criteria=[
            "Yahoo Finance API를 활용한 주식 검색 함수 작성",
            "부분 문자열 매칭 및 관련도 점수 계산 알고리즘 구현",
            "300ms 디바운싱으로 불필요한 API 호출 방지",
            "비동기 처리 및 응답 시간 최적화 (500ms 이내)"
        ],
        story_points=13,
        priority="high",
        dependencies=["ES-001"]
    ),
    ImplementationTask(
        id="ES-003",
        title="SearchCache 시스템 구현",
        description="검색 결과 캐싱으로 성능 향상 및 API 호출 최소화",
        acceptance_criteria=[
            "검색 쿼리를 키로 하는 캐시 시스템 구현",
            "TTL(5분) 및 최대 크기(1000개) 제한 적용",
            "만료된 캐시 항목 자동 정리 메커니즘",
            "메모리 사용량 모니터링 및 최적화"
        ],
        story_points=8,
        priority="medium",
        dependencies=["ES-002"]
    ),
    ImplementationTask(
        id="ES-004",
        title="FilterSystem 구현",
        description="다중 조건 필터링 시스템 개발",
        acceptance_criteria=[
            "주식 유형, 섹터, 거래소별 필터링 함수 작성",
            "다중 필터 조합 처리 로직 구현",
            "검색 결과에 따른 사용가능한 필터 값 동적 생성",
            "필터 적용 시 실시간 결과 업데이트"
        ],
        story_points=13,
        priority="high",
        dependencies=["ES-001"]
    ),
    ImplementationTask(
        id="ES-005",
        title="SearchHistoryManager 구현",
        description="사용자 검색 기록 저장 및 관리 시스템",
        acceptance_criteria=[
            "검색한 주식 정보를 Session State에 저장",
            "중복 제거 및 최신 시간 기준 정렬 로직",
            "최근 20개 검색 기록 유지 및 표시",
            "검색 기록에서 주식 선택 시 즉시 로드 기능"
        ],
        story_points=8,
        priority="medium",
        dependencies=["ES-001"]
    ),
    ImplementationTask(
        id="ES-006",
        title="Enhanced WatchlistManager 구현",
        description="기존 관심종목 기능을 확장하여 카테고리, 메모, 정렬 기능 추가",
        acceptance_criteria=[
            "관심종목을 카테고리별로 그룹화하는 기능 구현",
            "카테고리 생성, 수정, 삭제 기능 개발",
            "각 관심종목에 개인 메모 추가 기능",
            "버튼 기반 순서 변경 기능 (Streamlit 제약 고려)",
            "Session State를 활용한 관심종목 데이터 저장",
            "중복 추가 방지 및 자동 저장 기능"
        ],
        story_points=21,
        priority="high",
        dependencies=["ES-001"]
    ),
    ImplementationTask(
        id="ES-007",
        title="에러 처리 및 복구 시스템 구현",
        description="API 오류, 네트워크 문제 등에 대한 견고한 에러 처리",
        acceptance_criteria=[
            "Yahoo Finance API 호출 실패 시 재시도 메커니즘 (최대 3회)",
            "타임아웃 및 연결 오류에 대한 적절한 에러 메시지",
            "검색어 길이 제한 (50자) 및 특수문자 필터링",
            "빈 검색어 처리 및 검색 히스토리 표시"
        ],
        story_points=8,
        priority="medium",
        dependencies=["ES-002"]
    ),
    ImplementationTask(
        id="ES-008",
        title="향상된 검색 UI 구현",
        description="자동완성이 포함된 검색 인터페이스 개발",
        acceptance_criteria=[
            "실시간 자동완성 제안을 표시하는 검색 인터페이스",
            "키보드 네비게이션 지원 및 선택 기능",
            "주식 정보를 카드 형태로 표시하는 UI 컴포넌트",
            "관심종목 추가 버튼 및 차트 보기 버튼 포함",
            "다중 필터 선택을 위한 사용자 인터페이스",
            "검색 히스토리 드롭다운 및 선택 기능"
        ],
        story_points=21,
        priority="high",
        dependencies=["ES-002", "ES-004", "ES-005"]
    ),
    ImplementationTask(
        id="ES-009",
        title="향상된 관심종목 패널 UI 구현",
        description="카테고리별 그룹화된 관심종목 표시",
        acceptance_criteria=[
            "접을 수 있는 카테고리 섹션으로 관심종목 그룹화",
            "카테고리 추가/편집/삭제 인터페이스",
            "각 관심종목의 메모 편집 인터페이스",
            "순서 변경을 위한 위/아래 이동 버튼"
        ],
        story_points=13,
        priority="medium",
        dependencies=["ES-006"]
    ),
    ImplementationTask(
        id="ES-010",
        title="기존 애플리케이션과의 통합",
        description="새로운 검색 시스템을 기존 app.py에 통합",
        acceptance_criteria=[
            "기존의 search_stocks 함수를 새로운 SearchController로 교체",
            "기존 관심종목 시스템을 Enhanced WatchlistManager로 마이그레이션",
            "기존 사이드바 검색 섹션을 새로운 UI로 교체",
            "검색 결과 표시 방식을 카드 형태로 변경",
            "전체 검색 플로우 end-to-end 테스트",
            "기존 기능과의 호환성 검증"
        ],
        story_points=13,
        priority="high",
        dependencies=["ES-008", "ES-009"]
    ),
    ImplementationTask(
        id="ES-011",
        title="성능 최적화 및 마무리",
        description="전체 시스템의 성능 튜닝 및 최적화",
        acceptance_criteria=[
            "검색 응답 시간 측정 및 500ms 이내 달성 확인",
            "메모리 사용량 모니터링 및 최적화",
            "코드 리팩토링 및 주석 추가",
            "새로운 기능에 대한 사용자 가이드 작성"
        ],
        story_points=8,
        priority="medium",
        dependencies=["ES-010"]
    )
]
```

### 8.2 Social Sentiment Tracker 구현 태스크

#### 8.2.1 소셜 센티먼트 추적 시스템
```python
# tasks/social_sentiment_tasks.py
SOCIAL_SENTIMENT_TASKS = [
    ImplementationTask(
        id="SS-001",
        title="프로젝트 구조 설정 및 핵심 데이터 모델 구현",
        description="소셜 센티먼트 추적을 위한 모듈 구조 생성 및 핵심 데이터 모델 정의",
        acceptance_criteria=[
            "소셜 센티먼트 추적을 위한 모듈 구조 생성",
            "StockMention, TrendingStock, SentimentData 데이터클래스 구현",
            "타입 힌트 및 검증 로직 포함",
            "SentimentController 기본 클래스 구현",
            "PRAW (Reddit API), tweepy (Twitter API), VADER sentiment 등 필요 패키지 추가",
            "API 키 및 설정 관리 시스템 구현"
        ],
        story_points=8,
        priority="critical",
        dependencies=[]
    ),
    ImplementationTask(
        id="SS-002",
        title="Reddit 데이터 수집 시스템 구현",
        description="Reddit API를 활용한 주식 언급 데이터 수집",
        acceptance_criteria=[
            "PRAW를 활용한 Reddit 데이터 수집 클래스 작성",
            "주요 서브레딧 (wallstreetbets, investing, stocks 등) 연동",
            "텍스트에서 주식 심볼 ($AAPL, TSLA 등) 추출하는 정규식 및 로직",
            "유효한 주식 심볼 검증 시스템",
            "실시간 게시물 및 댓글에서 주식 언급 추출",
            "메타데이터 (업보트, 작성자, 시간 등) 함께 수집"
        ],
        story_points=13,
        priority="high",
        dependencies=["SS-001"]
    ),
    ImplementationTask(
        id="SS-003",
        title="언급 카운팅 및 랭킹 시스템 구현",
        description="시간대별 주식 언급 횟수 집계 및 랭킹 생성",
        acceptance_criteria=[
            "1시간, 24시간, 7일 단위 언급 횟수 집계 로직",
            "시간 윈도우별 데이터 관리 시스템",
            "상위 20개 언급 주식 랭킹 생성 및 업데이트",
            "언급 횟수 변화율 계산 로직",
            "5분 간격 자동 업데이트를 위한 캐싱 메커니즘",
            "TTL 기반 캐시 관리 및 메모리 최적화"
        ],
        story_points=13,
        priority="high",
        dependencies=["SS-002"]
    ),
    ImplementationTask(
        id="SS-004",
        title="트렌딩 감지 알고리즘 구현",
        description="언급량 급증 주식을 감지하는 트렌딩 알고리즘",
        acceptance_criteria=[
            "지난 7일 평균 언급량을 기준으로 한 베이스라인 계산",
            "시간대별 가중치 적용 및 노이즈 필터링",
            "200% 이상 증가 감지 및 지속성 확인 (최소 30분)",
            "트렌딩 점수 계산 및 우선순위 정렬",
            "트렌딩 주식 별도 섹션 표시 및 시각적 알림",
            "언급량 변화 그래프 생성 및 표시"
        ],
        story_points=21,
        priority="high",
        dependencies=["SS-003"]
    ),
    ImplementationTask(
        id="SS-005",
        title="커뮤니티 필터링 시스템 구현",
        description="투자 성향별 커뮤니티 분류 및 필터링 기능",
        acceptance_criteria=[
            "단타, 가치투자, 성장투자 카테고리별 커뮤니티 매핑",
            "커뮤니티 프로필 및 특성 정의 시스템",
            "사용자가 투자 성향을 선택할 수 있는 UI 컴포넌트",
            "다중 선택 지원 및 실시간 필터 적용",
            "각 커뮤니티별 언급 비중 계산 및 시각화",
            "커뮤니티 특성에 따른 데이터 가중치 적용"
        ],
        story_points=13,
        priority="medium",
        dependencies=["SS-002"]
    ),
    ImplementationTask(
        id="SS-006",
        title="감정 분석 시스템 구현",
        description="VADER 기반 텍스트 감정 분석 엔진",
        acceptance_criteria=[
            "VADER sentiment analyzer를 활용한 기본 감정 분석",
            "소셜 미디어 텍스트에 특화된 전처리 로직",
            "'moon', 'diamond hands', 'paper hands' 등 주식 커뮤니티 용어 사전",
            "주식 관련 감정 표현의 가중치 조정 시스템",
            "-100 ~ +100 범위로 정규화된 감정 점수 계산",
            "시간별 감정 변화 추이 추적 및 색상 시각화"
        ],
        story_points=21,
        priority="high",
        dependencies=["SS-002"]
    ),
    ImplementationTask(
        id="SS-007",
        title="Twitter 데이터 수집 시스템 구현 (선택적)",
        description="Twitter API를 활용한 추가 데이터 소스 확보",
        acceptance_criteria=[
            "tweepy를 활용한 Twitter 데이터 수집 클래스",
            "$TICKER 해시태그 및 키워드 기반 트윗 수집",
            "Reddit 데이터와 Twitter 데이터의 통합 처리",
            "플랫폼별 가중치 및 신뢰도 조정"
        ],
        story_points=13,
        priority="low",
        dependencies=["SS-001"]
    ),
    ImplementationTask(
        id="SS-008",
        title="소셜 센티먼트 UI 구현",
        description="트렌딩 주식, 언급 랭킹, 필터 등을 포함한 대시보드",
        acceptance_criteria=[
            "트렌딩 주식, 상위 언급 주식, 필터 옵션을 포함한 메인 대시보드",
            "실시간 업데이트 및 인터랙티브 요소 구현",
            "개별 주식의 상세 센티먼트 정보 표시 페이지",
            "커뮤니티별 분석 및 감정 점수 시각화",
            "커뮤니티 필터링 및 시간대 선택 인터페이스",
            "사용자 맞춤 설정 및 알림 옵션"
        ],
        story_points=21,
        priority="high",
        dependencies=["SS-004", "SS-005", "SS-006"]
    ),
    ImplementationTask(
        id="SS-009",
        title="차트 통합 시스템 구현",
        description="기존 주식 차트에 소셜 센티먼트 데이터 오버레이",
        acceptance_criteria=[
            "기존 Plotly 차트에 언급량 데이터를 바 그래프로 오버레이",
            "감정 점수를 별도 서브플롯으로 표시하는 시스템",
            "차트 특정 시점 클릭 시 해당 시점의 주요 언급 내용 표시",
            "언급량 급증 시점에 마커 및 툴팁 표시",
            "소셜 데이터와 주가 데이터의 상관관계 계산",
            "상관계수 및 지연 상관관계 지표 표시"
        ],
        story_points=21,
        priority="high",
        dependencies=["SS-006", "SS-008"]
    ),
    ImplementationTask(
        id="SS-010",
        title="에러 처리 및 성능 최적화",
        description="API 제한, 네트워크 오류 등에 대한 견고한 에러 처리",
        acceptance_criteria=[
            "Reddit/Twitter API 제한 및 오류에 대한 재시도 메커니즘",
            "Fallback 데이터 소스 및 Graceful degradation 구현",
            "스팸 필터링, 봇 계정 제거, 무관한 언급 필터링",
            "데이터 정제 및 검증 파이프라인 구현",
            "대량 데이터 처리를 위한 배치 처리 및 비동기 작업",
            "메모리 사용량 최적화 및 오래된 데이터 자동 정리"
        ],
        story_points=13,
        priority="medium",
        dependencies=["SS-002", "SS-007"]
    ),
    ImplementationTask(
        id="SS-011",
        title="기존 애플리케이션과의 통합",
        description="새로운 소셜 센티먼트 기능을 기존 app.py에 통합",
        acceptance_criteria=[
            "기존 'Chart Analysis', 'Compare Stocks' 탭에 'Social Sentiment' 탭 추가",
            "탭 간 데이터 공유 및 상태 관리 시스템",
            "기존 관심종목에서 소셜 센티먼트 데이터 빠른 조회",
            "센티먼트 기반 관심종목 추천 시스템",
            "기존 주식 검색에 소셜 트렌딩 정보 추가 표시",
            "센티먼트 점수 기반 검색 결과 정렬 옵션"
        ],
        story_points=13,
        priority="high",
        dependencies=["SS-008", "SS-009"]
    ),
    ImplementationTask(
        id="SS-012",
        title="통합 테스트 및 검증",
        description="전체 소셜 센티먼트 시스템의 end-to-end 테스트",
        acceptance_criteria=[
            "데이터 수집부터 UI 표시까지 전체 플로우 테스트",
            "다양한 시나리오에서의 시스템 동작 검증",
            "대량 데이터 처리 성능 측정 및 최적화",
            "동시 사용자 및 실시간 업데이트 성능 테스트",
            "새로운 소셜 센티먼트 기능에 대한 사용자 가이드",
            "Reddit/Twitter API 설정 방법 및 키 발급 가이드",
            "새로운 데이터 소스 추가 방법 문서화"
        ],
        story_points=13,
        priority="medium",
        dependencies=["SS-011"]
    )
]
```

### 8.3 통합 개선 구현 태스크

#### 8.3.1 시스템 통합 및 개선
```python
# tasks/integration_improvements_tasks.py
INTEGRATION_IMPROVEMENTS_TASKS = [
    ImplementationTask(
        id="II-001",
        title="데이터 모델 통합",
        description="Enhanced Search와 Social Sentiment의 데이터 모델 통합",
        acceptance_criteria=[
            "UnifiedStockData 모델 정의",
            "기존 StockResult와 StockMention 데이터 통합",
            "검색 관련 필드와 센티먼트 관련 필드 통합",
            "데이터 변환 레이어 구현",
            "통합 캐싱 시스템 구현"
        ],
        story_points=13,
        priority="critical",
        dependencies=[]
    ),
    ImplementationTask(
        id="II-002",
        title="통합 검색 결과 구현",
        description="검색 시 센티먼트 점수도 함께 표시",
        acceptance_criteria=[
            "검색 결과에 센티먼트 점수 표시",
            "센티먼트 기반 정렬 옵션 추가",
            "센티먼트 필터링 (긍정/부정) 기능",
            "트렌딩 주식을 검색 제안에 우선 표시",
            "관심종목에 실시간 센티먼트 상태 표시"
        ],
        story_points=8,
        priority="high",
        dependencies=["II-001"]
    ),
    ImplementationTask(
        id="II-003",
        title="통합 캐싱 시스템 구현",
        description="검색과 센티먼트 데이터의 통합 캐싱",
        acceptance_criteria=[
            "UnifiedCache 클래스 구현",
            "주식 데이터, 센티먼트 데이터, 검색 결과 통합 캐시",
            "관련 캐시 무효화 메커니즘",
            "캐시 효율성 최적화",
            "메모리 사용량 관리"
        ],
        story_points=8,
        priority="medium",
        dependencies=["II-001"]
    ),
    ImplementationTask(
        id="II-004",
        title="UI/UX 통합 개선",
        description="검색 UI와 센티먼트 UI의 통합",
        acceptance_criteria=[
            "통합 검색 인터페이스 디자인",
            "검색 결과에 센티먼트 정보 표시",
            "실시간 업데이트를 위한 UI 개선",
            "일관된 디자인 패턴 적용",
            "사용자 피드백 반영"
        ],
        story_points=13,
        priority="high",
        dependencies=["II-002"]
    ),
    ImplementationTask(
        id="II-005",
        title="성능 최적화 통합",
        description="API 호출 최적화 및 병렬 처리",
        acceptance_criteria=[
            "UnifiedDataService 구현",
            "병렬 데이터 수집 로직",
            "API 호출 최소화 전략",
            "응답 시간 개선",
            "자원 사용량 최적화"
        ],
        story_points=8,
        priority="medium",
        dependencies=["II-001", "II-003"]
    ),
    ImplementationTask(
        id="II-006",
        title="에러 처리 통합",
        description="통합된 에러 처리 시스템 구현",
        acceptance_criteria=[
            "UnifiedErrorHandler 클래스 구현",
            "일관된 에러 메시지 시스템",
            "Fallback 데이터 제공 메커니즘",
            "사용자 친화적 에러 표시",
            "에러 복구 자동화"
        ],
        story_points=8,
        priority="medium",
        dependencies=["II-001"]
    )
]
```

### 8.4 태스크 관리 및 추적 시스템

#### 8.4.1 태스크 관리자 구현
```python
# tasks/task_manager.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, ImplementationTask] = {}
        self.task_dependencies: Dict[str, List[str]] = {}
        self.completed_tasks: List[str] = []
        self.task_history: List[Dict] = []
    
    def add_task(self, task: ImplementationTask):
        """태스크 추가"""
        self.tasks[task.id] = task
        self.task_dependencies[task.id] = task.dependencies
    
    def get_available_tasks(self) -> List[ImplementationTask]:
        """의존성이 충족된 태스크 목록 반환"""
        available_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                # 모든 의존성이 완료되었는지 확인
                dependencies_met = all(
                    dep_id in self.completed_tasks
                    for dep_id in task.dependencies
                )
                if dependencies_met:
                    available_tasks.append(task)
        
        # 우선순위별 정렬
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        available_tasks.sort(key=lambda t: priority_order.get(t.priority, 4))
        
        return available_tasks
    
    def start_task(self, task_id: str, assignee: str):
        """태스크 시작"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.IN_PROGRESS
            task.assignee = assignee
            
            # 기록 저장
            self.task_history.append({
                "task_id": task_id,
                "action": "started",
                "timestamp": datetime.now(),
                "assignee": assignee
            })
    
    def complete_task(self, task_id: str):
        """태스크 완료"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            self.completed_tasks.append(task_id)
            
            # 기록 저장
            self.task_history.append({
                "task_id": task_id,
                "action": "completed",
                "timestamp": datetime.now(),
                "assignee": task.assignee
            })
    
    def get_task_progress(self) -> Dict[str, int]:
        """태스크 진행률 반환"""
        total_tasks = len(self.tasks)
        completed_tasks = len(self.completed_tasks)
        
        return {
            "total": total_tasks,
            "completed": completed_tasks,
            "in_progress": len([t for t in self.tasks.values()
                              if t.status == TaskStatus.IN_PROGRESS]),
            "pending": len([t for t in self.tasks.values()
                          if t.status == TaskStatus.PENDING]),
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
    
    def get_sprint_burndown(self, sprint_days: int = 14) -> Dict:
        """스프린트 번다운 차트 데이터"""
        completed_by_date = {}
        
        # 날짜별 완료 태스크 집계
        for history_item in self.task_history:
            if history_item["action"] == "completed":
                date = history_item["timestamp"].date()
                completed_by_date[date] = completed_by_date.get(date, 0) + 1
        
        # 번다운 데이터 생성
        burndown_data = []
        remaining_tasks = len(self.tasks)
        current_date = datetime.now().date()
        
        for day in range(sprint_days):
            check_date = current_date - timedelta(days=sprint_days - day - 1)
            completed_today = completed_by_date.get(check_date, 0)
            remaining_tasks -= completed_today
            
            burndown_data.append({
                "day": day + 1,
                "date": check_date,
                "remaining": remaining_tasks,
                "completed": len(self.tasks) - remaining_tasks
            })
        
        return {
            "ideal_burndown": [
                {"day": day + 1, "remaining": len(self.tasks) - (len(self.tasks) * day / sprint_days)}
                for day in range(sprint_days)
            ],
            "actual_burndown": burndown_data
        }
    
    def export_tasks(self, filepath: str):
        """태스크 내보내기"""
        export_data = {
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "acceptance_criteria": task.acceptance_criteria,
                    "story_points": task.story_points,
                    "priority": task.priority,
                    "dependencies": task.dependencies,
                    "status": task.status.value,
                    "assignee": task.assignee
                }
                for task in self.tasks.values()
            ],
            "task_history": self.task_history,
            "export_date": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
```

이 구현 계획은 InsiteChart 프로젝트의 성공적인 개발과 배포를 위한 상세한 로드맵, 팀 구성, 기술 스택, 데이터베이스 설계, CI/CD 파이프라인, 모니터링 시스템을 포함합니다. 특히 현재 Streamlit 기반 애플리케이션에 즉시 적용할 수 있는 구체적인 코드 예시들과 .kiro 스펙문서의 상세한 구현 태스크 목록을 추가하여 실용성을 높였습니다.