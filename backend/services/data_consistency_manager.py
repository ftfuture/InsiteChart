"""
Data consistency management service for ensuring data integrity across the platform.

This service provides strategies for maintaining data consistency between
different data sources and handling eventual consistency scenarios.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import json
import hashlib

from ..models.unified_models import UnifiedStockData, SentimentSource


class DataConsistencyStrategy(ABC):
    """Data consistency strategy interface."""
    
    @abstractmethod
    async def ensure_consistency(self, symbol: str) -> bool:
        """Ensure data consistency for a given symbol."""
        pass


class EventualConsistencyStrategy(DataConsistencyStrategy):
    """Eventual consistency strategy for distributed data sources."""
    
    def __init__(self, max_delay_seconds: int = 300):
        self.max_delay = timedelta(seconds=max_delay_seconds)
        self.logger = logging.getLogger(__name__)
    
    async def ensure_consistency(self, symbol: str) -> bool:
        """Ensure eventual consistency (asynchronous approach)."""
        try:
            # Get source timestamps from different data sources
            source_timestamps = await self._get_source_timestamps(symbol)
            
            if not source_timestamps:
                return True  # No data means consistent
            
            # Find time difference between oldest and newest data
            oldest = min(source_timestamps.values())
            newest = max(source_timestamps.values())
            
            if newest - oldest > self.max_delay:
                self.logger.warning(
                    f"Data consistency issue for {symbol}: "
                    f"time difference {newest - oldest} exceeds threshold {self.max_delay}"
                )
                
                # Trigger data synchronization
                await self._trigger_data_sync(symbol)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking consistency for {symbol}: {str(e)}")
            return False
    
    async def _get_source_timestamps(self, symbol: str) -> Dict[str, datetime]:
        """Get timestamps from different data sources."""
        # In a real implementation, this would query actual data sources
        # Here we return simulated data
        return {
            "yahoo_finance": datetime.now(timezone.utc) - timedelta(minutes=5),
            "reddit": datetime.now(timezone.utc) - timedelta(minutes=2),
            "twitter": datetime.now(timezone.utc) - timedelta(minutes=3)
        }
    
    async def _trigger_data_sync(self, symbol: str):
        """Trigger data synchronization for a symbol."""
        # In a real implementation, this would trigger background sync
        self.logger.info(f"Triggering data sync for {symbol}")


class StrongConsistencyStrategy(DataConsistencyStrategy):
    """Strong consistency strategy with distributed locking."""
    
    def __init__(self, lock_timeout_seconds: int = 30):
        self.lock_timeout = timedelta(seconds=lock_timeout_seconds)
        self.data_locks = {}
        self.logger = logging.getLogger(__name__)
    
    async def ensure_consistency(self, symbol: str) -> bool:
        """Ensure strong consistency (synchronous approach)."""
        try:
            # Acquire distributed lock
            lock_acquired = await self._acquire_lock(symbol)
            
            if not lock_acquired:
                self.logger.warning(f"Could not acquire lock for {symbol}")
                return False
            
            # Check and restore consistency
            consistency_restored = await self._restore_consistency(symbol)
            
            # Release lock
            await self._release_lock(symbol)
            
            return consistency_restored
            
        except Exception as e:
            self.logger.error(f"Error ensuring consistency for {symbol}: {str(e)}")
            await self._release_lock(symbol)
            return False
    
    async def _acquire_lock(self, symbol: str) -> bool:
        """Acquire distributed lock for a symbol."""
        # In a real implementation, this would use Redis or similar
        if symbol in self.data_locks:
            if datetime.now(timezone.utc) - self.data_locks[symbol] > self.lock_timeout:
                del self.data_locks[symbol]
            else:
                return False
        
        self.data_locks[symbol] = datetime.now(timezone.utc)
        return True
    
    async def _release_lock(self, symbol: str):
        """Release distributed lock for a symbol."""
        if symbol in self.data_locks:
            del self.data_locks[symbol]
    
    async def _restore_consistency(self, symbol: str) -> bool:
        """Restore data consistency for a symbol."""
        # In a real implementation, this would fetch latest data from all sources
        # and resolve conflicts
        self.logger.info(f"Restoring consistency for {symbol}")
        return True


class DataConsistencyManager:
    """Data consistency manager for unified stock data."""
    
    def __init__(self, strategy: DataConsistencyStrategy):
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
        self._consistency_cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def check_consistency(self, symbol: str) -> bool:
        """Check data consistency for a symbol."""
        # Check cache first
        if symbol in self._consistency_cache:
            cached_result, cached_time = self._consistency_cache[symbol]
            if datetime.now(timezone.utc) - cached_time < self._cache_ttl:
                return cached_result
        
        # Use strategy to check consistency
        result = await self.strategy.ensure_consistency(symbol)
        
        # Cache result
        self._consistency_cache[symbol] = (result, datetime.now(timezone.utc))
        
        return result
    
    async def batch_check_consistency(self, symbols: List[str]) -> Dict[str, bool]:
        """Check consistency for multiple symbols in parallel."""
        results = {}
        
        # Check consistency in parallel
        tasks = [self.check_consistency(symbol) for symbol in symbols]
        consistency_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, result in zip(symbols, consistency_results):
            if isinstance(result, Exception):
                self.logger.error(f"Error checking consistency for {symbol}: {str(result)}")
                results[symbol] = False
            else:
                results[symbol] = result
        
        return results
    
    async def validate_data_integrity(self, data: UnifiedStockData) -> Dict[str, Any]:
        """Validate data integrity of unified stock data."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 1.0
        }
        
        try:
            # Basic validation
            if not data.symbol:
                validation_result['errors'].append("Symbol is required")
                validation_result['is_valid'] = False
            
            if not data.company_name:
                validation_result['errors'].append("Company name is required")
                validation_result['is_valid'] = False
            
            # Price validation
            if data.current_price is not None and data.current_price <= 0:
                validation_result['errors'].append("Current price must be positive")
                validation_result['is_valid'] = False
            
            if (data.previous_close is not None and data.day_change is not None and 
                abs(data.day_change - (data.current_price - data.previous_close)) > 0.01):
                validation_result['warnings'].append("Day change doesn't match price difference")
            
            # Sentiment validation
            if data.overall_sentiment is not None:
                if not -100 <= data.overall_sentiment <= 100:
                    validation_result['errors'].append("Overall sentiment must be between -100 and 100")
                    validation_result['is_valid'] = False
            
            # Validate sentiment sources
            for source, score in data.sentiment_sources.items():
                if not -100 <= score <= 100:
                    validation_result['errors'].append(f"Sentiment score for {source} must be between -100 and 100")
                    validation_result['is_valid'] = False
            
            # Check for missing data
            missing_fields = []
            if not data.sector:
                missing_fields.append("sector")
            if not data.industry:
                missing_fields.append("industry")
            
            if missing_fields:
                validation_result['warnings'].append(f"Missing fields: {', '.join(missing_fields)}")
            
            # Calculate quality score
            validation_result['quality_score'] = self._calculate_quality_score(data, validation_result)
            
        except Exception as e:
            self.logger.error(f"Error validating data integrity: {str(e)}")
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['is_valid'] = False
            validation_result['quality_score'] = 0.0
        
        return validation_result
    
    def _calculate_quality_score(self, data: UnifiedStockData, validation_result: Dict[str, Any]) -> float:
        """Calculate data quality score (0.0 to 1.0)."""
        score = 1.0
        
        # Deduct for errors
        score -= len(validation_result['errors']) * 0.2
        
        # Deduct for warnings
        score -= len(validation_result['warnings']) * 0.1
        
        # Bonus for complete data
        completeness_bonus = 0.0
        
        # Price data completeness
        price_fields = [
            data.current_price, data.previous_close, data.day_high, 
            data.day_low, data.volume
        ]
        price_completeness = sum(1 for field in price_fields if field is not None) / len(price_fields)
        completeness_bonus += price_completeness * 0.2
        
        # Financial metrics completeness
        financial_fields = [
            data.pe_ratio, data.dividend_yield, data.beta, data.eps
        ]
        financial_completeness = sum(1 for field in financial_fields if field is not None) / len(financial_fields)
        completeness_bonus += financial_completeness * 0.1
        
        # Sentiment data completeness
        if data.overall_sentiment is not None:
            completeness_bonus += 0.1
        
        # Add completeness bonus
        score = min(1.0, score + completeness_bonus)
        
        return max(0.0, score)
    
    async def resolve_conflicts(self, data_sources: List[Dict[str, Any]]) -> UnifiedStockData:
        """Resolve conflicts between different data sources."""
        if not data_sources:
            raise ValueError("No data sources provided")
        
        if len(data_sources) == 1:
            return UnifiedStockData.from_dict(data_sources[0])
        
        # Sort by data quality score and timestamp
        sorted_sources = sorted(
            data_sources,
            key=lambda x: (x.get('data_quality_score', 0.5), x.get('last_updated', datetime.min)),
            reverse=True
        )
        
        # Use highest quality source as base
        base_data = UnifiedStockData.from_dict(sorted_sources[0])
        
        # Merge with other sources
        for source_data in sorted_sources[1:]:
            other_data = UnifiedStockData.from_dict(source_data)
            base_data = self._merge_conflicting_data(base_data, other_data)
        
        return base_data
    
    def _merge_conflicting_data(self, base: UnifiedStockData, other: UnifiedStockData) -> UnifiedStockData:
        """Merge conflicting data from two sources."""
        # Use more recent data
        if other.last_updated > base.last_updated:
            # Prefer other data for recent fields
            if other.current_price is not None:
                base.current_price = other.current_price
            if other.volume is not None:
                base.volume = other.volume
            if other.overall_sentiment is not None:
                base.overall_sentiment = other.overall_sentiment
        
        # Merge sentiment sources
        for source, score in other.sentiment_sources.items():
            base.sentiment_sources[source] = score
        
        # Merge data sources
        base.data_sources = list(set(base.data_sources + other.data_sources))
        
        # Update last_updated
        base.last_updated = max(base.last_updated, other.last_updated)
        
        # Update data quality score (use average)
        base.data_quality_score = (base.data_quality_score + other.data_quality_score) / 2
        
        return base
    
    def generate_data_hash(self, data: UnifiedStockData) -> str:
        """Generate hash for data integrity verification."""
        # Create a deterministic representation of the data
        data_dict = {
            'symbol': data.symbol,
            'current_price': data.current_price,
            'previous_close': data.previous_close,
            'overall_sentiment': data.overall_sentiment,
            'last_updated': data.last_updated.isoformat() if data.last_updated else None
        }
        
        # Generate hash
        data_str = json.dumps(data_dict, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def verify_data_integrity(self, data: UnifiedStockData, expected_hash: str) -> bool:
        """Verify data integrity using hash comparison."""
        actual_hash = self.generate_data_hash(data)
        return actual_hash == expected_hash