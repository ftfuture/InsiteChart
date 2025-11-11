# 단순화된 배포 및 운영 계획

## 1. 단순화된 배포 전략

### 1.1 기본 컨테이너화

#### 1.1.1 단순화된 Dockerfile
```dockerfile
# Dockerfile
# 단순화된 단일 단계 빌드

FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 시작 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.1.2 단순화된 Docker Compose 설정
```yaml
# docker-compose.yml
version: '3.8'

services:
  # 통합 서비스
  unified-service:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/insitechart
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    networks:
      - insitechart-network
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL 데이터베이스
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=insitechart
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
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
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - insitechart-network
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  insitechart-network:
    driver: bridge
```

### 1.2 단순화된 쿠버네티스 배포

#### 1.2.1 기본 쿠버네티스 매니페스트
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
  SECRET_KEY: <base64-encoded-secret-key>
  YAHOO_FINANCE_API_KEY: <base64-encoded-yahoo-key>

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
        image: postgres:14
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
            memory: "512Mi"
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
          storage: 10Gi

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
        command: ["redis-server", "--appendonly", "yes"]
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
            memory: "256Mi"
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
      storage: 2Gi

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
# k8s/unified-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unified-service
  namespace: insitechart
spec:
  replicas: 2
  selector:
    matchLabels:
      app: unified-service
  template:
    metadata:
      labels:
        app: unified-service
    spec:
      containers:
      - name: unified-service
        image: insitechart/unified-service:latest
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)"
        - name: REDIS_URL
          value: "redis://$(REDIS_HOST):$(REDIS_PORT)/0"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: insitechart-secrets
              key: SECRET_KEY
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
  name: unified-service
  namespace: insitechart
spec:
  selector:
    app: unified-service
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
spec:
  rules:
  - host: api.insitechart.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: unified-service
            port:
              number: 8000
```

### 1.3 단순화된 롤링 배포

#### 1.3.1 기본 롤링 배포 스크립트
```bash
#!/bin/bash
# deploy-rolling.sh

set -e

# 환경 변수
ENVIRONMENT=${1:-production}
NEW_VERSION=${2:-latest}
NAMESPACE="insitechart"
SERVICE_NAME="unified-service"

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

# 롤링 업데이트
update_rolling_deployment() {
    local version=$1
    
    log_info "Updating rolling deployment with version ${version}"
    
    # 이미지 태그 업데이트
    kubectl set image deployment/${SERVICE_NAME} ${SERVICE_NAME}=insitechart/${SERVICE_NAME}:${version} -n ${NAMESPACE}
    
    # 롤링 업데이트 상태 확인
    log_info "Waiting for rolling update to complete..."
    kubectl rollout status deployment/${SERVICE_NAME} -n ${NAMESPACE} --timeout=600s
    
    # 배포 상태 확인
    local ready_replicas=$(kubectl get deployment ${SERVICE_NAME} -n ${NAMESPACE} -o jsonpath='{.status.readyReplicas}')
    local replicas=$(kubectl get deployment ${SERVICE_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}')
    
    if [[ "$ready_replicas" == "$replicas" ]]; then
        log_success "Rolling update completed successfully"
        return 0
    else
        log_error "Rolling update failed"
        return 1
    fi
}

# 헬스 체크
health_check() {
    log_info "Performing health check..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local response=$(kubectl get pods -n ${NAMESPACE} -l app=${SERVICE_NAME} -o jsonpath='{.items[*].status.containerStatuses[*].ready}')
        
        if [[ "$response" == *"true"* ]]; then
            log_success "Health check passed"
            return 0
        fi
        
        log_info "Health check attempt ${attempt}/${max_attempts} failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after ${max_attempts} attempts"
    return 1
}

# 롤백
rollback() {
    log_warning "Rolling back to previous revision..."
    
    # 롤백 실행
    kubectl rollout undo deployment/${SERVICE_NAME} -n ${NAMESPACE}
    
    # 롤백 상태 확인
    kubectl rollout status deployment/${SERVICE_NAME} -n ${NAMESPACE} --timeout=300s
    
    log_success "Rollback completed"
}

# 메인 배포 프로세스
main() {
    log_info "Starting rolling deployment for ${SERVICE_NAME} in ${ENVIRONMENT}"
    
    # 롤링 업데이트
    if ! update_rolling_deployment $NEW_VERSION; then
        log_error "Failed to update deployment"
        exit 1
    fi
    
    # 헬스 체크
    if ! health_check; then
        log_warning "Health check failed, rolling back..."
        rollback
        exit 1
    fi
    
    log_success "Rolling deployment completed successfully"
}

# 스크립트 실행
main
```

## 2. 단순화된 CI/CD 파이프라인

### 2.1 기본 GitHub Actions 워크플로우

#### 2.1.1 단순화된 빌드 및 배포 파이프라인
```yaml
# .github/workflows/simple-deploy.yml
name: Simple Build and Deploy

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
        python-version: [3.11]
    
    services:
      postgres:
        image: postgres:14
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
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_insitechart
        REDIS_URL: redis://localhost:6379/1
        SECRET_KEY: test-secret-key
      run: |
        pytest tests/unit -v --cov=app --cov-report=xml
    
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
          type=semver,pattern={{version}}
          type=sha,prefix={{branch}}-
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # 실제 배포 로직은 여기에 구현
        echo "Deployment completed"

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # 실제 배포 로직은 여기에 구현
        echo "Deployment completed"
    
    - name: Notify deployment
      run: |
        echo "Production deployment completed successfully"
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

## 4. 단순화된 재해 복구

### 4.1 기본 백업 전략

#### 4.1.1 단순화된 데이터베이스 백업 스크립트
```bash
#!/bin/bash
# simple-backup.sh

set -e

# 환경 변수
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="insitechart_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=7

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 백업 디렉토리 생성
create_backup_dir() {
    log_info "Creating backup directory..."
    mkdir -p ${BACKUP_DIR}
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
        --file=${BACKUP_DIR}/${BACKUP_FILE}
    
    if [[ $? -eq 0 ]]; then
        log_success "Database backup completed: ${BACKUP_FILE}"
        
        # 백업 파일 압축
        gzip ${BACKUP_DIR}/${BACKUP_FILE}
        BACKUP_FILE="${BACKUP_FILE}.gz"
        
        return 0
    else
        log_error "Database backup failed"
        return 1
    fi
}

# 오래된 백업 정리
cleanup_old_backups() {
    log_info "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
    
    # 로컬 백업 정리
    find ${BACKUP_DIR} -name "*.gz" -type f -mtime +${RETENTION_DAYS} -delete
    
    log_success "Old backups cleanup completed"
}

# 메인 함수
main() {
    log_info "Starting simple backup process..."
    
    # 백업 디렉토리 생성
    create_backup_dir
    
    # 데이터베이스 백업
    if backup_database; then
        # 오래된 백업 정리
        cleanup_old_backups
        
        log_success "Simple backup process completed successfully"
    else
        log_error "Database backup failed"
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

이 단순화된 배포 및 운영 계획 문서는 시스템의 기본적인 배포와 운영을 위한 단순한 접근 방식을 제공합니다. 컨테이너화, 기본 쿠버네티스 배포, 단순화된 CI/CD 파이프라인, 기본 모니터링, 재해 복구 등을 통해 안정적인 시스템 운영을 보장할 수 있습니다.