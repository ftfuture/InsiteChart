import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import ta

st.set_page_config(page_title="Stock Chart Analysis", layout="wide")

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

def get_stock_info(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    return ticker, info

def create_financial_summary(info, ticker_symbol):
    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
    
    financial_data = {
        'Metric': [
            'Current Price', 'Previous Close', 'Open', 'Day High', 'Day Low',
            'Volume', 'Market Cap', '52 Week High', '52 Week Low',
            'P/E Ratio', 'EPS', 'Dividend Yield', 'Beta'
        ],
        'Value': [
            format_currency(current_price),
            format_currency(info.get('previousClose')),
            format_currency(info.get('open')),
            format_currency(info.get('dayHigh')),
            format_currency(info.get('dayLow')),
            format_large_number(info.get('volume')),
            f"${format_large_number(info.get('marketCap'))}" if isinstance(info.get('marketCap'), (int, float)) else 'N/A',
            format_currency(info.get('fiftyTwoWeekHigh')),
            format_currency(info.get('fiftyTwoWeekLow')),
            format_number(info.get('trailingPE')),
            format_currency(info.get('trailingEps')),
            format_percentage(info.get('dividendYield')),
            format_number(info.get('beta'))
        ]
    }
    
    return pd.DataFrame(financial_data)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']

if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = 'AAPL'

st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        border-radius: 4px;
        font-weight: 500;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Professional Stock Chart Analysis")

tab1, tab2 = st.tabs(["📊 Chart Analysis", "📉 Compare Stocks"])

with tab1:
    col_left, col_main, col_right = st.columns([1.5, 6, 1.5])
    
    with col_left:
        st.markdown("### 🔖 Watchlist")
        
        for ticker in st.session_state.watchlist:
            if st.button(f"📊 {ticker}", key=f"watch_{ticker}", use_container_width=True):
                st.session_state.current_ticker = ticker
                st.rerun()
        
        st.markdown("---")
        new_ticker = st.text_input("Add Symbol", placeholder="NVDA", key="add_ticker").upper()
        if st.button("➕ Add to Watchlist", key="add_btn", use_container_width=True):
            if new_ticker and new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                st.rerun()
        
        if len(st.session_state.watchlist) > 0:
            st.markdown("---")
            remove_ticker = st.selectbox("Remove from list", st.session_state.watchlist, key="remove_select")
            if st.button("🗑️ Remove", key="remove_btn", use_container_width=True):
                st.session_state.watchlist.remove(remove_ticker)
                if st.session_state.current_ticker == remove_ticker and st.session_state.watchlist:
                    st.session_state.current_ticker = st.session_state.watchlist[0]
                st.rerun()
    
    with col_main:
        col_sym, col_info = st.columns([1, 4])
        
        with col_sym:
            ticker_input = st.text_input("Symbol", value=st.session_state.current_ticker, placeholder="AAPL", key="main_ticker", label_visibility="collapsed").upper()
            if ticker_input != st.session_state.current_ticker:
                st.session_state.current_ticker = ticker_input
                st.rerun()
        
        ticker_symbol = st.session_state.current_ticker
        
        try:
            ticker, info = get_stock_info(ticker_symbol)
            
            if not info or 'symbol' not in info:
                st.error(f"❌ Invalid stock symbol: {ticker_symbol}")
            else:
                company_name = info.get('longName', ticker_symbol)
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                previous_close = info.get('previousClose')
                
                with col_info:
                    if current_price and previous_close:
                        price_change = current_price - previous_close
                        price_change_pct = (price_change / previous_close) * 100
                        change_color = "🟢" if price_change >= 0 else "🔴"
                        change_sign = "+" if price_change >= 0 else ""
                        
                        st.markdown(f"### {company_name} ({ticker_symbol})  |  {format_currency(current_price)}  {change_color} {change_sign}{format_currency(price_change)} ({change_sign}{price_change_pct:.2f}%)")
                    else:
                        st.markdown(f"### {company_name} ({ticker_symbol})")
                
                st.markdown("---")
                
                st.markdown("#### ⏱️ Timeframe & Chart Settings")
                col_t1, col_t2, col_t3, col_t4, col_t5, col_t6, col_t7, col_t8, col_t9, col_spacer = st.columns([1,1,1,1,1,1,1,1,1,2])
                
                time_periods = {
                    "1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo", 
                    "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y", "MAX": "max"
                }
                
                if 'selected_period' not in st.session_state:
                    st.session_state.selected_period = "1Y"
                
                with col_t1:
                    if st.button("1D", key="tf_1d", use_container_width=True, type="primary" if st.session_state.selected_period == "1D" else "secondary"):
                        st.session_state.selected_period = "1D"
                with col_t2:
                    if st.button("1W", key="tf_1w", use_container_width=True, type="primary" if st.session_state.selected_period == "1W" else "secondary"):
                        st.session_state.selected_period = "1W"
                with col_t3:
                    if st.button("1M", key="tf_1m", use_container_width=True, type="primary" if st.session_state.selected_period == "1M" else "secondary"):
                        st.session_state.selected_period = "1M"
                with col_t4:
                    if st.button("3M", key="tf_3m", use_container_width=True, type="primary" if st.session_state.selected_period == "3M" else "secondary"):
                        st.session_state.selected_period = "3M"
                with col_t5:
                    if st.button("6M", key="tf_6m", use_container_width=True, type="primary" if st.session_state.selected_period == "6M" else "secondary"):
                        st.session_state.selected_period = "6M"
                with col_t6:
                    if st.button("1Y", key="tf_1y", use_container_width=True, type="primary" if st.session_state.selected_period == "1Y" else "secondary"):
                        st.session_state.selected_period = "1Y"
                with col_t7:
                    if st.button("2Y", key="tf_2y", use_container_width=True, type="primary" if st.session_state.selected_period == "2Y" else "secondary"):
                        st.session_state.selected_period = "2Y"
                with col_t8:
                    if st.button("5Y", key="tf_5y", use_container_width=True, type="primary" if st.session_state.selected_period == "5Y" else "secondary"):
                        st.session_state.selected_period = "5Y"
                with col_t9:
                    if st.button("MAX", key="tf_max", use_container_width=True, type="primary" if st.session_state.selected_period == "MAX" else "secondary"):
                        st.session_state.selected_period = "MAX"
                
                period = time_periods[st.session_state.selected_period]
                
                col_ct1, col_ct2, col_ct3, col_spacer2 = st.columns([1.5, 1.5, 1.5, 6.5])
                
                with col_ct1:
                    if 'chart_type' not in st.session_state:
                        st.session_state.chart_type = "Candlestick"
                    
                    chart_options = ["Line", "Candlestick", "Area"]
                    selected_chart = st.selectbox("Chart Type", chart_options, 
                                                  index=chart_options.index(st.session_state.chart_type),
                                                  key="chart_type_select")
                    st.session_state.chart_type = selected_chart
                
                with col_ct2:
                    chart_height = st.slider("Height", min_value=400, max_value=1200, value=700, step=50, key="height_slider")
                
                st.markdown("#### 🔧 Indicators")
                col_i1, col_i2, col_i3, col_i4, col_i5, col_spacer3 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 4.5])
                
                with col_i1:
                    show_bb = st.checkbox("📊 Bollinger Bands", value=False, key="bb_toggle")
                with col_i2:
                    show_rsi = st.checkbox("📈 RSI", value=False, key="rsi_toggle")
                with col_i3:
                    show_macd = st.checkbox("📉 MACD", value=False, key="macd_toggle")
                with col_i4:
                    show_volume_ma = st.checkbox("📦 Volume MA", value=False, key="vol_ma_toggle")
                with col_i5:
                    show_mas = st.checkbox("📍 Moving Averages", value=False, key="ma_toggle")
                
                with st.expander("⚙️ Advanced Indicator Settings", expanded=False):
                    col_s1, col_s2, col_s3 = st.columns(3)
                    
                    with col_s1:
                        st.markdown("**Moving Averages**")
                        show_sma1 = st.checkbox("SMA 20", value=False, key="sma1")
                        show_sma2 = st.checkbox("SMA 50", value=False, key="sma2")
                        show_sma3 = st.checkbox("SMA 200", value=False, key="sma3")
                        show_custom_sma = st.checkbox("Custom SMA", value=False, key="custom_sma")
                        if show_custom_sma:
                            custom_sma_period = st.number_input("SMA Period", min_value=2, max_value=500, value=30, key="custom_sma_period")
                    
                    with col_s2:
                        st.markdown("**Exponential MAs**")
                        show_ema1 = st.checkbox("EMA 12", value=False, key="ema1")
                        show_ema2 = st.checkbox("EMA 26", value=False, key="ema2")
                        show_custom_ema = st.checkbox("Custom EMA", value=False, key="custom_ema")
                        if show_custom_ema:
                            custom_ema_period = st.number_input("EMA Period", min_value=2, max_value=500, value=30, key="custom_ema_period")
                    
                    with col_s3:
                        st.markdown("**Bollinger Bands Settings**")
                        if show_bb:
                            bb_period = st.slider("BB Period", min_value=5, max_value=50, value=20, key="bb_period")
                            bb_std = st.slider("Std Dev", min_value=1.0, max_value=3.0, value=2.0, step=0.1, key="bb_std")
                        else:
                            bb_period = 20
                            bb_std = 2.0
                
                st.markdown("---")
                
                hist_data = ticker.history(period=period)
                
                if not hist_data.empty:
                    df = hist_data.copy()
                    
                    if show_mas or show_sma1:
                        df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
                    if show_mas or show_sma2:
                        df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
                    if show_mas or show_sma3:
                        df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
                    if show_custom_sma:
                        df[f'SMA_{custom_sma_period}'] = ta.trend.sma_indicator(df['Close'], window=custom_sma_period)
                    
                    if show_mas or show_ema1:
                        df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
                    if show_mas or show_ema2:
                        df['EMA_26'] = ta.trend.ema_indicator(df['Close'], window=26)
                    if show_custom_ema:
                        df[f'EMA_{custom_ema_period}'] = ta.trend.ema_indicator(df['Close'], window=custom_ema_period)
                    
                    if show_bb:
                        bb = ta.volatility.BollingerBands(df['Close'], window=bb_period, window_dev=bb_std)
                        df['BB_High'] = bb.bollinger_hband()
                        df['BB_Mid'] = bb.bollinger_mavg()
                        df['BB_Low'] = bb.bollinger_lband()
                    
                    if show_rsi:
                        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
                    
                    if show_macd:
                        macd = ta.trend.MACD(df['Close'])
                        df['MACD'] = macd.macd()
                        df['MACD_signal'] = macd.macd_signal()
                        df['MACD_diff'] = macd.macd_diff()
                    
                    if show_volume_ma:
                        df['Volume_MA'] = ta.trend.sma_indicator(df['Volume'], window=20)
                    
                    num_subplots = 1
                    if show_rsi:
                        num_subplots += 1
                    if show_macd:
                        num_subplots += 1
                    
                    row_heights = [0.6] + [0.2] * (num_subplots - 1)
                    
                    subplot_titles = [f'{ticker_symbol} - {st.session_state.selected_period}']
                    if show_rsi:
                        subplot_titles.append('RSI')
                    if show_macd:
                        subplot_titles.append('MACD')
                    
                    fig = make_subplots(
                        rows=num_subplots, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=subplot_titles,
                        row_heights=row_heights,
                        specs=[[{"secondary_y": True}]] + [[{"secondary_y": False}]] * (num_subplots - 1)
                    )
                    
                    if st.session_state.chart_type == "Candlestick":
                        fig.add_trace(go.Candlestick(
                            x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='Price',
                            increasing_line_color='#26a69a',
                            decreasing_line_color='#ef5350'
                        ), row=1, col=1, secondary_y=False)
                    elif st.session_state.chart_type == "Area":
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['Close'],
                            mode='lines',
                            name='Close',
                            line=dict(color='#1f77b4', width=2),
                            fill='tozeroy',
                            fillcolor='rgba(31, 119, 180, 0.2)'
                        ), row=1, col=1, secondary_y=False)
                    else:
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['Close'],
                            mode='lines',
                            name='Close',
                            line=dict(color='#1f77b4', width=2.5)
                        ), row=1, col=1, secondary_y=False)
                    
                    if show_bb:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['BB_High'],
                            mode='lines', name='BB Upper',
                            line=dict(color='rgba(250, 128, 114, 0.5)', width=1, dash='dash')
                        ), row=1, col=1, secondary_y=False)
                        
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['BB_Mid'],
                            mode='lines', name='BB Middle',
                            line=dict(color='rgba(250, 128, 114, 0.8)', width=1.5)
                        ), row=1, col=1, secondary_y=False)
                        
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['BB_Low'],
                            mode='lines', name='BB Lower',
                            line=dict(color='rgba(250, 128, 114, 0.5)', width=1, dash='dash'),
                            fill='tonexty', fillcolor='rgba(250, 128, 114, 0.1)'
                        ), row=1, col=1, secondary_y=False)
                    
                    ma_colors = ['#ff9800', '#9c27b0', '#795548', '#e91e63', '#00bcd4', '#ff5722']
                    ma_idx = 0
                    
                    if show_mas or show_sma1:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['SMA_20'],
                            mode='lines', name='SMA 20',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5)
                        ), row=1, col=1, secondary_y=False)
                        ma_idx += 1
                    
                    if show_mas or show_sma2:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['SMA_50'],
                            mode='lines', name='SMA 50',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5)
                        ), row=1, col=1, secondary_y=False)
                        ma_idx += 1
                    
                    if show_mas or show_sma3:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['SMA_200'],
                            mode='lines', name='SMA 200',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5)
                        ), row=1, col=1, secondary_y=False)
                        ma_idx += 1
                    
                    if show_custom_sma:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df[f'SMA_{custom_sma_period}'],
                            mode='lines', name=f'SMA {custom_sma_period}',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5)
                        ), row=1, col=1, secondary_y=False)
                        ma_idx += 1
                    
                    if show_mas or show_ema1:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['EMA_12'],
                            mode='lines', name='EMA 12',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5, dash='dot')
                        ), row=1, col=1, secondary_y=False)
                        ma_idx += 1
                    
                    if show_mas or show_ema2:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['EMA_26'],
                            mode='lines', name='EMA 26',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5, dash='dot')
                        ), row=1, col=1, secondary_y=False)
                        ma_idx += 1
                    
                    if show_custom_ema:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df[f'EMA_{custom_ema_period}'],
                            mode='lines', name=f'EMA {custom_ema_period}',
                            line=dict(color=ma_colors[ma_idx % len(ma_colors)], width=1.5, dash='dot')
                        ), row=1, col=1, secondary_y=False)
                    
                    volume_colors = ['#ef5350' if df['Close'].iloc[i] < df['Open'].iloc[i] else '#26a69a' 
                                    for i in range(len(df))]
                    
                    fig.add_trace(go.Bar(
                        x=df.index,
                        y=df['Volume'],
                        name='Volume',
                        marker_color=volume_colors,
                        opacity=0.5,
                        showlegend=False
                    ), row=1, col=1, secondary_y=True)
                    
                    if show_volume_ma:
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['Volume_MA'],
                            mode='lines',
                            name='Volume MA',
                            line=dict(color='#2196f3', width=1.5),
                            showlegend=True
                        ), row=1, col=1, secondary_y=True)
                    
                    current_row = 2
                    
                    if show_rsi:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['RSI'],
                            mode='lines', name='RSI',
                            line=dict(color='#9c27b0', width=2)
                        ), row=current_row, col=1)
                        
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
                        
                        fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                        current_row += 1
                    
                    if show_macd:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['MACD'],
                            mode='lines', name='MACD',
                            line=dict(color='#2196f3', width=2)
                        ), row=current_row, col=1)
                        
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df['MACD_signal'],
                            mode='lines', name='Signal',
                            line=dict(color='#f44336', width=2)
                        ), row=current_row, col=1)
                        
                        colors_macd = ['#26a69a' if val >= 0 else '#ef5350' for val in df['MACD_diff']]
                        fig.add_trace(go.Bar(
                            x=df.index, y=df['MACD_diff'],
                            name='Histogram',
                            marker_color=colors_macd,
                            opacity=0.5
                        ), row=current_row, col=1)
                    
                    fig.update_layout(
                        height=chart_height,
                        showlegend=True,
                        hovermode='x unified',
                        xaxis_rangeslider_visible=False,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    fig.update_xaxes(showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')
                    fig.update_yaxes(title_text="Price (USD)", showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)', row=1, col=1, secondary_y=False)
                    fig.update_yaxes(title_text="Volume", showgrid=False, row=1, col=1, secondary_y=True)
                    
                    st.plotly_chart(fig, config={'displayModeBar': True, 'scrollZoom': True}, use_container_width=True)
                    
                    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
                    
                    with col_stat1:
                        st.metric("📊 High", f"${df['High'].max():.2f}")
                    with col_stat2:
                        st.metric("📉 Low", f"${df['Low'].min():.2f}")
                    with col_stat3:
                        change = df['Close'].iloc[-1] - df['Close'].iloc[0]
                        change_pct = (change / df['Close'].iloc[0]) * 100
                        st.metric("📈 Change", f"${change:.2f}", f"{change_pct:.2f}%")
                    with col_stat4:
                        st.metric("📦 Avg Volume", f"{df['Volume'].mean():,.0f}")
                    with col_stat5:
                        volatility = df['Close'].pct_change().std() * 100
                        st.metric("📊 Volatility", f"{volatility:.2f}%")
                    
                else:
                    st.warning("⚠️ No historical data available for this period.")
                
                with st.expander("📊 Financial Summary Table"):
                    df_summary = create_financial_summary(info, ticker_symbol)
                    st.dataframe(df_summary, width='stretch', hide_index=True)
                    
                    csv = df_summary.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"{ticker_symbol}_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                with st.expander("📋 Financial Statements"):
                    statement_tab1, statement_tab2, statement_tab3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
                    
                    with statement_tab1:
                        try:
                            income_stmt = ticker.income_stmt
                            if not income_stmt.empty:
                                income_stmt_display = income_stmt.T
                                income_stmt_display.index = pd.to_datetime(income_stmt_display.index).strftime('%Y-%m-%d')
                                st.dataframe(income_stmt_display, width='stretch')
                                
                                csv_income = income_stmt_display.to_csv()
                                st.download_button(
                                    label="📥 Download Income Statement",
                                    data=csv_income,
                                    file_name=f"{ticker_symbol}_income_statement.csv",
                                    mime="text/csv",
                                    key="download_income"
                                )
                            else:
                                st.info("Income statement data not available.")
                        except Exception as e:
                            st.error(f"Error loading income statement: {str(e)}")
                    
                    with statement_tab2:
                        try:
                            balance_sheet = ticker.balance_sheet
                            if not balance_sheet.empty:
                                balance_sheet_display = balance_sheet.T
                                balance_sheet_display.index = pd.to_datetime(balance_sheet_display.index).strftime('%Y-%m-%d')
                                st.dataframe(balance_sheet_display, width='stretch')
                                
                                csv_balance = balance_sheet_display.to_csv()
                                st.download_button(
                                    label="📥 Download Balance Sheet",
                                    data=csv_balance,
                                    file_name=f"{ticker_symbol}_balance_sheet.csv",
                                    mime="text/csv",
                                    key="download_balance"
                                )
                            else:
                                st.info("Balance sheet data not available.")
                        except Exception as e:
                            st.error(f"Error loading balance sheet: {str(e)}")
                    
                    with statement_tab3:
                        try:
                            cash_flow = ticker.cashflow
                            if not cash_flow.empty:
                                cash_flow_display = cash_flow.T
                                cash_flow_display.index = pd.to_datetime(cash_flow_display.index).strftime('%Y-%m-%d')
                                st.dataframe(cash_flow_display, width='stretch')
                                
                                csv_cashflow = cash_flow_display.to_csv()
                                st.download_button(
                                    label="📥 Download Cash Flow",
                                    data=csv_cashflow,
                                    file_name=f"{ticker_symbol}_cash_flow.csv",
                                    mime="text/csv",
                                    key="download_cashflow"
                                )
                            else:
                                st.info("Cash flow data not available.")
                        except Exception as e:
                            st.error(f"Error loading cash flow: {str(e)}")
                
                with st.expander("📅 Custom Data Export"):
                    col_date1, col_date2 = st.columns(2)
                    
                    with col_date1:
                        start_date = st.date_input(
                            "Start Date",
                            value=datetime.now() - timedelta(days=365),
                            max_value=datetime.now(),
                            key="export_start"
                        )
                    
                    with col_date2:
                        end_date = st.date_input(
                            "End Date",
                            value=datetime.now(),
                            max_value=datetime.now(),
                            key="export_end"
                        )
                    
                    st.markdown("**Select Metrics:**")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    
                    with col_m1:
                        exp_open = st.checkbox("Open", value=True, key="exp_open")
                        exp_high = st.checkbox("High", value=True, key="exp_high")
                    with col_m2:
                        exp_low = st.checkbox("Low", value=True, key="exp_low")
                        exp_close = st.checkbox("Close", value=True, key="exp_close")
                    with col_m3:
                        exp_volume = st.checkbox("Volume", value=True, key="exp_volume")
                        exp_adj = st.checkbox("Adj Close", value=False, key="exp_adj")
                    with col_m4:
                        exp_sma = st.checkbox("SMA", value=False, key="exp_sma")
                        if exp_sma:
                            exp_sma_period = st.number_input("Period", min_value=5, max_value=200, value=20, key="exp_sma_period")
                    
                    if st.button("Generate Export", key="gen_export"):
                        try:
                            custom_hist = ticker.history(start=start_date, end=end_date)
                            
                            if not custom_hist.empty:
                                export_cols = []
                                if exp_open:
                                    export_cols.append('Open')
                                if exp_high:
                                    export_cols.append('High')
                                if exp_low:
                                    export_cols.append('Low')
                                if exp_close:
                                    export_cols.append('Close')
                                if exp_adj and 'Adj Close' in custom_hist.columns:
                                    export_cols.append('Adj Close')
                                if exp_volume:
                                    export_cols.append('Volume')
                                
                                export_df = custom_hist[export_cols].copy()
                                
                                if exp_sma:
                                    export_df[f'SMA_{exp_sma_period}'] = ta.trend.sma_indicator(custom_hist['Close'], window=exp_sma_period)
                                
                                export_df.reset_index(inplace=True)
                                if 'Date' in export_df.columns:
                                    export_df['Date'] = pd.to_datetime(export_df['Date']).dt.strftime('%Y-%m-%d')
                                
                                st.success(f"✅ Generated {len(export_df)} rows")
                                st.dataframe(export_df.head(10), width='stretch')
                                
                                csv_custom = export_df.to_csv(index=False)
                                st.download_button(
                                    label=f"📥 Download ({len(export_df)} rows)",
                                    data=csv_custom,
                                    file_name=f"{ticker_symbol}_export_{start_date}_{end_date}.csv",
                                    mime="text/csv",
                                    key="dl_custom"
                                )
                            else:
                                st.warning("No data available for selected range.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    with col_right:
        st.markdown("### 📊 Quick Stats")
        if ticker_symbol:
            try:
                ticker_obj = yf.Ticker(ticker_symbol)
                info = ticker_obj.info
                
                mkt_cap = info.get('marketCap')
                pe_ratio = info.get('trailingPE')
                div_yield = info.get('dividendYield')
                beta = info.get('beta')
                
                st.metric("Market Cap", f"${format_large_number(mkt_cap)}" if isinstance(mkt_cap, (int, float)) else 'N/A')
                st.metric("P/E Ratio", format_number(pe_ratio) if pe_ratio else 'N/A')
                st.metric("Div Yield", format_percentage(div_yield) if div_yield else 'N/A')
                st.metric("Beta", format_number(beta) if beta else 'N/A')
            except:
                pass

with tab2:
    st.markdown("### Compare Multiple Stocks")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ticker1 = st.text_input("Stock 1", value="AAPL", key="comp_ticker1").upper()
    with col2:
        ticker2 = st.text_input("Stock 2", value="MSFT", key="comp_ticker2").upper()
    with col3:
        ticker3 = st.text_input("Stock 3 (optional)", value="", key="comp_ticker3").upper()
    with col4:
        ticker4 = st.text_input("Stock 4 (optional)", value="", key="comp_ticker4").upper()
    
    tickers = [t for t in [ticker1, ticker2, ticker3, ticker4] if t]
    
    if len(tickers) >= 2:
        st.markdown("### Time Period")
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        
        with col_p1:
            comp_1m = st.button("1M", key="comp_1m")
        with col_p2:
            comp_3m = st.button("3M", key="comp_3m")
        with col_p3:
            comp_6m = st.button("6M", key="comp_6m")
        with col_p4:
            comp_1y = st.button("1Y", type="primary", key="comp_1y")
        with col_p5:
            comp_5y = st.button("5Y", key="comp_5y")
        
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
                ticker_obj = yf.Ticker(ticker_sym)
                hist = ticker_obj.history(period=comp_period)
                if not hist.empty:
                    comparison_data[ticker_sym] = hist
            
            if comparison_data:
                fig_comp = go.Figure()
                
                metrics_data = []
                
                for ticker_sym, hist in comparison_data.items():
                    normalized = (hist['Close'] / hist['Close'].iloc[0] - 1) * 100
                    
                    fig_comp.add_trace(go.Scatter(
                        x=hist.index,
                        y=normalized,
                        mode='lines',
                        name=ticker_sym,
                        line=dict(width=2.5)
                    ))
                    
                    ticker_obj = yf.Ticker(ticker_sym)
                    info = ticker_obj.info
                    
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                    total_return = normalized.iloc[-1]
                    period_high = hist['High'].max()
                    period_low = hist['Low'].min()
                    avg_volume = hist['Volume'].mean()
                    market_cap = info.get('marketCap')
                    pe_ratio = info.get('trailingPE')
                    
                    metrics_data.append({
                        'Stock': ticker_sym,
                        'Current Price': format_currency(current_price),
                        'Total Return': f"{total_return:.2f}%",
                        'Period High': format_currency(period_high),
                        'Period Low': format_currency(period_low),
                        'Avg Volume': format_large_number(avg_volume),
                        'Market Cap': f"${format_large_number(market_cap)}" if isinstance(market_cap, (int, float)) else 'N/A',
                        'P/E Ratio': format_number(pe_ratio)
                    })
                
                fig_comp.update_layout(
                    title=f"Stock Performance Comparison - Normalized Returns (%)",
                    xaxis_title="Date",
                    yaxis_title="Return (%)",
                    hovermode='x unified',
                    height=600,
                    showlegend=True,
                    xaxis=dict(showgrid=True, gridcolor='lightgray'),
                    yaxis=dict(showgrid=True, gridcolor='lightgray')
                )
                
                st.plotly_chart(fig_comp, config={'displayModeBar': True}, use_container_width=True)
                
                st.markdown("### Performance Metrics")
                df_metrics = pd.DataFrame(metrics_data)
                st.dataframe(df_metrics, width='stretch', hide_index=True)
                
                csv_comp = df_metrics.to_csv(index=False)
                st.download_button(
                    label="📥 Download Comparison Data",
                    data=csv_comp,
                    file_name=f"stock_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_comparison"
                )
            else:
                st.warning("Unable to fetch data for the selected stocks.")
        
        except Exception as e:
            st.error(f"Error comparing stocks: {str(e)}")
    else:
        st.info("Please enter at least 2 stock symbols to compare.")
