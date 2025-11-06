"""
Utility functions for InsiteChart Frontend.

This module provides various utility functions for data formatting,
chart creation, and UI components.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import numpy as np


def format_currency(value: Union[int, float, None], decimals: int = 2, currency_symbol: str = "$") -> str:
    """Format value as currency."""
    if isinstance(value, (int, float)) and value is not None:
        if abs(value) >= 1e9:
            return f"{currency_symbol}{value/1e9:.{decimals}f}B"
        elif abs(value) >= 1e6:
            return f"{currency_symbol}{value/1e6:.{decimals}f}M"
        elif abs(value) >= 1e3:
            return f"{currency_symbol}{value/1e3:.{decimals}f}K"
        else:
            return f"{currency_symbol}{value:.{decimals}f}"
    return 'N/A'


def format_number(value: Union[int, float, None], decimals: int = 2) -> str:
    """Format number with decimal places."""
    if isinstance(value, (int, float)) and value is not None:
        if abs(value) >= 1e9:
            return f"{value/1e9:.{decimals}f}B"
        elif abs(value) >= 1e6:
            return f"{value/1e6:.{decimals}f}M"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.{decimals}f}K"
        else:
            return f"{value:.{decimals}f}"
    return 'N/A'


def format_large_number(value: Union[int, float, None]) -> str:
    """Format large number with commas."""
    if isinstance(value, (int, float)) and value is not None:
        return f"{value:,.0f}"
    return 'N/A'


def format_percentage(value: Union[int, float, None], decimals: int = 2, include_symbol: bool = True) -> str:
    """Format value as percentage."""
    if isinstance(value, (int, float)) and value is not None:
        formatted = f"{value * 100:.{decimals}f}"
        return f"{formatted}%" if include_symbol else formatted
    return 'N/A'


def format_change(value: Union[int, float, None], decimals: int = 2) -> str:
    """Format change value with sign."""
    if isinstance(value, (int, float)) and value is not None:
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.{decimals}f}"
    return 'N/A'


def format_change_percentage(value: Union[int, float, None], decimals: int = 2) -> str:
    """Format percentage change with sign and color indicator."""
    if isinstance(value, (int, float)) and value is not None:
        sign = "+" if value >= 0 else ""
        color = "🟢" if value >= 0 else "🔴"
        return f"{color} {sign}{value:.{decimals}f}%"
    return 'N/A'


def create_metric_card(title: str, value: str, delta: Optional[str] = None, 
                   help_text: Optional[str] = None, color: Optional[str] = None) -> None:
    """Create a styled metric card."""
    if color:
        st.markdown(f"""
        <div style="background-color: {color}; padding: 15px; border-radius: 10px; margin: 5px 0;">
            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">{title}</div>
            <div style="font-size: 24px; font-weight: bold;">{value}</div>
            {f'<div style="font-size: 14px; color: #666;">{delta}</div>' if delta else ''}
        </div>
        """, unsafe_allow_html=True)
    else:
        if help_text:
            st.metric(title, value, delta, help=help_text)
        else:
            st.metric(title, value, delta)


def create_sentiment_indicator(sentiment_score: float, show_gauge: bool = False) -> None:
    """Create sentiment indicator with gauge or text."""
    if sentiment_score is None:
        st.info("Sentiment data not available")
        return
    
    # Determine sentiment category and color
    if sentiment_score > 0.2:
        sentiment = "Positive"
        color = "#26a69a"
        emoji = "🟢"
    elif sentiment_score < -0.2:
        sentiment = "Negative"
        color = "#ef5350"
        emoji = "🔴"
    else:
        sentiment = "Neutral"
        color = "#ffa726"
        emoji = "🟡"
    
    if show_gauge:
        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = sentiment_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Sentiment Score"},
            delta = {'reference': 0},
            gauge = {
                'axis': {'range': [-1, 1]},
                'bar': {'color': color},
                'steps': [
                    {'range': [-1, -0.2], 'color': "lightgray"},
                    {'range': [-0.2, 0.2], 'color': "lightyellow"},
                    {'range': [0.2, 1], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Create simple text indicator
        st.markdown(f"""
        <div style="background-color: {color}20; padding: 15px; border-radius: 10px; text-align: center; border-left: 5px solid {color};">
            <div style="font-size: 18px; margin-bottom: 5px;">{emoji} {sentiment}</div>
            <div style="font-size: 24px; font-weight: bold;">{sentiment_score:.2f}</div>
        </div>
        """, unsafe_allow_html=True)


def create_stock_chart(data: pd.DataFrame, chart_type: str = "Candlestick", 
                    show_volume: bool = True, height: int = 600) -> go.Figure:
    """Create stock price chart."""
    if data.empty:
        return go.Figure()
    
    # Create subplot with volume
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=["Price", "Volume"]
        )
    else:
        fig = go.Figure()
    
    # Add price chart
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='Price',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ), row=1, col=1 if show_volume else None)
    elif chart_type == "Area":
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Close'],
            mode='lines',
            name='Close',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.2)'
        ), row=1, col=1 if show_volume else None)
    else:  # Line
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Close'],
            mode='lines',
            name='Close',
            line=dict(color='#1f77b4', width=2.5)
        ), row=1, col=1 if show_volume else None)
    
    # Add volume chart
    if show_volume and 'Volume' in data.columns:
        volume_colors = ['#ef5350' if data['Close'].iloc[i] < data['Open'].iloc[i] 
                       else '#26a69a' for i in range(len(data))]
        
        fig.add_trace(go.Bar(
            x=data.index,
            y=data['Volume'],
            name='Volume',
            marker_color=volume_colors,
            opacity=0.5
        ), row=2, col=1)
    
    # Update layout
    fig.update_layout(
        height=height,
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
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')
    fig.update_yaxes(title_text="Price (USD)", showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)', row=1, col=1)
    
    if show_volume:
        fig.update_yaxes(title_text="Volume", showgrid=False, row=2, col=1)
    
    return fig


def create_comparison_chart(data: Dict[str, pd.DataFrame], normalize: bool = True) -> go.Figure:
    """Create stock comparison chart."""
    fig = go.Figure()
    
    for symbol, df in data.items():
        if df.empty:
            continue
            
        if normalize:
            # Normalize to percentage change from first value
            normalized = (df['Close'] / df['Close'].iloc[0] - 1) * 100
            y_values = normalized
            name = f"{symbol} (%)"
        else:
            y_values = df['Close']
            name = symbol
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=y_values,
            mode='lines',
            name=name,
            line=dict(width=2.5)
        ))
    
    fig.update_layout(
        title="Stock Performance Comparison",
        xaxis_title="Date",
        yaxis_title="Return (%)" if normalize else "Price (USD)",
        hovermode='x unified',
        height=600,
        showlegend=True,
        xaxis=dict(showgrid=True, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridcolor='lightgray')
    )
    
    return fig


def create_sentiment_timeline(data: List[Dict[str, Any]]) -> go.Figure:
    """Create sentiment timeline chart."""
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(data)
    
    fig = go.Figure()
    
    # Add sentiment line
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['sentiment_score'],
        mode='lines+markers',
        name='Sentiment Score',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6)
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    # Color zones
    fig.add_hrect(y0=0.2, y1=1, fillcolor="lightgreen", opacity=0.2, layer="below", line_width=0)
    fig.add_hrect(y0=-0.2, y1=0, fillcolor="lightyellow", opacity=0.2, layer="below", line_width=0)
    fig.add_hrect(y0=-1, y1=-0.2, fillcolor="lightcoral", opacity=0.2, layer="below", line_width=0)
    
    fig.update_layout(
        title="Sentiment Score Timeline",
        xaxis_title="Time",
        yaxis_title="Sentiment Score",
        hovermode='x unified',
        height=400,
        yaxis=dict(range=[-1, 1])
    )
    
    return fig


def display_stock_summary(stock_data: Dict[str, Any]) -> None:
    """Display comprehensive stock summary."""
    if not stock_data:
        st.error("No stock data available")
        return
    
    # Basic info
    symbol = stock_data.get('symbol', 'N/A')
    company_name = stock_data.get('company_name', 'N/A')
    current_price = stock_data.get('current_price')
    previous_close = stock_data.get('previous_close')
    
    # Calculate change
    if current_price and previous_close:
        change = current_price - previous_close
        change_pct = (change / previous_close) * 100
        change_str = format_change(change)
        change_pct_str = format_change_percentage(change_pct)
    else:
        change_str = 'N/A'
        change_pct_str = 'N/A'
    
    # Display header
    st.markdown(f"### {company_name} ({symbol})")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        create_metric_card("Current Price", format_currency(current_price))
    
    with col2:
        create_metric_card("Change", change_str, change_pct_str)
    
    with col3:
        # Sentiment if available
        sentiment = stock_data.get('overall_sentiment')
        if sentiment is not None:
            create_sentiment_indicator(sentiment, show_gauge=False)
        else:
            create_metric_card("Sentiment", "N/A")
    
    # Financial metrics
    st.markdown("#### Financial Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_metric_card("Market Cap", format_large_number(stock_data.get('market_cap')))
        create_metric_card("Volume", format_large_number(stock_data.get('volume')))
    
    with col2:
        create_metric_card("P/E Ratio", format_number(stock_data.get('pe_ratio')))
        create_metric_card("EPS", format_currency(stock_data.get('eps')))
    
    with col3:
        create_metric_card("Dividend Yield", format_percentage(stock_data.get('dividend_yield')))
        create_metric_card("Beta", format_number(stock_data.get('beta')))
    
    with col4:
        create_metric_card("52W High", format_currency(stock_data.get('fifty_two_week_high')))
        create_metric_card("52W Low", format_currency(stock_data.get('fifty_two_week_low')))
    
    # Sentiment details if available
    if sentiment is not None:
        st.markdown("#### Sentiment Analysis")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            create_metric_card("Mentions (24h)", format_large_number(stock_data.get('mention_count_24h')))
            create_metric_card("Mentions (1h)", format_large_number(stock_data.get('mention_count_1h')))
        
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


def display_error_message(error: str, retry_action: Optional[str] = None) -> None:
    """Display formatted error message with optional retry action."""
    st.error(f"❌ {error}")
    
    if retry_action:
        if st.button("🔄 Retry", key="retry_button"):
            st.rerun()


def display_loading_message(message: str = "Loading...") -> None:
    """Display loading message with spinner."""
    with st.spinner(message):
        pass  # The caller should handle the actual loading


def create_data_table(data: Union[pd.DataFrame, List[Dict]], title: str = "", 
                    use_container_width: bool = True, height: Optional[int] = None) -> None:
    """Display data in a formatted table."""
    if title:
        st.markdown(f"#### {title}")
    
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data
    
    if df.empty:
        st.info("No data available")
        return
    
    # Format columns based on common patterns
    for col in df.columns:
        if 'price' in col.lower() or 'value' in col.lower():
            if df[col].dtype in ['float64', 'int64']:
                df[col] = df[col].apply(lambda x: format_currency(x) if pd.notna(x) else 'N/A')
        elif 'percentage' in col.lower() or 'ratio' in col.lower():
            if df[col].dtype in ['float64', 'int64']:
                df[col] = df[col].apply(lambda x: format_percentage(x) if pd.notna(x) else 'N/A')
        elif 'volume' in col.lower() or 'count' in col.lower():
            if df[col].dtype in ['float64', 'int64']:
                df[col] = df[col].apply(lambda x: format_large_number(x) if pd.notna(x) else 'N/A')
    
    st.dataframe(df, use_container_width=use_container_width, height=height)


def create_download_button(data: Union[pd.DataFrame, Dict, List], filename: str, 
                       label: str = "Download Data", mime_type: str = "text/csv") -> None:
    """Create download button for data."""
    if isinstance(data, pd.DataFrame):
        csv_data = data.to_csv(index=False)
    elif isinstance(data, dict):
        import json
        csv_data = json.dumps(data, indent=2)
        mime_type = "application/json"
    else:
        csv_data = str(data)
    
    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime=mime_type
    )


def safe_divide(numerator: Union[int, float], denominator: Union[int, float], 
                default: float = 0.0) -> float:
    """Safely divide two numbers."""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def calculate_returns(prices: pd.Series) -> pd.Series:
    """Calculate returns from price series."""
    return prices.pct_change().fillna(0)


def calculate_volatility(returns: pd.Series, annualize: bool = True) -> float:
    """Calculate volatility from returns."""
    vol = returns.std()
    if annualize:
        vol = vol * np.sqrt(252)  # Assuming daily returns
    return vol


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio from returns."""
    excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
    return safe_divide(excess_returns.mean(), excess_returns.std()) * np.sqrt(252)


def calculate_max_drawdown(prices: pd.Series) -> float:
    """Calculate maximum drawdown from price series."""
    peak = prices.expanding().max()
    drawdown = (prices - peak) / peak
    return drawdown.min()


def create_performance_metrics(prices: pd.Series) -> Dict[str, float]:
    """Calculate comprehensive performance metrics."""
    returns = calculate_returns(prices)
    
    return {
        'total_return': (prices.iloc[-1] / prices.iloc[0] - 1) * 100,
        'annualized_return': ((prices.iloc[-1] / prices.iloc[0]) ** (252 / len(prices)) - 1) * 100,
        'volatility': calculate_volatility(returns) * 100,
        'sharpe_ratio': calculate_sharpe_ratio(returns),
        'max_drawdown': calculate_max_drawdown(prices) * 100,
        'win_rate': (returns > 0).sum() / len(returns) * 100
    }