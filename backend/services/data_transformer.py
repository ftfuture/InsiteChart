"""
Data transformation service for converting between different data models.

This service provides functionality to convert legacy models to the unified
data model and merge data from different sources.
"""

from typing import Dict, List, Optional, Any, Union
import logging
from datetime import datetime, timezone

from ..models.unified_models import (
    UnifiedStockData, SentimentPoint, MentionDetail, 
    StockType, SentimentSource, InvestmentStyle
)


class UnifiedDataTransformer:
    """Data transformation layer: converts legacy models to unified model."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def from_stock_result(self, stock_result: Dict[str, Any]) -> UnifiedStockData:
        """Convert StockResult dictionary to UnifiedStockData."""
        try:
            # Convert stock type string to enum
            stock_type_str = stock_result.get('stock_type', 'EQUITY')
            stock_type = StockType(stock_type_str.upper())
            
            return UnifiedStockData(
                symbol=stock_result['symbol'],
                company_name=stock_result['company_name'],
                stock_type=stock_type,
                exchange=stock_result.get('exchange', 'UNKNOWN'),
                sector=stock_result.get('sector'),
                industry=stock_result.get('industry'),
                description=stock_result.get('description'),
                website=stock_result.get('website'),
                current_price=stock_result.get('current_price'),
                previous_close=stock_result.get('previous_close'),
                day_change=stock_result.get('day_change'),
                day_change_pct=stock_result.get('day_change_pct'),
                volume=stock_result.get('volume'),
                avg_volume=stock_result.get('avg_volume'),
                day_high=stock_result.get('day_high'),
                day_low=stock_result.get('day_low'),
                market_cap=stock_result.get('market_cap'),
                pe_ratio=stock_result.get('pe_ratio'),
                dividend_yield=stock_result.get('dividend_yield'),
                beta=stock_result.get('beta'),
                eps=stock_result.get('eps'),
                fifty_two_week_high=stock_result.get('fifty_two_week_high'),
                fifty_two_week_low=stock_result.get('fifty_two_week_low'),
                relevance_score=stock_result.get('relevance_score', 0.0),
                search_count=stock_result.get('search_count', 0),
                data_sources=["yahoo_finance"]
            )
            
        except Exception as e:
            self.logger.error(f"Error transforming StockResult: {str(e)}")
            raise
    
    def from_stock_mention(self, stock_mention: Dict[str, Any]) -> UnifiedStockData:
        """Convert StockMention dictionary to UnifiedStockData."""
        try:
            # Convert sentiment score to -100 to +100 range
            sentiment_score = stock_mention.get('sentiment_score', 0.0)
            if isinstance(sentiment_score, (int, float)):
                # Assume VADER range (-1 to 1) and convert to -100 to +100
                if -1 <= sentiment_score <= 1:
                    sentiment_score = sentiment_score * 100
            
            # Convert source string to enum
            source_str = stock_mention.get('source', 'REDDIT')
            source = SentimentSource(source_str.upper())
            
            # Convert investment style string to enum
            investment_style_str = stock_mention.get('investment_style', 'VALUE_INVESTING')
            investment_style = InvestmentStyle(investment_style_str.upper())
            
            # Create mention detail
            mention_detail = MentionDetail(
                id=stock_mention.get('id', f"{stock_mention['symbol']}_{stock_mention.get('timestamp', datetime.now().isoformat())}"),
                text=stock_mention.get('text', ''),
                author=stock_mention.get('author', 'unknown'),
                community=stock_mention.get('community', 'unknown'),
                upvotes=stock_mention.get('upvotes', 0),
                downvotes=stock_mention.get('downvotes', 0),
                timestamp=datetime.fromisoformat(stock_mention.get('timestamp', datetime.now().isoformat())),
                investment_style=investment_style,
                sentiment_score=sentiment_score,
                confidence=stock_mention.get('confidence', 0.8)
            )
            
            # Create sentiment point
            sentiment_point = SentimentPoint(
                timestamp=mention_detail.timestamp,
                sentiment_score=sentiment_score,
                mention_count=1,
                source=source,
                confidence=mention_detail.confidence
            )
            
            return UnifiedStockData(
                symbol=stock_mention['symbol'],
                company_name=stock_mention.get('company_name', ''),  # May not be available
                stock_type=StockType.EQUITY,  # Default assumption
                exchange="UNKNOWN",  # May not be available
                overall_sentiment=sentiment_score,
                sentiment_sources={source: sentiment_score},
                mention_count_24h=1,
                mention_details=[mention_detail],
                sentiment_history=[sentiment_point],
                community_breakdown={mention_detail.community: 1},
                investment_style_distribution={investment_style: 1.0},
                data_sources=[source.value.lower()]
            )
            
        except Exception as e:
            self.logger.error(f"Error transforming StockMention: {str(e)}")
            raise
    
    def merge_stock_data(self, base_data: UnifiedStockData, 
                        update_data: UnifiedStockData) -> UnifiedStockData:
        """Merge two UnifiedStockData objects."""
        try:
            # Basic info - use base_data as primary
            merged = UnifiedStockData(
                symbol=base_data.symbol,
                company_name=base_data.company_name,
                stock_type=base_data.stock_type,
                exchange=base_data.exchange,
                sector=base_data.sector,
                industry=base_data.industry,
                description=base_data.description,
                website=base_data.website,
                # Price data - prefer more recent
                current_price=update_data.current_price or base_data.current_price,
                previous_close=update_data.previous_close or base_data.previous_close,
                day_change=update_data.day_change or base_data.day_change,
                day_change_pct=update_data.day_change_pct or base_data.day_change_pct,
                volume=update_data.volume or base_data.volume,
                avg_volume=update_data.avg_volume or base_data.avg_volume,
                day_high=update_data.day_high or base_data.day_high,
                day_low=update_data.day_low or base_data.day_low,
                market_cap=update_data.market_cap or base_data.market_cap,
                # Financial metrics - prefer update_data
                pe_ratio=update_data.pe_ratio or base_data.pe_ratio,
                dividend_yield=update_data.dividend_yield or base_data.dividend_yield,
                beta=update_data.beta or base_data.beta,
                eps=update_data.eps or base_data.eps,
                fifty_two_week_high=update_data.fifty_two_week_high or base_data.fifty_two_week_high,
                fifty_two_week_low=update_data.fifty_two_week_low or base_data.fifty_two_week_low,
                # Sentiment data - merge
                overall_sentiment=update_data.overall_sentiment or base_data.overall_sentiment,
                sentiment_sources=self._merge_sentiment_sources(
                    base_data.sentiment_sources, update_data.sentiment_sources
                ),
                mention_count_24h=self._merge_counts(
                    base_data.mention_count_24h, update_data.mention_count_24h
                ),
                mention_count_7d=self._merge_counts(
                    base_data.mention_count_7d, update_data.mention_count_7d
                ),
                mention_count_1h=self._merge_counts(
                    base_data.mention_count_1h, update_data.mention_count_1h
                ),
                positive_mentions=self._merge_counts(
                    base_data.positive_mentions, update_data.positive_mentions
                ),
                negative_mentions=self._merge_counts(
                    base_data.negative_mentions, update_data.negative_mentions
                ),
                neutral_mentions=self._merge_counts(
                    base_data.neutral_mentions, update_data.neutral_mentions
                ),
                trending_status=update_data.trending_status or base_data.trending_status,
                trend_score=update_data.trend_score or base_data.trend_score,
                trend_start_time=update_data.trend_start_time or base_data.trend_start_time,
                trend_duration_hours=update_data.trend_duration_hours or base_data.trend_duration_hours,
                # Detailed sentiment - merge lists
                sentiment_history=self._merge_sentiment_history(
                    base_data.sentiment_history, update_data.sentiment_history
                ),
                mention_details=self._merge_mention_details(
                    base_data.mention_details, update_data.mention_details
                ),
                community_breakdown=self._merge_community_breakdown(
                    base_data.community_breakdown, update_data.community_breakdown
                ),
                investment_style_distribution=self._merge_investment_styles(
                    base_data.investment_style_distribution, 
                    update_data.investment_style_distribution
                ),
                # Search data - use higher values
                relevance_score=max(base_data.relevance_score, update_data.relevance_score),
                search_count=base_data.search_count + update_data.search_count,
                view_count=base_data.view_count + update_data.view_count,
                last_searched=max(
                    base_data.last_searched or datetime.min,
                    update_data.last_searched or datetime.min
                ),
                last_viewed=max(
                    base_data.last_viewed or datetime.min,
                    update_data.last_viewed or datetime.min
                ),
                # Time series data - merge
                timestamps=self._merge_time_series(base_data.timestamps, update_data.timestamps),
                prices=self._merge_numeric_series(base_data.prices, update_data.prices),
                volumes=self._merge_numeric_series(base_data.volumes, update_data.volumes),
                mentions=self._merge_numeric_series(base_data.mentions, update_data.mentions),
                # Metadata
                last_updated=max(base_data.last_updated, update_data.last_updated),
                data_quality_score=min(base_data.data_quality_score, update_data.data_quality_score),
                data_sources=list(set(base_data.data_sources + update_data.data_sources)),
                api_errors=base_data.api_errors + update_data.api_errors
            )
            
            return merged
            
        except Exception as e:
            self.logger.error(f"Error merging stock data: {str(e)}")
            raise
    
    def _merge_sentiment_sources(self, base: Dict[SentimentSource, float], 
                               update: Dict[SentimentSource, float]) -> Dict[SentimentSource, float]:
        """Merge sentiment sources dictionaries."""
        merged = {}
        
        # Add base sources
        for source, score in base.items():
            merged[source] = score
        
        # Add/update with update sources
        for source, score in update.items():
            merged[source] = score
        
        return merged
    
    def _merge_counts(self, base: Optional[int], update: Optional[int]) -> Optional[int]:
        """Merge count values."""
        if base is None and update is None:
            return None
        if base is None:
            return update
        if update is None:
            return base
        return base + update
    
    def _merge_sentiment_history(self, base: List[SentimentPoint], 
                               update: List[SentimentPoint]) -> List[SentimentPoint]:
        """Merge sentiment history lists."""
        merged = base + update
        # Sort by timestamp
        merged.sort(key=lambda x: x.timestamp)
        return merged
    
    def _merge_mention_details(self, base: List[MentionDetail], 
                             update: List[MentionDetail]) -> List[MentionDetail]:
        """Merge mention details lists."""
        merged = base + update
        # Sort by timestamp
        merged.sort(key=lambda x: x.timestamp)
        return merged
    
    def _merge_community_breakdown(self, base: Dict[str, int], 
                                 update: Dict[str, int]) -> Dict[str, int]:
        """Merge community breakdown dictionaries."""
        merged = {}
        
        # Add base communities
        for community, count in base.items():
            merged[community] = count
        
        # Add/update with update communities
        for community, count in update.items():
            merged[community] = merged.get(community, 0) + count
        
        return merged
    
    def _merge_investment_styles(self, base: Dict[InvestmentStyle, float], 
                                update: Dict[InvestmentStyle, float]) -> Dict[InvestmentStyle, float]:
        """Merge investment style distributions."""
        merged = {}
        
        # Add base styles
        for style, distribution in base.items():
            merged[style] = distribution
        
        # Add/update with update styles
        for style, distribution in update.items():
            merged[style] = (merged.get(style, 0) + distribution) / 2
        
        return merged
    
    def _merge_time_series(self, base: List[datetime], update: List[datetime]) -> List[datetime]:
        """Merge time series timestamps."""
        merged = list(set(base + update))
        merged.sort()
        return merged
    
    def _merge_numeric_series(self, base: List[Union[int, float]], 
                            update: List[Union[int, float]]) -> List[Union[int, float]]:
        """Merge numeric series data."""
        # For simplicity, concatenate the series
        # In a real implementation, you might want more sophisticated merging
        return base + update
    
    def normalize_sentiment_score(self, score: float, source_range: str = "vader") -> float:
        """Normalize sentiment score to -100 to +100 range."""
        if source_range.lower() == "vader":
            # VADER range: -1 to +1
            return score * 100
        elif source_range.lower() == "textblob":
            # TextBlob range: -1 to +1
            return score * 100
        elif source_range.lower() == "custom_1":
            # Custom range 1: -5 to +5
            return score * 20
        elif source_range.lower() == "custom_2":
            # Custom range 2: 0 to 1
            return (score - 0.5) * 200
        else:
            # Assume already in -100 to +100 range
            return score