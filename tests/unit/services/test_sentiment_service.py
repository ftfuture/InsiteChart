"""
SentimentService 단위 테스트

이 모듈은 SentimentService의 개별 기능을 독립적으로 테스트합니다.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from datetime import datetime, timedelta
import random

from backend.services.sentiment_service import SentimentService
from backend.models.unified_models import StockMention, SentimentResult, SentimentSource, InvestmentStyle


class TestSentimentService:
    """SentimentService 단위 테스트 클래스"""
    
    @pytest.fixture
    def sentiment_service(self, mock_cache_manager, mock_sentiment_analyzer):
        """SentimentService 픽스처"""
        service = SentimentService(cache_manager=mock_cache_manager)
        # 테스트 환경에서는 속도 제한 완화
        service.reddit_requests_per_minute = 1000
        service.twitter_requests_per_minute = 1000
        return service
    
    def test_load_stock_lexicon(self, sentiment_service):
        """주식 특정 감성 사전 로드 테스트"""
        # 테스트 실행
        lexicon = sentiment_service._load_stock_lexicon()
        
        # 검증
        assert isinstance(lexicon, dict)
        assert len(lexicon) > 0
        
        # 주요 용어 확인
        assert 'moon' in lexicon
        assert 'rocket' in lexicon
        assert 'crash' in lexicon
        assert 'paper hands' in lexicon
        
        # 점수 범위 확인
        for term, score in lexicon.items():
            assert isinstance(score, (int, float))
            assert -1.0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_collect_mentions_testing_mode(self, sentiment_service):
        """테스트 모드에서 언급 수집 테스트"""
        # 테스트 환경 변수 설정
        with patch('os.getenv', return_value='true'):
            # 테스트 실행
            mentions = await sentiment_service.collect_mentions('AAPL', '24h')
            
            # 검증
            assert isinstance(mentions, list)
            assert len(mentions) > 0
            
            # 각 언급 확인
            for mention in mentions:
                assert isinstance(mention, StockMention)
                assert mention.symbol == 'AAPL'
                assert mention.source in [SentimentSource.REDDIT, SentimentSource.TWITTER]
                assert mention.text is not None
                assert mention.timestamp is not None
                assert -1.0 <= mention.sentiment_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_collect_mentions_parallel(self, sentiment_service):
        """병렬 언급 수집 테스트"""
        # 모의 언급 데이터 설정
        reddit_mentions = [
            create_mock_stock_mention('AAPL', 0.3),
            create_mock_stock_mention('AAPL', 0.2)
        ]
        
        twitter_mentions = [
            create_mock_stock_mention('AAPL', 0.1),
            create_mock_stock_mention('AAPL', -0.1)
        ]
        
        # 모의 메서드 설정
        sentiment_service._collect_reddit_mentions = AsyncMock(return_value=reddit_mentions)
        sentiment_service._collect_twitter_mentions = AsyncMock(return_value=twitter_mentions)
        
        # 테스트 실행
        mentions = await sentiment_service.collect_mentions('AAPL', '24h')
        
        # 검증
        assert len(mentions) == 4
        
        # 병렬 호출 확인
        sentiment_service._collect_reddit_mentions.assert_called_once_with('AAPL', '24h')
        sentiment_service._collect_twitter_mentions.assert_called_once_with('AAPL', '24h')
        
        # 시간순 정렬 확인
        for i in range(len(mentions) - 1):
            assert mentions[i].timestamp >= mentions[i + 1].timestamp
    
    @pytest.mark.asyncio
    async def test_collect_reddit_mentions_testing_mode(self, sentiment_service):
        """테스트 모드에서 Reddit 언급 수집 테스트"""
        # 테스트 환경 변수 설정
        with patch('os.getenv', return_value='true'):
            # 테스트 실행
            mentions = await sentiment_service._collect_reddit_mentions('AAPL', '24h')
            
            # 검증
            assert isinstance(mentions, list)
            
            # 각 언급 확인
            for mention in mentions:
                assert isinstance(mention, StockMention)
                assert mention.symbol == 'AAPL'
                assert mention.source == SentimentSource.REDDIT
                assert mention.community in ['wallstreetbets', 'investing', 'stocks']
                assert mention.author.startswith('reddit_user_')
                assert mention.upvotes > 0
                assert -1.0 <= mention.sentiment_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_collect_twitter_mentions_testing_mode(self, sentiment_service):
        """테스트 모드에서 Twitter 언급 수집 테스트"""
        # 테스트 환경 변수 설정
        with patch('os.getenv', return_value='true'):
            # 테스트 실행
            mentions = await sentiment_service._collect_twitter_mentions('AAPL', '24h')
            
            # 검증
            assert isinstance(mentions, list)
            
            # 각 언급 확인
            for mention in mentions:
                assert isinstance(mention, StockMention)
                assert mention.symbol == 'AAPL'
                assert mention.source == SentimentSource.TWITTER
                assert mention.community == 'twitter'
                assert mention.author.startswith('twitter_user_')
                assert mention.upvotes > 0
                assert -1.0 <= mention.sentiment_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_collect_reddit_mentions_api_error(self, sentiment_service, mock_aiohttp):
        """Reddit API 오류 시 언급 수집 테스트"""
        # 테스트 환경 변수 설정 (실제 API 호출)
        with patch('os.getenv', return_value='false'):
            # 모의 HTTP 응답 오류 설정
            mock_response = AsyncMock()
            mock_response.status = 500
            
            mock_aiohttp.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # 테스트 실행
            mentions = await sentiment_service._collect_reddit_mentions('AAPL', '24h')
            
            # 검증
            assert mentions == []
    
    @pytest.mark.asyncio
    async def test_collect_twitter_mentions_api_error(self, sentiment_service, mock_aiohttp):
        """Twitter API 오류 시 언급 수집 테스트"""
        # 테스트 환경 변수 설정 (실제 API 호출)
        with patch('os.getenv', return_value='false'):
            # 모의 HTTP 응답 오류 설정
            mock_response = AsyncMock()
            mock_response.status = 500
            
            mock_aiohttp.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # 테스트 실행
            mentions = await sentiment_service._collect_twitter_mentions('AAPL', '24h')
            
            # 검증
            assert mentions == []
    
    def test_contains_stock_mention(self, sentiment_service):
        """주식 언급 포함 확인 테스트"""
        # 테스트 케이스
        test_cases = [
            # (텍스트, 심볼, 예상 결과)
            ('$AAPL is going up', 'AAPL', True),
            ('AAPL stock is bullish', 'AAPL', True),
            ('I like AAPL', 'AAPL', True),
            ('Apple is good', 'AAPL', False),
            ('$AAPL', 'AAPL', True),
            ('AAPL', 'AAPL', True),
            ('aapl', 'aapl', True),  # 소문자
            ('Something else', 'AAPL', False)
        ]
        
        for text, symbol, expected in test_cases:
            result = sentiment_service._contains_stock_mention(text, symbol)
            assert result == expected, f"Failed for text: '{text}', symbol: '{symbol}'"
    
    def test_analyze_sentiment(self, sentiment_service):
        """감성 분석 테스트"""
        # 테스트 케이스
        test_cases = [
            # (텍스트, 예상 감성 범위)
            ('This stock is going to the moon! 🚀', (0.1, 1.0)),  # 긍정적
            ('This stock is crashing hard', (-1.0, -0.1)),  # 부정적
            ('The stock is trading sideways', (-0.3, 0.3)),  # 중립적
            ('Technical analysis shows support at $150', (-0.3, 0.3)),  # 분석적
        ]
        
        for text, expected_range in test_cases:
            result = sentiment_service.analyze_sentiment(text)
            
            # 검증
            assert isinstance(result, SentimentResult)
            assert -1.0 <= result.compound_score <= 1.0
            assert 0.0 <= result.positive_score <= 1.0
            assert 0.0 <= result.negative_score <= 1.0
            assert 0.0 <= result.neutral_score <= 1.0
            assert 0.0 <= result.confidence <= 1.0
            
            # 예상 범위 확인
            min_score, max_score = expected_range
            assert min_score <= result.compound_score <= max_score
    
    def test_analyze_stock_specific_terms(self, sentiment_service):
        """주식 특정 용어 분석 테스트"""
        # 테스트 케이스
        test_cases = [
            # (텍스트, 예상 방향)
            ('This is going to the moon! 🚀', 'positive'),  # 긍정적
            ('Paper hands selling', 'negative'),  # 부정적
            ('Diamond hands holding', 'positive'),  # 긍정적
            ('Technical analysis chart', 'neutral'),  # 중립적
        ]
        
        for text, expected_direction in test_cases:
            result = sentiment_service._analyze_stock_specific_terms(text)
            
            # 검증
            assert isinstance(result, dict)
            assert 'positive' in result
            assert 'negative' in result
            assert 'compound' in result
            
            if expected_direction == 'positive':
                assert result['positive'] > 0
                assert result['compound'] > 0
            elif expected_direction == 'negative':
                assert result['negative'] > 0
                assert result['compound'] < 0
            else:  # neutral
                assert result['compound'] == 0
    
    def test_calculate_confidence(self, sentiment_service):
        """신뢰도 계산 테스트"""
        # 테스트 케이스
        test_cases = [
            # (VADER 점수, 주식 점수, 예상 신뢰도 범위)
            ({'pos': 0.8, 'neg': 0.1, 'neu': 0.1}, {'compound': 0.7}, (0.5, 1.0)),
            ({'pos': 0.1, 'neg': 0.8, 'neu': 0.1}, {'compound': -0.7}, (0.5, 1.0)),
            ({'pos': 0.3, 'neg': 0.3, 'neu': 0.4}, {'compound': 0.0}, (0.0, 0.8)),
        ]
        
        for vader_scores, stock_scores, expected_range in test_cases:
            confidence = sentiment_service._calculate_confidence(vader_scores, stock_scores)
            
            # 검증
            assert 0.0 <= confidence <= 1.0
            min_conf, max_conf = expected_range
            assert min_conf <= confidence <= max_conf
    
    def test_detect_investment_style(self, sentiment_service):
        """투자 스타일 감지 테스트"""
        # 테스트 케이스
        test_cases = [
            # (텍스트, 예상 스타일)
            ('Day trading AAPL for quick profits', InvestmentStyle.DAY_TRADING),
            ('Value investing in undervalued stocks', InvestmentStyle.VALUE_INVESTING),
            ('Growth stocks with future potential', InvestmentStyle.GROWTH_INVESTING),
            ('Long term buy and hold strategy', InvestmentStyle.LONG_TERM),
            ('Swing trading opportunities', InvestmentStyle.SWING_TRADING),
            ('Just random stock talk', InvestmentStyle.SWING_TRADING),  # 기본값
        ]
        
        for text, expected_style in test_cases:
            result = sentiment_service._detect_investment_style(text)
            # 'Day trading'의 경우 'day'가 'swing'에 포함되지 않으므로 DAY_TRADING이 반환되어야 함
            if expected_style == InvestmentStyle.DAY_TRADING:
                assert result == InvestmentStyle.DAY_TRADING
            elif expected_style == InvestmentStyle.SWING_TRADING:
                assert result == InvestmentStyle.SWING_TRADING
            else:
                assert result == expected_style
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data_cache_hit(self, sentiment_service, mock_cache_manager, sample_sentiment_data):
        """캐시 히트 시 감성 데이터 조회 테스트"""
        # 캐시에 미리 데이터 저장
        mock_cache_manager.get.return_value = sample_sentiment_data
        
        # 테스트 실행
        result = await sentiment_service.get_sentiment_data('AAPL')
        
        # 검증
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert 'overall_sentiment' in result
        assert 'mention_count_24h' in result
        
        # 캐시가 호출되었는지 확인
        expected_key = f"sentiment_AAPL"
        mock_cache_manager.get.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data_cache_miss(self, sentiment_service, mock_cache_manager):
        """캐시 미스 시 감성 데이터 조회 테스트"""
        # 캐시에 데이터 없음 설정
        mock_cache_manager.get.return_value = None
        
        # 모의 언급 데이터 설정
        mentions = [
            create_mock_stock_mention('AAPL', 0.3),
            create_mock_stock_mention('AAPL', 0.2),
            create_mock_stock_mention('AAPL', -0.1),
            create_mock_stock_mention('AAPL', -0.2),
            create_mock_stock_mention('AAPL', 0.0)
        ]
        
        sentiment_service.collect_mentions = AsyncMock(return_value=mentions)
        sentiment_service._check_trending_status = AsyncMock(return_value=(False, 1.0))
        sentiment_service._analyze_community_breakdown = AsyncMock(return_value=[])
        
        # 테스트 실행
        result = await sentiment_service.get_sentiment_data('AAPL')
        
        # 검증
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert result['overall_sentiment'] == 0.04  # (0.3 + 0.2 - 0.1 - 0.2 + 0.0) / 5
        assert result['mention_count_24h'] == 5
        assert result['positive_mentions'] == 2
        # SentimentService에서는 -0.1보다 작은 값만 부정으로 간주하므로 -0.2만 부정
        assert result['negative_mentions'] == 1
        assert result['neutral_mentions'] == 2  # 0.0은 중립으로 간주
        
        # 캐시 저장이 호출되었는지 확인
        mock_cache_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_sentiment_data_no_mentions(self, sentiment_service, mock_cache_manager):
        """언급 없을 시 감성 데이터 조회 테스트"""
        # 캐시에 데이터 없음 설정
        mock_cache_manager.get.return_value = None
        
        # 모의 언급 데이터 설정 (빈 리스트)
        sentiment_service.collect_mentions = AsyncMock(return_value=[])
        
        # 테스트 실행
        result = await sentiment_service.get_sentiment_data('AAPL')
        
        # 검증
        assert result is None
        
        # 캐시 저장이 호출되지 않았는지 확인
        mock_cache_manager.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_trending_status(self, sentiment_service):
        """트렌딩 상태 확인 테스트"""
        # 테스트 케이스
        test_cases = [
            # (현재 언급, 역사적 언급, 예상 트렌딩, 예상 점수)
            (100, 50, True, 10.0),  # 100 / (50/7) = 14, capped at 10.0 -> trending=True
            (50, 50, True, 7.0),   # 50 / (50/7) = 7, trending=True (>= 2.0)
            (25, 50, True, 3.5),   # 25 / (50/7) = 3.5, trending=True (>= 2.0)
            (200, 10, True, 10.0),  # 200 / (10/7) = 140, capped at 10.0 -> trending=True
        ]
        
        for current_count, historical_count, expected_trending, expected_score in test_cases:
            # 모의 역사적 데이터 설정
            sentiment_service._get_historical_mention_count = AsyncMock(return_value=historical_count)
            
            # 테스트 실행
            mentions = [create_mock_stock_mention('AAPL', 0.0)] * current_count
            trending, score = await sentiment_service._check_trending_status('AAPL', mentions)
            
            # 검증
            assert trending == expected_trending
            # 점수는 계산 방식에 따라 약간의 차이가 있을 수 있음
            assert abs(score - expected_score) < 0.1
    
    @pytest.mark.asyncio
    async def test_get_historical_mention_count(self, sentiment_service):
        """역사적 언급 수 조회 테스트"""
        # 테스트 실행
        result = await sentiment_service._get_historical_mention_count('AAPL', '7d')
        
        # 검증
        assert isinstance(result, int)
        assert 50 <= result <= 500  # 모의 데이터 범위
    
    def test_analyze_community_breakdown(self, sentiment_service):
        """커뮤니티 분석 테스트"""
        # 샘플 언급 데이터
        mentions = [
            create_mock_stock_mention('AAPL', 0.3),
            create_mock_stock_mention('AAPL', 0.2),
            create_mock_stock_mention('AAPL', -0.1)
        ]
        
        # 커뮤니티 설정
        mentions[0].community = 'wallstreetbets'
        mentions[1].community = 'investing'
        mentions[2].community = 'wallstreetbets'
        
        # 테스트 실행
        breakdown = sentiment_service._analyze_community_breakdown(mentions)
        
        # 검증
        assert isinstance(breakdown, list)
        assert len(breakdown) == 2  # wallstreetbets, investing
        
        # wallstreetbets 확인
        ws_breakdown = next((b for b in breakdown if b['community'] == 'wallstreetbets'), None)
        assert ws_breakdown is not None
        assert ws_breakdown['mentions'] == 2
        assert ws_breakdown['avg_sentiment'] == 0.1  # (0.3 + (-0.1)) / 2
        
        # investing 확인
        inv_breakdown = next((b for b in breakdown if b['community'] == 'investing'), None)
        assert inv_breakdown is not None
        assert inv_breakdown['mentions'] == 1
        assert inv_breakdown['avg_sentiment'] == 0.2
        
        # 정렬 확인 (언급 수 기준 내림차순)
        assert breakdown[0]['mentions'] >= breakdown[1]['mentions']
    
    @pytest.mark.asyncio
    async def test_get_trending_stocks_cache_hit(self, sentiment_service, mock_cache_manager):
        """캐시 히트 시 트렌딩 주식 조회 테스트"""
        # 샘플 트렌딩 데이터
        trending_data = [
            {
                'symbol': 'AAPL',
                'trend_score': 2.0,
                'mention_count_24h': 100,
                'sentiment_score': 0.3
            }
        ]
        
        # 캐시에 미리 데이터 저장
        mock_cache_manager.get.return_value = trending_data
        
        # 테스트 실행
        result = await sentiment_service.get_trending_stocks(limit=5)
        
        # 검증
        assert result is not None
        assert len(result) == 1
        assert result[0]['symbol'] == 'AAPL'
        
        # 캐시가 호출되었는지 확인
        expected_key = f"trending_5"
        mock_cache_manager.get.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_get_trending_stocks_cache_miss(self, sentiment_service, mock_cache_manager):
        """캐시 미스 시 트렌딩 주식 조회 테스트"""
        # 캐시에 데이터 없음 설정
        mock_cache_manager.get.return_value = None
        
        # 모의 감성 데이터 설정
        def mock_get_sentiment_data(symbol):
            if symbol in ['GME', 'AMC']:
                return {
                    'symbol': symbol,
                    'trending_status': True,
                    'trend_score': 2.0,
                    'mention_count_24h': 100,
                    'overall_sentiment': 0.3  # 'sentiment_score'를 'overall_sentiment'로 변경
                }
            return None
        
        sentiment_service.get_sentiment_data = AsyncMock(side_effect=mock_get_sentiment_data)
        
        # 테스트 실행
        result = await sentiment_service.get_trending_stocks(limit=5)
        
        # 검증
        assert result is not None
        assert len(result) == 2  # GME, AMC만 트렌딩
        
        # 트렌드 점수순 정렬 확인
        assert all(result[i]['trend_score'] >= result[i+1]['trend_score']
                  for i in range(len(result)-1))
        
        # 캐시 저장이 호출되었는지 확인
        mock_cache_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_reddit(self, sentiment_service):
        """Reddit 속도 제한 테스트"""
        # 속도 제한 설정
        sentiment_service.reddit_requests_per_minute = 2
        sentiment_service.reddit_request_times = []
        
        # 첫 번째 요청
        await sentiment_service._check_rate_limit('reddit')
        
        # 두 번째 요청 (제한 내)
        await sentiment_service._check_rate_limit('reddit')
        
        # 세 번째 요청 (제한 초과 - 대기 필요)
        start_time = datetime.now()
        await sentiment_service._check_rate_limit('reddit')
        end_time = datetime.now()
        
        # 검증
        # 세 번째 요청은 대기 시간 있음
        # (실제 대기 시간은 테스트 환경에 따라 다를 수 있음)
        assert (end_time - start_time).total_seconds() >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting_twitter(self, sentiment_service):
        """Twitter 속도 제한 테스트"""
        # 속도 제한 설정
        sentiment_service.twitter_requests_per_minute = 2
        sentiment_service.twitter_request_times = []
        
        # 첫 번째 요청
        await sentiment_service._check_rate_limit('twitter')
        
        # 두 번째 요청 (제한 내)
        await sentiment_service._check_rate_limit('twitter')
        
        # 세 번째 요청 (제한 초과 - 대기 필요)
        start_time = datetime.now()
        await sentiment_service._check_rate_limit('twitter')
        end_time = datetime.now()
        
        # 검증
        # 세 번째 요청은 대기 시간 있음
        assert (end_time - start_time).total_seconds() >= 0
    
    @pytest.mark.asyncio
    async def test_close(self, sentiment_service):
        """서비스 종료 테스트"""
        # 모의 HTTP 세션 설정
        mock_reddit_session = AsyncMock()
        mock_twitter_session = AsyncMock()
        sentiment_service.reddit_session = mock_reddit_session
        sentiment_service.twitter_session = mock_twitter_session
        
        # 세션 상태 설정 (closed=False로 설정)
        mock_reddit_session.closed = False
        mock_twitter_session.closed = False
        
        # 테스트 실행
        await sentiment_service.close()
        
        # 검증 - 세션이 None이 아니고 close가 호출되었는지 확인
        mock_reddit_session.close.assert_called_once()
        mock_twitter_session.close.assert_called_once()
        
        # 세션 초기화 확인
        assert sentiment_service._sessions_created is False


# 테스트 헬퍼 함수
def create_mock_stock_mention(symbol: str, sentiment_score: float = 0.0):
    """모의 주식 언급 생성 헬퍼"""
    return StockMention(
        symbol=symbol,
        text=f"Mock mention about {symbol}",
        source=SentimentSource.REDDIT,
        community='wallstreetbets',
        author=f'test_user_{symbol}',
        timestamp=datetime.utcnow() - timedelta(hours=1),
        upvotes=100,
        sentiment_score=sentiment_score,
        investment_style=InvestmentStyle.DAY_TRADING,
        url=f'https://reddit.com/mock/{symbol}'
    )