import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

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

# Title
st.title("📈 Stock Financial Data Analysis")

# Input section
col1, col2 = st.columns([1, 3])
with col1:
    ticker_symbol = st.text_input("Enter Stock Symbol", value="AAPL", placeholder="e.g., AAPL, MSFT, TSLA").upper()

# Fetch data button
if ticker_symbol:
    try:
        # Create ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Get stock info
        info = ticker.info
        
        # Check if valid stock
        if not info or 'symbol' not in info:
            st.error(f"Invalid stock symbol: {ticker_symbol}")
        else:
            # Display company name
            company_name = info.get('longName', ticker_symbol)
            st.subheader(f"{company_name} ({ticker_symbol})")
            
            # Create financial summary table
            st.markdown("### 📊 Financial Summary")
            
            # Prepare financial data
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
            
            # Create DataFrame
            df_summary = pd.DataFrame(financial_data)
            
            # Display table
            st.dataframe(df_summary, width='stretch', hide_index=True)
            
            # CSV download button
            csv = df_summary.to_csv(index=False)
            st.download_button(
                label="📥 Download Financial Data as CSV",
                data=csv,
                file_name=f"{ticker_symbol}_financial_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Historical price chart
            st.markdown("### 📉 Historical Stock Price")
            
            # Time period selection
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                period_1m = st.button("1 Month")
            with col2:
                period_3m = st.button("3 Months")
            with col3:
                period_6m = st.button("6 Months")
            with col4:
                period_1y = st.button("1 Year", type="primary")
            with col5:
                period_5y = st.button("5 Years")
            
            # Determine period
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
            
            # Fetch historical data
            hist_data = ticker.history(period=period)
            
            if not hist_data.empty:
                # Create interactive chart with Plotly
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=hist_data.index,
                    y=hist_data['Close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color='#1f77b4', width=2),
                    hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>Price</b>: $%{y:.2f}<extra></extra>'
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
                
                # Additional statistics
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
                
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        st.info("Please make sure you've entered a valid stock ticker symbol.")
else:
    st.info("👆 Enter a stock ticker symbol above to get started!")
