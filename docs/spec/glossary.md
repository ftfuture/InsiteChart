# InsiteChart 프로젝트 용어집

## 개요

본 용어집은 InsiteChart 프로젝트에서 사용되는 주요 용어들을 정의하고 설명하여 프로젝트의 이해도를 높이고 커뮤니케이션의 일관성을 확보하는 것을 목적으로 합니다.

## A

### API (Application Programming Interface)
- **정의**: 소프트웨어 애플리케이션이 서로 통신할 수 있게 하는 인터페이스
- **문맥**: InsiteChart에서는 RESTful API와 WebSocket API를 제공하여 프론트엔드와 백엔드 간의 데이터 교환을 담당
- **관련 문서**: [API 통합 스펙](docs/spec/03-api-integration.md), [통합 API 스펙](docs/spec/api-spec-unified.md)

### API 게이트웨이 (API Gateway)
- **정의**: 클라이언트 요청을 적절한 마이크로서비스로 라우팅하고 인증, 로깅, 레이트 리밋 등의 공통 기능을 제공하는 서비스
- **문맥**: InsiteChart에서 모든 API 요청을 중앙에서 관리하고 보안 정책을 적용
- **관련 문서**: [API 게이트웨이 라우팅](docs/spec/12-api-gateway-routing.md)

## B

### BERT (Bidirectional Encoder Representations from Transformers)
- **정의**: Google이 개발한 사전 훈련된 언어 모델로, 문맥을 양방향으로 이해하여 자연어 처리 작업에 높은 성능을 보임
- **문맥**: InsiteChart의 고급 감성 분석에 사용되어 금융 텍스트의 미묘한 감정과 뉘앙스를 파악
- **관련 문서**: [최종 스펙 검토](docs/spec/22-final-spec-review.md)

### 백엔드 (Backend)
- **정의**: 서버 측에서 동작하는 소프트웨어 컴포넌트로, 데이터 처리, 비즈니스 로직, 데이터베이스 관리 등을 담당
- **문맥**: InsiteChart의 FastAPI 기반 서버 애플리케이션과 관련 서비스들을 의미
- **관련 문서**: [시스템 아키텍처](docs/spec/02-system-architecture.md)

## C

### 캐싱 (Caching)
- **정의**: 자주 사용되는 데이터를 빠른 저장소에 임시로 저장하여 시스템 성능을 향상시키는 기술
- **문맥**: InsiteChart에서는 Redis를 사용하여 다계층 캐싱 시스템을 구현
- **관련 문서**: [통합 캐싱 시스템](docs/spec/13-unified-caching-system.md)

### CORS (Cross-Origin Resource Sharing)
- **정의**: 웹 페이지가 다른 도메인의 리소스를 요청할 수 있게 하는 보안 메커니즘
- **문맥**: InsiteChart의 프론트엔드와 백엔드가 다른 도메인에서 동작할 때 필요한 보안 설정
- **관련 문서**: [통합 API 스펙](docs/spec/api-spec-unified.md)

## D

### 데이터 모델 (Data Model)
- **정의**: 데이터의 구조, 관계, 제약 조건 등을 정의한 추상적인 표현
- **문맥**: InsiteChart의 모든 데이터 구조를 정의한 스펙으로, Pydantic 모델로 구현
- **관련 문서**: [통합 데이터 모델](docs/spec/data-model-unified.md), [통합 데이터 모델 스펙](docs/spec/11-integrated-data-model.md)

### 데이터 소스 (Data Source)
- **정의**: 분석에 사용되는 원본 데이터를 제공하는 시스템이나 서비스
- **문맥**: InsiteChart에서는 Reddit, Twitter, Discord, 뉴스 등의 소셜 미디어 데이터를 수집
- **관련 문서**: [API 통합 스펙](docs/spec/03-api-integration.md)

### Discord
- **정의**: 게이머와 커뮤니티를 위한 음성, 비디오, 텍스트 채팅 플랫폼
- **문맥**: InsiteChart에서 감성 분석을 위한 데이터 소스 중 하나로 사용
- **관련 문서**: [통합 데이터 모델](docs/spec/data-model-unified.md)

### Docker
- **정의**: 컨테이너화 기술을 제공하는 플랫폼으로, 애플리케이션을 격리된 환경에서 실행할 수 있게 함
- **문맥**: InsiteChart의 배포와 개발 환경을 일관성 있게 관리하기 위해 사용
- **관련 문서**: [배포 및 운영](docs/spec/07-deployment-operations.md)

## E

### 엔티티 (Entity)
- **정의**: 자연어 처리에서 명사, 조직, 장소 등 의미 있는 단위를 인식하고 분류하는 작업
- **문맥**: InsiteChart의 감성 분석에서 텍스트에서 중요한 키워드와 개체를 추출
- **관련 문서**: [통합 데이터 모델](docs/spec/data-model-unified.md)

## F

### FastAPI
- **정의**: Python 기반의 현대적이고 빠른 웹 프레임워크로, API 개발에 최적화
- **문맥**: InsiteChart의 백엔드 API 서버 구현에 사용되는 핵심 프레임워크
- **관련 문서**: [시스템 아키텍처](docs/spec/02-system-architecture.md)

### 프론트엔드 (Frontend)
- **정의**: 사용자가 직접 상호작용하는 사용자 인터페이스 부분
- **문맥**: InsiteChart에서는 Streamlit 기반의 웹 인터페이스를 의미
- **관련 문서**: [UX 및 접근성](docs/spec/08-ux-accessibility.md)

## G

### GDPR (General Data Protection Regulation)
- **정의**: 유럽 연합의 개인정보 보호 규정으로, 데이터 처리와 보호에 대한 엄격한 요구사항을 정의
- **문맥**: InsiteChart의 개인정보 보호 정책 수립 시 준수해야 하는 규정
- **관련 문서**: [보안 및 개인정보 보호](docs/spec/05-security-privacy.md)

### GitOps
- **정의**: Git을 단일 진실 공급원(Single Source of Truth)으로 사용하여 인프라와 애플리케이션을 선언적으로 관리하는 운영 방식
- **문맥**: InsiteChart의 배포 자동화를 위해 도입된 운영 방식
- **관련 문서**: [최종 스펙 검토](docs/spec/22-final-spec-review.md)

## H

### JWT (JSON Web Token)
- **정의**: JSON 객체를 안전하게 전송하기 위한 개방형 표준으로, 인증과 정보 교환에 사용
- **문맥**: InsiteChart의 사용자 인증과 API 접근 제어에 사용
- **관련 문서**: [통합 API 스펙](docs/spec/api-spec-unified.md)

## K

### Kafka
- **정의**: 분산 스트리밍 플랫폼으로, 대용량 실시간 데이터 처리를 위해 설계
- **문맥**: InsiteChart의 고급 실시간 기능 확장을 위해 도입된 이벤트 스트리밍 아키텍처
- **관련 문서**: [최종 스펙 검토](docs/spec/22-final-spec-review.md)

## L

### L1/L2/L3 캐시
- **정의**: 다계층 캐싱 시스템에서 각 계층을 의미
  - L1: 인메모리 캐시 (가장 빠름)
  - L2: Redis 캐시 (중간 속도)
  - L3: 데이터베이스 쿼리 캐시 (가장 느림)
- **문맥**: InsiteChart의 성능 최적화를 위한 다계층 캐싱 전략
- **관련 문서**: [통합 캐싱 시스템](docs/spec/13-unified-caching-system.md)

## M

### 마이크로서비스 (Microservices)
- **정의**: 단일 애플리케이션을 작은 독립적인 서비스들의 집합으로 구성하는 아키텍처 스타일
- **문맥**: InsiteChart의 확장성과 유지보수성을 향상시키기 위해 채택된 아키텍처
- **관련 문서**: [시스템 아키텍처](docs/spec/02-system-architecture.md)

### MLflow
- **정의**: 머신러닝 라이프사이클을 관리하는 오픈소스 플랫폼
- **문맥**: InsiteChart의 감성 분석 모델 관리와 자동 재학습을 위해 도입
- **관련 문서**: [최종 스펙 검토](docs/spec/22-final-spec-review.md)

### 모니터링 (Monitoring)
- **정의**: 시스템의 상태, 성능, 가용성 등을 지속적으로 관찰하고 분석하는 활동
- **문맥**: InsiteChart의 안정적인 운영을 위해 Prometheus와 Grafana를 사용한 모니터링 시스템 구현
- **관련 문서**: [모니터링 및 알림 시스템](docs/spec/23-monitoring-alerting-system.md)

## O

### OpenAPI
- **정의**: RESTful API를 설계, 빌드, 문서화하기 위한 표준 명세
- **문맥**: InsiteChart의 API 스펙을 정의하고 문서화하는 데 사용
- **관련 문서**: [통합 API 스펙](docs/spec/api-spec-unified.md)

## P

### PostgreSQL
- **정의**: 오픈소스 관계형 데이터베이스 관리 시스템
- **문맥**: InsiteChart의 주요 데이터 저장소로 사용
- **관련 문서**: [시스템 아키텍처](docs/spec/02-system-architecture.md)

### Pydantic
- **정의**: Python의 데이터 유효성 검사와 설정 관리를 위한 라이브러리
- **문맥**: InsiteChart의 데이터 모델 정의와 API 요청/응답 검증에 사용
- **관련 문서**: [통합 데이터 모델](docs/spec/data-model-unified.md)

## R

### 레이트 리밋 (Rate Limiting)
- **정의**: 특정 시간 동안의 요청 수를 제한하여 시스템을 보호하는 메커니즘
- **문맥**: InsiteChart의 API 서비스를 과부하로부터 보호하고 공정한 사용을 보장
- **관련 문서**: [API 레이트 리밋 전략](docs/spec/21-api-rate-limiting-strategy.md)

### Reddit
- **정의**: 소셜 뉴스 집계, 웹 콘텐츠 평가, 토론 포럼을 제공하는 플랫폼
- **문맥**: InsiteChart에서 감성 분석을 위한 주요 데이터 소스 중 하나
- **관련 문서**: [통합 데이터 모델](docs/spec/data-model-unified.md)

### Redis
- **정의**: 인메모리 데이터 구조 저장소로, 캐시, 메시지 브로커, 데이터베이스로 사용
- **문맥**: InsiteChart의 캐싱 시스템과 실시간 데이터 처리에 사용
- **관련 문서**: [통합 캐싱 시스템](docs/spec/13-unified-caching-system.md)

### RESTful API
- **정의**: HTTP 프로토콜을 기반으로 하는 아키텍처 스타일의 API
- **문맥**: InsiteChart의 주요 API 통신 방식으로 사용
- **관련 문서**: [API 통합 스펙](docs/spec/03-api-integration.md)

## S

### 감성 분석 (Sentiment Analysis)
- **정의**: 텍스트에 담긴 주관적인 감정, 의견, 태도를 분석하여 긍정, 부정, 중립으로 분류하는 자연어 처리 기술
- **문맥**: InsiteChart의 핵심 기능으로, 소셜 미디어 데이터를 분석하여 시장 동향 파악
- **관련 문서**: [감성 분석 통합 계획](docs/spec/sentiment-analysis-integration-plan.md)

### Streamlit
- **정의**: Python 기반의 오픈소스 프레임워크로, 머신러닝 애플리케이션을 빠르게 구축할 수 있게 함
- **문맥**: InsiteChart의 프론트엔드 인터페이스 구현에 사용
- **관련 문서**: [UX 및 접근성](docs/spec/08-ux-accessibility.md)

## T

### 테스트 전략 (Testing Strategy)
- **정의**: 소프트웨어의 품질을 보증하기 위한 체계적인 테스트 계획과 절차
- **문맥**: InsiteChart의 안정적인 개발과 배포를 위해 단위 테스트, 통합 테스트, E2E 테스트 등을 포함한 전략 수립
- **관련 문서**: [테스트 전략](docs/spec/06-testing-strategy.md)

### Twitter
- **정의**: 마이크로블로깅 및 소셜 네트워킹 서비스
- **문맥**: InsiteChart에서 감성 분석을 위한 데이터 소스 중 하나
- **관련 문서**: [통합 데이터 모델](docs/spec/data-model-unified.md)

## U

### UI/UX (User Interface/User Experience)
- **정의**: 
  - UI: 사용자가 시스템과 상호작용하는 인터페이스
  - UX: 사용자가 시스템을 사용하면서 느끼는 전체적인 경험
- **문맥**: InsiteChart의 사용자 인터페이스 설계와 사용자 경험 최적화
- **관련 문서**: [UX 및 접근성](docs/spec/08-ux-accessibility.md)

## V

### 버전 관리 (Version Control)
- **정의**: 소프트웨어 변경 사항을 추적하고 관리하는 시스템
- **문맥**: InsiteChart의 소스 코드 관리를 위해 Git 사용
- **관련 문서**: [배포 및 운영](docs/spec/07-deployment-operations.md)

## W

### WebSocket
- **정의**: 단일 TCP 연결을 통해 양방향 통신을 제공하는 프로토콜
- **문맥**: InsiteChart의 실시간 데이터 동기화와 알림 기능에 사용
- **관련 문서**: [실시간 데이터 동기화](docs/spec/14-realtime-data-sync.md)

## Z

### Zustand
- **정의**: React를 위한 작고 빠르며 확장 가능한 상태 관리 솔루션
- **문맥**: InsiteChart의 마이크로프론트엔드 아키텍처에서 상태 관리를 위해 도입
- **관련 문서**: [최종 스펙 검토](docs/spec/22-final-spec-review.md)

## 약어 목록

| 약어 | 전체 이름 | 한국어 설명 |
|------|-----------|-------------|
| API | Application Programming Interface | 애플리케이션 프로그래밍 인터페이스 |
| BERT | Bidirectional Encoder Representations from Transformers | 트랜스포머 기반 양방향 인코더 표현 |
| CI/CD | Continuous Integration/Continuous Deployment | 지속적 통합/지속적 배포 |
| CORS | Cross-Origin Resource Sharing | 교차 출처 리소스 공유 |
| GDPR | General Data Protection Regulation | 일반 개인정보 보호 규정 |
| JWT | JSON Web Token | JSON 웹 토큰 |
| ML | Machine Learning | 머신러닝 |
| NLP | Natural Language Processing | 자연어 처리 |
| REST | Representational State Transfer | 표현 상태 전이 |
| UI/UX | User Interface/User Experience | 사용자 인터페이스/사용자 경험 |
| YAML | YAML Ain't Markup Language | YAML 마크업 언어가 아님 |

---

**문서 버전**: 1.0  
**작성일**: 2024-01-01  
**작성자**: InsiteChart 개발팀  
**검토자**: 기술 아키텍트