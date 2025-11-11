"""
UnifiedCacheManager 단위 테스트

이 모듈은 UnifiedCacheManager의 개별 기능을 독립적으로 테스트합니다.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from backend.cache.unified_cache import UnifiedCacheManager
from backend.models.unified_models import UnifiedStockData, SearchQuery


class TestUnifiedCacheManager:
    """UnifiedCacheManager 단위 테스트 클래스"""
    
    @pytest.fixture
    def cache_manager(self, mock_redis):
        """UnifiedCacheManager 픽스처"""
        manager = UnifiedCacheManager(backend=mock_redis)
        return manager
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, cache_manager, mock_redis):
        """성공적인 초기화 테스트"""
        # 테스트 실행
        result = await cache_manager.initialize()
        
        # 검증
        assert result is True
    
    @pytest.mark.asyncio
    async def test_initialize_fallback(self, cache_manager):
        """Redis 실패 시 폴백 테스트"""
        # Redis 초기화 실패 설정
        with patch('backend.cache.unified_cache.RedisCacheBackend') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis connection failed")
            
            with patch('backend.cache.unified_cache.resilient_cache_manager') as mock_resilient:
                mock_resilient.initialize = AsyncMock(return_value=True)
                
                # 테스트 실행
                result = await cache_manager.initialize()
                
                # 검증
                assert result is True
                mock_resilient.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_local_cache_hit(self, cache_manager):
        """로컬 캐시 히트 테스트"""
        # 로컬 캐시에 미리 데이터 저장
        test_key = "test_key"
        test_value = {"data": "test_value"}
        cache_manager._local_cache[test_key] = test_value
        cache_manager._local_cache_ttl[test_key] = time.time() + 60
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result == test_value
        assert cache_manager.stats['hits'] == 1
        assert cache_manager.stats['misses'] == 0
    
    @pytest.mark.asyncio
    async def test_get_local_cache_miss_expired(self, cache_manager):
        """로컬 캐시 만료 테스트"""
        # 만료된 데이터 저장
        test_key = "test_key"
        test_value = {"data": "test_value"}
        cache_manager._local_cache[test_key] = test_value
        cache_manager._local_cache_ttl[test_key] = time.time() - 60  # 만료됨
        
        # 모의 백엔드 설정
        cache_manager.backend = AsyncMock()
        cache_manager.backend.get.return_value = None
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result is None
        assert cache_manager.stats['hits'] == 0
        assert cache_manager.stats['misses'] == 1
        assert test_key not in cache_manager._local_cache
    
    @pytest.mark.asyncio
    async def test_get_backend_hit(self, cache_manager, mock_redis):
        """백엔드 캐시 히트 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        # 백엔드에 데이터 설정
        mock_redis.get.return_value = json.dumps(test_value)
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result == test_value
        assert cache_manager.stats['hits'] == 1
        assert cache_manager.stats['misses'] == 0
        
        # 로컬 캐시에 저장되었는지 확인
        assert test_key in cache_manager._local_cache
    
    @pytest.mark.asyncio
    async def test_get_backend_miss(self, cache_manager, mock_redis):
        """백엔드 캐시 미스 테스트"""
        test_key = "test_key"
        
        # 백엔드에 데이터 없음 설정
        mock_redis.get.return_value = None
        
        # 테스트 실행
        result = await cache_manager.get(test_key)
        
        # 검증
        assert result is None
        assert cache_manager.stats['hits'] == 0
        assert cache_manager.stats['misses'] == 1
    
    @pytest.mark.asyncio
    async def test_get_no_backend(self, cache_manager):
        """백엔드 없을 때 테스트"""
        cache_manager.backend = None
        
        # 테스트 실행
        result = await cache_manager.get("test_key")
        
        # 검증
        assert result is None
        assert cache_manager.stats['hits'] == 0
        assert cache_manager.stats['misses'] == 1
    
    @pytest.mark.asyncio
    async def test_get_error_handling(self, cache_manager, mock_redis):
        """에러 처리 테스트"""
        # 백엔드에서 예외 발생 설정
        mock_redis.get.side_effect = Exception("Cache error")
        
        # 테스트 실행
        result = await cache_manager.get("test_key")
        
        # 검증
        assert result is None
        assert cache_manager.stats['hits'] == 0
        assert cache_manager.stats['misses'] == 1
        assert cache_manager.stats['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_set_success(self, cache_manager, mock_redis):
        """성공적인 설정 테스트"""
        test_key = "test_key"
        test_value = {"data": "test_value"}
        test_ttl = 300
        
        # 백엔드 성공 설정
        mock_redis.set.return_value = True
        
        # 테스트 실행
        result = await cache_manager.set(test_key, test_value, test_ttl)
        
        # 검증
        assert result is True
        assert cache_manager.stats['sets'] == 1
        
        # 로컬 캐시에 저장되었는지 확인
        assert test_key in cache_manager._local_cache
        
        # 백엔드에 저장되었는지 확인
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == test_key
        assert call_args[0][1] == json.dumps(test_value)
        assert call_args[1]['ttl'] == test_ttl
    
    @pytest.mark.asyncio
    async def test_set_no_backend(self, cache_manager):
        """백엔드 없을 때 설정 테스트"""
        cache_manager.backend = None
        
        # 테스트 실행
        result = await cache_manager.set("test_key", {"data": "test"})
        
        # 검증
        assert result is False
        assert cache_manager.stats['sets'] == 0
    
    @pytest.mark.asyncio
    async def test_set_error_handling(self, cache_manager, mock_redis):
        """설정 시 에러 처리 테스트"""
        # 백엔드에서 예외 발생 설정
        mock_redis.set.side_effect = Exception("Cache error")
        
        # 테스트 실행
        result = await cache_manager.set("test_key", {"data": "test"})
        
        # 검증
        assert result is False
        assert cache_manager.stats['sets'] == 0
        assert cache_manager.stats['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_delete_success(self, cache_manager, mock_redis):
        """성공적인 삭제 테스트"""
        test_key = "test_key"
        
        # 로컬 캐시에 데이터 저장
        cache_manager._local_cache[test_key] = {"data": "test"}
        cache_manager._local_cache_ttl[test_key] = time.time() + 60
        
        # 백엔드 성공 설정
        mock_redis.delete.return_value = True
        
        # 테스트 실행
        result = await cache_manager.delete(test_key)
        
        # 검증
        assert result is True
        assert cache_manager.stats['deletes'] == 1
        
        # 로컬 캐시에서 삭제되었는지 확인
        assert test_key not in cache_manager._local_cache
        assert test_key not in cache_manager._local_cache_ttl
        
        # 백엔드에서 삭제되었는지 확인
        mock_redis.delete.assert_called_once_with(test_key)
    
    @pytest.mark.asyncio
    async def test_delete_no_backend(self, cache_manager):
        """백엔드 없을 때 삭제 테스트"""
        cache_manager.backend = None
        
        # 테스트 실행
        result = await cache_manager.delete("test_key")
        
        # 검증
        assert result is False
        assert cache_manager.stats['deletes'] == 0
    
    @pytest.mark.asyncio
    async def test_delete_pattern_success(self, cache_manager, mock_redis):
        """패턴 삭제 성공 테스트"""
        pattern = "test:*"
        deleted_count = 5
        
        # 백엔드 성공 설정
        mock_redis.delete_pattern.return_value = deleted_count
        
        # 테스트 실행
        result = await cache_manager.delete_pattern(pattern)
        
        # 검증
        assert result == deleted_count
        assert cache_manager.stats['deletes'] == deleted_count
        
        # 백엔드에서 패턴 삭제가 호출되었는지 확인
        mock_redis.delete_pattern.assert_called_once_with(pattern)
    
    @pytest.mark.asyncio
    async def test_delete_pattern_no_backend(self, cache_manager):
        """백엔드 없을 때 패턴 삭제 테스트"""
        cache_manager.backend = None
        
        # 테스트 실행
        result = await cache_manager.delete_pattern("test:*")
        
        # 검증
        assert result == 0
        assert cache_manager.stats['deletes'] == 0
    
    @pytest.mark.asyncio
    async def test_get_stock_data_success(self, cache_manager, mock_redis, sample_stock_data):
        """주식 데이터 조회 성공 테스트"""
        symbol = "AAPL"
        stock_data = UnifiedStockData(**sample_stock_data)
        
        # 백엔드에 데이터 설정
        mock_redis.get.return_value = json.dumps(sample_stock_data)
        
        # 테스트 실행
        result = await cache_manager.get_stock_data(symbol)
        
        # 검증
        assert result is not None
        assert isinstance(result, UnifiedStockData)
        assert result.symbol == symbol
        assert result.current_price == sample_stock_data['current_price']
        
        # 올바른 키로 호출되었는지 확인
        expected_key = f"stock:{symbol}"
        mock_redis.get.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_get_stock_data_not_found(self, cache_manager, mock_redis):
        """주식 데이터 없을 때 테스트"""
        symbol = "AAPL"
        
        # 백엔드에 데이터 없음 설정
        mock_redis.get.return_value = None
        
        # 테스트 실행
        result = await cache_manager.get_stock_data(symbol)
        
        # 검증
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_stock_data_invalid_data(self, cache_manager, mock_redis):
        """잘못된 주식 데이터 테스트"""
        symbol = "AAPL"
        
        # 백엔드에 잘못된 데이터 설정
        mock_redis.get.return_value = "invalid_json"
        
        # 테스트 실행
        result = await cache_manager.get_stock_data(symbol)
        
        # 검증
        assert result is None
        
        # 삭제가 호출되었는지 확인
        expected_key = f"stock:{symbol}"
        mock_redis.delete.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_set_stock_data_success(self, cache_manager, mock_redis, sample_stock_data):
        """주식 데이터 설정 성공 테스트"""
        stock_data = UnifiedStockData(**sample_stock_data)
        
        # 백엔드 성공 설정
        mock_redis.set.return_value = True
        
        # 테스트 실행
        result = await cache_manager.set_stock_data(stock_data)
        
        # 검증
        assert result is True
        
        # 올바른 키와 데이터로 호출되었는지 확인
        expected_key = f"stock:{stock_data.symbol}"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == stock_data.to_dict()
        assert call_args[1]['ttl'] == cache_manager.ttl_settings['stock_data']
    
    @pytest.mark.asyncio
    async def test_get_search_results_success(self, cache_manager, mock_redis, sample_search_results):
        """검색 결과 조회 성공 테스트"""
        query = create_mock_search_query("Apple")
        query_hash = cache_manager._generate_query_hash(query)
        
        # 백엔드에 데이터 설정
        search_data = {
            'query': query.to_dict(),
            'results': sample_search_results,
            'total_count': len(sample_search_results),
            'timestamp': datetime.utcnow().isoformat()
        }
        mock_redis.get.return_value = json.dumps(search_data)
        
        # 테스트 실행
        result = await cache_manager.get_search_results(query)
        
        # 검증
        assert result is not None
        assert len(result) == len(sample_search_results)
        
        # 각 결과 확인
        for i, stock in enumerate(result):
            assert isinstance(stock, UnifiedStockData)
            assert stock.symbol == sample_search_results[i]['symbol']
        
        # 올바른 키로 호출되었는지 확인
        expected_key = f"search:{query_hash}"
        mock_redis.get.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_set_search_results_success(self, cache_manager, mock_redis, sample_search_results):
        """검색 결과 설정 성공 테스트"""
        query = create_mock_search_query("Apple")
        unified_results = [UnifiedStockData(**result) for result in sample_search_results]
        
        # 백엔드 성공 설정
        mock_redis.set.return_value = True
        
        # 테스트 실행
        result = await cache_manager.set_search_results(query, unified_results)
        
        # 검증
        assert result is True
        
        # 올바른 데이터로 호출되었는지 확인
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        expected_key = f"search:{cache_manager._generate_query_hash(query)}"
        
        assert call_args[0][0] == expected_key
        
        # 저장된 데이터 구조 확인
        stored_data = call_args[0][1]
        assert 'query' in stored_data
        assert 'results' in stored_data
        assert 'total_count' in stored_data
        assert 'timestamp' in stored_data
        assert stored_data['total_count'] == len(unified_results)
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data_success(self, cache_manager, mock_redis, sample_sentiment_data):
        """감성 데이터 조회 성공 테스트"""
        symbol = "AAPL"
        
        # 백엔드에 데이터 설정
        mock_redis.get.return_value = json.dumps(sample_sentiment_data)
        
        # 테스트 실행
        result = await cache_manager.get_sentiment_data(symbol)
        
        # 검증
        assert result is not None
        assert result['symbol'] == symbol
        assert 'overall_sentiment' in result
        assert 'mention_count_24h' in result
        
        # 올바른 키로 호출되었는지 확인
        expected_key = f"sentiment:{symbol}"
        mock_redis.get.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_set_sentiment_data_success(self, cache_manager, mock_redis, sample_sentiment_data):
        """감성 데이터 설정 성공 테스트"""
        symbol = "AAPL"
        
        # 백엔드 성공 설정
        mock_redis.set.return_value = True
        
        # 테스트 실행
        result = await cache_manager.set_sentiment_data(symbol, sample_sentiment_data)
        
        # 검증
        assert result is True
        
        # 올바른 키와 데이터로 호출되었는지 확인
        expected_key = f"sentiment:{symbol}"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == sample_sentiment_data
        assert call_args[1]['ttl'] == cache_manager.ttl_settings['sentiment_data']
    
    @pytest.mark.asyncio
    async def test_get_trending_stocks_success(self, cache_manager, mock_redis):
        """트렌딩 주식 조회 성공 테스트"""
        timeframe = "24h"
        trending_data = [
            {'symbol': 'AAPL', 'trend_score': 2.0},
            {'symbol': 'GOOGL', 'trend_score': 1.5}
        ]
        
        # 백엔드에 데이터 설정
        mock_redis.get.return_value = json.dumps(trending_data)
        
        # 테스트 실행
        result = await cache_manager.get_trending_stocks(timeframe)
        
        # 검증
        assert result is not None
        assert len(result) == len(trending_data)
        assert result[0]['symbol'] == 'AAPL'
        assert result[0]['trend_score'] == 2.0
        
        # 올바른 키로 호출되었는지 확인
        expected_key = f"trending:{timeframe}"
        mock_redis.get.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_set_trending_stocks_success(self, cache_manager, mock_redis):
        """트렌딩 주식 설정 성공 테스트"""
        timeframe = "24h"
        trending_stocks = [
            {'symbol': 'AAPL', 'trend_score': 2.0},
            {'symbol': 'GOOGL', 'trend_score': 1.5}
        ]
        
        # 백엔드 성공 설정
        mock_redis.set.return_value = True
        
        # 테스트 실행
        result = await cache_manager.set_trending_stocks(timeframe, trending_stocks)
        
        # 검증
        assert result is True
        
        # 올바른 키와 데이터로 호출되었는지 확인
        expected_key = f"trending:{timeframe}"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == trending_stocks
        assert call_args[1]['ttl'] == cache_manager.ttl_settings['trending_stocks']
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_success(self, cache_manager, mock_redis):
        """속도 제한 확인 성공 테스트"""
        identifier = "test_user"
        window = "60s"
        limit = 10
        
        # 백엔드에 현재 카운트 설정
        mock_redis.get.return_value = "5"  # 현재 5번 요청
        
        # 테스트 실행
        result = await cache_manager.check_rate_limit(identifier, window, limit)
        
        # 검증
        assert result is True  # 제한 내
        
        # 카운트 증가 확인
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        expected_key = f"rate_limit:{identifier}:{window}"
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == 6  # 5 + 1
        assert call_args[1]['ttl'] == cache_manager.ttl_settings['rate_limit']
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, cache_manager, mock_redis):
        """속도 제한 초과 테스트"""
        identifier = "test_user"
        window = "60s"
        limit = 10
        
        # 백엔드에 현재 카운트 설정 (제한 도달)
        mock_redis.get.return_value = "10"  # 이미 제한 도달
        
        # 테스트 실행
        result = await cache_manager.check_rate_limit(identifier, window, limit)
        
        # 검증
        assert result is False  # 제한 초과
        
        # 카운트 증가 안 함 확인
        mock_redis.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_no_count(self, cache_manager, mock_redis):
        """속도 제한 확인 (카운트 없음) 테스트"""
        identifier = "test_user"
        window = "60s"
        limit = 10
        
        # 백엔드에 카운트 없음 설정
        mock_redis.get.return_value = None
        
        # 테스트 실행
        result = await cache_manager.check_rate_limit(identifier, window, limit)
        
        # 검증
        assert result is True  # 제한 내
        
        # 카운트 1로 설정 확인
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        expected_key = f"rate_limit:{identifier}:{window}"
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == 1
        assert call_args[1]['ttl'] == cache_manager.ttl_settings['rate_limit']
    
    @pytest.mark.asyncio
    async def test_invalidate_stock_data_success(self, cache_manager, mock_redis):
        """주식 데이터 무효화 성공 테스트"""
        symbol = "AAPL"
        deleted_count = 3
        
        # 백엔드 성공 설정
        mock_redis.delete.return_value = True
        mock_redis.delete_pattern.return_value = 2  # 패턴 삭제된 수
        
        # 테스트 실행
        result = await cache_manager.invalidate_stock_data(symbol)
        
        # 검증
        assert result == deleted_count
        
        # 각 패턴 삭제 확인
        expected_patterns = [
            f"stock:{symbol}",
            f"sentiment:{symbol}",
            f"hist:{symbol}:*"
        ]
        
        # 개별 삭제 확인
        assert mock_redis.delete.call_count == 1
        assert mock_redis.delete.call_args[0][0] == f"stock:{symbol}"
        
        # 패턴 삭제 확인
        assert mock_redis.delete_pattern.call_count == 2
        assert mock_redis.delete_pattern.call_args_list[0][0][0] == f"sentiment:{symbol}"
        assert mock_redis.delete_pattern.call_args_list[1][0][0] == f"hist:{symbol}:*"
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_manager):
        """캐시 통계 조회 테스트"""
        # 통계 설정
        cache_manager.stats = {
            'hits': 80,
            'misses': 20,
            'sets': 50,
            'deletes': 10,
            'errors': 5
        }
        
        # 백엔드 통계 설정
        mock_backend_stats = {
            'memory_usage': 1024,
            'key_count': 100
        }
        cache_manager.backend = AsyncMock()
        cache_manager.backend.get_stats.return_value = mock_backend_stats
        
        # 테스트 실행
        result = await cache_manager.get_cache_stats()
        
        # 검증
        assert result['hits'] == 80
        assert result['misses'] == 20
        assert result['sets'] == 50
        assert result['deletes'] == 10
        assert result['errors'] == 5
        assert result['hit_rate'] == 80.0  # 80 / (80 + 20) * 100
        
        # 백엔드 통계 포함 확인
        assert 'memory_usage' in result
        assert 'key_count' in result
    
    @pytest.mark.asyncio
    async def test_clear_all_success(self, cache_manager, mock_redis):
        """전체 삭제 성공 테스트"""
        # 백엔드 성공 설정
        mock_redis.clear_all.return_value = True
        
        # 테스트 실행
        result = await cache_manager.clear_all()
        
        # 검증
        assert result is True
        
        # 통계 초기화 확인
        assert cache_manager.stats['hits'] == 0
        assert cache_manager.stats['misses'] == 0
        assert cache_manager.stats['sets'] == 0
        assert cache_manager.stats['deletes'] == 0
        assert cache_manager.stats['errors'] == 0
        
        # 로컬 캐시 초기화 확인
        assert len(cache_manager._local_cache) == 0
        assert len(cache_manager._local_cache_ttl) == 0
        
        # 백엔드 전체 삭제 호출 확인
        mock_redis.clear_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_manager, mock_redis):
        """상태 확인 성공 테스트"""
        # 백엔드 성공 설정
        mock_redis.get.return_value = json.dumps({'test': 'data'})
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        
        # 백엔드 통계 설정
        mock_redis.get_stats.return_value = {'memory_usage': 1024}
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result['status'] == 'healthy'
        assert 'stats' in result
        assert 'backend' in result
        assert result['backend'] == 'Redis'  # Mock 클래스 이름
    
    @pytest.mark.asyncio
    async def test_health_check_no_backend(self, cache_manager):
        """백엔드 없을 때 상태 확인 테스트"""
        cache_manager.backend = None
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result['status'] == 'unhealthy'
        assert 'reason' in result
        assert result['reason'] == 'No backend configured'
    
    @pytest.mark.asyncio
    async def test_health_check_backend_error(self, cache_manager, mock_redis):
        """백엔드 오류 시 상태 확인 테스트"""
        # 백엔드 오류 설정
        mock_redis.get.side_effect = Exception("Backend error")
        
        # 테스트 실행
        result = await cache_manager.health_check()
        
        # 검증
        assert result['status'] == 'unhealthy'
        assert 'reason' in result
        assert 'Backend error' in result['reason']
    
    def test_generate_query_hash(self, cache_manager):
        """쿼리 해시 생성 테스트"""
        # 동일한 쿼리에 대해 동일한 해시 생성 확인
        query1 = create_mock_search_query("Apple", {'sector': 'Technology'})
        query2 = create_mock_search_query("Apple", {'sector': 'Technology'})
        
        hash1 = cache_manager._generate_query_hash(query1)
        hash2 = cache_manager._generate_query_hash(query2)
        
        # 검증
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 해시 길이
        
        # 다른 쿼리에 대해 다른 해시 생성 확인
        query3 = create_mock_search_query("Google", {'sector': 'Technology'})
        hash3 = cache_manager._generate_query_hash(query3)
        
        assert hash1 != hash3
    
    def test_get_key(self, cache_manager):
        """키 생성 테스트"""
        # 테스트 케이스
        test_cases = [
            ('stock_data', {'symbol': 'AAPL'}, 'stock:AAPL'),
            ('search_results', {'query_hash': 'abc123'}, 'search:abc123'),
            ('sentiment_data', {'symbol': 'GOOGL'}, 'sentiment:GOOGL'),
            ('trending_stocks', {'timeframe': '24h'}, 'trending:24h'),
            ('user_watchlist', {'user_id': 'user123'}, 'watchlist:user123')
        ]
        
        for pattern, kwargs, expected_key in test_cases:
            result = cache_manager._get_key(pattern, **kwargs)
            assert result == expected_key
    
    def test_store_in_local_cache(self, cache_manager):
        """로컬 캐시 저장 테스트"""
        # 로컬 캐시 크기 제한 설정
        cache_manager._local_cache_max_size = 2
        
        # 첫 번째 데이터 저장
        cache_manager._store_in_local_cache("key1", "value1", 60)
        assert "key1" in cache_manager._local_cache
        
        # 두 번째 데이터 저장
        cache_manager._store_in_local_cache("key2", "value2", 60)
        assert "key2" in cache_manager._local_cache
        
        # 세 번째 데이터 저장 (LRU로 인해 가장 오래된 데이터 삭제)
        cache_manager._store_in_local_cache("key3", "value3", 60)
        assert "key3" in cache_manager._local_cache
        assert "key1" not in cache_manager._local_cache  # 가장 오래된 데이터 삭제
        assert "key2" in cache_manager._local_cache


# 테스트 헬퍼 함수
def create_mock_search_query(query: str, filters: dict = None):
    """모의 검색 쿼리 생성"""
    return SearchQuery(
        query=query,
        filters=filters or {},
        limit=10,
        offset=0,
        sort_by='relevance',
        sort_order='desc'
    )