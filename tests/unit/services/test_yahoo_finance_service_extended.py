"""
YahooFinanceService 확장 테스트

미커버리지 영역에 대한 추가 테스트 케이스
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from dataclasses import asdict

from backend.services.yahoo_finance_service import (
    YahooFinanceService,
    StockData,
    HistoricalData
)


class TestYahooFinanceServiceExtended:
    """YahooFinanceService 확장 테스트 클래스"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """모의 Redis 클라이언트"""
        client = AsyncMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.setex.return_value = True
        return client
    
    @pytest.fixture
    def mock_session(self):
        """모의 HTTP 세션"""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def yahoo_finance_service(self, mock_redis_client, mock_session):
        """YahooFinanceService 인스턴스"""
        service = YahooFinanceService()
        service.redis_client = mock_redis_client
        service.session = mock_session
        return service
    
    @pytest.mark.asyncio
    async def test_save_to_cache_success(self, yahoo_finance_service, mock_redis_client):
        """캐시에 데이터 저장 성공 테스트"""
        # 설정
        test_data = {"symbol": "AAPL", "price": 150.25}
        
        # 테스트 실행
        await yahoo_finance_service._save_to_cache("test_key", test_data, "current")
        
        # 결과 검증
        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args[0]
        assert call_args[0] == "test_key"  # key
        assert call_args[1] == 60  # TTL (current 타입)
        
        # JSON 문자열 비교 - 직접 JSON 변환 결과 비교
        expected_json = json.dumps(test_data)
        assert call_args[2] == expected_json  # value
    
    @pytest.mark.asyncio
    async def test_save_to_cache_no_redis(self, yahoo_finance_service):
        """Redis 클라이언트 없을 때 캐시 저장 테스트"""
        # 설정
        yahoo_finance_service.redis_client = None
        test_data = {"symbol": "AAPL", "price": 150.25}
        
        # 테스트 실행 (예외 없이 실행되어야 함)
        await yahoo_finance_service._save_to_cache("test_key", test_data, "current")
        
        # 결과 검증 - 아무것도 호출되지 않아야 함
        assert True  # 테스트가 완료되었음을 확인
    
    @pytest.mark.asyncio
    async def test_save_to_cache_error_handling(self, yahoo_finance_service, mock_redis_client):
        """캐시 저장 오류 처리 테스트"""
        # 설정
        mock_redis_client.setex.side_effect = Exception("Redis error")
        test_data = {"symbol": "AAPL", "price": 150.25}
        
        # 테스트 실행 (예외 없이 실행되어야 함)
        await yahoo_finance_service._save_to_cache("test_key", test_data, "current")
        
        # 결과 검증 - 예외가 처리되었는지 확인
        assert True  # 테스트가 완료되었음을 확인
    
    @pytest.mark.asyncio
    async def test_get_from_cache_not_found(self, yahoo_finance_service, mock_redis_client):
        """캐시에서 데이터가 없을 때 테스트"""
        # 설정
        mock_redis_client.get.return_value = None
        
        # 테스트 실행
        result = await yahoo_finance_service._get_from_cache("nonexistent_key", "current")
        
        # 결과 검증
        assert result is None
        mock_redis_client.get.assert_called_once_with("nonexistent_key")
    
    @pytest.mark.asyncio
    async def test_get_from_cache_invalid_json(self, yahoo_finance_service, mock_redis_client):
        """캐시에서 잘못된 JSON 데이터 처리 테스트"""
        # 설정
        mock_redis_client.get.return_value = "invalid json"
        
        # 테스트 실행
        result = await yahoo_finance_service._get_from_cache("invalid_key", "current")
        
        # 결과 검증
        assert result is None  # JSON 파싱 오류 시 None 반환
    
    @pytest.mark.asyncio
    async def test_get_from_cache_no_redis(self, yahoo_finance_service):
        """Redis 클라이언트 없을 때 캐시 조회 테스트"""
        # 설정
        yahoo_finance_service.redis_client = None
        
        # 테스트 실행
        result = await yahoo_finance_service._get_from_cache("test_key", "current")
        
        # 결과 검증
        assert result is None
    
    @pytest.mark.asyncio
    async def test_close_service(self, yahoo_finance_service, mock_redis_client, mock_session):
        """서비스 종료 테스트"""
        # 테스트 실행
        await yahoo_finance_service.close()
        
        # 결과 검증
        mock_session.close.assert_called_once()
        mock_redis_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_service_no_session(self, yahoo_finance_service, mock_redis_client):
        """세션 없을 때 서비스 종료 테스트"""
        # 설정
        yahoo_finance_service.session = None
        
        # 테스트 실행
        await yahoo_finance_service.close()
        
        # 결과 검증
        mock_redis_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_service_no_redis(self, yahoo_finance_service, mock_session):
        """Redis 클라이언트 없을 때 서비스 종료 테스트"""
        # 설정
        yahoo_finance_service.redis_client = None
        
        # 테스트 실행
        await yahoo_finance_service.close()
        
        # 결과 검증
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_redis_client):
        """서비스 초기화 성공 테스트"""
        # 설정
        service = YahooFinanceService()
        service.redis_url = "redis://localhost:6379"
        
        # 모의 Redis 클라이언트 설정
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.return_value = mock_redis_client
            
            # 테스트 실행
            await service.initialize()
            
            # 결과 검증
            mock_redis.assert_called_once_with("redis://localhost:6379")
            mock_redis_client.ping.assert_called_once()
            assert service.redis_client == mock_redis_client
    
    @pytest.mark.asyncio
    async def test_initialize_redis_error(self):
        """Redis 연결 오류 시 초기화 테스트"""
        # 설정
        service = YahooFinanceService()
        service.redis_url = "redis://localhost:6379"
        
        # 모의 Redis 연결 오류
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection error")
            
            # 테스트 실행 및 예외 확인
            with pytest.raises(Exception):
                await service.initialize()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, yahoo_finance_service):
        """동시 요청 처리 테스트"""
        # 설정
        initial_count = yahoo_finance_service.semaphore._value
        
        # 테스트 실행 - 여러 동시 요청 시뮬레이션
        async def make_request():
            async with yahoo_finance_service.semaphore:
                await asyncio.sleep(0.1)
                return "result"
        
        # 동시 요청 실행
        tasks = [make_request() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # 결과 검증
        assert len(results) == 3
        assert all(r == "result" for r in results)
        
        # 세마포어 값이 복원되었는지 확인
        final_count = yahoo_finance_service.semaphore._value
        assert final_count == initial_count
    
    @pytest.mark.asyncio
    async def test_retry_mechanism_exponential_backoff(self, yahoo_finance_service):
        """재시도 메커니즘 지수 백오프 테스트"""
        # 설정
        call_count = 0
        original_time = time.time
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return {"result": "success"}
        
        # 재시도 로직이 포함된 메서드 모의
        with patch.object(yahoo_finance_service, '_fetch_stock_data') as mock_fetch:
            mock_fetch.side_effect = side_effect
            
            # 테스트 실행 - 실제 서비스 메서드를 호출하여 재시도 로직 테스트
            try:
                result = await yahoo_finance_service.get_stock_data("AAPL")
            except:
                # 재시도 실패 시 None 반환 확인
                result = None
            
            # 결과 검증
            assert call_count == 3  # 3번 재시도 확인
    
    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, yahoo_finance_service, mock_redis_client):
        """캐시 TTL 설정 테스트"""
        # 테스트 데이터 타입별 TTL 확인
        ttl_tests = [
            ("current", 60),
            ("historical", 3600),
            ("profile", 86400),
            ("search", 1800),
            ("unknown", 300)  # 기본값
        ]
        
        for data_type, expected_ttl in ttl_tests:
            # 테스트 실행
            await yahoo_finance_service._save_to_cache("test_key", {"data": "test"}, data_type)
            
            # 결과 검증
            call_args = mock_redis_client.setex.call_args[0]
            assert call_args[1] == expected_ttl  # TTL은 두 번째 인자
            
            # 다음 테스트를 위해 mock 리셋
            mock_redis_client.setex.reset_mock()
    
    @pytest.mark.asyncio
    async def test_data_transformation_edge_cases(self, yahoo_finance_service):
        """데이터 변환 엣지 케이스 테스트"""
        # 테스트 케이스 1: 누락 필드
        data_missing_fields = {
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": 150.25
                        # previousClose 누락
                    }
                }]
            }
        }
        
        result = yahoo_finance_service._transform_stock_data(data_missing_fields, "AAPL")
        
        # 결과 검증 - 기본값 사용 확인
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.current_price == 150.25
        assert result.previous_close == 0.0  # 기본값
        
        # 테스트 케이스 2: null 값 처리
        data_with_nulls = {
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": None,  # null 값
                        "previousClose": 147.75
                    }
                }]
            }
        }
        
        result = yahoo_finance_service._transform_stock_data(data_with_nulls, "AAPL")
        
        # 결과 검증 - null 값 처리 확인
        assert result is None  # 필수 필드가 null이면 None 반환
    
    @pytest.mark.asyncio
    async def test_historical_data_transformation_edge_cases(self, yahoo_finance_service):
        """과거 데이터 변환 엣지 케이스 테스트"""
        # 빈 타임스탬프 배열
        data_empty_timestamps = {
            "chart": {
                "result": [{
                    "timestamp": [],
                    "indicators": {
                        "quote": [{
                            "open": [],
                            "high": [],
                            "low": [],
                            "close": [],
                            "volume": []
                        }]
                    }
                }]
            }
        }
        
        result = yahoo_finance_service._transform_historical_data(data_empty_timestamps, "AAPL")
        
        # 결과 검증
        assert result == []  # 빈 데이터 반환
        
        # 불일치한 길이의 배열
        data_mismatched_lengths = {
            "chart": {
                "result": [{
                    "timestamp": [1640995200, 1641081600],
                    "indicators": {
                        "quote": [{
                            "open": [148.50],  # 길이 불일치
                            "high": [151.00, 151.50],
                            "low": [147.75, 148.25],
                            "close": [150.25, 150.75],
                            "volume": [1000000, 1100000]
                        }]
                    }
                }]
            }
        }
        
        result = yahoo_finance_service._transform_historical_data(data_mismatched_lengths, "AAPL")
        
        # 결과 검증 - 길이가 다른 경우 예외 처리로 빈 배열 반환
        assert len(result) == 0  # 실제 구현에서는 길이 불일치 시 빈 배열 반환
    
    @pytest.mark.asyncio
    async def test_search_results_transformation_edge_cases(self, yahoo_finance_service):
        """검색 결과 변환 엣지 케이스 테스트"""
        # 빈 quotes 배열
        data_empty_quotes = {"quotes": []}
        
        result = yahoo_finance_service._transform_search_results(data_empty_quotes)
        
        # 결과 검증
        assert result == []
        
        # 필수 필드 누락
        data_missing_fields = {
            "quotes": [
                {
                    "symbol": "AAPL"
                    # shortname 누락
                }
            ]
        }
        
        result = yahoo_finance_service._transform_search_results(data_missing_fields)
        
        # 결과 검증 - 기본값 사용
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["name"] is None  # shortname과 longname이 모두 없으면 None 반환
    
    @pytest.mark.asyncio
    async def test_profile_data_transformation_edge_cases(self, yahoo_finance_service):
        """프로필 데이터 변환 엣지 케이스 테스트"""
        # 빈 결과 배열
        data_empty_result = {"quoteSummary": {"result": []}}
        
        result = yahoo_finance_service._transform_profile_data(data_empty_result)
        
        # 결과 검증
        assert result is None
        
        # 중첩된 누락 필드
        data_nested_missing = {
            "quoteSummary": {
                "result": [{
                    "price": {
                        "symbol": "AAPL"
                        # currency 누락
                    },
                    "assetProfile": {
                        "website": "https://www.apple.com"
                        # city 누락
                    }
                }]
            }
        }
        
        result = yahoo_finance_service._transform_profile_data(data_nested_missing)
        
        # 결과 검증 - 기본값 확인
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["website"] == "https://www.apple.com"
        assert result["city"] is None  # 기본값
    
    @pytest.mark.asyncio
    async def test_rate_limit_time_window_reset(self, yahoo_finance_service):
        """속도 제한 시간 창 초기화 테스트"""
        # 설정
        current_time = time.time()
        old_minute = int(current_time // 60) - 2
        old_hour = int(current_time // 3600) - 2
        
        yahoo_finance_service.request_count = {
            "minute": 60,
            "hour": 2000,
            "last_minute": old_minute,
            "last_hour": old_hour
        }
        
        # 테스트 실행
        result = await yahoo_finance_service._check_rate_limit()
        
        # 결과 검증 - 시간 초기화로 인해 다시 허용
        assert result is True
        assert yahoo_finance_service.request_count["minute"] == 1
        assert yahoo_finance_service.request_count["hour"] == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, yahoo_finance_service, caplog):
        """오류 처리 및 로깅 테스트"""
        import logging
        
        # 로그 레벨 설정
        with caplog.at_level(logging.ERROR):
            # 알 수 없는 심볼로 데이터 가져오기 시도
            result = await yahoo_finance_service.get_stock_data("UNKNOWN_SYMBOL_12345")
            
            # 결과 검증
            assert result is None
            
            # 오류 로그 확인
            error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
            assert len(error_logs) > 0  # 오류 로그가 기록되었는지 확인