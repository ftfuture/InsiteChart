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
                    return cached_data.to_dict()
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'symbol' not in info:
                self.logger.warning(f"No data found for symbol: {symbol}")
                return None
            
            stock_data = {
                'symbol': symbol,
                'company_name': info.get('longName', info.get('shortName', '')),
                'stock_type': self._map_quote_type(info.get('quoteType', 'EQUITY')),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'previous_close': info.get('previousClose'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'volume': info.get('volume'),
                'avg_volume': info.get('averageVolume'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'eps': info.get('trailingEps'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'data_sources': ['yahoo_finance']
            }
            
            # Cache the result
            if self.cache_manager:
                unified_stock = UnifiedStockData(**stock_data)
                await self.cache_manager.set_stock_data(unified_stock)
            
            self.logger.info(f"Successfully fetched stock info for: {symbol}")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Error getting stock info for {symbol}: {str(e)}")
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
                    return pd.read_json(cached_data)
            
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(period=period)
            
            if hist_data.empty:
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
                    return [stock.to_dict() for stock in cached_results]
            
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
                        'stock_type': self._map_quote_type(quote.get('quoteType', 'EQUITY')),
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
    
    def _map_quote_type(self, quote_type: str) -> StockType:
        """Map Yahoo Finance quote type to our StockType enum."""
        type_mapping = {
            'EQUITY': StockType.EQUITY,
            'ETF': StockType.ETF,
            'MUTUALFUND': StockType.MUTUAL_FUND,
            'CRYPTOCURRENCY': StockType.CRYPTO,
            'INDEX': StockType.INDEX
        }
        return type_mapping.get(quote_type.upper(), StockType.EQUITY)
    
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
                        'name': info['company_name'],
                        'current_price': info['current_price'],
                        'day_change': info['day_change'],
                        'day_change_pct': info['day_change_pct']
                    }
            
            # Trending stocks (mock data for now)
            trending = await self._get_trending_stocks()
            
            return {
                'indices': market_data,
                'trending': trending,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market overview: {str(e)}")
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
                    'company_name': info['company_name'],
                    'current_price': info['current_price'],
                    'day_change_pct': info['day_change_pct']
                })
        
        return trending
    
    async def close(self):
        """Close HTTP session."""
        if self.yahoo_session and not self.yahoo_session.closed:
            await self.yahoo_session.close()