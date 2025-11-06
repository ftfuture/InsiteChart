"""
Advanced Sentiment Analysis Service for InsiteChart platform.

This service provides BERT-based advanced sentiment analysis for financial text,
improving accuracy and contextual understanding beyond basic VADER analysis.
"""

import asyncio
import logging
import re
import statistics
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Try to import transformers and torch
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers library not available. Using fallback sentiment analysis.")

from ..cache.unified_cache import UnifiedCacheManager


class SentimentModel(str, Enum):
    """Available sentiment analysis models."""
    VADER = "vader"
    BERT_FINANCIAL = "bert_financial"
    BERT_BASE = "bert_base"
    DISTILBERT = "distilbert"
    ROBERTA = "roberta"


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    text: str
    sentiment_score: float  # -1 to 1
    confidence: float  # 0 to 1
    sentiment_label: str  # positive, negative, neutral
    model_used: str
    processing_time_ms: float
    financial_keywords: List[str] = None
    emotional_indicators: Dict[str, float] = None
    contextual_factors: Dict[str, Any] = None


@dataclass
class FinancialSentimentContext:
    """Financial context for sentiment analysis."""
    symbol: str
    sector: Optional[str] = None
    market_condition: Optional[str] = None  # bull, bear, neutral
    recent_price_change: Optional[float] = None
    volatility: Optional[float] = None
    volume_anomaly: Optional[bool] = None


class AdvancedSentimentService:
    """Advanced sentiment analysis service with BERT models."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Model configurations
        self.models = {}
        self.tokenizers = {}
        self.pipelines = {}
        
        # Financial sentiment lexicon
        self.financial_keywords = self._load_financial_keywords()
        
        # Model cache
        self.model_cache_ttl = 3600  # 1 hour
        
        # Initialize models
        self._initialize_models()
        
        self.logger.info("AdvancedSentimentService initialized")
    
    def _load_financial_keywords(self) -> Dict[str, float]:
        """Load financial sentiment keywords with weights."""
        return {
            # Positive financial terms
            "bullish": 0.8, "rally": 0.7, "surge": 0.8, "soar": 0.9,
            "breakout": 0.7, "momentum": 0.6, "uptrend": 0.7, "growth": 0.6,
            "profit": 0.7, "gain": 0.6, "dividend": 0.5, "buy": 0.6,
            "strong": 0.5, "outperform": 0.7, "beat": 0.6, "exceed": 0.6,
            
            # Negative financial terms
            "bearish": -0.8, "crash": -0.9, "plunge": -0.8, "slump": -0.7,
            "downtrend": -0.7, "decline": -0.6, "loss": -0.7, "sell": -0.6,
            "weak": -0.5, "underperform": -0.7, "miss": -0.6, "below": -0.5,
            "volatility": -0.3, "risk": -0.4, "debt": -0.3, "default": -0.8,
            
            # Neutral financial terms
            "hold": 0.1, "stable": 0.2, "steady": 0.2, "flat": 0.0,
            "neutral": 0.0, "maintain": 0.1, "unchanged": 0.0
        }
    
    def _initialize_models(self):
        """Initialize sentiment analysis models."""
        try:
            if not TRANSFORMERS_AVAILABLE:
                self.logger.warning("Transformers not available, using VADER only")
                return
            
            # Financial BERT model (if available)
            try:
                model_name = "yiyanghkust/finbert-tone"
                self._load_model(SentimentModel.BERT_FINANCIAL, model_name)
            except Exception as e:
                self.logger.warning(f"Could not load financial BERT model: {str(e)}")
            
            # Base BERT model
            try:
                model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
                self._load_model(SentimentModel.BERT_BASE, model_name)
            except Exception as e:
                self.logger.warning(f"Could not load base BERT model: {str(e)}")
            
            # DistilBERT model (faster)
            try:
                model_name = "distilbert-base-uncased-finetuned-sst-2-english"
                self._load_model(SentimentModel.DISTILBERT, model_name)
            except Exception as e:
                self.logger.warning(f"Could not load DistilBERT model: {str(e)}")
            
            # RoBERTa model
            try:
                model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
                self._load_model(SentimentModel.ROBERTA, model_name)
            except Exception as e:
                self.logger.warning(f"Could not load RoBERTa model: {str(e)}")
            
            self.logger.info(f"Initialized {len(self.models)} sentiment models")
            
        except Exception as e:
            self.logger.error(f"Error initializing models: {str(e)}")
    
    def _load_model(self, model_type: SentimentModel, model_name: str):
        """Load a specific sentiment model."""
        try:
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Create pipeline
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                return_all_scores=True
            )
            
            # Store model components
            self.tokenizers[model_type] = tokenizer
            self.models[model_type] = model
            self.pipelines[model_type] = sentiment_pipeline
            
            self.logger.info(f"Loaded model: {model_type.value} ({model_name})")
            
        except Exception as e:
            self.logger.error(f"Error loading model {model_type}: {str(e)}")
            raise
    
    async def analyze_sentiment(
        self, 
        text: str, 
        model: SentimentModel = SentimentModel.BERT_FINANCIAL,
        context: Optional[FinancialSentimentContext] = None
    ) -> SentimentResult:
        """Analyze sentiment of text using specified model."""
        start_time = datetime.utcnow()
        
        try:
            # Check cache first
            cache_key = f"sentiment_{hash(text)}_{model.value}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for sentiment analysis")
                return SentimentResult(**cached_result)
            
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            # Analyze with specified model
            if model == SentimentModel.VADER or not TRANSFORMERS_AVAILABLE:
                result = await self._analyze_with_vader(processed_text, context)
            elif model in self.pipelines:
                result = await self._analyze_with_transformer(
                    processed_text, model, context
                )
            else:
                # Fallback to VADER
                self.logger.warning(f"Model {model} not available, using VADER")
                result = await self._analyze_with_vader(processed_text, context)
            
            # Add processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            
            # Cache result
            await self.cache_manager.set(
                cache_key, 
                result.__dict__, 
                ttl=self.model_cache_ttl
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            # Return neutral sentiment on error
            return SentimentResult(
                text=text,
                sentiment_score=0.0,
                confidence=0.0,
                sentiment_label="neutral",
                model_used="error",
                processing_time_ms=0.0
            )
    
    async def analyze_batch_sentiment(
        self, 
        texts: List[str], 
        model: SentimentModel = SentimentModel.BERT_FINANCIAL,
        context: Optional[FinancialSentimentContext] = None
    ) -> List[SentimentResult]:
        """Analyze sentiment for multiple texts."""
        try:
            # Process in parallel batches
            batch_size = 8  # Adjust based on GPU memory
            results = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_results = await asyncio.gather(
                    *[
                        self.analyze_sentiment(text, model, context)
                        for text in batch
                    ],
                    return_exceptions=True
                )
                
                # Filter out exceptions
                for result in batch_results:
                    if not isinstance(result, Exception):
                        results.append(result)
                    else:
                        self.logger.error(f"Error in batch sentiment analysis: {str(result)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch sentiment analysis: {str(e)}")
            return []
    
    async def get_financial_context_sentiment(
        self, 
        symbol: str, 
        texts: List[str],
        market_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment with financial context."""
        try:
            # Create financial context
            context = self._create_financial_context(symbol, market_data)
            
            # Analyze all texts
            results = await self.analyze_batch_sentiment(texts, context=context)
            
            # Calculate aggregate metrics
            if not results:
                return {"error": "No valid sentiment results"}
            
            sentiment_scores = [r.sentiment_score for r in results]
            confidences = [r.confidence for r in results]
            
            # Weight by confidence
            weighted_sentiment = sum(
                s * c for s, c in zip(sentiment_scores, confidences)
            ) / sum(confidences)
            
            # Calculate distribution
            positive_count = sum(1 for s in sentiment_scores if s > 0.1)
            negative_count = sum(1 for s in sentiment_scores if s < -0.1)
            neutral_count = len(sentiment_scores) - positive_count - negative_count
            
            # Extract financial keywords
            all_keywords = []
            for result in results:
                if result.financial_keywords:
                    all_keywords.extend(result.financial_keywords)
            
            # Analyze emotional indicators
            emotional_profile = self._analyze_emotional_profile(results)
            
            return {
                "symbol": symbol,
                "overall_sentiment": weighted_sentiment,
                "sentiment_distribution": {
                    "positive": positive_count,
                    "negative": negative_count,
                    "neutral": neutral_count
                },
                "confidence": statistics.mean(confidences),
                "sample_size": len(results),
                "financial_keywords": list(set(all_keywords)),
                "emotional_profile": emotional_profile,
                "context": context.__dict__ if context else None,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in financial context sentiment: {str(e)}")
            return {"error": str(e)}
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for sentiment analysis."""
        try:
            # Convert to lowercase
            text = text.lower()
            
            # Remove URLs
            text = re.sub(r'http\S+|www\S+', '', text)
            
            # Remove mentions and hashtags (keep text after #)
            text = re.sub(r'@\w+', '', text)
            text = re.sub(r'#', '', text)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Handle emojis (convert to text if needed)
            text = self._handle_emojis(text)
            
            # Handle financial symbols and numbers
            text = self._handle_financial_entities(text)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error preprocessing text: {str(e)}")
            return text
    
    def _handle_emojis(self, text: str) -> str:
        """Convert emojis to text representations."""
        # Simple emoji to text mapping
        emoji_map = {
            "🚀": "rocket bullish",
            "📈": "uptrend positive",
            "📉": "downtrend negative",
            "💰": "money profit",
            "🔥": "hot trending",
            "👍": "positive good",
            "👎": "negative bad",
            "😎": "confident strong",
            "😱": "fear panic",
            "🤔": "uncertain neutral"
        }
        
        for emoji, replacement in emoji_map.items():
            text = text.replace(emoji, f" {replacement} ")
        
        return text
    
    def _handle_financial_entities(self, text: str) -> str:
        """Handle financial entities in text."""
        # Extract and preserve financial symbols
        symbols = re.findall(r'\$[A-Z]+', text)
        for symbol in symbols:
            text = text.replace(symbol, f" {symbol} stock ")
        
        # Handle percentages
        percentages = re.findall(r'\d+\.?\d*%', text)
        for pct in percentages:
            text = text.replace(pct, f" {pct} percent ")
        
        # Handle dollar amounts
        amounts = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', text)
        for amount in amounts:
            text = text.replace(amount, f" {amount} dollars ")
        
        return text
    
    async def _analyze_with_vader(
        self, 
        text: str, 
        context: Optional[FinancialSentimentContext] = None
    ) -> SentimentResult:
        """Analyze sentiment using VADER."""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            
            analyzer = SentimentIntensityAnalyzer()
            scores = analyzer.polarity_scores(text)
            
            # Convert to -1 to 1 scale
            sentiment_score = scores['compound']
            
            # Determine label
            if sentiment_score >= 0.05:
                label = "positive"
            elif sentiment_score <= -0.05:
                label = "negative"
            else:
                label = "neutral"
            
            # Extract financial keywords
            financial_keywords = self._extract_financial_keywords(text)
            
            # Apply financial context adjustment
            if context:
                sentiment_score = self._apply_context_adjustment(
                    sentiment_score, text, context
                )
            
            return SentimentResult(
                text=text,
                sentiment_score=sentiment_score,
                confidence=abs(sentiment_score),
                sentiment_label=label,
                model_used=SentimentModel.VADER.value,
                processing_time_ms=0.0,
                financial_keywords=financial_keywords
            )
            
        except Exception as e:
            self.logger.error(f"Error in VADER analysis: {str(e)}")
            raise
    
    async def _analyze_with_transformer(
        self, 
        text: str, 
        model: SentimentModel,
        context: Optional[FinancialSentimentContext] = None
    ) -> SentimentResult:
        """Analyze sentiment using transformer model."""
        try:
            pipeline = self.pipelines[model]
            
            # Get predictions
            results = pipeline(text)
            
            # Process results (format varies by model)
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    # Multiple labels with scores
                    scores = results[0]
                    sentiment_score = self._convert_transformer_scores(scores)
                    confidence = max(s['score'] for s in scores)
                else:
                    # Single result with label and score
                    result = results[0]
                    sentiment_score = self._convert_single_result(result)
                    confidence = result.get('score', 0.0)
            else:
                # Fallback to neutral
                sentiment_score = 0.0
                confidence = 0.0
            
            # Determine label
            if sentiment_score >= 0.1:
                label = "positive"
            elif sentiment_score <= -0.1:
                label = "negative"
            else:
                label = "neutral"
            
            # Extract financial keywords
            financial_keywords = self._extract_financial_keywords(text)
            
            # Apply financial context adjustment
            if context:
                sentiment_score = self._apply_context_adjustment(
                    sentiment_score, text, context
                )
            
            return SentimentResult(
                text=text,
                sentiment_score=sentiment_score,
                confidence=confidence,
                sentiment_label=label,
                model_used=model.value,
                processing_time_ms=0.0,
                financial_keywords=financial_keywords
            )
            
        except Exception as e:
            self.logger.error(f"Error in transformer analysis: {str(e)}")
            raise
    
    def _convert_transformer_scores(self, scores: List[Dict]) -> float:
        """Convert transformer scores to -1 to 1 scale."""
        try:
            # Map labels to scores
            label_scores = {}
            for score_dict in scores:
                label = score_dict['label'].lower()
                score = score_dict['score']
                
                if 'pos' in label:
                    label_scores['positive'] = score
                elif 'neg' in label:
                    label_scores['negative'] = score
                else:
                    label_scores['neutral'] = score
            
            # Calculate weighted score
            positive = label_scores.get('positive', 0)
            negative = label_scores.get('negative', 0)
            neutral = label_scores.get('neutral', 0)
            
            # Convert to -1 to 1 scale
            if positive > negative and positive > neutral:
                return positive
            elif negative > positive and negative > neutral:
                return -negative
            else:
                return (positive - negative)
                
        except Exception as e:
            self.logger.error(f"Error converting transformer scores: {str(e)}")
            return 0.0
    
    def _convert_single_result(self, result: Dict) -> float:
        """Convert single transformer result to -1 to 1 scale."""
        try:
            label = result['label'].lower()
            score = result['score']
            
            if 'pos' in label:
                return score
            elif 'neg' in label:
                return -score
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error converting single result: {str(e)}")
            return 0.0
    
    def _extract_financial_keywords(self, text: str) -> List[str]:
        """Extract financial keywords from text."""
        keywords = []
        text_lower = text.lower()
        
        for keyword, weight in self.financial_keywords.items():
            if keyword in text_lower:
                keywords.append(keyword)
        
        return keywords
    
    def _apply_context_adjustment(
        self, 
        base_score: float, 
        text: str, 
        context: FinancialSentimentContext
    ) -> float:
        """Apply financial context adjustments to sentiment score."""
        try:
            adjusted_score = base_score
            
            # Market condition adjustment
            if context.market_condition:
                if context.market_condition == "bear":
                    # In bear market, negative sentiment is weighted more heavily
                    if adjusted_score < 0:
                        adjusted_score *= 1.2
                elif context.market_condition == "bull":
                    # In bull market, positive sentiment is weighted more heavily
                    if adjusted_score > 0:
                        adjusted_score *= 1.2
            
            # Recent price change adjustment
            if context.recent_price_change is not None:
                price_change_weight = 0.1
                if (context.recent_price_change > 0 and adjusted_score > 0) or \
                   (context.recent_price_change < 0 and adjusted_score < 0):
                    # Sentiment aligns with price movement
                    adjusted_score *= (1 + price_change_weight)
                else:
                    # Sentiment contradicts price movement
                    adjusted_score *= (1 - price_change_weight)
            
            # Volatility adjustment
            if context.volatility is not None and context.volatility > 0.3:
                # High volatility reduces confidence in sentiment
                adjusted_score *= 0.9
            
            # Ensure score stays within bounds
            return max(-1.0, min(1.0, adjusted_score))
            
        except Exception as e:
            self.logger.error(f"Error applying context adjustment: {str(e)}")
            return base_score
    
    def _create_financial_context(
        self, 
        symbol: str, 
        market_data: Optional[Dict] = None
    ) -> FinancialSentimentContext:
        """Create financial context from market data."""
        try:
            context = FinancialSentimentContext(symbol=symbol)
            
            if market_data:
                context.sector = market_data.get('sector')
                context.recent_price_change = market_data.get('day_change_pct')
                context.volatility = market_data.get('volatility')
                context.volume_anomaly = market_data.get('volume_anomaly', False)
                
                # Determine market condition
                market_sentiment = market_data.get('market_sentiment', 0)
                if market_sentiment > 0.2:
                    context.market_condition = "bull"
                elif market_sentiment < -0.2:
                    context.market_condition = "bear"
                else:
                    context.market_condition = "neutral"
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error creating financial context: {str(e)}")
            return FinancialSentimentContext(symbol=symbol)
    
    def _analyze_emotional_profile(self, results: List[SentimentResult]) -> Dict[str, float]:
        """Analyze emotional profile from sentiment results."""
        try:
            # Simple emotional indicators based on sentiment distribution
            scores = [r.sentiment_score for r in results]
            
            if not scores:
                return {}
            
            # Calculate emotional metrics
            avg_sentiment = statistics.mean(scores)
            sentiment_variance = statistics.variance(scores) if len(scores) > 1 else 0
            
            # Emotional intensity (how extreme the sentiments are)
            intensity = statistics.mean([abs(s) for s in scores])
            
            # Emotional consistency (how similar the sentiments are)
            consistency = 1.0 - min(1.0, sentiment_variance)
            
            # Emotional momentum (trend over time if available)
            momentum = 0.0  # Would need timestamped data for real calculation
            
            return {
                "average_sentiment": avg_sentiment,
                "intensity": intensity,
                "consistency": consistency,
                "momentum": momentum,
                "variance": sentiment_variance
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing emotional profile: {str(e)}")
            return {}
    
    async def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about available models."""
        try:
            return {
                "available_models": list(self.models.keys()),
                "transformers_available": TRANSFORMERS_AVAILABLE,
                "model_count": len(self.models),
                "financial_keywords_count": len(self.financial_keywords),
                "cache_ttl": self.model_cache_ttl
            }
            
        except Exception as e:
            self.logger.error(f"Error getting model stats: {str(e)}")
            return {}