# InsiteChart - 종합 금융 데이터 및 소셜 감성 분석 플랫폼

InsiteChart는 실시간 주식 데이터와 소셜 미디어 감성 분석을 통합한 차세대 금융 분석 플랫폼입니다. 사용자들은 종합적인 시장 인사이트, 실시간 데이터 동기화, 및 고급 분석 도구를 통해 더 나은 투자 결정을 내릴 수 있습니다.

## 🚀 주요 기능

### 💰 금융 데이터
- 실시간 주식 가격 및 시장 데이터
- 포괄적인 재무 정보 및 지표
- 과거 데이터 분석 및 차트
- 시장 지수 모니터링

### 📊 소셜 감성 분석
- Reddit, Twitter, Discord에서 실시간 감성 데이터 수집
- AI 기반 감성 분석 및 트렌드 식별
- 커뮤니티별 감성 분석
- 트렌딩 주식 식별

### 🔄 통합 분석
- 주식 데이터와 감성 분석의 통합
- 상관관계 분석 및 비교 도구
- 시장 인사이트 및 예측
- 개인화된 워치리스트 및 알림

### 🌐 고급 기능
- 다국어 지원 (한국어, 영어, 일본어 등 10개 언어)
- 실시간 데이터 동기화 (WebSocket)
- 고급 캐싱 시스템
- API 레이트리밋 및 보안
- 모니터링 및 알림 시스템

## 🏗️ 아키텍처

InsiteChart는 마이크로서비스 아키텍처를 기반으로 구축되었습니다:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   프론트엔드     │    │   API 게이트웨이  │    │   마이크로서비스  │
│  (Streamlit)    │◄──►│   (FastAPI)     │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   캐시 시스템    │    │   데이터베이스    │
                       │   (Redis)      │    │  (PostgreSQL)   │
                       └─────────────────┘    └─────────────────┘
```

### 핵심 컴포넌트

- **백엔드 API**: FastAPI 기반의 RESTful API
- **프론트엔드**: Streamlit 기반의 웹 인터페이스
- **데이터 소스**: Yahoo Finance, Reddit, Twitter
- **캐싱**: Redis 기반의 다계층 캐싱
- **데이터베이스**: PostgreSQL 기반의 데이터 저장
- **모니터링**: Prometheus & Grafana

## 📦 설치 및 실행

### 사전 요구사항

- Docker & Docker Compose
- Python 3.11+ (로컬 개발 시)
- Node.js 18+ (프론트엔드 개발 시)

### Docker를 사용한 설치 (권장)

1. 리포지토리 클론:
```bash
git clone https://github.com/your-org/insitechart.git
cd insitechart
```

2. 환경 변수 설정:
```bash
cp .env.example .env
# .env 파일에 필요한 API 키 및 설정 입력
```

3. 서비스 시작:
```bash
docker-compose up -d
```

4. 서비스 확인:
- 프론트엔드: http://localhost:8501
- API 문서: http://localhost:8000/docs
- 모니터링: http://localhost:3000 (Grafana)

### 로컬 개발 환경

1. 백엔드 설치:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. 프론트엔드 설치:
```bash
pip install -r requirements.txt
```

3. 데이터베이스 시작:
```bash
docker-compose up -d postgres redis
```

4. 서비스 시작:
```bash
# 백엔드
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 (다른 터미널)
streamlit run app.py --server.port 8501
```

## 🔧 설정

### 환경 변수

주요 환경 변수들은 `.env` 파일에서 설정할 수 있습니다:

```bash
# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost/insitechart

# Redis
REDIS_URL=redis://localhost:6379/0

# API 키
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# 보안
SECRET_KEY=your_secret_key_here
```

### API 키 설정

1. **Reddit API**:
   - https://www.reddit.com/prefs/apps 에서 앱 생성
   - Client ID 및 Secret 획득

2. **Twitter API**:
   - https://developer.twitter.com 에서 개발자 계정 신청
   - Bearer Token 획득

## 📚 API 문서

API 문서는 다음 URL에서 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 주요 엔드포인트

- `GET /api/v1/stock` - 주식 데이터 조회
- `POST /api/v1/search` - 주식 검색
- `GET /api/v1/trending` - 트렌딩 주식
- `POST /api/v1/sentiment` - 감성 분석
- `POST /api/v1/compare` - 주식 비교
- `GET /api/v1/market/sentiment` - 시장 감성

## 🧪 테스트

### 백엔드 테스트
```bash
cd backend
pytest tests/ -v --cov=.
```

### 통합 테스트
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📊 모니터링

InsiteChart는 종합적인 모니터링 시스템을 제공합니다:

- **Prometheus**: 메트릭 수집 (http://localhost:9090)
- **Grafana**: 시각화 대시보드 (http://localhost:3000)
- **로그**: 구조화된 로그 시스템

### 주요 메트릭

- API 응답 시간
- 캐시 히트율
- 데이터 소스 연결 상태
- 시스템 리소스 사용량

## 🔒 보안

- JWT 기반 인증
- API 레이트리밋
- HTTPS 강제
- 데이터 암호화
- CORS 설정

## 🌍 국제화

다음 언어들을 지원합니다:
- 한국어 (ko)
- English (en)
- 日本語 (ja)
- 中文 (zh)
- Español (es)
- Français (fr)
- Deutsch (de)
- Italiano (it)
- Português (pt)
- Русский (ru)

## 📈 성능

- **응답 시간**: < 100ms (캐시된 데이터)
- **처리량**: 1000+ 요청/초
- **가용성**: 99.9% 목표
- **캐시 히트율**: > 90%

## 🤝 기여

기여를 환영합니다! 다음 단계를 따라주세요:

1. 리포지토리 포크
2. 기능 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 푸시 (`git push origin feature/AmazingFeature`)
5. 풀 리퀘스트 생성

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

질문이나 문제가 있으신가요?

- 이슈 생성: https://github.com/your-org/insitechart/issues
- 이메일: support@insitechart.com
- 문서: https://docs.insitechart.com

## 🗺️ 로드맵

### v1.1 (예정)
- [ ] 모바일 앱
- [ ] 고급 차트 기능
- [ ] 머신러닝 예측 모델

### v1.2 (예정)
- [ ] 암호화폐 지원
- [ ] 포트폴리오 관리
- [ ] 소셜 트레이딩 기능

## 📄 스펙 문서

자세한 기술 스펙은 [docs/spec](docs/spec) 디렉토리를 참조하세요:

- [시스템 아키텍처](docs/spec/02-system-architecture.md)
- [API 통합](docs/spec/03-api-integration.md)
- [보안 및 개인정보보호](docs/spec/05-security-privacy.md)
- [성능 및 확장성](docs/spec/04-performance-scalability.md)
- 그리고 더 많은 문서들...

---

**InsiteChart** - 스마트한 투자를 위한 스마트한 플랫폼 🚀