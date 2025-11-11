"""
BERT-based Advanced Sentiment Analysis Service for InsiteChart platform.

This service provides advanced sentiment analysis using BERT models
for financial text analysis, improving upon the basic VADER approach.
"""

import asyncio
import logging
import torch
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import re

from ..cache.unified_cache import UnifiedCacheManager


@dataclass
class SentimentAnalysisResult:
    """Sentiment analysis result data structure."""
    symbol: str
    overall_sentiment: float  # -1 to 1 scale
    confidence: float  # 0 to 1 scale
    sentiment_breakdown: Dict[str, float]  # positive, negative, neutral
    source_breakdown: Dict[str, float]  # news, social, analyst
    key_phrases: List[str]  # Important phrases detected
    entities: List[Dict[str, Any]]  # Named entities
    topics: List[str]  # Detected topics
    timestamp: datetime
    model_version: str


@dataclass
class SentimentSource:
    """Sentiment source data structure."""
    source_type: str  # news, social_media, analyst_report
    content: str
    weight: float  # Reliability weight
    timestamp: datetime
    url: Optional[str] = None
    author: Optional[str] = None


class BertSentimentService:
    """Advanced sentiment analysis service using BERT models."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Model configuration
        self.model_name = "ProsusAI/finbert"
        self.tokenizer = None
        self.model = None
        self.sentiment_pipeline = None
        
        # Cache for model results
        self.analysis_cache: Dict[str, SentimentAnalysisResult] = {}
        
        # Financial sentiment keywords
        self.financial_keywords = {
            "positive": [
                "bullish", "uptrend", "growth", "profit", "gain", "rally", 
                "breakout", "momentum", "outperform", "beat", "exceed",
                "strong", "robust", "healthy", "expanding", "improving"
            ],
            "negative": [
                "bearish", "downtrend", "decline", "loss", "drop", 
                "sell-off", "correction", "underperform", "miss", "fall",
                "weak", "poor", "declining", "contracting", "risk"
            ]
        }
        
        self.logger.info("BERTSentimentService initialized")
    
    async def initialize(self):
        """Initialize the BERT model and tokenizer."""
        try:
            self.logger.info("Loading BERT model for sentiment analysis...")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Create sentiment analysis pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                return_all_scores=True
            )
            
            self.logger.info(f"BERT model loaded successfully: {self.model_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize BERT model: {str(e)}")
            raise
    
    async def analyze_sentiment(self, symbol: str, sources: List[SentimentSource]) -> SentimentAnalysisResult:
        """Analyze sentiment for a symbol using multiple sources."""
        try:
            # Check cache first
            cache_key = f"bert_sentiment_{symbol}_{hash(str(sources))}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return SentimentAnalysisResult(**cached_result)
            
            # Analyze each source
            source_results = []
            for source in sources:
                result = await self._analyze_source(source)
                if result:
                    source_results.append(result)
            
            # Combine results with weighted averaging
            overall_result = await self._combine_source_results(symbol, source_results)
            
            # Cache the result
            await self.cache_manager.set(
                cache_key,
                overall_result.__dict__,
                ttl=1800  # 30 minutes
            )
            
            return overall_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment for {symbol}: {str(e)}")
            # Return fallback result
            return SentimentAnalysisResult(
                symbol=symbol,
                overall_sentiment=0.0,
                confidence=0.0,
                sentiment_breakdown={"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                source_breakdown={},
                key_phrases=[],
                entities=[],
                topics=[],
                timestamp=datetime.utcnow(),
                model_version=self.model_name
            )
    
    async def _analyze_source(self, source: SentimentSource) -> Optional[Dict[str, Any]]:
        """Analyze sentiment from a single source."""
        try:
            # Preprocess text
            processed_text = self._preprocess_text(source.content)
            
            if not processed_text:
                return None
            
            # Analyze with BERT
            result = self.sentiment_pipeline(processed_text)
            
            # Extract sentiment scores
            scores = result[0] if result else None
            if not scores:
                return None
            
            # Map to our format
            labels = scores['labels']
            sentiment_scores = scores['scores']
            
            # Find dominant sentiment
            max_score_idx = np.argmax(sentiment_scores)
            dominant_label = labels[max_score_idx]
            confidence = sentiment_scores[max_score_idx]
            
            # Convert to -1 to 1 scale
            if dominant_label == 'POSITIVE':
                sentiment_score = confidence
            elif dominant_label == 'NEGATIVE':
                sentiment_score = -confidence
            else:
                sentiment_score = 0.0
            
            # Extract key phrases and entities
            key_phrases = self._extract_key_phrases(source.content)
            entities = self._extract_entities(source.content)
            topics = self._extract_topics(source.content)
            
            return {
                "source_type": source.source_type,
                "sentiment_score": sentiment_score,
                "confidence": confidence,
                "dominant_label": dominant_label,
                "key_phrases": key_phrases,
                "entities": entities,
                "topics": topics,
                "weight": source.weight,
                "timestamp": source.timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing source: {str(e)}")
            return None
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for BERT analysis."""
        try:
            # Clean text
            text = re.sub(r'http\S+', '', text)  # Remove URLs
            text = re.sub(r'@\w+', '', text)  # Remove mentions
            text = re.sub(r'#\w+', '', text)  # Remove hashtags
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = text.strip()
            
            # Handle financial specific preprocessing
            text = self._normalize_financial_terms(text)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error preprocessing text: {str(e)}")
            return text
    
    def _normalize_financial_terms(self, text: str) -> str:
        """Normalize financial terms for better analysis."""
        try:
            # Common financial term normalizations
            replacements = {
                r'\$': ' dollar ',
                r'%': ' percent ',
                r'bps': ' basis points ',
                r'EPS': ' earnings per share ',
                r'P/E': ' price to earnings ratio ',
                r'ROI': ' return on investment ',
                r'YoY': ' year over year ',
                r'QoQ': ' quarter over quarter '
            }
            
            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error normalizing financial terms: {str(e)}")
            return text
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key financial phrases from text."""
        try:
            key_phrases = []
            
            # Financial indicators
            financial_patterns = [
                r'\$[\d,\.]+',  # Stock prices
                r'[\d,\.]+%',  # Percentages
                r'[\d,\.]+\s*(?:million|billion|trillion)',  # Large numbers
                r'(?:bullish|bearish|neutral|positive|negative)',
                r'(?:buy|sell|hold|upgrade|downgrade)',
                r'(?:resistance|support|breakout|correction)',
                r'(?:earnings|revenue|profit|loss|margin)',
                r'(?:dividend|yield|growth|decline)'
            ]
            
            for pattern in financial_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                key_phrases.extend(matches)
            
            # Remove duplicates and limit to top 10
            return list(set(key_phrases))[:10]
            
        except Exception as e:
            self.logger.error(f"Error extracting key phrases: {str(e)}")
            return []
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from financial text."""
        try:
            entities = []
            
            # Company names (simple pattern)
            company_pattern = r'\b[A-Z][a-z]+(?:\.| Inc\.| Corp\.| Ltd\.| LLC| Group| Holdings)\b'
            companies = re.findall(company_pattern, text)
            for company in companies:
                entities.append({
                    "type": "company",
                    "text": company,
                    "confidence": 0.8
                })
            
            # Financial metrics
            metric_pattern = r'\$?[\d,\.]+\s*(?:million|billion|trillion|MM|BB|TTT)'
            metrics = re.findall(metric_pattern, text)
            for metric in metrics:
                entities.append({
                    "type": "financial_metric",
                    "text": metric,
                    "confidence": 0.9
                })
            
            # People (CEOs, analysts)
            person_pattern = r'\b(?:CEO|CFO|President|Vice President|Analyst|Trader)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*'
            people = re.findall(person_pattern, text)
            for person in people:
                entities.append({
                    "type": "person",
                    "text": person,
                    "confidence": 0.7
                })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {str(e)}")
            return []
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from financial text."""
        try:
            topics = []
            
            # Financial topic keywords
            topic_keywords = {
                "earnings": ["earnings", "profit", "loss", "revenue", "sales", "income"],
                "mergers": ["merger", "acquisition", "takeover", "buyout", "M&A"],
                "regulatory": ["SEC", "regulation", "compliance", "filing", "investigation"],
                "market": ["market", "index", "sector", "industry", "trend"],
                "technology": ["AI", "blockchain", "fintech", "cloud", "software", "digital"],
                "energy": ["oil", "gas", "energy", "renewable", "solar", "wind"],
                "healthcare": ["healthcare", "pharma", "biotech", "medical", "drug", "FDA"]
            }
            
            text_lower = text.lower()
            
            for topic, keywords in topic_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        topics.append(topic)
                        break
            
            return list(set(topics))[:5]  # Limit to top 5 topics
            
        except Exception as e:
            self.logger.error(f"Error extracting topics: {str(e)}")
            return []
    
    async def _combine_source_results(self, symbol: str, source_results: List[Dict[str, Any]]) -> SentimentAnalysisResult:
        """Combine results from multiple sources with weighted averaging."""
        try:
            if not source_results:
                return SentimentAnalysisResult(
                    symbol=symbol,
                    overall_sentiment=0.0,
                    confidence=0.0,
                    sentiment_breakdown={"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                    source_breakdown={},
                    key_phrases=[],
                    entities=[],
                    topics=[],
                    timestamp=datetime.utcnow(),
                    model_version=self.model_name
                )
            
            # Calculate weighted sentiment
            total_weight = sum(result.get("weight", 1.0) for result in source_results)
            if total_weight == 0:
                total_weight = 1.0
            
            weighted_sentiment = 0.0
            source_breakdown = {}
            all_key_phrases = []
            all_entities = []
            all_topics = []
            
            # Weight by source reliability
            source_weights = {
                "analyst_report": 1.0,  # Highest weight
                "news": 0.8,  # High weight
                "social_media": 0.5,  # Medium weight
                "other": 0.3  # Lower weight
            }
            
            for result in source_results:
                source_type = result.get("source_type", "other")
                weight = result.get("weight", 1.0) * source_weights.get(source_type, 0.5)
                sentiment_score = result.get("sentiment_score", 0.0)
                confidence = result.get("confidence", 0.0)
                
                weighted_sentiment += sentiment_score * weight
                
                # Update source breakdown
                if source_type not in source_breakdown:
                    source_breakdown[source_type] = {
                        "sentiment": sentiment_score,
                        "confidence": confidence,
                        "weight": weight
                    }
                
                # Collect all items
                all_key_phrases.extend(result.get("key_phrases", []))
                all_entities.extend(result.get("entities", []))
                all_topics.extend(result.get("topics", []))
            
            # Normalize weighted sentiment
            overall_sentiment = weighted_sentiment / total_weight if total_weight > 0 else 0.0
            
            # Calculate overall confidence
            overall_confidence = np.mean([result.get("confidence", 0.0) for result in source_results])
            
            # Calculate sentiment breakdown
            positive_sources = [r for r in source_results if r.get("sentiment_score", 0) > 0.1]
            negative_sources = [r for r in source_results if r.get("sentiment_score", 0) < -0.1]
            neutral_sources = [r for r in source_results if -0.1 <= r.get("sentiment_score", 0) <= 0.1]
            
            sentiment_breakdown = {
                "positive": len(positive_sources) / len(source_results),
                "negative": len(negative_sources) / len(source_results),
                "neutral": len(neutral_sources) / len(source_results)
            }
            
            # Remove duplicates and limit results
            all_key_phrases = list(set(all_key_phrases))[:20]
            all_entities = all_entities[:15]  # Limit entities
            all_topics = list(set(all_topics))[:10]  # Limit topics
            
            return SentimentAnalysisResult(
                symbol=symbol,
                overall_sentiment=overall_sentiment,
                confidence=overall_confidence,
                sentiment_breakdown=sentiment_breakdown,
                source_breakdown=source_breakdown,
                key_phrases=all_key_phrases,
                entities=all_entities,
                topics=all_topics,
                timestamp=datetime.utcnow(),
                model_version=self.model_name
            )
            
        except Exception as e:
            self.logger.error(f"Error combining source results: {str(e)}")
            return SentimentAnalysisResult(
                symbol=symbol,
                overall_sentiment=0.0,
                confidence=0.0,
                sentiment_breakdown={"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                source_breakdown={},
                key_phrases=[],
                entities=[],
                topics=[],
                timestamp=datetime.utcnow(),
                model_version=self.model_name
            )
    
    async def batch_analyze(self, symbols: List[str], sources: Dict[str, List[SentimentSource]]) -> Dict[str, SentimentAnalysisResult]:
        """Batch analyze sentiment for multiple symbols."""
        try:
            results = {}
            
            # Create tasks for parallel processing
            tasks = []
            for symbol in symbols:
                symbol_sources = sources.get(symbol, [])
                if symbol_sources:
                    task = asyncio.create_task(self.analyze_sentiment(symbol, symbol_sources))
                    tasks.append(task)
            
            # Wait for all tasks to complete
            if tasks:
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(task_results):
                    if isinstance(result, SentimentAnalysisResult):
                        results[symbols[i]] = result
                    else:
                        self.logger.error(f"Error analyzing sentiment for {symbols[i]}: {result}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch sentiment analysis: {str(e)}")
            return {}
    
    async def get_sentiment_trend(self, symbol: str, hours: int = 24) -> Optional[Dict[str, Any]]:
        """Get sentiment trend for a symbol over time."""
        try:
            # Get historical sentiment data
            trend_key = f"sentiment_trend_{symbol}_{hours}h"
            cached_trend = await self.cache_manager.get(trend_key)
            
            if cached_trend:
                return cached_trend
            
            # Calculate trend from recent analyses
            # This would typically query a time-series database
            # For now, return mock trend data
            trend_data = {
                "symbol": symbol,
                "period_hours": hours,
                "trend_direction": "stable",  # increasing, decreasing, stable
                "trend_strength": 0.1,  # 0 to 1 scale
                "volatility": 0.2,  # Sentiment volatility
                "data_points": [],  # Would contain historical sentiment scores
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache the trend
            await self.cache_manager.set(
                trend_key,
                trend_data,
                ttl=3600  # 1 hour
            )
            
            return trend_data
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment trend for {symbol}: {str(e)}")
            return None
    
    async def compare_sentiment_models(self, symbol: str, text: str) -> Dict[str, Any]:
        """Compare BERT sentiment with VADER for validation."""
        try:
            # Analyze with BERT
            bert_result = await self._analyze_source(SentimentSource(
                source_type="comparison",
                content=text,
                weight=1.0,
                timestamp=datetime.utcnow()
            ))
            
            # Analyze with VADER (existing service)
            from .sentiment_service import SentimentService
            vader_service = SentimentService(self.cache_manager)
            vader_result = await vader_service.analyze_text_sentiment(text)
            
            comparison = {
                "symbol": symbol,
                "text": text,
                "bert_sentiment": bert_result.get("sentiment_score", 0.0) if bert_result else 0.0,
                "bert_confidence": bert_result.get("confidence", 0.0) if bert_result else 0.0,
                "vader_sentiment": vader_result.get("compound", 0.0) if vader_result else 0.0,
                "difference": abs((bert_result.get("sentiment_score", 0.0) if bert_result else 0.0) - (vader_result.get("compound", 0.0) if vader_result else 0.0)),
                "agreement": "high" if abs((bert_result.get("sentiment_score", 0.0) if bert_result else 0.0) - (vader_result.get("compound", 0.0) if vader_result else 0.0)) < 0.2 else "medium" if abs((bert_result.get("sentiment_score", 0.0) if bert_result else 0.0) - (vader_result.get("compound", 0.0) if vader_result else 0.0)) < 0.5 else "low",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing sentiment models: {str(e)}")
            return {}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded BERT model."""
        try:
            return {
                "model_name": self.model_name,
                "model_loaded": self.model is not None,
                "tokenizer_loaded": self.tokenizer is not None,
                "pipeline_loaded": self.sentiment_pipeline is not None,
                "financial_keywords_count": len(self.financial_keywords["positive"]) + len(self.financial_keywords["negative"]),
                "cache_size": len(self.analysis_cache),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting model info: {str(e)}")
            return {}
    
    async def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded BERT model."""
        try:
            return {
                "model_name": self.model_name,
                "model_loaded": self.model is not None,
                "tokenizer_loaded": self.tokenizer is not None,
                "pipeline_loaded": self.sentiment_pipeline is not None,
                "financial_keywords_count": len(self.financial_keywords["positive"]) + len(self.financial_keywords["negative"]),
                "cache_size": len(self.analysis_cache),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting model stats: {str(e)}")
            return {}
    
    async def analyze_sentiment_trend(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment trend from historical data."""
        try:
            if not historical_data:
                return {"error": "No historical data provided"}
            
            # Extract sentiment scores
            sentiments = []
            for item in historical_data:
                if isinstance(item, dict) and "sentiment" in item:
                    sentiments.append(item["sentiment"])
            
            if not sentiments:
                return {"error": "No sentiment data found"}
            
            # Calculate trend
            if len(sentiments) < 2:
                return {"error": "Insufficient data for trend analysis"}
            
            # Simple trend calculation
            recent_sentiment = sentiments[-1]
            older_sentiment = sentiments[0]
            
            if recent_sentiment > older_sentiment + 0.1:
                trend = "increasing"
            elif recent_sentiment < older_sentiment - 0.1:
                trend = "decreasing"
            else:
                trend = "stable"
            
            # Calculate strength
            strength = abs(recent_sentiment - older_sentiment)
            
            # Calculate volatility
            if len(sentiments) > 1:
                mean_sentiment = sum(sentiments) / len(sentiments)
                variance = sum((s - mean_sentiment) ** 2 for s in sentiments) / len(sentiments)
                volatility = variance ** 0.5
            else:
                volatility = 0.0
            
            return {
                "success": True,
                "trend": trend,
                "trend_strength": strength,
                "volatility": volatility,
                "data_points": len(sentiments),
                "sentiment_range": [min(sentiments), max(sentiments)]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment trend: {str(e)}")
            return {"error": str(e)}
    
    async def analyze_financial_entities(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze financial entities in text."""
        try:
            # Preprocess text
            processed_text = text.lower()
            
            # Simple financial entity extraction
            entities = []
            
            # Stock symbols
            import re
            symbols = re.findall(r'\$[A-Z]+', text)
            for symbol in symbols:
                entities.append({
                    "type": "stock_symbol",
                    "value": symbol,
                    "confidence": 0.9
                })
            
            # Monetary amounts
            amounts = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', text)
            for amount in amounts:
                entities.append({
                    "type": "monetary_amount",
                    "value": amount,
                    "confidence": 0.8
                })
            
            # Percentages
            percentages = re.findall(r'\d+\.?\d*%', text)
            for percentage in percentages:
                entities.append({
                    "type": "percentage",
                    "value": percentage,
                    "confidence": 0.8
                })
            
            # Financial keywords
            financial_keywords = [
                "earnings", "revenue", "profit", "loss", "growth", "decline",
                "bullish", "bearish", "volatility", "dividend", "yield",
                "market", "stock", "share", "price", "target", "guidance"
            ]
            
            for keyword in financial_keywords:
                if keyword in processed_text:
                    entities.append({
                        "type": "financial_keyword",
                        "value": keyword,
                        "confidence": 0.7
                    })
            
            # Analyze sentiment for context
            sentiment_source = SentimentSource(
                source_type="financial_analysis",
                content=text,
                weight=1.0,
                timestamp=datetime.utcnow()
            )
            sentiment_result = await self.analyze_sentiment("ANALYSIS", [sentiment_source])
            
            return {
                "success": True,
                "entities": entities,
                "entity_count": len(entities),
                "sentiment": {
                    "score": sentiment_result.overall_sentiment,
                    "label": "positive" if sentiment_result.overall_sentiment > 0.1 else "negative" if sentiment_result.overall_sentiment < -0.1 else "neutral",
                    "confidence": sentiment_result.confidence
                },
                "text": text,
                "processed_text": processed_text
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing financial entities: {str(e)}")
            return {"error": str(e)}
    
    async def stream_real_time_sentiment(self, symbol: str, sources: List[SentimentSource]):
        """Stream real-time sentiment analysis results."""
        try:
            # Analyze sentiment
            result = await self.analyze_sentiment(symbol, sources)
            
            # Yield the result
            yield {
                "symbol": symbol,
                "timestamp": result.timestamp.isoformat(),
                "overall_sentiment": result.overall_sentiment,
                "confidence": result.confidence,
                "sentiment_breakdown": result.sentiment_breakdown,
                "source_breakdown": result.source_breakdown,
                "key_phrases": result.key_phrases,
                "entities": result.entities,
                "topics": result.topics,
                "model_version": result.model_version
            }
            
        except Exception as e:
            self.logger.error(f"Error streaming real-time sentiment for {symbol}: {str(e)}")
            yield {
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }