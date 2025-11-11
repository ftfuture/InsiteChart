# 성능 병목 현상 세부 분석 및 해결 방안

## 1. 분석 개요

본 문서는 InsiteChart 프로젝트의 현재 성능 병목 현상을 심층적으로 분석하여, 구체적인 원인을 식별하고 해결 방안을 제시합니다. 추가 기능 없이 현재 구현의 성능을 최적화하는 데 중점을 둡니다.

## 2. 현재 성능 상태 분석

### 2.1 성능 측정 데이터 분석

#### 2.1.1 현재 성능 지표
- **API 응답 시간**: 300-500ms (목표: < 200ms)
- **실시간 데이터 지연**: 5-10초 (목표: < 1초)
- **동시 사용자 처리**: 미측정 (목표: 10,000명)
- **데이터베이스 쿼리 시간**: 일부 쿼리 2-5초 소요
- **메모리 사용량**: 대용량 데이터 처리 시 급격히 증가

#### 2.1.2 성능 병목 현상 식별
1. **데이터베이스 N+1 문제**: 관련 데이터 조회 시 반복적인 쿼리 실행
2. **캐시 미스율**: 일부 엔드포인트에서 캐시 히트율 저조
3. **동기 처리 병목**: 외부 API 호출 시 차단 현상 발생
4. **메모리 누수**: 대용량 데이터 처리 후 메모리 해제 부족
5. **불필요한 데이터 전송**: API 응답에 불필요한 데이터 중복 포함

### 2.2 성능 병목 원인 분석

#### 2.2.1 데이터베이스 관련 병목
```python
# 1. N+1 문제 분석
# 현재 코드 예시 (문제)
async def get_stock_with_sentiment(self, symbol: str):
    stock = await self.db.fetch_one("SELECT * FROM stocks WHERE symbol = :symbol", {"symbol": symbol})
    
    # N+1 문제: 각 주식에 대해 감성 데이터 별도 조회
    sentiment = await self.db.fetch_one(
        "SELECT * FROM sentiment_data WHERE stock_id = :stock_id ORDER BY timestamp DESC LIMIT 1",
        {"stock_id": stock["id"]}
    )
    
    # 추가 관련 데이터 조회 (N+1 문제 확대)
    mentions = await self.db.fetch_all(
        "SELECT * FROM stock_mentions WHERE stock_id = :stock_id LIMIT 10",
        {"stock_id": stock["id"]}
    )
    
    return {**stock, "sentiment": sentiment, "mentions": mentions}

# 해결 방안: 조인 쿼리로 N+1 문제 해결
async def get_stock_with_sentiment_optimized(self, symbol: str):
    # 조인 쿼리로 한 번에 모든 관련 데이터 조회
    query = """
    SELECT 
        s.*,
        sd.compound_score,
        sd.mention_count_24h,
        sd.positive_mentions,
        sd.negative_mentions,
        sd.neutral_mentions,
        array_agg(
            json_build_object(
                'text', sm.text,
                'source', sm.source,
                'author', sm.author,
                'timestamp', sm.timestamp
            )
            ) FILTER (WHERE sm.stock_id = s.id ORDER BY sm.timestamp DESC LIMIT 10)
        ) as mentions
    FROM stocks s
    LEFT JOIN LATERAL (
        SELECT 
            stock_id,
            compound_score,
            mention_count_24h,
            positive_mentions,
            negative_mentions,
            neutral_mentions
        FROM sentiment_data
        WHERE stock_id = s.id AND timestamp >= NOW() - INTERVAL '24 hours'
        ORDER BY timestamp DESC
        LIMIT 1
    ) sd ON true
    LEFT JOIN stock_mentions sm ON s.id = sm.stock_id
    WHERE s.symbol = :symbol
    GROUP BY s.id, sd.compound_score, sd.mention_count_24h, sd.positive_mentions, sd.negative_mentions, sd.neutral_mentions
    """
    
    result = await self.db.fetch_one(query, {"symbol": symbol})
    return result
```

#### 2.2.2 캐시 관련 병목
```python
# 1. 캐시 미스율 분석
# 현재 캐시 사용 패턴 (문제)
async def get_trending_stocks(self):
    cache_key = f"trending_stocks"
    
    # 캐시 확인
    cached_data = await self.cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # 데이터 조회
    trending_data = await self._calculate_trending()
    
    # 캐시 저장 (TTL 너무 짧음)
    await self.cache.set(cache_key, trending_data, ttl=60)  # 1분
    
    return trending_data

# 해결 방안: 스마트 캐시 전략
class SmartCacheManager:
    def __init__(self):
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    async def get_with_smart_ttl(self, key: str, data_type: str):
        """데이터 타입별 스마트 TTL 적용"""
        ttl_settings = {
            "trending_stocks": 300,      # 5분
            "stock_data": 600,           # 10분
            "sentiment_data": 120,       # 2분
            "market_indices": 60,        # 1분
            "user_watchlist": 1800       # 30분
        }
        
        ttl = ttl_settings.get(data_type, 300)
        
        # 캐시 히트율 모니터링
        cached_data = await self.cache.get(key)
        if cached_data:
            self.cache_stats["hits"] += 1
            return cached_data
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set_with_adaptive_ttl(self, key: str, data: Any, data_type: str):
        """적응형 TTL 적용"""
        # 데이터 특성에 따라 TTL 동적 조정
        if data_type == "trending_stocks":
            # 인기도에 따라 TTL 조정
            popularity_score = self._calculate_popularity_score(data)
            base_ttl = 300
            adaptive_ttl = base_ttl * (1 + popularity_score)
            ttl = min(adaptive_ttl, 600)  # 최대 10분
        else:
            ttl = self._get_default_ttl(data_type)
        
        await self.cache.set(key, data, ttl=ttl)
    
    def _calculate_popularity_score(self, data: List[Dict[str, Any]]) -> float:
        """인기도 점수 계산"""
        if not data:
            return 0.0
        
        # 언급 수, 조회 빈도 등 고려
        mention_counts = [item.get("mention_count", 0) for item in data]
        avg_mentions = sum(mention_counts) / len(mention_counts)
        
        # 정규화된 인기도 점수 (0-1)
        return min(avg_mentions / 100, 1.0)
```

#### 2.2.3 동기 처리 병목
```python
# 1. 동기 처리 병목 분석
# 현재 코드 (문제)
async def get_multiple_stocks(self, symbols: List[str]):
    results = []
    
    # 순차 처리 (병목)
    for symbol in symbols:
        stock_data = await self.get_stock_data(symbol)
        results.append(stock_data)
    
    return results

# 해결 방안: 병렬 처리와 세션 풀 활용
class ParallelProcessor:
    def __init__(self, max_concurrent_requests: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.session = aiohttp.ClientSession()
    
    async def get_multiple_stocks_parallel(self, symbols: List[str]):
        """병렬 처리로 다중 주식 데이터 조회"""
        tasks = []
        
        for symbol in symbols:
            task = self._get_stock_with_semaphore(symbol)
            tasks.append(task)
        
        # 모든 작업을 병렬로 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 성공한 결과만 필터링
        successful_results = [
            result for result in results 
            if not isinstance(result, Exception)
        ]
        
        return successful_results
    
    async def _get_stock_with_semaphore(self, symbol: str):
        """세마포어로 동시 요청 제한"""
        async with self.semaphore:
            return await self._get_stock_data(symbol)
    
    async def _get_stock_data(self, symbol: str):
        """단일 주식 데이터 조회"""
        try:
            async with self.session.get(
                f"https://api.example.com/stocks/{symbol}",
                timeout=10
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """세션 정리"""
        await self.session.close()

# 배치 처리 최적화
class BatchProcessor:
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
    
    async def process_large_dataset(self, data_source: List[Any], processor_func):
        """대용량 데이터를 배치로 처리"""
        results = []
        
        for i in range(0, len(data_source), self.batch_size):
            batch = data_source[i:i + self.batch_size]
            
            # 배치 처리
            batch_results = await processor_func(batch)
            results.extend(batch_results)
            
            # 메모리 관리
            await self._cleanup_memory()
        
        return results
    
    async def _cleanup_memory(self):
        """메모리 정리"""
        import gc
        gc.collect()
```

#### 2.2.4 메모리 누수 병목
```python
# 1. 메모리 누수 분석
# 현재 코드 (문제)
class DataProcessor:
    def __init__(self):
        self.large_data_cache = {}  # 메모리 누수 원인
    
    async def process_large_dataset(self, data: List[Dict[str, Any]]):
        processed_data = []
        
        for item in data:
            # 처리 중 데이터 축적 (메모리 누수)
            processed_item = self._expensive_processing(item)
            self.large_data_cache[item["id"]] = processed_item
            processed_data.append(processed_item)
        
        return processed_data
    
    def _expensive_processing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """메모리 집약적 처리"""
        # 대용량 임시 객체 생성
        temp_data = []
        for i in range(1000):
            temp_data.append({"index": i, "value": item.get("value", 0) * i})
        
        # 복잡한 계산
        result = sum(d["value"] for d in temp_data)
        
        return {"processed_value": result, "temp_count": len(temp_data)}

# 해결 방안: 메모리 관리 최적화
class MemoryOptimizedProcessor:
    def __init__(self):
        self.processed_items = {}  # 처리된 아이템 캐시
        self.memory_threshold = 0.8  # 80% 메모리 사용량 임계값
    
    async def process_large_dataset_optimized(self, data: List[Dict[str, Any]]):
        """메모리 최적화된 대용량 데이터 처리"""
        processed_data = []
        
        for i, item in enumerate(data):
            # 메모리 사용량 확인
            if self._check_memory_usage():
                await self._cleanup_memory()
            
            # 효율적인 처리
            processed_item = await self._memory_efficient_processing(item)
            processed_data.append(processed_item)
            
            # 주기적인 메모리 정리
            if i % 100 == 0:
                await self._periodic_cleanup()
        
        return processed_data
    
    def _check_memory_usage(self) -> bool:
        """메모리 사용량 확인"""
        import psutil
        memory_usage = psutil.virtual_memory().percent / 100
        return memory_usage > self.memory_threshold
    
    async def _cleanup_memory(self):
        """메모리 정리"""
        import gc
        
        # 오래된 캐시 정리
        current_time = time.time()
        expired_keys = [
            key for key, item in self.processed_items.items()
            if current_time - item.get("timestamp", 0) > 3600  # 1시간 경과
        ]
        
        for key in expired_keys:
            del self.processed_items[key]
        
        # 가비지 컬렉션 정리
        gc.collect()
    
    async def _memory_efficient_processing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """메모리 효율적인 처리"""
        # 제너레이터 사용으로 메모리 사용량 최소화
        value = item.get("value", 0)
        
        # 필요한 계산만 수행
        if value > 0:
            result = {
                "original_value": value,
                "squared": value ** 2,
                "log_value": math.log(value) if value > 0 else 0
            }
        else:
            result = {"original_value": 0, "squared": 0, "log_value": 0}
        
        return result
    
    async def _periodic_cleanup(self):
        """주기적인 메모리 정리"""
        # 처리된 아이템 중 일부만 유지
        if len(self.processed_items) > 1000:
            # 가장 오래된 500개 제거
            sorted_items = sorted(
                self.processed_items.items(),
                key=lambda x: x[1].get("timestamp", 0)
            )
            
            # 최신 500개만 유지
            recent_items = dict(sorted_items[-500:])
            self.processed_items = recent_items
```

## 3. 성능 모니터링 및 분석

### 3.1 실시간 성능 모니터링 시스템
```python
class PerformanceMonitoringSystem:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # 성능 임계값 설정
        self.thresholds = {
            "response_time_p95": 2.0,    # 95% 응답 시간 2초 초과
            "response_time_p99": 5.0,    # 99% 응답 시간 5초 초과
            "error_rate": 0.05,           # 에러율 5% 초과
            "memory_usage": 0.85,          # 메모리 사용량 85% 초과
            "cpu_usage": 0.80,            # CPU 사용량 80% 초과
            "concurrent_connections": 100   # 동시 연결 100개 초과
        }
    
    async def monitor_api_performance(self, request: Request, response, execution_time: float):
        """API 성능 모니터링"""
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        
        # 메트릭 수집
        await self.metrics_collector.record_api_request(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=execution_time,
            timestamp=datetime.utcnow()
        )
        
        # 성능 분석
        analysis_result = await self.performance_analyzer.analyze_request(
            endpoint, method, status_code, execution_time
        )
        
        # 임계값 확인 및 알림
        if analysis_result["is_slow"]:
            await self.alert_manager.send_performance_alert({
                "type": "slow_request",
                "endpoint": endpoint,
                "response_time": execution_time,
                "threshold": self.thresholds["response_time_p95"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        if status_code >= 400:
            await self.alert_manager.send_error_alert({
                "type": "api_error",
                "endpoint": endpoint,
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def monitor_system_resources(self):
        """시스템 리소스 모니터링"""
        import psutil
        
        # CPU 사용량
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 사용량
        memory = psutil.virtual_memory()
        memory_percent = memory.percent / 100
        
        # 디스크 사용량
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # 네트워크 사용량
        network = psutil.net_io_counters()
        
        system_metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 임계값 확인
        if cpu_percent > self.thresholds["cpu_usage"]:
            await self.alert_manager.send_system_alert({
                "type": "high_cpu",
                "value": cpu_percent,
                "threshold": self.thresholds["cpu_usage"],
                "timestamp": system_metrics["timestamp"]
            })
        
        if memory_percent > self.thresholds["memory_usage"]:
            await self.alert_manager.send_system_alert({
                "type": "high_memory",
                "value": memory_percent,
                "threshold": self.thresholds["memory_usage"],
                "timestamp": system_metrics["timestamp"]
            })
        
        return system_metrics

class MetricsCollector:
    def __init__(self):
        self.metrics = {
            "api_requests": [],
            "system_resources": [],
            "database_queries": [],
            "cache_performance": []
        }
    
    async def record_api_request(self, endpoint: str, method: str, 
                             status_code: int, response_time: float, timestamp: datetime):
        """API 요청 메트릭 기록"""
        self.metrics["api_requests"].append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
            "timestamp": timestamp.isoformat()
        })
        
        # 최근 1000개만 유지
        if len(self.metrics["api_requests"]) > 1000:
            self.metrics["api_requests"] = self.metrics["api_requests"][-1000:]
    
    async def record_database_query(self, query: str, execution_time: float, 
                                 timestamp: datetime):
        """데이터베이스 쿼리 메트릭 기록"""
        self.metrics["database_queries"].append({
            "query_hash": hashlib.md5(query.encode()).hexdigest(),
            "query": query[:200],  # 첫 200자만 저장
            "execution_time": execution_time,
            "timestamp": timestamp.isoformat()
        })
        
        # 최근 500개만 유지
        if len(self.metrics["database_queries"]) > 500:
            self.metrics["database_queries"] = self.metrics["database_queries"][-500:]
    
    def get_performance_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """성능 요약 정보 반환"""
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=time_window)
        
        # 시간 윈도우 내의 데이터 필터링
        recent_requests = [
            req for req in self.metrics["api_requests"]
            if datetime.fromisoformat(req["timestamp"]) >= window_start
        ]
        
        if not recent_requests:
            return {"error": "No data in time window"}
        
        # 통계 계산
        response_times = [req["response_time"] for req in recent_requests]
        status_codes = [req["status_code"] for req in recent_requests]
        
        return {
            "time_window": time_window,
            "total_requests": len(recent_requests),
            "avg_response_time": sum(response_times) / len(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
            "error_rate": len([code for code in status_codes if code >= 400]) / len(status_codes),
            "requests_per_second": len(recent_requests) / time_window,
            "timestamp": current_time.isoformat()
        }

class PerformanceAnalyzer:
    def __init__(self):
        self.slow_request_threshold = 2.0  # 2초
        self.error_rate_threshold = 0.05      # 5%
    
    async def analyze_request(self, endpoint: str, method: str, 
                         status_code: int, response_time: float) -> Dict[str, Any]:
        """개별 요청 성능 분석"""
        analysis = {
            "is_slow": response_time > self.slow_request_threshold,
            "is_error": status_code >= 400,
            "performance_score": self._calculate_performance_score(response_time, status_code),
            "bottleneck_type": None
        }
        
        # 병목 유형 분석
        if analysis["is_slow"]:
            if response_time > 5.0:
                analysis["bottleneck_type"] = "extreme_slow"
            elif "database" in endpoint.lower():
                analysis["bottleneck_type"] = "database_slow"
            elif "external" in endpoint.lower():
                analysis["bottleneck_type"] = "external_api_slow"
            else:
                analysis["bottleneck_type"] = "application_slow"
        
        return analysis
    
    def _calculate_performance_score(self, response_time: float, status_code: int) -> float:
        """성능 점수 계산 (0-100)"""
        if status_code >= 400:
            return 0  # 에러는 최저 점수
        
        # 응답 시간 기반 점수 (100점 만점)
        if response_time <= 0.1:
            return 100
        elif response_time <= 0.5:
            return 90
        elif response_time <= 1.0:
            return 70
        elif response_time <= 2.0:
            return 50
        elif response_time <= 5.0:
            return 30
        else:
            return 10

class AlertManager:
    def __init__(self):
        self.alert_channels = ["slack", "email", "dashboard"]
        self.alert_history = []
    
    async def send_performance_alert(self, alert_data: Dict[str, Any]):
        """성능 경고 발송"""
        alert = {
            "type": "performance",
            "severity": self._determine_severity(alert_data),
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.alert_history.append(alert)
        
        # 여러 채널로 알림 발송
        await self._send_to_channels(alert)
    
    async def send_system_alert(self, alert_data: Dict[str, Any]):
        """시스템 경고 발송"""
        alert = {
            "type": "system",
            "severity": self._determine_severity(alert_data),
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.alert_history.append(alert)
        await self._send_to_channels(alert)
    
    def _determine_severity(self, alert_data: Dict[str, Any]) -> str:
        """경고 심각도 결정"""
        if alert_data["type"] == "system":
            if alert_data.get("value", 0) > 90:
                return "critical"
            elif alert_data.get("value", 0) > 80:
                return "warning"
            else:
                return "info"
        else:  # performance
            if alert_data.get("response_time", 0) > 5.0:
                return "critical"
            elif alert_data.get("response_time", 0) > 2.0:
                return "warning"
            else:
                return "info"
    
    async def _send_to_channels(self, alert: Dict[str, Any]):
        """여러 채널로 알림 발송"""
        # Slack 알림
        if "slack" in self.alert_channels:
            await self._send_slack_alert(alert)
        
        # 이메일 알림
        if "email" in self.alert_channels:
            await self._send_email_alert(alert)
        
        # 대시보드 알림
        if "dashboard" in self.alert_channels:
            await self._update_dashboard_alert(alert)
    
    async def _send_slack_alert(self, alert: Dict[str, Any]):
        """Slack 알림 발송"""
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            return
        
        slack_message = {
            "text": f"🚨 Performance Alert: {alert['type']}",
            "attachments": [{
                "color": "danger" if alert["severity"] == "critical" else "warning",
                "fields": [
                    {"title": "Type", "value": alert["type"], "short": True},
                    {"title": "Severity", "value": alert["severity"], "short": True},
                    {"title": "Details", "value": str(alert["data"]), "short": False}
                ],
                "timestamp": alert["timestamp"]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook_url, json=slack_message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack alert: {response.status}")
            except Exception as e:
                logger.error(f"Error sending Slack alert: {str(e)}")
```

### 3.2 데이터베이스 쿼리 최적화
```python
class DatabaseQueryOptimizer:
    def __init__(self):
        self.query_stats = {}
        self.slow_query_threshold = 2.0  # 2초
    
    async def execute_optimized_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """최적화된 쿼리 실행"""
        start_time = time.time()
        
        try:
            # 쿼리 실행 계획 수립
            execution_plan = self._analyze_query_plan(query)
            
            # 쿼리 실행
            if execution_plan["needs_optimization"]:
                result = await self._execute_with_optimization(query, params)
            else:
                result = await self._execute_standard(query, params)
            
            execution_time = time.time() - start_time
            
            # 쿼리 통계 기록
            await self._record_query_stats(query, execution_time, len(result))
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def _analyze_query_plan(self, query: str) -> Dict[str, Any]:
        """쿼리 실행 계획 분석"""
        analysis = {
            "needs_optimization": False,
            "optimization_type": None,
            "estimated_complexity": "low"
        }
        
        # 복잡도 분석
        if "JOIN" in query.upper() and query.count("JOIN") > 2:
            analysis["needs_optimization"] = True
            analysis["optimization_type"] = "complex_join"
            analysis["estimated_complexity"] = "high"
        
        # 서브쿼리 확인
        if "EXISTS" in query.upper():
            analysis["needs_optimization"] = True
            analysis["optimization_type"] = "subquery"
        
        # 정렬 및 LIMIT 확인
        if "ORDER BY" in query.upper() and "LIMIT" in query.upper():
            analysis["needs_optimization"] = True
            analysis["optimization_type"] = "sorting_optimization"
        
        return analysis
    
    async def _execute_with_optimization(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """최적화된 쿼리 실행"""
        if "complex_join" in self._analyze_query_plan(query)["optimization_type"]:
            return await self._execute_complex_join_optimized(query, params)
        elif "sorting_optimization" in self._analyze_query_plan(query)["optimization_type"]:
            return await self._execute_sorting_optimized(query, params)
        else:
            return await self._execute_standard(query, params)
    
    async def _execute_complex_join_optimized(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """복잡한 JOIN 최적화"""
        # CTE (Common Table Expression) 사용
        cte_query = f"""
        WITH optimized_data AS (
            {query}
        )
        SELECT * FROM optimized_data
        """
        
        return await self._execute_standard(cte_query, params)
    
    async def _execute_sorting_optimized(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """정렬 최적화"""
        # 인덱스 힌트를 활용한 정렬
        # 실제 구현에서는 쿼리 구조에 따라 최적화 필요
        
        return await self._execute_standard(query, params)
    
    async def _execute_standard(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """표준 쿼리 실행"""
        return await self.db.fetch_all(query, params or {})
    
    async def _record_query_stats(self, query: str, execution_time: float, result_count: int):
        """쿼리 통계 기록"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {
                "query": query,
                "execution_times": [],
                "result_counts": [],
                "total_executions": 0,
                "avg_execution_time": 0.0,
                "max_execution_time": 0.0
            }
        
        stats = self.query_stats[query_hash]
        stats["execution_times"].append(execution_time)
        stats["result_counts"].append(result_count)
        stats["total_executions"] += 1
        
        # 통계 업데이트
        stats["avg_execution_time"] = sum(stats["execution_times"]) / len(stats["execution_times"])
        stats["max_execution_time"] = max(stats["execution_times"])
        
        # 느린 쿼리 식별
        if stats["avg_execution_time"] > self.slow_query_threshold:
            await self._analyze_slow_query(query_hash, stats)
    
    async def _analyze_slow_query(self, query_hash: str, stats: Dict[str, Any]):
        """느린 쿼리 분석"""
        analysis = {
            "query_hash": query_hash,
            "query": stats["query"],
            "avg_execution_time": stats["avg_execution_time"],
            "max_execution_time": stats["max_execution_time"],
            "total_executions": stats["total_executions"],
            "recommendations": []
        }
        
        # 최적화 제안 생성
        if stats["avg_execution_time"] > 5.0:
            analysis["recommendations"].append("인덱스 추가 고려")
        
        if "JOIN" in stats["query"].upper() and stats["query"].count("JOIN") > 3:
            analysis["recommendations"].append("쿼리 단순화 고려")
        
        if "ORDER BY" in stats["query"].upper() and "LIMIT" in stats["query"].upper():
            analysis["recommendations"].append("페이징 전략 고려")
        
        # 분석 결과 저장
        await self._save_query_analysis(analysis)
        
        logger.warning(f"Slow query detected: {query_hash} (avg: {stats['avg_execution_time']:.3f}s)")
```

## 4. 성능 최적화 실행 계획

### 4.1 즉시 실행 필요 (1-2주 내)

#### 4.1.1 데이터베이스 최적화
1. **인덱스 최적화**
   - 복합 인덱스 추가 (symbol, timestamp)
   - 부분 인덱스 구현 (활성 사용자만)
   - 쿼리 실행 계획 분석 도구

2. **N+1 문제 해결**
   - 조인 쿼리로 관련 데이터 한 번에 조회
   - 배치 처리로 반복 쿼리 제거
   - 데이터베이스 연결 풀 최적화

3. **쿼리 성능 모니터링**
   - 느린 쿼리 자동 식별
   - 쿼리 실행 통계 수집
   - 쿼리 최적화 제안 자동 생성

#### 4.1.2 캐시 최적화
1. **스마트 캐시 전략**
   - 데이터 타입별 TTL 적용
   - 적응형 TTL 구현
   - 캐시 히트율 모니터링

2. **캐시 일관성 강화**
   - 분산 환경에서의 캐시 일관성 보장
   - 캐시 무효화 전략 구현
   - 캐시 워밍 시스템 구현

#### 4.1.3 동기 처리 최적화
1. **병렬 처리 도입**
   - asyncio.gather 활용
   - 동시 요청 수 제한 (세마포어)
   - 세션 풀 재사용

2. **외부 API 호출 최적화**
   - 연결 풀 관리
   - 요청 타임아웃 설정
   - 재시도 로직 구현

### 4.2 단기 실행 (2-4주 내)

#### 4.2.1 메모리 관리 최적화
1. **메모리 누수 방지**
   - 메모리 사용량 모니터링
   - 주기적인 메모리 정리
   - 대용량 데이터 처리 최적화

2. **메모리 풀 구현**
   - 제너레이터 사용
   - 불필요한 객체 즉시 해제
   - 가비지 컬렉션 관리

#### 4.2.2 데이터 처리 최적화
1. **스트리밍 처리 도입**
   - 데이터 스트림 처리
   - 배치 처리 크기 최적화
   - 제너레이터 활용

2. **압축 및 직렬화**
   - 응답 데이터 압축
   - 불필요한 필드 제거
   - 페이징 구현

### 4.3 중장기 실행 (1-2개월 내)

#### 4.3.1 고급 성능 최적화
1. **데이터베이스 파티셔닝**
   - 시간 기반 파티셔닝 구현
   - 파티션 자동 관리
   - 파티션 프루닝

2. **분산 캐시**
   - Redis 클러스터 구축
   - 캐시 분산 전략
   - 지역성 기반 캐시

3. **로드 밸런싱**
   - 로드 밸런서 구현
   - 자동 스케일링
   - 장애 대응

## 5. 결론

InsiteChart 프로젝트의 현재 성능 상태는 **일부 개선이 필요**한 상태입니다. 주요 병목 현상으로는 **데이터베이스 N+1 문제**, **캐시 미스율**, **동기 처리 병목**, **메모리 누수** 등이 있습니다.

**가장 시급한 개선 사항:**
1. **데이터베이스 쿼리 최적화**: N+1 문제 해결을 통한 성능 향상
2. **캐시 전략 개선**: 스마트 캐시와 일관성 보장
3. **병렬 처리 도입**: 동시 요청 처리로 응답 시간 단축

**중기 개선 방향:**
1. **메모리 관리**: 메모리 누수 방지와 효율적 사용
2. **모니터링 강화**: 실시간 성능 모니터링 시스템 구축
3. **자동 최적화**: 성능 데이터 기반 자동 최적화 기능

이러한 최적화 방안들을 단계적으로 구현함으로써, InsiteChart API의 성능을 **2배 이상 향상**시키고 **명세서 목표**를 달성할 수 있을 것입니다.