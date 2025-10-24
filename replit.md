# Overview

This is a comprehensive Stock Chart Analysis application built with Streamlit that provides an advanced charting experience for analyzing publicly traded stocks. The application uses the Yahoo Finance API (via yfinance) to fetch real-time stock data and presents it through a chart-focused interface with professional-grade data visualizations using Plotly.

## Recent Changes (October 2025)

### Latest Update - Chart-Focused Redesign:
**Complete UI Restructure** - The application has been completely redesigned with charts as the main focus:
- **Compact Header**: Stock symbol input and essential info (company name, price, change %) in a single clean row
- **Sidebar Controls**: All chart controls organized in an intuitive sidebar panel for easy access
- **Large Charts**: Chart display maximized with adjustable height (400-1200px, default 700px)
- **Enhanced Time Periods**: Expanded from 5 to 9 time period options (1D, 1W, 1M, 3M, 6M, 1Y, 2Y, 5Y, MAX)
- **Area Chart**: New chart type added alongside Line and Candlestick
- **Bollinger Bands**: Added with customizable period and standard deviation
- **Multiple Moving Averages**: Display up to 6 different moving averages simultaneously (SMA 20/50/200, EMA 12/26, plus custom)
- **Volume MA**: Volume moving average overlay on secondary axis
- **Collapsible Sections**: Financial data moved to expandable sections below chart for cleaner layout

### Professional Trading Platform UI (Latest):
**TradingView-Style Interface** - Redesigned to match professional charting platforms:
- **3-Column Layout**: Watchlist sidebar | Main chart area | Quick Stats panel
- **Watchlist Feature**: Save favorite stocks, one-click switching between charts
- **Top Toolbar**: Timeframe buttons (1D-MAX) in horizontal layout for quick access
- **Quick Indicators**: One-click toggles for Bollinger Bands, RSI, MACD, Volume MA, Moving Averages
- **Advanced Settings**: Detailed indicator configuration in collapsible expander
- **Quick Stats Panel**: Essential metrics (Market Cap, P/E, Div Yield, Beta) always visible
- **Session State**: Maintains selected ticker, timeframe, and chart preferences

### Previous Major Features:
1. **Multiple Stock Comparison** - Compare 2-4 stocks side-by-side with normalized returns charts and performance metrics
2. **Technical Indicators** - SMA, EMA, RSI, MACD, and Bollinger Bands with customizable parameters
3. **Candlestick Charts** - OHLC visualization with volume bars for detailed price analysis
4. **Financial Statements** - Income statement, balance sheet, and cash flow data tables with CSV export
5. **Custom Historical Data Export** - Date range selection and metric filtering for tailored data exports

# User Preferences

Preferred communication style: Simple, everyday language.

# Features

## Chart Analysis (Primary Tab)

### Professional Layout
- **Left Sidebar - Watchlist (1.5 units)**:
  - Default stocks: AAPL, MSFT, GOOGL, TSLA
  - Click any stock to instantly switch charts
  - Add new symbols to watchlist
  - Remove unwanted symbols
  - Persistent across session using st.session_state

- **Main Chart Area (6 units)**:
  - Large interactive chart as primary focus
  - Top toolbar with all essential controls
  - Advanced settings in collapsible sections
  - Statistics and data exports below

- **Right Sidebar - Quick Stats (1.5 units)**:
  - Market Cap
  - P/E Ratio
  - Dividend Yield
  - Beta
  - Always visible for quick reference

### Chart Display
- **Large, interactive charts** as the main focus with adjustable height (400-1200px)
- **3 Chart Types**: Line (default), Candlestick with OHLC, and Area chart with gradient fill
- **9 Time Periods**: 1 Day, 1 Week, 1 Month, 3 Months, 6 Months, 1 Year, 2 Years, 5 Years, Max
- **Real-time price updates** with color-coded change indicators (🟢 up / 🔴 down)

### Top Toolbar Controls
- **Timeframe Buttons**: Horizontal row of 9 buttons for instant period switching
  - Active button highlighted with primary styling
  - Session state tracking for selected period
- **Chart Type Selector**: Dropdown to switch between Line, Candlestick, Area
- **Height Slider**: Adjust chart height from 400 to 1200 pixels

### Indicators Section
Quick toggle checkboxes in horizontal layout:
- **Bollinger Bands**: Volatility bands with adjustable parameters
- **RSI**: Relative Strength Index oscillator
- **MACD**: Moving Average Convergence Divergence
- **Volume MA**: 20-period moving average for volume
- **Moving Averages**: Quick toggle for standard MAs

### Advanced Indicator Settings
Collapsible expander with detailed controls:
- **Moving Averages**: 
  * SMA 20, 50, 200: Standard simple moving averages
  * EMA 12, 26: Exponential moving averages
  * Custom SMA/EMA: User-defined periods (2-500 days)
  * Display up to 6 moving averages simultaneously
  
- **Bollinger Bands Settings**:
  * Period slider: 5-50 (default 20)
  * Standard deviation slider: 1.0-3.0 (default 2.0)
  * Shaded area between bands

### Volume Display
- **Integrated volume bars** on secondary y-axis below price chart
- **Color-coded**: Green (price up) / Red (price down) matching candle direction
- **Volume MA overlay**: Optional 20-period SMA for volume trend analysis

### Period Statistics
Five key metrics displayed below chart:
- **High/Low**: Period's highest and lowest prices
- **Change**: Total price change and percentage for selected period
- **Avg Volume**: Average trading volume
- **Volatility**: Standard deviation of price changes

### Detailed Information (Expandable)
- **Financial Summary Table**: 13 key metrics in collapsible section
- **Financial Statements**: Income, Balance Sheet, Cash Flow in separate tabs
- **Custom Data Export**: Historical data with custom date range and metric selection

## Stock Comparison (Secondary Tab)
- Compare 2-4 stocks simultaneously
- Normalized returns chart showing percentage changes from start date
- Performance metrics table with key statistics for each stock
- Time period selection (1M, 3M, 6M, 1Y, 5Y)
- CSV export for comparison data

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

**Layout Structure**: Professional 3-column trading platform design
- **Left Sidebar**: Watchlist panel for quick stock switching
- **Main Area**: Chart-first interface with top toolbar controls
- **Right Sidebar**: Quick Stats panel for essential metrics
- **Top Toolbar**: Timeframe buttons, chart type, indicator toggles
- **Advanced Settings**: Collapsible expander for detailed configuration
- **Wide Layout**: Full browser width utilization for better visualization

**Session State Management**:
- `watchlist`: List of favorite ticker symbols (persistent)
- `current_ticker`: Currently displayed stock
- `selected_period`: Active timeframe (1D, 1W, 1M, etc.)
- `chart_type`: Selected chart type (Line, Candlestick, Area)
- Maintains user preferences throughout session

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
- Functions used: sma_indicator, ema_indicator, rsi, MACD, BollingerBands
- Ensures accurate calculations for trading indicators

## Visualization

**Charting Library**: Plotly Graph Objects
- **Rationale**: Interactive charts with zoom, pan, and hover capabilities enhance user experience
- **Pros**: Rich interactivity, professional appearance, extensive chart types, subplot support
- **Cons**: Heavier than static plotting libraries

**Chart Types**:
1. Line charts for closing prices with gradient fills (Area mode)
2. Candlestick charts with OHLC data and color coding
3. Volume bar charts on secondary y-axis
4. RSI oscillator charts in separate subplot
5. MACD indicator charts with histogram in separate subplot
6. Multi-stock comparison charts with normalized returns

**Visualization Features**:
- **Multiple subplots**: Main chart + RSI + MACD in synchronized layout
- **Dual y-axes**: Price on primary, Volume on secondary
- **Overlays**: Moving averages and Bollinger Bands on price chart
- **Color scheme**: Green (#26a69a) for up, Red (#ef5350) for down
- **Interactive hover**: Unified crosshair with detailed data tooltips
- **Responsive sizing**: use_container_width=True for flexible layout
- **Adjustable height**: 400-1200px range with slider control

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
4. **plotly**: Interactive data visualization with subplots
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
- Stateless application design (except session state for UI preferences)
- Server runs on port 5000

# Implementation Notes

## UI/UX Design - Professional Trading Platform
- **TradingView-inspired**: Industry-standard layout familiar to traders
- **3-column structure**: Watchlist | Chart | Quick Stats
- **Top toolbar**: Quick access to frequently used controls (timeframe, chart type, indicators)
- **Advanced settings**: Detailed configuration in collapsible sections
- **One-click switching**: Watchlist enables rapid stock comparison
- **Session persistence**: Maintains user selections throughout session
- **Color indicators**: Emoji-based visual cues for price direction (🟢/🔴)

## Chart Rendering
- **Dynamic subplot creation**: Chart layout adjusts based on enabled indicators
- **Row heights**: Main chart 60%, indicators 20% each for balanced view
- **Secondary y-axis**: Volume shares space with price without obscuring data
- **Legend positioning**: Horizontal at top-right for easy reference
- **Grid styling**: Light gray (rgba) for subtle background guides
- **Multiple MA support**: Up to 6 moving averages with distinct colors

## Watchlist Implementation
- **Session state storage**: st.session_state.watchlist (list)
- **Default stocks**: ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
- **Add functionality**: Text input + button to add new symbols
- **Remove functionality**: Selectbox + button to remove symbols
- **Auto-switch**: Clicking watchlist item updates current_ticker and triggers rerun
- **Persistence**: Watchlist maintained throughout session

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
- Large charts may impact performance on older devices
- Session state prevents unnecessary data refetches

## Future Enhancements (Potential)
- Data caching to reduce API calls and improve speed
- Persistent watchlist storage (database or file)
- Drawing tools (trend lines, horizontal/vertical lines, annotations)
- Chart pattern recognition
- Price alerts and notifications
- Support for cryptocurrency analysis
- Portfolio tracking features
- More technical indicators (Stochastic, Fibonacci retracements)
- Export to Excel format
- Dark/light theme toggle
- Mobile-optimized layout
- Multi-chart layouts (2x2, 3x1 grids)
