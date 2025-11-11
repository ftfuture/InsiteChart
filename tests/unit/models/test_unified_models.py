"""
통합 데이터 모델 단위 테스트

이 모듈은 UnifiedStockData와 관련 모델의 개별 기능을 독립적으로 테스트합니다.
"""

import pytest
from datetime import datetime, timedelta, timezone
from backend.models.unified_models import (
    UnifiedStockData,
    SearchQuery,
    SearchResult,
    StockType,
    SentimentSource,
    InvestmentStyle,
    SentimentResult,
    StockMention,
    User,
    WatchlistItem
)


class TestUnifiedStockData:
    """UnifiedStockData 모델 단위 테스트 클래스"""
    
    def test_unified_stock_data_creation(self):
        """UnifiedStockData 생성 테스트"""
        # 최소 필드만으로 생성
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ"
        )
        
        assert stock_data.symbol == "AAPL"
        assert stock_data.company_name == "Apple Inc."
        assert stock_data.stock_type == StockType.EQUITY
        assert stock_data.exchange == "NASDAQ"
        
        # 기본값 확인
        assert stock_data.current_price is None
        assert stock_data.previous_close is None
        assert stock_data.day_change is None
        assert stock_data.day_change_pct is None
        assert stock_data.volume is None
        assert stock_data.overall_sentiment is None
        assert stock_data.sentiment_sources == {}
        assert stock_data.mention_count_24h is None
        assert stock_data.trending_status is False
        assert stock_data.data_quality_score == 1.0
        assert stock_data.data_sources == ["yahoo_finance"]
    
    def test_unified_stock_data_with_all_fields(self):
        """모든 필드를 포함한 UnifiedStockData 생성 테스트"""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000000000.0,
            current_price=150.0,
            previous_close=148.0,
            volume=50000000,
            avg_volume=45000000,
            day_high=151.0,
            day_low=149.0,
            pe_ratio=25.5,
            dividend_yield=0.5,
            beta=1.2,
            eps=5.88,
            fifty_two_week_high=180.0,
            fifty_two_week_low=120.0,
            overall_sentiment=0.2,
            sentiment_sources={
                SentimentSource.REDDIT: 0.1,
                SentimentSource.TWITTER: 0.3
            },
            mention_count_24h=100,
            mention_count_1h=10,
            positive_mentions=60,
            negative_mentions=20,
            neutral_mentions=20,
            trending_status=True,
            trend_score=2.5,
            trend_duration_hours=12,
            relevance_score=0.8,
            search_count=100,
            view_count=500,
            last_viewed=yesterday,
            data_quality_score=0.9,
            data_sources=["yahoo_finance", "reddit", "twitter"]
        )
        
        # 모든 필드 값 확인
        assert stock_data.symbol == "AAPL"
        assert stock_data.current_price == 150.0
        assert stock_data.previous_close == 148.0
        assert stock_data.day_change == 2.0
        assert stock_data.day_change_pct == pytest.approx(1.35, rel=1e-2)
        assert stock_data.volume == 50000000
        assert stock_data.overall_sentiment == 0.2
        assert len(stock_data.sentiment_sources) == 2
        assert stock_data.mention_count_24h == 100
        assert stock_data.trending_status is True
        assert stock_data.data_quality_score == 0.9
        assert len(stock_data.data_sources) == 3
    
    def test_unified_stock_data_derived_fields(self):
        """UnifiedStockData 파생 필드 계산 테스트"""
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ",
            current_price=150.0,
            previous_close=148.0
        )
        
        # 파생 필드 자동 계산 확인
        assert stock_data.day_change == 2.0
        assert stock_data.day_change_pct == pytest.approx(1.35, rel=1e-2)
    
    def test_unified_stock_data_to_dict(self):
        """UnifiedStockData to_dict 메서드 테스트"""
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ",
            current_price=150.0,
            previous_close=148.0,
            overall_sentiment=0.2,
            sentiment_sources={
                SentimentSource.REDDIT: 0.1,
                SentimentSource.TWITTER: 0.3
            }
        )
        
        result_dict = stock_data.to_dict()
        
        # 필드 변환 확인
        assert result_dict["symbol"] == "AAPL"
        assert result_dict["company_name"] == "Apple Inc."
        assert result_dict["stock_type"] == "EQUITY"
        assert result_dict["current_price"] == 150.0
        assert result_dict["day_change"] == 2.0
        assert result_dict["overall_sentiment"] == 0.2
        assert result_dict["sentiment_sources"] == {"REDDIT": 0.1, "TWITTER": 0.3}
        assert "last_updated" in result_dict
        assert "data_sources" in result_dict
    
    def test_unified_stock_data_from_dict(self):
        """UnifiedStockData from_dict 클래스 메서드 테스트"""
        data_dict = {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "stock_type": "EQUITY",
            "exchange": "NASDAQ",
            "current_price": 150.0,
            "previous_close": 148.0,
            "overall_sentiment": 0.2,
            "sentiment_sources": {"REDDIT": 0.1, "TWITTER": 0.3},
            "last_viewed": "2023-01-01T00:00:00",
            "data_sources": ["yahoo_finance", "reddit"]
        }
        
        stock_data = UnifiedStockData.from_dict(data_dict)
        
        # 필드 변환 확인
        assert stock_data.symbol == "AAPL"
        assert stock_data.company_name == "Apple Inc."
        assert stock_data.stock_type == StockType.EQUITY
        assert stock_data.current_price == 150.0
        assert stock_data.overall_sentiment == 0.2
        assert len(stock_data.sentiment_sources) == 2
        assert stock_data.sentiment_sources[SentimentSource.REDDIT] == 0.1
        assert stock_data.last_viewed.year == 2023
        assert len(stock_data.data_sources) == 2


class TestSearchQuery:
    """SearchQuery 모델 단위 테스트 클래스"""
    
    def test_search_query_creation(self):
        """SearchQuery 생성 테스트"""
        query = SearchQuery(
            query="Apple",
            user_id="test_user",
            limit=10,
            sort_by="relevance",
            sort_order="desc"
        )
        
        assert query.query == "Apple"
        assert query.user_id == "test_user"
        assert query.limit == 10
        assert query.sort_by == "relevance"
        assert query.sort_order == "desc"
        
        # 기본값 확인
        assert query.filters == {}
        assert query.offset == 0
    
    def test_search_query_with_filters(self):
        """필터를 포함한 SearchQuery 생성 테스트"""
        filters = {
            "sector": "Technology",
            "market_cap_min": 1000000000,
            "price_max": 200.0
        }
        
        query = SearchQuery(
            query="Apple",
            filters=filters,
            limit=20,
            offset=5,
            sort_by="market_cap",
            sort_order="asc"
        )
        
        assert query.query == "Apple"
        assert query.filters == filters
        assert query.limit == 20
        assert query.offset == 5
        assert query.sort_by == "market_cap"
        assert query.sort_order == "asc"
    
    def test_search_query_to_hash(self):
        """SearchQuery to_hash 메서드 테스트"""
        query = SearchQuery(
            query="Apple",
            filters={"sector": "Technology"},
            limit=10,
            offset=0,
            sort_by="relevance",
            sort_order="desc"
        )
        
        hash_value = query.to_hash()
        
        # 해시 값은 일관성이 있어야 함
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 해시 길이
        
        # 동일한 쿼리는 동일한 해시를 반환해야 함
        query2 = SearchQuery(
            query="Apple",
            filters={"sector": "Technology"},
            limit=10,
            offset=0,
            sort_by="relevance",
            sort_order="desc"
        )
        
        assert query.to_hash() == query2.to_hash()
    
    def test_search_query_to_dict(self):
        """SearchQuery to_dict 메서드 테스트"""
        query = SearchQuery(
            query="Apple",
            user_id="test_user",
            filters={"sector": "Technology"},
            limit=10,
            offset=5,
            sort_by="relevance",
            sort_order="desc"
        )
        
        result_dict = query.to_dict()
        
        assert result_dict["query"] == "Apple"
        assert result_dict["user_id"] == "test_user"
        assert result_dict["filters"] == {"sector": "Technology"}
        assert result_dict["limit"] == 10
        assert result_dict["offset"] == 5
        assert result_dict["sort_by"] == "relevance"
        assert result_dict["sort_order"] == "desc"
        assert "timestamp" in result_dict


class TestSearchResult:
    """SearchResult 모델 단위 테스트 클래스"""
    
    def test_search_result_creation(self):
        """SearchResult 생성 테스트"""
        query = SearchQuery(query="Apple", limit=10)
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ"
        )
        
        result = SearchResult(
            query=query,
            results=[stock_data],
            total_count=1,
            search_time_ms=150.0,
            cache_hit=False
        )
        
        assert result.query == query
        assert len(result.results) == 1
        assert result.results[0].symbol == "AAPL"
        assert result.total_count == 1
        assert result.search_time_ms == 150.0
        assert result.cache_hit is False
        assert result.suggestions is None
        assert result.facets is None
    
    def test_search_result_with_suggestions(self):
        """제안을 포함한 SearchResult 생성 테스트"""
        query = SearchQuery(query="Apple", limit=10)
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ"
        )
        
        result = SearchResult(
            query=query,
            results=[stock_data],
            total_count=1,
            search_time_ms=150.0,
            cache_hit=False,
            suggestions=["AAPL", "MSFT"],
            facets={"sectors": ["Technology", "Finance"]}
        )
        
        assert result.suggestions == ["AAPL", "MSFT"]
        assert result.facets == {"sectors": ["Technology", "Finance"]}
    
    def test_search_result_to_dict(self):
        """SearchResult to_dict 메서드 테스트"""
        query = SearchQuery(query="Apple", limit=10)
        stock_data = UnifiedStockData(
            symbol="AAPL",
            company_name="Apple Inc.",
            stock_type=StockType.EQUITY,
            exchange="NASDAQ"
        )
        
        result = SearchResult(
            query=query,
            results=[stock_data],
            total_count=1,
            search_time_ms=150.0,
            cache_hit=False,
            suggestions=["AAPL", "MSFT"]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["query"]["query"] == "Apple"
        assert len(result_dict["results"]) == 1
        assert result_dict["results"][0]["symbol"] == "AAPL"
        assert result_dict["total_count"] == 1
        assert result_dict["search_time_ms"] == 150.0
        assert result_dict["cache_hit"] is False
        assert result_dict["suggestions"] == ["AAPL", "MSFT"]
        assert result_dict["facets"] == {"sectors": ["Technology", "Finance"]}


class TestStockMention:
    """StockMention 모델 단위 테스트 클래스"""
    
    def test_stock_mention_creation(self):
        """StockMention 생성 테스트"""
        now = datetime.now(timezone.utc)
        
        mention = StockMention(
            symbol="AAPL",
            text="AAPL is going to the moon! 🚀",
            source=SentimentSource.REDDIT,
            community="wallstreetbets",
            author="investor123",
            timestamp=now,
            upvotes=150,
            sentiment_score=0.8,
            investment_style=InvestmentStyle.DAY_TRADING,
            url="https://reddit.com/r/wallstreetbets/comments/abc123"
        )
        
        assert mention.symbol == "AAPL"
        assert "going to the moon" in mention.text
        assert mention.source == SentimentSource.REDDIT
        assert mention.community == "wallstreetbets"
        assert mention.author == "investor123"
        assert mention.upvotes == 150
        assert mention.sentiment_score == 0.8
        assert mention.investment_style == InvestmentStyle.DAY_TRADING
        assert mention.url == "https://reddit.com/r/wallstreetbets/comments/abc123"
    
    def test_stock_mention_optional_fields(self):
        """선택적 필드를 포함한 StockMention 생성 테스트"""
        mention = StockMention(
            symbol="AAPL",
            text="Just talking about AAPL",
            source=SentimentSource.TWITTER,
            community="twitter",
            author="trader456",
            timestamp=datetime.now(timezone.utc)
        )
        
        # 선택적 필드 기본값 확인
        assert mention.upvotes == 0
        assert mention.sentiment_score is None
        assert mention.investment_style is None
        assert mention.url is None


class TestSentimentResult:
    """SentimentResult 모델 단위 테스트 클래스"""
    
    def test_sentiment_result_creation(self):
        """SentimentResult 생성 테스트"""
        now = datetime.now(timezone.utc)
        
        result = SentimentResult(
            compound_score=0.5,
            positive_score=0.7,
            negative_score=0.2,
            neutral_score=0.1,
            confidence=0.8,
            source=SentimentSource.REDDIT,
            timestamp=now
        )
        
        assert result.compound_score == 0.5
        assert result.positive_score == 0.7
        assert result.negative_score == 0.2
        assert result.neutral_score == 0.1
        assert result.confidence == 0.8
        assert result.source == SentimentSource.REDDIT
        assert result.timestamp == now
    
    def test_sentiment_result_timestamp_default(self):
        """SentimentResult 타임스탬프 기본값 테스트"""
        result = SentimentResult(
            compound_score=0.5,
            positive_score=0.7,
            negative_score=0.2,
            neutral_score=0.1,
            confidence=0.8,
            source=SentimentSource.TWITTER
        )
        
        # 타임스탬프 기본값 확인
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)


class TestUser:
    """User 모델 단위 테스트 클래스"""
    
    def test_user_creation(self):
        """User 생성 테스트"""
        now = datetime.now(timezone.utc)
        
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role="basic",
            is_active=True,
            created_at=now,
            permissions=["stock:read", "sentiment:read"],
            preferences={"theme": "dark", "notifications": True}
        )
        
        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.role == "basic"
        assert user.is_active is True
        assert user.created_at == now
        assert user.permissions == ["stock:read", "sentiment:read"]
        assert user.preferences["theme"] == "dark"
        assert user.preferences["notifications"] is True
    
    def test_user_optional_fields(self):
        """선택적 필드를 포함한 User 생성 테스트"""
        user = User(
            id=2,
            username="user2",
            email="user2@example.com",
            password_hash="hashed_password2"
        )
        
        # 선택적 필드 기본값 확인
        assert user.role == "basic"
        assert user.is_active is True
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
        assert user.permissions == []
        assert user.preferences == {}


class TestWatchlistItem:
    """WatchlistItem 모델 단위 테스트 클래스"""
    
    def test_watchlist_item_creation(self):
        """WatchlistItem 생성 테스트"""
        now = datetime.now(timezone.utc)
        
        item = WatchlistItem(
            id=1,
            user_id=123,
            symbol="AAPL",
            category="Technology",
            note="Long term hold",
            added_date=now,
            order_index=0,
            alert_threshold=5.0,
            sentiment_alert=True
        )
        
        assert item.id == 1
        assert item.user_id == 123
        assert item.symbol == "AAPL"
        assert item.category == "Technology"
        assert item.note == "Long term hold"
        assert item.order_index == 0
        assert item.alert_threshold == 5.0
        assert item.sentiment_alert is True
    
    def test_watchlist_item_optional_fields(self):
        """선택적 필드를 포함한 WatchlistItem 생성 테스트"""
        item = WatchlistItem(
            id=2,
            user_id=456,
            symbol="MSFT"
        )
        
        # 선택적 필드 기본값 확인
        assert item.category is None
        assert item.note is None
        assert item.order_index == 0
        assert item.alert_threshold is None
        assert item.sentiment_alert is False
        assert item.added_date is not None
        assert isinstance(item.added_date, datetime)


class TestEnums:
    """열거형 모델 단위 테스트 클래스"""
    
    def test_stock_type_enum(self):
        """StockType 열거형 테스트"""
        assert StockType.EQUITY.value == "EQUITY"
        assert StockType.ETF.value == "ETF"
        assert StockType.MUTUAL_FUND.value == "MUTUAL_FUND"
        assert StockType.CRYPTO.value == "CRYPTO"
        assert StockType.INDEX.value == "INDEX"
    
    def test_sentiment_source_enum(self):
        """SentimentSource 열거형 테스트"""
        assert SentimentSource.REDDIT.value == "REDDIT"
        assert SentimentSource.TWITTER.value == "TWITTER"
        assert SentimentSource.DISCORD.value == "DISCORD"
        assert SentimentSource.NEWS.value == "NEWS"
    
    def test_investment_style_enum(self):
        """InvestmentStyle 열거형 테스트"""
        assert InvestmentStyle.DAY_TRADING.value == "DAY_TRADING"
        assert InvestmentStyle.SWING_TRADING.value == "SWING_TRADING"
        assert InvestmentStyle.VALUE_INVESTING.value == "VALUE_INVESTING"
        assert InvestmentStyle.GROWTH_INVESTING.value == "GROWTH_INVESTING"
        assert InvestmentStyle.LONG_TERM.value == "LONG_TERM"
    
    def test_enum_comparison(self):
        """열거형 비교 테스트"""
        assert StockType.EQUITY != StockType.ETF
        assert SentimentSource.REDDIT == SentimentSource.REDDIT
        assert InvestmentStyle.DAY_TRADING != InvestmentStyle.SWING_TRADING
        
        # 열거형 멤버십 확인
        stock_types = list(StockType)
        assert StockType.EQUITY in stock_types
        assert StockType.ETF in stock_types
        assert len(stock_types) == 5
        
        sentiment_sources = list(SentimentSource)
        assert SentimentSource.REDDIT in sentiment_sources
        assert len(sentiment_sources) == 5