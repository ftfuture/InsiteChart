# Overview

This is a comprehensive Stock Financial Data Analysis application built with Streamlit that allows users to analyze financial information for publicly traded stocks. The application uses the Yahoo Finance API (via yfinance) to fetch real-time stock data and presents it through an interactive web interface with advanced data visualizations using Plotly.

## Recent Changes (October 2025)

### Major Feature Additions:
1. **Multiple Stock Comparison** - Compare 2-4 stocks side-by-side with normalized returns charts and performance metrics
2. **Technical Indicators** - SMA, EMA, RSI, and MACD indicators with customizable parameters
3. **Candlestick Charts** - OHLC visualization with volume bars for detailed price analysis
4. **Financial Statements** - Income statement, balance sheet, and cash flow data tables with CSV export
5. **Custom Historical Data Export** - Date range selection and metric filtering for tailored data exports

# User Preferences

Preferred communication style: Simple, everyday language.

# Features

## Single Stock Analysis
- Financial summary with 13 key metrics (price, volume, market cap, P/E ratio, etc.)
- Historical price charts with 5 time period options (1M, 3M, 6M, 1Y, 5Y)
- Technical indicators: SMA, EMA, RSI, MACD
- Dual chart modes: Line chart and candlestick chart with volume
- Financial statements (income, balance sheet, cash flow)
- Custom historical data export with metric filtering
- CSV downloads for all data tables

## Multiple Stock Comparison
- Compare 2-4 stocks simultaneously
- Normalized returns chart showing percentage changes from start date
- Performance metrics table with key statistics for each stock
- Time period selection (1M, 3M, 6M, 1Y, 5Y)
- CSV export for comparison data

## Technical Analysis Tools
- Simple Moving Average (SMA) with configurable periods (5-200 days)
- Exponential Moving Average (EMA) with configurable periods (5-200 days)
- Relative Strength Index (RSI) with overbought/oversold indicators
- MACD (Moving Average Convergence Divergence) with signal line and histogram
- All indicators work with both chart types

## Data Export Options
- Financial summary CSV export
- Comparison data CSV export
- Financial statements CSV export (3 separate downloads)
- Custom historical data export with date range and metric selection

# System Architecture

## Frontend Architecture

**Technology**: Streamlit web framework
- **Rationale**: Streamlit provides rapid development of data applications with minimal frontend code, allowing focus on data analysis rather than UI implementation
- **Pros**: Fast prototyping, built-in widgets, automatic reactivity, Python-native
- **Cons**: Limited customization compared to traditional web frameworks, requires Python runtime

**Layout Structure**: Tab-based organization with wide layout
- Two main tabs: "Single Stock Analysis" and "Compare Multiple Stocks"
- Uses Streamlit's native column system for responsive design
- Expandable sections for optional features (custom data export)
- Page configured with custom title and wide layout for better data visualization

## Data Layer

**Stock Data Source**: yfinance library (Yahoo Finance API wrapper)
- **Problem addressed**: Need for reliable, free stock market data
- **Chosen solution**: yfinance provides comprehensive stock information including historical prices, financial statements, and company metadata
- **Alternatives considered**: Paid APIs like Alpha Vantage or IEX Cloud
- **Pros**: Free, comprehensive data, active maintenance
- **Cons**: Unofficial API, potential rate limiting, dependent on Yahoo Finance availability

**Data Processing**: Pandas DataFrames
- Used for data manipulation and organization of financial metrics
- Enables efficient handling of time-series data and tabular information
- Date formatting and transposition for financial statements

**Technical Analysis**: ta library
- Provides implementations for technical indicators
- Functions used: sma_indicator, ema_indicator, rsi, MACD
- Ensures accurate calculations for trading indicators

## Visualization

**Charting Library**: Plotly Graph Objects
- **Rationale**: Interactive charts with zoom, pan, and hover capabilities enhance user experience
- **Pros**: Rich interactivity, professional appearance, extensive chart types
- **Cons**: Heavier than static plotting libraries

**Chart Types**:
1. Line charts for closing prices
2. Candlestick charts with OHLC data
3. Volume bar charts
4. RSI oscillator charts
5. MACD indicator charts
6. Multi-stock comparison charts

**Visualization Features**:
- Overlays for moving averages on price charts
- Subplot layouts for volume and indicators
- Color-coded elements (green/red for up/down movements)
- Interactive hover templates with formatted data

## Utility Functions

**Data Formatting System**: Custom formatting functions for different data types
- `format_currency()`: Monetary values with dollar signs
- `format_number()`: Decimal numbers
- `format_large_number()`: Large integers with comma separators
- `format_percentage()`: Ratio to percentage conversion
- **Design principle**: Consistent null handling (returns 'N/A' for invalid/missing data) prevents display errors and improves user experience

# External Dependencies

## Third-Party Libraries

1. **streamlit**: Web application framework for the user interface
2. **yfinance**: Yahoo Finance API wrapper for stock data retrieval
3. **pandas**: Data manipulation and analysis
4. **plotly**: Interactive data visualization
5. **ta**: Technical analysis library for trading indicators
6. **datetime**: Date and time manipulation for historical data queries

## External APIs

**Yahoo Finance** (via yfinance)
- Primary data source for all stock information
- Provides: real-time quotes, historical prices, financial statements, company metadata
- No authentication required
- Rate limiting may apply (handled by yfinance library)

## Runtime Environment

- Python 3.11 runtime
- No database dependencies (data fetched on-demand from external API)
- No authentication or user management system
- Stateless application design
- Server runs on port 5000

# Implementation Notes

## Error Handling
- Try-except blocks around all external API calls
- User-friendly error messages for invalid stock symbols
- Graceful handling of missing data in financial statements
- Fallback values ('N/A') for unavailable metrics

## Performance Considerations
- Data fetched on-demand (no caching currently implemented)
- Yahoo Finance API may have rate limits
- Multiple API calls for comparison feature (one per stock)
- Financial statements are separate API calls

## Future Enhancements (Potential)
- Data caching to reduce API calls
- Support for cryptocurrency analysis
- Portfolio tracking features
- More technical indicators (Bollinger Bands, Stochastic)
- Automated alerts and notifications
- Export to Excel format
