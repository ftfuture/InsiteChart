# API 연동 및 데이터 소스 상세화

## 1. 외부 API 연동 전략

### 1.1 API 의존성 관리

#### 1.1.1 API 클라이언트 팩토리 패턴
```python
# api_clients/base_client.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class APIConfig:
    base_url: str
    api_key: str
    api_secret: str = None
    rate_limit: int = 100
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

class BaseAPIClient(ABC):
    def __init__(self, config: APIConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = None
        self.rate_limiter = RateLimiter(config.rate_limit)
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    @abstractmethod
    async def initialize(self):
        """API 클라이언트 초기화"""
        pass
    
    @abstractmethod
    async def close(self):
        """API 클라이언트 종료"""
        pass
    
    @abstractmethod
    async def authenticate(self):
        """API 인증"""
        pass
    
    async def make_request(self, method: str, endpoint: str, 
                          params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """API 요청 실행 (재시도 및 에러 처리 포함)"""
        for attempt in range(self.config.retry_attempts):
            try:
                # Rate Limiting 확인
                await self.rate_limiter.acquire()
                
                # 요청 실행
                response = await self._execute_request(method, endpoint, params, data)
                
                if response and self._is_success_response(response):
                    return response
                    
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    self.logger.error(f"All retry attempts failed: {str(e)}")
                    raise
        
        return None
    
    @abstractmethod
    async def _execute_request(self, method: str, endpoint: str, 
                               params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """실제 API 요청 실행"""
        pass
    
    def _is_success_response(self, response: Dict) -> bool:
        """성공 응답 확인"""
        return response.get('status') == 'success' or response.get('code') == 200

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        async with self._lock:
            now = datetime.now()
            # 오래된 요청 제거
            self.requests = [req for req in self.requests 
                            if now - req < timedelta(seconds=self.time_window)]
            
            if len(self.requests) >= self.max_requests:
                # 가장 오래된 요청 시간 계산
                wait_time = self.time_window - (now - self.requests[0]).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.requests.append(now)
```

#### 1.1.2 API 상태 모니터링
```python
# api_clients/health_monitor.py
from typing import Dict, List
from datetime import datetime, timedelta
import asyncio
import logging

class APIHealthMonitor:
    def __init__(self):
        self.clients = {}
        self.health_status = {}
        self.logger = logging.getLogger(__name__)
    
    def register_client(self, name: str, client: BaseAPIClient):
        """API 클라이언트 등록"""
        self.clients[name] = client
        self.health_status[name] = {
            'status': 'unknown',
            'last_check': None,
            'response_time': None,
            'error_count': 0,
            'last_error': None
        }
    
    async def start_monitoring(self, interval: int = 60):
        """상태 모니터링 시작"""
        while True:
            await self.check_all_clients()
            await asyncio.sleep(interval)
    
    async def check_all_clients(self):
        """모든 클라이언트 상태 확인"""
        tasks = []
        for name, client in self.clients.items():
            tasks.append(self._check_client_health(name, client))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_client_health(self, name: str, client: BaseAPIClient):
        """개별 클라이언트 상태 확인"""
        start_time = datetime.now()
        
        try:
            # 간단한 상태 확인 요청
            response = await client.make_request('GET', '/health')
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 상태 업데이트
            if response:
                self.health_status[name].update({
                    'status': 'healthy',
                    'last_check': datetime.now(),
                    'response_time': response_time,
                    'error_count': 0,
                    'last_error': None
                })
            else:
                self._increment_error_count(name)
                
        except Exception as e:
            self.logger.error(f"Health check failed for {name}: {str(e)}")
            self._increment_error_count(name, str(e))
    
    def _increment_error_count(self, name: str, error_message: str = None):
        """에러 카운트 증가"""
        self.health_status[name].update({
            'status': 'unhealthy',
            'last_check': datetime.now(),
            'error_count': self.health_status[name]['error_count'] + 1,
            'last_error': error_message
        })
    
    def get_health_summary(self) -> Dict:
        """상태 요약 정보 반환"""
        total_clients = len(self.clients)
        healthy_clients = sum(1 for status in self.health_status.values() 
                              if status['status'] == 'healthy')
        
        return {
            'total_clients': total_clients,
            'healthy_clients': healthy_clients,
            'unhealthy_clients': total_clients - healthy_clients,
            'health_percentage': (healthy_clients / total_clients * 100) if total_clients > 0 else 0,
            'status': 'healthy' if healthy_clients == total_clients else 'degraded',
            'details': self.health_status
        }
```

### 1.2 Yahoo Finance API 연동

#### 1.2.1 고급 Yahoo Finance 클라이언트
```python
# api_clients/yahoo_finance_client.py
import yfinance as yf
import requests
import asyncio
from typing import Dict, List, Optional
from .base_client import BaseAPIClient, APIConfig

class YahooFinanceClient(BaseAPIClient):
    def __init__(self, config: APIConfig):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
    
    async def initialize(self):
        """Yahoo Finance API 초기화"""
        try:
            # API 연결 테스트
            test_response = await self.make_request('GET', '/v1/finance/search', 
                                               params={'q': 'AAPL', 'quotesCount': 1})
            if test_response:
                self.logger.info("Yahoo Finance API initialized successfully")
            else:
                self.logger.warning("Yahoo Finance API initialization failed")
        except Exception as e:
            self.logger.error(f"Failed to initialize Yahoo Finance API: {str(e)}")
            raise
    
    async def close(self):
        """세션 종료"""
        if self.session:
            self.session.close()
    
    async def authenticate(self):
        """Yahoo Finance API는 인증이 필요 없음"""
        return True
    
    async def _execute_request(self, method: str, endpoint: str, 
                               params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """실제 Yahoo Finance API 요청"""
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.config.timeout
                )
            elif method.upper() == 'POST':
                response = self.session.post(
                    url, 
                    json=data, 
                    timeout=self.config.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Yahoo Finance API request failed: {str(e)}")
            return None
    
    async def search_stocks(self, query: str, max_results: int = 10) -> List[Dict]:
        """주식 검색"""
        try:
            # yfinance를 통한 검색 (대체 방법)
            tickers = yf.Tickers(query, session=self.session)
            
            results = []
            for ticker in tickers.tickers[:max_results]:
                try:
                    info = ticker.info
                    if info and 'symbol' in info:
                        result = {
                            'symbol': info.get('symbol', ''),
                            'company_name': info.get('longname') or info.get('shortname', ''),
                            'stock_type': info.get('quoteType', ''),
                            'exchange': info.get('exchange', ''),
                            'sector': info.get('sector', ''),
                            'industry': info.get('industry', ''),
                            'market_cap': info.get('marketCap'),
                            'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                            'currency': info.get('currency', 'USD')
                        }
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to process ticker {ticker.ticker}: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            self.logger.error(f"Stock search failed: {str(e)}")
            return []
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """주식 상세 정보 조회"""
        try:
            ticker = yf.Ticker(symbol, session=self.session)
            info = ticker.info
            
            if not info or 'symbol' not in info:
                return None
            
            # 기본 정보
            basic_info = {
                'symbol': info.get('symbol', symbol),
                'company_name': info.get('longName', ''),
                'stock_type': info.get('quoteType', ''),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'website': info.get('website', ''),
                'description': info.get('longBusinessSummary', ''),
                'employees': info.get('fullTimeEmployees'),
                'country': info.get('country', '')
            }
            
            # 가격 정보
            price_info = {
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'previous_close': info.get('previousClose'),
                'open': info.get('open'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'bid': info.get('bid'),
                'ask': info.get('ask'),
                'volume': info.get('volume'),
                'average_volume': info.get('averageVolume'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta')
            }
            
            # 52주 정보
            week_52_info = {
                'week_52_high': info.get('fiftyTwoWeekHigh'),
                'week_52_low': info.get('fiftyTwoWeekLow'),
                'week_52_change': info.get('fiftyTwoWeekChange'),
                'week_52_change_percent': info.get('fiftyTwoWeekChangePercent')
            }
            
            # 배당 정보
            dividend_info = {
                'dividend_rate': info.get('dividendRate'),
                'dividend_yield': info.get('dividendYield'),
                'ex_dividend_date': info.get('exDividendDate'),
                'payout_ratio': info.get('payoutRatio'),
                'dividend_date': info.get('dividendDate')
            }
            
            # 재무 정보
            financial_info = {
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'price_to_book': info.get('priceToBook'),
                'price_to_sales': info.get('priceToSales'),
                'revenue': info.get('totalRevenue'),
                'gross_profits': info.get('grossProfits'),
                'operating_margin': info.get('operatingMargins'),
                'return_on_equity': info.get('returnOnEquity')
            }
            
            return {
                **basic_info,
                **price_info,
                **week_52_info,
                **dividend_info,
                **financial_info,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stock info for {symbol}: {str(e)}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> Optional[List[Dict]]:
        """과거 가격 데이터 조회"""
        try:
            ticker = yf.Ticker(symbol, session=self.session)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
            
            # 데이터 변환
            historical_data = []
            for date, row in hist.iterrows():
                historical_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'adj_close': float(row['Adj Close']),
                    'volume': int(row['Volume'])
                })
            
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {str(e)}")
            return None
```

#### 1.2.2 Yahoo Finance 데이터 캐싱
```python
# api_clients/yahoo_finance_cache.py
import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class YahooFinanceCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 300  # 5분
        
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """캐시 키 생성"""
        key_data = {k: str(v) for k, v in sorted(kwargs.items())}
        key_string = json.dumps(key_data, sort_keys=True)
        hash_object = hashlib.md5(key_string.encode())
        return f"yahoo_finance:{prefix}:{hash_object.hexdigest()}"
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """주식 정보 캐시 조회"""
        cache_key = self._generate_cache_key('stock_info', symbol=symbol)
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_stock_info(self, symbol: str, data: Dict, ttl: int = None):
        """주식 정보 캐시 저장"""
        cache_key = self._generate_cache_key('stock_info', symbol=symbol)
        ttl = ttl or self.default_ttl
        
        await self.redis.setex(
            cache_key, 
            ttl, 
            json.dumps(data, default=str)
        )
    
    async def get_search_results(self, query: str, filters: Dict = None) -> Optional[List[Dict]]:
        """검색 결과 캐시 조회"""
        cache_key = self._generate_cache_key('search', query=query, **(filters or {}))
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_search_results(self, query: str, results: List[Dict], 
                             filters: Dict = None, ttl: int = None):
        """검색 결과 캐시 저장"""
        cache_key = self._generate_cache_key('search', query=query, **(filters or {}))
        ttl = ttl or self.default_ttl
        
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(results, default=str)
        )
    
    async def get_historical_data(self, symbol: str, period: str) -> Optional[List[Dict]]:
        """과거 데이터 캐시 조회"""
        cache_key = self._generate_cache_key('historical', symbol=symbol, period=period)
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_historical_data(self, symbol: str, period: str, 
                              data: List[Dict], ttl: int = None):
        """과거 데이터 캐시 저장"""
        cache_key = self._generate_cache_key('historical', symbol=symbol, period=period)
        ttl = ttl or self.default_ttl
        
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(data, default=str)
        )
    
    async def invalidate_symbol_cache(self, symbol: str):
        """특정 심볼 캐시 무효화"""
        patterns = [
            f"yahoo_finance:*:{symbol}:*",
            f"yahoo_finance:stock_info:*{symbol}*"
        ]
        
        for pattern in patterns:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
    
    async def get_cache_stats(self) -> Dict:
        """캐시 통계 정보"""
        info = await self.redis.info()
        
        return {
            'total_keys': info.get('used_memory', 0),
            'memory_usage': info.get('used_memory_human', '0B'),
            'hit_rate': await self._calculate_hit_rate(),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0)
        }
    
    async def _calculate_hit_rate(self) -> float:
        """캐시 적중률 계산"""
        stats = await self.redis.info()
        hits = stats.get('keyspace_hits', 0)
        misses = stats.get('keyspace_misses', 0)
        
        if hits + misses == 0:
            return 0.0
        
        return (hits / (hits + misses)) * 100
```

### 1.3 Reddit API 연동

#### 1.3.1 Reddit 클라이언트
```python
# api_clients/reddit_client.py
import praw
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
from .base_client import BaseAPIClient, APIConfig

class RedditClient(BaseAPIClient):
    def __init__(self, config: APIConfig):
        super().__init__(config)
        self.reddit = None
        self.subreddits = [
            'wallstreetbets', 'investing', 'stocks',
            'SecurityAnalysis', 'ValueInvesting',
            'StockMarket', 'pennystocks'
        ]
        
        # 주식 심볼 추출 정규식
        self.stock_pattern = re.compile(
            r'\$([A-Z]{1,5})\b|(?<!\w)([A-Z]{1,5})(?=\s|$|[,.!?])'
        )
        
        # 일반적인 단어 필터링
        self.common_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 
            'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY',
            'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY',
            'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'WHO',
            'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE',
            'TOO', 'USE', 'A', 'AN', 'AS', 'AT', 'BE', 'BY',
            'DO', 'GO', 'HE', 'IF', 'IN', 'IS', 'IT', 'ME',
            'NO', 'OF', 'ON', 'OR', 'SO', 'TO', 'UP', 'US'
        }
    
    async def initialize(self):
        """Reddit API 초기화"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.config.api_key,
                client_secret=self.config.api_secret,
                user_agent='InsiteChart/1.0'
            )
            
            # 인증 테스트
            await self._test_authentication()
            
            self.logger.info("Reddit API initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit API: {str(e)}")
            raise
    
    async def close(self):
        """Reddit 연결 종료"""
        if self.reddit:
            # PRAW은 명시적인 종료 메서드가 없음
            pass
    
    async def authenticate(self):
        """Reddit API 인증"""
        return True  # PRAW이 자동으로 처리
    
    async def _execute_request(self, method: str, endpoint: str, 
                               params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Reddit API는 PRAW를 통해 처리"""
        # PRAW는 별도적인 HTTP 요청이 필요 없음
        return None
    
    async def _test_authentication(self):
        """인증 테스트"""
        try:
            # 읽기 전용 테스트
            subreddit = self.reddit.subreddit('test')
            subreddit.display_name
            return True
        except Exception as e:
            self.logger.error(f"Reddit authentication test failed: {str(e)}")
            raise
    
    async def collect_mentions(self, timeframe: str = "24h") -> List[Dict]:
        """주식 언급 데이터 수집"""
        mentions = []
        time_limit = self._get_time_limit(timeframe)
        
        for subreddit_name in self.subreddits:
            try:
                subreddit_mentions = await self._collect_subreddit_mentions(
                    subreddit_name, time_limit
                )
                mentions.extend(subreddit_mentions)
                
                # Rate limiting 방지를 위한 지연
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"Failed to collect from r/{subreddit_name}: {str(e)}")
                continue
        
        return mentions
    
    async def _collect_subreddit_mentions(self, subreddit_name: str, 
                                      time_limit: datetime) -> List[Dict]:
        """서브레딧별 언급 수집"""
        mentions = []
        subreddit = self.reddit.subreddit(subreddit_name)
        
        try:
            # 핫 포스트 수집
            hot_posts = list(subreddit.hot(limit=50))
            for post in hot_posts:
                if post.created_utc < time_limit:
                    continue
                
                post_mentions = await self._extract_mentions_from_post(
                    post, subreddit_name, 'post'
                )
                mentions.extend(post_mentions)
            
            # 새 포스트 수집
            new_posts = list(subreddit.new(limit=100))
            for post in new_posts:
                if post.created_utc < time_limit:
                    continue
                
                post_mentions = await self._extract_mentions_from_post(
                    post, subreddit_name, 'post'
                )
                mentions.extend(post_mentions)
            
            # 댓글 수집 (인기 포스트에 한해)
            for post in hot_posts[:20]:  # 상위 20개 포스트만
                post.comments.replace_more(limit=0)
                for comment in post.comments.list():
                    if comment.created_utc < time_limit:
                        continue
                    
                    comment_mentions = await self._extract_mentions_from_comment(
                        comment, subreddit_name
                    )
                    mentions.extend(comment_mentions)
                    
        except Exception as e:
            self.logger.error(f"Error collecting from r/{subreddit_name}: {str(e)}")
        
        return mentions
    
    async def _extract_mentions_from_post(self, post, subreddit_name: str, 
                                         mention_type: str) -> List[Dict]:
        """포스트에서 주식 언급 추출"""
        text = f"{post.title} {post.selftext}"
        symbols = self._extract_stock_symbols(text)
        
        mentions = []
        for symbol in symbols:
            mention = {
                'symbol': symbol,
                'text': text,
                'source': 'reddit',
                'community': subreddit_name,
                'author': str(post.author),
                'timestamp': datetime.fromtimestamp(post.created_utc),
                'upvotes': post.score,
                'url': f"https://reddit.com{post.permalink}",
                'type': mention_type,
                'post_id': post.id,
                'title': post.title,
                'num_comments': post.num_comments
            }
            mentions.append(mention)
        
        return mentions
    
    async def _extract_mentions_from_comment(self, comment, 
                                         subreddit_name: str) -> List[Dict]:
        """댓글에서 주식 언급 추출"""
        symbols = self._extract_stock_symbols(comment.body)
        
        mentions = []
        for symbol in symbols:
            mention = {
                'symbol': symbol,
                'text': comment.body,
                'source': 'reddit',
                'community': subreddit_name,
                'author': str(comment.author),
                'timestamp': datetime.fromtimestamp(comment.created_utc),
                'upvotes': comment.score,
                'url': f"https://reddit.com{comment.permalink}",
                'type': 'comment',
                'comment_id': comment.id,
                'parent_id': comment.parent_id if hasattr(comment, 'parent_id') else None
            }
            mentions.append(mention)
        
        return mentions
    
    def _extract_stock_symbols(self, text: str) -> List[str]:
        """텍스트에서 주식 심볼 추출"""
        matches = self.stock_pattern.findall(text)
        symbols = []
        
        for match in matches:
            symbol = match[0] if match[0] else match[1]
            
            # 일반적인 단어 필터링
            if symbol.upper() in self.common_words:
                continue
            
            # 길이 유효성 검증 (1-5자)
            if 1 <= len(symbol) <= 5:
                symbols.append(symbol.upper())
        
        return list(set(symbols))  # 중복 제거
    
    def _get_time_limit(self, timeframe: str) -> datetime:
        """시간 제한 계산"""
        now = datetime.now()
        
        if timeframe == "1h":
            return now - timedelta(hours=1)
        elif timeframe == "24h":
            return now - timedelta(days=1)
        elif timeframe == "7d":
            return now - timedelta(days=7)
        elif timeframe == "30d":
            return now - timedelta(days=30)
        else:
            return now - timedelta(days=1)
    
    async def get_community_stats(self, subreddit_name: str) -> Dict:
        """커뮤니티 통계 정보"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            stats = {
                'name': subreddit.display_name,
                'subscribers': subreddit.subscribers,
                'created_utc': subreddit.created_utc,
                'description': subreddit.public_description,
                'over18': subreddit.over18,
                'user_flair_enabled': subreddit.user_flair_enabled,
                'link_flair_enabled': subreddit.link_flair_enabled
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats for r/{subreddit_name}: {str(e)}")
            return {}
```

### 1.4 Twitter API 연동

#### 1.4.1 Twitter 클라이언트
```python
# api_clients/twitter_client.py
import tweepy
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
from .base_client import BaseAPIClient, APIConfig

class TwitterClient(BaseAPIClient):
    def __init__(self, config: APIConfig):
        super().__init__(config)
        self.api = None
        self.client = None
        
        # 주식 심볼 추출 정규식
        self.stock_pattern = re.compile(
            r'\$([A-Z]{1,5})\b|(?<!\w)([A-Z]{1,5})(?=\s|$|[,.!?])'
        )
        
        # 검색 키워드
        self.search_keywords = [
            'stocks', 'investing', 'trading', 'market', 'finance',
            'bullish', 'bearish', 'buy', 'sell', 'hold'
        ]
    
    async def initialize(self):
        """Twitter API 초기화"""
        try:
            # v1.1 API 클라이언트
            auth = tweepy.OAuth1UserHandler(
                self.config.api_key,
                self.config.api_secret,
                self.config.access_token,
                self.config.access_token_secret
            )
            
            self.api = tweepy.API(auth)
            
            # v2 API 클라이언트
            self.client = tweepy.Client(
                bearer_token=self.config.bearer_token,
                consumer_key=self.config.api_key,
                consumer_secret=self.config.api_secret,
                access_token=self.config.access_token,
                access_token_secret=self.config.access_token_secret
            )
            
            # 인증 테스트
            await self._test_authentication()
            
            self.logger.info("Twitter API initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Twitter API: {str(e)}")
            raise
    
    async def close(self):
        """Twitter 연결 종료"""
        if self.client:
            self.client.close()
    
    async def authenticate(self):
        """Twitter API 인증"""
        return True  # Tweepy가 자동으로 처리
    
    async def _execute_request(self, method: str, endpoint: str, 
                               params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Twitter API는 Tweepy를 통해 처리"""
        # Tweepy는 별도적인 HTTP 요청이 필요 없음
        return None
    
    async def _test_authentication(self):
        """인증 테스트"""
        try:
            me = self.client.get_me()
            return me is not None
        except Exception as e:
            self.logger.error(f"Twitter authentication test failed: {str(e)}")
            raise
    
    async def collect_mentions(self, query: str = None, timeframe: str = "24h") -> List[Dict]:
        """주식 언급 데이터 수집"""
        mentions = []
        
        if not query:
            # 기본 검색어 사용
            query = " OR ".join([f"${symbol}" for symbol in ["AAPL", "TSLA", "GME", "AMC"]])
        
        try:
            # v2 API 사용 (Recent Search)
            tweets = tweepy.Paginator(
                self.client.search_recent_tweets,
                query=query,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations'],
                max_results=100
            )
            
            time_limit = self._get_time_limit(timeframe)
            
            for tweet in tweets:
                if tweet.created_at < time_limit:
                    continue
                
                tweet_mentions = await self._extract_mentions_from_tweet(tweet)
                mentions.extend(tweet_mentions)
                
        except Exception as e:
            self.logger.error(f"Twitter search failed: {str(e)}")
        
        return mentions
    
    async def collect_mentions_by_symbols(self, symbols: List[str], 
                                             timeframe: str = "24h") -> List[Dict]:
        """심볼별 언급 수집"""
        all_mentions = []
        
        for symbol in symbols:
            try:
                # 각 심볼에 대한 검색
                query = f"${symbol}"
                symbol_mentions = await self.collect_mentions(query, timeframe)
                
                # 심볼 정보 추가
                for mention in symbol_mentions:
                    mention['symbol'] = symbol
                
                all_mentions.extend(symbol_mentions)
                
                # Rate limiting 방지
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"Failed to collect mentions for {symbol}: {str(e)}")
                continue
        
        return all_mentions
    
    async def _extract_mentions_from_tweet(self, tweet) -> List[Dict]:
        """트윗에서 주식 언급 추출"""
        text = tweet.text or ""
        symbols = self._extract_stock_symbols(text)
        
        mentions = []
        for symbol in symbols:
            mention = {
                'symbol': symbol,
                'text': text,
                'source': 'twitter',
                'community': 'general',
                'author': str(tweet.author_id),
                'timestamp': tweet.created_at,
                'upvotes': tweet.public_metrics.get('like_count', 0),
                'retweets': tweet.public_metrics.get('retweet_count', 0),
                'replies': tweet.public_metrics.get('reply_count', 0),
                'quotes': tweet.public_metrics.get('quote_count', 0),
                'url': f"https://twitter.com/user/status/{tweet.id}",
                'type': 'tweet',
                'tweet_id': tweet.id,
                'lang': tweet.lang or 'en'
            }
            mentions.append(mention)
        
        return mentions
    
    def _extract_stock_symbols(self, text: str) -> List[str]:
        """텍스트에서 주식 심볼 추출"""
        matches = self.stock_pattern.findall(text)
        symbols = []
        
        for match in matches:
            symbol = match[0] if match[0] else match[1]
            
            # 길이 유효성 검증 (1-5자)
            if 1 <= len(symbol) <= 5:
                symbols.append(symbol.upper())
        
        return list(set(symbols))  # 중복 제거
    
    def _get_time_limit(self, timeframe: str) -> datetime:
        """시간 제한 계산"""
        now = datetime.now()
        
        if timeframe == "1h":
            return now - timedelta(hours=1)
        elif timeframe == "24h":
            return now - timedelta(days=1)
        elif timeframe == "7d":
            return now - timedelta(days=7)
        elif timeframe == "30d":
            return now - timedelta(days=30)
        else:
            return now - timedelta(days=1)
    
    async def get_trending_topics(self) -> List[Dict]:
        """트렌딩 토픽 조회"""
        try:
            # v2 API 사용 (Trending)
            trending = self.client.get_place_trends(
                id=1,  # Worldwide
                exclude_hashtags=True
            )
            
            topics = []
            for trend in trending[0]['trends'][:20]:  # 상위 20개
                if any(keyword in trend['name'].lower() 
                       for keyword in self.search_keywords):
                    topics.append({
                        'name': trend['name'],
                        'url': trend['url'],
                        'promoted_content': trend.get('promoted_content', False),
                        'tweet_volume': trend.get('tweet_volume', 0)
                    })
            
            return topics
            
        except Exception as e:
            self.logger.error(f"Failed to get trending topics: {str(e)}")
            return []
    
    async def get_user_tweets(self, username: str, count: int = 100) -> List[Dict]:
        """특정 사용자 트윗 수집"""
        try:
            user = self.client.get_user(username=username)
            if not user:
                return []
            
            tweets = tweepy.Paginator(
                self.client.get_users_tweets,
                id=user.id,
                max_results=count,
                tweet_fields=['created_at', 'public_metrics', 'context_annotations']
            )
            
            user_tweets = []
            for tweet in tweets:
                user_tweets.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'public_metrics': tweet.public_metrics,
                    'url': f"https://twitter.com/user/status/{tweet.id}"
                })
            
            return user_tweets
            
        except Exception as e:
            self.logger.error(f"Failed to get tweets for {username}: {str(e)}")
            return []
```

### 1.5 데이터 소스 관리자

#### 1.5.1 통합 데이터 수집 관리자
```python
# data_sources/data_collection_manager.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

class DataCollectionManager:
    def __init__(self, yahoo_client, reddit_client, twitter_client, 
                         message_queue, cache_manager):
        self.yahoo_client = yahoo_client
        self.reddit_client = reddit_client
        self.twitter_client = twitter_client
        self.message_queue = message_queue
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # 수집 설정
        self.collection_intervals = {
            'stock_data': 300,      # 5분
            'reddit_mentions': 600,  # 10분
            'twitter_mentions': 900, # 15분
            'trending_detection': 1800 # 30분
        }
        
        self.last_collection_times = {}
    
    async def start_collection(self):
        """데이터 수집 시작"""
        self.logger.info("Starting data collection manager")
        
        # 각 수집 작업을 별도 태스크로 실행
        tasks = [
            asyncio.create_task(self._collect_stock_data()),
            asyncio.create_task(self._collect_reddit_mentions()),
            asyncio.create_task(self._collect_twitter_mentions()),
            asyncio.create_task(self._detect_trending_stocks())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _collect_stock_data(self):
        """주식 데이터 수집"""
        while True:
            try:
                # 인기 주식 목록 (실제로는 데이터베이스에서 조회)
                popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN', 'NVDA']
                
                for symbol in popular_symbols:
                    # 캐시 확인
                    cached_data = await self.cache_manager.get_stock_info(symbol)
                    
                    if not cached_data:
                        # API 호출
                        stock_info = await self.yahoo_client.get_stock_info(symbol)
                        
                        if stock_info:
                            # 캐시 저장
                            await self.cache_manager.set_stock_info(symbol, stock_info)
                            
                            # 메시지 큐에 전송
                            await self.message_queue.publish('stock_data_update', {
                                'symbol': symbol,
                                'data': stock_info,
                                'source': 'yahoo_finance'
                            })
                    
                    # Rate limiting 방지
                    await asyncio.sleep(1)
                
                self.last_collection_times['stock_data'] = datetime.now()
                
                # 다음 수집까지 대기
                await asyncio.sleep(self.collection_intervals['stock_data'])
                
            except Exception as e:
                self.logger.error(f"Stock data collection error: {str(e)}")
                await asyncio.sleep(60)  # 에러 발생 시 1분 대기
    
    async def _collect_reddit_mentions(self):
        """Reddit 언급 데이터 수집"""
        while True:
            try:
                # 언급 데이터 수집
                mentions = await self.reddit_client.collect_mentions("24h")
                
                if mentions:
                    # 메시지 큐에 전송
                    for mention in mentions:
                        await self.message_queue.publish('reddit_mention', {
                            'mention': mention,
                            'source': 'reddit'
                        })
                
                self.last_collection_times['reddit_mentions'] = datetime.now()
                
                # 다음 수집까지 대기
                await asyncio.sleep(self.collection_intervals['reddit_mentions'])
                
            except Exception as e:
                self.logger.error(f"Reddit mentions collection error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _collect_twitter_mentions(self):
        """Twitter 언급 데이터 수집"""
        while True:
            try:
                # 언급 데이터 수집
                mentions = await self.twitter_client.collect_mentions()
                
                if mentions:
                    # 메시지 큐에 전송
                    for mention in mentions:
                        await self.message_queue.publish('twitter_mention', {
                            'mention': mention,
                            'source': 'twitter'
                        })
                
                self.last_collection_times['twitter_mentions'] = datetime.now()
                
                # 다음 수집까지 대기
                await asyncio.sleep(self.collection_intervals['twitter_mentions'])
                
            except Exception as e:
                self.logger.error(f"Twitter mentions collection error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _detect_trending_stocks(self):
        """트렌딩 주식 감지"""
        while True:
            try:
                # 최근 언급 데이터 분석 (실제로는 데이터베이스에서 조회)
                trending_stocks = await self._analyze_trending_patterns()
                
                if trending_stocks:
                    # 메시지 큐에 전송
                    await self.message_queue.publish('trending_update', {
                        'trending_stocks': trending_stocks,
                        'detection_time': datetime.now().isoformat()
                    })
                
                self.last_collection_times['trending_detection'] = datetime.now()
                
                # 다음 분석까지 대기
                await asyncio.sleep(self.collection_intervals['trending_detection'])
                
            except Exception as e:
                self.logger.error(f"Trending detection error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _analyze_trending_patterns(self) -> List[Dict]:
        """트렌딩 패턴 분석"""
        # 실제 구현에서는 데이터베이스에서 최근 언급 데이터를 조회하고
        # 기준 시간 대비 증가율 계산
        # 이 예시에서는 더미 데이터 반환
        
        trending_stocks = [
            {
                'symbol': 'TSLA',
                'current_mentions': 1250,
                'baseline_mentions': 200,
                'growth_rate': 525,  # 525% 증가
                'trend_score': 0.95,
                'trend_start_time': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'symbol': 'GME',
                'current_mentions': 890,
                'baseline_mentions': 150,
                'growth_rate': 493,  # 493% 증가
                'trend_score': 0.88,
                'trend_start_time': (datetime.now() - timedelta(hours=3)).isoformat()
            }
        ]
        
        return trending_stocks
    
    def get_collection_status(self) -> Dict:
        """수집 상태 정보"""
        now = datetime.now()
        status = {}
        
        for source, last_time in self.last_collection_times.items():
            if last_time:
                time_since_last = now - last_time
                status[source] = {
                    'last_collection': last_time.isoformat(),
                    'seconds_since_last': time_since_last.total_seconds(),
                    'is_overdue': time_since_last.total_seconds() > self.collection_intervals.get(source, 300) * 1.5,
                    'interval': self.collection_intervals.get(source, 300)
                }
            else:
                status[source] = {
                    'last_collection': None,
                    'seconds_since_last': None,
                    'is_overdue': True,
                    'interval': self.collection_intervals.get(source, 300)
                }
        
        return status
    
    async def trigger_manual_collection(self, source: str):
        """수동 데이터 수집 트리거"""
        self.logger.info(f"Manual collection triggered for {source}")
        
        if source == 'reddit':
            await self._collect_reddit_mentions()
        elif source == 'twitter':
            await self._collect_twitter_mentions()
        elif source == 'stock_data':
            await self._collect_stock_data()
        elif source == 'trending':
            await self._detect_trending_stocks()
        else:
            self.logger.warning(f"Unknown source for manual collection: {source}")
```

## 2. 데이터 품질 관리

### 2.1 데이터 검증 및 정제

#### 2.1.1 데이터 검증기
```python
# data_quality/validator.py
from typing import Dict, List, Optional, Any
from datetime import datetime
import re
import logging

class DataValidator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 주식 심볼 유효성 패턴
        self.stock_symbol_pattern = re.compile(r'^[A-Z]{1,5}$')
        
        # 스팸 필터링 패턴
        self.spam_patterns = [
            re.compile(r'buy\s+now', re.IGNORECASE),
            re.compile(r'click\s+here', re.IGNORECASE),
            re.compile(r'check\s+my\s+profile', re.IGNORECASE),
            re.compile(r'follow\s+me', re.IGNORECASE)
        ]
        
        # 중요 키워드
        self.important_keywords = [
            'buy', 'sell', 'hold', 'long', 'short', 'bullish', 'bearish',
            'moon', 'rocket', 'crash', 'dip', 'pump', 'dump'
        ]
    
    def validate_stock_symbol(self, symbol: str) -> bool:
        """주식 심볼 유효성 검증"""
        if not symbol:
            return False
        
        return bool(self.stock_symbol_pattern.match(symbol))
    
    def validate_mention_text(self, text: str, symbol: str) -> bool:
        """언급 텍스트 검증"""
        if not text or not symbol:
            return False
        
        # 최소 길이 검증
        if len(text.strip()) < 10:
            return False
        
        # 심볼 포함 확인
        if symbol.lower() not in text.lower():
            return False
        
        # 스팸 필터링
        for pattern in self.spam_patterns:
            if pattern.search(text):
                self.logger.debug(f"Filtered spam: {text[:50]}...")
                return False
        
        # 의미 있는 내용 확인
        has_important_keyword = any(
            keyword in text.lower() 
            for keyword in self.important_keywords
        )
        
        return has_important_keyword
    
    def validate_price_data(self, price_data: Dict) -> bool:
        """가격 데이터 유효성 검증"""
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        
        for field in required_fields:
            if field not in price_data:
                self.logger.warning(f"Missing required field: {field}")
                return False
            
            value = price_data[field]
            if not isinstance(value, (int, float)) or value <= 0:
                self.logger.warning(f"Invalid price value for {field}: {value}")
                return False
        
        # OHLC 관계 검증
        open_price = float(price_data['open'])
        high_price = float(price_data['high'])
        low_price = float(price_data['low'])
        close_price = float(price_data['close'])
        
        if not (low_price <= open_price <= high_price and 
                low_price <= close_price <= high_price):
            self.logger.warning(f"Invalid OHLC relationship: {price_data}")
            return False
        
        return True
    
    def validate_sentiment_score(self, score: float) -> bool:
        """센티먼트 점수 유효성 검증"""
        if not isinstance(score, (int, float)):
            return False
        
        return -1.0 <= score <= 1.0
    
    def validate_timestamp(self, timestamp: Any) -> bool:
        """타임스탬프 유효성 검증"""
        if isinstance(timestamp, str):
            try:
                datetime.fromisoformat(timestamp)
                return True
            except ValueError:
                return False
        elif isinstance(timestamp, datetime):
            return True
        else:
            return False
    
    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # 여러 공백 문자를 단일 공백으로
        text = re.sub(r'\s+', ' ', text)
        
        # 특수문자 제거 (URL, 이메일 등)
        text = re.sub(r'https?://\S+', '[URL]', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        return text.strip()
    
    def validate_batch(self, data_list: List[Dict], data_type: str) -> List[Dict]:
        """배치 데이터 검증"""
        validated_data = []
        validation_errors = []
        
        for i, item in enumerate(data_list):
            try:
                if data_type == 'stock_mentions':
                    validated_item = self._validate_mention(item)
                elif data_type == 'price_data':
                    validated_item = self._validate_price_data_item(item)
                elif data_type == 'sentiment_data':
                    validated_item = self._validate_sentiment_item(item)
                else:
                    validated_item = item  # 기본적으로 통과
                
                if validated_item:
                    validated_data.append(validated_item)
                else:
                    validation_errors.append(f"Item {i} validation failed")
                    
            except Exception as e:
                self.logger.error(f"Error validating item {i}: {str(e)}")
                validation_errors.append(f"Item {i} validation error: {str(e)}")
        
        if validation_errors:
            self.logger.warning(f"Validation errors: {validation_errors}")
        
        return validated_data
    
    def _validate_mention(self, mention: Dict) -> Optional[Dict]:
        """언급 데이터 검증"""
        # 필수 필드 확인
        required_fields = ['symbol', 'text', 'source', 'timestamp']
        for field in required_fields:
            if field not in mention:
                return None
        
        # 심볼 유효성 검증
        if not self.validate_stock_symbol(mention['symbol']):
            return None
        
        # 텍스트 검증
        if not self.validate_mention_text(mention['text'], mention['symbol']):
            return None
        
        # 타임스탬프 검증
        if not self.validate_timestamp(mention['timestamp']):
            return None
        
        # 텍스트 정제
        mention['text'] = self.clean_text(mention['text'])
        
        return mention
    
    def _validate_price_data_item(self, item: Dict) -> Optional[Dict]:
        """가격 데이터 항목 검증"""
        if not self.validate_price_data(item):
            return None
        
        return item
    
    def _validate_sentiment_item(self, item: Dict) -> Optional[Dict]:
        """센티먼트 데이터 항목 검증"""
        if 'sentiment_score' in item:
            if not self.validate_sentiment_score(item['sentiment_score']):
                return None
        
        return item
```

#### 2.1.2 데이터 정제 파이프라인
```python
# data_quality/pipeline.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

class DataQualityPipeline:
    def __init__(self, validator, cache_manager):
        self.validator = validator
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # 정제 규칙
        self.deduplication_window = timedelta(hours=1)
        self.min_text_length = 10
        self.max_text_length = 10000
    
    async def process_mentions(self, mentions: List[Dict]) -> List[Dict]:
        """언급 데이터 정제 파이프라인"""
        self.logger.info(f"Processing {len(mentions)} mentions")
        
        # 1. 데이터 검증
        validated_mentions = self.validator.validate_batch(mentions, 'stock_mentions')
        self.logger.info(f"Validated {len(validated_mentions)} mentions")
        
        # 2. 중복 제거
        deduplicated_mentions = await self._deduplicate_mentions(validated_mentions)
        self.logger.info(f"Deduplicated to {len(deduplicated_mentions)} mentions")
        
        # 3. 품질 필터링
        filtered_mentions = self._filter_by_quality(deduplicated_mentions)
        self.logger.info(f"Filtered to {len(filtered_mentions)} mentions")
        
        # 4. 풍성화
        enriched_mentions = await self._enrich_mentions(filtered_mentions)
        
        return enriched_mentions
    
    async def _deduplicate_mentions(self, mentions: List[Dict]) -> List[Dict]:
        """중복 언급 제거"""
        seen_mentions = set()
        deduplicated = []
        
        for mention in mentions:
            # 중복 키 생성 (심볼, 소스, 작성자, 타임스탬프)
            dedupe_key = (
                f"{mention['symbol']}_{mention['source']}_"
                f"{mention.get('author', '')}_"
                f"{mention.get('timestamp', '')}"
            )
            
            # 텍스트 내용 기반 중복 확인
            text_hash = hash(mention.get('text', ''))
            
            if dedupe_key not in seen_mentions and text_hash not in seen_mentions:
                seen_mentions.add(dedupe_key)
                seen_mentions.add(text_hash)
                deduplicated.append(mention)
        
        return deduplicated
    
    def _filter_by_quality(self, mentions: List[Dict]) -> List[Dict]:
        """품질 기반 필터링"""
        filtered = []
        
        for mention in mentions:
            text = mention.get('text', '')
            
            # 최소 길이 필터링
            if len(text) < self.min_text_length:
                continue
            
            # 최대 길이 필터링
            if len(text) > self.max_text_length:
                continue
            
            # 스팸 가능성 필터링
            if self._is_likely_spam(text):
                continue
            
            # 의미 있는 내용 확인
            if not self._has_meaningful_content(text):
                continue
            
            filtered.append(mention)
        
        return filtered
    
    def _is_likely_spam(self, text: str) -> bool:
        """스팸 가능성 확인"""
        spam_indicators = [
            # 반복되는 문자
            len(set(text)) < len(text) * 0.3,
            # 과도한 대문자
            text.count('!') > 5,
            # 단어 수 비율 (너무 적은 단어)
            len(text.split()) < len(text) * 0.05,
            # 링크 비율 (너무 많은 링크)
            text.count('http') > 3
        ]
        
        return any(indicator for indicator in spam_indicators)
    
    def _has_meaningful_content(self, text: str) -> bool:
        """의미 있는 내용 확인"""
        # 금융 관련 키워드
        financial_keywords = [
            'stock', 'share', 'price', 'market', 'trade', 'buy', 'sell',
            'bull', 'bear', 'call', 'put', 'option', 'future',
            'dividend', 'earnings', 'revenue', 'profit', 'loss'
        ]
        
        # 감정 표현
        sentiment_words = [
            'good', 'bad', 'great', 'terrible', 'amazing', 'awful',
            'love', 'hate', 'recommend', 'avoid', 'strong', 'weak'
        ]
        
        text_lower = text.lower()
        
        # 금융 또는 감정 키워드 포함 확인
        has_financial = any(keyword in text_lower for keyword in financial_keywords)
        has_sentiment = any(word in text_lower for word in sentiment_words)
        
        return has_financial or has_sentiment
    
    async def _enrich_mentions(self, mentions: List[Dict]) -> List[Dict]:
        """언급 데이터 풍성화"""
        enriched = []
        
        for mention in mentions:
            try:
                # 시간대별 분류
                mention['time_category'] = self._categorize_time(mention.get('timestamp'))
                
                # 커뮤니티 유형 분류
                mention['community_type'] = self._categorize_community(mention.get('community', ''))
                
                # 텍스트 분석
                mention['text_analysis'] = self._analyze_text(mention.get('text', ''))
                
                # 신뢰도 평가
                mention['credibility_score'] = self._calculate_credibility(mention)
                
                enriched.append(mention)
                
            except Exception as e:
                self.logger.error(f"Error enriching mention: {str(e)}")
                enriched.append(mention)  # 원본 데이터 유지
        
        return enriched
    
    def _categorize_time(self, timestamp: str) -> str:
        """시간대별 분류"""
        if not timestamp:
            return 'unknown'
        
        try:
            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour
            
            if 6 <= hour < 12:
                return 'morning'
            elif 12 <= hour < 18:
                return 'afternoon'
            elif 18 <= hour < 22:
                return 'evening'
            else:
                return 'night'
                
        except:
            return 'unknown'
    
    def _categorize_community(self, community: str) -> str:
        """커뮤니티 유형 분류"""
        community_lower = community.lower()
        
        if any(keyword in community_lower for keyword in ['wallstreetbets', 'pennystocks']):
            return 'day_trading'
        elif any(keyword in community_lower for keyword in ['valueinvesting', 'securityanalysis']):
            return 'value_investing'
        elif any(keyword in community_lower for keyword in ['investing', 'stocks']):
            return 'general'
        else:
            return 'other'
    
    def _analyze_text(self, text: str) -> Dict:
        """텍스트 분석"""
        return {
            'length': len(text),
            'word_count': len(text.split()),
            'has_urls': 'http' in text.lower(),
            'has_numbers': any(char.isdigit() for char in text),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'uppercase_ratio': sum(1 for c in text if c.isupper()) / len(text) if text else 0
        }
    
    def _calculate_credibility(self, mention: Dict) -> float:
        """신뢰도 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 업보트 수 기반 신뢰도
        upvotes = mention.get('upvotes', 0)
        if upvotes > 0:
            score += min(upvotes / 1000, 0.3)  # 최대 0.3
        
        # 텍스트 품질 기반 신뢰도
        text = mention.get('text', '')
        if len(text) > 50 and len(text) < 500:
            score += 0.1
        
        # 작성자 신뢰도 (실제로는 사용자 이력 기반)
        author = mention.get('author', '')
        if author and not author.startswith('u/'):  # 실제 사용자
            score += 0.1
        
        return min(score, 1.0)
```

## 3. 실시간 데이터 스트리밍

### 3.1 웹소켓 연동

#### 3.1.1 웹소켓 클라이언트
```python
# realtime/websocket_manager.py
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Callable
from datetime import datetime
import websockets
from fastapi import WebSocket, WebSocketDisconnect

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_subscriptions: Dict[str, Set[str]] = {}
        self.logger = logging.getLogger(__name__)
        
        # 구독 주제
        self.available_topics = [
            'stock_updates',
            'sentiment_changes',
            'trending_alerts',
            'price_alerts'
        ]
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """웹소켓 연결"""
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = set()
        
        self.logger.info(f"User {user_id} connected via WebSocket")
        
        # 연결 환영 전송
        await self._send_personal_message(user_id, {
            'type': 'connection',
            'message': 'Connected successfully',
            'available_topics': self.available_topics,
            'timestamp': datetime.now().isoformat()
        })
        
        # 활성 사용자 수 브로드캐스트
        await self._broadcast_active_users()
    
    async def disconnect(self, user_id: str):
        """웹소켓 연결 해제"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        
        self.logger.info(f"User {user_id} disconnected")
        
        # 활성 사용자 수 브로드캐스트
        await self._broadcast_active_users()
    
    async def subscribe(self, websocket: WebSocket, user_id: str, topic: str):
        """주제 구독"""
        if topic not in self.available_topics:
            await self._send_error(websocket, f"Invalid topic: {topic}")
            return
        
        self.user_subscriptions[user_id].add(topic)
        
        self.logger.info(f"User {user_id} subscribed to {topic}")
        
        await self._send_personal_message(user_id, {
            'type': 'subscription',
            'topic': topic,
            'message': f'Subscribed to {topic}',
            'timestamp': datetime.now().isoformat()
        })
    
    async def unsubscribe(self, websocket: WebSocket, user_id: str, topic: str):
        """주제 구독 해제"""
        if topic in self.user_subscriptions.get(user_id, set()):
            self.user_subscriptions[user_id].remove(topic)
            
            await self._send_personal_message(user_id, {
                'type': 'unsubscription',
                'topic': topic,
                'message': f'Unsubscribed from {topic}',
                'timestamp': datetime.now().isoformat()
            })
    
    async def broadcast_to_topic(self, topic: str, message: Dict):
        """주제별 메시지 브로드캐스트"""
        disconnected_users = []
        
        for user_id, subscriptions in self.user_subscriptions.items():
            if topic in subscriptions and user_id in self.active_connections:
                try:
                    await self._send_personal_message(user_id, {
                        'type': 'broadcast',
                        'topic': topic,
                        'data': message,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"Failed to send message to {user_id}: {str(e)}")
                    disconnected_users.append(user_id)
        
        # 연결이 끊긴 사용자 정리
        for user_id in disconnected_users:
            await self.disconnect(user_id)
    
    async def broadcast_to_all(self, message: Dict):
        """모든 사용자에게 메시지 브로드캐스트"""
        for user_id in list(self.active_connections.keys()):
            try:
                await self._send_personal_message(user_id, {
                    'type': 'broadcast',
                    'data': message,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"Failed to send broadcast to {user_id}: {str(e)}")
                await self.disconnect(user_id)
    
    async def _send_personal_message(self, user_id: str, message: Dict):
        """개인 메시지 전송"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Failed to send message to {user_id}: {str(e)}")
                await self.disconnect(user_id)
    
    async def _send_error(self, websocket: WebSocket, error_message: str):
        """에러 메시지 전송"""
        error_message = {
            'type': 'error',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            await websocket.send_text(json.dumps(error_message))
        except Exception as e:
            self.logger.error(f"Failed to send error message: {str(e)}")
    
    async def _broadcast_active_users(self):
        """활성 사용자 수 브로드캐스트"""
        active_count = len(self.active_connections)
        
        message = {
            'type': 'system',
            'message': f'Active users: {active_count}',
            'active_count': active_count,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.broadcast_to_all(message)
    
    def get_connection_stats(self) -> Dict:
        """연결 통계 정보"""
        return {
            'active_connections': len(self.active_connections),
            'total_subscriptions': sum(len(subs) for subs in self.user_subscriptions.values()),
            'subscriptions_by_topic': {
                topic: sum(1 for subs in self.user_subscriptions.values() if topic in subs)
                for topic in self.available_topics
            }
        }
```

#### 3.1.2 실시간 이벤트 처리
```python
# realtime/event_processor.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

class EventProcessor:
    def __init__(self, websocket_manager, cache_manager, message_queue):
        self.websocket_manager = websocket_manager
        self.cache_manager = cache_manager
        self.message_queue = message_queue
        self.logger = logging.getLogger(__name__)
        
        # 이벤트 핸들러
        self.event_handlers = {
            'stock_price_update': self._handle_stock_price_update,
            'sentiment_change': self._handle_sentiment_change,
            'trending_alert': self._handle_trending_alert,
            'new_mention': self._handle_new_mention,
            'user_activity': self._handle_user_activity
        }
    
    async def start_processing(self):
        """이벤트 처리 시작"""
        self.logger.info("Starting event processor")
        
        while True:
            try:
                # 메시지 큐에서 이벤트 수신
                event_data = await self.message_queue.consume('realtime_events')
                
                if event_data:
                    await self._process_event(event_data)
                
            except Exception as e:
                self.logger.error(f"Event processing error: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_event(self, event_data: Dict):
        """이벤트 처리"""
        event_type = event_data.get('type')
        event_payload = event_data.get('payload', {})
        
        handler = self.event_handlers.get(event_type)
        if handler:
            await handler(event_payload)
        else:
            self.logger.warning(f"Unknown event type: {event_type}")
    
    async def _handle_stock_price_update(self, payload: Dict):
        """주식 가격 업데이트 이벤트 처리"""
        symbol = payload.get('symbol')
        new_price = payload.get('price')
        old_price = payload.get('old_price')
        change_percent = payload.get('change_percent')
        
        if not all([symbol, new_price]):
            return
        
        # 캐시 업데이트
        await self.cache_manager.set_stock_price(symbol, {
            'price': new_price,
            'old_price': old_price,
            'change_percent': change_percent,
            'timestamp': datetime.now().isoformat()
        })
        
        # 웹소켓 브로드캐스트
        message = {
            'symbol': symbol,
            'new_price': new_price,
            'old_price': old_price,
            'change_percent': change_percent,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.websocket_manager.broadcast_to_topic('stock_updates', message)
        
        self.logger.info(f"Stock price update broadcasted for {symbol}: {new_price}")
    
    async def _handle_sentiment_change(self, payload: Dict):
        """센티먼트 변화 이벤트 처리"""
        symbol = payload.get('symbol')
        old_sentiment = payload.get('old_sentiment')
        new_sentiment = payload.get('new_sentiment')
        change_threshold = payload.get('change_threshold', 0.2)
        
        if not all([symbol, old_sentiment, new_sentiment]):
            return
        
        # 의미 있는 변화만 처리
        if abs(new_sentiment - old_sentiment) < change_threshold:
            return
        
        # 캐시 업데이트
        await self.cache_manager.set_sentiment_data(symbol, {
            'current_sentiment': new_sentiment,
            'previous_sentiment': old_sentiment,
            'change_time': datetime.now().isoformat()
        })
        
        # 웹소켓 브로드캐스트
        message = {
            'symbol': symbol,
            'old_sentiment': old_sentiment,
            'new_sentiment': new_sentiment,
            'change_direction': 'increase' if new_sentiment > old_sentiment else 'decrease',
            'timestamp': datetime.now().isoformat()
        }
        
        await self.websocket_manager.broadcast_to_topic('sentiment_changes', message)
        
        self.logger.info(f"Sentiment change broadcasted for {symbol}: {old_sentiment} -> {new_sentiment}")
    
    async def _handle_trending_alert(self, payload: Dict):
        """트렌딩 알림 이벤트 처리"""
        symbol = payload.get('symbol')
        trend_data = payload.get('trend_data', {})
        
        if not symbol:
            return
        
        # 웹소켓 브로드캐스트
        message = {
            'symbol': symbol,
            'trend_data': trend_data,
            'alert_type': payload.get('alert_type', 'trending'),
            'timestamp': datetime.now().isoformat()
        }
        
        await self.websocket_manager.broadcast_to_topic('trending_alerts', message)
        
        self.logger.info(f"Trending alert broadcasted for {symbol}")
    
    async def _handle_new_mention(self, payload: Dict):
        """새 언급 이벤트 처리"""
        mention = payload.get('mention')
        
        if not mention:
            return
        
        # 관심 심볼을 가진 사용자에게 알림
        symbol = mention.get('symbol')
        if symbol:
            await self._notify_watchlist_users(symbol, mention)
        
        # 최신 언급으로 캐시 업데이트
        await self._update_mention_cache(symbol, mention)
        
        self.logger.info(f"New mention processed for {symbol}")
    
    async def _handle_user_activity(self, payload: Dict):
        """사용자 활동 이벤트 처리"""
        user_id = payload.get('user_id')
        activity_type = payload.get('activity_type')
        
        if user_id and activity_type:
            # 사용자 활동 로깅
            self.logger.info(f"User {user_id} activity: {activity_type}")
    
    async def _notify_watchlist_users(self, symbol: str, mention: Dict):
        """관심종목 사용자에게 알림"""
        # 실제 구현에서는 관심종목을 가진 사용자 조회
        # 여기서는 더미 데이터 사용
        watchlist_users = ['user1', 'user2', 'user3']  # 예시 데이터
        
        message = {
            'type': 'watchlist_alert',
            'symbol': symbol,
            'mention': {
                'text': mention.get('text', '')[:100] + '...',
                'source': mention.get('source'),
                'timestamp': mention.get('timestamp')
            },
            'timestamp': datetime.now().isoformat()
        }
        
        for user_id in watchlist_users:
            if user_id in self.websocket_manager.active_connections:
                await self.websocket_manager._send_personal_message(user_id, message)
    
    async def _update_mention_cache(self, symbol: str, mention: Dict):
        """언급 캐시 업데이트"""
        cache_key = f"latest_mentions:{symbol}"
        
        # 최근 언급 목록 조회
        latest_mentions = await self.cache_manager.get(cache_key) or []
        
        # 새 언급 추가
        latest_mentions.insert(0, mention)
        
        # 최근 100개만 유지
        latest_mentions = latest_mentions[:100]
        
        await self.cache_manager.set(cache_key, latest_mentions, ttl=3600)
```

이 API 연동 및 데이터 소스 상세화 문서는 외부 API와의 안정적인 연동을 위한 구체적인 구현 방안을 제공합니다. 각 API 클라이언트, 데이터 품질 관리, 실시간 데이터 스트리밍 등을 통해 신뢰성 높은 데이터 수집 시스템을 구축할 수 있습니다.

## 4. 결론

### 4.1 API 연동 전략 요약

본 문서에서 정의한 API 연동 및 데이터 소스 통합 가이드는 InsiteChart 프로젝트가 다양한 외부 서비스와 효과적으로 통합될 수 있도록 지원합니다. 각 API의 특성을 고려한 최적화된 연동 전략을 통해 안정적이고 신뢰성 높은 데이터 수집이 가능합니다.

#### 4.1.1 주요 구성 요소

1. **표준화된 API 클라이언트 아키텍처**
   - 공통 기반 클래스(`BaseAPIClient`)를 통한 일관된 인터페이스 제공
   - 재시도 로직, 레이트 리밋, 에러 처리 등 공통 기능 구현
   - 각 API별 특수화된 클라이언트 구현

2. **데이터 품질 관리 시스템**
   - 다단계 데이터 검증 및 정제 파이프라인
   - 스팸 필터링, 중복 제거, 품질 평가 기능
   - 데이터 풍성화를 통한 부가 정보 추가

3. **실시간 데이터 스트리밍**
   - 웹소켓 기반 실시간 통신
   - 이벤트 기반 데이터 처리 아키텍처
   - 사용자별 맞춤형 데이터 전송

#### 4.1.2 기대 효과

1. **안정성 향상**
   - 다중 재시도 및 에러 복구 메커니즘
   - API 상태 모니터링을 통한 선제적 문제 감지
   - 장애 격리 및 회복 자동화

2. **성능 최적화**
   - 효율적인 캐싱 전략으로 API 호출 최소화
   - 비동기 처리를 통한 높은 처리량
   - 레이트 리밋 준수로 API 제한 회피

3. **확장성 확보**
   - 새로운 데이터 소스 쉽게 추가 가능
   - 모듈화된 아키텍처로 유지보수 용이
   - 플러그인 방식의 데이터 소스 확장

### 4.2 향후 개선 방향

#### 4.2.1 기술적 개선

1. **머신러닝 기반 데이터 품질 평가**
   - 자연어 처리를 통한 언급 품질 자동 평가
   - 패턴 인식 기반 스팸 필터링 고도화
   - 사용자 피드백을 통한 필터링 모델 개선

2. **분산 데이터 수집 아키텍처**
   - 마이크로서비스 기반 데이터 수집 서비스 분리
   - 메시지 큐를 통한 데이터 파이프라인 확장
   - 컨테이너화된 데이터 수집 워커 배포

3. **고급 캐싱 전략**
   - 예측적 캐싱을 통한 응답 시간 개선
   - 계층적 캐시 아키텍처 도입
   - 캐시 일관성 보장 메커니즘 강화

#### 4.2.2 데이터 소스 확장

1. **추가 금융 데이터 소스**
   - Alpha Vantage, IEX Cloud 등 전문 금융 API 연동
   - 뉴스 데이터 소스 연동을 통한 시장 감성 분석 확장
   - 기업 실적 발표, 경제 지표 등 정형 데이터 수집

2. **글로벌 소셜 미디어 확장**
   - 다국어 소셜 미디어 데이터 수집
   - 지역별 금융 커뮤니티 연동
   - 문화적 차이를 고려한 센티먼트 분석 모델

3. **실시간 시장 데이터**
   - 실시간 주가 데이터 스트림 연동
   - 고빈도 거래 데이터 수집 및 분석
   - 시장 마이크로스트럭처 데이터 활용

### 4.3 성공 지표

#### 4.3.1 기술적 지표

1. **데이터 수집 안정성**
   - API 연동 성공률: 99.5% 이상
   - 데이터 수집 가동률: 99.9% 이상
   - 평균 복구 시간(MTTR): 5분 이하

2. **성능 지표**
   - API 응답 시간: 평균 200ms 이하
   - 데이터 처리량: 분당 10,000건 이상
   - 캐시 적중률: 85% 이상

3. **데이터 품질**
   - 중복 데이터 비율: 5% 이하
   - 스팸 필터링 정확도: 95% 이상
   - 데이터 정확도: 99% 이상

#### 4.3.2 비즈니스 지표

1. **사용자 만족도**
   - 데이터 신선도 만족도: 90% 이상
   - 실시간 업데이트 만족도: 85% 이상
   - 시스템 안정성 만족도: 95% 이상

2. **운영 효율성**
   - 수동 개입 횟수: 월 5회 이하
   - 데이터 처리 자동화율: 95% 이상
   - 시스템 운영 비용 절감: 연간 20% 이상

### 4.4 최종 권장 사항

1. **단계적 구현**
   - 1단계: 핵심 API(Yahoo Finance, Reddit) 연동 구현
   - 2단계: 데이터 품질 관리 시스템 구축
   - 3단계: 실시간 데이터 스트리밍 구현
   - 4단계: 고급 분석 기능 및 추가 데이터 소스 연동

2. **지속적 모니터링 및 개선**
   - API 상태 및 데이터 품질 지속적 모니터링
   - 사용자 피드백을 통한 시스템 개선
   - 기술 변화에 따른 아키텍처 지속적 업데이트

3. **보안 및 규제 준수**
   - 데이터 수집 및 처리 시 개인정보보호 규정 준수
   - API 사용 약관 및 라이선스 준수
   - 데이터 보안 및 접근 제어 강화

이러한 API 연동 및 데이터 소스 통합 전략을 통해 InsiteChart는 안정적이고 확장 가능한 데이터 수집 기반을 구축하여 사용자에게 신뢰성 높은 금융 정보와 시장 인사이트를 제공할 수 있을 것입니다.