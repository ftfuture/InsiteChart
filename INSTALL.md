# InsiteChart 설치 가이드

## 개요

InsiteChart는 실시간 금융 데이터 분석 및 소셜 미디어 감성 분석을 제공하는 종합적인 금융 분석 플랫폼입니다. 이 문서는 InsiteChart 시스템의 전체 구조를 파악하고 설치하는 방법을 상세하게 설명합니다.

## 시스템 아키텍처

### 전체 구조
```
InsiteChart/
├── backend/                    # FastAPI 기반 백엔드 서비스
│   ├── api/                 # API 라우트 및 엔드포인트
│   │   ├── routes.py         # 메인 API 라우트
│   │   ├── websocket_routes.py # WebSocket 실시간 알림
│   │   └── security_routes.py # 보안 모니터링 API
│   ├── services/            # 비즈니스 로직 서비스
│   │   ├── unified_service.py # 통합 서비스
│   │   ├── stock_service.py # 주식 데이터 서비스
│   │   ├── sentiment_service.py # 감성 분석 서비스
│   │   ├── advanced_sentiment_service.py # 고급 BERT 기반 감성 분석
│   │   ├── realtime_notification_service.py # 실시간 알림 서비스
│   │   └── security_service.py # 자동화된 보안 대응 서비스
│   ├── cache/               # 캐싱 시스템
│   │   ├── unified_cache.py # 통합 캐시 관리자
│   │   ├── redis_cache.py # Redis 캐시 구현
│   │   └── memory_cache.py # 메모리 캐시 구현
│   ├── models/              # 데이터 모델
│   │   └── unified_models.py # 통합 데이터 모델
│   ├── config.py            # 설정 관리
│   └── main.py              # FastAPI 애플리케이션 진입점
├── frontend/                  # Streamlit 기반 프론트엔드
│   ├── api_client.py        # 백엔드 API 클라이언트
│   ├── notification_client.py # 실시간 알림 클라이언트
│   ├── utils.py             # 유틸리티 함수
│   └── requirements.txt     # 프론트엔드 의존성
├── services/                 # 마이크로서비스
│   └── stock-service/       # 주식 데이터 마이크로서비스
├── docs/                     # 문서
│   └── spec/               # 스펙 문서
├── tests/                    # 테스트
└── docker-compose.yml        # Docker 컴포즈 설정
```

### 핵심 컴포넌트

#### 1. 백엔드 서비스 (FastAPI)
- **메인 API 서버**: [`backend/main.py`](backend/main.py)
- **통합 서비스**: 주식 데이터와 감성 분석 통합
- **실시간 알림**: WebSocket 기반 실시간 알림 시스템
- **고급 분석**: BERT 기반 감성 분석
- **자동화된 보안**: 위협 탐지 및 자동 대응

#### 2. 프론트엔드 (Streamlit)
- **메인 애플리케이션**: [`app_new.py`](app_new.py)
- **API 클라이언트**: 백엔드와의 통신
- **실시간 알림**: WebSocket 클라이언트
- **사용자 인터페이스**: 반응형 대시보드

#### 3. 데이터 계층
- **캐싱 시스템**: 다계층 캐싱 (Redis, 메모리)
- **데이터 모델**: 통합 데이터 구조
- **외부 API**: Yahoo Finance, 소셜 미디어

## 설치 요구사항

### 시스템 요구사항
- **운영체제**: Linux, macOS, Windows
- **Python**: 3.9 이상
- **메모리**: 최소 4GB, 권장 8GB
- **저장공간**: 최소 10GB, 권장 50GB
- **네트워크**: 안정적인 인터넷 연결

### 소프트웨어 의존성

#### 백엔드
```bash
# Python 패키지
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
redis>=5.0.0
websockets>=12.0
transformers>=4.35.0
torch>=2.1.0
vaderSentiment>=3.3.2
pandas>=2.1.0
numpy>=1.24.0
asyncio-mqtt>=0.16.0
```

#### 프론트엔드
```bash
# Python 패키지
streamlit>=1.28.0
requests>=2.31.0
plotly>=5.17.0
pandas>=2.1.0
websockets>=12.0
```

#### 인프라
```bash
# 데이터베이스 및 캐시
Redis 6.0+
PostgreSQL 13+ (선택사항)

# 컨테이너화
Docker 20.0+
Docker Compose 2.0+
```

## 설치 방법

### 1. 소스 코드 복제
```bash
# Git 리포지토리 복제
git clone https://github.com/your-org/insitechart.git
cd insitechart

# 또는 ZIP 파일 다운로드 및 압축 해제
wget https://github.com/your-org/insitechart/archive/main.zip
unzip main.zip
cd insitechart-main
```

### 2. 가상환경 설정
```bash
# Python 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 3. 의존성 설치

#### 백엔드 의존성 설치
```bash
# 백엔드 디렉토리로 이동
cd backend

# 의존성 설치
pip install -r requirements.txt

# 또는 개별 설치
pip install fastapi uvicorn pydantic redis websockets transformers torch vaderSentiment pandas numpy
```

#### 프론트엔드 의존성 설치
```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
pip install -r requirements.txt

# 또는 개별 설치
pip install streamlit requests plotly pandas websockets
```

### 4. 환경 설정

#### 백엔드 환경변수
```bash
# .env 파일 생성 (backend/.env)
cp .env.example .env

# 환경변수 편집
nano .env
```

`.env` 파일 예시:
```env
# 데이터베이스 설정
DATABASE_URL=postgresql://user:password@localhost:5432/insitechart
REDIS_URL=redis://localhost:6379/0

# API 설정
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key-here

# 외부 API 키
YAHOO_FINANCE_API_KEY=your-yahoo-api-key
REDDIT_CLIENT_ID=your-reddit-client-id
TWITTER_BEARER_TOKEN=your-twitter-bearer-token

# 보안 설정
JWT_SECRET_KEY=your-jwt-secret-key
ENCRYPTION_KEY=your-encryption-key

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=logs/insitechart.log
```

#### 프론트엔드 환경변수
```bash
# Streamlit 설정 파일 생성 (.streamlit/secrets.toml)
mkdir -p .streamlit
nano .streamlit/secrets.toml
```

`.streamlit/secrets.toml` 파일 예시:
```toml
[api]
base_url = "http://localhost:8000/api/v1"

[security]
jwt_secret = "your-jwt-secret-key"

[cache]
ttl = 300
```

### 5. 데이터베이스 설정

#### Redis 설치
```bash
# Docker를 사용한 Redis 설치
docker run -d --name redis -p 6379:6379 redis:6-alpine

# 또는 시스템 패키지로 설치
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server

# macOS
brew install redis

# 시작
sudo systemctl start redis-server
# 또는
brew services start redis
```

#### PostgreSQL 설치 (선택사항)
```bash
# Docker를 사용한 PostgreSQL 설치
docker run -d --name postgres \
  -e POSTGRES_DB=insitechart \
  -e POSTGRES_USER=insitechart \
  -e POSTGRES_PASSWORD=your-password \
  -p 5432:5432 postgres:13

# 또는 시스템 패키지로 설치
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql

# 데이터베이스 생성
sudo -u postgres createdb insitechart
sudo -u postgres createuser insitechart
```

### 6. Docker를 사용한 설치 (권장)

#### Docker Compose 사용
```bash
# Docker Compose로 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

`docker-compose.yml` 파일:
```yaml
version: '3.8'

services:
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: insitechart
      POSTGRES_USER: insitechart
      POSTGRES_PASSWORD: your-password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://insitechart:your-password@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres
    volumes:
      - ./backend:/app
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://localhost:8000/api/v1
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

## 실행 방법

### 1. 개발 환경 실행

#### 백엔드 서버 실행
```bash
# 백엔드 디렉토리에서
cd backend

# 개발 모드로 실행
python main.py

# 또는 uvicorn 사용
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 프론트엔드 실행
```bash
# 새 터미널에서 프론트엔드 실행
cd frontend

# Streamlit 애플리케이션 실행
streamlit run app_new.py

# 또는 개선된 버전 실행
streamlit run app_new.py --server.port 8501
```

### 2. 프로덕션 환경 실행

#### Docker Compose 사용
```bash
# 프로덕션 환경으로 실행
docker-compose -f docker-compose.prod.yml up -d

# 상태 확인
docker-compose ps
```

#### 수동 프로덕션 실행
```bash
# 백엔드 실행 (백그라운드)
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > backend.log 2>&1 &

# 프론트엔드 실행 (백그라운드)
nohup streamlit run app_new.py --server.port 8501 > frontend.log 2>&1 &
```

## 설정 최적화

### 1. 성능 최적화

#### 캐시 설정
```python
# backend/config.py
CACHE_CONFIG = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,
        "ssl": False,
        "max_connections": 20,
        "retry_on_timeout": True,
        "socket_timeout": 5,
        "socket_connect_timeout": 5
    },
    "memory": {
        "max_size": 1000,  # 최대 캐시 항목 수
        "ttl": 300        # 기본 TTL (초)
    }
}
```

#### API 레이트리밋
```python
# backend/config.py
RATE_LIMIT_CONFIG = {
    "default": "100/minute",  # 기본 제한
    "authenticated": "1000/minute",  # 인증된 사용자
    "admin": "5000/minute",  # 관리자
    "endpoints": {
        "/api/v1/stock": "50/minute",
        "/api/v1/search": "20/minute",
        "/api/v1/sentiment": "30/minute"
    }
}
```

### 2. 보안 설정

#### JWT 설정
```python
# backend/config.py
JWT_CONFIG = {
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "secret_key": "your-very-secure-secret-key"
}
```

#### CORS 설정
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 프로덕션에서는 구체적 도메인 지정
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)
```

## 모니터링 및 로깅

### 1. 로그 설정
```python
# backend/config.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "logs/insitechart.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {  # 루트 로거
            "level": "INFO",
            "handlers": ["console", "file"]
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}
```

### 2. 헬스체크 설정
```python
# backend/api/routes.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "external_apis": await check_external_apis_health()
        }
    }
```

## 문제 해결

### 1. 일반적인 문제

#### 포트 충돌
```bash
# 포트 사용 확인
netstat -tulpn | grep :8000
netstat -tulpn | grep :8501

# 다른 포트 사용
uvicorn main:app --host 0.0.0.0 --port 8001
streamlit run app_new.py --server.port 8502
```

#### 의존성 문제
```bash
# 의존성 재설치
pip install --upgrade pip
pip install --force-reinstall -r requirements.txt

# 가상환경 재생성
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 권한 문제
```bash
# 파일 권한 확인
ls -la

# 권한 수정
chmod +x scripts/*.sh
chmod 644 config/*.json
```

### 2. 성능 문제

#### 메모리 부족
```bash
# 메모리 사용량 확인
free -h
htop

# 스왑 메모리 사용 확인
swapon --show

# Python 메모리 제한 증가
export PYTHONMALLOC=malloc_arena
```

#### 캐시 문제
```bash
# Redis 상태 확인
redis-cli ping
redis-cli info memory

# 캐시 클리어
redis-cli flushall
```

### 3. 네트워크 문제

#### 방화벽 설정
```bash
# Ubuntu/Debian
sudo ufw allow 8000
sudo ufw allow 8501
sudo ufw reload

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

#### 프록시 설정
```bash
# 환경변수 설정
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Python requests 설정
import os
proxies = {
    "http": os.environ.get("HTTP_PROXY"),
    "https": os.environ.get("HTTPS_PROXY")
}
```

## 업데이트 및 유지보수

### 1. 시스템 업데이트
```bash
# 최신 코드 가져오기
git pull origin main

# 의존성 업데이트
pip install -r requirements.txt --upgrade

# 데이터베이스 마이그레이션
alembic upgrade head

# 서비스 재시작
docker-compose restart
```

### 2. 백업 전략
```bash
# 데이터베이스 백업
pg_dump insitechart > backup_$(date +%Y%m%d_%H%M%S).sql

# Redis 백업
redis-cli --rdb backup_$(date +%Y%m%d_%H%M%S).rdb

# 설정 파일 백업
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp -r config/ config.backup.$(date +%Y%m%d_%H%M%S)
```

### 3. 모니터링 설정
```bash
# 시스템 모니터링 스크립트
#!/bin/bash
# monitor.sh

# 서비스 상태 확인
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend service is down" | mail -s "Service Alert" admin@company.com
fi

if ! curl -f http://localhost:8501 > /dev/null 2>&1; then
    echo "Frontend service is down" | mail -s "Service Alert" admin@company.com
fi

# 디스크 공간 확인
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Disk usage is ${DISK_USAGE}%" | mail -s "Disk Alert" admin@company.com
fi
```

## 추가 리소스

### 1. 문서
- [사용자 매뉴얼](USER_MANUAL.md)
- [API 문서](docs/api/)
- [스펙 문서](docs/spec/)

### 2. 지원
- GitHub Issues: https://github.com/your-org/insitechart/issues
- 이메일: support@insitechart.com
- 위키: https://github.com/your-org/insitechart/wiki

### 3. 커뮤니티
- Discord: https://discord.gg/insitechart
- 포럼: https://forum.insitechart.com
- 블로그: https://blog.insitechart.com

## 결론

이 설치 가이드는 InsiteChart 시스템의 전체 구조를 파악하고 성공적으로 설치하는 데 필요한 모든 정보를 제공합니다. Docker를 사용한 설치를 권장하며, 개발 환경과 프로덕션 환경 모두에서 안정적인 운영이 가능하도록 구성되었습니다.

설치 과정에서 문제가 발생할 경우 문제 해결 섹션을 참고하시거나 지원 채널을 통해 도움을 요청하십시오.