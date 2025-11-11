"""
Yahoo Finance API 연동 강화 서비스
실시간 주식 데이터 수집 및 캐싱 기능 제공
"""

import asyncio
import aiohttp
import json
import time
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
import logging
import redis.asyncio as redis
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

@dataclass
class StockData:
    """주식 데이터 모델"""
    symbol: str
    company_name: str
    current_price: float
    previous_close: float
    open_price: float
    day_high: float
    day_low: float
    volume: int
    market_cap: Optional[int] = None
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None
    timestamp: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        
        if self.price_change is None and self.current_price and self.previous_close:
            self.price_change = self.current_price - self.previous_close
            
        if self.price_change_percent is None and self.price_change and self.previous_close:
            self.price_change_percent = (self.price_change / self.previous_close) * 100

@dataclass
class HistoricalData:
    """과거 데이터 모델"""
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None

class YahooFinanceService:
    """Yahoo Finance API 서비스 클래스"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.session = None
        self.base_url = "https://query1.finance.yahoo.com"
        self.base_v2_url = "https://query2.finance.yahoo.com"
        
        # 캐시 설정
        self.cache_ttl = {
            "current": 60,      # 현재 가격: 1분
            "historical": 3600,  # 과거 데이터: 1시간
            "profile": 86400,   # 프로필 정보: 24시간
            "search": 1800      # 검색 결과: 30분
        }
        
        # 속도 제한 설정
        self.rate_limits = {
            "requests_per_minute": 60,
            "requests_per_hour": 2000,
            "concurrent_requests": 5
        }
        
        # 요청 카운터
        self.request_count = {
            "minute": 0,
            "hour": 0,
            "last_minute": time.time() // 60,
            "last_hour": time.time() // 3600
        }
        
        # 세마포어 (동시 요청 제한)
        self.semaphore = asyncio.Semaphore(self.rate_limits["concurrent_requests"])
        
        # 재시도 설정
        self.retry_config = {
            "max_retries": 3,
            "retry_delay": 1.0,
            "backoff_factor": 2.0
        }
        
        # Crumb 토큰 관리
        self.crumb_token = None
        self.crumb_expiry = None
        self.crumb_cache_duration = 3600  # 1시간
    
    async def initialize(self):
        """서비스 초기화"""
        try:
            # Redis 클라이언트 초기화
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # HTTP 세션 초기화
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector
            )
            
            # Crumb 토큰 초기화
            await self._refresh_crumb_token()
            
            logger.info("Yahoo Finance Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Yahoo Finance Service: {str(e)}")
            raise
    
    async def get_stock_data(self, symbol: str) -> Optional[StockData]:
        """
        주식 데이터 가져오기
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            주식 데이터 또는 None
        """
        try:
            # 캐시 확인
            cache_key = f"yahoo:stock:{symbol}"
            cached_data = await self._get_from_cache(cache_key, "current")
            if cached_data:
                logger.debug(f"Cache hit for stock data: {symbol}")
                return StockData(**cached_data)
            
            # 속도 제한 확인
            if not await self._check_rate_limit():
                logger.warning(f"Rate limit exceeded for symbol: {symbol}")
                return None
            
            # API 요청
            async with self.semaphore:
                stock_data = await self._fetch_stock_data_with_retry(symbol)
            
            if stock_data:
                # 캐시에 저장
                await self._save_to_cache(cache_key, asdict(stock_data), "current")
                logger.info(f"Fetched stock data for {symbol}: {stock_data.current_price}")
                
            return stock_data
            
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return None
    
    async def get_multiple_stocks(self, symbols: List[str]) -> Dict[str, Optional[StockData]]:
        """
        다중 주식 데이터 병렬 처리
        
        Args:
            symbols: 주식 심볼 목록
            
        Returns:
            심볼별 주식 데이터 딕셔너리
        """
        if not symbols:
            return {}
        
        try:
            # 병렬로 데이터 가져오기
            tasks = [self.get_stock_data(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 매핑
            stock_data = {}
            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {symbol}: {str(result)}")
                    stock_data[symbol] = None
                else:
                    stock_data[symbol] = result
            
            logger.info(f"Fetched {len([r for r in stock_data.values() if r])}/{len(symbols)} stocks")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error getting multiple stocks: {str(e)}")
            return {symbol: None for symbol in symbols}
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1mo", 
        interval: str = "1d"
    ) -> List[HistoricalData]:
        """
        과거 데이터 가져오기
        
        Args:
            symbol: 주식 심볼
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            과거 데이터 목록
        """
        try:
            # 캐시 확인
            cache_key = f"yahoo:historical:{symbol}:{period}:{interval}"
            cached_data = await self._get_from_cache(cache_key, "historical")
            if cached_data:
                logger.debug(f"Cache hit for historical data: {symbol}")
                return [HistoricalData(**data) for data in cached_data]
            
            # 속도 제한 확인
            if not await self._check_rate_limit():
                logger.warning(f"Rate limit exceeded for historical data: {symbol}")
                return []
            
            # API 요청
            async with self.semaphore:
                historical_data = await self._fetch_historical_data_with_retry(symbol, period, interval)
            
            if historical_data:
                # 캐시에 저장
                data_dicts = [asdict(data) for data in historical_data]
                await self._save_to_cache(cache_key, data_dicts, "historical")
                logger.info(f"Fetched {len(historical_data)} historical data points for {symbol}")
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return []
    
    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """
        주식 검색
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 목록
        """
        try:
            # 캐시 확인
            cache_key = f"yahoo:search:{query.lower()}"
            cached_data = await self._get_from_cache(cache_key, "search")
            if cached_data:
                logger.debug(f"Cache hit for search: {query}")
                return cached_data
            
            # 속도 제한 확인
            if not await self._check_rate_limit():
                logger.warning(f"Rate limit exceeded for search: {query}")
                return []
            
            # API 요청
            async with self.semaphore:
                search_results = await self._fetch_search_results_with_retry(query)
            
            if search_results:
                # 캐시에 저장
                await self._save_to_cache(cache_key, search_results, "search")
                logger.info(f"Found {len(search_results)} search results for: {query}")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching stocks for {query}: {str(e)}")
            return []
    
    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        회사 프로필 정보 가져오기
        
        Args:
            symbol: 주식 심볼
            
        Returns:
            회사 프로필 정보 또는 None
        """
        try:
            # 캐시 확인
            cache_key = f"yahoo:profile:{symbol}"
            cached_data = await self._get_from_cache(cache_key, "profile")
            if cached_data:
                logger.debug(f"Cache hit for profile: {symbol}")
                return cached_data
            
            # 속도 제한 확인
            if not await self._check_rate_limit():
                logger.warning(f"Rate limit exceeded for profile: {symbol}")
                return None
            
            # API 요청
            async with self.semaphore:
                profile_data = await self._fetch_profile_data_with_retry(symbol)
            
            if profile_data:
                # 캐시에 저장
                await self._save_to_cache(cache_key, profile_data, "profile")
                logger.info(f"Fetched profile for {symbol}")
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting profile for {symbol}: {str(e)}")
            return None
    
    async def _fetch_stock_data_with_retry(self, symbol: str) -> Optional[StockData]:
        """재시도 로직과 함께 주식 데이터 가져오기"""
        last_exception = None
        
        for attempt in range(self.retry_config["max_retries"]):
            try:
                return await self._fetch_stock_data(symbol)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config["max_retries"] - 1:
                    delay = self.retry_config["retry_delay"] * (self.retry_config["backoff_factor"] ** attempt)
                    logger.warning(f"Retry {attempt + 1} for {symbol} after {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to fetch stock data for {symbol} after {self.retry_config['max_retries']} attempts: {str(last_exception)}")
        return None
    
    async def _fetch_stock_data(self, symbol: str) -> Optional[StockData]:
        """주식 데이터 가져오기"""
        url = f"{self.base_url}/v8/finance/chart/{symbol}"
        
        params = {
            "interval": "1m",
            "range": "1d",
            "includePrePost": "true",
            "events": "div%7Csplit"
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise aiohttp.ClientError(f"HTTP {response.status}: {await response.text()}")
            
            data = await response.json()
            
            # 데이터 변환
            return self._transform_stock_data(data, symbol)
    
    async def _fetch_historical_data_with_retry(self, symbol: str, period: str, interval: str) -> List[HistoricalData]:
        """재시도 로직과 함께 과거 데이터 가져오기"""
        last_exception = None
        
        for attempt in range(self.retry_config["max_retries"]):
            try:
                return await self._fetch_historical_data(symbol, period, interval)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config["max_retries"] - 1:
                    delay = self.retry_config["retry_delay"] * (self.retry_config["backoff_factor"] ** attempt)
                    logger.warning(f"Retry {attempt + 1} for historical {symbol} after {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to fetch historical data for {symbol} after {self.retry_config['max_retries']} attempts: {str(last_exception)}")
        return []
    
    async def _fetch_historical_data(self, symbol: str, period: str, interval: str) -> List[HistoricalData]:
        """과거 데이터 가져오기"""
        url = f"{self.base_url}/v8/finance/chart/{symbol}"
        
        # 기간과 간격에 따라 다른 파라미터 사용
        params = {
            "period1": self._get_period_start_timestamp(period),
            "period2": int(time.time()),
            "interval": interval,
            "includePrePost": "true"
        }
        
        # 특정 기간에 대해서는 range 파라미터 사용
        if period in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]:
            params = {
                "range": period,
                "interval": interval,
                "includePrePost": "true"
            }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise aiohttp.ClientError(f"HTTP {response.status}: {await response.text()}")
            
            data = await response.json()
            
            # 데이터 변환
            return self._transform_historical_data(data, symbol)
    
    def _get_period_start_timestamp(self, period: str) -> int:
        """기간에 따른 시작 타임스탬프 계산"""
        current_time = time.time()
        
        if period == "1d":
            return int(current_time - 86400)  # 1일
        elif period == "5d":
            return int(current_time - 432000)  # 5일
        elif period == "1mo":
            return int(current_time - 2592000)  # 30일
        elif period == "3mo":
            return int(current_time - 7776000)  # 90일
        elif period == "6mo":
            return int(current_time - 15552000)  # 180일
        elif period == "1y":
            return int(current_time - 31536000)  # 365일
        elif period == "2y":
            return int(current_time - 63072000)  # 730일
        elif period == "5y":
            return int(current_time - 157680000)  # 1825일
        elif period == "10y":
            return int(current_time - 315360000)  # 3650일
        elif period == "ytd":
            # 올해의 시작
            current_year = datetime.now().year
            start_of_year = datetime(current_year, 1, 1, tzinfo=timezone.utc)
            return int(start_of_year.timestamp())
        else:  # max
            return 0  # 1970년부터
    
    async def _fetch_search_results_with_retry(self, query: str) -> List[Dict[str, Any]]:
        """재시도 로직과 함께 검색 결과 가져오기"""
        last_exception = None
        
        for attempt in range(self.retry_config["max_retries"]):
            try:
                return await self._fetch_search_results(query)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config["max_retries"] - 1:
                    delay = self.retry_config["retry_delay"] * (self.retry_config["backoff_factor"] ** attempt)
                    logger.warning(f"Retry {attempt + 1} for search {query} after {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to fetch search results for {query} after {self.retry_config['max_retries']} attempts: {str(last_exception)}")
        return []
    
    async def _fetch_search_results(self, query: str) -> List[Dict[str, Any]]:
        """검색 결과 가져오기"""
        url = f"{self.base_v2_url}/v1/finance/search"
        
        params = {
            "q": query,
            "quotesCount": 10,
            "newsCount": 0
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise aiohttp.ClientError(f"HTTP {response.status}: {await response.text()}")
            
            data = await response.json()
            
            # 데이터 변환
            return self._transform_search_results(data)
    
    async def _fetch_profile_data_with_retry(self, symbol: str) -> Optional[Dict[str, Any]]:
        """재시도 로직과 함께 프로필 데이터 가져오기"""
        last_exception = None
        
        for attempt in range(self.retry_config["max_retries"]):
            try:
                return await self._fetch_profile_data(symbol)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config["max_retries"] - 1:
                    delay = self.retry_config["retry_delay"] * (self.retry_config["backoff_factor"] ** attempt)
                    logger.warning(f"Retry {attempt + 1} for profile {symbol} after {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to fetch profile data for {symbol} after {self.retry_config['max_retries']} attempts: {str(last_exception)}")
        return None
    
    async def _fetch_profile_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """프로필 데이터 가져오기"""
        # 대체 방법: 주식 데이터에서 프로필 정보 추출
        try:
            # 먼저 기본 주식 데이터 가져오기
            stock_data = await self._fetch_stock_data(symbol)
            if not stock_data:
                return None
            
            # 기본 정보 구성
            profile_info = {
                "symbol": symbol,
                "long_name": stock_data.long_name,
                "short_name": stock_data.short_name,
                "currency": stock_data.currency,
                "exchange": stock_data.exchange
            }
            
            # 추가 정보를 위해 다른 API 엔드포인트 시도
            try:
                # 간단한 헤더 사용
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
                
                # 대체 API 엔드포인트
                url = f"https://query2.finance.yahoo.com/v1/finance/quoteSummary/{symbol}"
                params = {
                    "modules": "price,summaryDetail,defaultKeyStatistics"
                }
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("quoteSummary", {}).get("result", [])
                        if result:
                            summary = result[0]
                            price = summary.get("price", {})
                            summary_detail = summary.get("summaryDetail", {})
                            key_stats = summary.get("defaultKeyStatistics", {})
                            
                            # 추가 정보 병합
                            profile_info.update({
                                "market_cap": price.get("marketCap"),
                                "trailing_pe": price.get("trailingPE"),
                                "forward_pe": price.get("forwardPE"),
                                "dividend_yield": price.get("dividendYield"),
                                "dividend_rate": price.get("dividendRate"),
                                "beta": price.get("beta"),
                                "fifty_two_week_high": price.get("fiftyTwoWeekHigh"),
                                "fifty_two_week_low": price.get("fiftyTwoWeekLow"),
                                "price_to_book": price.get("priceToBook"),
                                "profit_margin": price.get("profitMargins"),
                                "operating_margin": price.get("operatingMargins"),
                                "return_on_assets": price.get("returnOnAssets"),
                                "return_on_equity": price.get("returnOnEquity"),
                                "revenue_growth": price.get("revenueGrowth"),
                                "earnings_growth": price.get("earningsGrowth"),
                                "analyst_rating": price.get("averageAnalystRating"),
                                "enterprise_value": price.get("enterpriseValue"),
                                "peg_ratio": price.get("pegRatio"),
                                "price_to_sales": price.get("priceToSalesTrailing12Months"),
                                "enterprise_to_revenue": price.get("enterpriseToRevenue"),
                                "enterprise_to_ebitda": price.get("enterpriseToEbitda")
                            })
                            
                            logger.info(f"Successfully fetched profile for {symbol} using alternative method")
            except Exception as e:
                logger.warning(f"Alternative profile fetch failed for {symbol}: {str(e)}")
            
            return profile_info
            
        except Exception as e:
            logger.error(f"Error fetching profile data for {symbol}: {str(e)}")
            return None
    
    def _transform_stock_data(self, data: Dict, symbol: str) -> Optional[StockData]:
        """Yahoo Finance 데이터를 StockData로 변환"""
        try:
            result = data.get("chart", {}).get("result", [])
            if not result:
                return None
            
            chart = result[0]
            meta = chart.get("meta", {})
            
            # 현재 가격 정보
            current_price = meta.get("regularMarketPrice")
            previous_close = meta.get("previousClose")
            open_price = meta.get("regularMarketOpen")
            day_high = meta.get("regularMarketDayHigh")
            day_low = meta.get("regularMarketDayLow")
            volume = meta.get("regularMarketVolume", 0)
            
            if current_price is None:
                return None
            
            return StockData(
                symbol=symbol,
                company_name=meta.get("symbol", symbol),
                current_price=float(current_price),
                previous_close=float(previous_close) if previous_close else 0.0,
                open_price=float(open_price) if open_price else 0.0,
                day_high=float(day_high) if day_high else 0.0,
                day_low=float(day_low) if day_low else 0.0,
                volume=int(volume),
                exchange=meta.get("exchangeName"),
                currency=meta.get("currency"),
                short_name=meta.get("shortName"),
                long_name=meta.get("longName"),
                timestamp=datetime.fromtimestamp(meta.get("regularMarketTime", time.time()), tz=timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error transforming stock data for {symbol}: {str(e)}")
            return None
    
    def _transform_historical_data(self, data: Dict, symbol: str) -> List[HistoricalData]:
        """Yahoo Finance 과거 데이터를 HistoricalData로 변환"""
        try:
            result = data.get("chart", {}).get("result", [])
            if not result:
                return []
            
            chart = result[0]
            timestamps = chart.get("timestamp", [])
            indicators = chart.get("indicators", {})
            
            quote = indicators.get("quote", [{}])[0]
            adjclose = indicators.get("adjclose", [{}])[0]
            
            historical_data = []
            
            # 데이터가 없는 경우 확인
            if not timestamps:
                logger.warning(f"No timestamps found for {symbol}")
                return []
            
            # 각 타임스탬프에 대한 데이터 처리
            for i, timestamp in enumerate(timestamps):
                # 데이터 유효성 확인
                open_values = quote.get("open", [])
                high_values = quote.get("high", [])
                low_values = quote.get("low", [])
                close_values = quote.get("close", [])
                volume_values = quote.get("volume", [])
                
                # 인덱스 범위 확인
                if i >= len(open_values) or i >= len(high_values) or i >= len(low_values) or i >= len(close_values) or i >= len(volume_values):
                    continue
                
                # None 값 확인
                open_val = open_values[i]
                high_val = high_values[i]
                low_val = low_values[i]
                close_val = close_values[i]
                volume_val = volume_values[i]
                
                # 유효한 데이터만 추가
                if all(val is not None for val in [open_val, high_val, low_val, close_val, volume_val]):
                    date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    
                    adj_close_val = None
                    if adjclose and adjclose.get("adjclose") and i < len(adjclose.get("adjclose", [])):
                        adj_close_val = adjclose.get("adjclose")[i]
                    
                    historical_data.append(HistoricalData(
                        symbol=symbol,
                        date=date_str,
                        open=float(open_val),
                        high=float(high_val),
                        low=float(low_val),
                        close=float(close_val),
                        volume=int(volume_val),
                        adj_close=float(adj_close_val) if adj_close_val is not None else None
                    ))
            
            logger.info(f"Transformed {len(historical_data)} historical data points for {symbol}")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error transforming historical data for {symbol}: {str(e)}")
            return []
    
    def _transform_search_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Yahoo Finance 검색 결과 변환"""
        try:
            quotes = data.get("quotes", [])
            
            results = []
            for quote in quotes:
                results.append({
                    "symbol": quote.get("symbol"),
                    "name": quote.get("shortname") or quote.get("longname"),
                    "exchange": quote.get("exchange"),
                    "type": quote.get("quoteType"),
                    "score": quote.get("score")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error transforming search results: {str(e)}")
            return []
    
    def _transform_profile_data(self, data: Dict) -> Optional[Dict[str, Any]]:
        """Yahoo Finance 프로필 데이터 변환"""
        try:
            result = data.get("quoteSummary", {}).get("result", [])
            if not result:
                return None
            
            summary = result[0]
            
            # 기본 정보
            price = summary.get("price", {})
            asset_profile = summary.get("assetProfile", {})
            summary_profile = summary.get("summaryProfile", {})
            
            return {
                "symbol": price.get("symbol"),
                "long_name": summary_profile.get("longName"),
                "short_name": summary_profile.get("shortName"),
                "sector": summary_profile.get("sector"),
                "industry": summary_profile.get("industry"),
                "website": asset_profile.get("website"),
                "employees": asset_profile.get("fullTimeEmployees"),
                "description": summary_profile.get("longBusinessSummary"),
                "city": asset_profile.get("city"),
                "country": asset_profile.get("country"),
                "currency": price.get("currency"),
                "market_cap": price.get("marketCap"),
                "enterprise_value": price.get("enterpriseValue"),
                "trailing_pe": price.get("trailingPE"),
                "forward_pe": price.get("forwardPE"),
                "peg_ratio": price.get("pegRatio"),
                "price_to_sales": price.get("priceToSalesTrailing12Months"),
                "price_to_book": price.get("priceToBook"),
                "enterprise_to_revenue": price.get("enterpriseToRevenue"),
                "enterprise_to_ebitda": price.get("enterpriseToEbitda"),
                "beta": price.get("beta"),
                "fifty_two_week_high": price.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": price.get("fiftyTwoWeekLow"),
                "dividend_yield": price.get("dividendYield"),
                "dividend_rate": price.get("dividendRate"),
                "ex_dividend_date": price.get("exDividendDate"),
                "payout_ratio": price.get("payoutRatio"),
                "profit_margin": price.get("profitMargins"),
                "operating_margin": price.get("operatingMargins"),
                "return_on_assets": price.get("returnOnAssets"),
                "return_on_equity": price.get("returnOnEquity"),
                "revenue_growth": price.get("revenueGrowth"),
                "earnings_growth": price.get("earningsGrowth"),
                "earnings_quarterly_growth": price.get("earningsQuarterlyGrowth"),
                "analyst_rating": price.get("averageAnalystRating")
            }
            
        except Exception as e:
            logger.error(f"Error transforming profile data: {str(e)}")
            return None
    
    async def _check_rate_limit(self) -> bool:
        """속도 제한 확인"""
        current_time = time.time()
        current_minute = int(current_time // 60)
        current_hour = int(current_time // 3600)
        
        # 분당 요청 수 초기화
        if current_minute != self.request_count["last_minute"]:
            self.request_count["minute"] = 0
            self.request_count["last_minute"] = current_minute
        
        # 시간당 요청 수 초기화
        if current_hour != self.request_count["last_hour"]:
            self.request_count["hour"] = 0
            self.request_count["last_hour"] = current_hour
        
        # 속도 제한 확인
        if self.request_count["minute"] >= self.rate_limits["requests_per_minute"]:
            return False
        
        if self.request_count["hour"] >= self.rate_limits["requests_per_hour"]:
            return False
        
        # 요청 수 증가
        self.request_count["minute"] += 1
        self.request_count["hour"] += 1
        
        return True
    
    async def _get_from_cache(self, key: str, data_type: str) -> Optional[Any]:
        """캐시에서 데이터 가져오기"""
        try:
            if not self.redis_client:
                return None
            
            cached_data = await self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    async def _save_to_cache(self, key: str, data: Any, data_type: str) -> None:
        """캐시에 데이터 저장"""
        try:
            if not self.redis_client:
                return
            
            ttl = self.cache_ttl.get(data_type, 300)
            await self.redis_client.setex(key, ttl, json.dumps(data))
            
        except Exception as e:
            logger.error(f"Error saving to cache: {str(e)}")
    
    async def invalidate_cache(self, symbol: str = None, pattern: str = None) -> bool:
        """
        캐시 무효화
        
        Args:
            symbol: 특정 심볼의 캐시 무효화 (선택적)
            pattern: 특정 패턴의 캐시 무효화 (선택적)
            
        Returns:
            성공 여부
        """
        try:
            if not self.redis_client:
                return False
            
            if symbol:
                # 특정 심볼 관련 캐시 무효화
                patterns = [
                    f"yahoo:stock:{symbol}",
                    f"yahoo:historical:{symbol}:*",
                    f"yahoo:profile:{symbol}"
                ]
                
                for pattern in patterns:
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
                        logger.info(f"Invalidated {len(keys)} cache entries for {symbol}")
                
            elif pattern:
                # 특정 패턴의 캐시 무효화
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries matching pattern: {pattern}")
            
            else:
                # 모든 Yahoo Finance 관련 캐시 무효화
                keys = await self.redis_client.keys("yahoo:*")
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} Yahoo Finance cache entries")
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보 가져오기
        
        Returns:
            캐시 통계 정보
        """
        try:
            if not self.redis_client:
                return {"error": "Redis client not available"}
            
            stats = {}
            
            # 캐시 키별 개수
            cache_types = {
                "stock": "yahoo:stock:*",
                "historical": "yahoo:historical:*",
                "profile": "yahoo:profile:*",
                "search": "yahoo:search:*"
            }
            
            for cache_type, pattern in cache_types.items():
                keys = await self.redis_client.keys(pattern)
                stats[cache_type] = len(keys)
            
            # 전체 캐시 개수
            all_keys = await self.redis_client.keys("yahoo:*")
            stats["total"] = len(all_keys)
            
            # 메모리 사용량 (Redis info에서 가져오기)
            info = await self.redis_client.info("memory")
            stats["memory_used"] = info.get("used_memory_human", "N/A")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"error": str(e)}
    
    async def _refresh_crumb_token(self) -> bool:
        """
        Crumb 토큰 갱신
        
        Returns:
            성공 여부
        """
        try:
            # Yahoo Finance 페이지 접속하여 쿠키와 Crumb 토큰获取
            url = "https://finance.yahoo.com/quote/AAPL"
            
            # 간단한 헤더 사용
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to get Yahoo Finance page: HTTP {response.status}")
                    return False
                
                # 페이지 내용에서 Crumb 토큰 추출
                content = await response.text()
                
                # Crumb 토큰 추출 (여러 패턴 시도)
                crumb_patterns = [
                    r'"CrumbStore":\{"crumb":"([^"]+)"\}',
                    r'crumb=([^&\s]+)',
                    r'window\.YAHOO\.context\.crumb=encodeURIComponent\("([^"]+)"\)',
                    r'Context\.Store\.crumb=encodeURIComponent\("([^"]+)"\)',
                    r'YAHOO\.context\.crumb=encodeURIComponent\("([^"]+)"\)'
                ]
                
                for pattern in crumb_patterns:
                    match = re.search(pattern, content)
                    if match:
                        self.crumb_token = match.group(1)
                        self.crumb_expiry = time.time() + self.crumb_cache_duration
                        logger.info(f"Successfully refreshed crumb token: {self.crumb_token[:10]}...")
                        return True
                
                # 대체 방법: API 엔드포인트에서 Crumb 토큰 가져오기
                crumb_url = "https://query1.finance.yahoo.com/v1/test/getcrumb"
                
                async with self.session.get(crumb_url, headers=headers) as crumb_response:
                    if crumb_response.status == 200:
                        crumb_text = await crumb_response.text()
                        if crumb_text and len(crumb_text) > 5:  # 유효한 Crumb 토큰 확인
                            self.crumb_token = crumb_text.strip()
                            self.crumb_expiry = time.time() + self.crumb_cache_duration
                            logger.info(f"Successfully refreshed crumb token from API: {self.crumb_token[:10]}...")
                            return True
                
                logger.error("Could not find crumb token in Yahoo Finance page")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing crumb token: {str(e)}")
            return False
    
    async def _ensure_valid_crumb(self) -> bool:
        """
        유효한 Crumb 토큰이 있는지 확인하고 필요시 갱신
        
        Returns:
            성공 여부
        """
        current_time = time.time()
        
        # Crumb 토큰이 없거나 만료된 경우 갱신
        if (not self.crumb_token or
            not self.crumb_expiry or
            current_time >= self.crumb_expiry):
            
            return await self._refresh_crumb_token()
        
        return True
    
    async def close(self):
        """서비스 종료"""
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Yahoo Finance Service closed")

# 전역 Yahoo Finance 서비스 인스턴스
yahoo_finance_service = YahooFinanceService()