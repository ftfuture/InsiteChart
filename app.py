import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import ta

# Page configuration
st.set_page_config(page_title="Stock Financial Data", layout="wide")

# Helper function to format values safely
def format_currency(value, decimals=2):
    """Format a value as currency, return 'N/A' if not numeric"""
    if isinstance(value, (int, float)) and value is not None:
        return f"${value:.{decimals}f}"
    return 'N/A'

def format_number(value, decimals=2):
    """Format a number with decimals, return 'N/A' if not numeric"""
    if isinstance(value, (int, float)) and value is not None:
        return f"{value:.{decimals}f}"
    return 'N/A'

def format_large_number(value):
    """Format a large number with commas, return 'N/A' if not numeric"""
    if isinstance(value, (int, float)) and value is not None:
        return f"{value:,.0f}"
    return 'N/A'

def format_percentage(value, decimals=2):
    """Format a value as percentage, return 'N/A' if not numeric"""
    if isinstance(value, (int, float)) and value is not None:
        return f"{value * 100:.{decimals}f}%"
    return 'N/A'

def get_stock_info(ticker_symbol):
    """Fetch stock information and return ticker object and info dict"""
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    return ticker, info

def create_financial_summary(info, ticker_symbol):
    """Create financial summary DataFrame"""
    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
    
    financial_data = {
        'Metric': [
            'Current Price',
            'Previous Close',
            'Open',
            'Day High',
            'Day Low',
            'Volume',
            'Market Cap',
            '52 Week High',
            '52 Week Low',
            'P/E Ratio',
            'EPS',
            'Dividend Yield',
            'Beta'
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

# Title
st.title("📈 Stock Financial Data Analysis")

# Create tabs for different views
tab1, tab2 = st.tabs(["Single Stock Analysis", "Compare Multiple Stocks"])

# TAB 1: Single Stock Analysis
with tab1:
    col1, col2 = st.columns([1, 3])
    with col1:
        ticker_symbol = st.text_input("Enter Stock Symbol", value="AAPL", placeholder="e.g., AAPL, MSFT, TSLA", key="single_stock").upper()

    if ticker_symbol:
        try:
            ticker, info = get_stock_info(ticker_symbol)
            
            if not info or 'symbol' not in info:
                st.error(f"Invalid stock symbol: {ticker_symbol}")
            else:
                company_name = info.get('longName', ticker_symbol)
                st.subheader(f"{company_name} ({ticker_symbol})")
                
                st.markdown("### 📊 Financial Summary")
                df_summary = create_financial_summary(info, ticker_symbol)
                st.dataframe(df_summary, width='stretch', hide_index=True)
                
                csv = df_summary.to_csv(index=False)
                st.download_button(
                    label="📥 Download Financial Data as CSV",
                    data=csv,
                    file_name=f"{ticker_symbol}_financial_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                with st.expander("📅 Custom Historical Data Export"):
                    st.markdown("Download historical stock data with custom date range and metrics")
                    
                    col_date1, col_date2 = st.columns(2)
                    
                    with col_date1:
                        start_date = st.date_input(
                            "Start Date",
                            value=datetime.now() - timedelta(days=365),
                            max_value=datetime.now(),
                            key="export_start_date"
                        )
                    
                    with col_date2:
                        end_date = st.date_input(
                            "End Date",
                            value=datetime.now(),
                            max_value=datetime.now(),
                            key="export_end_date"
                        )
                    
                    st.markdown("**Select Metrics to Export:**")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    
                    with col_m1:
                        export_open = st.checkbox("Open", value=True, key="export_open")
                        export_high = st.checkbox("High", value=True, key="export_high")
                    
                    with col_m2:
                        export_low = st.checkbox("Low", value=True, key="export_low")
                        export_close = st.checkbox("Close", value=True, key="export_close")
                    
                    with col_m3:
                        export_volume = st.checkbox("Volume", value=True, key="export_volume")
                        export_adj_close = st.checkbox("Adj Close", value=False, key="export_adj_close")
                    
                    with col_m4:
                        export_sma_custom = st.checkbox("SMA", value=False, key="export_sma")
                        if export_sma_custom:
                            export_sma_period = st.number_input("SMA Period", min_value=5, max_value=200, value=20, key="export_sma_period")
                    
                    if st.button("Generate Custom Export", key="generate_export"):
                        try:
                            # Fetch historical data for custom range
                            custom_hist = ticker.history(start=start_date, end=end_date)
                            
                            if not custom_hist.empty:
                                # Select only requested columns
                                export_columns = []
                                if export_open:
                                    export_columns.append('Open')
                                if export_high:
                                    export_columns.append('High')
                                if export_low:
                                    export_columns.append('Low')
                                if export_close:
                                    export_columns.append('Close')
                                if export_adj_close and 'Adj Close' in custom_hist.columns:
                                    export_columns.append('Adj Close')
                                if export_volume:
                                    export_columns.append('Volume')
                                
                                # Create export dataframe
                                export_df = custom_hist[export_columns].copy()
                                
                                # Add SMA if requested
                                if export_sma_custom:
                                    export_df[f'SMA_{export_sma_period}'] = ta.trend.sma_indicator(custom_hist['Close'], window=export_sma_period)
                                
                                # Reset index to include date as column
                                export_df.reset_index(inplace=True)
                                export_df.rename(columns={'index': 'Date'}, inplace=True)
                                
                                # Format date column
                                if 'Date' in export_df.columns:
                                    export_df['Date'] = pd.to_datetime(export_df['Date']).dt.strftime('%Y-%m-%d')
                                
                                st.success(f"✅ Generated {len(export_df)} rows of data from {start_date} to {end_date}")
                                st.dataframe(export_df.head(10), width='stretch')
                                st.info(f"Preview showing first 10 rows. Download to see all {len(export_df)} rows.")
                                
                                # Create CSV for download
                                csv_custom = export_df.to_csv(index=False)
                                st.download_button(
                                    label=f"📥 Download Custom Historical Data ({len(export_df)} rows)",
                                    data=csv_custom,
                                    file_name=f"{ticker_symbol}_custom_export_{start_date}_{end_date}.csv",
                                    mime="text/csv",
                                    key="download_custom_export"
                                )
                            else:
                                st.warning("No data available for the selected date range.")
                        except Exception as e:
                            st.error(f"Error generating custom export: {str(e)}")
                
                st.markdown("### 📉 Historical Stock Price & Technical Indicators")
                
                chart_type = st.radio("Chart Type", ["Line Chart", "Candlestick Chart"], horizontal=True, key="chart_type")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    period_1m = st.button("1 Month", key="single_1m")
                with col2:
                    period_3m = st.button("3 Months", key="single_3m")
                with col3:
                    period_6m = st.button("6 Months", key="single_6m")
                with col4:
                    period_1y = st.button("1 Year", type="primary", key="single_1y")
                with col5:
                    period_5y = st.button("5 Years", key="single_5y")
                
                st.markdown("#### Technical Indicators")
                col_ind1, col_ind2, col_ind3, col_ind4 = st.columns(4)
                
                with col_ind1:
                    show_sma = st.checkbox("Simple Moving Average (SMA)", value=False, key="show_sma")
                    if show_sma:
                        sma_period = st.slider("SMA Period", min_value=5, max_value=200, value=20, key="sma_period")
                
                with col_ind2:
                    show_ema = st.checkbox("Exponential Moving Average (EMA)", value=False, key="show_ema")
                    if show_ema:
                        ema_period = st.slider("EMA Period", min_value=5, max_value=200, value=20, key="ema_period")
                
                with col_ind3:
                    show_rsi = st.checkbox("RSI (Relative Strength Index)", value=False, key="show_rsi")
                
                with col_ind4:
                    show_macd = st.checkbox("MACD", value=False, key="show_macd")
                
                if period_1m:
                    period = "1mo"
                    period_label = "1 Month"
                elif period_3m:
                    period = "3mo"
                    period_label = "3 Months"
                elif period_6m:
                    period = "6mo"
                    period_label = "6 Months"
                elif period_5y:
                    period = "5y"
                    period_label = "5 Years"
                else:
                    period = "1y"
                    period_label = "1 Year"
                
                hist_data = ticker.history(period=period)
                
                if not hist_data.empty:
                    # Calculate technical indicators
                    if show_sma:
                        hist_data['SMA'] = ta.trend.sma_indicator(hist_data['Close'], window=sma_period)
                    
                    if show_ema:
                        hist_data['EMA'] = ta.trend.ema_indicator(hist_data['Close'], window=ema_period)
                    
                    if show_rsi:
                        hist_data['RSI'] = ta.momentum.rsi(hist_data['Close'], window=14)
                    
                    if show_macd:
                        macd = ta.trend.MACD(hist_data['Close'])
                        hist_data['MACD'] = macd.macd()
                        hist_data['MACD_signal'] = macd.macd_signal()
                        hist_data['MACD_diff'] = macd.macd_diff()
                    
                    # Create main price chart
                    if chart_type == "Candlestick Chart":
                        # Create figure with secondary y-axis for volume
                        from plotly.subplots import make_subplots
                        
                        fig = make_subplots(
                            rows=2, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.03,
                            subplot_titles=(f'{ticker_symbol} Stock Price - {period_label}', 'Volume'),
                            row_heights=[0.7, 0.3]
                        )
                        
                        # Add candlestick chart
                        fig.add_trace(go.Candlestick(
                            x=hist_data.index,
                            open=hist_data['Open'],
                            high=hist_data['High'],
                            low=hist_data['Low'],
                            close=hist_data['Close'],
                            name='OHLC',
                            increasing_line_color='green',
                            decreasing_line_color='red'
                        ), row=1, col=1)
                        
                        # Add SMA
                        if show_sma:
                            fig.add_trace(go.Scatter(
                                x=hist_data.index,
                                y=hist_data['SMA'],
                                mode='lines',
                                name=f'SMA ({sma_period})',
                                line=dict(color='orange', width=1.5, dash='dash')
                            ), row=1, col=1)
                        
                        # Add EMA
                        if show_ema:
                            fig.add_trace(go.Scatter(
                                x=hist_data.index,
                                y=hist_data['EMA'],
                                mode='lines',
                                name=f'EMA ({ema_period})',
                                line=dict(color='blue', width=1.5, dash='dot')
                            ), row=1, col=1)
                        
                        # Add volume bars
                        colors = ['red' if hist_data['Close'].iloc[i] < hist_data['Open'].iloc[i] else 'green' 
                                  for i in range(len(hist_data))]
                        
                        fig.add_trace(go.Bar(
                            x=hist_data.index,
                            y=hist_data['Volume'],
                            name='Volume',
                            marker_color=colors,
                            showlegend=False
                        ), row=2, col=1)
                        
                        fig.update_layout(
                            height=600,
                            showlegend=True,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified'
                        )
                        
                        fig.update_xaxes(showgrid=True, gridcolor='lightgray')
                        fig.update_yaxes(title_text="Price (USD)", showgrid=True, gridcolor='lightgray', row=1, col=1)
                        fig.update_yaxes(title_text="Volume", showgrid=True, gridcolor='lightgray', row=2, col=1)
                        
                    else:
                        # Line chart (original)
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=hist_data.index,
                            y=hist_data['Close'],
                            mode='lines',
                            name='Close Price',
                            line=dict(color='#1f77b4', width=2),
                            hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>Price</b>: $%{y:.2f}<extra></extra>'
                        ))
                        
                        # Add SMA
                        if show_sma:
                            fig.add_trace(go.Scatter(
                                x=hist_data.index,
                                y=hist_data['SMA'],
                                mode='lines',
                                name=f'SMA ({sma_period})',
                                line=dict(color='orange', width=1.5, dash='dash'),
                                hovertemplate=f'<b>SMA ({sma_period})</b>: $%{{y:.2f}}<extra></extra>'
                            ))
                        
                        # Add EMA
                        if show_ema:
                            fig.add_trace(go.Scatter(
                                x=hist_data.index,
                                y=hist_data['EMA'],
                                mode='lines',
                                name=f'EMA ({ema_period})',
                                line=dict(color='green', width=1.5, dash='dot'),
                                hovertemplate=f'<b>EMA ({ema_period})</b>: $%{{y:.2f}}<extra></extra>'
                            ))
                        
                        fig.update_layout(
                            title=f"{ticker_symbol} Stock Price - {period_label}",
                            xaxis_title="Date",
                            yaxis_title="Price (USD)",
                            hovermode='x unified',
                            height=500,
                            showlegend=True,
                            xaxis=dict(showgrid=True, gridcolor='lightgray'),
                            yaxis=dict(showgrid=True, gridcolor='lightgray')
                        )
                    
                    st.plotly_chart(fig, config={'displayModeBar': True}, use_container_width=True)
                    
                    # Add RSI chart if enabled
                    if show_rsi:
                        st.markdown("#### RSI (Relative Strength Index)")
                        fig_rsi = go.Figure()
                        
                        fig_rsi.add_trace(go.Scatter(
                            x=hist_data.index,
                            y=hist_data['RSI'],
                            mode='lines',
                            name='RSI',
                            line=dict(color='purple', width=2),
                            hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>RSI</b>: %{y:.2f}<extra></extra>'
                        ))
                        
                        # Add overbought/oversold lines
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
                        
                        fig_rsi.update_layout(
                            xaxis_title="Date",
                            yaxis_title="RSI",
                            hovermode='x unified',
                            height=300,
                            showlegend=True,
                            xaxis=dict(showgrid=True, gridcolor='lightgray'),
                            yaxis=dict(showgrid=True, gridcolor='lightgray', range=[0, 100])
                        )
                        
                        st.plotly_chart(fig_rsi, config={'displayModeBar': True}, use_container_width=True)
                    
                    # Add MACD chart if enabled
                    if show_macd:
                        st.markdown("#### MACD (Moving Average Convergence Divergence)")
                        fig_macd = go.Figure()
                        
                        fig_macd.add_trace(go.Scatter(
                            x=hist_data.index,
                            y=hist_data['MACD'],
                            mode='lines',
                            name='MACD',
                            line=dict(color='blue', width=2),
                            hovertemplate='<b>MACD</b>: %{y:.2f}<extra></extra>'
                        ))
                        
                        fig_macd.add_trace(go.Scatter(
                            x=hist_data.index,
                            y=hist_data['MACD_signal'],
                            mode='lines',
                            name='Signal',
                            line=dict(color='red', width=2),
                            hovertemplate='<b>Signal</b>: %{y:.2f}<extra></extra>'
                        ))
                        
                        fig_macd.add_trace(go.Bar(
                            x=hist_data.index,
                            y=hist_data['MACD_diff'],
                            name='Histogram',
                            marker_color='gray',
                            hovertemplate='<b>Histogram</b>: %{y:.2f}<extra></extra>'
                        ))
                        
                        fig_macd.update_layout(
                            xaxis_title="Date",
                            yaxis_title="MACD",
                            hovermode='x unified',
                            height=300,
                            showlegend=True,
                            xaxis=dict(showgrid=True, gridcolor='lightgray'),
                            yaxis=dict(showgrid=True, gridcolor='lightgray')
                        )
                        
                        st.plotly_chart(fig_macd, config={'displayModeBar': True}, use_container_width=True)
                    
                    st.markdown("### 📈 Period Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Period High", f"${hist_data['High'].max():.2f}")
                    with col2:
                        st.metric("Period Low", f"${hist_data['Low'].min():.2f}")
                    with col3:
                        change = hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[0]
                        change_pct = (change / hist_data['Close'].iloc[0]) * 100
                        st.metric("Period Change", f"${change:.2f}", f"{change_pct:.2f}%")
                    with col4:
                        st.metric("Avg Volume", f"{hist_data['Volume'].mean():,.0f}")
                else:
                    st.warning("No historical data available for this period.")
                
                st.markdown("---")
                st.markdown("### 📋 Financial Statements")
                
                statement_tab1, statement_tab2, statement_tab3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
                
                with statement_tab1:
                    st.markdown("#### Income Statement")
                    try:
                        income_stmt = ticker.financials
                        if not income_stmt.empty:
                            income_stmt_transposed = income_stmt.T
                            income_stmt_transposed.index = pd.to_datetime(income_stmt_transposed.index).strftime('%Y-%m-%d')
                            st.dataframe(income_stmt_transposed, width='stretch')
                            
                            csv_income = income_stmt_transposed.to_csv()
                            st.download_button(
                                label="📥 Download Income Statement as CSV",
                                data=csv_income,
                                file_name=f"{ticker_symbol}_income_statement_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                key="download_income"
                            )
                        else:
                            st.info("Income statement data not available for this stock.")
                    except Exception as e:
                        st.warning(f"Could not load income statement: {str(e)}")
                
                with statement_tab2:
                    st.markdown("#### Balance Sheet")
                    try:
                        balance_sheet = ticker.balance_sheet
                        if not balance_sheet.empty:
                            balance_sheet_transposed = balance_sheet.T
                            balance_sheet_transposed.index = pd.to_datetime(balance_sheet_transposed.index).strftime('%Y-%m-%d')
                            st.dataframe(balance_sheet_transposed, width='stretch')
                            
                            csv_balance = balance_sheet_transposed.to_csv()
                            st.download_button(
                                label="📥 Download Balance Sheet as CSV",
                                data=csv_balance,
                                file_name=f"{ticker_symbol}_balance_sheet_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                key="download_balance"
                            )
                        else:
                            st.info("Balance sheet data not available for this stock.")
                    except Exception as e:
                        st.warning(f"Could not load balance sheet: {str(e)}")
                
                with statement_tab3:
                    st.markdown("#### Cash Flow Statement")
                    try:
                        cash_flow = ticker.cashflow
                        if not cash_flow.empty:
                            cash_flow_transposed = cash_flow.T
                            cash_flow_transposed.index = pd.to_datetime(cash_flow_transposed.index).strftime('%Y-%m-%d')
                            st.dataframe(cash_flow_transposed, width='stretch')
                            
                            csv_cashflow = cash_flow_transposed.to_csv()
                            st.download_button(
                                label="📥 Download Cash Flow as CSV",
                                data=csv_cashflow,
                                file_name=f"{ticker_symbol}_cashflow_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                key="download_cashflow"
                            )
                        else:
                            st.info("Cash flow data not available for this stock.")
                    except Exception as e:
                        st.warning(f"Could not load cash flow: {str(e)}")
                    
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            st.info("Please make sure you've entered a valid stock ticker symbol.")
    else:
        st.info("👆 Enter a stock ticker symbol above to get started!")

# TAB 2: Multiple Stock Comparison
with tab2:
    st.markdown("### Compare Multiple Stocks")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        stock1 = st.text_input("Stock 1", value="AAPL", placeholder="e.g., AAPL", key="compare_stock1").upper()
    with col2:
        stock2 = st.text_input("Stock 2", value="MSFT", placeholder="e.g., MSFT", key="compare_stock2").upper()
    with col3:
        stock3 = st.text_input("Stock 3 (Optional)", value="", placeholder="e.g., GOOGL", key="compare_stock3").upper()
    with col4:
        stock4 = st.text_input("Stock 4 (Optional)", value="", placeholder="e.g., TSLA", key="compare_stock4").upper()
    
    stocks = [s for s in [stock1, stock2, stock3, stock4] if s]
    
    if len(stocks) >= 2:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            comp_period_1m = st.button("1 Month", key="comp_1m")
        with col2:
            comp_period_3m = st.button("3 Months", key="comp_3m")
        with col3:
            comp_period_6m = st.button("6 Months", key="comp_6m")
        with col4:
            comp_period_1y = st.button("1 Year", type="primary", key="comp_1y")
        with col5:
            comp_period_5y = st.button("5 Years", key="comp_5y")
        
        if comp_period_1m:
            comp_period = "1mo"
            comp_period_label = "1 Month"
        elif comp_period_3m:
            comp_period = "3mo"
            comp_period_label = "3 Months"
        elif comp_period_6m:
            comp_period = "6mo"
            comp_period_label = "6 Months"
        elif comp_period_5y:
            comp_period = "5y"
            comp_period_label = "5 Years"
        else:
            comp_period = "1y"
            comp_period_label = "1 Year"
        
        try:
            st.markdown(f"### 📊 Performance Comparison - {comp_period_label}")
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            fig = go.Figure()
            
            comparison_data = []
            
            for idx, symbol in enumerate(stocks):
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=comp_period)
                
                if not hist.empty:
                    normalized = (hist['Close'] / hist['Close'].iloc[0] - 1) * 100
                    
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=normalized,
                        mode='lines',
                        name=symbol,
                        line=dict(color=colors[idx], width=2),
                        hovertemplate=f'<b>{symbol}</b><br>Date: %{{x|%Y-%m-%d}}<br>Return: %{{y:.2f}}%<extra></extra>'
                    ))
                    
                    info = ticker.info
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                    
                    total_return = normalized.iloc[-1]
                    period_high = hist['High'].max()
                    period_low = hist['Low'].min()
                    avg_volume = hist['Volume'].mean()
                    
                    comparison_data.append({
                        'Symbol': symbol,
                        'Company': info.get('longName', symbol)[:30],
                        'Current Price': format_currency(current_price),
                        'Total Return': f"{total_return:.2f}%",
                        'Period High': format_currency(period_high),
                        'Period Low': format_currency(period_low),
                        'Avg Volume': format_large_number(avg_volume),
                        'Market Cap': f"${format_large_number(info.get('marketCap'))}" if isinstance(info.get('marketCap'), (int, float)) else 'N/A',
                        'P/E Ratio': format_number(info.get('trailingPE'))
                    })
            
            fig.update_layout(
                title=f"Normalized Returns - {comp_period_label} (% Change from Start)",
                xaxis_title="Date",
                yaxis_title="Return (%)",
                hovermode='x unified',
                height=500,
                showlegend=True,
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray', zeroline=True, zerolinecolor='gray', zerolinewidth=1)
            )
            
            st.plotly_chart(fig, config={'displayModeBar': True}, use_container_width=True)
            
            st.markdown("### 📈 Comparison Metrics")
            df_comparison = pd.DataFrame(comparison_data)
            st.dataframe(df_comparison, width='stretch', hide_index=True)
            
            csv_comp = df_comparison.to_csv(index=False)
            st.download_button(
                label="📥 Download Comparison Data as CSV",
                data=csv_comp,
                file_name=f"stock_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_comparison"
            )
            
        except Exception as e:
            st.error(f"Error comparing stocks: {str(e)}")
            st.info("Please make sure all stock symbols are valid.")
    else:
        st.info("👆 Enter at least 2 stock symbols to compare.")
