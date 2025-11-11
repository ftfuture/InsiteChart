"""
Stock data service for InsiteChart platform.

This service handles all stock-related data operations including
search, historical data, and financial metrics.
"""

import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from ..models.unified_models import UnifiedStockData, StockType, SearchQuery


class StockService:
    """Stock data service for managing stock information and search."""
    
    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        self.yahoo_session = None
        self.cache_ttl = 300  # 5 minutes
        self.request_timeout = 10
        
        # API rate limiting
        self.requests_per_minute = 60
        self.request_times = []
        
        # Thread pool for synchronous operations
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.yahoo_session is None or self.yahoo_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            self.yahoo_session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.yahoo_session
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.request_times.append(now)
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get basic stock information."""
        try:
            await self._check_rate_limit()
            
            # Check cache first
            if self.cache_manager:
                cached_data = await self.cache_manager.get_stock_data(symbol)
                if cached_data:
                    self.logger.info(f"Cache hit for stock info: {symbol}")
                    # Handle both dict and UnifiedStockData objects
                    if hasattr(cached_data, 'to_dict'):
                        return cached_data.to_dict()
                    elif isinstance(cached_data, dict):
                        return cached_data
                    else:
                        # Convert to dict if it's a UnifiedStockData object
                        stock_type = getattr(cached_data, 'stock_type', 'EQUITY')
                        # Handle enum values
                        if hasattr(stock_type, 'value'):
                            stock_type = stock_type.value
                        
                        return {
                            'symbol': getattr(cached_data, 'symbol', ''),
                            'company_name': getattr(cached_data, 'company_name', ''),
                            'stock_type': stock_type,
                            'exchange': getattr(cached_data, 'exchange', ''),
                            'sector': getattr(cached_data, 'sector', ''),
                            'industry': getattr(cached_data, 'industry', ''),
                            'current_price': getattr(cached_data, 'current_price', 0.0),
                            'previous_close': getattr(cached_data, 'previous_close', 0.0),
                            'day_high': getattr(cached_data, 'day_high', 0.0),
                            'day_low': getattr(cached_data, 'day_low', 0.0),
                            'volume': getattr(cached_data, 'volume', 0),
                            'avg_volume': getattr(cached_data, 'avg_volume', 0),
                            'market_cap': getattr(cached_data, 'market_cap', 0.0),
                            'pe_ratio': getattr(cached_data, 'pe_ratio', 0.0),
                            'dividend_yield': getattr(cached_data, 'dividend_yield', 0.0),
                            'beta': getattr(cached_data, 'beta', 0.0),
                            'eps': getattr(cached_data, 'eps', 0.0),
                            'fifty_two_week_high': getattr(cached_data, 'fifty_two_week_high', 0.0),
                            'fifty_two_week_low': getattr(cached_data, 'fifty_two_week_low', 0.0),
                            'data_sources': getattr(cached_data, 'data_sources', ['yahoo_finance'])
                        }
            
            # Fetch from Yahoo Finance in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker_info = await loop.run_in_executor(
                self.executor,
                self._get_ticker_info_sync,
                symbol
            )
            
            if not ticker_info or 'symbol' not in ticker_info:
                self.logger.warning(f"No data found for symbol: {symbol}")
                return None
            
            stock_data = {
                'symbol': symbol,
                'company_name': ticker_info.get('longName', ticker_info.get('shortName', '')),
                'stock_type': self._map_quote_type(ticker_info.get('quoteType', 'EQUITY')).value,
                'exchange': ticker_info.get('exchange', ''),
                'sector': ticker_info.get('sector', ''),
                'industry': ticker_info.get('industry', ''),
                'current_price': ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice'),
                'previous_close': ticker_info.get('previousClose'),
                'day_high': ticker_info.get('dayHigh'),
                'day_low': ticker_info.get('dayLow'),
                'volume': ticker_info.get('volume'),
                'avg_volume': ticker_info.get('averageVolume'),
                'market_cap': ticker_info.get('marketCap'),
                'pe_ratio': ticker_info.get('trailingPE'),
                'dividend_yield': ticker_info.get('dividendYield'),
                'beta': ticker_info.get('beta'),
                'eps': ticker_info.get('trailingEps'),
                'fifty_two_week_high': ticker_info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': ticker_info.get('fiftyTwoWeekLow'),
                'data_sources': ['yahoo_finance']
            }
            
            # Cache the result
            if self.cache_manager:
                unified_stock = UnifiedStockData(**stock_data)
                await self.cache_manager.set_stock_data(unified_stock)
            
            self.logger.info(f"Successfully fetched stock info for: {symbol}")
            return stock_data
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error getting stock info for {symbol}: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """Get historical price data."""
        try:
            await self._check_rate_limit()
            
            # Check cache first
            cache_key = f"hist_{symbol}_{period}"
            if self.cache_manager:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    self.logger.info(f"Cache hit for historical data: {symbol}")
                    # Handle both string and DataFrame objects
                    if isinstance(cached_data, str):
                        from io import StringIO
                        return pd.read_json(StringIO(cached_data))
                    elif isinstance(cached_data, pd.DataFrame):
                        return cached_data
            
            # Fetch historical data in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            hist_data = await loop.run_in_executor(
                self.executor,
                self._get_historical_data_sync,
                symbol,
                period
            )
            
            if hist_data is None or hist_data.empty:
                self.logger.warning(f"No historical data for {symbol}")
                return None
            
            # Cache the result
            if self.cache_manager:
                await self.cache_manager.set(cache_key, hist_data.to_json(), ttl=self.cache_ttl)
            
            self.logger.info(f"Successfully fetched historical data for: {symbol}")
            return hist_data
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    async def search_stocks(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for stocks based on query and filters."""
        try:
            await self._check_rate_limit()
            
            # Check cache first
            search_query = SearchQuery(query=query, filters=filters or {})
            if self.cache_manager:
                cached_results = await self.cache_manager.get_search_results(search_query)
                if cached_results:
                    self.logger.info(f"Cache hit for search: {query}")
                    # Handle both dict and UnifiedStockData objects
                    results = []
                    for stock in cached_results:
                        if hasattr(stock, 'to_dict'):
                            results.append(stock.to_dict())
                        elif isinstance(stock, dict):
                            results.append(stock)
                        else:
                            # Convert to dict if it's a UnifiedStockData object
                            stock_type = getattr(stock, 'stock_type', 'EQUITY')
                            # Handle enum values
                            if hasattr(stock_type, 'value'):
                                stock_type = stock_type.value
                            
                            results.append({
                                'symbol': getattr(stock, 'symbol', ''),
                                'company_name': getattr(stock, 'company_name', ''),
                                'stock_type': stock_type,
                                'exchange': getattr(stock, 'exchange', ''),
                                'sector': getattr(stock, 'sector', ''),
                                'industry': getattr(stock, 'industry', ''),
                                'relevance_score': getattr(stock, 'relevance_score', 0.0),
                                'data_sources': getattr(stock, 'data_sources', ['yahoo_finance'])
                            })
                    return results
            
            # Yahoo Finance search API
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {
                "q": query,
                "quotes_count": 20,
                "country": "United States"
            }
            
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"Search API error: {response.status}")
                    return []
                
                data = await response.json()
                results = []
                
                for quote in data.get('quotes', []):
                    # Apply filters
                    if filters and not self._apply_filters(quote, filters):
                        continue
                    
                    # Calculate relevance score
                    relevance_score = self._calculate_relevance_score(quote, query)
                    
                    stock_data = {
                        'symbol': quote.get('symbol', ''),
                        'company_name': quote.get('shortname') or quote.get('longname', ''),
                        'stock_type': self._map_quote_type(quote.get('quoteType', 'EQUITY')).value,
                        'exchange': quote.get('exchange', ''),
                        'sector': quote.get('sector', ''),
                        'industry': quote.get('industry', ''),
                        'relevance_score': relevance_score,
                        'data_sources': ['yahoo_finance']
                    }
                    results.append(stock_data)
                
                # Sort by relevance
                results.sort(key=lambda x: x['relevance_score'], reverse=True)
                
                # Cache the results
                if self.cache_manager:
                    unified_results = [UnifiedStockData(**stock) for stock in results]
                    await self.cache_manager.set_search_results(search_query, unified_results)
                
                self.logger.info(f"Successfully searched stocks for query: {query}")
                return results
                
        except Exception as e:
            self.logger.error(f"Error searching stocks for {query}: {str(e)}")
            return []
    
    def _process_search_results(self, quotes: List[Dict[str, Any]], query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process search results from Yahoo Finance API."""
        results = []
        
        for quote in quotes:
            # Apply filters
            if filters and not self._apply_filters(quote, filters):
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(quote, query)
            
            stock_data = {
                'symbol': quote.get('symbol', ''),
                'company_name': quote.get('shortname') or quote.get('longname', ''),
                'stock_type': self._map_quote_type(quote.get('quoteType', 'EQUITY')).value,
                'exchange': quote.get('exchange', ''),
                'sector': quote.get('sector', ''),
                'industry': quote.get('industry', ''),
                'relevance_score': relevance_score,
                'data_sources': ['yahoo_finance']
            }
            results.append(stock_data)
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results
    
    def _map_quote_type(self, quote_type: str) -> StockType:
        """Map Yahoo Finance quote type to our StockType enum."""
        # Handle both string and enum inputs
        if hasattr(quote_type, 'value'):
            # Already an enum, return as is
            return quote_type
        elif isinstance(quote_type, str):
            # String input, map to enum
            type_mapping = {
                'EQUITY': StockType.EQUITY,
                'ETF': StockType.ETF,
                'MUTUALFUND': StockType.MUTUAL_FUND,
                'CRYPTOCURRENCY': StockType.CRYPTO,
                'INDEX': StockType.INDEX
            }
            return type_mapping.get(quote_type.upper(), StockType.EQUITY)
        else:
            # Default case
            return StockType.EQUITY
    
    def _apply_filters(self, quote: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Apply filters to search results."""
        # Stock type filter
        if 'stock_type' in filters:
            if quote.get('quoteType', '').upper() != filters['stock_type'].upper():
                return False
        
        # Exchange filter
        if 'exchange' in filters:
            if quote.get('exchange', '').upper() != filters['exchange'].upper():
                return False
        
        # Sector filter
        if 'sector' in filters:
            if filters['sector'].lower() not in quote.get('sector', '').lower():
                return False
        
        return True
    
    def _calculate_relevance_score(self, quote: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for search result."""
        query = query.lower()
        symbol = quote.get('symbol', '').lower()
        name = quote.get('shortname', '').lower()
        longname = quote.get('longname', '').lower()
        
        score = 0.0
        
        # Exact symbol match
        if symbol == query:
            score += 100
        # Symbol starts with query
        elif symbol.startswith(query):
            score += 80
        # Name starts with query
        elif name.startswith(query) or longname.startswith(query):
            score += 60
        # Symbol contains query
        elif query in symbol:
            score += 40
        # Name contains query
        elif query in name or query in longname:
            score += 20
        
        return score
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview data."""
        try:
            # Major indices
            indices = ['^GSPC', '^DJI', '^IXIC', '^RUT']
            market_data = {}
            
            for index in indices:
                info = await self.get_stock_info(index)
                if info:
                    market_data[index] = {
                        'name': info.get('company_name', ''),
                        'current_price': info.get('current_price', 0.0),
                        'day_change': info.get('day_change', 0.0),
                        'day_change_pct': info.get('day_change_pct', 0.0)
                    }
            
            # Trending stocks (mock data for now)
            trending = await self._get_trending_stocks()
            
            return {
                'indices': market_data,
                'trending': trending,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error getting market overview: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    async def _get_trending_stocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending stocks (placeholder implementation)."""
        # This would typically come from social media analysis
        # For now, return popular stocks
        popular_symbols = ['GME', 'AMC', 'TSLA', 'AAPL', 'NVDA', 'AMD', 'PLTR', 'BB', 'NOK', 'SNDL']
        trending = []
        
        for symbol in popular_symbols[:limit]:
            info = await self.get_stock_info(symbol)
            if info:
                trending.append({
                    'symbol': symbol,
                    'company_name': info.get('company_name', ''),
                    'current_price': info.get('current_price', 0.0),
                    'day_change_pct': info.get('day_change_pct', 0.0)
                })
        
        return trending
    
    async def close(self):
        """Close HTTP session and thread pool."""
        if self.yahoo_session and not self.yahoo_session.closed:
            await self.yahoo_session.close()
        
        if self.executor:
            self.executor.shutdown(wait=False)
    
    def _get_ticker_info_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Synchronous method to get ticker info."""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except Exception as e:
            self.logger.error(f"Error getting ticker info for {symbol}: {str(e)}")
            return None
    
    def _get_historical_data_sync(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Synchronous method to get historical data."""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.history(period=period)
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None