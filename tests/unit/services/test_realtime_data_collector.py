"""
RealtimeDataCollector 단위 테스트

실시간 데이터 수집기의 기능을 테스트합니다.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from backend.services.realtime_data_collector import (
    RealtimeDataCollector,
    DataSource,
    DataPoint,
    CollectionConfig,
    CollectionStatus,
    DataCollectorError
)


class TestDataPoint:
    """DataPoint 모델 테스트 클래스"""
    
    def test_data_point_creation(self):
        """DataPoint 생성 테스트"""
        timestamp = datetime.utcnow()
        data_point = DataPoint(
            symbol="AAPL",
            source=DataSource.YAHOO_FINANCE,
            data_type="stock_price",
            value=150.25,
            timestamp=timestamp,
            metadata={"volume": 1000000, "currency": "USD"}
        )
        
        assert data_point.symbol == "AAPL"
        assert data_point.source == DataSource.YAHOO_FINANCE
        assert data_point.data_type == "stock_price"
        assert data_point.value == 150.25
        assert data_point.timestamp == timestamp
        assert data_point.metadata["volume"] == 1000000
        assert data_point.metadata["currency"] == "USD"
    
    def test_data_point_to_dict(self):
        """DataPoint 딕셔너리 변환 테스트"""
        timestamp = datetime.utcnow()
        data_point = DataPoint(
            symbol="AAPL",
            source=DataSource.YAHOO_FINANCE,
            data_type="stock_price",
            value=150.25,
            timestamp=timestamp,
            metadata={"volume": 1000000}
        )
        
        data_dict = data_point.to_dict()
        
        assert data_dict["symbol"] == "AAPL"
        assert data_dict["source"] == "yahoo_finance"
        assert data_dict["data_type"] == "stock_price"
        assert data_dict["value"] == 150.25
        assert data_dict["timestamp"] == timestamp.isoformat()
        assert data_dict["metadata"]["volume"] == 1000000
    
    def test_data_point_from_dict(self):
        """딕셔너리로부터 DataPoint 생성 테스트"""
        timestamp = datetime.utcnow()
        data_dict = {
            "symbol": "AAPL",
            "source": "yahoo_finance",
            "data_type": "stock_price",
            "value": 150.25,
            "timestamp": timestamp.isoformat(),
            "metadata": {"volume": 1000000}
        }
        
        data_point = DataPoint.from_dict(data_dict)
        
        assert data_point.symbol == "AAPL"
        assert data_point.source == DataSource.YAHOO_FINANCE
        assert data_point.data_type == "stock_price"
        assert data_point.value == 150.25
        assert data_point.metadata["volume"] == 1000000


class TestCollectionConfig:
    """CollectionConfig 모델 테스트 클래스"""
    
    def test_collection_config_creation(self):
        """CollectionConfig 생성 테스트"""
        config = CollectionConfig(
            symbols=["AAPL", "GOOGL", "MSFT"],
            data_types=["stock_price", "volume"],
            sources=[DataSource.YAHOO_FINANCE, DataSource.ALPHA_VANTAGE],
            interval=5,  # 5초 간격
            batch_size=10,
            retry_attempts=3,
            retry_delay=1.0,
            timeout=10.0
        )
        
        assert "AAPL" in config.symbols
        assert "GOOGL" in config.symbols
        assert "MSFT" in config.symbols
        assert "stock_price" in config.data_types
        assert "volume" in config.data_types
        assert DataSource.YAHOO_FINANCE in config.sources
        assert DataSource.ALPHA_VANTAGE in config.sources
        assert config.interval == 5
        assert config.batch_size == 10
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
        assert config.timeout == 10.0
    
    def test_collection_config_defaults(self):
        """기본값 CollectionConfig 생성 테스트"""
        config = CollectionConfig(
            symbols=["AAPL"],
            data_types=["stock_price"],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        assert config.symbols == ["AAPL"]
        assert config.data_types == ["stock_price"]
        assert config.sources == [DataSource.YAHOO_FINANCE]
        assert config.interval == 60  # 기본 간격
        assert config.batch_size == 100  # 기본 배치 크기
        assert config.retry_attempts == 3  # 기본 재시도 횟수
        assert config.retry_delay == 1.0  # 기본 재시도 지연
        assert config.timeout == 10.0  # 기본 타임아웃


class TestRealtimeDataCollector:
    """RealtimeDataCollector 테스트 클래스"""
    
    @pytest.fixture
    def mock_data_sources(self):
        """모의 데이터 소스"""
        sources = {
            DataSource.YAHOO_FINANCE: AsyncMock(),
            DataSource.ALPHA_VANTAGE: AsyncMock()
        }
        
        # Yahoo Finance 모의 데이터
        sources[DataSource.YAHOO_FINANCE].get_realtime_data.return_value = {
            "symbol": "AAPL",
            "price": 150.25,
            "volume": 1000000,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Alpha Vantage 모의 데이터
        sources[DataSource.ALPHA_VANTAGE].get_realtime_data.return_value = {
            "symbol": "AAPL",
            "price": 150.30,
            "volume": 1000500,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return sources
    
    @pytest.fixture
    def mock_event_bus(self):
        """모의 이벤트 버스"""
        event_bus = AsyncMock()
        event_bus.publish.return_value = True
        return event_bus
    
    @pytest.fixture
    def collection_config(self):
        """수집 설정"""
        return CollectionConfig(
            symbols=["AAPL", "GOOGL"],
            data_types=["stock_price", "volume"],
            sources=[DataSource.YAHOO_FINANCE],
            interval=5,
            batch_size=10
        )
    
    @pytest.fixture
    def data_collector(self, mock_data_sources, mock_event_bus, collection_config):
        """RealtimeDataCollector 인스턴스"""
        return RealtimeDataCollector(
            config=collection_config,
            data_sources=mock_data_sources,
            event_bus=mock_event_bus
        )
    
    @pytest.mark.asyncio
    async def test_start_collection(self, data_collector):
        """데이터 수집 시작 테스트"""
        # 테스트 실행
        await data_collector.start()
        
        # 결과 검증
        assert data_collector.status == CollectionStatus.RUNNING
        assert data_collector.collection_task is not None
    
    @pytest.mark.asyncio
    async def test_stop_collection(self, data_collector):
        """데이터 수집 중지 테스트"""
        # 설정
        await data_collector.start()
        
        # 테스트 실행
        await data_collector.stop()
        
        # 결과 검증
        assert data_collector.status == CollectionStatus.STOPPED
        assert data_collector.collection_task is None
    
    @pytest.mark.asyncio
    async def test_collect_data_single_source(self, data_collector, mock_data_sources):
        """단일 소스 데이터 수집 테스트"""
        # 테스트 실행
        data_points = await data_collector._collect_data("AAPL", ["stock_price"], [DataSource.YAHOO_FINANCE])
        
        # 결과 검증
        assert len(data_points) == 1
        assert data_points[0].symbol == "AAPL"
        assert data_points[0].source == DataSource.YAHOO_FINANCE
        assert data_points[0].data_type == "stock_price"
        assert data_points[0].value == 150.25
        
        # 모의 호출 검증
        mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.assert_called_once_with(
            "AAPL", ["stock_price"]
        )
    
    @pytest.mark.asyncio
    async def test_collect_data_multiple_sources(self, data_collector, mock_data_sources):
        """다중 소스 데이터 수집 테스트"""
        # 설정
        config = CollectionConfig(
            symbols=["AAPL"],
            data_types=["stock_price"],
            sources=[DataSource.YAHOO_FINANCE, DataSource.ALPHA_VANTAGE]
        )
        data_collector.config = config
        
        # 테스트 실행
        data_points = await data_collector._collect_data("AAPL", ["stock_price"], config.sources)
        
        # 결과 검증
        assert len(data_points) == 2
        assert data_points[0].symbol == "AAPL"
        assert data_points[1].symbol == "AAPL"
        
        # Yahoo Finance 데이터
        yahoo_data = next(dp for dp in data_points if dp.source == DataSource.YAHOO_FINANCE)
        assert yahoo_data.value == 150.25
        
        # Alpha Vantage 데이터
        alpha_data = next(dp for dp in data_points if dp.source == DataSource.ALPHA_VANTAGE)
        assert alpha_data.value == 150.30
        
        # 모의 호출 검증
        mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.assert_called_once()
        mock_data_sources[DataSource.ALPHA_VANTAGE].get_realtime_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_data_source_error(self, data_collector, mock_data_sources):
        """데이터 소스 오류 수집 테스트"""
        # 설정
        mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.side_effect = Exception("API error")
        
        # 테스트 실행
        data_points = await data_collector._collect_data("AAPL", ["stock_price"], [DataSource.YAHOO_FINANCE])
        
        # 결과 검증
        assert len(data_points) == 0  # 오류 발생 시 데이터 포인트 없음
    
    @pytest.mark.asyncio
    async def test_collect_data_timeout(self, data_collector, mock_data_sources):
        """데이터 수집 타임아웃 테스트"""
        # 설정
        mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.side_effect = asyncio.TimeoutError("Timeout")
        
        # 테스트 실행
        data_points = await data_collector._collect_data("AAPL", ["stock_price"], [DataSource.YAHOO_FINANCE])
        
        # 결과 검증
        assert len(data_points) == 0  # 타임아웃 시 데이터 포인트 없음
    
    @pytest.mark.asyncio
    async def test_collection_loop(self, data_collector, mock_data_sources):
        """수집 루프 테스트"""
        # 설정
        await data_collector.start()
        
        # 테스트 실행 (짧게 실행 후 중지)
        await asyncio.sleep(0.1)
        await data_collector.stop()
        
        # 결과 검증
        assert data_collector.status == CollectionStatus.STOPPED
        
        # 모의 호출 검증 (최소 한 번은 호출되어야 함)
        assert mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_publish_data_points(self, data_collector, mock_event_bus):
        """데이터 포인트 발행 테스트"""
        # 설정
        data_points = [
            DataPoint(
                symbol="AAPL",
                source=DataSource.YAHOO_FINANCE,
                data_type="stock_price",
                value=150.25,
                timestamp=datetime.utcnow()
            ),
            DataPoint(
                symbol="GOOGL",
                source=DataSource.YAHOO_FINANCE,
                data_type="stock_price",
                value=2500.50,
                timestamp=datetime.utcnow()
            )
        ]
        
        # 테스트 실행
        await data_collector._publish_data_points(data_points)
        
        # 결과 검증
        assert mock_event_bus.publish.call_count == 2
        
        # 첫 번째 데이터 포인트 발행 검증
        first_call = mock_event_bus.publish.call_args_list[0]
        assert first_call[0][0] == "data_collected"
        assert first_call[0][1].symbol == "AAPL"
        
        # 두 번째 데이터 포인트 발행 검증
        second_call = mock_event_bus.publish.call_args_list[1]
        assert second_call[0][0] == "data_collected"
        assert second_call[0][1].symbol == "GOOGL"
    
    @pytest.mark.asyncio
    async def test_publish_data_points_with_error(self, data_collector, mock_event_bus):
        """데이터 포인트 발행 오류 테스트"""
        # 설정
        mock_event_bus.publish.side_effect = Exception("Event bus error")
        
        data_points = [
            DataPoint(
                symbol="AAPL",
                source=DataSource.YAHOO_FINANCE,
                data_type="stock_price",
                value=150.25,
                timestamp=datetime.utcnow()
            )
        ]
        
        # 테스트 실행 (예외가 발생하지 않아야 함)
        await data_collector._publish_data_points(data_points)
        
        # 결과 검증
        mock_event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_collection_statistics(self, data_collector):
        """수집 통계 조회 테스트"""
        # 설정
        data_collector.total_collections = 100
        data_collector.successful_collections = 95
        data_collector.failed_collections = 5
        data_collector.data_points_collected = 950
        data_collector.start_time = datetime.utcnow() - timedelta(hours=1)
        
        # 테스트 실행
        stats = await data_collector.get_collection_statistics()
        
        # 결과 검증
        assert stats["total_collections"] == 100
        assert stats["successful_collections"] == 95
        assert stats["failed_collections"] == 5
        assert stats["success_rate"] == 95.0
        assert stats["data_points_collected"] == 950
        assert stats["status"] == CollectionStatus.STOPPED.value
        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_update_config(self, data_collector):
        """설정 업데이트 테스트"""
        # 설정
        new_config = CollectionConfig(
            symbols=["MSFT", "TSLA"],
            data_types=["stock_price"],
            sources=[DataSource.ALPHA_VANTAGE],
            interval=10
        )
        
        # 테스트 실행
        await data_collector.update_config(new_config)
        
        # 결과 검증
        assert data_collector.config.symbols == ["MSFT", "TSLA"]
        assert data_collector.config.data_types == ["stock_price"]
        assert data_collector.config.sources == [DataSource.ALPHA_VANTAGE]
        assert data_collector.config.interval == 10
    
    @pytest.mark.asyncio
    async def test_update_config_while_running(self, data_collector):
        """실행 중 설정 업데이트 테스트"""
        # 설정
        await data_collector.start()
        
        new_config = CollectionConfig(
            symbols=["MSFT"],
            data_types=["stock_price"],
            sources=[DataSource.YAHOO_FINANCE],
            interval=15
        )
        
        # 테스트 실행
        await data_collector.update_config(new_config)
        
        # 결과 검증
        assert data_collector.config.symbols == ["MSFT"]
        assert data_collector.config.interval == 15
        assert data_collector.status == CollectionStatus.RUNNING  # 계속 실행 중
        
        # 정리
        await data_collector.stop()
    
    @pytest.mark.asyncio
    async def test_add_symbol(self, data_collector):
        """심볼 추가 테스트"""
        # 테스트 실행
        await data_collector.add_symbol("MSFT")
        
        # 결과 검증
        assert "MSFT" in data_collector.config.symbols
        assert len(data_collector.config.symbols) == 3  # AAPL, GOOGL, MSFT
    
    @pytest.mark.asyncio
    async def test_remove_symbol(self, data_collector):
        """심볼 제거 테스트"""
        # 테스트 실행
        await data_collector.remove_symbol("GOOGL")
        
        # 결과 검증
        assert "GOOGL" not in data_collector.config.symbols
        assert len(data_collector.config.symbols) == 1  # AAPL만 남음
    
    @pytest.mark.asyncio
    async def test_add_data_type(self, data_collector):
        """데이터 타입 추가 테스트"""
        # 테스트 실행
        await data_collector.add_data_type("market_cap")
        
        # 결과 검증
        assert "market_cap" in data_collector.config.data_types
        assert len(data_collector.config.data_types) == 3  # stock_price, volume, market_cap
    
    @pytest.mark.asyncio
    async def test_remove_data_type(self, data_collector):
        """데이터 타입 제거 테스트"""
        # 테스트 실행
        await data_collector.remove_data_type("volume")
        
        # 결과 검증
        assert "volume" not in data_collector.config.data_types
        assert len(data_collector.config.data_types) == 1  # stock_price만 남음
    
    @pytest.mark.asyncio
    async def test_retry_collection(self, data_collector, mock_data_sources):
        """수집 재시도 테스트"""
        # 설정
        call_count = 0
        
        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary error")
            return {"symbol": "AAPL", "price": 150.25}
        
        mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.side_effect = failing_then_success
        
        # 테스트 실행
        data_points = await data_collector._collect_data_with_retry("AAPL", ["stock_price"], [DataSource.YAHOO_FINANCE])
        
        # 결과 검증
        assert len(data_points) == 1  # 성공적으로 데이터 수집
        assert call_count == 3  # 2번 실패 후 1번 성공
    
    @pytest.mark.asyncio
    async def test_retry_collection_max_attempts(self, data_collector, mock_data_sources):
        """최대 재시도 횟수 테스트"""
        # 설정
        mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.side_effect = Exception("Persistent error")
        
        # 테스트 실행
        data_points = await data_collector._collect_data_with_retry("AAPL", ["stock_price"], [DataSource.YAHOO_FINANCE])
        
        # 결과 검증
        assert len(data_points) == 0  # 모든 재시도 실패
        
        # 재시도 횟수 검증 (기본값 3번)
        assert mock_data_sources[DataSource.YAHOO_FINANCE].get_realtime_data.call_count == 3
    
    @pytest.mark.asyncio
    async def test_validate_config_valid(self, data_collector):
        """유효한 설정 검증 테스트"""
        # 설정
        config = CollectionConfig(
            symbols=["AAPL"],
            data_types=["stock_price"],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        is_valid, errors = data_collector._validate_config(config)
        
        # 결과 검증
        assert is_valid is True
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_config_empty_symbols(self, data_collector):
        """빈 심볼 설정 검증 테스트"""
        # 설정
        config = CollectionConfig(
            symbols=[],
            data_types=["stock_price"],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        is_valid, errors = data_collector._validate_config(config)
        
        # 결과 검증
        assert is_valid is False
        assert len(errors) > 0
        assert "At least one symbol is required" in errors[0]
    
    @pytest.mark.asyncio
    async def test_validate_config_empty_data_types(self, data_collector):
        """빈 데이터 타입 설정 검증 테스트"""
        # 설정
        config = CollectionConfig(
            symbols=["AAPL"],
            data_types=[],
            sources=[DataSource.YAHOO_FINANCE]
        )
        
        # 테스트 실행
        is_valid, errors = data_collector._validate_config(config)
        
        # 결과 검증
        assert is_valid is False
        assert len(errors) > 0
        assert "At least one data type is required" in errors[0]
        
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_interval(self, data_collector):
        """잘못된 간격 설정 검증 테스트"""
        # 설정
        config = CollectionConfig(
            symbols=["AAPL"],
            data_types=["stock_price"],
            sources=[DataSource.YAHOO_FINANCE],
            interval=0  # 0 간격은 유효하지 않음
        )
        
        # 테스트 실행
        is_valid, errors = data_collector._validate_config(config)
        
        # 결과 검증
        assert is_valid is False
        assert len(errors) > 0
        assert "Interval must be greater than 0" in errors[0]
    
    def test_data_collector_error(self):
        """DataCollectorError 테스트"""
        # 테스트 실행
        error = DataCollectorError("Test error message")
        
        # 결과 검증
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    @pytest.mark.asyncio
    async def test_get_active_symbols(self, data_collector):
        """활성 심볼 조회 테스트"""
        # 테스트 실행
        symbols = await data_collector.get_active_symbols()
        
        # 결과 검증
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
        assert len(symbols) == 2
    
    @pytest.mark.asyncio
    async def test_get_data_sources_status(self, data_collector, mock_data_sources):
        """데이터 소스 상태 조회 테스트"""
        # 설정
        mock_data_sources[DataSource.YAHOO_FINANCE].is_healthy.return_value = True
        mock_data_sources[DataSource.ALPHA_VANTAGE].is_healthy.return_value = False
        
        # 테스트 실행
        status = await data_collector.get_data_sources_status()
        
        # 결과 검증
        assert status[DataSource.YAHOO_FINANCE.value] is True
        assert status[DataSource.ALPHA_VANTAGE.value] is False