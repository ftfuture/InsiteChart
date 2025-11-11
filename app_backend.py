import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
import json
import sys
import os

# 접근성, 국제화 및 피드백 기능 임포트
sys.path.append(os.path.join(os.path.dirname(__file__), 'frontend'))
from accessibility import accessibility_manager
from i18n import i18n_manager
from feedback_client import feedback_client, render_feedback_dashboard, auto_log_activity

# 백엔드 API URL 설정
BACKEND_URL = "http://localhost:8000"

# 국제화된 페이지 설정
st.set_page_config(
    page_title=i18n_manager.get_text("app_title"),
    layout="wide"
)

def format_currency(value, decimals=2):
    if isinstance(value, (int, float)) and value is not None:
        return f"${value:.{decimals}f}"
    return 'N/A'

def format_number(value, decimals=2):
    if isinstance(value, (int, float)) and value is not None:
        return f"{value:.{decimals}f}"
    return 'N/A'

def format_large_number(value):
    if isinstance(value, (int, float)) and value is not None:
        return f"{value:,.0f}"
    return 'N/A'

def format_percentage(value, decimals=2):
    if isinstance(value, (int, float)) and value is not None:
        return f"{value * 100:.{decimals}f}%"
    return 'N/A'

def search_stocks_backend(query, max_results=10):
    """백엔드 API를 사용하여 주식 검색"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/search",
            json={"query": query, "limit": max_results},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']['results']
        return []
    except Exception as e:
        st.error(f"검색 오류: {str(e)}")
        return []

def get_stock_details(symbol):
    """백엔드 API를 사용하여 주식 상세 정보 가져오기"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/stocks/{symbol}",
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"주식 정보 가져오기 오류: {str(e)}")
        return None

def get_stock_price_history(symbol, period="1y"):
    """주식 가격 기록 가져오기 (임시 구현)"""
    try:
        # 실제로는 백엔드 API를 통해 가져와야 함
        # 지금은 임시로 Yahoo Finance 직접 호출
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        return hist
    except Exception as e:
        st.error(f"가격 기록 가져오기 오류: {str(e)}")
        return pd.DataFrame()

# 세션 상태 초기화
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']

if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = 'AAPL'

if 'search_results' not in st.session_state:
    st.session_state.search_results = []

# 접근성 CSS 적용
st.markdown(f"""
<style>
{accessibility_manager.get_accessibility_css()}

    .stButton > button {{
        width: 100%;
        border-radius: 4px;
        font-weight: 500;
    }}
    .metric-card {{
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }}
    .stock-card {{
        background-color: #ffffff;
        border: 1px solid #e1e5e9;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
</style>
""", unsafe_allow_html=True)

# 접근성 스킵 링크 렌더링
accessibility_manager.render_skip_links()

# 포커스 관리 스크립트 추가
accessibility_manager.add_focus_management()

# 국제화된 제목
st.title(f"📈 {i18n_manager.get_text('app_title')}")

# API 상태 확인
try:
    health_response = requests.get(f"{BACKEND_URL}/health", timeout=5)
    if health_response.status_code == 200:
        st.success(f"✅ {i18n_manager.get_text('connected')}")
    else:
        st.error(f"❌ {i18n_manager.get_text('connection_failed')}")
except:
    st.error(f"❌ {i18n_manager.get_text('connection_failed')}")

# 국제화된 탭
tab1, tab2, tab3, tab4 = st.tabs([
f"📊 {i18n_manager.get_text('chart_analysis')}",
f"📉 {i18n_manager.get_text('compare_stocks')}",
f"🔍 {i18n_manager.get_text('market_overview')}",
f"💬 {i18n_manager.get_text('feedback_center')}"
])

with tab1:
    col_left, col_main, col_right = st.columns([1.5, 6, 1.5])
    
    with col_left:
        st.markdown(f"### 🔍 {i18n_manager.get_text('stock_search')}")
        
        search_query = accessibility_manager.render_accessible_input(
            "Search by name, symbol, sector...",
            help_text="주식 이름, 심볼 또는 섹터로 검색",
            key="search_input"
        )
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            search_btn = accessibility_manager.render_accessible_button("🔍 Search", help_text="검색 실행", key="search_btn")
        with col_s2:
            clear_btn = accessibility_manager.render_accessible_button("Clear", help_text="검색 결과 지우기", key="clear_search_btn")
        
        if clear_btn:
            st.session_state.search_results = []
        
        if search_btn and search_query:
            with st.spinner("Searching..."):
                results = search_stocks_backend(search_query, max_results=10)
                st.session_state.search_results = results
        
        if st.session_state.search_results:
            st.markdown("**Search Results:**")
            
            for idx, result in enumerate(st.session_state.search_results[:8]):
                symbol = result['symbol']
                name = result['company_name']
                stock_type = result['stock_type']
                exchange = result['exchange']
                
                with st.container():
                    st.markdown(f"""
                    <div class="stock-card">
                        <strong>{symbol}</strong><br>
                        <small>{name}</small><br>
                        <small>Type: {stock_type} | Exchange: {exchange}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(
                        f"Select {symbol}",
                        key=f"search_result_{idx}_{symbol}",
                        use_container_width=True
                    ):
                        st.session_state.current_ticker = symbol
                        if symbol not in st.session_state.watchlist:
                            st.session_state.watchlist.append(symbol)
                        st.rerun()
        
        st.markdown("---")
        st.markdown(f"### 🔖 {i18n_manager.get_text('watchlist')}")
        
        for ticker in st.session_state.watchlist:
            if st.button(f"📊 {ticker}", key=f"watch_{ticker}", use_container_width=True):
                st.session_state.current_ticker = ticker
                st.rerun()
        
        st.markdown("---")
        new_ticker = accessibility_manager.render_accessible_input(
            "Add Symbol",
            help_text="감시 목록에 추가할 주식 심볼을 입력",
            placeholder="NVDA",
            key="add_ticker"
        )
        
        if accessibility_manager.render_accessible_button("➕ Add to Watchlist", help_text="주식을 감시 목록에 추가", key="add_btn"):
            if new_ticker and new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                st.rerun()
        
        if len(st.session_state.watchlist) > 0:
            st.markdown("---")
            remove_ticker = st.selectbox(
                "Remove from list", 
                st.session_state.watchlist, 
                key="remove_select"
            )
            if accessibility_manager.render_accessible_button("🗑️ Remove", help_text="주식을 감시 목록에서 제거", key="remove_btn"):
                st.session_state.watchlist.remove(remove_ticker)
                if st.session_state.current_ticker == remove_ticker and st.session_state.watchlist:
                    st.session_state.current_ticker = st.session_state.watchlist[0]
                st.rerun()
    
    with col_main:
        col_sym, col_info = st.columns([1, 4])
        
        with col_sym:
            ticker_input = accessibility_manager.render_accessible_input(
                "Symbol",
                help_text="분석할 주식 심볼을 입력",
                value=st.session_state.current_ticker,
                placeholder="AAPL",
                key="main_ticker",
                label_visibility="collapsed"
            )
            
            if ticker_input != st.session_state.current_ticker:
                st.session_state.current_ticker = ticker_input
                st.rerun()
        
        ticker_symbol = st.session_state.current_ticker
        
        # 백엔드 API에서 주식 정보 가져오기
        stock_data = get_stock_details(ticker_symbol)
        
        if stock_data and stock_data.get('success'):
            stock_info = stock_data['data']
            
            with col_info:
                current_price = stock_info.get('current_price')
                previous_close = stock_info.get('previous_close')
                
                if current_price and previous_close:
                    price_change = current_price - previous_close
                    price_change_pct = (price_change / previous_close) * 100
                    change_color = "🟢" if price_change >= 0 else "🔴"
                    change_sign = "+" if price_change >= 0 else ""
                    
                    st.markdown(f"""
                    ### {stock_info.get('company_name', ticker_symbol)} ({ticker_symbol})  
                    | {format_currency(current_price)}  {change_color} {change_sign}{format_currency(price_change)} ({change_sign}{price_change_pct:.2f}%)
                    """)
                else:
                    st.markdown(f"### {stock_info.get('company_name', ticker_symbol)} ({ticker_symbol})")
            
            st.markdown("---")
            
            # 기본 통계 표시
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                st.metric("Market Cap", format_large_number(stock_info.get('market_cap')))
            with col_stat2:
                st.metric("P/E Ratio", format_number(stock_info.get('pe_ratio')))
            with col_stat3:
                st.metric("Volume", format_large_number(stock_info.get('volume')))
            with col_stat4:
                st.metric("Beta", format_number(stock_info.get('beta')))
            
            st.markdown("---")
            
            # 차트 설정
            st.markdown("#### ⏱️ Timeframe Selection")
            time_periods = ["1D", "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]
            
            if 'selected_period' not in st.session_state:
                st.session_state.selected_period = "1Y"
            
            cols = st.columns(len(time_periods))
            for i, period in enumerate(time_periods):
                with cols[i]:
                    if st.button(
                        period, 
                        key=f"tf_{period}", 
                        use_container_width=True,
                        type="primary" if st.session_state.selected_period == period else "secondary"
                    ):
                        st.session_state.selected_period = period
            
            # 차트 표시
            period_map = {
                "1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo", 
                "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y", "MAX": "max"
            }
            
            hist_data = get_stock_price_history(ticker_symbol, period_map[st.session_state.selected_period])
            
            if not hist_data.empty:
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=hist_data.index,
                    open=hist_data['Open'],
                    high=hist_data['High'],
                    low=hist_data['Low'],
                    close=hist_data['Close'],
                    name='Price'
                ))
                
                fig.update_layout(
                    title=f'{ticker_symbol} - {st.session_state.selected_period}',
                    yaxis_title='Price (USD)',
                    xaxis_title='Date',
                    height=600,
                    showlegend=True
                )
                
                st.plotly_chart(fig, config={'displayModeBar': True}, use_container_width=True)
                
                # 통계 정보
                col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
                
                with col_stat1:
                    st.metric("📊 High", f"${hist_data['High'].max():.2f}")
                with col_stat2:
                    st.metric("📉 Low", f"${hist_data['Low'].min():.2f}")
                with col_stat3:
                    change = hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[0]
                    change_pct = (change / hist_data['Close'].iloc[0]) * 100
                    st.metric("📈 Change", f"${change:.2f}", f"{change_pct:.2f}%")
                with col_stat4:
                    st.metric("📦 Avg Volume", f"{hist_data['Volume'].mean():,.0f}")
                with col_stat5:
                    volatility = hist_data['Close'].pct_change().std() * 100
                    st.metric("📊 Volatility", f"{volatility:.2f}%")
            else:
                st.warning("⚠️ No historical data available for this period.")
        else:
            st.error(f"❌ Unable to fetch data for {ticker_symbol}")
    
    with col_right:
        st.markdown("### 📊 Quick Stats")
        if stock_data and stock_data.get('success'):
            stock_info = stock_data['data']
            
            st.metric("Day High", format_currency(stock_info.get('day_high')))
            st.metric("Day Low", format_currency(stock_info.get('day_low')))
            st.metric("52W High", format_currency(stock_info.get('fifty_two_week_high')))
            st.metric("52W Low", format_currency(stock_info.get('fifty_two_week_low')))
            st.metric("EPS", format_currency(stock_info.get('eps')))
            st.metric("Dividend", format_percentage(stock_info.get('dividend_yield')))

with tab2:
    st.markdown(f"### {i18n_manager.get_text('compare_stocks')}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ticker1 = accessibility_manager.render_accessible_input("Stock 1", help_text="비교할 첫 번째 주식 심볼", value="AAPL", key="comp_ticker1").upper()
    with col2:
        ticker2 = accessibility_manager.render_accessible_input("Stock 2", help_text="비교할 두 번째 주식 심볼", value="MSFT", key="comp_ticker2").upper()
    with col3:
        ticker3 = accessibility_manager.render_accessible_input("Stock 3 (optional)", help_text="비교할 세 번째 주식 심볼 (선택사항)", value="", key="comp_ticker3").upper()
    with col4:
        ticker4 = accessibility_manager.render_accessible_input("Stock 4 (optional)", help_text="비교할 네 번째 주식 심볼 (선택사항)", value="", key="comp_ticker4").upper()
    
    tickers = [t for t in [ticker1, ticker2, ticker3, ticker4] if t]
    
    if len(tickers) >= 2:
        st.markdown(f"### {i18n_manager.get_text('period_selection')}")
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        
        with col_p1:
            comp_1m = accessibility_manager.render_accessible_button("1M", help_text="1개월 비교", key="comp_1m")
        with col_p2:
            comp_3m = accessibility_manager.render_accessible_button("3M", help_text="3개월 비교", key="comp_3m")
        with col_p3:
            comp_6m = accessibility_manager.render_accessible_button("6M", help_text="6개월 비교", key="comp_6m")
        with col_p4:
            comp_1y = accessibility_manager.render_accessible_button("1Y", help_text="1년 비교", key="comp_1y", type="primary")
        with col_p5:
            comp_5y = accessibility_manager.render_accessible_button("5Y", help_text="5년 비교", key="comp_5y")
        
        if comp_1m:
            comp_period = "1mo"
        elif comp_3m:
            comp_period = "3mo"
        elif comp_6m:
            comp_period = "6mo"
        elif comp_5y:
            comp_period = "5y"
        else:
            comp_period = "1y"
        
        try:
            comparison_data = {}
            for ticker_sym in tickers:
                hist = get_stock_price_history(ticker_sym, comp_period)
                if not hist.empty:
                    comparison_data[ticker_sym] = hist
            
            if comparison_data:
                fig_comp = go.Figure()
                
                for ticker_sym, hist in comparison_data.items():
                    normalized = (hist['Close'] / hist['Close'].iloc[0] - 1) * 100
                    
                    fig_comp.add_trace(go.Scatter(
                        x=hist.index,
                        y=normalized,
                        mode='lines',
                        name=ticker_sym,
                        line=dict(width=2.5)
                    ))
                
                fig_comp.update_layout(
                    title=i18n_manager.get_text("performance_comparison"),
                    xaxis_title=i18n_manager.get_text("date"),
                    yaxis_title=i18n_manager.get_text("return_percentage"),
                    hovermode='x unified',
                    height=600,
                    showlegend=True
                )
                
                st.plotly_chart(fig_comp, config={'displayModeBar': True}, use_container_width=True)
            else:
                st.warning("Unable to fetch data for selected stocks.")
        
        except Exception as e:
            st.error(f"Error comparing stocks: {str(e)}")
    else:
        st.info(i18n_manager.get_text("no_results"))

with tab3:
    st.markdown(f"### {i18n_manager.get_text('market_overview')}")
    
    # 시장 지표 표시
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"#### 📈 {i18n_manager.get_text('trending_stocks')}")
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/trending", timeout=10)
            if response.status_code == 200:
                trending_data = response.json()
                if trending_data.get('success'):
                    for stock in trending_data['data'][:5]:
                        st.write(f"• {stock['symbol']} - {stock['company_name']}")
        except:
            st.write("Unable to fetch trending data")
    
    with col2:
        st.markdown(f"#### 📊 {i18n_manager.get_text('market_sentiment')}")
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/market/sentiment", timeout=10)
            if response.status_code == 200:
                sentiment_data = response.json()
                if sentiment_data.get('success'):
                    sentiment = sentiment_data['data']
                    st.metric("Overall Sentiment", sentiment.get('overall_sentiment', 'N/A'))
                    st.metric("Positive Mentions", sentiment.get('positive_mentions', 0))
                    st.metric("Negative Mentions", sentiment.get('negative_mentions', 0))
        except:
            st.write("Unable to fetch sentiment data")
    
    with col3:
        st.markdown(f"#### 📈 {i18n_manager.get_text('market_indices')}")
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/market/indices", timeout=10)
            if response.status_code == 200:
                indices_data = response.json()
                if indices_data.get('success'):
                    for index in indices_data['data']:
                        st.metric(index['name'], f"{index.get('value', 0):.2f}", f"{index.get('change', 0):.2f}%")
        except:
            st.write("Unable to fetch market indices")

# 피드백 탭
with tab4:
    # Get auth token if available
    auth_token = st.session_state.get('auth_token') if 'auth_token' in st.session_state else None
    render_feedback_dashboard(auth_token)

# 푸터 정보
st.markdown("---")
st.markdown(f"### 📊 {i18n_manager.get_text('system_info')}")
st.info(f"{i18n_manager.get_text('app_title')} - {i18n_manager.get_text('connected')}")

# 국제화 및 접근성 설정
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # 언어 선택
    i18n_manager.render_locale_selector()
    
    # 접근성 설정
    accessibility_manager.render_accessibility_controls()

# API 테스트 섹션
with st.expander(f"🔧 {i18n_manager.get_text('api_test')}", expanded=False):
    st.markdown(f"### {i18n_manager.get_text('test_endpoint')}")
    
    test_endpoint = st.selectbox(
        i18n_manager.get_text("select_endpoint"),
        [
            "/api/v1/health",
            "/api/v1/market/statistics",
            "/api/v1/cache/stats"
        ]
    )
    
    if st.button(i18n_manager.get_text("test_endpoint"), key="test_api"):
        try:
            response = requests.get(f"{BACKEND_URL}{test_endpoint}", timeout=10)
            st.json(response.json())
        except Exception as e:
            st.error(f"{i18n_manager.get_text('error_occurred')}: {str(e)}")