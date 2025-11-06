"""
InsiteChart - Enhanced Streamlit Application

This is the enhanced version of InsiteChart with backend API integration
and comprehensive sentiment analysis features.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional, Any

# Import our custom modules
try:
    from frontend.api_client import get_api_client, format_api_response, display_sentiment_score
    from frontend.utils import (
        format_currency, format_number, format_large_number, format_percentage,
        create_metric_card, create_sentiment_indicator, create_stock_chart,
        create_comparison_chart, display_stock_summary, create_data_table,
        create_download_button, display_error_message, display_loading_message
    )
    from frontend.notification_client import (
        init_notification_system, render_notification_panel,
        subscribe_to_symbol_notifications
    )
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    st.warning("API modules not available. Running in legacy mode.")


# Page configuration
st.set_page_config(
    page_title="InsiteChart - Financial Analysis & Sentiment",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #1f77b4;
        margin: 10px 0;
    }
    .sentiment-positive {
        background-color: #e8f5e8;
        border-left-color: #26a69a;
    }
    .sentiment-negative {
        background-color: #ffeaea;
        border-left-color: #ef5350;
    }
    .sentiment-neutral {
        background-color: #fff8e1;
        border-left-color: #ffa726;
    }
    .trending-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    if 'current_ticker' not in st.session_state:
        st.session_state.current_ticker = 'AAPL'
    
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    
    if 'selected_period' not in st.session_state:
        st.session_state.selected_period = '1Y'
    
    if 'chart_type' not in st.session_state:
        st.session_state.chart_type = 'Candlestick'
    
    if 'show_sentiment' not in st.session_state:
        st.session_state.show_sentiment = True
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = 'demo_user'


# Legacy functions for fallback mode
def legacy_search_stocks(query: str, max_results: int = 10) -> List[Dict]:
    """Legacy stock search using Yahoo Finance API."""
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        params = {
            "q": query,
            "quotes_count": max_results,
            "country": "United States"
        }
        
        response = requests.get(
            url=url,
            params=params,
            headers={'User-Agent': user_agent},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for quote in data.get('quotes', []):
                result = {
                    'symbol': quote.get('symbol', 'N/A'),
                    'name': quote.get('shortname') or quote.get('longname', 'N/A'),
                    'type': quote.get('quoteType', 'N/A'),
                    'exchange': quote.get('exchange', 'N/A'),
                    'sector': quote.get('sector', 'N/A'),
                    'industry': quote.get('industry', 'N/A')
                }
                results.append(result)
            
            return results
        else:
            return []
    except Exception as e:
        st.error(f"검색 오류: {str(e)}")
        return []


def legacy_get_stock_data(ticker: str) -> Dict:
    """Legacy stock data using yfinance."""
    try:
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        return {
            'symbol': ticker,
            'company_name': info.get('longName', ticker),
            'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
            'previous_close': info.get('previousClose'),
            'open': info.get('open'),
            'day_high': info.get('dayHigh'),
            'day_low': info.get('dayLow'),
            'volume': info.get('volume'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'eps': info.get('trailingEps'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'overall_sentiment': None,
            'mention_count_24h': None,
            'trending_status': False
        }
    except Exception as e:
        st.error(f"데이터 로딩 오류: {str(e)}")
        return {}


# Main functions
def search_stocks(query: str, max_results: int = 10) -> List[Dict]:
    """Search stocks using API or fallback to legacy."""
    if API_AVAILABLE:
        api_client = get_api_client()
        success, data = format_api_response(api_client.search_stocks(query, limit=max_results))
        
        if success and 'results' in data:
            # Convert API response to expected format
            results = []
            for item in data['results']:
                results.append({
                    'symbol': item.get('symbol'),
                    'name': item.get('company_name'),
                    'type': item.get('stock_type'),
                    'exchange': item.get('exchange'),
                    'sector': item.get('sector'),
                    'industry': item.get('industry')
                })
            return results
    
    # Fallback to legacy mode
    return legacy_search_stocks(query, max_results)


def get_stock_data(symbol: str, include_sentiment: bool = True) -> Dict:
    """Get stock data using API or fallback to legacy."""
    if API_AVAILABLE:
        api_client = get_api_client()
        success, data = format_api_response(api_client.get_stock_data(symbol, include_sentiment))
        
        if success:
            return data
    
    # Fallback to legacy mode
    return legacy_get_stock_data(symbol)


def get_trending_stocks(limit: int = 10) -> List[Dict]:
    """Get trending stocks using API."""
    if API_AVAILABLE:
        api_client = get_api_client()
        success, data = format_api_response(api_client.get_trending_stocks(limit))
        
        if success:
            return data
    
    return []


def get_market_sentiment() -> Dict:
    """Get market sentiment using API."""
    if API_AVAILABLE:
        api_client = get_api_client()
        success, data = format_api_response(api_client.get_market_sentiment())
        
        if success:
            return data
    
    return {'overall_sentiment': 0, 'sentiment_distribution': {}}


# UI Components
def render_sidebar():
    """Render the sidebar with navigation and controls."""
    st.sidebar.markdown("# 📈 InsiteChart")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["📊 Dashboard", "🔍 Stock Analysis", "📈 Compare Stocks", 
         "💬 Sentiment Analysis", "🌊 Market Overview", "⚙️ Settings"]
    )
    
    st.sidebar.markdown("---")
    
    # Quick Actions
    st.sidebar.markdown("### ⚡ Quick Actions")
    
    # Add to watchlist
    new_ticker = st.sidebar.text_input("Add Symbol", placeholder="NVDA").upper()
    if st.sidebar.button("➕ Add to Watchlist"):
        if new_ticker and new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
            st.sidebar.success(f"Added {new_ticker} to watchlist")
            st.rerun()
    
    # Watchlist
    st.sidebar.markdown("### 🔖 Watchlist")
    for ticker in st.session_state.watchlist:
        if st.sidebar.button(f"📊 {ticker}", key=f"sidebar_{ticker}"):
            st.session_state.current_ticker = ticker
            st.rerun()
    
    # Remove from watchlist
    if st.session_state.watchlist:
        remove_ticker = st.sidebar.selectbox("Remove", st.session_state.watchlist)
        if st.sidebar.button("🗑️ Remove"):
            st.session_state.watchlist.remove(remove_ticker)
            if st.session_state.current_ticker == remove_ticker and st.session_state.watchlist:
                st.session_state.current_ticker = st.session_state.watchlist[0]
            st.rerun()
    
    return page


def render_dashboard():
    """Render the main dashboard."""
    st.markdown("# 📊 Financial Dashboard")
    
    # Market Overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Market Sentiment
        market_sentiment = get_market_sentiment()
        overall_sentiment = market_sentiment.get('overall_sentiment', 0)
        create_sentiment_indicator(overall_sentiment, show_gauge=True)
    
    with col2:
        # Trending Stocks
        trending = get_trending_stocks(5)
        if trending:
            st.markdown("### 🔥 Trending")
            for stock in trending[:3]:
                symbol = stock.get('symbol', 'N/A')
                trend_score = stock.get('trend_score', 0)
                sentiment = stock.get('overall_sentiment', 0)
                
                if stock.get('trending_status'):
                    badge = '<span class="trending-badge">TRENDING</span>'
                else:
                    badge = ''
                
                st.markdown(f"""
                <div style="padding: 8px; margin: 5px 0; border-left: 3px solid #1f77b4; background-color: #f8f9fa;">
                    <strong>{symbol}</strong> {badge}<br>
                    <small>Trend: {trend_score:.1f} | Sentiment: {display_sentiment_score(sentiment, False)}</small>
                </div>
                """, unsafe_allow_html=True)
    
    with col3:
        # Market Indices (placeholder)
        st.markdown("### 📈 Market Indices")
        if API_AVAILABLE:
            api_client = get_api_client()
            success, data = format_api_response(api_client.get_market_indices())
            
            if success and data:
                for index in data[:3]:
                    symbol = index.get('symbol', 'N/A')
                    price = index.get('current_price', 0)
                    change = index.get('day_change', 0)
                    change_pct = index.get('day_change_pct', 0)
                    
                    color = "🟢" if change >= 0 else "🔴"
                    st.markdown(f"""
                    <div style="padding: 5px; margin: 3px 0;">
                        <strong>{symbol}</strong><br>
                        <small>{format_currency(price)} {color} {format_change(change)} ({change_pct:.2f}%)</small>
                    </div>
                    """, unsafe_allow_html=True)
    
    with col4:
        # Quick Stats
        st.markdown("### 📊 Quick Stats")
        if st.session_state.current_ticker:
            stock_data = get_stock_data(st.session_state.current_ticker)
            if stock_data:
                current_price = stock_data.get('current_price')
                volume = stock_data.get('volume')
                market_cap = stock_data.get('market_cap')
                
                create_metric_card("Current Price", format_currency(current_price))
                create_metric_card("Volume", format_large_number(volume))
                create_metric_card("Market Cap", format_large_number(market_cap))
    
    # Main Chart
    st.markdown("---")
    st.markdown("## 📈 Current Stock Analysis")
    
    if st.session_state.current_ticker:
        stock_data = get_stock_data(st.session_state.current_ticker, include_sentiment=True)
        
        if stock_data:
            # Display stock summary
            display_stock_summary(stock_data)
            
            # Chart controls
            col1, col2, col3 = st.columns(3)
            
            with col1:
                chart_type = st.selectbox(
                    "Chart Type",
                    ["Candlestick", "Line", "Area"],
                    index=["Candlestick", "Line", "Area"].index(st.session_state.chart_type)
                )
                st.session_state.chart_type = chart_type
            
            with col2:
                time_period = st.selectbox(
                    "Time Period",
                    ["1D", "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y"],
                    index=["1D", "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y"].index(st.session_state.selected_period)
                )
                st.session_state.selected_period = time_period
            
            with col3:
                show_volume = st.checkbox("Show Volume", value=True)
            
            # Create chart (placeholder - would need historical data)
            st.info("Historical chart data will be displayed here with the new API integration")
            
            # Sentiment details if available
            if stock_data.get('overall_sentiment') is not None:
                with st.expander("💬 Sentiment Details"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        create_metric_card("24h Mentions", format_large_number(stock_data.get('mention_count_24h')))
                        create_metric_card("1h Mentions", format_large_number(stock_data.get('mention_count_1h')))
                    
                    with col2:
                        create_metric_card("Positive", format_large_number(stock_data.get('positive_mentions')))
                        create_metric_card("Negative", format_large_number(stock_data.get('negative_mentions')))
                    
                    with col3:
                        create_metric_card("Neutral", format_large_number(stock_data.get('neutral_mentions')))
                        trending = stock_data.get('trending_status', False)
                        trend_score = stock_data.get('trend_score')
                        if trending:
                            create_metric_card("Trending", f"Yes ({trend_score:.1f})")
                        else:
                            create_metric_card("Trending", "No")


def render_stock_analysis():
    """Render detailed stock analysis page."""
    st.markdown("# 🔍 Stock Analysis")
    
    # Stock selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ticker_input = st.text_input(
            "Enter Stock Symbol",
            value=st.session_state.current_ticker,
            placeholder="AAPL"
        ).upper()
        
        if ticker_input != st.session_state.current_ticker:
            st.session_state.current_ticker = ticker_input
            st.rerun()
    
    with col2:
        include_sentiment = st.checkbox("Include Sentiment", value=st.session_state.show_sentiment)
        st.session_state.show_sentiment = include_sentiment
    
    # Get stock data
    stock_data = get_stock_data(st.session_state.current_ticker, include_sentiment)
    
    if not stock_data:
        display_error_message(f"Could not fetch data for {st.session_state.current_ticker}")
        return
    
    # Display comprehensive stock information
    display_stock_summary(stock_data)
    
    # Additional analysis sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Price Chart", "💬 Sentiment", "📈 Technical", "📋 Details"])
    
    with tab1:
        st.markdown("### 📊 Price Analysis")
        st.info("Historical price charts and technical indicators will be displayed here")
        
        # Chart controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_type = st.selectbox("Chart Type", ["Candlestick", "Line", "Area"])
        
        with col2:
            time_period = st.selectbox("Period", ["1D", "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y"])
        
        with col3:
            show_indicators = st.checkbox("Show Indicators")
        
        # Placeholder for chart
        st.info("Chart will be displayed here with historical data from the new API")
    
    with tab2:
        st.markdown("### 💬 Sentiment Analysis")
        
        if stock_data.get('overall_sentiment') is not None:
            # Overall sentiment
            col1, col2 = st.columns(2)
            
            with col1:
                create_sentiment_indicator(stock_data['overall_sentiment'], show_gauge=True)
            
            with col2:
                st.markdown("#### Sentiment Breakdown")
                sentiment_data = {
                    'Metric': ['Positive Mentions', 'Negative Mentions', 'Neutral Mentions', 'Total Mentions (24h)', 'Trending Status'],
                    'Value': [
                        format_large_number(stock_data.get('positive_mentions')),
                        format_large_number(stock_data.get('negative_mentions')),
                        format_large_number(stock_data.get('neutral_mentions')),
                        format_large_number(stock_data.get('mention_count_24h')),
                        "Yes" if stock_data.get('trending_status') else "No"
                    ]
                }
                create_data_table(pd.DataFrame(sentiment_data), use_container_width=True)
            
            # Detailed sentiment button
            if st.button("Get Detailed Sentiment Analysis"):
                if API_AVAILABLE:
                    api_client = get_api_client()
                    success, data = format_api_response(
                        api_client.get_detailed_sentiment(
                            st.session_state.current_ticker,
                            include_mentions=True
                        )
                    )
                    
                    if success:
                        st.markdown("#### Detailed Sentiment Data")
                        create_data_table(data)
                        
                        if 'mentions' in data:
                            st.markdown("#### Recent Mentions")
                            for mention in data['mentions'][:5]:
                                st.markdown(f"""
                                <div style="padding: 10px; margin: 5px 0; border-left: 3px solid #1f77b4; background-color: #f8f9fa;">
                                    <strong>{mention.get('author', 'Anonymous')}</strong> 
                                    <small>({mention.get('source', 'Unknown')})</small><br>
                                    {mention.get('text', 'N/A')}<br>
                                    <small>Sentiment: {display_sentiment_score(mention.get('sentiment_score', 0), False)} | 
                                    Upvotes: {mention.get('upvotes', 0)}</small>
                                </div>
                                """, unsafe_allow_html=True)
        else:
            st.info("Sentiment data not available for this stock")
    
    with tab3:
        st.markdown("### 📈 Technical Analysis")
        st.info("Technical indicators and analysis will be displayed here")
        
        # Technical indicators placeholder
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Momentum Indicators")
            st.info("RSI, MACD, and other momentum indicators")
        
        with col2:
            st.markdown("#### Volatility Indicators")
            st.info("Bollinger Bands, ATR, and other volatility indicators")
    
    with tab4:
        st.markdown("### 📋 Company Details")
        
        # Company information
        company_info = {
            'Attribute': ['Symbol', 'Company Name', 'Exchange', 'Sector', 'Industry'],
            'Value': [
                stock_data.get('symbol', 'N/A'),
                stock_data.get('company_name', 'N/A'),
                stock_data.get('exchange', 'N/A'),
                stock_data.get('sector', 'N/A'),
                stock_data.get('industry', 'N/A')
            ]
        }
        
        create_data_table(pd.DataFrame(company_info), use_container_width=True)
        
        # Financial metrics
        financial_metrics = {
            'Metric': ['Market Cap', 'P/E Ratio', 'EPS', 'Dividend Yield', 'Beta'],
            'Value': [
                format_large_number(stock_data.get('market_cap')),
                format_number(stock_data.get('pe_ratio')),
                format_currency(stock_data.get('eps')),
                format_percentage(stock_data.get('dividend_yield')),
                format_number(stock_data.get('beta'))
            ]
        }
        
        create_data_table(pd.DataFrame(financial_metrics), use_container_width=True)


def render_comparison():
    """Render stock comparison page."""
    st.markdown("# 📈 Compare Stocks")
    
    # Stock selection
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ticker1 = st.text_input("Stock 1", value="AAPL").upper()
    with col2:
        ticker2 = st.text_input("Stock 2", value="MSFT").upper()
    with col3:
        ticker3 = st.text_input("Stock 3 (optional)", value="").upper()
    with col4:
        ticker4 = st.text_input("Stock 4 (optional)", value="").upper()
    
    tickers = [t for t in [ticker1, ticker2, ticker3, ticker4] if t]
    
    if len(tickers) < 2:
        st.warning("Please enter at least 2 stock symbols to compare")
        return
    
    # Comparison settings
    col1, col2, col3 = st.columns(3)
    
    with col1:
        time_period = st.selectbox("Time Period", ["1M", "3M", "6M", "1Y", "2Y", "5Y"])
    
    with col2:
        include_sentiment = st.checkbox("Include Sentiment", value=True)
    
    with col3:
        normalize = st.checkbox("Normalize Returns", value=True)
    
    # Get comparison data
    if st.button("Compare Stocks"):
        if API_AVAILABLE:
            api_client = get_api_client()
            success, data = format_api_response(
                api_client.compare_stocks(tickers, time_period.lower(), include_sentiment)
            )
            
            if success:
                st.markdown("### 📊 Comparison Results")
                
                # Performance metrics
                if 'performance_metrics' in data:
                    metrics_data = []
                    for symbol, metrics in data['performance_metrics'].items():
                        metrics_data.append({
                            'Symbol': symbol,
                            'Current Price': format_currency(metrics.get('current_price')),
                            'Daily Change': format_change(metrics.get('daily_change')),
                            'Daily Change %': format_percentage(metrics.get('daily_change_pct')/100 if metrics.get('daily_change_pct') else 0),
                            'Sentiment': display_sentiment_score(metrics.get('sentiment_score', 0), False) if include_sentiment else 'N/A'
                        })
                    
                    create_data_table(pd.DataFrame(metrics_data), "Performance Metrics")
                
                # Correlation matrix
                if 'correlation_matrix' in data:
                    st.markdown("#### Correlation Matrix")
                    corr_df = pd.DataFrame(data['correlation_matrix'])
                    st.dataframe(corr_df, use_container_width=True)
                
                # Historical data charts (placeholder)
                st.info("Historical comparison charts will be displayed here")
        
        else:
            st.warning("Comparison feature requires API connectivity")


def render_sentiment_analysis():
    """Render sentiment analysis page."""
    st.markdown("# 💬 Sentiment Analysis")
    
    # Market sentiment overview
    st.markdown("## 🌊 Market Sentiment Overview")
    
    market_sentiment = get_market_sentiment()
    
    if market_sentiment:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            overall_sentiment = market_sentiment.get('overall_sentiment', 0)
            create_sentiment_indicator(overall_sentiment, show_gauge=True)
        
        with col2:
            sentiment_dist = market_sentiment.get('sentiment_distribution', {})
            st.markdown("#### Sentiment Distribution")
            
            dist_data = {
                'Sentiment': ['Positive', 'Negative', 'Neutral'],
                'Count': [
                    sentiment_dist.get('positive', 0),
                    sentiment_dist.get('negative', 0),
                    sentiment_dist.get('neutral', 0)
                ]
            }
            create_data_table(pd.DataFrame(dist_data), use_container_width=True)
        
        with col3:
            st.markdown("#### Market Insights")
            if overall_sentiment > 0.2:
                st.success("🟢 Market sentiment is predominantly positive")
            elif overall_sentiment < -0.2:
                st.error("🔴 Market sentiment is predominantly negative")
            else:
                st.warning("🟡 Market sentiment is neutral")
    
    # Individual stock sentiment
    st.markdown("---")
    st.markdown("## 📊 Stock Sentiment Analysis")
    
    # Stock selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        sentiment_ticker = st.text_input(
            "Enter Stock Symbol",
            value=st.session_state.current_ticker,
            placeholder="AAPL"
        ).upper()
    
    with col2:
        timeframe = st.selectbox("Timeframe", ["1h", "24h", "7d", "30d"])
        include_mentions = st.checkbox("Include Mentions", value=False)
    
    if st.button("Analyze Sentiment"):
        if API_AVAILABLE:
            api_client = get_api_client()
            success, data = format_api_response(
                api_client.get_detailed_sentiment(
                    sentiment_ticker,
                    timeframe=timeframe,
                    include_mentions=include_mentions
                )
            )
            
            if success:
                st.markdown(f"### 💬 {sentiment_ticker} Sentiment Analysis")
                
                # Sentiment overview
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    create_sentiment_indicator(data.get('overall_sentiment'), show_gauge=True)
                
                with col2:
                    st.markdown("#### Mention Statistics")
                    mention_stats = {
                        'Metric': ['24h Mentions', 'Positive', 'Negative', 'Neutral'],
                        'Value': [
                            format_large_number(data.get('mention_count_24h')),
                            format_large_number(data.get('positive_mentions')),
                            format_large_number(data.get('negative_mentions')),
                            format_large_number(data.get('neutral_mentions'))
                        ]
                    }
                    create_data_table(pd.DataFrame(mention_stats), use_container_width=True)
                
                with col3:
                    st.markdown("#### Trending Status")
                    trending = data.get('trending_status', False)
                    trend_score = data.get('trend_score')
                    
                    if trending:
                        st.success(f"🔥 Trending with score: {trend_score:.1f}")
                    else:
                        st.info("Not currently trending")
                
                # Community breakdown
                if 'community_breakdown' in data:
                    st.markdown("#### Community Sentiment Breakdown")
                    
                    community_data = []
                    for community in data['community_breakdown']:
                        community_data.append({
                            'Community': community.get('community', 'N/A'),
                            'Avg Sentiment': display_sentiment_score(community.get('avg_sentiment', 0), False),
                            'Mentions': community.get('mention_count', 0)
                        })
                    
                    create_data_table(pd.DataFrame(community_data), use_container_width=True)
                
                # Individual mentions
                if include_mentions and 'mentions' in data:
                    st.markdown("#### Recent Mentions")
                    
                    for mention in data['mentions'][:10]:
                        sentiment_score = mention.get('sentiment_score', 0)
                        if sentiment_score > 0.2:
                            bg_color = "#e8f5e8"
                        elif sentiment_score < -0.2:
                            bg_color = "#ffeaea"
                        else:
                            bg_color = "#fff8e1"
                        
                        st.markdown(f"""
                        <div style="padding: 15px; margin: 10px 0; border-radius: 5px; background-color: {bg_color};">
                            <strong>{mention.get('author', 'Anonymous')}</strong> 
                            <small>({mention.get('source', 'Unknown')} - {mention.get('community', 'N/A')})</small><br>
                            <em>{mention.get('text', 'N/A')}</em><br>
                            <small>Sentiment: {display_sentiment_score(sentiment_score, False)} | 
                            Upvotes: {mention.get('upvotes', 0)} | 
                            {mention.get('timestamp', 'N/A')}</small>
                        </div>
                        """, unsafe_allow_html=True)
        
        else:
            st.warning("Detailed sentiment analysis requires API connectivity")
    
    # Trending stocks
    st.markdown("---")
    st.markdown("## 🔥 Trending Stocks")
    
    trending = get_trending_stocks(10)
    
    if trending:
        trending_data = []
        for stock in trending:
            trending_data.append({
                'Symbol': stock.get('symbol', 'N/A'),
                'Company': stock.get('company_name', 'N/A'),
                'Trend Score': f"{stock.get('trend_score', 0):.1f}",
                'Sentiment': display_sentiment_score(stock.get('overall_sentiment', 0), False),
                '24h Mentions': format_large_number(stock.get('mention_count_24h'))
            })
        
        create_data_table(pd.DataFrame(trending_data), "Trending Stocks", use_container_width=True)


def render_market_overview():
    """Render market overview page."""
    st.markdown("# 🌊 Market Overview")
    
    # Market indices
    st.markdown("## 📈 Market Indices")
    
    if API_AVAILABLE:
        api_client = get_api_client()
        success, data = format_api_response(api_client.get_market_indices())
        
        if success:
            indices_data = []
            for index in data:
                indices_data.append({
                    'Index': index.get('symbol', 'N/A'),
                    'Name': index.get('name', 'N/A'),
                    'Price': format_currency(index.get('current_price')),
                    'Change': format_change(index.get('day_change')),
                    'Change %': format_percentage(index.get('day_change_pct')/100 if index.get('day_change_pct') else 0),
                    'Volume': format_large_number(index.get('volume'))
                })
            
            create_data_table(pd.DataFrame(indices_data), use_container_width=True)
    
    # Market sentiment
    st.markdown("---")
    st.markdown("## 💬 Market Sentiment")
    
    market_sentiment = get_market_sentiment()
    
    if market_sentiment:
        col1, col2 = st.columns(2)
        
        with col1:
            create_sentiment_indicator(market_sentiment.get('overall_sentiment'), show_gauge=True)
        
        with col2:
            sentiment_dist = market_sentiment.get('sentiment_distribution', {})
            
            # Create pie chart for sentiment distribution
            fig = go.Figure(data=[go.Pie(
                labels=['Positive', 'Negative', 'Neutral'],
                values=[
                    sentiment_dist.get('positive', 0),
                    sentiment_dist.get('negative', 0),
                    sentiment_dist.get('neutral', 0)
                ],
                hole=0.3
            )])
            
            fig.update_layout(title="Sentiment Distribution")
            st.plotly_chart(fig, use_container_width=True)
    
    # Market statistics
    st.markdown("---")
    st.markdown("## 📊 Market Statistics")
    
    if API_AVAILABLE:
        api_client = get_api_client()
        success, data = format_api_response(api_client.get_market_statistics())
        
        if success:
            st.markdown("### Market Overview")
            
            # Display various market metrics
            if 'market_overview' in data:
                overview = data['market_overview']
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    create_metric_card("Total Volume", format_large_number(overview.get('total_volume')))
                
                with col2:
                    create_metric_card("Advancers", format_large_number(overview.get('advancers')))
                
                with col3:
                    create_metric_card("Decliners", format_large_number(overview.get('decliners')))
                
                with col4:
                    create_metric_card("Unchanged", format_large_number(overview.get('unchanged')))
            
            # Data quality
            if 'data_quality' in data:
                st.markdown("### Data Quality")
                quality = data['data_quality']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    create_metric_card("Cache Hit Rate", f"{quality.get('cache_hit_rate', 0):.1%}")
                
                with col2:
                    create_metric_card("Data Completeness", f"{quality.get('data_completeness', 0):.1%}")
                
                with col3:
                    create_metric_card("Overall Quality", f"{quality.get('overall_quality_score', 0):.1%}")


def render_settings():
    """Render settings page."""
    st.markdown("# ⚙️ Settings")
    
    # API Configuration
    st.markdown("## 🔗 API Configuration")
    
    if API_AVAILABLE:
        api_client = get_api_client()
        
        # Test API connection
        if st.button("Test API Connection"):
            success, data = format_api_response(api_client.health_check())
            
            if success:
                st.success("✅ API connection successful")
                st.json(data)
            else:
                st.error("❌ API connection failed")
        
        # Cache statistics
        st.markdown("### 📊 Cache Statistics")
        
        if st.button("Get Cache Stats"):
            success, data = format_api_response(api_client.get_cache_statistics())
            
            if success:
                create_data_table(pd.DataFrame([data]), "Cache Statistics")
        
        # Clear cache
        st.markdown("### 🗑️ Cache Management")
        
        if st.button("Clear All Cache"):
            success, data = format_api_response(api_client.clear_cache())
            
            if success:
                st.success("✅ Cache cleared successfully")
            else:
                st.error("❌ Failed to clear cache")
    
    else:
        st.error("❌ API modules not available")
    
    # Display Settings
    st.markdown("---")
    st.markdown("## 🎨 Display Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Chart Settings")
        default_chart_type = st.selectbox(
            "Default Chart Type",
            ["Candlestick", "Line", "Area"],
            index=["Candlestick", "Line", "Area"].index(st.session_state.chart_type)
        )
        st.session_state.chart_type = default_chart_type
    
    with col2:
        st.markdown("### Data Settings")
        show_sentiment_default = st.checkbox(
            "Show Sentiment by Default",
            value=st.session_state.show_sentiment
        )
        st.session_state.show_sentiment = show_sentiment_default
    
    # User Settings
    st.markdown("---")
    st.markdown("## 👤 User Settings")
    
    user_id = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Unique identifier for your watchlist and preferences"
    )
    st.session_state.user_id = user_id
    
    # About
    st.markdown("---")
    st.markdown("## ℹ️ About")
    
    st.markdown("""
    **InsiteChart** - Comprehensive Financial Analysis Platform
    
    Version: 2.0 (Enhanced with API Integration)
    
    Features:
    - Real-time stock data
    - Social media sentiment analysis
    - Advanced charting and technical indicators
    - Market sentiment overview
    - Stock comparison tools
    - Customizable watchlists
    """)
    
    if API_AVAILABLE:
        st.success("🟢 Enhanced features available with API integration")
    else:
        st.warning("🟡 Running in legacy mode - some features may be limited")


# Main application
def main():
    """Main application function."""
    # Initialize session state
    init_session_state()
    
    # Render sidebar
    page = render_sidebar()
    
    # API Status Indicator
    if API_AVAILABLE:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📡 API Status")
        st.sidebar.success("🟢 Connected")
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📡 API Status")
        st.sidebar.error("🔴 Disconnected")
    
    # Notification indicator in main area
    if API_AVAILABLE and 'notifications' in st.session_state:
        unread_count = len([n for n in st.session_state.notifications if not n.get('is_read', False)])
        if unread_count > 0:
            st.markdown(f"""
            <div style="position: fixed; top: 10px; right: 10px; background-color: #ff4b4b;
                        color: white; padding: 8px 15px; border-radius: 20px;
                        font-weight: bold; z-index: 999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
                🔔 {unread_count} New Notifications
            </div>
            """, unsafe_allow_html=True)
    
    # Render selected page
    if page == "📊 Dashboard":
        render_dashboard()
    elif page == "🔍 Stock Analysis":
        render_stock_analysis()
    elif page == "📈 Compare Stocks":
        render_comparison()
    elif page == "💬 Sentiment Analysis":
        render_sentiment_analysis()
    elif page == "🌊 Market Overview":
        render_market_overview()
    elif page == "⚙️ Settings":
        render_settings()


if __name__ == "__main__":
    main()