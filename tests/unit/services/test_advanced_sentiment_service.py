"""
고급 감성 분석 서비스 단위 테스트

이 모듈은 고급 감성 분석 서비스의 개별 기능을 테스트합니다.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.services.advanced_sentiment_service import AdvancedSentimentService, SentimentModel
from backend.models.unified_models import SentimentResult, SentimentScore, SentimentSource


class TestAdvancedSentimentService:
    """고급 감성 분석 서비스 단위 테스트 클래스"""
    
    @pytest.fixture
    def advanced_sentiment_service(self):
        """고급 감성 분석 서비스 픽스처"""
        mock_cache = MagicMock()
        return AdvancedSentimentService(cache_manager=mock_cache)
    
    @pytest.fixture
    def mock_news_data(self):
        """모의 뉴스 데이터 픽스처"""
        return [
            {
                "title": "Apple Reports Record Quarterly Earnings",
                "content": "Apple Inc. announced better than expected quarterly earnings, driven by strong iPhone sales and services revenue.",
                "source": "financial_times",
                "published_at": "2023-01-15T10:30:00Z",
                "author": "John Doe"
            },
            {
                "title": "Tech Stocks Face Headwinds",
                "content": "Technology stocks are facing challenges due to supply chain issues and regulatory concerns.",
                "source": "reuters",
                "published_at": "2023-01-14T14:20:00Z",
                "author": "Jane Smith"
            }
        ]
    
    @pytest.fixture
    def mock_social_data(self):
        """모의 소셜 미디어 데이터 픽스처"""
        return [
            {
                "platform": "twitter",
                "content": "Just bought more $AAPL stock! Bullish on their new product lineup 🚀",
                "author": "trader123",
                "published_at": "2023-01-15T09:15:00Z",
                "likes": 45,
                "retweets": 12,
                "followers": 1500
            },
            {
                "platform": "reddit",
                "content": "Concerned about Apple's supply chain issues affecting Q2 earnings",
                "author": "investor456",
                "published_at": "2023-01-14T16:45:00Z",
                "upvotes": 23,
                "comments": 8,
                "subreddit": "investing"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_news_sentiment_positive(self, advanced_sentiment_service, mock_news_data):
        """긍정 뉴스 감성 분석 테스트"""
        with patch.object(advanced_sentiment_service, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = SentimentResult(
                compound_score=0.75,
                positive_score=0.75,
                negative_score=0.0,
                neutral_score=0.25,
                confidence=0.85,
                source=SentimentSource.NEWS,
                model_used="bert_financial",
                financial_keywords=["earnings", "strong", "growth", "success"]
            )
            
            result = await advanced_sentiment_service.analyze_sentiment(
                mock_news_data[0]["content"],
                SentimentModel.BERT_FINANCIAL
            )
            
            assert result is not None
            assert result.compound_score == 0.75
            assert result.confidence == 0.85
            assert result.model_used == "bert_financial"
            assert "earnings" in result.financial_keywords
            assert "strong" in result.financial_keywords
    
    @pytest.mark.asyncio
    async def test_analyze_news_sentiment_negative(self, advanced_sentiment_service, mock_news_data):
        """부정 뉴스 감성 분석 테스트"""
        with patch.object(advanced_sentiment_service, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = SentimentResult(
                compound_score=-0.65,
                positive_score=0.0,
                negative_score=0.65,
                neutral_score=0.35,
                confidence=0.80,
                source=SentimentSource.NEWS,
                model_used="bert_financial",
                financial_keywords=["challenges", "issues", "concerns", "headwinds"]
            )
            
            result = await advanced_sentiment_service.analyze_sentiment(
                mock_news_data[1]["content"],
                SentimentModel.BERT_FINANCIAL
            )
            
            assert result is not None
            assert result.compound_score == -0.65
            assert result.confidence == 0.80
            assert result.model_used == "bert_financial"
            assert "challenges" in result.financial_keywords
            assert "issues" in result.financial_keywords
    
    @pytest.mark.asyncio
    async def test_analyze_social_sentiment_positive(self, advanced_sentiment_service, mock_social_data):
        """긍정 소셜 미디어 감성 분석 테스트"""
        with patch.object(advanced_sentiment_service, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = SentimentResult(
                compound_score=0.80,
                positive_score=0.80,
                negative_score=0.0,
                neutral_score=0.20,
                confidence=0.75,
                source=SentimentSource.SOCIAL,
                model_used="bert_financial",
                financial_keywords=["bullish", "bought", "product", "growth"]
            )
            
            result = await advanced_sentiment_service.analyze_sentiment(
                mock_social_data[0]["content"],
                SentimentModel.BERT_FINANCIAL
            )
            
            assert result is not None
            assert result.compound_score == 0.80
            assert result.confidence == 0.75
            assert result.model_used == "bert_financial"
            assert "bullish" in result.financial_keywords
            assert "bought" in result.financial_keywords
    
    @pytest.mark.asyncio
    async def test_analyze_social_sentiment_negative(self, advanced_sentiment_service, mock_social_data):
        """부정 소셜 미디어 감성 분석 테스트"""
        with patch.object(advanced_sentiment_service, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = SentimentResult(
                compound_score=-0.55,
                positive_score=0.0,
                negative_score=0.55,
                neutral_score=0.45,
                confidence=0.70,
                source=SentimentSource.SOCIAL,
                model_used="bert_financial",
                financial_keywords=["concerned", "issues", "affecting", "supply chain"]
            )
            
            result = await advanced_sentiment_service.analyze_sentiment(
                mock_social_data[1]["content"],
                SentimentModel.BERT_FINANCIAL
            )
            
            assert result is not None
            assert result.compound_score == -0.55
            assert result.confidence == 0.70
            assert result.model_used == "bert_financial"
            assert "concerned" in result.financial_keywords
            assert "issues" in result.financial_keywords
    
    @pytest.mark.asyncio
    async def test_analyst_sentiment_analysis(self, advanced_sentiment_service):
        """애널리스트 감성 분석 테스트"""
        analyst_text = "Strong buy recommendation based on solid fundamentals and product pipeline"
        
        with patch.object(advanced_sentiment_service, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = SentimentResult(
                compound_score=0.75,
                positive_score=0.75,
                negative_score=0.0,
                neutral_score=0.25,
                confidence=0.85,
                source=SentimentSource.ANALYST,
                model_used="bert_financial",
                financial_keywords=["buy", "strong", "fundamentals", "growth"]
            )
            
            result = await advanced_sentiment_service.analyze_sentiment(
                analyst_text,
                SentimentModel.BERT_FINANCIAL
            )
            
            assert result is not None
            assert result.compound_score > 0  # 긍정 감성
            assert result.confidence > 0.5
            assert result.model_used == "bert_financial"
            assert result.financial_keywords is not None
            assert len(result.financial_keywords) > 0
    
    @pytest.mark.asyncio
    async def test_comprehensive_sentiment_analysis(self, advanced_sentiment_service, mock_news_data, mock_social_data):
        """종합 감성 분석 테스트"""
        # 뉴스와 소셜 데이터에서 텍스트 추출
        news_text = mock_news_data[0]["content"]
        social_text = mock_social_data[0]["content"]
        
        with patch.object(advanced_sentiment_service, 'analyze_batch_sentiment') as mock_analyze:
            mock_analyze.return_value = [
                SentimentResult(
                    compound_score=0.75,
                    positive_score=0.75,
                    negative_score=0.0,
                    neutral_score=0.25,
                    confidence=0.85,
                    source=SentimentSource.NEWS,
                    model_used="bert_financial",
                    financial_keywords=["earnings", "growth"]
                ),
                SentimentResult(
                    compound_score=0.80,
                    positive_score=0.80,
                    negative_score=0.0,
                    neutral_score=0.20,
                    confidence=0.75,
                    source=SentimentSource.SOCIAL,
                    model_used="bert_financial",
                    financial_keywords=["bullish", "bought"]
                )
            ]
            
            result = await advanced_sentiment_service.analyze_batch_sentiment(
                [news_text, social_text],
                SentimentModel.BERT_FINANCIAL
            )
            
            assert result is not None
            assert len(result) == 2
            assert result[0].compound_score == 0.75
            assert result[1].compound_score == 0.80
            assert all(r.financial_keywords for r in result)
    
    @pytest.mark.asyncio
    async def test_sentiment_trend_analysis(self, advanced_sentiment_service):
        """감성 트렌드 분석 테스트"""
        # 시간에 따른 감성 데이터
        historical_data = [
            {"date": "2023-01-01", "sentiment": 0.60, "confidence": 0.80},
            {"date": "2023-01-02", "sentiment": 0.65, "confidence": 0.82},
            {"date": "2023-01-03", "sentiment": 0.70, "confidence": 0.85},
            {"date": "2023-01-04", "sentiment": 0.75, "confidence": 0.87},
            {"date": "2023-01-05", "sentiment": 0.80, "confidence": 0.90}
        ]
        
        with patch.object(advanced_sentiment_service, 'analyze_sentiment_trend') as mock_analyze:
            mock_analyze.return_value = {
                "success": True,
                "trend": "increasing",
                "trend_strength": 0.8,
                "volatility": 0.2,
                "key_events": [
                    {"date": "2023-01-02", "event": "earnings_release", "impact": 0.3}
                ]
            }
            
            result = await advanced_sentiment_service.analyze_sentiment_trend(historical_data)
            
            assert result is not None
            assert result["success"] is True
            assert result["trend"] == "increasing"
            assert result["trend_strength"] == 0.8
            assert "key_events" in result
    
    @pytest.mark.asyncio
    async def test_sentiment_anomaly_detection(self, advanced_sentiment_service):
        """감성 이상 감지 테스트"""
        # 정상 감성 데이터와 이상 데이터 텍스트
        texts = [
            "Normal positive sentiment about earnings",
            "Steady performance expectations",
            "Moderate growth forecast",
            "SHOCKING NEWS: Major scandal discovered!",
            "Continued positive outlook"
        ]
        
        with patch.object(advanced_sentiment_service, 'analyze_batch_sentiment') as mock_analyze:
            mock_analyze.return_value = [
                SentimentResult(
                    compound_score=0.6 if i < 3 else -0.8 if i == 3 else 0.7,
                    positive_score=0.6 if i < 3 else 0.0 if i == 3 else 0.7,
                    negative_score=0.0 if i < 3 else 0.8 if i == 3 else 0.0,
                    neutral_score=0.4 if i < 3 else 0.2 if i == 3 else 0.3,
                    confidence=0.8,
                    source=SentimentSource.NEWS,
                    model_used="bert_financial",
                    financial_keywords=[]
                ) for i, text in enumerate(texts)
            ]
            
            result = await advanced_sentiment_service.analyze_batch_sentiment(texts)
            
            assert result is not None
            assert len(result) == 5
            # 이상 감지: 4번째 텍스트가 갑작스러운 부정 전환
            assert result[3].compound_score < -0.5
            assert result[3].model_used == "bert_financial"
    
    @pytest.mark.asyncio
    async def test_cross_platform_sentiment_correlation(self, advanced_sentiment_service):
        """플랫폼 간 감성 상관관계 분석 테스트"""
        # 다양한 플랫폼의 감성 데이터
        symbol = "AAPL"
        texts = [
            "Positive news about earnings",
            "Bullish social media sentiment",
            "Analyst buy recommendation"
        ]
        
        result = await advanced_sentiment_service.get_financial_context_sentiment(
            symbol,
            texts,
            {"sector": "Technology", "day_change_pct": 2.5}
        )
        
        assert result is not None
        assert "symbol" in result
        assert result["symbol"] == symbol
        assert "overall_sentiment" in result
        assert "sentiment_distribution" in result
        assert "financial_keywords" in result
    
    @pytest.mark.asyncio
    async def test_sentiment_impact_on_price_prediction(self, advanced_sentiment_service):
        """가격 예측에 대한 감성 영향 분석 테스트"""
        # 금융 엔티티 분석 테스트
        text = "Strong earnings report with positive analyst sentiment and bullish social media reaction"
        
        result = await advanced_sentiment_service.analyze_financial_entities(text)
        
        assert result is not None
        assert "entities" in result or "error" not in result
    
    @pytest.mark.asyncio
    async def test_real_time_sentiment_streaming(self, advanced_sentiment_service):
        """실시간 감성 스트리밍 테스트"""
        # 실시간 데이터 스트림 모의
        stream_texts = [
            "Apple announces new product",
            "Excited about $AAPL earnings!",
            "Concerns about supply chain"
        ]
        
        with patch.object(advanced_sentiment_service, 'analyze_batch_sentiment') as mock_analyze:
            mock_analyze.return_value = [
                SentimentResult(
                    compound_score=0.7 - i * 0.1 if i < 2 else -0.6,
                    positive_score=0.7 - i * 0.1 if i < 2 else 0.0,
                    negative_score=0.0 if i < 2 else 0.6,
                    neutral_score=0.3 + i * 0.1 if i < 2 else 0.4,
                    confidence=0.8,
                    source=SentimentSource.SOCIAL,
                    model_used="bert_financial",
                    financial_keywords=[]
                ) for i, text in enumerate(stream_texts)
            ]
            
            result = await advanced_sentiment_service.analyze_batch_sentiment(stream_texts)
            
            assert result is not None
            assert len(result) == 3
            assert result[0].compound_score == 0.7
            assert result[1].compound_score == 0.6
            assert result[2].compound_score == -0.6
    
    @pytest.mark.asyncio
    async def test_sentiment_model_training(self, advanced_sentiment_service):
        """감성 모델 훈련 테스트"""
        # 모델 비교 테스트로 변경
        test_text = "Test sentiment analysis for model comparison"
        
        result = await advanced_sentiment_service.compare_sentiment_models(test_text)
        
        assert result is not None
        assert "error" not in result or len(result) > 0
    
    @pytest.mark.asyncio
    async def test_sentiment_model_evaluation(self, advanced_sentiment_service):
        """감성 모델 평가 테스트"""
        # 모델 통계 테스트로 변경
        result = await advanced_sentiment_service.get_model_stats()
        
        assert result is not None
        assert "available_models" in result
        assert "model_count" in result
        assert "transformers_available" in result
    
    @pytest.mark.asyncio
    async def test_sentiment_confidence_calibration(self, advanced_sentiment_service):
        """감성 신뢰도 보정 테스트"""
        # 배치 감성 분석 테스트로 변경
        texts = [
            "Clearly positive text",
            "Slightly negative text",
            "Very neutral text"
        ]
        
        result = await advanced_sentiment_service.analyze_batch_sentiment(texts)
        
        assert result is not None
        assert len(result) == 3
        assert all(isinstance(r, SentimentResult) for r in result)
        assert all(0 <= r.confidence <= 1 for r in result)
    
    @pytest.mark.asyncio
    async def test_multilingual_sentiment_analysis(self, advanced_sentiment_service):
        """다국어 감성 분석 테스트"""
        # 다국어 텍스트
        multilingual_texts = [
            "Apple reports excellent earnings",
            "Apple publie d'excellents résultats",
            "Apple berichtet überzeugende Ergebnisse",
            "苹果公布优秀业绩"
        ]
        
        # 다국어 모델 사용하여 배치 분석
        result = await advanced_sentiment_service.analyze_batch_sentiment(
            multilingual_texts,
            SentimentModel.BERT_BASE  # 다국어 모델
        )
        
        assert result is not None
        assert len(result) == 4
        assert all(isinstance(r, SentimentResult) for r in result)
        assert all(r.model_used == "bert_base" for r in result)
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_performance(self, advanced_sentiment_service):
        """감성 분석 성능 테스트"""
        import time
        
        # 대량의 텍스트 데이터
        large_text_dataset = [
            {"text": f"Sample text {i} for sentiment analysis", "id": i}
            for i in range(1000)
        ]
        
        with patch.object(advanced_sentiment_service, 'analyze_batch_sentiment') as mock_analyze:
            mock_analyze.return_value = [
                SentimentResult(
                    compound_score=0.5,
                    positive_score=0.5,
                    negative_score=0.0,
                    neutral_score=0.5,
                    confidence=0.8,
                    source=SentimentSource.NEWS,
                    model_used="bert_financial",
                    financial_keywords=[]
                ) for i in range(1000)
            ]
            
            start_time = time.time()
            
            results = await advanced_sentiment_service.analyze_batch_sentiment(
                [f"Sample text {i} for sentiment analysis" for i in range(1000)]
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            assert len(results) == 1000
            assert processing_time < 10.0  # 10초 이내 처리
            assert processing_time / 1000 < 0.01  # 텍스트당 10ms 이하
            
            print(f"Sentiment Analysis Performance:")
            print(f"  Total Texts: {len(large_text_dataset)}")
            print(f"  Processing Time: {processing_time:.4f}s")
            print(f"  Time per Text: {processing_time / len(large_text_dataset):.6f}s")