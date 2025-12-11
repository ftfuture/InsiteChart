"""Sentiment analysis using VADER and BERT ensemble."""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import numpy as np

# NLP imports
from nltk.sentiment import SentimentIntensityAnalyzer
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment using VADER and BERT ensemble."""

    def __init__(self):
        """Initialize sentiment analyzers."""
        self.vader_analyzer = SentimentIntensityAnalyzer()

        # Initialize BERT model and tokenizer
        try:
            self.bert_tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
            self.bert_model = AutoModelForSequenceClassification.from_pretrained(
                "distilbert-base-uncased-finetuned-sst-2-english"
            )
            self.bert_available = True
        except Exception as e:
            logger.warning(f"BERT model not available: {e}. Using VADER only.")
            self.bert_available = False

        # VADER weights for ensemble (can be tuned)
        self.vader_weight = 0.4
        self.bert_weight = 0.6

    def analyze_vader(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using VADER.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores (negative, neutral, positive, compound)
        """
        scores = self.vader_analyzer.polarity_scores(text)
        return {
            "positive": scores["pos"],
            "negative": scores["neg"],
            "neutral": scores["neu"],
            "compound": scores["compound"]
        }

    def analyze_bert(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using BERT.

        Args:
            text: Text to analyze (will be truncated to 512 tokens)

        Returns:
            Dictionary with sentiment scores
        """
        if not self.bert_available:
            return {}

        try:
            # Tokenize and truncate to 512 tokens
            inputs = self.bert_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )

            # Get model predictions
            with torch.no_grad():
                outputs = self.bert_model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)

            # Extract scores (label 0 = negative, label 1 = positive)
            neg_score = probabilities[0][0].item()
            pos_score = probabilities[0][1].item()

            return {
                "positive": pos_score,
                "negative": neg_score,
                "neutral": 1.0 - (pos_score + neg_score),
                "compound": pos_score - neg_score  # Approximate compound score
            }
        except Exception as e:
            logger.error(f"BERT analysis failed: {e}")
            return {}

    def analyze_ensemble(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using VADER and BERT ensemble.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with ensemble sentiment scores
        """
        # Get VADER scores
        vader_scores = self.analyze_vader(text)

        # Get BERT scores if available
        if self.bert_available:
            bert_scores = self.analyze_bert(text)
            if bert_scores:
                # Weighted average
                ensemble_scores = {
                    "positive": (
                        vader_scores["positive"] * self.vader_weight +
                        bert_scores["positive"] * self.bert_weight
                    ),
                    "negative": (
                        vader_scores["negative"] * self.vader_weight +
                        bert_scores["negative"] * self.bert_weight
                    ),
                    "neutral": (
                        vader_scores["neutral"] * self.vader_weight +
                        bert_scores["neutral"] * self.bert_weight
                    ),
                    "compound": (
                        vader_scores["compound"] * self.vader_weight +
                        bert_scores["compound"] * self.bert_weight
                    )
                }
                return ensemble_scores

        # Return VADER scores if BERT not available
        return vader_scores

    def analyze(
        self,
        text: str,
        model: str = "ensemble",
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze
            model: Model to use ('vader', 'bert', or 'ensemble')
            symbol: Stock symbol (optional, for logging)

        Returns:
            Dictionary with sentiment analysis results
        """
        # Validate input
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")

        if len(text) > 5000:
            logger.warning(f"Text truncated from {len(text)} to 5000 characters")
            text = text[:5000]

        # Select analysis method
        if model == "vader":
            scores = self.analyze_vader(text)
        elif model == "bert" and self.bert_available:
            scores = self.analyze_bert(text)
            if not scores:
                scores = self.analyze_vader(text)
        else:  # ensemble
            scores = self.analyze_ensemble(text)

        # Calculate confidence score
        confidence = self._calculate_confidence(scores)

        # Determine sentiment label
        sentiment_label = self._get_sentiment_label(scores["compound"])

        return {
            "positive": round(scores["positive"], 4),
            "negative": round(scores["negative"], 4),
            "neutral": round(scores["neutral"], 4),
            "compound": round(scores["compound"], 4),
            "sentiment": sentiment_label,
            "confidence": round(confidence, 4),
            "model": model if model in ["vader", "bert", "ensemble"] else "ensemble",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate confidence score based on sentiment distribution.

        High confidence when sentiment is clearly positive/negative,
        low confidence when scores are balanced (ambiguous).
        """
        max_score = max(scores["positive"], scores["negative"], scores["neutral"])
        return max_score  # Simple confidence: dominant sentiment score

    def _get_sentiment_label(self, compound_score: float) -> str:
        """Get sentiment label from compound score.

        Args:
            compound_score: Compound sentiment score (-1 to 1)

        Returns:
            Sentiment label: positive, negative, or neutral
        """
        if compound_score >= 0.05:
            return "positive"
        elif compound_score <= -0.05:
            return "negative"
        else:
            return "neutral"

    def batch_analyze(
        self,
        texts: list[str],
        model: str = "ensemble"
    ) -> list[Dict[str, Any]]:
        """Analyze multiple texts efficiently.

        Args:
            texts: List of texts to analyze
            model: Model to use

        Returns:
            List of sentiment analysis results
        """
        results = []
        for text in texts:
            try:
                result = self.analyze(text, model)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing text: {e}")
                results.append({
                    "error": str(e),
                    "text": text[:100]
                })
        return results
