# 배포 및 운영 계획

## 1. 배포 전략

### 1.1 컨테이너화

#### 1.1.1 Dockerfile 최적화
```dockerfile
# Dockerfile
# 다단계 빌드를 통한 이미지 최적화

# 빌드 단계
FROM python:3.11-slim as builder

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사
COPY requirements.txt .
COPY requirements-dev.txt .

# 가상환경 생성 및 의존성 설치
RUN python -m venv /opt/venv
RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install -r requirements.txt

# 프로덕션 단계
FROM python:3.11-slim as production

# 보안을 위한 비루트 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (프로덕션용)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 가상환경 복사
COPY --from=builder /opt/venv /opt/venv

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY main.py .

# 정적 파일 복사
COPY static/ ./static/

# 권한 설정
RUN chown -R appuser:appuser /app
RUN chmod +x /app/main.py

# 비루트 사용자로 전환
USER appuser

# 환경변수 설정
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 포트 노출
EXPOSE 8000

# 시작 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.1.2 Docker Compose 설정
```yaml
# docker-compose.yml
version: '3.8'

services:
  # API 게이트웨이
  api-gateway:
    image: kong:3.4
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /kong/declarative/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_PLUGINS: rate-limiting, request-size-limiting, ip-restriction, oauth2, jwt
    volumes:
      - ./kong/kong.yml:/kong/declarative/kong.yml:ro
    ports:
      - "80:8000"
      - "443:8443"
      - "8001:8001"
      - "8444:8444"
    networks:
      - insitechart-network
    depends_on:
      - stock-search-service
      - sentiment-service
      - user-service
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "kong", "health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 주식 검색 서비스
  stock-search-service:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - YAHOO_FINANCE_API_KEY=${YAHOO_FINANCE_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    networks:
      - insitechart-network
    depends_on:
      - postgres
      - redis
      - rabbitmq
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 센티먼트 분석 서비스
  sentiment-service:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379/1
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - REDDIT_API_KEY=${REDDIT_API_KEY}
      - REDDIT_API_SECRET=${REDDIT_API_SECRET}
      - TWITTER_API_KEY=${TWITTER_API_KEY}
      - TWITTER_API_SECRET=${TWITTER_API_SECRET}
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    networks:
      - insitechart-network
    depends_on:
      - postgres
      - redis
      - rabbitmq
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 사용자 서비스
  user-service:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379/2
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    networks:
      - insitechart-network
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.3'
          memory: 256M
        reservations:
          cpus: '0.15'
          memory: 128M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 데이터 수집 서비스
  data-collection-service:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379/3
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - YAHOO_FINANCE_API_KEY=${YAHOO_FINANCE_API_KEY}
      - REDDIT_API_KEY=${REDDIT_API_KEY}
      - REDDIT_API_SECRET=${REDDIT_API_SECRET}
      - TWITTER_API_KEY=${TWITTER_API_KEY}
      - TWITTER_API_SECRET=${TWITTER_API_SECRET}
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    networks:
      - insitechart-network
    depends_on:
      - postgres
      - redis
      - rabbitmq
    restart: unless-stopped
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  # PostgreSQL 데이터베이스
  postgres:
    image: timescale/timescaledb:latest-pg14
    environment:
      - POSTGRES_DB=insitechart
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    networks:
      - insitechart-network
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis 캐시
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - insitechart-network
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # RabbitMQ 메시지 큐
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
      - RABBITMQ_DEFAULT_VHOST=insitechart
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - insitechart-network
    ports:
      - "5672:5672"
      - "15672:15672"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus 모니터링
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
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - insitechart-network
    ports:
      - "9090:9090"
    restart: unless-stopped

  # Grafana 대시보드
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    networks:
      - insitechart-network
    ports:
      - "3000:3000"
    restart: unless-stopped

  # Nginx 로드 밸런서
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    networks:
      - insitechart-network
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api-gateway
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  prometheus_data:
  grafana_data:

networks:
  insitechart-network:
    driver: bridge
```

### 1.2 쿠버네티스 배포

#### 1.2.1 쿠버네티스 매니페스트
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: insitechart
  labels:
    name: insitechart

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: insitechart-config
  namespace: insitechart
data:
  LOG_LEVEL: "INFO"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "insitechart"
  RABBITMQ_HOST: "rabbitmq-service"
  RABBITMQ_PORT: "5672"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: insitechart-secrets
  namespace: insitechart
type: Opaque
data:
  POSTGRES_PASSWORD: <base64-encoded-password>
  REDIS_PASSWORD: <base64-encoded-password>
  RABBITMQ_PASSWORD: <base64-encoded-password>
  SECRET_KEY: <base64-encoded-secret-key>
  JWT_SECRET_KEY: <base64-encoded-jwt-secret>
  YAHOO_FINANCE_API_KEY: <base64-encoded-yahoo-key>
  REDDIT_API_KEY: <base64-encoded-reddit-key>
  REDDIT_API_SECRET: <base64-encoded-reddit-secret>
  TWITTER_API_KEY: <base64-encoded-twitter-key>
  TWITTER_API_SECRET: <base64-encoded-twitter-secret>

---
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: insitechart
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: timescale/timescaledb:latest-pg14
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: insitechart-config
              key: POSTGRES_DB
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: insitechart-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: insitechart
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP

---
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: insitechart
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)", "--appendonly", "yes"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: insitechart-secrets
              key: REDIS_PASSWORD
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: insitechart
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: insitechart
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP

---
# k8s/stock-search-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-search-service
  namespace: insitechart
spec:
  replicas: 3
  selector:
    matchLabels:
      app: stock-search-service
  template:
    metadata:
      labels:
        app: stock-search-service
    spec:
      containers:
      - name: stock-search-service
        image: insitechart/stock-search-service:latest
        env:
        - name: DATABASE_URL
          value: "postgresql+asyncpg://postgres:$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)"
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@$(REDIS_HOST):$(REDIS_PORT)/0"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: insitechart-secrets
              key: SECRET_KEY
        - name: YAHOO_FINANCE_API_KEY
          valueFrom:
            secretKeyRef:
              name: insitechart-secrets
              key: YAHOO_FINANCE_API_KEY
        envFrom:
        - configMapRef:
            name: insitechart-config
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: stock-search-service
  namespace: insitechart
spec:
  selector:
    app: stock-search-service
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: insitechart-ingress
  namespace: insitechart
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.insitechart.com
    secretName: insitechart-tls
  rules:
  - host: api.insitechart.com
    http:
      paths:
      - path: /api/v1/stocks
        pathType: Prefix
        backend:
          service:
            name: stock-search-service
            port:
              number: 8000
      - path: /api/v1/sentiment
        pathType: Prefix
        backend:
          service:
            name: sentiment-service
            port:
              number: 8000
      - path: /api/v1/users
        pathType: Prefix
        backend:
          service:
            name: user-service
            port:
              number: 8000

---
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stock-search-service-hpa
  namespace: insitechart
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stock-search-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 1.3 블루-그린 배포

#### 1.3.1 블루-그린 배포 스크립트
```bash
#!/bin/bash
# deploy-blue-green.sh

set -e

# 환경 변수
ENVIRONMENT=${1:-production}
NEW_VERSION=${2:-latest}
NAMESPACE="insitechart"
SERVICE_NAME="stock-search-service"

# 색상 정의
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 활성 환경 확인
get_active_environment() {
    local active_env=$(kubectl get service ${SERVICE_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.selector.color}')
    echo ${active_env:-blue}
}

# 새 환경 배포
deploy_new_environment() {
    local new_color=$1
    local version=$2
    
    log_info "Deploying ${new_color} environment with version ${version}"
    
    # 새 배포 생성
    envsubst < k8s/${SERVICE_NAME}-${new_color}.yaml.template | kubectl apply -f -
    
    # 배포 상태 확인
    log_info "Waiting for ${new_color} deployment to be ready..."
    kubectl rollout status deployment/${SERVICE_NAME}-${new_color} -n ${NAMESPACE} --timeout=300s
    
    # 파드 상태 확인
    local ready_pods=$(kubectl get pods -n ${NAMESPACE} -l color=${new_color} -o jsonpath='{.items[*].status.containerStatuses[*].ready}')
    
    if [[ "$ready_pods" == *"true"* ]]; then
        log_success "${new_color} deployment is ready"
        return 0
    else
        log_error "${new_color} deployment failed"
        return 1
    fi
}

# 헬스 체크
health_check() {
    local color=$1
    local service_url=$(kubectl get service ${SERVICE_NAME}-${color} -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    if [[ -z "$service_url" ]]; then
        log_warning "No external IP found for ${color} service"
        return 1
    fi
    
    log_info "Performing health check on ${color} environment..."
    
    # 헬스 체크 엔드포인트 호출
    local health_check_url="http://${service_url}:8000/health"
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" ${health_check_url})
        
        if [[ "$response" == "200" ]]; then
            log_success "Health check passed for ${color} environment"
            return 0
        fi
        
        log_info "Health check attempt ${attempt}/${max_attempts} failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed for ${color} environment after ${max_attempts} attempts"
    return 1
}

# 트래픽 전환
switch_traffic() {
    local new_color=$1
    
    log_info "Switching traffic to ${new_color} environment..."
    
    # 서비스 선택자 업데이트
    kubectl patch service ${SERVICE_NAME} -n ${NAMESPACE} -p '{"spec":{"selector":{"color":"'${new_color}'"}}}'
    
    log_success "Traffic switched to ${new_color} environment"
}

# 이전 환경 정리
cleanup_old_environment() {
    local old_color=$1
    
    log_info "Cleaning up ${old_color} environment..."
    
    # 이전 배포 삭제
    kubectl delete deployment ${SERVICE_NAME}-${old_color} -n ${NAMESPACE} --ignore-not-found=true
    kubectl delete service ${SERVICE_NAME}-${old_color} -n ${NAMESPACE} --ignore-not-found=true
    
    log_success "Cleaned up ${old_color} environment"
}

# 롤백
rollback() {
    local old_color=$1
    
    log_warning "Rolling back to ${old_color} environment..."
    
    # 트래픽 전환
    switch_traffic $old_color
    
    # 새 환경 정리
    cleanup_old_environment $([[ "$old_color" == "blue" ]] && echo "green" || echo "blue")
    
    log_success "Rollback completed"
}

# 메인 배포 프로세스
main() {
    log_info "Starting blue-green deployment for ${SERVICE_NAME} in ${ENVIRONMENT}"
    
    # 현재 활성 환경 확인
    local active_color=$(get_active_environment)
    log_info "Currently active environment: ${active_color}"
    
    # 새 환경 색상 결정
    local new_color=$([[ "$active_color" == "blue" ]] && echo "green" || echo "blue")
    log_info "New environment color: ${new_color}"
    
    # 새 환경 배포
    if ! deploy_new_environment $new_color $NEW_VERSION; then
        log_error "Failed to deploy new environment"
        exit 1
    fi
    
    # 헬스 체크
    if ! health_check $new_color; then
        log_error "Health check failed for new environment"
        log_info "Keeping ${active_color} environment active"
        cleanup_old_environment $new_color
        exit 1
    fi
    
    # 트래픽 전환
    switch_traffic $new_color
    
    # 배포 후 헬스 체크
    log_info "Performing post-deployment health check..."
    sleep 30
    
    if ! health_check $new_color; then
        log_warning "Post-deployment health check failed, rolling back..."
        rollback $active_color
        exit 1
    fi
    
    # 이전 환경 정리
    cleanup_old_environment $active_color
    
    log_success "Blue-green deployment completed successfully"
    log_info "Active environment is now: ${new_color}"
}

# 스크립트 실행
main
```

## 2. CI/CD 파이프라인

### 2.1 GitHub Actions 워크플로우

#### 2.1.1 빌드 및 배포 파이프라인
```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [ main, develop ]
    tags:
      - 'v*'
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: insitechart

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
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
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 app tests
        black --check app tests
        isort --check-only app tests
    
    - name: Run type checking
      run: |
        mypy app
    
    - name: Run security checks
      run: |
        bandit -r app
        safety check
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        pytest tests/unit -v --cov=app --cov-report=xml --cov-report=html
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
        YAHOO_API_KEY: ${{ secrets.YAHOO_API_KEY }}
        REDDIT_API_KEY: ${{ secrets.REDDIT_API_KEY }}
        TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
      run: |
        pytest tests/integration -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          type=sha,prefix={{branch}}-
    
    - name: Build and push Docker image
      id: build
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.24.0'
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
    
    - name: Deploy to staging
      run: |
        export KUBECONFIG=kubeconfig
        
        # 네임스페이스 확인
        kubectl get namespace insitechart-staging || kubectl create namespace insitechart-staging
        
        # 시크릿 생성
        kubectl create secret generic insitechart-secrets \
          --from-literal=POSTGRES_PASSWORD="${{ secrets.POSTGRES_PASSWORD_STAGING }}" \
          --from-literal=REDIS_PASSWORD="${{ secrets.REDIS_PASSWORD_STAGING }}" \
          --from-literal=SECRET_KEY="${{ secrets.SECRET_KEY_STAGING }}" \
          --from-literal=YAHOO_FINANCE_API_KEY="${{ secrets.YAHOO_FINANCE_API_KEY }}" \
          --namespace=insitechart-staging \
          --dry-run=client -o yaml | kubectl apply -f -
        
        # 이미지 태그 업데이트
        sed -i "s|IMAGE_TAG|${{ needs.build.outputs.image-tag }}|g" k8s/staging/*.yaml
        
        # 배포
        kubectl apply -f k8s/staging/ --namespace=insitechart-staging
        
        # 배포 상태 확인
        kubectl rollout status deployment/stock-search-service --namespace=insitechart-staging --timeout=300s
        kubectl rollout status deployment/sentiment-service --namespace=insitechart-staging --timeout=300s
        kubectl rollout status deployment/user-service --namespace=insitechart-staging --timeout=300s
    
    - name: Run E2E tests on staging
      run: |
        # 스테이징 환경 E2E 테스트
        pytest tests/e2e --base-url=https://staging.insitechart.com -v

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.24.0'
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG_PRODUCTION }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
    
    - name: Deploy to production (Blue-Green)
      run: |
        export KUBECONFIG=kubeconfig
        
        # 블루-그린 배포 스크립트 실행
        chmod +x scripts/deploy-blue-green.sh
        ./scripts/deploy-blue-green.sh production ${{ needs.build.outputs.image-tag }}
    
    - name: Run smoke tests
      run: |
        # 프로덕션 환경 스모크 테스트
        pytest tests/smoke --base-url=https://api.insitechart.com -v
    
    - name: Notify deployment
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        text: "Production deployment completed successfully"
      if: success()

  rollback:
    needs: deploy-production
    runs-on: ubuntu-latest
    if: failure() && github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.24.0'
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG_PRODUCTION }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
    
    - name: Rollback deployment
      run: |
        export KUBECONFIG=kubeconfig
        
        # 롤백 스크립트 실행
        chmod +x scripts/rollback.sh
        ./scripts/rollback.sh production
    
    - name: Notify rollback
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        text: "Production deployment failed, rolled back successfully"
```

## 3. 운영 모니터링

### 3.1 로깅 시스템

#### 3.1.1 ELK 스택 구성
```yaml
# logging/elasticsearch.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    container_name: elasticsearch
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
      - elk

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    container_name: logstash
    ports:
      - "5044:5044"
      - "5000:5000/tcp"
      - "5000:5000/udp"
      - "9600:9600"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
      - ./logstash/config:/usr/share/logstash/config:ro
    networks:
      - elk
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - elk
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.5.0
    container_name: filebeat
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/log:/var/log:ro
    networks:
      - elk
    depends_on:
      - logstash

volumes:
  elasticsearch_data:

networks:
  elk:
    driver: bridge
```

#### 3.1.2 Logstash 파이프라인 설정
```ruby
# logstash/pipeline/logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  # JSON 파싱
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
    }
  }

  # 타임스탬프 파싱
  if [timestamp] {
    date {
      match => [ "timestamp", "ISO8601" ]
    }
  }

  # 애플리케이션 로그 필터링
  if [fields][service] {
    mutate {
      add_field => { "service_name" => "%{[fields][service]}" }
    }
  }

  # 로그 레벨 필터링
  if [level] {
    mutate {
      add_field => { "log_level" => "%{level}" }
    }
  }

  # 에러 로그 강조
  if [log_level] == "ERROR" or [log_level] == "CRITICAL" {
    mutate {
      add_tag => [ "error" ]
    }
  }

  # IP 주소 추출
  grok {
    match => { "message" => "%{IPORHOST:client_ip}" }
  }

  # 지리적 위치 정보 추가 (GeoIP)
  if [client_ip] {
    geoip {
      source => "client_ip"
      target => "geoip"
    }
  }

  # 사용자 에이전트 파싱
  if [user_agent] {
    useragent {
      source => "user_agent"
      target => "user_agent"
    }
  }

  # 요청 ID 추적
  if [request_id] {
    mutate {
      add_field => { "trace_id" => "%{request_id}" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "insitechart-logs-%{+YYYY.MM.dd}"
  }

  # 에러 로그는 별도 인덱스에 저장
  if "error" in [tags] {
    elasticsearch {
      hosts => ["elasticsearch:9200"]
      index => "insitechart-errors-%{+YYYY.MM.dd}"
    }
  }

  # 디버그 출력 (개발 환경)
  stdout {
    codec => rubydebug
  }
}
```

### 3.2 메트릭 수집

#### 3.2.1 Prometheus 설정
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Prometheus 자체 모니터링
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # 애플리케이션 서비스 모니터링
  - job_name: 'stock-search-service'
    static_configs:
      - targets: ['stock-search-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'sentiment-service'
    static_configs:
      - targets: ['sentiment-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'user-service'
    static_configs:
      - targets: ['user-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # 데이터베이스 모니터링
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis 모니터링
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # RabbitMQ 모니터링
  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['rabbitmq:15692']

  # 노드 모니터링
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # 쿠버네티스 모니터링
  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
      - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https

  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name
```

#### 3.2.2 알림 규칙
```yaml
# monitoring/alert_rules.yml
groups:
- name: insitechart.rules
  rules:
  # 애플리케이션 다운 알림
  - alert: ServiceDown
    expr: up{job=~"stock-search-service|sentiment-service|user-service"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.job }} is down"
      description: "Service {{ $labels.job }} has been down for more than 1 minute."

  # 높은 CPU 사용률 알림
  - alert: HighCPUUsage
    expr: 100 * (1 - avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m]))) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage on {{ $labels.instance }}"
      description: "CPU usage is above 80% for more than 5 minutes on {{ $labels.instance }}."

  # 높은 메모리 사용률 알림
  - alert: HighMemoryUsage
    expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage on {{ $labels.instance }}"
      description: "Memory usage is above 85% for more than 5 minutes on {{ $labels.instance }}."

  # 디스크 공간 부족 알림
  - alert: DiskSpaceLow
    expr: (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 90
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Disk space low on {{ $labels.instance }}"
      description: "Disk usage is above 90% for more than 5 minutes on {{ $labels.instance }}."

  # 데이터베이스 연결 실패 알림
  - alert: DatabaseConnectionFailure
    expr: postgres_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failure"
      description: "Cannot connect to PostgreSQL database."

  # 높은 데이터베이스 연결 수 알림
  - alert: HighDatabaseConnections
    expr: postgres_stat_database_numbackends / postgres_settings_max_connections * 100 > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High number of database connections"
      description: "Database connection usage is above 80%."

  # API 응답 시간 알림
  - alert: HighAPIResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API response time"
      description: "95th percentile response time is above 1 second for {{ $labels.job }}."

  # API 에러율 알림
  - alert: HighAPIErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100 > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API error rate"
      description: "Error rate is above 5% for {{ $labels.job }}."

  # Redis 다운 알림
  - alert: RedisDown
    expr: redis_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Redis is down"
      description: "Redis server has been down for more than 1 minute."

  # RabbitMQ 큐 길이 알림
  - alert: RabbitMQQueueLength
    expr: rabbitmq_queue_messages > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High RabbitMQ queue length"
      description: "Queue {{ $labels.queue }} has more than 1000 messages."

  # 파드 재시작 알림
  - alert: PodRestartHigh
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Pod {{ $labels.pod }} is restarting frequently"
      description: "Pod {{ $labels.pod }} has restarted {{ $value }} times in the last 15 minutes."
```

## 4. 재해 복구

### 4.1 백업 전략

#### 4.1.1 데이터베이스 백업 스크립트
```bash
#!/bin/bash
# backup-database.sh

set -e

# 환경 변수
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="insitechart_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=30
S3_BUCKET="insitechart-backups"

# 색상 정의
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 백업 디렉토리 생성
create_backup_dir() {
    log_info "Creating backup directory..."
    mkdir -p ${BACKUP_DIR}
    chmod 700 ${BACKUP_DIR}
}

# 데이터베이스 백업
backup_database() {
    log_info "Starting database backup..."
    
    # pg_dump를 사용한 백업
    PGPASSWORD=${POSTGRES_PASSWORD} pg_dump \
        -h ${POSTGRES_HOST} \
        -p ${POSTGRES_PORT} \
        -U ${POSTGRES_USER} \
        -d ${POSTGRES_DB} \
        --format=custom \
        --compress=9 \
        --verbose \
        --file=${BACKUP_DIR}/${BACKUP_FILE}
    
    if [[ $? -eq 0 ]]; then
        log_success "Database backup completed: ${BACKUP_FILE}"
        
        # 백업 파일 크기 확인
        local file_size=$(du -h ${BACKUP_DIR}/${BACKUP_FILE} | cut -f1)
        log_info "Backup file size: ${file_size}"
        
        # 백업 파일 압축
        gzip ${BACKUP_DIR}/${BACKUP_FILE}
        BACKUP_FILE="${BACKUP_FILE}.gz"
        
        return 0
    else
        log_error "Database backup failed"
        return 1
    fi
}

# S3에 백업 업로드
upload_to_s3() {
    log_info "Uploading backup to S3..."
    
    aws s3 cp ${BACKUP_DIR}/${BACKUP_FILE} s3://${S3_BUCKET}/postgres/
    
    if [[ $? -eq 0 ]]; then
        log_success "Backup uploaded to S3: s3://${S3_BUCKET}/postgres/${BACKUP_FILE}"
        return 0
    else
        log_error "Failed to upload backup to S3"
        return 1
    fi
}

# 백업 검증
verify_backup() {
    log_info "Verifying backup integrity..."
    
    # 백업 파일 복원 테스트 (새 데이터베이스에)
    local test_db="test_restore_${TIMESTAMP}"
    
    createdb -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} ${test_db}
    
    PGPASSWORD=${POSTGRES_PASSWORD} pg_restore \
        -h ${POSTGRES_HOST} \
        -p ${POSTGRES_PORT} \
        -U ${POSTGRES_USER} \
        -d ${test_db} \
        --verbose \
        ${BACKUP_DIR}/${BACKUP_FILE}
    
    if [[ $? -eq 0 ]]; then
        log_success "Backup verification successful"
        
        # 테스트 데이터베이스 삭제
        dropdb -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} ${test_db}
        
        return 0
    else
        log_error "Backup verification failed"
        return 1
    fi
}

# 오래된 백업 정리
cleanup_old_backups() {
    log_info "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
    
    # 로컬 백업 정리
    find ${BACKUP_DIR} -name "*.gz" -type f -mtime +${RETENTION_DAYS} -delete
    
    # S3 백업 정리
    aws s3 ls s3://${S3_BUCKET}/postgres/ | while read -r line; do
        createDate=$(echo $line | awk '{print $1" "$2}')
        createDate=$(date -d "$createDate" +%s)
        olderThan=$(date -d "${RETENTION_DAYS} days ago" +%s)
        
        if [[ $createDate -lt $olderThan ]]; then
            fileName=$(echo $line | awk '{print $4}')
            if [[ $fileName != "" ]]; then
                aws s3 rm s3://${S3_BUCKET}/postgres/$fileName
                log_info "Deleted old backup: $fileName"
            fi
        fi
    done
    
    log_success "Old backups cleanup completed"
}

# 백업 알림
send_notification() {
    local status=$1
    local message=$2
    
    # Slack 알림
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"Database Backup ${status}: ${message}\"}" \
        ${SLACK_WEBHOOK_URL}
    
    # 이메일 알림 (선택적)
    if [[ ${status} == "SUCCESS" ]]; then
        echo "${message}" | mail -s "Database Backup Success" ${ADMIN_EMAIL}
    else
        echo "${message}" | mail -s "Database Backup Failed" ${ADMIN_EMAIL}
    fi
}

# 메인 함수
main() {
    log_info "Starting database backup process..."
    
    # 백업 디렉토리 생성
    create_backup_dir
    
    # 데이터베이스 백업
    if backup_database; then
        # 백업 검증
        if verify_backup; then
            # S3 업로드
            if upload_to_s3; then
                # 오래된 백업 정리
                cleanup_old_backups
                
                log_success "Database backup process completed successfully"
                send_notification "SUCCESS" "Database backup completed successfully: ${BACKUP_FILE}"
            else
                log_error "Failed to upload backup to S3"
                send_notification "FAILED" "Failed to upload backup to S3"
                exit 1
            fi
        else
            log_error "Backup verification failed"
            send_notification "FAILED" "Backup verification failed"
            exit 1
        fi
    else
        log_error "Database backup failed"
        send_notification "FAILED" "Database backup failed"
        exit 1
    fi
}

# 스크립트 실행
main
```

### 4.2 재해 복구 계획

#### 4.2.1 재해 복구 절차
```markdown
# 재해 복구 절서

## 1. 재해 유형별 대응

### 1.1 데이터베이스 장애
- **증상**: 데이터베이스 연결 실패, 응답 시간 증가
- **영향도**: 높음 (서비스 전체 장애)
- **복구 시간 목표 (RTO)**: 1시간
- **복구 지점 목표 (RPO)**: 15분

#### 복구 절차
1. **장애 확인** (5분)
   - 모니터링 시스템 알림 확인
   - 데이터베이스 상태 확인
   - 영향 범위 파악

2. **근본 원인 분석** (15분)
   - 로그 분석
   - 시스템 리소스 확인
   - 네트워크 상태 확인

3. **복구 전략 선택** (5분)
   - 최신 백업 복원
   - 스트리밍 복제 전환
   - 장애 조치

4. **복구 실행** (30분)
   - 백업 파일 다운로드
   - 데이터베이스 복원
   - 데이터 일관성 검증

5. **서비스 재시작** (5분)
   - 애플리케이션 서비스 재시작
   - 연결 테스트
   - 기능 검증

### 1.2 애플리케이션 서비스 장애
- **증상**: API 응답 실패, 5xx 에러 증가
- **영향도**: 중간 (일부 기능 장애)
- **RTO**: 30분
- **RPO**: 5분

#### 복구 절차
1. **장애 확인** (5분)
   - 헬스체크 실패 확인
   - 에러 로그 분석
   - 영향 범위 파악

2. **서비스 재시작** (10분)
   - 문제 서비스 식별
   - 롤링 재시작
   - 상태 모니터링

3. **롤백 고려** (10분)
   - 이전 버전으로 롤백
   - 데이터 일관성 확인
   - 기능 검증

4. **근본 원인 해결** (5분)
   - 버그 수정
   - 설정 조정
   - 재발 방지 조치

### 1.3 인프라 장애
- **증상**: 서버 다운, 네트워크 단절
- **영향도**: 높음 (서비스 전체 장애)
- **RTO**: 2시간
- **RPO**: 1시간

#### 복구 절차
1. **장애 확인** (15분)
   - 인프라 상태 확인
   - 영향 범위 파악
   - 재해 복구팀 소집

2. **대체 인프라 준비** (45분)
   - DR 사이트 활성화
   - 네트워크 구성
   - 데이터 복원

3. **서비스 전환** (30분)
   - DNS 변경
   - 부하 분산 조정
   - 연결 테스트

4. **안정화 확인** (30분)
   - 모니터링 강화
   - 성능 확인
   - 사용자 알림

## 2. 재해 복구 훈련

### 2.1 훈련 계획
- **빈도**: 분기별 1회
- **참여자**: 개발팀, 운영팀, 인프라팀
- **시나리오**: 실제 장애 상황 시뮬레이션
- **목표**: RTO/RPO 달성 여부 확인, 절차 개선

### 2.2 훈련 시나리오
1. **데이터베이스 장애 시뮬레이션**
   - 주 데이터베이스 서버 중단
   - 복제본으로 전환 테스트
   - 백업 복원 테스트

2. **애플리케이션 장애 시뮬레이션**
   - 주요 서비스 중단
   - 블루-그린 전환 테스트
   - 롤백 절차 테스트

3. **인프라 장애 시뮬레이션**
   - 데이터센터 장애 가정
   - DR 사이트 전환 테스트
   - 네트워크 복구 테스트

## 3. 재해 복구 체크리스트

### 3.1 사전 준비
- [ ] 백업 최신성 확인
- [ ] 복구 절차 문서 최신화
- [ ] 담당자 연락처 확인
- [ ] DR 인프라 상태 확인
- [ ] 복구 도구 준비 상태 확인

### 3.2 장애 발생 시
- [ ] 장애 알림 확인
- [ ] 영향 범위 파악
- [ ] 재해 복구팀 소집
- [ ] 근본 원인 분석 시작
- [ ] 사용자 알림 발송

### 3.3 복구 실행
- [ ] 복구 전략 결정
- [ ] 복구 절차 실행
- [ ] 진행 상황 기록
- [ ] 복구 상태 모니터링
- [ ] 정상화 여부 확인

### 3.4 사후 조치
- [ ] 서비스 안정화 확인
- [ ] 근본 원인 분석 완료
- [ ] 재발 방지 대책 수립
- [ ] 복구 절차 개선
- [ ] 훈련 결과 보고서 작성
```

이 배포 및 운영 계획 문서는 시스템의 안정적인 배포와 운영을 위한 포괄적인 접근 방식을 제공합니다. 컨테이너화, 쿠버네티스 배포, CI/CD 파이프라인, 모니터링, 재해 복구 등을 통해 안정적이고 신뢰성 높은 시스템 운영을 보장할 수 있습니다.