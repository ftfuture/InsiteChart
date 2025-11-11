"""
Unit tests for TimescaleDB Service.

This module tests TimescaleDB service functionality including
hypertable management, partitioning, compression, and
retention policies.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from backend.services.timescale_service import (
    TimescaleService,
    HypertableConfig,
    DataPartition,
    CompressionPolicy,
    RetentionPolicy
)
from backend.cache.unified_cache import UnifiedCacheManager


class TestTimescaleService:
    """Test cases for TimescaleService."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create mock cache manager."""
        return Mock(spec=UnifiedCacheManager)
    
    @pytest.fixture
    def timescale_service(self, cache_manager):
        """Create TimescaleDB service instance."""
        return TimescaleService(cache_manager)
    
    @pytest.mark.asyncio
    async def test_initialize_service(self, timescale_service):
        """Test service initialization."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Initialize service
        await timescale_service.initialize()
        
        # Verify initialization
        assert timescale_service.hypertables == {}
        assert timescale_service.partitions == {}
        assert timescale_service.compression_policies == {}
        assert timescale_service.retention_policies == {}
    
    @pytest.mark.asyncio
    async def test_create_hypertable(self, timescale_service):
        """Test hypertable creation."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.execute = AsyncMock()
            
            # Create hypertable config
            config = HypertableConfig(
                table_name="stock_data",
                time_column="timestamp",
                chunk_time_interval="1 day",
                compression_enabled=True,
                compression_segment_by_column="symbol",
                create_default_indexes=True,
                partitioning_column="symbol",
                partitioning_interval="1 month"
            )
            
            # Create hypertable
            result = await timescale_service.create_hypertable(config)
            
            # Verify result
            assert result["success"] is True
            assert result["table_name"] == "stock_data"
            assert "stock_data" in timescale_service.hypertables
    
    @pytest.mark.asyncio
    async def test_get_hypertables(self, timescale_service):
        """Test retrieving hypertables."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        
        # Add hypertables
        config1 = HypertableConfig(
            table_name="stock_data",
            time_column="timestamp",
            chunk_time_interval="1 day"
        )
        
        config2 = HypertableConfig(
            table_name="market_data",
            time_column="timestamp",
            chunk_time_interval="1 hour"
        )
        
        timescale_service.hypertables["stock_data"] = config1
        timescale_service.hypertables["market_data"] = config2
        
        # Get hypertables
        hypertables = await timescale_service.get_hypertables()
        
        # Verify result
        assert len(hypertables) == 2
        assert hypertables[0]["table_name"] == "stock_data"
        assert hypertables[1]["table_name"] == "market_data"
    
    @pytest.mark.asyncio
    async def test_manage_partitions(self, timescale_service):
        """Test partition management."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[
                {"partition_name": "stock_data_2023_01", "start_time": datetime(2023, 1, 1)},
                {"partition_name": "stock_data_2023_02", "start_time": datetime(2023, 2, 1)}
            ])
            mock_conn.execute = AsyncMock()
            
            # Manage partitions
            result = await timescale_service._manage_partitions("stock_data")
            
            # Verify result
            assert result["success"] is True
            assert result["partitions_created"] >= 0
            assert result["partitions_dropped"] >= 0
    
    @pytest.mark.asyncio
    async def test_apply_compression_policy(self, timescale_service):
        """Test compression policy application."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.execute = AsyncMock()
            
            # Create compression policy
            policy = CompressionPolicy(
                table_name="stock_data",
                segment_by_column="symbol",
                compression_method="gzip",
                schedule_interval="1 day"
            )
            
            # Apply compression policy
            result = await timescale_service.apply_compression_policy(policy)
            
            # Verify result
            assert result["success"] is True
            assert result["table_name"] == "stock_data"
            assert result["compression_method"] == "gzip"
    
    @pytest.mark.asyncio
    async def test_apply_retention_policy(self, timescale_service):
        """Test retention policy application."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.execute = AsyncMock()
            
            # Create retention policy
            policy = RetentionPolicy(
                table_name="stock_data",
                retention_interval="1 year",
                drop_cascades=True
            )
            
            # Apply retention policy
            result = await timescale_service.apply_retention_policy(policy)
            
            # Verify result
            assert result["success"] is True
            assert result["table_name"] == "stock_data"
            assert result["retention_interval"] == "1 year"
    
    @pytest.mark.asyncio
    async def test_insert_time_series_data(self, timescale_service):
        """Test time series data insertion."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[{"id": 1}])
            mock_conn.execute = AsyncMock()
            mock_conn.executemany = AsyncMock()
            
            # Prepare data
            data = [
                {
                    "timestamp": datetime.utcnow(),
                    "symbol": "AAPL",
                    "price": 150.25,
                    "volume": 1000000,
                    "market_cap": 2500000000000
                },
                {
                    "timestamp": datetime.utcnow() + timedelta(minutes=1),
                    "symbol": "GOOGL",
                    "price": 2800.50,
                    "volume": 500000,
                    "market_cap": 1800000000000
                }
            ]
            
            # Insert data
            result = await timescale_service.insert_time_series_data("stock_data", data)
            
            # Verify result
            assert result["success"] is True
            assert result["rows_inserted"] == 2
            assert result["table_name"] == "stock_data"
    
    @pytest.mark.asyncio
    async def test_query_time_series_data(self, timescale_service):
        """Test time series data querying."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[
                {
                    "timestamp": datetime.utcnow() - timedelta(hours=1),
                    "symbol": "AAPL",
                    "price": 150.25,
                    "volume": 1000000
                },
                {
                    "timestamp": datetime.utcnow() - timedelta(minutes=30),
                    "symbol": "AAPL",
                    "price": 150.50,
                    "volume": 800000
                }
            ])
            
            # Query parameters
            start_time = datetime.utcnow() - timedelta(hours=2)
            end_time = datetime.utcnow()
            symbols = ["AAPL"]
            limit = 100
            
            # Query data
            result = await timescale_service.query_time_series_data(
                table_name="stock_data",
                start_time=start_time,
                end_time=end_time,
                symbols=symbols,
                limit=limit
            )
            
            # Verify result
            assert result["success"] is True
            assert result["row_count"] == 2
            assert len(result["data"]) == 2
            assert result["data"][0]["symbol"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_optimize_table(self, timescale_service):
        """Test table optimization."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[
                {"table_name": "stock_data", "size_mb": 1000, "compression_ratio": 0.7}
            ])
            mock_conn.execute = AsyncMock()
            
            # Optimize table
            result = await timescale_service.optimize_table("stock_data")
            
            # Verify result
            assert result["success"] is True
            assert result["table_name"] == "stock_data"
            assert "compression_applied" in result
            assert "reindex_performed" in result
            assert "statistics_updated" in result
    
    @pytest.mark.asyncio
    async def test_get_table_metrics(self, timescale_service):
        """Test table metrics retrieval."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[
                {
                    "table_name": "stock_data",
                    "row_count": 1000000,
                    "size_mb": 2500,
                    "compression_ratio": 0.65,
                    "partition_count": 12,
                    "last_compression": datetime.utcnow() - timedelta(hours=6)
                }
            ])
            
            # Get table metrics
            metrics = await timescale_service.get_table_metrics("stock_data")
            
            # Verify result
            assert metrics["table_name"] == "stock_data"
            assert metrics["row_count"] == 1000000
            assert metrics["size_mb"] == 2500
            assert metrics["compression_ratio"] == 0.65
            assert metrics["partition_count"] == 12
    
    @pytest.mark.asyncio
    async def test_drop_hypertable(self, timescale_service):
        """Test hypertable dropping."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.execute = AsyncMock()
            
            # Add hypertable to service
            config = HypertableConfig(
                table_name="test_table",
                time_column="timestamp"
            )
            timescale_service.hypertables["test_table"] = config
            
            # Drop hypertable
            result = await timescale_service.drop_hypertable("test_table")
            
            # Verify result
            assert result["success"] is True
            assert result["table_name"] == "test_table"
            assert "test_table" not in timescale_service.hypertables
    
    @pytest.mark.asyncio
    async def test_backup_hypertable(self, timescale_service):
        """Test hypertable backup."""
        # Mock cache operations
        timescale_service.cache_manager.get = AsyncMock(return_value={})
        timescale_service.cache_manager.set = AsyncMock()
        
        # Mock database operations
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.execute = AsyncMock()
            
            # Backup hypertable
            result = await timescale_service.backup_hypertable(
                table_name="stock_data",
                backup_path="/backups/stock_data_backup.sql"
            )
            
            # Verify result
            assert result["success"] is True
            assert result["table_name"] == "stock_data"
            assert result["backup_path"] == "/backups/stock_data_backup.sql"
            assert "backup_size" in result
            assert "backup_duration" in result
    
    def test_hypertable_config_serialization(self, timescale_service):
        """Test HypertableConfig serialization."""
        config = HypertableConfig(
            table_name="stock_data",
            time_column="timestamp",
            chunk_time_interval="1 day",
            compression_enabled=True,
            compression_segment_by_column="symbol",
            create_default_indexes=True,
            partitioning_column="symbol",
            partitioning_interval="1 month",
            retention_interval="1 year"
        )
        
        # Convert to dict
        config_dict = config.to_dict()
        
        # Verify serialization
        assert config_dict["table_name"] == "stock_data"
        assert config_dict["time_column"] == "timestamp"
        assert config_dict["chunk_time_interval"] == "1 day"
        assert config_dict["compression_enabled"] is True
        assert config_dict["compression_segment_by_column"] == "symbol"
        assert config_dict["create_default_indexes"] is True
        assert config_dict["partitioning_column"] == "symbol"
        assert config_dict["partitioning_interval"] == "1 month"
        assert config_dict["retention_interval"] == "1 year"
    
    def test_data_partition_serialization(self, timescale_service):
        """Test DataPartition serialization."""
        partition = DataPartition(
            partition_name="stock_data_2023_01",
            table_name="stock_data",
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 2, 1),
            row_count=500000,
            size_mb=500,
            compression_ratio=0.7
        )
        
        # Convert to dict
        partition_dict = partition.to_dict()
        
        # Verify serialization
        assert partition_dict["partition_name"] == "stock_data_2023_01"
        assert partition_dict["table_name"] == "stock_data"
        assert partition_dict["row_count"] == 500000
        assert partition_dict["size_mb"] == 500
        assert partition_dict["compression_ratio"] == 0.7
    
    def test_compression_policy_serialization(self, timescale_service):
        """Test CompressionPolicy serialization."""
        policy = CompressionPolicy(
            table_name="stock_data",
            segment_by_column="symbol",
            compression_method="gzip",
            schedule_interval="1 day",
            enabled=True
        )
        
        # Convert to dict
        policy_dict = policy.to_dict()
        
        # Verify serialization
        assert policy_dict["table_name"] == "stock_data"
        assert policy_dict["segment_by_column"] == "symbol"
        assert policy_dict["compression_method"] == "gzip"
        assert policy_dict["schedule_interval"] == "1 day"
        assert policy_dict["enabled"] is True
    
    def test_retention_policy_serialization(self, timescale_service):
        """Test RetentionPolicy serialization."""
        policy = RetentionPolicy(
            table_name="stock_data",
            retention_interval="1 year",
            drop_cascades=True,
            enabled=True
        )
        
        # Convert to dict
        policy_dict = policy.to_dict()
        
        # Verify serialization
        assert policy_dict["table_name"] == "stock_data"
        assert policy_dict["retention_interval"] == "1 year"
        assert policy_dict["drop_cascades"] is True
        assert policy_dict["enabled"] is True