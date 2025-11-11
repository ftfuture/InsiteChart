# 통합 API 스펙 문서

## 1. 개요

### 1.1. 목적
본 문서는 InsiteChart 프로젝트의 모든 API 엔드포인트를 통합하여 일관된 스펙을 제공하는 것을 목적으로 합니다.

### 1.2. 범위
- 모든 REST API 엔드포인트
- 표준 요청/응답 형식
- 에러 처리 및 상태 코드
- 인증 및 인가 방식

### 1.3. 관련 문서
- [API 통합 스펙](docs/spec/03-api-integration.md)
- [API 게이트웨이 라우팅](docs/spec/12-api-gateway-routing.md)
- [보안 및 개인정보 보호](docs/spec/05-security-privacy.md)

## 2. 표준 응답 형식

### 2.1. 성공 응답

```json
{
  "success": true,
  "data": {
    // 응답 데이터
  },
  "message": "요청이 성공적으로 처리되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 2.2. 에러 응답

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지",
    "details": {
      // 상세 에러 정보
    }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 3. API 엔드포인트 목록

### 3.1. 인증 API

#### 3.1.1. 로그인
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "refresh_token": "string",
    "expires_in": 3600,
    "user": {
      "id": "string",
      "username": "string",
      "email": "string"
    }
  },
  "message": "로그인이 성공적으로 처리되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 3.1.2. 토큰 갱신
```http
POST /api/v1/auth/refresh
Content-Type: application/json
Authorization: Bearer <refresh_token>

{
  "refresh_token": "string"
}
```

### 3.2. 데이터 소스 API

#### 3.2.1. 데이터 소스 목록 조회
```http
GET /api/v1/datasources
Authorization: Bearer <access_token>
```

**응답:**
```json
{
  "success": true,
  "data": {
    "datasources": [
      {
        "id": "string",
        "name": "string",
        "type": "reddit|twitter|discord",
        "status": "active|inactive|error",
        "last_sync": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 10,
    "page": 1,
    "per_page": 20
  },
  "message": "데이터 소스 목록이 성공적으로 조회되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 3.2.2. 데이터 소스 추가
```http
POST /api/v1/datasources
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "name": "string",
  "type": "reddit|twitter|discord",
  "config": {
    // 데이터 소스별 설정
  }
}
```

### 3.3. 분석 API

#### 3.3.1. 감성 분석 요청
```http
POST /api/v1/analysis/sentiment
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "text": "string",
  "source": "reddit|twitter|discord",
  "metadata": {
    // 추가 메타데이터
  }
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "sentiment": "positive|negative|neutral",
    "confidence": 0.95,
    "scores": {
      "positive": 0.8,
      "negative": 0.1,
      "neutral": 0.1
    },
    "keywords": ["keyword1", "keyword2"],
    "analysis_id": "string"
  },
  "message": "감성 분석이 성공적으로 완료되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 3.3.2. 분석 결과 조회
```http
GET /api/v1/analysis/{analysis_id}
Authorization: Bearer <access_token>
```

### 3.4. 대시보드 API

#### 3.4.1. 대시보드 데이터 조회
```http
GET /api/v1/dashboard/data
Authorization: Bearer <access_token>
```

**응답:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_sentiments": 1000,
      "positive_ratio": 0.6,
      "negative_ratio": 0.2,
      "neutral_ratio": 0.2
    },
    "trends": [
      {
        "date": "2024-01-01",
        "positive": 100,
        "negative": 50,
        "neutral": 30
      }
    ],
    "top_keywords": [
      {
        "keyword": "string",
        "count": 100,
        "sentiment": "positive"
      }
    ]
  },
  "message": "대시보드 데이터가 성공적으로 조회되었습니다.",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 3.5. 실시간 API

#### 3.5.1. WebSocket 연결
```javascript
// WebSocket 연결
const ws = new WebSocket('ws://localhost:8000/ws/realtime');

// 인증 메시지
ws.send(JSON.stringify({
  type: 'auth',
  token: 'access_token'
}));

// 구독 메시지
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['sentiment', 'trends']
}));
```

#### 3.5.2. 실시간 데이터 수신
```javascript
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'sentiment_update':
      // 감성 분석 업데이트 처리
      break;
    case 'trend_update':
      // 트렌드 업데이트 처리
      break;
  }
};
```

## 4. 에러 코드 정의

### 4.1. 인증 에러
| 코드 | 메시지 | 설명 |
|------|--------|------|
| AUTH_001 | 인증 토큰이 유효하지 않습니다. | 만료되거나 위조된 토큰 |
| AUTH_002 | 권한이 없습니다. | 리소스 접근 권한 부족 |
| AUTH_003 | 로그인 정보가 올바르지 않습니다. | 사용자 이름 또는 비밀번호 오류 |

### 4.2. 데이터 에러
| 코드 | 메시지 | 설명 |
|------|--------|------|
| DATA_001 | 데이터를 찾을 수 없습니다. | 요청한 데이터가 존재하지 않음 |
| DATA_002 | 데이터 형식이 올바르지 않습니다. | 요청 데이터 형식 오류 |
| DATA_003 | 데이터 처리 중 오류가 발생했습니다. | 서버 내부 데이터 처리 오류 |

### 4.3. 시스템 에러
| 코드 | 메시지 | 설명 |
|------|--------|------|
| SYS_001 | 서버에 일시적인 오류가 발생했습니다. | 일시적인 서버 오류 |
| SYS_002 | 서비스를 사용할 수 없습니다. | 서비스 점검 또는 장애 |
| SYS_003 | 요청 처리 시간이 초과되었습니다. | 타임아웃 오류 |

## 5. 인증 및 인가

### 5.1. JWT 토큰 형식
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id",
    "iat": 1640995200,
    "exp": 1640998800,
    "scope": ["read", "write"],
    "roles": ["user"]
  }
}
```

### 5.2. API 키 관리
```http
GET /api/v1/auth/apikeys
Authorization: Bearer <access_token>
```

**응답:**
```json
{
  "success": true,
  "data": {
    "api_keys": [
      {
        "id": "string",
        "name": "string",
        "key": "masked_key",
        "permissions": ["read", "write"],
        "created_at": "2024-01-01T00:00:00Z",
        "last_used": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

## 6. 레이트 리밋

### 6.1. 레이트 리밋 정책
| 엔드포인트 그룹 | 제한 | 시간 윈도우 |
|----------------|------|-------------|
| 인증 API | 5회/IP | 1분 |
| 데이터 API | 100회/사용자 | 1분 |
| 분석 API | 50회/사용자 | 1분 |
| 실시간 API | 10연결/사용자 | 동시 |

### 6.2. 레이트 리밋 응답
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "요청 한도를 초과했습니다.",
    "details": {
      "limit": 100,
      "remaining": 0,
      "reset_time": "2024-01-01T00:01:00Z"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 7. 보안 헤더

### 7.1. 필수 보안 헤더
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### 7.2. CORS 설정
```http
Access-Control-Allow-Origin: https://insitechart.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type, X-Requested-With
Access-Control-Max-Age: 86400
```

## 8. API 버전 관리

### 8.1. 버전 정책
- URL 경로 기반 버전 관리: `/api/v1/`, `/api/v2/`
- 하위 호환성 보장 기간: 6개월
- 주 버전 변경 시 사전 공지: 3개월 전

### 8.2. 버전 마이그레이션
```http
GET /api/v1/data
# v1에서 v2로 마이그레이션 안내
{
  "success": true,
  "data": {
    // v1 형식 데이터
  },
  "migration_notice": {
    "deprecated_version": "v1",
    "removal_date": "2024-06-01",
    "migration_guide": "https://docs.insitechart.com/api/v2/migration"
  }
}
```

## 9. 테스트 및 검증

### 9.1. API 테스트 도구
- Postman 컬렉션 제공
- OpenAPI 3.0 스펙 파일 제공
- 자동화된 API 테스트 스위트

### 9.2. 검증 체크리스트
- [ ] 모든 엔드포인트가 표준 응답 형식을 따르는가?
- [ ] 에러 코드가 일관하게 정의되었는가?
- [ ] 인증 및 인가가 올바르게 구현되었는가?
- [ ] 레이트 리밋이 적절히 설정되었는가?
- [ ] 보안 헤더가 올바르게 설정되었는가?

---

**문서 버전**: 1.0  
**작성일**: 2024-01-01  
**작성자**: InsiteChart 개발팀  
**검토자**: 기술 아키텍트