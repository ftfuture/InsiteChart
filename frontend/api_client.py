"""
API Client for InsiteChart Frontend.

This module provides a client interface to communicate with the InsiteChart backend API.
"""

import requests
import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd


class InsiteChartAPIClient:
    """Client for interacting with InsiteChart API."""
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {"success": True, "data": {}}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            st.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            st.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        return self._make_request("GET", "/health")
    
    def get_stock_data(self, symbol: str, include_sentiment: bool = True) -> Dict[str, Any]:
        """Get comprehensive stock data."""
        data = {
            "symbol": symbol.upper(),
            "include_sentiment": include_sentiment
        }
        return self._make_request("POST", "/stock", json=data)
    
    def search_stocks(self, query: str, filters: Optional[Dict] = None, limit: int = 10) -> Dict[str, Any]:
        """Search for stocks."""
        data = {
            "query": query,
            "filters": filters or {},
            "limit": limit
        }
        return self._make_request("POST", "/search", json=data)
    
    def get_trending_stocks(self, limit: int = 10, timeframe: str = "24h") -> Dict[str, Any]:
        """Get trending stocks."""
        params = {
            "limit": limit,
            "timeframe": timeframe
        }
        return self._make_request("GET", "/trending", params=params)
    
    def get_market_indices(self) -> Dict[str, Any]:
        """Get major market indices."""
        return self._make_request("GET", "/market/indices")
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """Get overall market sentiment."""
        return self._make_request("GET", "/market/sentiment")
    
    def get_market_statistics(self) -> Dict[str, Any]:
        """Get market-wide statistics."""
        return self._make_request("GET", "/market/statistics")
    
    def compare_stocks(self, symbols: List[str], period: str = "1mo", include_sentiment: bool = True) -> Dict[str, Any]:
        """Compare multiple stocks."""
        data = {
            "symbols": [s.upper() for s in symbols],
            "period": period,
            "include_sentiment": include_sentiment
        }
        return self._make_request("POST", "/compare", json=data)
    
    def get_detailed_sentiment(self, symbol: str, sources: Optional[List[str]] = None, 
                             timeframe: str = "24h", include_mentions: bool = False) -> Dict[str, Any]:
        """Get detailed sentiment analysis for a stock."""
        data = {
            "symbol": symbol.upper(),
            "sources": sources,
            "timeframe": timeframe,
            "include_mentions": include_mentions
        }
        return self._make_request("POST", "/sentiment", json=data)
    
    def get_correlation_analysis(self, symbol1: str, symbol2: str, period: str = "1mo", 
                               include_sentiment: bool = True) -> Dict[str, Any]:
        """Get correlation analysis between two stocks."""
        data = {
            "symbol1": symbol1.upper(),
            "symbol2": symbol2.upper(),
            "period": period,
            "include_sentiment": include_sentiment
        }
        return self._make_request("POST", "/correlation", json=data)
    
    def get_user_watchlist(self, user_id: str, include_sentiment: bool = True, 
                         include_alerts: bool = True) -> Dict[str, Any]:
        """Get user's watchlist."""
        params = {
            "include_sentiment": include_sentiment,
            "include_alerts": include_alerts
        }
        return self._make_request("GET", f"/watchlist/{user_id}", params=params)
    
    def add_to_watchlist(self, user_id: str, symbol: str, category: Optional[str] = None,
                        alert_threshold: Optional[float] = None, sentiment_alert: bool = False) -> Dict[str, Any]:
        """Add stock to user's watchlist."""
        data = {
            "user_id": user_id,
            "symbol": symbol.upper(),
            "category": category,
            "alert_threshold": alert_threshold,
            "sentiment_alert": sentiment_alert
        }
        return self._make_request("POST", "/watchlist", json=data)
    
    def get_market_insights(self, timeframe: str = "24h", category: Optional[str] = None) -> Dict[str, Any]:
        """Get market insights and analytics."""
        params = {
            "timeframe": timeframe
        }
        if category:
            params["category"] = category
        return self._make_request("GET", "/insights", params=params)
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """Get data quality report."""
        return self._make_request("GET", "/quality")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return self._make_request("GET", "/cache/stats")
    
    def clear_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Clear cache entries."""
        params = {}
        if pattern:
            params["pattern"] = pattern
        return self._make_request("POST", "/cache/clear", params=params)


# Global API client instance
@st.cache_resource
def get_api_client() -> InsiteChartAPIClient:
    """Get cached API client instance."""
    # Try to get API URL from environment or use default
    api_url = st.secrets.get("API_BASE_URL", "http://localhost:8000/api/v1")
    return InsiteChartAPIClient(api_url)


# Utility functions for Streamlit integration
def format_api_response(response: Dict[str, Any]) -> tuple[bool, Any]:
    """Format API response for Streamlit usage."""
    if response.get("success", False):
        return True, response.get("data", {})
    else:
        error_msg = response.get("error", "Unknown error occurred")
        st.error(f"API Error: {error_msg}")
        return False, None


def display_sentiment_score(score: float, show_label: bool = True) -> str:
    """Display sentiment score with appropriate color and label."""
    if score is None:
        return "N/A"
    
    # Determine sentiment category
    if score > 0.2:
        sentiment = "Positive"
        color = "🟢"
    elif score < -0.2:
        sentiment = "Negative"
        color = "🔴"
    else:
        sentiment = "Neutral"
        color = "🟡"
    
    if show_label:
        return f"{color} {sentiment} ({score:.2f})"
    else:
        return f"{color} {score:.2f}"


def create_sentiment_gauge(score: float) -> Dict[str, Any]:
    """Create a gauge chart for sentiment score."""
    if score is None:
        score = 0
    
    # Determine color based on sentiment
    if score > 0.2:
        color = "#26a69a"  # Green
    elif score < -0.2:
        color = "#ef5350"  # Red
    else:
        color = "#ffa726"  # Orange
    
    return {
        "value": score,
        "delta": {"reference": 0},
        "domain": {"x": [0, 1], "y": [0, 1]},
        "title": {"text": "Sentiment Score"},
        "type": "indicator",
        "mode": "gauge+number+delta",
        "gauge": {
            "axis": {"range": [-1, 1]},
            "bar": {"color": color},
            "steps": [
                {"range": [-1, -0.2], "color": "lightgray"},
                {"range": [-0.2, 0.2], "color": "lightyellow"},
                {"range": [0.2, 1], "color": "lightgreen"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 0
            }
        }
    }


def safe_get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError):
        return default


def convert_to_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert API response data to pandas DataFrame."""
    if not data:
        return pd.DataFrame()
    
    try:
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error converting data to DataFrame: {str(e)}")
        return pd.DataFrame()


def display_api_error(response: Dict[str, Any]) -> None:
    """Display API error message in Streamlit."""
    if not response.get("success", False):
        error_msg = response.get("error", "Unknown error occurred")
        st.error(f"API Error: {error_msg}")
        
        # Show additional error details if available
        if "details" in response:
            st.code(str(response["details"]))