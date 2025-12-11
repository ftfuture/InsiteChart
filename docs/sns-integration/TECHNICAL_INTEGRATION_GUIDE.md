# SNS 플랫폼 기술적 통합 가이드

**작성일**: 2025년 12월 11일
**목적**: InsiteChart에 SNS 플랫폼 통합을 위한 기술 문서
**대상**: 개발자, 아키텍트

---

## 목차

1. [API 접근성 맵](#api-접근성-맵)
2. [데이터 수집 아키텍처](#데이터-수집-아키텍처)
3. [플랫폼별 구현 가이드](#플랫폼별-구현-가이드)
4. [데이터 전처리 파이프라인](#데이터-전처리-파이프라인)
5. [성능 최적화](#성능-최적화)
6. [에러 처리 및 폴백](#에러-처리-및-폴백)

---

## API 접근성 맵

### 플랫폼별 접근 방식

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1: REST API (직접 접근) - 구현 쉬움               │
├─────────────────────────────────────────────────────────┤
│ ✅ StockTwits    | GET /api/2/streams/symbol/{ticker}   │
│ ✅ Reddit (PRAW) | pip install praw                      │
│ ✅ Twitter V2    | bearToken 기반 (유료)                │
│ ✅ Koyfin        | REST API (유료)                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Tier 2: 웹 스크래핑 - 구현 중간 난이도                 │
├─────────────────────────────────────────────────────────┤
│ ⚠️ Seeking Alpha | Selenium + Beautiful Soup             │
│ ⚠️ TradingView   | Selenium + 로그인 관리                │
│ ⚠️ Yahoo Finance | requests + parsing                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Tier 3: 어려운 접근 - 구현 어려움                       │
├─────────────────────────────────────────────────────────┤
│ ❌ Public.com    | JavaScript 렌더링 필수                │
│ ❌ eToro         | 로그인 필수 + 안티봇 대책             │
│ ❌ 국내 플랫폼   | 로그인 + CAPTCHA 우회                 │
└─────────────────────────────────────────────────────────┘
```

---

## 데이터 수집 아키텍처

### 전체 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                         SNS 플랫폼들                          │
│  StockTwits │ Twitter │ Reddit │ Seeking Alpha │ TradingView │
└──────────────┬────────┬────────┬──────────────┬──────────────┘
               │        │        │              │
               ▼        ▼        ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│         Collector Services (각 플랫폼별 마이크로서비스)        │
│                                                              │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │StockTwits    │  │Twitter       │  │Reddit        │       │
│ │Collector     │  │Collector     │  │Collector     │       │
│ └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│ (8001:stocktwits)  (8001:twitter)   (8001:reddit)           │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Data Collector Service (통합 수집)                  │    │
│ │ Port: 8001                                          │    │
│ │ - Batch job 관리                                    │    │
│ │ - Rate limiting 관리                                │    │
│ │ - 에러 재시도                                       │    │
│ └──────┬───────────────────────────────────────────────┘    │
└────────┼────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│              Cache Layer (Redis)                             │
│                                                              │
│ sentiment:{source}:{symbol}  → 감정 점수                    │
│ message:{id}:{symbol}        → 원본 메시지                   │
│ job:{job_id}                 → 수집 작업 상태               │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│         Analytics Service (데이터 처리)                       │
│         Port: 8002                                           │
│                                                              │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐         │
│ │Sentiment    │  │Correlation   │  │Aggregation   │         │
│ │Analyzer     │  │Analyzer      │  │Engine        │         │
│ │(VADER+BERT) │  │(Pearson)     │  │(Multi-source)│         │
│ └─────────────┘  └──────────────┘  └──────────────┘         │
└──────────────┬────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│        API Gateway & Storage                                 │
│        Port: 8080                                            │
│                                                              │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│ │PostgreSQL    │  │Redis Cache   │  │Time-series   │         │
│ │(persistent)  │  │(hot data)    │  │DB            │         │
│ └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────┬────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│              Frontend                                         │
│              Port: 8501                                      │
│                                                              │
│ - 실시간 감정 대시보드                                        │
│ - 추세 분석 차트                                              │
│ - 알림 설정                                                  │
└──────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
1. 데이터 수집 (Collection)
   ├─ 각 Collector가 독립적으로 데이터 수집
   ├─ Rate limiting 준수 (platform별)
   └─ 원본 데이터 저장

2. 캐싱 (Caching)
   ├─ Redis에 최신 데이터 캐시
   ├─ TTL: 5분 (설정 가능)
   └─ 반복 요청 시 캐시에서 응답

3. 처리 (Processing)
   ├─ 텍스트 정규화
   ├─ 감정 분석 (VADER + BERT)
   ├─ 신호 추출
   └─ 스코어 계산

4. 집계 (Aggregation)
   ├─ 멀티소스 가중치 적용
   ├─ 신뢰도 점수 계산
   └─ 최종 신호 결정

5. 저장 (Storage)
   ├─ PostgreSQL (영구 저장)
   ├─ Time-series DB (시계열 분석)
   └─ 히스토리 보존 (백테스팅용)

6. 노출 (Exposure)
   ├─ REST API 제공
   ├─ WebSocket (실시간)
   └─ 대시보드 시각화
```

---

## 플랫폼별 구현 가이드

### 1️⃣ StockTwits 수집 구현

**설치**:
```bash
pip install httpx  # 이미 설치됨
```

**기본 수집 코드**:
```python
import httpx
from datetime import datetime

class StockTwitsAPI:
    BASE_URL = "https://api.stocktwits.com/api/2"

    async def get_symbol_data(self, symbol: str, limit: 30):
        """
        종목 데이터 수집

        엔드포인트: GET /streams/symbol/{symbol}.json
        응답: 메시지 배열 (최대 30개)
        """
        url = f"{self.BASE_URL}/streams/symbol/{symbol}.json"

        params = {
            "limit": limit,
            "max": None  # 페이징을 위한 최대 ID
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

            return {
                "symbol": symbol,
                "messages": data.get("messages", []),
                "sentiment": data.get("sentiment", {}),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_s_score(self, symbol: str):
        """
        S-Score 조회

        엔드포인트: GET /instruments/{symbol}.json
        응답: 종목 정보 (s_score 포함)
        """
        url = f"{self.BASE_URL}/instruments/{symbol}.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            return {
                "symbol": symbol,
                "s_score": data.get("watchlist", {}).get("s_score", 50)
            }

# 사용 예
async def collect_stocktwits_data(symbols: List[str]):
    api = StockTwitsAPI()

    results = {}
    for symbol in symbols:
        try:
            messages = await api.get_symbol_data(symbol)
            s_score = await api.get_s_score(symbol)

            results[symbol] = {
                **messages,
                "s_score": s_score["s_score"]
            }

            await asyncio.sleep(2)  # Rate limiting

        except Exception as e:
            logger.error(f"StockTwits 수집 실패 {symbol}: {e}")
            results[symbol] = None

    return results
```

**Rate Limiting**:
```
- 공개 API: 200 요청/시간 (10.8req/분)
- API 키 사용: 1000 요청/시간 (16.7req/분)

권장 설정:
- 배치 크기: 50 종목
- 배치당 지연: 2초
- 예상 시간: 50종목 × 2초 = 100초 (2req/분)
```

---

### 2️⃣ Reddit 수집 구현

**설치**:
```bash
pip install praw  # 이미 설치됨
```

**설정**:
```python
import praw

# Reddit 인증 정보 필요
# /etc/insitechart/.env 파일에 추가:
# REDDIT_CLIENT_ID=xxxxx
# REDDIT_CLIENT_SECRET=xxxxx

class RedditAPI:
    def __init__(self, client_id, client_secret):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="InsiteChart/1.0"
        )

    def search_subreddit(self, subreddit: str, symbol: str, limit: int = 30):
        """
        서브레딧에서 종목 검색

        예: subreddit="stocks", symbol="AAPL"
        응답: 포스트 배열
        """
        sub = self.reddit.subreddit(subreddit)

        posts = []
        for post in sub.search(f"${symbol}", time_filter="week", limit=limit):
            posts.append({
                "id": post.id,
                "title": post.title,
                "text": post.selftext,
                "score": post.score,
                "comments": post.num_comments,
                "url": post.url,
                "timestamp": post.created_utc
            })

        return posts

# 멀티 서브레딧 수집
async def collect_reddit_data(symbol: str, api: RedditAPI):
    subreddits = ["stocks", "investing", "wallstreetbets", "options"]

    all_posts = []
    for subreddit in subreddits:
        posts = api.search_subreddit(subreddit, symbol, limit=10)
        all_posts.extend(posts)

        await asyncio.sleep(1)  # Rate limiting

    return {
        "symbol": symbol,
        "posts": all_posts,
        "count": len(all_posts)
    }
```

**Rate Limiting**:
```
- PRAW: 60 요청/분 (자동 관리)
- 권장: 배치당 3-5초 지연

실제 측정:
- 10개 종목 × 4개 서브레딧 = 40 요청
- 예상 시간: ~2분 (rate limit 포함)
```

---

### 3️⃣ Seeking Alpha 스크래핑

**설치**:
```bash
pip install selenium beautifulsoup4
```

**기본 구현**:
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

class SeekingAlphaScraper:
    def __init__(self):
        # Headless 모드로 브라우저 시작
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = webdriver.Chrome(options=options)

    def get_analyst_rating(self, symbol: str):
        """
        분석가 평가 수집

        URL: https://seekingalpha.com/symbol/{symbol}/ratings
        """
        url = f"https://seekingalpha.com/symbol/{symbol}/ratings"

        try:
            self.driver.get(url)
            time.sleep(3)  # JavaScript 로딩 대기

            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # CSS 셀렉터 사용 (실제 HTML 구조 확인 필요)
            rating = soup.find('div', {'class': 'rating'})
            target_price = soup.find('div', {'class': 'target-price'})

            return {
                "symbol": symbol,
                "rating": rating.text if rating else "N/A",
                "target_price": target_price.text if target_price else "N/A"
            }

        except Exception as e:
            logger.error(f"Seeking Alpha 스크래핑 실패: {e}")
            return None

        finally:
            pass

    def close(self):
        self.driver.quit()

# 사용
async def collect_seeking_alpha(symbols: List[str]):
    scraper = SeekingAlphaScraper()
    results = {}

    for symbol in symbols:
        rating = scraper.get_analyst_rating(symbol)
        results[symbol] = rating
        await asyncio.sleep(5)  # Anti-bot 대책

    scraper.close()
    return results
```

**주의사항**:
```
❌ 웹 스크래핑 법적 위험
   - Seeking Alpha 이용약관 확인 필수
   - robots.txt 준수

⚠️ 탐지 회피
   - User-Agent 변경
   - 지연 추가 (5초 이상)
   - Proxy 사용 고려
   - 헤더 위조 (Referer 등)
```

---

## 데이터 전처리 파이프라인

### 텍스트 정규화

```python
import re
from typing import Dict

class TextPreprocessor:
    """텍스트 데이터 정규화"""

    @staticmethod
    def normalize(text: str) -> str:
        """
        1. URL 제거
        2. HTML 태그 제거
        3. 이모지 제거
        4. 반복 문자 축약 (여러 느낌표 → 하나)
        5. 공백 정규화
        """

        # URL 제거
        text = re.sub(r'http\S+', '', text)

        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)

        # 이모지 제거
        text = re.sub(r'[^\x00-\x7F]+', '', text)

        # 반복 문자 축약
        text = re.sub(r'([!?])\1{2,}', r'\1', text)

        # 공백 정규화
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def extract_ticker(text: str) -> List[str]:
        """텍스트에서 티커 추출 ($AAPL 형식)"""
        return re.findall(r'\$[A-Z]{1,5}', text)

    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """투자 관련 키워드 추출"""
        keywords = {
            'bullish': ['buy', 'long', 'bullish', 'moon', 'rocket', 'hodl'],
            'bearish': ['sell', 'short', 'bearish', 'dump', 'crash', 'dive'],
            'earnings': ['earnings', 'eps', 'revenue', 'profit', 'guidance'],
            'analyst': ['upgr', 'downgrad', 'analyst', 'target price']
        }

        text_lower = text.lower()
        found_keywords = {}

        for category, words in keywords.items():
            found_keywords[category] = [w for w in words if w in text_lower]

        return found_keywords
```

### 감정 점수 정규화

```python
def normalize_sentiment_score(score: float, platform: str) -> float:
    """
    플랫폼별 감정 점수를 -1 ~ +1 범위로 정규화

    StockTwits S-Score: 0-100 → -1 ~ +1
    Twitter polarity: -1 ~ +1 → -1 ~ +1
    Reddit upvote ratio: 0-1 → -1 ~ +1
    """

    if platform == "stocktwits":
        # 0-100 → -1 ~ +1
        return (score - 50) / 50

    elif platform == "twitter":
        # -1 ~ +1 (그대로)
        return max(-1, min(1, score))

    elif platform == "reddit":
        # 0-1 → -1 ~ +1
        return (score * 2) - 1

    else:
        return score

# 테스트
assert normalize_sentiment_score(75, "stocktwits") == 0.5   # 강세
assert normalize_sentiment_score(25, "stocktwits") == -0.5  # 약세
assert normalize_sentiment_score(0.7, "twitter") == 0.7     # 긍정
```

---

## 성능 최적화

### 병렬 수집

```python
import asyncio
from typing import List, Dict

async def parallel_collection(symbols: List[str]) -> Dict:
    """
    여러 플랫폼에서 병렬로 데이터 수집
    """

    tasks = []

    # 각 종목별 병렬 수집
    for symbol in symbols:
        task = asyncio.create_task(collect_all_platforms(symbol))
        tasks.append(task)

    # 모든 작업 완료 대기
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {symbol: result for symbol, result in zip(symbols, results)}

async def collect_all_platforms(symbol: str) -> Dict:
    """한 종목에 대해 모든 플랫폼에서 수집"""

    tasks = [
        stocktwits_api.get_symbol_data(symbol),
        reddit_api.search_subreddit("stocks", symbol),
        twitter_api.search_tweets(symbol),
        seeking_alpha_scraper.get_analyst_rating(symbol)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "stocktwits": results[0],
        "reddit": results[1],
        "twitter": results[2],
        "seeking_alpha": results[3]
    }

# 성능 예상
"""
순차 수집: 50 종목 × 4 플랫폼 × 2초/요청 = 400초
병렬 수집 (4개 동시): 50 종목 × 2초 (병렬) = 100초 (4배 향상)
"""
```

### 캐싱 전략

```python
import redis
import json
from datetime import timedelta

class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client

        # 플랫폼별 TTL
        self.ttl = {
            "stocktwits": 300,      # 5분 (실시간)
            "twitter": 600,         # 10분 (높은 변동)
            "reddit": 900,          # 15분
            "seeking_alpha": 1800,  # 30분 (변하지 않음)
        }

    async def get_cached(self, key: str):
        """캐시에서 데이터 가져오기"""
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set_cache(self, key: str, data: Dict, platform: str):
        """데이터 캐시 저장"""
        ttl = self.ttl.get(platform, 600)
        await self.redis.setex(
            key,
            timedelta(seconds=ttl),
            json.dumps(data)
        )

    def get_cache_key(self, platform: str, symbol: str, type: str):
        """캐시 키 생성"""
        return f"sentiment:{platform}:{symbol}:{type}"

# 사용
async def get_sentiment_data(symbol: str, platform: str):
    cache_mgr = CacheManager(redis_client)

    # 캐시 확인
    cache_key = cache_mgr.get_cache_key(platform, symbol, "main")
    cached = await cache_mgr.get_cached(cache_key)

    if cached:
        return cached  # 캐시에서 즉시 반환

    # 캐시 미스 → 데이터 수집
    data = await collect_data(symbol, platform)

    # 캐시 저장
    await cache_mgr.set_cache(cache_key, data, platform)

    return data
```

---

## 에러 처리 및 폴백

### 재시도 로직

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def collect_with_retry(symbol: str, platform: str):
    """
    최대 3회 재시도 (2, 4, 8초 대기)
    """
    return await collect_data(symbol, platform)

# 수동 재시도
async def collect_with_manual_retry(symbol: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await collect_data(symbol)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"최대 재시도 횟수 초과: {symbol}")
                raise

            wait_time = 2 ** attempt  # 2, 4, 8 초
            logger.warning(f"재시도 {attempt + 1}/{max_retries} ({wait_time}초 대기)")
            await asyncio.sleep(wait_time)
```

### 폴백 메커니즘

```python
class CollectionFallback:
    """데이터 수집 실패 시 폴백"""

    async def get_sentiment(self, symbol: str) -> Dict:
        """
        우선순위별 데이터 소스 시도
        """

        # 1차: 캐시 확인
        cached = await self.get_from_cache(symbol)
        if cached and not self.is_stale(cached):
            return cached

        # 2차: API 수집 시도
        try:
            data = await self.collect_from_api(symbol)
            await self.save_to_cache(data)
            return data
        except Exception as e:
            logger.error(f"API 수집 실패: {e}")

        # 3차: 부실 캐시 사용
        if cached:
            logger.warning(f"부실 캐시 사용: {symbol}")
            return cached

        # 4차: 기본값 반환
        logger.error(f"모든 소스 실패, 기본값 반환: {symbol}")
        return self.get_default_sentiment()

    def get_default_sentiment(self) -> Dict:
        """기본 감정 점수 (중립)"""
        return {
            "symbol": None,
            "sentiment": 0.0,  # 중립
            "confidence": 0.1,
            "source": "default"
        }
```

---

## 배포 체크리스트

### 프리 배포 검증

```
Data Collection:
☐ 모든 API 엔드포인트 접근 테스트
☐ Rate limiting 준수 확인
☐ 에러 처리 테스트
☐ 타임아웃 설정 확인

Performance:
☐ 배치 처리 성능 측정
☐ 병렬 수집 동작 확인
☐ 캐시 히트율 검증
☐ 메모리 사용량 모니터링

Security:
☐ API 키 보안 확인
☐ HTTPS 연결 확인
☐ 로그에 민감 정보 제거
☐ Rate limit 우회 시도 탐지

Monitoring:
☐ 에러 로깅 설정
☐ 메트릭 수집 확인
☐ 알람 규칙 설정
☐ 헬스 체크 엔드포인트
```

---

**문서 버전**: 1.0
**최종 업데이트**: 2025년 12월 11일
**다음 검토**: Phase 2 구현 시
