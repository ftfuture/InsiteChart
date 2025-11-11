"""
Unified service for InsiteChart platform.

This service combines stock data and sentiment analysis to provide
a comprehensive view of financial information.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import statistics
import math
import pandas as pd
from dataclasses import dataclass

from ..models.unified_models import (
    UnifiedStockData,
    SearchQuery,
    SearchResult,
    StockType,
    SentimentSource,
    UnifiedDataRequest
)
from ..cache.unified_cache import UnifiedCacheManager
from .realtime_data_collector import DataSource


@dataclass
class UnifiedDataResponse:
    """Unified data response model."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }


class UnifiedService:
    """Unified service combining stock and sentiment data."""
    
    def __init__(self, stock_service, sentiment_service, cache_manager: UnifiedCacheManager):
        self.stock_service = stock_service
        self.sentiment_service = sentiment_service
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    async def get_stock_data(self, symbol: str, include_sentiment: bool = True) -> Optional[UnifiedStockData]:
        """Get unified stock data combining financial and sentiment information."""
        try:
            # Check cache first
            cache_key = f"unified_stock_{symbol}_{include_sentiment}"
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                self.logger.debug(f"Cache hit for unified stock data: {symbol}")
                return UnifiedStockData.from_dict(cached_data)
            
            # Get stock information
            stock_info = await self.stock_service.get_stock_info(symbol)
            if not stock_info:
                return None
            
            # Get sentiment data if requested
            sentiment_data = None
            if include_sentiment:
                sentiment_data = await self.sentiment_service.get_sentiment_data(symbol)
            
            # Create unified stock data
            unified_stock = UnifiedStockData(
                symbol=stock_info['symbol'],
                company_name=stock_info['company_name'],
                stock_type=StockType(stock_info.get('stock_type', 'EQUITY')),
                exchange=stock_info['exchange'],
                sector=stock_info.get('sector'),
                industry=stock_info.get('industry'),
                market_cap=stock_info.get('market_cap'),
                current_price=stock_info.get('current_price'),
                previous_close=stock_info.get('previous_close'),
                day_high=stock_info.get('day_high'),
                day_low=stock_info.get('day_low'),
                volume=stock_info.get('volume'),
                avg_volume=stock_info.get('avg_volume'),
                pe_ratio=stock_info.get('pe_ratio'),
                dividend_yield=stock_info.get('dividend_yield'),
                beta=stock_info.get('beta'),
                eps=stock_info.get('eps'),
                fifty_two_week_high=stock_info.get('fifty_two_week_high'),
                fifty_two_week_low=stock_info.get('fifty_two_week_low'),
                data_sources=stock_info.get('data_sources', ['yahoo_finance'])
            )
            
            # Add sentiment data
            if sentiment_data:
                unified_stock.overall_sentiment = sentiment_data.get('overall_sentiment')
                unified_stock.mention_count_24h = sentiment_data.get('mention_count_24h')
                unified_stock.mention_count_1h = sentiment_data.get('mention_count_1h')
                unified_stock.positive_mentions = sentiment_data.get('positive_mentions')
                unified_stock.negative_mentions = sentiment_data.get('negative_mentions')
                unified_stock.neutral_mentions = sentiment_data.get('neutral_mentions')
                unified_stock.trending_status = sentiment_data.get('trending_status', False)
                unified_stock.trend_score = sentiment_data.get('trend_score')
                unified_stock.trend_duration_hours = sentiment_data.get('trend_duration_hours')
                
                # Add sentiment sources
                if 'community_breakdown' in sentiment_data:
                    for community in sentiment_data['community_breakdown']:
                        community_name = community['community']
                        avg_sentiment = community.get('avg_sentiment')
                        if avg_sentiment is not None:
                            if community_name == 'wallstreetbets':
                                unified_stock.sentiment_sources[SentimentSource.REDDIT] = avg_sentiment
                            elif community_name == 'twitter':
                                unified_stock.sentiment_sources[SentimentSource.TWITTER] = avg_sentiment
                            elif community_name == 'discord':
                                unified_stock.sentiment_sources[SentimentSource.DISCORD] = avg_sentiment
                
                # Add data source
                if 'yahoo_finance' not in unified_stock.data_sources:
                    unified_stock.data_sources.append('sentiment_analysis')
            
            # Cache the result
            await self.cache_manager.set(cache_key, unified_stock.to_dict(), ttl=300)
            
            return unified_stock
            
        except Exception as e:
            self.logger.error(f"Error getting unified stock data for {symbol}: {str(e)}")
            return None
    
    async def search_stocks(self, query: SearchQuery) -> SearchResult:
        """Search stocks with integrated sentiment data."""
        try:
            # Check cache first
            cache_key = f"unified_search_{query.to_hash()}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for search: {query.query}")
                return SearchResult.from_dict(cached_result)
            
            start_time = datetime.utcnow()
            
            # Get stock search results
            stock_results = await self.stock_service.search_stocks(query.query, query.filters)
            
            # Enhance with sentiment data
            unified_results = []
            if stock_results:
                # Get sentiment data for all stocks in parallel
                sentiment_tasks = [
                    self.sentiment_service.get_sentiment_data(stock['symbol'])
                    for stock in stock_results
                ]
                
                sentiment_results = await asyncio.gather(*sentiment_tasks, return_exceptions=True)
                
                # Create unified results
                for i, stock in enumerate(stock_results):
                    sentiment_data = sentiment_results[i] if not isinstance(sentiment_results[i], Exception) else None
                    
                    unified_stock = UnifiedStockData(
                        symbol=stock['symbol'],
                        company_name=stock['company_name'],
                        stock_type=StockType(stock.get('stock_type', 'EQUITY')),
                        exchange=stock['exchange'],
                        sector=stock.get('sector'),
                        industry=stock.get('industry'),
                        market_cap=stock.get('market_cap'),
                        current_price=stock.get('current_price'),
                        previous_close=stock.get('previous_close'),
                        day_high=stock.get('day_high'),
                        day_low=stock.get('day_low'),
                        volume=stock.get('volume'),
                        avg_volume=stock.get('avg_volume'),
                        pe_ratio=stock.get('pe_ratio'),
                        dividend_yield=stock.get('dividend_yield'),
                        beta=stock.get('beta'),
                        eps=stock.get('eps'),
                        fifty_two_week_high=stock.get('fifty_two_week_high'),
                        fifty_two_week_low=stock.get('fifty_two_week_low'),
                        relevance_score=stock.get('relevance_score', 0.0),
                        data_sources=stock.get('data_sources', ['yahoo_finance'])
                    )
                    
                    # Add sentiment data
                    if sentiment_data:
                        unified_stock.overall_sentiment = sentiment_data.get('overall_sentiment')
                        unified_stock.mention_count_24h = sentiment_data.get('mention_count_24h')
                        unified_stock.mention_count_1h = sentiment_data.get('mention_count_1h')
                        unified_stock.positive_mentions = sentiment_data.get('positive_mentions')
                        unified_stock.negative_mentions = sentiment_data.get('negative_mentions')
                        unified_stock.neutral_mentions = sentiment_data.get('neutral_mentions')
                        unified_stock.trending_status = sentiment_data.get('trending_status', False)
                        unified_stock.trend_score = sentiment_data.get('trend_score')
                        
                        if 'yahoo_finance' not in unified_stock.data_sources:
                            unified_stock.data_sources.append('sentiment_analysis')
                    
                    unified_results.append(unified_stock)
                
                # Sort by relevance and trending status
                unified_results.sort(key=lambda x: (
                    x.trending_status or False,
                    x.trend_score or 0,
                    x.relevance_score
                ), reverse=True)
            
            search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = SearchResult(
                query=query,
                results=unified_results,
                total_count=len(unified_results),
                search_time_ms=search_time,
                cache_hit=False
            )
            
            # Cache the result
            await self.cache_manager.set(cache_key, result.to_dict(), ttl=180)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error searching stocks: {str(e)}")
            return SearchResult(
                query=query,
                results=[],
                total_count=0,
                search_time_ms=0,
                cache_hit=False
            )
    
    async def get_trending_stocks(self, limit: int = 10, timeframe: str = "24h") -> List[UnifiedStockData]:
        """Get trending stocks with comprehensive data."""
        try:
            # Check cache first
            cache_key = f"trending_{limit}_{timeframe}"
            cached_stocks = await self.cache_manager.get(cache_key)
            if cached_stocks:
                self.logger.debug(f"Cache hit for trending stocks")
                return [UnifiedStockData.from_dict(stock) for stock in cached_stocks]
            
            # Get trending stocks from sentiment service
            trending_data = await self.sentiment_service.get_trending_stocks(limit)
            
            # Get stock information for trending stocks
            stock_tasks = [
                self.stock_service.get_stock_info(stock['symbol'])
                for stock in trending_data
            ]
            
            stock_results = await asyncio.gather(*stock_tasks, return_exceptions=True)
            
            # Create unified results
            unified_stocks = []
            for i, trending_stock in enumerate(trending_data):
                stock_info = stock_results[i] if not isinstance(stock_results[i], Exception) else None
                
                if stock_info:
                    unified_stock = UnifiedStockData(
                        symbol=stock_info['symbol'],
                        company_name=stock_info['company_name'],
                        stock_type=StockType(stock_info.get('stock_type', 'EQUITY')),
                        exchange=stock_info['exchange'],
                        sector=stock_info.get('sector'),
                        industry=stock_info.get('industry'),
                        market_cap=stock_info.get('market_cap'),
                        current_price=stock_info.get('current_price'),
                        previous_close=stock_info.get('previous_close'),
                        day_high=stock_info.get('day_high'),
                        day_low=stock_info.get('day_low'),
                        volume=stock_info.get('volume'),
                        avg_volume=stock_info.get('avg_volume'),
                        pe_ratio=stock_info.get('pe_ratio'),
                        dividend_yield=stock_info.get('dividend_yield'),
                        beta=stock_info.get('beta'),
                        eps=stock_info.get('eps'),
                        fifty_two_week_high=stock_info.get('fifty_two_week_high'),
                        fifty_two_week_low=stock_info.get('fifty_two_week_low'),
                        overall_sentiment=trending_stock.get('sentiment_score'),
                        mention_count_24h=trending_stock.get('mention_count_24h'),
                        trending_status=True,
                        trend_score=trending_stock.get('trend_score'),
                        data_sources=stock_info.get('data_sources', ['yahoo_finance']) + ['sentiment_analysis']
                    )
                    
                    unified_stocks.append(unified_stock)
            
            # Sort by trend score
            unified_stocks.sort(key=lambda x: x.trend_score or 0, reverse=True)
            
            # Cache the result
            cache_data = [stock.to_dict() for stock in unified_stocks]
            await self.cache_manager.set(cache_key, cache_data, ttl=600)
            
            return unified_stocks
            
        except Exception as e:
            self.logger.error(f"Error getting trending stocks: {str(e)}")
            return []
    
    async def get_market_indices(self) -> List[Dict[str, Any]]:
        """Get major market indices data."""
        try:
            indices_symbols = ['^GSPC', '^DJI', '^IXIC', '^RUT']
            
            # Fetch all indices in parallel
            tasks = [
                self.get_stock_data(symbol, include_sentiment=False)
                for symbol in indices_symbols
            ]
            
            stock_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            indices_data = []
            for i, symbol in enumerate(indices_symbols):
                stock_data = stock_results[i]
                if stock_data and not isinstance(stock_data, Exception):
                    indices_data.append({
                        'symbol': symbol,
                        'name': stock_data.company_name,
                        'current_price': stock_data.current_price,
                        'day_change': stock_data.day_change,
                        'day_change_pct': stock_data.day_change_pct,
                        'volume': stock_data.volume
                    })
            
            return indices_data
            
        except Exception as e:
            self.logger.error(f"Error getting market indices: {str(e)}")
            return []
    
    async def get_market_sentiment(self) -> Dict[str, Any]:
        """Get overall market sentiment analysis."""
        try:
            # Get trending stocks
            trending_stocks = await self.get_trending_stocks(20, "24h")
            
            if not trending_stocks:
                return {'overall_sentiment': 0, 'sentiment_distribution': {}}
            
            # Calculate overall sentiment
            sentiments = [stock.overall_sentiment for stock in trending_stocks if stock.overall_sentiment is not None]
            
            if not sentiments:
                return {'overall_sentiment': 0, 'sentiment_distribution': {}}
            
            overall_sentiment = statistics.mean(sentiments)
            
            # Calculate sentiment distribution
            positive_count = sum(1 for s in sentiments if s > 0.1)
            negative_count = sum(1 for s in sentiments if s < -0.1)
            neutral_count = len(sentiments) - positive_count - negative_count
            
            sentiment_distribution = {
                'positive': positive_count,
                'negative': negative_count,
                'neutral': neutral_count
            }
            
            return {
                'overall_sentiment': round(overall_sentiment, 3),
                'sentiment_distribution': sentiment_distribution,
                'analyzed_stocks': len(trending_stocks),
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market sentiment: {str(e)}")
            return {'overall_sentiment': 0, 'sentiment_distribution': {}}
    
    async def get_market_statistics(self) -> Dict[str, Any]:
        """Get market-wide statistics."""
        try:
            # Get market overview from stock service
            market_overview = await self.stock_service.get_market_overview()
            
            # Get market sentiment
            market_sentiment = await self.get_market_sentiment()
            
            # Combine statistics
            statistics = {
                'market_overview': market_overview,
                'market_sentiment': market_sentiment,
                'data_quality': await self.get_data_quality_report(),
                'cache_stats': await self.cache_manager.get_cache_stats(),
                'last_updated': datetime.utcnow().isoformat()
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Error getting market statistics: {str(e)}")
            return {}
    
    async def compare_stocks(self, symbols: List[str], period: str, include_sentiment: bool) -> Dict[str, Any]:
        """Compare multiple stocks with comprehensive analysis."""
        try:
            if len(symbols) > 10:
                raise ValueError("Maximum 10 symbols can be compared at once")
            
            # Get stock data and historical data in parallel for better performance
            stock_tasks = [
                self.get_stock_data(symbol, include_sentiment)
                for symbol in symbols
            ]
            
            historical_tasks = [
                self.stock_service.get_historical_data(symbol, period)
                for symbol in symbols
            ]
            
            # Execute all tasks in parallel
            all_results = await asyncio.gather(*stock_tasks, *historical_tasks, return_exceptions=True)
            
            # Split results back into stock and historical data
            stock_results = all_results[:len(symbols)]
            historical_results = all_results[len(symbols):]
            
            # Filter successful results
            valid_stocks = [
                stock for stock in stock_results
                if stock is not None and not isinstance(stock, Exception)
            ]
            
            # Calculate performance metrics
            comparison_data = {
                'symbols': symbols,
                'period': period,
                'stocks': [stock.to_dict() for stock in valid_stocks],
                'historical_data': {},
                'performance_metrics': {},
                'correlation_matrix': {}
            }
            
            # Add historical data
            for i, symbol in enumerate(symbols):
                historical_data = historical_results[i]
                if historical_data is not None and not isinstance(historical_data, Exception):
                    # Convert to dict for JSON serialization
                    comparison_data['historical_data'][symbol] = historical_data.to_dict()
            
            # Calculate performance metrics
            for stock in valid_stocks:
                if stock.current_price and stock.previous_close:
                    performance = {
                        'daily_change': stock.day_change,
                        'daily_change_pct': stock.day_change_pct,
                        'current_price': stock.current_price,
                        'previous_close': stock.previous_close
                    }
                    
                    if include_sentiment and stock.overall_sentiment is not None:
                        performance['sentiment_score'] = stock.overall_sentiment
                        performance['mention_count_24h'] = stock.mention_count_24h
                        performance['trending_status'] = stock.trending_status
                        performance['trend_score'] = stock.trend_score
                    
                    comparison_data['performance_metrics'][stock.symbol] = performance
            
            # Calculate correlation matrix (simplified)
            if len(valid_stocks) > 1:
                comparison_data['correlation_matrix'] = await self._calculate_correlation_matrix(valid_stocks)
            
            return comparison_data
            
        except Exception as e:
            self.logger.error(f"Error comparing stocks: {str(e)}")
            return {}
    
    async def _calculate_correlation_matrix(self, stocks: List[UnifiedStockData]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between stocks."""
        try:
            # This is a simplified correlation calculation
            # In production, you'd use historical price data
            correlation_matrix = {}
            
            for i, stock1 in enumerate(stocks):
                correlation_matrix[stock1.symbol] = {}
                
                for j, stock2 in enumerate(stocks):
                    if i == j:
                        correlation_matrix[stock1.symbol][stock2.symbol] = 1.0
                    else:
                        # Simplified correlation based on sentiment and price movement
                        if stock1.day_change_pct and stock2.day_change_pct:
                            price_correlation = 1.0 - abs(stock1.day_change_pct - stock2.day_change_pct) / 100.0
                        else:
                            price_correlation = 0.0
                        
                        if stock1.overall_sentiment is not None and stock2.overall_sentiment is not None:
                            sentiment_correlation = 1.0 - abs(stock1.overall_sentiment - stock2.overall_sentiment)
                        else:
                            sentiment_correlation = 0.0
                        
                        # Weighted average
                        correlation = (price_correlation * 0.7 + sentiment_correlation * 0.3)
                        correlation_matrix[stock1.symbol][stock2.symbol] = round(correlation, 3)
            
            return correlation_matrix
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation matrix: {str(e)}")
            return {}
    
    async def get_detailed_sentiment(self, symbol: str, sources: Optional[List[str]] = None, 
                                  timeframe: str = "24h", include_mentions: bool = False) -> Dict[str, Any]:
        """Get detailed sentiment analysis for a stock."""
        try:
            # Get basic sentiment data
            sentiment_data = await self.sentiment_service.get_sentiment_data(symbol)
            
            if not sentiment_data:
                return {}
            
            # Get stock information
            stock_info = await self.stock_service.get_stock_info(symbol)
            
            detailed_sentiment = {
                'symbol': symbol,
                'company_name': stock_info['company_name'] if stock_info else '',
                'overall_sentiment': sentiment_data.get('overall_sentiment'),
                'mention_count_24h': sentiment_data.get('mention_count_24h'),
                'positive_mentions': sentiment_data.get('positive_mentions'),
                'negative_mentions': sentiment_data.get('negative_mentions'),
                'neutral_mentions': sentiment_data.get('neutral_mentions'),
                'trending_status': sentiment_data.get('trending_status'),
                'trend_score': sentiment_data.get('trend_score'),
                'timeframe': timeframe,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # Add community breakdown if available
            if 'community_breakdown' in sentiment_data:
                detailed_sentiment['community_breakdown'] = sentiment_data['community_breakdown']
            
            # Add individual mentions if requested
            if include_mentions:
                mentions = await self.sentiment_service.collect_mentions(symbol, timeframe)
                detailed_sentiment['mentions'] = [
                    {
                        'text': mention.text,
                        'source': mention.source.value,
                        'community': mention.community,
                        'author': mention.author,
                        'timestamp': mention.timestamp.isoformat(),
                        'upvotes': mention.upvotes,
                        'sentiment_score': mention.sentiment_score,
                        'investment_style': mention.investment_style.value if mention.investment_style else None,
                        'url': mention.url
                    }
                    for mention in mentions
                ]
            
            return detailed_sentiment
            
        except Exception as e:
            self.logger.error(f"Error getting detailed sentiment for {symbol}: {str(e)}")
            return {}
    
    async def get_correlation_analysis(self, symbol1: str, symbol2: str, period: str, 
                                   include_sentiment: bool) -> Dict[str, Any]:
        """Get detailed correlation analysis between two stocks."""
        try:
            # Get stock data for both symbols
            stock1_data = await self.get_stock_data(symbol1, include_sentiment)
            stock2_data = await self.get_stock_data(symbol2, include_sentiment)
            
            if not stock1_data or not stock2_data:
                return {'error': 'One or both symbols not found'}
            
            # Get historical data
            hist1 = await self.stock_service.get_historical_data(symbol1, period)
            hist2 = await self.stock_service.get_historical_data(symbol2, period)
            
            correlation_analysis = {
                'symbol1': symbol1,
                'symbol2': symbol2,
                'period': period,
                'stock1_info': stock1_data.to_dict(),
                'stock2_info': stock2_data.to_dict(),
                'price_correlation': 0.0,
                'sentiment_correlation': 0.0,
                'combined_correlation': 0.0,
                'analysis_period': datetime.utcnow().isoformat()
            }
            
            # Calculate price correlation if historical data available
            if hist1 is not None and hist2 is not None and not isinstance(hist1, Exception) and not isinstance(hist2, Exception):
                price_correlation = self._calculate_price_correlation(hist1, hist2)
                correlation_analysis['price_correlation'] = price_correlation
            
            # Calculate sentiment correlation
            if include_sentiment and stock1_data.overall_sentiment is not None and stock2_data.overall_sentiment is not None:
                sentiment_correlation = 1.0 - abs(stock1_data.overall_sentiment - stock2_data.overall_sentiment)
                correlation_analysis['sentiment_correlation'] = sentiment_correlation
                
                # Combined correlation
                correlation_analysis['combined_correlation'] = (price_correlation * 0.7 + sentiment_correlation * 0.3)
            
            return correlation_analysis
            
        except Exception as e:
            self.logger.error(f"Error getting correlation analysis: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_price_correlation(self, hist1, hist2) -> float:
        """Calculate price correlation between two stocks."""
        try:
            # Handle DataFrame or dict input
            if hasattr(hist1, 'get'):
                prices1 = hist1.get('Close', pd.Series()).dropna()
            else:
                prices1 = hist1['Close'].dropna()
            
            if hasattr(hist2, 'get'):
                prices2 = hist2.get('Close', pd.Series()).dropna()
            else:
                prices2 = hist2['Close'].dropna()
            
            # Align dates
            common_dates = prices1.index.intersection(prices2.index)
            if len(common_dates) < 2:
                return 0.0
            
            aligned_prices1 = prices1.loc[common_dates]
            aligned_prices2 = prices2.loc[common_dates]
            
            # Calculate correlation
            correlation = aligned_prices1.corr(aligned_prices2)
            
            # Handle both scalar and matrix results
            if hasattr(correlation, 'iloc'):
                # DataFrame result
                if correlation.shape == (1, 1):
                    corr_value = correlation.iloc[0, 0]
                else:
                    corr_value = correlation.values[0, 0] if correlation.values.size > 0 else 0.0
            else:
                # Scalar result
                corr_value = correlation
            
            return round(float(corr_value), 3) if not math.isnan(corr_value) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating price correlation: {str(e)}")
            return 0.0
    
    async def get_user_watchlist(self, user_id: str, include_sentiment: bool, include_alerts: bool) -> Dict[str, Any]:
        """Get user's watchlist with integrated data."""
        try:
            # Get watchlist from cache or database
            watchlist_symbols = await self.cache_manager.get_user_watchlist(user_id)
            
            if not watchlist_symbols:
                return {'user_id': user_id, 'watchlist': []}
            
            # Get stock data for watchlist
            stock_tasks = [
                self.get_stock_data(symbol, include_sentiment)
                for symbol in watchlist_symbols
            ]
            
            stock_results = await asyncio.gather(*stock_tasks, return_exceptions=True)
            
            # Filter successful results
            watchlist_data = []
            for i, symbol in enumerate(watchlist_symbols):
                stock_data = stock_results[i]
                if stock_data is not None and not isinstance(stock_data, Exception):
                    watchlist_item = stock_data.to_dict()
                    
                    # Add alert information if requested
                    if include_alerts:
                        watchlist_item['alerts'] = {
                            'price_alert': stock_data.day_change_pct and abs(stock_data.day_change_pct) > 5.0,
                            'sentiment_alert': stock_data.trending_status and stock_data.trend_score and stock_data.trend_score > 2.0
                        }
                    
                    watchlist_data.append(watchlist_item)
            
            return {
                'user_id': user_id,
                'watchlist': watchlist_data,
                'total_count': len(watchlist_data),
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting watchlist for user {user_id}: {str(e)}")
            return {'user_id': user_id, 'watchlist': []}
    
    async def add_to_watchlist(self, user_id: str, symbol: str, category: Optional[str] = None,
                           alert_threshold: Optional[float] = None, sentiment_alert: bool = False) -> Dict[str, Any]:
        """Add stock to user's watchlist."""
        try:
            # Get current watchlist
            watchlist_symbols = await self.cache_manager.get_user_watchlist(user_id) or []
            
            # Add symbol if not already present
            if symbol not in watchlist_symbols:
                watchlist_symbols.append(symbol)
                await self.cache_manager.set_user_watchlist(user_id, watchlist_symbols)
            
            # Get stock data
            stock_data = await self.get_stock_data(symbol, include_sentiment=True)
            
            return {
                'success': True,
                'user_id': user_id,
                'symbol': symbol,
                'category': category,
                'alert_threshold': alert_threshold,
                'sentiment_alert': sentiment_alert,
                'stock_data': stock_data.to_dict() if stock_data else None,
                'added_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error adding {symbol} to watchlist: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_market_insights(self, timeframe: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Get market insights and analytics."""
        try:
            # Get trending stocks
            trending_stocks = await self.get_trending_stocks(20, timeframe)
            
            # Analyze sector distribution
            sector_distribution = {}
            sentiment_by_sector = {}
            
            for stock in trending_stocks:
                sector = stock.sector or 'Unknown'
                
                if sector not in sector_distribution:
                    sector_distribution[sector] = 0
                    sentiment_by_sector[sector] = []
                
                sector_distribution[sector] += 1
                
                if stock.overall_sentiment is not None:
                    sentiment_by_sector[sector].append(stock.overall_sentiment)
            
            # Calculate sector sentiment averages
            sector_sentiment = {}
            for sector, sentiments in sentiment_by_sector.items():
                if sentiments:
                    sector_sentiment[sector] = statistics.mean(sentiments)
                else:
                    sector_sentiment[sector] = 0.0
            
            # Identify top performing sectors
            top_sectors = sorted(
                sector_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Get market sentiment
            market_sentiment = await self.get_market_sentiment()
            
            insights = {
                'timeframe': timeframe,
                'category_filter': category,
                'trending_stocks_count': len(trending_stocks),
                'sector_distribution': sector_distribution,
                'sector_sentiment': sector_sentiment,
                'top_sectors': top_sectors,
                'market_sentiment': market_sentiment,
                'insights': self._generate_insights(trending_stocks, sector_distribution, market_sentiment),
                'last_updated': datetime.utcnow().isoformat()
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting market insights: {str(e)}")
            return {}
    
    def _generate_insights(self, trending_stocks: List[UnifiedStockData], 
                          sector_distribution: Dict[str, int], 
                          market_sentiment: Dict[str, Any]) -> List[str]:
        """Generate market insights based on analysis."""
        insights = []
        
        # Trending insights
        if trending_stocks:
            top_trending = max(trending_stocks, key=lambda x: x.trend_score or 0)
            insights.append(f"Most trending stock: {top_trending.symbol} with trend score {top_trending.trend_score}")
        
        # Sector insights
        if sector_distribution:
            top_sector = max(sector_distribution.items(), key=lambda x: x[1])
            insights.append(f"Hottest sector: {top_sector[0]} with {top_sector[1]} trending stocks")
        
        # Sentiment insights
        overall_sentiment = market_sentiment.get('overall_sentiment', 0)
        if overall_sentiment > 0.2:
            insights.append("Market sentiment is predominantly positive")
        elif overall_sentiment < -0.2:
            insights.append("Market sentiment is predominantly negative")
        else:
            insights.append("Market sentiment is neutral")
        
        return insights
    
    async def get_data_quality_report(self) -> Dict[str, Any]:
        """Get data quality report for the platform."""
        try:
            # Get cache stats
            cache_stats = await self.cache_manager.get_cache_stats()
            
            # Calculate data quality metrics
            total_requests = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
            hit_rate = cache_stats.get('hit_rate', 0)
            
            # Sample some stocks to check data completeness
            sample_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
            
            # Fetch all sample stocks in parallel
            sample_tasks = [
                self.get_stock_data(symbol, include_sentiment=True)
                for symbol in sample_symbols
            ]
            
            sample_results = await asyncio.gather(*sample_tasks, return_exceptions=True)
            
            quality_checks = []
            for i, symbol in enumerate(sample_symbols):
                stock_data = sample_results[i]
                if stock_data and not isinstance(stock_data, Exception):
                    completeness = self._calculate_data_completeness(stock_data)
                    quality_checks.append({
                        'symbol': symbol,
                        'completeness': completeness,
                        'has_sentiment': stock_data.overall_sentiment is not None,
                        'has_basic_data': bool(stock_data.current_price and stock_data.volume)
                    })
            
            # Calculate overall quality score
            if quality_checks:
                avg_completeness = sum(check['completeness'] for check in quality_checks) / len(quality_checks)
                sentiment_coverage = sum(1 for check in quality_checks if check['has_sentiment']) / len(quality_checks)
            else:
                avg_completeness = 0.0
                sentiment_coverage = 0.0
            
            overall_quality = (avg_completeness * 0.7 + sentiment_coverage * 0.3)
            
            return {
                'cache_hit_rate': hit_rate,
                'total_requests': total_requests,
                'data_completeness': avg_completeness,
                'sentiment_coverage': sentiment_coverage,
                'overall_quality_score': overall_quality,
                'sample_checks': quality_checks,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting data quality report: {str(e)}")
            return {}
    
    def _calculate_data_completeness(self, stock_data: UnifiedStockData) -> float:
        """Calculate data completeness score for a stock."""
        required_fields = [
            'current_price', 'volume', 'market_cap', 'pe_ratio', 
            'dividend_yield', 'beta', 'eps'
        ]
        
        available_fields = 0
        for field in required_fields:
            value = getattr(stock_data, field, None)
            if value is not None:
                available_fields += 1
        
        return available_fields / len(required_fields)