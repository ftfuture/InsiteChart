"""
pytest 공통 픽스처 및 설정
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import tempfile
import shutil

# pytest-asyncio 설정
pytest_plugins = ('pytest_asyncio',)

# 백엔드 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 픽스처"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """임시 디렉토리 픽스처"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_redis():
    """Redis 모의 객체 픽스처"""
    redis_mock = Mock()
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.delete_pattern = AsyncMock(return_value=0)
    redis_mock.exists = AsyncMock(return_value=False)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_database():
    """데이터베이스 모의 객체 픽스처"""
    db_mock = Mock()
    db_mock.execute = AsyncMock()
    db_mock.fetchall = AsyncMock(return_value=[])
    db_mock.fetchone = AsyncMock(return_value=None)
    db_mock.commit = Mock()
    db_mock.rollback = Mock()
    return db_mock


@pytest.fixture
def mock_external_apis():
    """외부 API 모의 객체 픽스처"""
    apis = {
        'yahoo_finance': Mock(),
        'reddit': Mock(),
        'twitter': Mock(),
        'news_api': Mock()
    }
    
    # Yahoo Finance 모의 설정
    apis['yahoo_finance'].get_stock_data = AsyncMock(return_value={
        'symbol': 'AAPL',
        'current_price': 150.0,
        'change': 2.5,
        'change_percent': 1.69
    })
    
    # Reddit 모의 설정
    apis['reddit'].get_posts = AsyncMock(return_value=[
        {'id': '1', 'title': 'Test Post', 'content': 'Test content'}
    ])
    
    # Twitter 모의 설정
    apis['twitter'].get_tweets = AsyncMock(return_value=[
        {'id': '1', 'text': 'Test tweet', 'user': 'test_user'}
    ])
    
    # News API 모의 설정
    apis['news_api'].get_articles = AsyncMock(return_value=[
        {'id': '1', 'title': 'Test News', 'content': 'Test news content'}
    ])
    
    return apis


@pytest.fixture
def sample_stock_data():
    """샘플 주식 데이터 픽스처"""
    return {
        'symbol': 'AAPL',
        'company_name': 'Apple Inc.',
        'current_price': 150.0,
        'change': 2.5,
        'change_percent': 1.69,
        'volume': 1000000,
        'avg_volume': 950000,
        'market_cap': 2500000000000,
        'pe_ratio': 25.5,
        'dividend_yield': 0.5,
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'description': 'Apple Inc. designs, manufactures...',
        'website': 'https://www.apple.com',
        'employees': 147000,
        'founded_year': 1976,
        'headquarters': 'Cupertino, CA'
    }


@pytest.fixture
def sample_sentiment_data():
    """샘플 센티먼트 데이터 픽스처"""
    return {
        'symbol': 'AAPL',
        'overall_sentiment': 0.5,
        'positive_score': 0.7,
        'negative_score': 0.1,
        'neutral_score': 0.2,
        'confidence': 0.8,
        'source': 'news',
        'timestamp': datetime.utcnow().isoformat(),
        'sources_analyzed': 10,
        'positive_mentions': 7,
        'negative_mentions': 1,
        'neutral_mentions': 2,
        'keywords': ['innovation', 'growth', 'strong earnings'],
        'sentiment_distribution': {
            'positive': 0.7,
            'negative': 0.1,
            'neutral': 0.2
        }
    }


@pytest.fixture
def sample_market_data():
    """샘플 시장 데이터 픽스처"""
    return {
        'market_status': 'open',
        'market_sentiment': 0.3,
        'trending_stocks': ['AAPL', 'GOOGL', 'MSFT'],
        'market_capitalization': 30000000000000,
        'trading_volume': 5000000000,
        'advancers': 150,
        'decliners': 120,
        'unchanged': 730,
        'sector_performance': {
            'Technology': 2.5,
            'Healthcare': 1.2,
            'Finance': 0.8,
            'Energy': -0.5
        },
        'indices': {
            'S&P_500': 4500.0,
            'Dow_Jones': 35000.0,
            'NASDAQ': 14000.0
        }
    }


@pytest.fixture
def mock_cache_manager():
    """캐시 관리자 모의 객체 픽스처"""
    cache_manager = Mock()
    cache_manager.get = AsyncMock()
    cache_manager.set = AsyncMock(return_value=True)
    cache_manager.delete = AsyncMock(return_value=True)
    cache_manager.get_stock_data = AsyncMock()
    cache_manager.set_stock_data = AsyncMock(return_value=True)
    cache_manager.get_sentiment_data = AsyncMock()
    cache_manager.set_sentiment_data = AsyncMock(return_value=True)
    cache_manager.get_cache_stats = AsyncMock(return_value={
        'hits': 100,
        'misses': 20,
        'sets': 50,
        'deletes': 10,
        'errors': 0
    })
    return cache_manager


@pytest.fixture
def mock_gateway():
    """API 게이트웨이 모의 객체 픽스처"""
    gateway = Mock()
    gateway.route_request = AsyncMock()
    gateway.add_route = Mock()
    gateway.register_service = Mock()
    gateway.get_metrics = AsyncMock(return_value={
        'total_requests': 1000,
        'successful_requests': 950,
        'failed_requests': 50,
        'average_response_time': 0.15,
        'p95_response_time': 0.3,
        'p99_response_time': 0.5
    })
    gateway.health_check = AsyncMock(return_value={
        'status': 'healthy',
        'routes': 10,
        'circuit_breakers': 5,
        'timestamp': datetime.utcnow().isoformat()
    })
    return gateway


@pytest.fixture
def performance_config():
    """성능 테스트 설정 픽스처"""
    return {
        'concurrency_levels': [10, 50, 100, 500],
        'response_time_thresholds': {
            'avg': 0.1,  # 100ms
            'p95': 0.2,  # 200ms
            'p99': 0.5   # 500ms
        },
        'throughput_thresholds': {
            'min': 100,   # 100 ops/sec
            'target': 500, # 500 ops/sec
            'max': 1000   # 1000 ops/sec
        },
        'memory_thresholds': {
            'warning': 70,  # 70%
            'critical': 85  # 85%
        },
        'cpu_thresholds': {
            'warning': 70,  # 70%
            'critical': 85  # 85%
        }
    }


@pytest.fixture
def test_environment():
    """테스트 환경 설정 픽스처"""
    return {
        'REDIS_URL': 'redis://localhost:6379/0',
        'DATABASE_URL': 'sqlite:///test.db',
        'LOG_LEVEL': 'DEBUG',
        'API_TIMEOUT': 30,
        'MAX_RETRIES': 3,
        'RATE_LIMIT': 1000,
        'CACHE_TTL': 300
    }


@pytest.fixture
def mock_kafka_event_bus():
    """Kafka 이벤트 버스 모의 객체 픽스처"""
    kafka_mock = Mock()
    kafka_mock.publish_stock_price_update = AsyncMock()
    kafka_mock.publish_sentiment_update = AsyncMock()
    kafka_mock.publish_system_alert = AsyncMock()
    kafka_mock.subscribe = AsyncMock()
    kafka_mock.initialize = AsyncMock()
    return kafka_mock


@pytest.fixture
def mock_sentiment_service():
    """센티먼트 서비스 모의 객체 픽스처"""
    service = Mock()
    service.analyze_sentiment = AsyncMock(return_value={
        'sentiment': 0.5,
        'confidence': 0.8,
        'positive_score': 0.7,
        'negative_score': 0.1,
        'neutral_score': 0.2
    })
    service.analyze_batch_sentiment = AsyncMock(return_value=[
        {
            'sentiment': 0.5,
            'confidence': 0.8,
            'positive_score': 0.7,
            'negative_score': 0.1,
            'neutral_score': 0.2
        }
    ])
    service.get_sentiment_trend = AsyncMock(return_value={
        'trend': 'increasing',
        'strength': 0.3,
        'data_points': 24
    })
    return service


@pytest.fixture
def mock_data_collector():
    """데이터 수집기 모의 객체 픽스처"""
    collector = Mock()
    collector.add_symbol = AsyncMock(return_value=True)
    collector.remove_symbol = AsyncMock(return_value=True)
    collector.get_collection_stats = AsyncMock(return_value={
        'total_collections': 1000,
        'successful_collections': 950,
        'failed_collections': 50,
        'success_rate': 95.0,
        'active_symbols': 50,
        'last_collection_time': datetime.utcnow().isoformat()
    })
    collector.start = AsyncMock()
    collector.stop = AsyncMock()
    return collector


@pytest.fixture
def error_scenarios():
    """에러 시나리오 픽스처"""
    return {
        'service_unavailable': {
            'exception': Exception('Service unavailable'),
            'expected_status': 503,
            'retry_after': 5
        },
        'timeout_error': {
            'exception': asyncio.TimeoutError('Request timeout'),
            'expected_status': 504,
            'retry_after': 1
        },
        'rate_limit_exceeded': {
            'exception': Exception('Rate limit exceeded'),
            'expected_status': 429,
            'retry_after': 60
        },
        'authentication_error': {
            'exception': Exception('Authentication failed'),
            'expected_status': 401,
            'retry_after': 0
        },
        'validation_error': {
            'exception': ValueError('Invalid input'),
            'expected_status': 400,
            'retry_after': 0
        }
    }


@pytest.fixture
def security_test_data():
    """보안 테스트 데이터 픽스처"""
    return {
        'valid_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'expired_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired',
        'invalid_token': 'invalid.token.format',
        'malformed_token': 'malformed_token',
        'valid_api_key': 'sk_test_valid_key_12345',
        'invalid_api_key': 'sk_test_invalid_key',
        'test_user_id': 'user123',
        'test_permissions': ['read', 'write', 'admin'],
        'test_ip': '192.168.1.1',
        'suspicious_ip': '10.0.0.1'
    }


@pytest.fixture
def load_test_data():
    """부하 테스트 데이터 픽스처"""
    return {
        'light_load': {
            'concurrent_users': 10,
            'requests_per_second': 50,
            'duration': 60,
            'expected_response_time': 0.1
        },
        'medium_load': {
            'concurrent_users': 50,
            'requests_per_second': 200,
            'duration': 120,
            'expected_response_time': 0.2
        },
        'heavy_load': {
            'concurrent_users': 200,
            'requests_per_second': 500,
            'duration': 300,
            'expected_response_time': 0.5
        },
        'stress_test': {
            'concurrent_users': 500,
            'requests_per_second': 1000,
            'duration': 600,
            'expected_response_time': 1.0
        }
    }


# 테스트 마커 정의
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow
pytest.mark.redis = pytest.mark.redis
pytest.mark.external_api = pytest.mark.external_api
pytest.mark.database = pytest.mark.database
pytest.mark.auth = pytest.mark.auth
pytest.mark.cache = pytest.mark.cache
pytest.mark.gateway = pytest.mark.gateway
pytest.mark.sentiment = pytest.mark.sentiment
pytest.mark.realtime = pytest.mark.realtime
pytest.mark.security = pytest.mark.security


# 테스트 유틸리티 함수
def assert_valid_response(response, expected_status=200):
    """유효한 응답 검증 유틸리티"""
    assert response is not None
    assert 'status_code' in response or 'status' in response
    status_code = response.get('status_code', response.get('status', 200))
    assert status_code == expected_status, f"Expected status {expected_status}, got {status_code}"


def assert_valid_data_structure(data, required_fields):
    """유효한 데이터 구조 검증 유틸리티"""
    assert data is not None
    assert isinstance(data, dict)
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def assert_performance_metrics(metrics, thresholds):
    """성능 메트릭 검증 유틸리티"""
    assert 'avg_response_time' in metrics
    assert 'p95_response_time' in metrics
    assert 'throughput' in metrics
    
    if 'avg' in thresholds:
        assert metrics['avg_response_time'] <= thresholds['avg'], \
            f"Average response time {metrics['avg_response_time']} exceeds threshold {thresholds['avg']}"
    
    if 'p95' in thresholds:
        assert metrics['p95_response_time'] <= thresholds['p95'], \
            f"P95 response time {metrics['p95_response_time']} exceeds threshold {thresholds['p95']}"
    
    if 'throughput' in thresholds:
        assert metrics['throughput'] >= thresholds['throughput'], \
            f"Throughput {metrics['throughput']} below threshold {thresholds['throughput']}"


def assert_cache_hit_rate(stats, min_hit_rate=70.0):
    """캐시 히트율 검증 유틸리티"""
    assert 'hit_rate' in stats
    hit_rate = stats['hit_rate']
    assert hit_rate >= min_hit_rate, \
        f"Cache hit rate {hit_rate}% below minimum {min_hit_rate}%"


def assert_error_handling(response, expected_error_type=None):
    """에러 처리 검증 유틸리티"""
    assert response is not None
    assert 'error' in response or 'status_code' in response
    
    if expected_error_type:
        assert 'error_type' in response
        assert response['error_type'] == expected_error_type


# 테스트 데이터 생성기
def generate_test_symbols(count=10):
    """테스트용 주식 심볼 생성"""
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 
               'META', 'NVDA', 'JPM', 'JNJ', 'V']
    return symbols[:count]


def generate_test_text(length=100):
    """테스트용 텍스트 생성"""
    words = ['bullish', 'bearish', 'rally', 'decline', 'growth', 
            'profit', 'loss', 'strong', 'weak', 'volatile']
    text = ' '.join(words[i % len(words)] for i in range(length))
    return text


def generate_timestamps(days=30, hours=24):
    """테스트용 타임스탬프 생성"""
    import random
    from datetime import datetime, timedelta
    
    base_time = datetime.utcnow()
    timestamps = []
    
    for day in range(days):
        for hour in range(hours):
            # 랜덤 시간 생성 (±30분)
            random_minutes = random.randint(-30, 30)
            timestamp = base_time - timedelta(days=day, hours=hour, minutes=random_minutes)
            timestamps.append(timestamp)
    
    return timestamps


# 환경 변수 설정
os.environ['TESTING'] = 'true'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['CACHE_TTL'] = '60'
os.environ['API_TIMEOUT'] = '5'