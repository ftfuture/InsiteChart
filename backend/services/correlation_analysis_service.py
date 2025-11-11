"""
Correlation Analysis Service for InsiteChart platform.

This service provides advanced correlation analysis and visualization capabilities
for financial instruments, including cross-asset correlation, sector analysis,
and dynamic correlation visualization.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics

from ..cache.unified_cache import UnifiedCacheManager


class CorrelationMethod(str, Enum):
    """Available correlation calculation methods."""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"
    DYNAMIC_ROLLING = "dynamic_rolling"


class VisualizationType(str, Enum):
    """Available visualization types."""
    HEATMAP = "heatmap"
    NETWORK = "network"
    SCATTER_MATRIX = "scatter_matrix"
    TIME_SERIES = "time_series"
    DENDROGRAM = "dendrogram"


@dataclass
class CorrelationResult:
    """Correlation analysis result."""
    symbol1: str
    symbol2: str
    correlation: float
    p_value: float
    method: str
    sample_size: int
    confidence_interval: Tuple[float, float]
    significance: bool
    data_period: Tuple[str, str]


@dataclass
class CorrelationMatrix:
    """Correlation matrix for multiple assets."""
    symbols: List[str]
    matrix: np.ndarray
    method: str
    data_period: Tuple[str, str]
    sample_size: int
    is_significant: np.ndarray
    p_values: np.ndarray


@dataclass
class VisualizationData:
    """Data for correlation visualization."""
    visualization_type: VisualizationType
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    config: Dict[str, Any]
    generated_at: datetime


class CorrelationAnalysisService:
    """Advanced correlation analysis and visualization service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Cache TTL settings
        self.correlation_cache_ttl = 3600  # 1 hour
        self.visualization_cache_ttl = 1800  # 30 minutes
        
        # Correlation thresholds
        self.high_correlation_threshold = 0.7
        self.medium_correlation_threshold = 0.5
        self.low_correlation_threshold = 0.3
        
        # Visualization configurations
        self.default_visualization_config = {
            "color_scheme": "RdYlBu",
            "show_values": True,
            "show_significance": True,
            "figure_size": (12, 8),
            "dpi": 100
        }
        
        self.logger.info("CorrelationAnalysisService initialized")
    
    async def calculate_correlation(
        self,
        symbol1: str,
        symbol2: str,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        period_days: int = 252,  # 1 year of trading days
        min_periods: int = 30
    ) -> CorrelationResult:
        """Calculate correlation between two financial instruments."""
        try:
            # Check cache first
            cache_key = f"correlation_{symbol1}_{symbol2}_{method.value}_{period_days}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for correlation {symbol1}-{symbol2}")
                return CorrelationResult(**cached_result)
            
            # Get price data for both symbols
            price_data1 = await self._get_price_data(symbol1, period_days)
            price_data2 = await self._get_price_data(symbol2, period_days)
            
            if not price_data1 or not price_data2:
                raise ValueError(f"Insufficient data for correlation calculation")
            
            # Align data by date
            aligned_data = self._align_data(price_data1, price_data2)
            
            if len(aligned_data) < min_periods:
                raise ValueError(f"Insufficient aligned data points: {len(aligned_data)}")
            
            # Calculate returns
            returns1 = self._calculate_returns(aligned_data[symbol1])
            returns2 = self._calculate_returns(aligned_data[symbol2])
            
            # Calculate correlation based on method
            if method == CorrelationMethod.PEARSON:
                correlation, p_value = self._pearson_correlation(returns1, returns2)
            elif method == CorrelationMethod.SPEARMAN:
                correlation, p_value = self._spearman_correlation(returns1, returns2)
            elif method == CorrelationMethod.KENDALL:
                correlation, p_value = self._kendall_correlation(returns1, returns2)
            elif method == CorrelationMethod.DYNAMIC_ROLLING:
                correlation, p_value = self._dynamic_rolling_correlation(returns1, returns2)
            else:
                raise ValueError(f"Unsupported correlation method: {method}")
            
            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(
                correlation, len(returns1)
            )
            
            # Determine significance
            significance = p_value < 0.05
            
            # Create result
            result = CorrelationResult(
                symbol1=symbol1,
                symbol2=symbol2,
                correlation=correlation,
                p_value=p_value,
                method=method.value,
                sample_size=len(returns1),
                confidence_interval=confidence_interval,
                significance=significance,
                data_period=(
                    aligned_data.index[0].strftime('%Y-%m-%d'),
                    aligned_data.index[-1].strftime('%Y-%m-%d')
                )
            )
            
            # Cache result
            await self.cache_manager.set(
                cache_key,
                result.__dict__,
                ttl=self.correlation_cache_ttl
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation: {str(e)}")
            raise
    
    async def calculate_correlation_matrix(
        self,
        symbols: List[str],
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        period_days: int = 252,
        min_periods: int = 30
    ) -> CorrelationMatrix:
        """Calculate correlation matrix for multiple symbols."""
        try:
            # Check cache first
            symbols_key = "_".join(sorted(symbols))
            cache_key = f"correlation_matrix_{symbols_key}_{method.value}_{period_days}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for correlation matrix")
                # Convert lists back to numpy arrays
                cached_result['matrix'] = np.array(cached_result['matrix'])
                cached_result['is_significant'] = np.array(cached_result['is_significant'])
                cached_result['p_values'] = np.array(cached_result['p_values'])
                return CorrelationMatrix(**cached_result)
            
            # Get price data for all symbols
            all_price_data = {}
            for symbol in symbols:
                price_data = await self._get_price_data(symbol, period_days)
                if price_data:
                    all_price_data[symbol] = price_data
            
            if len(all_price_data) < 2:
                raise ValueError("Insufficient symbols for correlation matrix")
            
            # Create aligned DataFrame
            aligned_df = self._align_multiple_data(all_price_data)
            
            if len(aligned_df) < min_periods:
                raise ValueError(f"Insufficient aligned data points: {len(aligned_df)}")
            
            # Calculate returns for all symbols
            returns_df = aligned_df.pct_change().dropna()
            
            # Calculate correlation matrix
            if method == CorrelationMethod.PEARSON:
                correlation_matrix = returns_df.corr(method='pearson')
            elif method == CorrelationMethod.SPEARMAN:
                correlation_matrix = returns_df.corr(method='spearman')
            elif method == CorrelationMethod.KENDALL:
                correlation_matrix = returns_df.corr(method='kendall')
            else:
                correlation_matrix = returns_df.corr(method='pearson')
            
            # Calculate p-values and significance
            p_values = self._calculate_p_values_matrix(returns_df)
            is_significant = p_values < 0.05
            
            # Create result
            result = CorrelationMatrix(
                symbols=list(correlation_matrix.columns),
                matrix=correlation_matrix.values,
                method=method.value,
                data_period=(
                    aligned_df.index[0].strftime('%Y-%m-%d'),
                    aligned_df.index[-1].strftime('%Y-%m-%d')
                ),
                sample_size=len(returns_df),
                is_significant=is_significant.values,
                p_values=p_values.values
            )
            
            # Cache result (convert numpy arrays to lists for JSON serialization)
            cache_data = result.__dict__.copy()
            cache_data['matrix'] = result.matrix.tolist()
            cache_data['is_significant'] = result.is_significant.tolist()
            cache_data['p_values'] = result.p_values.tolist()
            
            await self.cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.correlation_cache_ttl
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation matrix: {str(e)}")
            raise
    
    async def create_correlation_visualization(
        self,
        symbols: List[str],
        visualization_type: VisualizationType = VisualizationType.HEATMAP,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        period_days: int = 252,
        config: Optional[Dict[str, Any]] = None
    ) -> VisualizationData:
        """Create correlation visualization data."""
        try:
            # Check cache first
            symbols_key = "_".join(sorted(symbols))
            cache_key = f"viz_{visualization_type.value}_{symbols_key}_{method.value}_{period_days}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for correlation visualization")
                cached_result['generated_at'] = datetime.fromisoformat(cached_result['generated_at'])
                return VisualizationData(**cached_result)
            
            # Get correlation matrix
            correlation_matrix = await self.calculate_correlation_matrix(
                symbols, method, period_days
            )
            
            # Merge with default config
            viz_config = {**self.default_visualization_config}
            if config:
                viz_config.update(config)
            
            # Generate visualization data based on type
            if visualization_type == VisualizationType.HEATMAP:
                viz_data = self._create_heatmap_data(correlation_matrix, viz_config)
            elif visualization_type == VisualizationType.NETWORK:
                viz_data = self._create_network_data(correlation_matrix, viz_config)
            elif visualization_type == VisualizationType.SCATTER_MATRIX:
                viz_data = self._create_scatter_matrix_data(correlation_matrix, viz_config)
            elif visualization_type == VisualizationType.TIME_SERIES:
                viz_data = self._create_time_series_data(symbols, period_days, viz_config)
            elif visualization_type == VisualizationType.DENDROGRAM:
                viz_data = self._create_dendrogram_data(correlation_matrix, viz_config)
            else:
                raise ValueError(f"Unsupported visualization type: {visualization_type}")
            
            # Create result
            result = VisualizationData(
                visualization_type=visualization_type,
                data=viz_data,
                metadata={
                    "symbols": symbols,
                    "method": method.value,
                    "period_days": period_days,
                    "data_period": correlation_matrix.data_period,
                    "sample_size": correlation_matrix.sample_size
                },
                config=viz_config,
                generated_at=datetime.utcnow()
            )
            
            # Cache result
            cache_data = result.__dict__.copy()
            cache_data['generated_at'] = result.generated_at.isoformat()
            
            await self.cache_manager.set(
                cache_key,
                cache_data,
                ttl=self.visualization_cache_ttl
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating correlation visualization: {str(e)}")
            raise
    
    async def analyze_sector_correlations(
        self,
        sector_symbols: Dict[str, List[str]],
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        period_days: int = 252
    ) -> Dict[str, Any]:
        """Analyze correlations within and between sectors."""
        try:
            # Check cache first
            sectors_key = "_".join(sorted(sector_symbols.keys()))
            cache_key = f"sector_correlation_{sectors_key}_{method.value}_{period_days}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for sector correlation analysis")
                return cached_result
            
            results = {}
            
            # Analyze within-sector correlations
            for sector, symbols in sector_symbols.items():
                if len(symbols) < 2:
                    continue
                
                try:
                    sector_matrix = await self.calculate_correlation_matrix(
                        symbols, method, period_days
                    )
                    
                    # Calculate sector statistics
                    avg_correlation = np.mean(sector_matrix.matrix[np.triu_indices_from(sector_matrix.matrix, k=1)])
                    max_correlation = np.max(sector_matrix.matrix[np.triu_indices_from(sector_matrix.matrix, k=1)])
                    min_correlation = np.min(sector_matrix.matrix[np.triu_indices_from(sector_matrix.matrix, k=1)])
                    
                    results[sector] = {
                        "within_sector": {
                            "average_correlation": float(avg_correlation),
                            "max_correlation": float(max_correlation),
                            "min_correlation": float(min_correlation),
                            "matrix": sector_matrix.matrix.tolist(),
                            "symbols": symbols
                        }
                    }
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing sector {sector}: {str(e)}")
                    results[sector] = {"error": str(e)}
            
            # Analyze between-sector correlations
            sector_representatives = {}
            for sector, symbols in sector_symbols.items():
                if symbols:
                    sector_representatives[sector] = symbols[0]  # Use first symbol as representative
            
            if len(sector_representatives) > 1:
                try:
                    between_sectors_matrix = await self.calculate_correlation_matrix(
                        list(sector_representatives.values()), method, period_days
                    )
                    
                    results["between_sectors"] = {
                        "representatives": sector_representatives,
                        "matrix": between_sectors_matrix.matrix.tolist(),
                        "symbols": list(sector_representatives.values())
                    }
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing between-sector correlations: {str(e)}")
                    results["between_sectors"] = {"error": str(e)}
            
            # Cache result
            await self.cache_manager.set(
                cache_key,
                results,
                ttl=self.correlation_cache_ttl
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing sector correlations: {str(e)}")
            raise
    
    async def _get_price_data(self, symbol: str, period_days: int) -> pd.Series:
        """Get price data for a symbol."""
        try:
            # This would typically fetch from your data source
            # For now, return mock data
            dates = pd.date_range(end=datetime.utcnow(), periods=period_days, freq='D')
            
            # Generate realistic price data with trend and volatility
            np.random.seed(hash(symbol) % 2**32)
            base_price = 100 + np.random.uniform(-50, 150)
            trend = np.random.uniform(-0.001, 0.001)
            volatility = np.random.uniform(0.01, 0.03)
            
            prices = [base_price]
            for i in range(1, period_days):
                change = np.random.normal(trend, volatility)
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1))  # Ensure positive prices
            
            return pd.Series(prices, index=dates, name=symbol)
            
        except Exception as e:
            self.logger.error(f"Error getting price data for {symbol}: {str(e)}")
            return None
    
    def _align_data(self, data1: pd.Series, data2: pd.Series) -> pd.DataFrame:
        """Align two data series by date."""
        return pd.DataFrame({data1.name: data1, data2.name: data2}).dropna()
    
    def _align_multiple_data(self, data_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """Align multiple data series by date."""
        return pd.DataFrame(data_dict).dropna()
    
    def _calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate returns from price series."""
        return prices.pct_change().dropna()
    
    def _pearson_correlation(self, x: pd.Series, y: pd.Series) -> Tuple[float, float]:
        """Calculate Pearson correlation and p-value."""
        from scipy.stats import pearsonr
        correlation, p_value = pearsonr(x, y)
        return correlation, p_value
    
    def _spearman_correlation(self, x: pd.Series, y: pd.Series) -> Tuple[float, float]:
        """Calculate Spearman correlation and p-value."""
        from scipy.stats import spearmanr
        correlation, p_value = spearmanr(x, y)
        return correlation, p_value
    
    def _kendall_correlation(self, x: pd.Series, y: pd.Series) -> Tuple[float, float]:
        """Calculate Kendall correlation and p-value."""
        from scipy.stats import kendalltau
        correlation, p_value = kendalltau(x, y)
        return correlation, p_value
    
    def _dynamic_rolling_correlation(self, x: pd.Series, y: pd.Series, window: int = 30) -> Tuple[float, float]:
        """Calculate dynamic rolling correlation."""
        rolling_corr = x.rolling(window=window).corr(y)
        return rolling_corr.mean(), 0.05  # Simplified p-value
    
    def _calculate_confidence_interval(self, correlation: float, n: int, alpha: float = 0.05) -> Tuple[float, float]:
        """Calculate confidence interval for correlation coefficient."""
        from scipy.stats import norm
        
        if n <= 3:
            return (correlation, correlation)
        
        # Fisher's z-transform
        z = np.arctanh(correlation)
        se = 1 / np.sqrt(n - 3)
        
        # Calculate interval in z-space
        z_lower = z - norm.ppf(1 - alpha/2) * se
        z_upper = z + norm.ppf(1 - alpha/2) * se
        
        # Transform back to correlation space
        lower = np.tanh(z_lower)
        upper = np.tanh(z_upper)
        
        return (lower, upper)
    
    def _calculate_p_values_matrix(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate p-values for correlation matrix."""
        from scipy.stats import pearsonr
        
        symbols = returns_df.columns
        p_values = pd.DataFrame(index=symbols, columns=symbols)
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i == j:
                    p_values.loc[symbol1, symbol2] = 0.0
                else:
                    try:
                        _, p_val = pearsonr(returns_df[symbol1], returns_df[symbol2])
                        p_values.loc[symbol1, symbol2] = p_val
                    except:
                        p_values.loc[symbol1, symbol2] = 1.0
        
        return p_values.astype(float)
    
    def _create_heatmap_data(self, correlation_matrix: CorrelationMatrix, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create heatmap visualization data."""
        return {
            "type": "heatmap",
            "matrix": correlation_matrix.matrix.tolist(),
            "symbols": correlation_matrix.symbols,
            "is_significant": correlation_matrix.is_significant.tolist(),
            "p_values": correlation_matrix.p_values.tolist(),
            "config": config,
            "color_scale": "RdBu",
            "zmin": -1,
            "zmax": 1
        }
    
    def _create_network_data(self, correlation_matrix: CorrelationMatrix, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create network visualization data."""
        # Create nodes
        nodes = []
        for i, symbol in enumerate(correlation_matrix.symbols):
            nodes.append({
                "id": i,
                "symbol": symbol,
                "label": symbol
            })
        
        # Create edges (only significant correlations above threshold)
        edges = []
        for i in range(len(correlation_matrix.symbols)):
            for j in range(i + 1, len(correlation_matrix.symbols)):
                corr = correlation_matrix.matrix[i, j]
                is_sig = correlation_matrix.is_significant[i, j]
                
                if is_sig and abs(corr) > self.medium_correlation_threshold:
                    edges.append({
                        "source": i,
                        "target": j,
                        "correlation": float(corr),
                        "weight": abs(corr),
                        "type": "positive" if corr > 0 else "negative"
                    })
        
        return {
            "type": "network",
            "nodes": nodes,
            "edges": edges,
            "config": config
        }
    
    def _create_scatter_matrix_data(self, correlation_matrix: CorrelationMatrix, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create scatter plot matrix data."""
        return {
            "type": "scatter_matrix",
            "symbols": correlation_matrix.symbols,
            "correlation_matrix": correlation_matrix.matrix.tolist(),
            "config": config
        }
    
    def _create_time_series_data(self, symbols: List[str], period_days: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create time series correlation data."""
        # This would typically calculate rolling correlations over time
        # For now, return mock data
        dates = pd.date_range(end=datetime.utcnow(), periods=period_days, freq='D')
        
        rolling_correlations = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                # Generate mock rolling correlation
                np.random.seed(hash(f"{symbols[i]}_{symbols[j]}") % 2**32)
                rolling_corr = np.random.normal(0.3, 0.2, len(dates))
                rolling_corr = np.clip(rolling_corr, -1, 1)
                
                rolling_correlations.append({
                    "symbol1": symbols[i],
                    "symbol2": symbols[j],
                    "dates": dates.strftime('%Y-%m-%d').tolist(),
                    "correlations": rolling_corr.tolist()
                })
        
        return {
            "type": "time_series",
            "rolling_correlations": rolling_correlations,
            "config": config
        }
    
    def _create_dendrogram_data(self, correlation_matrix: CorrelationMatrix, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create dendrogram visualization data."""
        from scipy.cluster.hierarchy import linkage, dendrogram
        from scipy.spatial.distance import squareform
        
        # Convert correlation to distance
        distance_matrix = 1 - np.abs(correlation_matrix.matrix)
        np.fill_diagonal(distance_matrix, 0)
        
        # Perform hierarchical clustering
        condensed_distances = squareform(distance_matrix)
        linkage_matrix = linkage(condensed_distances, method='average')
        
        return {
            "type": "dendrogram",
            "linkage_matrix": linkage_matrix.tolist(),
            "symbols": correlation_matrix.symbols,
            "config": config
        }