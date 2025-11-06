# 배포 및 운영 자동화 계획

## 1. 개요

본 문서는 주식 차트 분석 애플리케이션의 배포 및 운영 자동화를 위한 상세한 계획을 제시합니다. Docker 컨테이너화, Kubernetes 오케스트레이션, CI/CD 파이프라인, 모니터링 시스템, 재해 복구 등 다양한 운영 자동화 측면을 다룹니다.

## 2. 컨테이너화 전략

### 2.1 다단계 Docker 빌드
```dockerfile
# Dockerfile.multi-stage
# 빌드 스테이지
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend/ ./
RUN npm run build

# Python 애플리케이션 빌드 스테이지
FROM python:3.11-slim AS backend-builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY . .
RUN python -m py_compile services/*.py

# 최종 런타임 스테이지
FROM python:3.11-slim AS runtime

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 비루트 사용자 생성
RUN useradd --create-home --shell /bin/bash app

# 애플리케이션 디렉토리 구조
WORKDIR /app

# Python 패키지 복사
COPY --from=backend-builder /root/.local /home/app/.local
ENV PATH=/home/app/.local/bin:$PATH

# 소스 코드 복사
COPY --chown=app:app . .

# 프론트엔드 빌드 결과 복사
COPY --from=frontend-builder /app/frontend/dist /app/static

# 권한 설정
RUN chown -R app:app /app

# 비루트 사용자로 전환
USER app

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 포트 노출
EXPOSE 8000

# 시작 명령
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 서비스별 Dockerfile
```dockerfile
# services/stock-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 비루트 사용자 생성
RUN useradd --create-home --shell /bin/bash stockuser
RUN chown -R stockuser:stockuser /app
USER stockuser

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')" || exit 1

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 2.3 Docker Compose 개발 환경
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # 데이터베이스 서비스
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    container_name: timescaledb-dev
    environment:
      POSTGRES_DB: stockdb
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    networks:
      - stock-network

  # Redis 서비스
  redis:
    image: redis:7-alpine
    container_name: redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    networks:
      - stock-network

  # Kafka 서비스
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    container_name: zookeeper-dev
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - stock-network

  kafka:
    image: confluentinc/cp-kafka:latest
    container_name: kafka-dev
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks:
      - stock-network

  # Stock Service
  stock-service:
    build:
      context: ./services/stock-service
      dockerfile: Dockerfile
    container_name: stock-service-dev
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://dev_user:dev_password@timescaledb:5432/stockdb
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - LOG_LEVEL=DEBUG
    depends_on:
      - timescaledb
      - redis
      - kafka
    volumes:
      - ./services/stock-service:/app
    networks:
      - stock-network

  # Sentiment Service
  sentiment-service:
    build:
      context: ./services/sentiment-service
      dockerfile: Dockerfile
    container_name: sentiment-service-dev
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql://dev_user:dev_password@timescaledb:5432/stockdb
      - REDIS_URL=redis://redis:6379/0
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
      - TWITTER_BEARER_TOKEN=${TWITTER_BEARER_TOKEN}
      - LOG_LEVEL=DEBUG
    depends_on:
      - timescaledb
      - redis
    volumes:
      - ./services/sentiment-service:/app
    networks:
      - stock-network

  # API Gateway
  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    container_name: api-gateway-dev
    ports:
      - "8080:8080"
    environment:
      - STOCK_SERVICE_URL=http://stock-service:8001
      - SENTIMENT_SERVICE_URL=http://sentiment-service:8002
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=DEBUG
    depends_on:
      - stock-service
      - sentiment-service
    volumes:
      - ./services/api-gateway:/app
    networks:
      - stock-network

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: frontend-dev
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8080
      - REACT_APP_WS_URL=ws://localhost:8080
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - stock-network

volumes:
  timescaledb_data:
  redis_data:

networks:
  stock-network:
    driver: bridge
```

## 3. Kubernetes 배포 전략

### 3.1 네임스페이스 및 리소스 설정
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: stock-analysis
  labels:
    name: stock-analysis
    environment: development

---
# k8s/resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: stock-analysis-quota
  namespace: stock-analysis
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: "10"
    services: "10"
    secrets: "10"
    configmaps: "20"

---
# k8s/limit-range.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: stock-analysis-limits
  namespace: stock-analysis
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
```

### 3.2 데이터베이스 배포 매니페스트
```yaml
# k8s/timescaledb-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: timescaledb
  namespace: stock-analysis
spec:
  serviceName: timescaledb
  replicas: 1
  selector:
    matchLabels:
      app: timescaledb
  template:
    metadata:
      labels:
        app: timescaledb
    spec:
      containers:
      - name: timescaledb
        image: timescale/timescaledb:latest-pg14
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "stockdb"
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: password
        volumeMounts:
        - name: timescaledb-storage
          mountPath: /var/lib/postgresql/data
        - name: timescaledb-config
          mountPath: /etc/postgresql/postgresql.conf
          subPath: postgresql.conf
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - $(POSTGRES_USER)
            - -d
            - $(POSTGRES_DB)
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - $(POSTGRES_USER)
            - -d
            - $(POSTGRES_DB)
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: timescaledb-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 100Gi
  volumes:
  - name: timescaledb-config
    configMap:
      name: timescaledb-config

---
# k8s/timescaledb-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: timescaledb
  namespace: stock-analysis
spec:
  selector:
    app: timescaledb
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### 3.3 마이크로서비스 배포 매니페스트
```yaml
# k8s/stock-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-service
  namespace: stock-analysis
  labels:
    app: stock-service
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: stock-service
  template:
    metadata:
      labels:
        app: stock-service
        version: v1
    spec:
      containers:
      - name: stock-service
        image: stock-analysis/stock-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        - name: LOG_LEVEL
          value: "INFO"
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]

---

# k8s/stock-service-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: stock-service
  namespace: stock-analysis
spec:
  selector:
    app: stock-service
  ports:
  - name: http
    port: 8001
    targetPort: 8001
  type: ClusterIP

---

# k8s/stock-service-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stock-service-hpa
  namespace: stock-analysis
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stock-service
  minReplicas: 3
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### 3.4 Ingress 및 로드 밸런싱
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: stock-analysis-ingress
  namespace: stock-analysis
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.stockanalysis.com
    secretName: stockanalysis-tls
  rules:
  - host: api.stockanalysis.com
    http:
      paths:
      - path: /api/v1/stocks(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: stock-service
            port:
              number: 8001
      - path: /api/v1/sentiment(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: sentiment-service
            port:
              number: 8002
      - path: /api(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80

---

# k8s/certificate.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: stockanalysis-tls
  namespace: stock-analysis
spec:
  secretName: stockanalysis-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - api.stockanalysis.com
  - stockanalysis.com
  - www.stockanalysis.com
```

## 4. CI/CD 파이프라인

### 4.1 GitHub Actions CI/CD 파이프라인
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  release:
    types: [ published ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: stock-analysis

jobs:
  # 코드 품질 검사
  code-quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flake8 black isort mypy bandit safety
    
    - name: Run code formatting checks
      run: |
        black --check .
        isort --check-only .
    
    - name: Run linting
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        mypy services/
    
    - name: Run security checks
      run: |
        bandit -r services/ -f json -o bandit-report.json
        safety check --json --output safety-report.json
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json

  # 단위 테스트
  unit-tests:
    runs-on: ubuntu-latest
    needs: code-quality
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=services --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  # 통합 테스트
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Start test environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 60
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --cov=services --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: integration
    
    - name: Cleanup test environment
      if: always()
      run: |
        docker-compose -f docker-compose.test.yml down -v

  # E2E 테스트
  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd frontend
        npm install
    
    - name: Install Playwright
      run: |
        cd frontend
        npx playwright install
    
    - name: Start test environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 60
    
    - name: Run E2E tests
      run: |
        cd frontend
        npx playwright test
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: playwright-report
        path: frontend/playwright-report/

  # Docker 이미지 빌드
  build-images:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    
    steps:
    - uses: actions/checkout@v3
    
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

  # 보안 스캔
  security-scan:
    runs-on: ubuntu-latest
    needs: build-images
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ needs.build-images.outputs.image-tag }}
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  # 스테이징 배포
  deploy-staging:
    runs-on: ubuntu-latest
    needs: [build-images, e2e-tests]
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v1
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}
    
    - name: Deploy to staging
      run: |
        helm upgrade --install stock-analysis-staging ./helm/stock-analysis \
          --namespace staging \
          --set image.tag=${{ needs.build-images.outputs.image-tag }} \
          --set environment=staging \
          --wait \
          --timeout=10m
    
    - name: Verify deployment
      run: |
        kubectl rollout status deployment/stock-analysis-staging --namespace staging
        kubectl get pods --namespace staging

  # 프로덕션 배포
  deploy-production:
    runs-on: ubuntu-latest
    needs: [build-images, security-scan]
    if: github.event_name == 'release'
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v1
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG_PROD }}
    
    - name: Deploy to production
      run: |
        helm upgrade --install stock-analysis-prod ./helm/stock-analysis \
          --namespace production \
          --set image.tag=${{ needs.build-images.outputs.image-tag }} \
          --set environment=production \
          --wait \
          --timeout=15m
    
    - name: Verify deployment
      run: |
        kubectl rollout status deployment/stock-analysis-prod --namespace production
        kubectl get pods --namespace production
    
    - name: Run smoke tests
      run: |
        ./scripts/smoke-tests.sh production
```

### 4.2 Helm 차트 구조
```yaml
# helm/stock-analysis/Chart.yaml
apiVersion: v2
name: stock-analysis
description: Stock Analysis Application Helm Chart
type: application
version: 1.0.0
appVersion: "1.0.0"

dependencies:
  - name: postgresql
    version: 12.x.x
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: 17.x.x
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled

# helm/stock-analysis/values.yaml
global:
  imageRegistry: ghcr.io
  imagePullSecrets:
    - name: regcred
  storageClass: fast-ssd

image:
  registry: ghcr.io
  repository: stock-analysis/stock-service
  tag: latest
  pullPolicy: IfNotPresent

replicaCount: 3

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

service:
  type: ClusterIP
  port: 8001

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: api.stockanalysis.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: stockanalysis-tls
      hosts:
        - api.stockanalysis.com

postgresql:
  enabled: true
  auth:
    postgresPassword: ""
    existingSecret: database-secret
  primary:
    persistence:
      enabled: true
      size: 100Gi
      storageClass: fast-ssd

redis:
  enabled: true
  auth:
    existingSecret: redis-secret
  master:
      persistence:
        enabled: true
        size: 10Gi
        storageClass: fast-ssd

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    namespace: monitoring
    labels:
      release: prometheus-operator
```

## 5. 모니터링 및 로깅

### 5.1 Prometheus 모니터링 구성
```yaml
# k8s/monitoring/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - "/etc/prometheus/rules/*.yml"
    
    scrape_configs:
    - job_name: 'stock-service'
      kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names:
          - stock-analysis
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_name]
        action: keep
        regex: stock-service
      - source_labels: [__meta_kubernetes_endpoint_port_name]
        action: keep
        regex: http
      - target_label: __address__
        replacement: kubernetes.default.svc:9090
    
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - stock-analysis
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
    
    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: monitoring
data:
  stock-service.yml: |
    groups:
    - name: stock-service
      rules:
      - alert: StockServiceDown
        expr: up{job="stock-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Stock service is down"
          description: "Stock service has been down for more than 1 minute."
      
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second."
      
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds."
      
      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Cannot connect to the database."
      
      - alert: RedisConnectionFailure
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failure"
          description: "Cannot connect to Redis."
```

### 5.2 Grafana 대시보드
```json
{
  "dashboard": {
    "id": null,
    "title": "Stock Analysis Monitoring",
    "tags": ["stock-analysis", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "yAxes": [
          {
            "label": "Requests/sec"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "99th percentile"
          }
        ],
        "yAxes": [
          {
            "label": "Seconds"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"4..\"}[5m])",
            "legendFormat": "4xx errors"
          },
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ],
        "yAxes": [
          {
            "label": "Errors/sec"
          }
        ]
      },
      {
        "id": 4,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total[5m])",
            "legendFormat": "{{pod}}"
          }
        ],
        "yAxes": [
          {
            "label": "CPU Cores"
          }
        ]
      },
      {
        "id": 5,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage_bytes / 1024 / 1024",
            "legendFormat": "{{pod}}"
          }
        ],
        "yAxes": [
          {
            "label": "MB"
          }
        ]
      },
      {
        "id": 6,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "{{datname}}"
          }
        ],
        "yAxes": [
          {
            "label": "Connections"
          }
        ]
      },
      {
        "id": 7,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)",
            "legendFormat": "Hit Rate"
          }
        ],
        "yAxes": [
          {
            "label": "Percentage",
            "min": 0,
            "max": 1
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### 5.3 ELK 스택 로깅
```yaml
# k8s/logging/elasticsearch.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: logging
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        ports:
        - containerPort: 9200
          name: rest
        - containerPort: 9300
          name: inter-node
        env:
        - name: cluster.name
          value: "stock-analysis-logs"
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "elasticsearch-0.elasticsearch,elasticsearch-1.elasticsearch,elasticsearch-2.elasticsearch"
        - name: cluster.initial_master_nodes
          value: "2"
        - name: ES_JAVA_OPTS
          value: "-Xms1g -Xmx1g"
        - name: xpack.security.enabled
          value: "false"
        - name: xpack.monitoring.collection.enabled
          value: "false"
        resources:
          requests:
            memory: 2Gi
            cpu: 1000m
          limits:
            memory: 4Gi
            cpu: 2000m
        volumeMounts:
        - name: elasticsearch-data
          mountPath: /usr/share/elasticsearch/data
  volumeClaimTemplates:
  - metadata:
      name: elasticsearch-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi

---
# k8s/logging/logstash.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logstash
  namespace: logging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: logstash
  template:
    metadata:
      labels:
        app: logstash
    spec:
      containers:
      - name: logstash
        image: docker.elastic.co/logstash/logstash:8.5.0
        ports:
        - containerPort: 5044
          name: beats
        - containerPort: 9600
          name: http
        env:
        - name: LS_JAVA_OPTS
          value: "-Xmx1g -Xms1g"
        resources:
          requests:
            memory: 1Gi
            cpu: 500m
          limits:
            memory: 2Gi
            cpu: 1000m
        volumeMounts:
        - name: logstash-config
          mountPath: /usr/share/logstash/pipeline
        - name: logstash-logs
          mountPath: /var/log/logstash
      volumes:
      - name: logstash-config
        configMap:
          name: logstash-config
      - name: logstash-logs
        emptyDir: {}

---
# k8s/logging/kibana.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kibana
  namespace: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kibana
  template:
    metadata:
      labels:
        app: kibana
    spec:
      containers:
      - name: kibana
        image: docker.elastic.co/kibana/kibana:8.5.0
        ports:
        - containerPort: 5601
        env:
        - name: ELASTICSEARCH_HOSTS
          value: "http://elasticsearch:9200"
        resources:
          requests:
            memory: 1Gi
            cpu: 500m
          limits:
            memory: 2Gi
            cpu: 1000m
```

## 6. 재해 복구 및 백업 전략

### 6.1 데이터베이스 백업 전략
```bash
#!/bin/bash
# scripts/backup-database.sh

set -e

# 설정
BACKUP_DIR="/backups/timescaledb"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="stockdb_backup_${TIMESTAMP}.sql"
S3_BUCKET="stock-analysis-backups"
RETENTION_DAYS=30

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# TimescaleDB 백업
echo "Starting TimescaleDB backup..."
kubectl exec -n stock-analysis timescaledb-0 -- pg_dump \
  --username=$POSTGRES_USER \
  --dbname=$POSTGRES_DB \
  --no-password \
  --verbose \
  --clean \
  --if-exists \
  --format=custom \
  --file=$BACKUP_DIR/$BACKUP_FILE

# 압축
echo "Compressing backup..."
gzip $BACKUP_DIR/$BACKUP_FILE

# S3에 업로드
echo "Uploading to S3..."
aws s3 cp $BACKUP_DIR/${BACKUP_FILE}.gz s3://$S3_BUCKET/database/

# 백업 검증
echo "Verifying backup..."
if [ $? -eq 0 ]; then
    echo "Backup successful: ${BACKUP_FILE}.gz"
    
    # 백업 메타데이터 저장
    echo "{
      \"timestamp\": \"$(date -Iseconds)\",
      \"filename\": \"${BACKUP_FILE}.gz\",
      \"size\": \"$(stat -f%z $BACKUP_DIR/${BACKUP_FILE}.gz)\",
      \"checksum\": \"$(sha256sum $BACKUP_DIR/${BACKUP_FILE}.gz | cut -d' ' -f1)\"
    }" > $BACKUP_DIR/${BACKUP_FILE}.json
    
    aws s3 cp $BACKUP_DIR/${BACKUP_FILE}.json s3://$S3_BUCKET/database/
else
    echo "Backup failed!"
    exit 1
fi

# 오래된 백업 정리
echo "Cleaning old backups..."
aws s3 ls s3://$S3_BUCKET/database/ | while read -r line; do
    createDate=$(echo $line | awk '{print $1" "$2}')
    createDate=$(date -d"$createDate" +%s)
    olderThan=$(date -d "$RETENTION_DAYS days ago" +%s)
    if [[ $createDate -lt $olderThan ]]; then
        fileName=$(echo $line | awk '{print $4}')
        if [[ $fileName != "" ]]; then
            aws s3 rm s3://$S3_BUCKET/database/$fileName
        fi
    fi
done

echo "Backup completed successfully!"
```

### 6.2 재해 복구 절차
```bash
#!/bin/bash
# scripts/disaster-recovery.sh

set -e

# 설정
BACKUP_BUCKET="stock-analysis-backups"
NAMESPACE="stock-analysis"
RECOVERY_TIMESTAMP=${1:-"latest"}

echo "Starting disaster recovery process..."

# 1. 현재 상태 백업
echo "Backing up current state..."
kubectl get all -n $NAMESPACE -o yaml > /tmp/current-state-backup.yaml

# 2. 네임스페이스 스케일링
echo "Scaling down deployments..."
kubectl scale deployment stock-service --replicas=0 -n $NAMESPACE
kubectl scale deployment sentiment-service --replicas=0 -n $NAMESPACE
kubectl scale deployment api-gateway --replicas=0 -n $NAMESPACE

# 3. 데이터베이스 복구
echo "Restoring database..."
LATEST_BACKUP=$(aws s3 ls s3://$BACKUP_BUCKET/database/ --recursive | sort | tail -n 1 | awk '{print $4}')
BACKUP_FILE=$(basename $LATEST_BACKUP .gz)

# 백업 다운로드
aws s3 cp s3://$BACKUP_BUCKET/database/$BACKUP_FILE.gz /tmp/
aws s3 cp s3://$BACKUP_BUCKET/database/${BACKUP_FILE}.json /tmp/

# 압축 해제
gunzip /tmp/$BACKUP_FILE.gz

# 데이터베이스 복구
kubectl exec -n $NAMESPACE timescaledb-0 -- psql \
  --username=$POSTGRES_USER \
  --dbname=$POSTGRES_DB \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  
kubectl exec -i -n $NAMESPACE timescaledb-0 -- psql \
  --username=$POSTGRES_USER \
  --dbname=$POSTGRES_DB \
  < /tmp/$BACKUP_FILE

# 4. Redis 데이터 복구
echo "Restoring Redis data..."
REDIS_BACKUP=$(aws s3 ls s3://$BACKUP_BUCKET/redis/ --recursive | sort | tail -n 1 | awk '{print $4}')

if [ ! -z "$REDIS_BACKUP" ]; then
    aws s3 cp s3://$BACKUP_BUCKET/redis/$REDIS_BACKUP /tmp/
    kubectl exec -i -n $NAMESPACE redis-0 -- redis-cli --pipe < /tmp/$REDIS_BACKUP
fi

# 5. 애플리케이션 재시작
echo "Restarting applications..."
kubectl scale deployment stock-service --replicas=3 -n $NAMESPACE
kubectl scale deployment sentiment-service --replicas=3 -n $NAMESPACE
kubectl scale deployment api-gateway --replicas=2 -n $NAMESPACE

# 6. 상태 확인
echo "Checking deployment status..."
kubectl rollout status deployment/stock-service -n $NAMESPACE
kubectl rollout status deployment/sentiment-service -n $NAMESPACE
kubectl rollout status deployment/api-gateway -n $NAMESPACE

# 7. 헬스 체크
echo "Running health checks..."
sleep 30

# API Gateway 헬스 체크
GATEWAY_URL="https://api.stockanalysis.com/health"
for i in {1..10}; do
    if curl -f $GATEWAY_URL > /dev/null 2>&1; then
        echo "API Gateway is healthy"
        break
    else
        echo "Waiting for API Gateway to be healthy... ($i/10)"
        sleep 10
    fi
done

# 서비스 헬스 체크
SERVICES=("stock-service" "sentiment-service")
for service in "${SERVICES[@]}"; do
    for i in {1..10}; do
        if kubectl exec -n $NAMESPACE $service-0 -- curl -f http://localhost:8001/health > /dev/null 2>&1; then
            echo "$service is healthy"
            break
        else
            echo "Waiting for $service to be healthy... ($i/10)"
            sleep 10
        fi
    done
done

# 8. 재해 복구 보고서 생성
echo "Generating recovery report..."
REPORT_FILE="/tmp/disaster-recovery-$(date +%Y%m%d_%H%M%S).json"

cat > $REPORT_FILE << EOF
{
  "recovery_timestamp": "$(date -Iseconds)",
  "backup_used": "$LATEST_BACKUP",
  "backup_timestamp": "$(cat /tmp/${BACKUP_FILE}.json | jq -r '.timestamp')",
  "services_restarted": ["stock-service", "sentiment-service", "api-gateway"],
  "health_checks": {
    "api_gateway": "$(curl -s -o /dev/null -w "%{http_code}" $GATEWAY_URL)",
    "stock_service": "$(kubectl exec -n $NAMESPACE stock-service-0 -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)",
    "sentiment_service": "$(kubectl exec -n $NAMESPACE sentiment-service-0 -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health)"
  },
  "recovery_status": "completed"
}
EOF

# 보고서 S3에 업로드
aws s3 cp $REPORT_FILE s3://$BACKUP_BUCKET/reports/

echo "Disaster recovery completed successfully!"
echo "Recovery report: $REPORT_FILE"
```

### 6.3 카나리 배포 전략
```yaml
# k8s/canary-deployment.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: stock-service-canary
  namespace: stock-analysis
spec:
  replicas: 5
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {duration: 10m}
      - setWeight: 40
      - pause: {duration: 10m}
      - setWeight: 60
      - pause: {duration: 10m}
      - setWeight: 80
      - pause: {duration: 10m}
      - setWeight: 100
      pause: {duration: 10m}
      canaryService: stock-service-canary
      stableService: stock-service-stable
      trafficRouting:
        managedRoutes:
        - primary: stable
          canary: canary
          references:
          - kind: Service
            name: stock-service-stable
            port: 80
          - kind: Service
            name: stock-service-canary
            port: 80
      analysis:
        templates:
        - templateName: success-rate
          args:
          - name: service-name
            value: stock-service-canary
        - templateName: latency
          args:
          - name: service-name
            value: stock-service-canary
        - templateName: error-rate
          args:
          - name: service-name
            value: stock-service-canary
        args:
        - name: service-name
          value: stock-service-stable
      - args:
      - name: service-name
        value: stock-service-canary
  selector:
    matchLabels:
      app: stock-service
  template:
    metadata:
      labels:
        app: stock-service
        version: canary
    spec:
      containers:
      - name: stock-service
        image: stock-analysis/stock-service:canary
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: stock-service-canary
  namespace: stock-analysis
spec:
  selector:
    app: stock-service
    version: canary
  ports:
  - port: 8001
    targetPort: 8001
    name: http
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: stock-service-stable
  namespace: stock-analysis
spec:
  selector:
    app: stock-service
    version: stable
  ports:
  - port: 8001
    targetPort: 8001
    name: http
  type: ClusterIP
```

## 7. 결론

본 배포 및 운영 자동화 계획은 컨테이너화, Kubernetes 오케스트레이션, CI/CD 파이프라인, 모니터링, 재해 복구 등 다양한 운영 자동화 측면에서의 포괄적인 접근 방식을 제시합니다.

주요 특징:
1. **컨테이너화**: 다단계 Docker 빌드를 통한 최적화된 이미지
2. **Kubernetes 오케스트레이션**: 확장 가능한 컨테이너 관리
3. **CI/CD 파이프라인**: GitHub Actions를 통한 자동화된 빌드 및 배포
4. **Helm 차트**: 관리형 Kubernetes 배포
5. **모니터링**: Prometheus, Grafana를 통한 포괄적인 모니터링
6. **로깅**: ELK 스택을 통한 중앙화된 로그 관리
7. **재해 복구**: 자동화된 백업 및 복구 절차
8. **카나리 배포**: 안정적인 롤아웃 전략
9. **보안**: 컨테이너 보안 및 시크릿 관리
10. **성능 최적화**: HPA, 리소스 관리를 통한 자동 확장

이 배포 및 운영 자동화 시스템을 통해 안정적이고 신뢰성 있는 애플리케이션 운영이 가능하며, 빠른 배포와 효과적인 문제 대응을 통해 서비스 연속성을 보장할 수 있습니다.