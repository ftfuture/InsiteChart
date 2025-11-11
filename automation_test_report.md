# InsiteChart 자동화 기능 테스트 보고서
생성 시간: 2025-11-07T12:28:06.931046+00:00
총 테스트: 29
통과 테스트: 26
실패 테스트: 3
성공률: 89.7%
전체 성공: 성공

## 상세 테스트 결과:
- jwt_token_generation: ✅ 통과
  JWT token generated successfully
  시간: 2025-11-07T12:28:06.960562

- jwt_token_verification: ✅ 통과
  JWT token verified successfully
  시간: 2025-11-07T12:28:06.962250

- jwt_token_refresh: ✅ 통과
  JWT token refresh successful
  시간: 2025-11-07T12:28:06.964439

- api_key_generation: ✅ 통과
  API key generated successfully
  시간: 2025-11-07T12:28:06.969652

- api_key_verification: ❌ 실패
  API key verification failed: No API key provided
  시간: 2025-11-07T12:28:06.971480

- api_key_usage_tracking: ✅ 통과
  API key usage tracking working
  시간: 2025-11-07T12:28:06.972893

- api_key_deletion: ✅ 통과
  API key deletion successful
  시간: 2025-11-07T12:28:06.974799

- rate_limiting_basic: ❌ 실패
  No rate limiting detected
  시간: 2025-11-07T12:28:06.991049

- rate_limiting_dynamic: ✅ 통과
  Dynamic rate limiting: 20/20 successful
  시간: 2025-11-07T12:28:09.008450

- security_headers: ✅ 통과
  All security headers properly configured
  시간: 2025-11-07T12:28:09.013420

- csp_header: ✅ 통과
  CSP header properly configured
  시간: 2025-11-07T12:28:09.013492

- external_api_integration: ✅ 통과
  External API integration working
  시간: 2025-11-07T12:28:09.015303

- external_api_caching: ❌ 실패
  External API caching not working properly
  시간: 2025-11-07T12:28:09.019162

- kafka_event_publishing: ✅ 통과
  Kafka event publishing successful
  시간: 2025-11-07T12:28:09.023068

- kafka_event_subscription: ✅ 통과
  Kafka event subscription successful
  시간: 2025-11-07T12:28:09.027920

- realtime_collection_status: ✅ 통과
  Realtime collection is running
  시간: 2025-11-07T12:28:09.029579

- realtime_collection_stats: ✅ 통과
  Total collections: 991
  시간: 2025-11-07T12:28:09.029630

- realtime_collection_trigger: ✅ 통과
  Realtime collection trigger successful
  시간: 2025-11-07T12:28:09.031206

- caching_performance: ✅ 통과
  Cache hit rate: 100.0%
  시간: 2025-11-07T12:28:09.039083

- intelligent_cache_warming: ✅ 통과
  Intelligent cache warming is active
  시간: 2025-11-07T12:28:09.042451

- distributed_caching: ✅ 통과
  Distributed caching active with 3 nodes
  시간: 2025-11-07T12:28:09.043990

- monitoring_dashboard: ✅ 통과
  Monitoring dashboard has 4 widgets
  시간: 2025-11-07T12:28:09.045122

- monitoring_alerts: ✅ 통과
  Found 1 alerts
  시간: 2025-11-07T12:28:09.045154

- performance_metrics_cpu: ✅ 통과
  CPU usage: 52.39%
  시간: 2025-11-07T12:28:09.046123

- performance_metrics_memory: ✅ 통과
  Memory usage: 47.2%
  시간: 2025-11-07T12:28:09.046170

- structured_logging: ✅ 통과
  Structured logging is active
  시간: 2025-11-07T12:28:09.047710

- log_level: ✅ 통과
  Log level: INFO
  시간: 2025-11-07T12:28:09.047763

- log_creation: ✅ 통과
  Log creation successful
  시간: 2025-11-07T12:28:09.052025

- log_retrieval: ✅ 통과
  Retrieved 10 logs
  시간: 2025-11-07T12:28:09.055001
