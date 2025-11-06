# 통합 대시보드 UI/UX 설계

## 1. 개요

Enhanced Stock Search와 Social Sentiment Tracker를 통합한 대시보드의 UI/UX를 설계합니다. 이 설계는 사용자가 주식 정보와 소셜 센티먼트를 자연스럽게 탐색하고 분석할 수 있도록 직관적이고 효율적인 인터페이스를 제공하는 것을 목표로 합니다.

## 2. 디자인 원칙

### 2.1 핵심 디자인 원칙

1. **일관성 (Consistency)**: 전체 애플리케이션에서 일관된 디자인 언어와 패턴 사용
2. **직관성 (Intuitiveness)**: 사용자가 배우지 않아도 쉽게 이해하고 사용할 수 있는 인터페이스
3. **효율성 (Efficiency)**: 최소한의 클릭으로 원하는 정보에 접근할 수 있는 경로 설계
4. **반응성 (Responsiveness)**: 다양한 화면 크기와 디바이스에서 최적의 사용자 경험 제공
5. **접근성 (Accessibility)**: 모든 사용자가 쉽게 접근하고 사용할 수 있는 인터페이스

### 2.2 시각적 디자인 시스템

```python
# 디자인 토큰 정의
class DesignTokens:
    # 색상
    colors = {
        "primary": "#1E88E5",      # 메인 브랜드 색상
        "secondary": "#7C4DFF",    # 보조 색상
        "success": "#4CAF50",      # 성공/긍정
        "warning": "#FF9800",      # 경고
        "error": "#F44336",        # 에러/부정
        "neutral": "#9E9E9E",      # 중립
        "background": "#FFFFFF",    # 배경
        "surface": "#F5F5F5",     # 표면
        "text_primary": "#212121", # 주요 텍스트
        "text_secondary": "#757575", # 보조 텍스트
        "border": "#E0E0E0",      # 테두리
        "shadow": "rgba(0, 0, 0, 0.1)", # 그림자
        "sentiment_positive": "#4CAF50", # 긍정 센티먼트
        "sentiment_negative": "#F44336", # 부정 센티먼트
        "sentiment_neutral": "#9E9E9E", # 중립 센티먼트
        "trending_up": "#4CAF50",     # 상승 트렌드
        "trending_down": "#F44336",   # 하락 트렌드
    }
    
    # 타이포그래피
    typography = {
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "font_sizes": {
            "xs": "0.75rem",    # 12px
            "sm": "0.875rem",   # 14px
            "base": "1rem",     # 16px
            "lg": "1.125rem",   # 18px
            "xl": "1.25rem",    # 20px
            "2xl": "1.5rem",    # 24px
            "3xl": "1.875rem",  # 30px
            "4xl": "2.25rem",   # 36px
        },
        "font_weights": {
            "light": "300",
            "normal": "400",
            "medium": "500",
            "semibold": "600",
            "bold": "700",
        }
    }
    
    # 간격
    spacing = {
        "xs": "0.25rem",   # 4px
        "sm": "0.5rem",    # 8px
        "md": "1rem",      # 16px
        "lg": "1.5rem",    # 24px
        "xl": "2rem",      # 32px
        "2xl": "3rem",     # 48px
    }
    
    # 경계선
    borders = {
        "radius_sm": "0.25rem",   # 4px
        "radius_md": "0.375rem",  # 6px
        "radius_lg": "0.5rem",    # 8px
        "radius_full": "9999px",
        "width_sm": "1px",
        "width_md": "2px",
        "width_lg": "4px",
    }
    
    # 그림자
    shadows = {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    }
```

## 3. 레이아웃 설계

### 3.1 전체 레이아웃 구조

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 헤더 (Header)                                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ 사이드바 (Sidebar)                │ 메인 콘텐츠 (Main Content)               │
│                                 │                                       │
│ ┌─────────────────────────────┐ │ ┌─────────────────────────────────────┐ │
│ │ 로고 및 검색              │ │ │ 탭 내비게이션                  │ │
│ │ ┌─────────────────────────┐   │ │ ┌─────┬─────┬─────┬─────┐ │ │
│ │ │ 🔍 통합 검색창     │   │ │ │ 검색 │ 센티 │ 트렌 │ 분석 │ │ │
│ │ │                     │   │ │ │      │ 먼트 │ 딩   │      │ │ │
│ │ └─────────────────────────┘   │ │ └─────┴─────┴─────┴─────┘ │ │
│ │                             │ │                                 │ │
│ │ ┌─────────────────────────┐   │ │ ┌─────────────────────────────────┐ │ │
│ │ │ 📊 빠른 통계        │   │ │ │ 동적 콘텐츠 영역            │ │ │
│ │ │                     │   │ │ │                                 │ │ │
│ │ │ 📈 인기 주식         │   │ │ │ (검색 결과/센티먼트/      │ │ │
│ │ │ 🔥 트렌딩 주식       │   │ │ │  트렌딩/차트)                │ │ │
│ │ │                     │   │ │ │                                 │ │ │
│ │ │ ⭐ 관심종목          │   │ │ └─────────────────────────────────┘ │ │
│ │ └─────────────────────────┘   │ │                                 │ │
│ │                             │ │                                 │ │
│ │ ┌─────────────────────────┐   │ │                                 │ │
│ │ │ 🏷️ 필터              │   │ │                                 │ │
│ │ │                     │   │ │                                 │ │
│ │ │ ⚙️ 설정                │   │ │                                 │ │
│ │ └─────────────────────────┘   │ │                                 │ │
│ └─────────────────────────────┘ │ └─────────────────────────────────┘ │
└─────────────────────────────────┴─────────────────────────────────────┘
```

### 3.2 반응형 레이아웃

```css
/* 모바일 (768px 이하) */
@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
    grid-template-areas: 
      "header"
      "sidebar"
      "content";
  }
  
  .sidebar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: auto;
    width: 100%;
    transform: translateY(100%);
    transition: transform 0.3s ease;
  }
  
  .sidebar.open {
    transform: translateY(0);
  }
}

/* 태블릿 (769px - 1024px) */
@media (min-width: 769px) and (max-width: 1024px) {
  .dashboard {
    grid-template-columns: 250px 1fr;
    grid-template-areas: 
      "header header"
      "sidebar content";
  }
  
  .sidebar {
    position: relative;
    width: 250px;
  }
}

/* 데스크톱 (1025px 이상) */
@media (min-width: 1025px) {
  .dashboard {
    grid-template-columns: 280px 1fr;
    grid-template-areas: 
      "header header"
      "sidebar content";
  }
  
  .sidebar {
    position: relative;
    width: 280px;
  }
}
```

## 4. 핵심 컴포넌트 설계

### 4.1 통합 검색 컴포넌트

```python
import streamlit as st
from typing import List, Dict, Optional, Any
import asyncio

class UnifiedSearchComponent:
    """통합 검색 컴포넌트"""
    
    def __init__(self, on_search_callback, on_filter_callback):
        self.on_search_callback = on_search_callback
        self.on_filter_callback = on_filter_callback
        self.search_state = "idle"  # idle, searching, error
        self.search_results = []
        self.filters = {
            "stock_types": [],
            "sectors": [],
            "exchanges": [],
            "sentiment_range": None,
            "trending_only": False
        }
    
    def render(self):
        """검색 컴포넌트 렌더링"""
        # 검색 상태 관리
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""
        
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        
        # 검색 입력 영역
        col1, col2, col3 = st.columns([6, 1, 1])
        
        with col1:
            search_query = st.text_input(
                "🔍 주식, 센티먼트, 트렌드 검색",
                value=st.session_state.search_query,
                key="unified_search",
                placeholder="예: AAPL, 긍정 센티먼트, 상승 트렌드",
                help="주식 심볼, 회사명, 센티먼트 키워드 등으로 검색",
                on_change=self._handle_search_input
            )
        
        with col2:
            if st.button("🔍", key="search_button", help="검색 실행"):
                self._execute_search()
        
        with col3:
            if st.button("🔄", key="refresh_button", help="검색 결과 새로고침"):
                self._refresh_results()
        
        # 고급 필터 토글
        with st.expander("🔍 고급 필터", expanded=False):
            self._render_filters()
        
        # 검색 결과 표시
        if st.session_state.search_results:
            self._render_search_results()
        elif self.search_state == "searching":
            st.info("🔍 검색 중...")
        elif self.search_state == "error":
            st.error("❌ 검색 중 오류가 발생했습니다. 다시 시도해주세요.")
    
    def _handle_search_input(self, value):
        """검색 입력 처리"""
        st.session_state.search_query = value
        
        # 자동완성 표시 (2글자 이상)
        if len(value) >= 2:
            self._show_autocomplete(value)
    
    def _show_autocomplete(self, query: str):
        """자동완성 표시"""
        # 실제 구현에서는 API 호출로 자동완성 데이터 가져오기
        autocomplete_results = self._get_autocomplete_results(query)
        
        if autocomplete_results:
            with st.container():
                st.write("**검색 제안:**")
                for result in autocomplete_results[:5]:
                    if st.button(f"📊 {result['symbol']} - {result['name']}", 
                                key=f"autocomplete_{result['symbol']}"):
                        st.session_state.search_query = result['symbol']
                        self._execute_search()
    
    def _get_autocomplete_results(self, query: str) -> List[Dict]:
        """자동완성 결과 가져오기"""
        # 시뮬레이션된 자동완성 결과
        return [
            {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "stock"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock"},
            {"symbol": "긍정 센티먼트", "name": "긍정적인 시장 분위기", "type": "sentiment"},
            {"symbol": "상승 트렌드", "name": "급상승하는 주식들", "type": "trending"},
        ]
    
    def _render_filters(self):
        """필터 렌더링"""
        col1, col2 = st.columns(2)
        
        with col1:
            # 주식 유형 필터
            stock_types = st.multiselect(
                "주식 유형",
                ["EQUITY", "ETF", "MUTUALFUND", "INDEX"],
                default=self.filters["stock_types"],
                key="stock_types_filter"
            )
            self.filters["stock_types"] = stock_types
            
            # 섹터 필터
            sectors = st.multiselect(
                "섹터",
                ["Technology", "Healthcare", "Finance", "Energy", "Consumer Goods"],
                default=self.filters["sectors"],
                key="sectors_filter"
            )
            self.filters["sectors"] = sectors
        
        with col2:
            # 거래소 필터
            exchanges = st.multiselect(
                "거래소",
                ["NASDAQ", "NYSE", "AMEX"],
                default=self.filters["exchanges"],
                key="exchanges_filter"
            )
            self.filters["exchanges"] = exchanges
            
            # 센티먼트 범위 필터
            sentiment_range = st.slider(
                "센티먼트 범위",
                -100, 100, (-50, 50),
                value=self.filters["sentiment_range"] or (-50, 50),
                key="sentiment_range_filter"
            )
            self.filters["sentiment_range"] = sentiment_range
            
            # 트렌딩만 보기
            trending_only = st.checkbox(
                "트렌딩 주식만 보기",
                value=self.filters["trending_only"],
                key="trending_only_filter"
            )
            self.filters["trending_only"] = trending_only
    
    def _execute_search(self):
        """검색 실행"""
        query = st.session_state.search_query
        
        if not query.strip():
            st.warning("⚠️ 검색어를 입력해주세요.")
            return
        
        self.search_state = "searching"
        
        # 비동기 검색 실행
        with st.spinner("🔍 검색 중..."):
            try:
                # 실제 구현에서는 API 호출로 검색 결과 가져오기
                search_results = asyncio.run(self._perform_search(query, self.filters))
                st.session_state.search_results = search_results
                self.search_state = "idle"
                
                # 검색 콜백 호출
                if self.on_search_callback:
                    self.on_search_callback(query, search_results)
                    
            except Exception as e:
                st.error(f"❌ 검색 중 오류: {str(e)}")
                self.search_state = "error"
    
    async def _perform_search(self, query: str, filters: Dict) -> List[Dict]:
        """검색 수행 (비동기)"""
        # 실제 구현에서는 API 호출로 검색 수행
        # 여기서는 시뮬레이션된 결과 반환
        
        await asyncio.sleep(1)  # 시뮬레이션된 지연
        
        # 시뮬레이션된 검색 결과
        return [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "type": "stock",
                "price": 150.25,
                "change": 2.5,
                "change_percent": 1.69,
                "sentiment_score": 65,
                "trending": True,
                "mention_count": 1247
            },
            {
                "symbol": "TSLA",
                "name": "Tesla, Inc.",
                "type": "stock",
                "price": 250.75,
                "change": -5.25,
                "change_percent": -2.05,
                "sentiment_score": -25,
                "trending": True,
                "mention_count": 892
            }
        ]
    
    def _refresh_results(self):
        """검색 결과 새로고침"""
        if st.session_state.search_query:
            self._execute_search()
    
    def _render_search_results(self):
        """검색 결과 렌더링"""
        results = st.session_state.search_results
        
        if not results:
            st.info("📭 검색 결과가 없습니다.")
            return
        
        st.write(f"📊 **{len(results)}개의 검색 결과**")
        
        # 결과 카드 렌더링
        for i, result in enumerate(results):
            with st.container():
                self._render_result_card(result, i)
    
    def _render_result_card(self, result: Dict, index: int):
        """검색 결과 카드 렌더링"""
        # 색상 결정
        change_color = "green" if result["change_percent"] > 0 else "red"
        sentiment_color = self._get_sentiment_color(result["sentiment_score"])
        
        # 카드 레이아웃
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            # 주식 정보
            st.write(f"**{result['symbol']}**")
            st.write(result['name'])
        
        with col2:
            # 가격 정보
            st.write(f"${result['price']:.2f}")
            st.markdown(f"<span style='color: {change_color}'>{result['change_percent']:+.2f}%</span>", 
                       unsafe_allow_html=True)
        
        with col3:
            # 센티먼트 정보
            st.write(f"💭 {result['sentiment_score']:+.0f}")
            st.markdown(f"<span style='color: {sentiment_color}'>{'🔥' if result['trending'] else '📊'}</span>", 
                       unsafe_allow_html=True)
        
        with col4:
            # 작업 버튼
            if st.button("📈", key=f"chart_{index}", help="차트 보기"):
                st.session_state.selected_stock = result
                st.rerun()
            
            if st.button("⭐", key=f"watchlist_{index}", help="관심종목 추가"):
                self._add_to_watchlist(result)
    
    def _get_sentiment_color(self, score: float) -> str:
        """센티먼트 점수에 따른 색상 반환"""
        if score > 30:
            return "green"
        elif score > 0:
            return "lightgreen"
        elif score > -30:
            return "orange"
        else:
            return "red"
    
    def _add_to_watchlist(self, result: Dict):
        """관심종목에 추가"""
        # 실제 구현에서는 관심종목 관리 로직
        st.success(f"⭐ {result['symbol']}을 관심종목에 추가했습니다.")
```

### 4.2 통합 차트 컴포넌트

```python
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

class UnifiedChartComponent:
    """통합 차트 컴포넌트"""
    
    def __init__(self, data_service):
        self.data_service = data_service
    
    def render(self, symbol: str):
        """통합 차트 렌더링"""
        if not symbol:
            st.warning("⚠️ 차트를 표시할 주식을 선택해주세요.")
            return
        
        # 데이터 가져오기
        with st.spinner("📊 차트 데이터 로딩 중..."):
            stock_data = self.data_service.get_stock_data(symbol)
            sentiment_data = self.data_service.get_sentiment_data(symbol)
        
        if not stock_data:
            st.error(f"❌ {symbol}에 대한 데이터를 찾을 수 없습니다.")
            return
        
        # 차트 탭 내비게이션
        tab1, tab2, tab3 = st.tabs(["📈 가격 차트", "💭 센티먼트 차트", "🔗 통합 차트"])
        
        with tab1:
            self._render_price_chart(stock_data, symbol)
        
        with tab2:
            self._render_sentiment_chart(sentiment_data, symbol)
        
        with tab3:
            self._render_unified_chart(stock_data, sentiment_data, symbol)
    
    def _render_price_chart(self, stock_data: Dict, symbol: str):
        """가격 차트 렌더링"""
        st.subheader(f"📈 {symbol} 가격 차트")
        
        # 차트 타입 선택
        chart_type = st.selectbox(
            "차트 타입",
            ["선형 차트", "캔들 차트", "OHLC 차트"],
            index=0,
            key=f"chart_type_{symbol}"
        )
        
        # 기간 선택
        period = st.selectbox(
            "기간",
            ["1일", "1주", "1개월", "3개월", "6개월", "1년"],
            index=2,
            key=f"period_{symbol}"
        )
        
        # 시뮬레이션된 가격 데이터
        price_data = self._get_simulated_price_data(symbol, period)
        
        # 차트 생성
        if chart_type == "선형 차트":
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=price_data['dates'],
                y=price_data['prices'],
                mode='lines',
                name=symbol,
                line=dict(color='#1E88E5', width=2)
            ))
            
            fig.update_layout(
                title=f"{symbol} 가격 차트 ({period})",
                xaxis_title="날짜",
                yaxis_title="가격 ($)",
                hovermode='x unified',
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "캔들 차트":
            fig = go.Figure()
            
            fig.add_trace(go.Candlestick(
                x=price_data['dates'],
                open=price_data['opens'],
                high=price_data['highs'],
                low=price_data['lows'],
                close=price_data['prices'],
                name=symbol
            ))
            
            fig.update_layout(
                title=f"{symbol} 캔들 차트 ({period})",
                xaxis_title="날짜",
                yaxis_title="가격 ($)",
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def _render_sentiment_chart(self, sentiment_data: Dict, symbol: str):
        """센티먼트 차트 렌더링"""
        st.subheader(f"💭 {symbol} 센티먼트 차트")
        
        if not sentiment_data:
            st.info(f"📭 {symbol}에 대한 센티먼트 데이터가 없습니다.")
            return
        
        # 시뮬레이션된 센티먼트 데이터
        sentiment_history = self._get_simulated_sentiment_data(symbol)
        
        # 센티먼트 점수 차트
        fig1 = go.Figure()
        
        fig1.add_trace(go.Scatter(
            x=sentiment_history['dates'],
            y=sentiment_history['scores'],
            mode='lines+markers',
            name='센티먼트 점수',
            line=dict(color='#7C4DFF', width=2),
            marker=dict(size=6)
        ))
        
        # 영역 색상 (긍정/부정)
        colors = ['green' if score > 0 else 'red' for score in sentiment_history['scores']]
        
        fig1.add_trace(go.Scatter(
            x=sentiment_history['dates'],
            y=sentiment_history['scores'],
            mode='markers',
            marker=dict(
                size=10,
                color=colors,
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            name='센티먼트 구분',
            showlegend=False
        ))
        
        fig1.update_layout(
            title=f"{symbol} 센티먼트 점수 변화",
            xaxis_title="날짜",
            yaxis_title="센티먼트 점수 (-100 ~ +100)",
            template='plotly_white',
            yaxis=dict(range=[-100, 100])
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # 언급량 차트
        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            x=sentiment_history['dates'],
            y=sentiment_history['mention_counts'],
            name='언급량',
            marker_color='#FF9800'
        ))
        
        fig2.update_layout(
            title=f"{symbol} 언급량 변화",
            xaxis_title="날짜",
            yaxis_title="언급량",
            template='plotly_white'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    def _render_unified_chart(self, stock_data: Dict, sentiment_data: Dict, symbol: str):
        """통합 차트 렌더링"""
        st.subheader(f"🔗 {symbol} 통합 차트")
        
        # 시뮬레이션된 통합 데이터
        unified_data = self._get_simulated_unified_data(symbol)
        
        # 서브플롯 생성
        fig = go.Figure()
        
        # 가격 차트 (주축)
        fig.add_trace(go.Scatter(
            x=unified_data['dates'],
            y=unified_data['prices'],
            mode='lines',
            name='가격',
            yaxis='y',
            line=dict(color='#1E88E5', width=2)
        ))
        
        # 언급량 막대 (보조축)
        fig.add_trace(go.Bar(
            x=unified_data['dates'],
            y=unified_data['mention_counts'],
            name='언급량',
            yaxis='y2',
            marker_color='#FF9800',
            opacity=0.7
        ))
        
        # 센티먼트 점수 (제2보조축)
        fig.add_trace(go.Scatter(
            x=unified_data['dates'],
            y=unified_data['sentiment_scores'],
            mode='lines+markers',
            name='센티먼트',
            yaxis='y3',
            line=dict(color='#4CAF50', width=2),
            marker=dict(size=4)
        ))
        
        # 레이아웃 업데이트
        fig.update_layout(
            title=f"{symbol} 통합 분석 차트",
            xaxis=dict(title="날짜"),
            yaxis=dict(
                title="가격 ($)",
                titlefont=dict(color="#1E88E5"),
                tickfont=dict(color="#1E88E5")
            ),
            yaxis2=dict(
                title="언급량",
                titlefont=dict(color="#FF9800"),
                tickfont=dict(color="#FF9800"),
                anchor="x",
                overlaying="y",
                side="right"
            ),
            yaxis3=dict(
                title="센티먼트 점수",
                titlefont=dict(color="#4CAF50"),
                tickfont=dict(color="#4CAF50"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.95
            ),
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 상관관계 분석
        st.subheader("📊 상관관계 분석")
        
        correlation = self._calculate_correlation(
            unified_data['prices'],
            unified_data['sentiment_scores']
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "가격-센티먼트 상관계수",
                f"{correlation:.3f}",
                delta=f"{correlation*100:.1f}%" if correlation > 0 else f"{correlation*100:.1f}%"
            )
        
        with col2:
            # 상관관계 해석
            if correlation > 0.5:
                interpretation = "강한 양의 상관관계"
                color = "green"
            elif correlation > 0.2:
                interpretation = "약한 양의 상관관계"
                color = "lightgreen"
            elif correlation > -0.2:
                interpretation = "거의 무상관"
                color = "orange"
            elif correlation > -0.5:
                interpretation = "약한 음의 상관관계"
                color = "lightcoral"
            else:
                interpretation = "강한 음의 상관관계"
                color = "red"
            
            st.markdown(f"<span style='color: {color}'>**{interpretation}**</span>", 
                       unsafe_allow_html=True)
    
    def _get_simulated_price_data(self, symbol: str, period: str) -> Dict:
        """시뮬레이션된 가격 데이터"""
        # 실제 구현에서는 API 호출로 데이터 가져오기
        import random
        from datetime import datetime, timedelta
        
        # 기간에 따른 날짜 수 계산
        if period == "1일":
            days = 1
        elif period == "1주":
            days = 7
        elif period == "1개월":
            days = 30
        elif period == "3개월":
            days = 90
        elif period == "6개월":
            days = 180
        else:  # 1년
            days = 365
        
        # 시뮬레이션된 데이터 생성
        base_price = 100.0 + random.uniform(-50, 200)
        dates = []
        prices = []
        opens = []
        highs = []
        lows = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            price_change = random.uniform(-5, 5)
            price = base_price + price_change
            
            dates.append(date)
            prices.append(price)
            opens.append(price + random.uniform(-2, 2))
            highs.append(price + random.uniform(0, 5))
            lows.append(price + random.uniform(-5, 0))
            
            base_price = price
        
        return {
            'dates': dates,
            'prices': prices,
            'opens': opens,
            'highs': highs,
            'lows': lows
        }
    
    def _get_simulated_sentiment_data(self, symbol: str) -> Dict:
        """시뮬레이션된 센티먼트 데이터"""
        # 실제 구현에서는 API 호출로 데이터 가져오기
        import random
        from datetime import datetime, timedelta
        
        dates = []
        scores = []
        mention_counts = []
        
        for i in range(30):  # 30일 데이터
            date = datetime.now() - timedelta(days=30-i)
            score = random.uniform(-100, 100)
            count = random.randint(10, 1000)
            
            dates.append(date)
            scores.append(score)
            mention_counts.append(count)
        
        return {
            'dates': dates,
            'scores': scores,
            'mention_counts': mention_counts
        }
    
    def _get_simulated_unified_data(self, symbol: str) -> Dict:
        """시뮬레이션된 통합 데이터"""
        # 실제 구현에서는 API 호출로 데이터 가져오기
        price_data = self._get_simulated_price_data(symbol, "1개월")
        sentiment_data = self._get_simulated_sentiment_data(symbol)
        
        # 데이터 정렬 및 병합
        return {
            'dates': price_data['dates'],
            'prices': price_data['prices'],
            'mention_counts': sentiment_data['mention_counts'][:len(price_data['dates'])],
            'sentiment_scores': sentiment_data['scores'][:len(price_data['dates'])]
        }
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """상관계수 계산"""
        import numpy as np
        
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        return np.corrcoef(x, y)[0, 1]
```

## 5. 사용자 인터랙션 디자인

### 5.1 상호작용 패턴

```python
class InteractionPatterns:
    """사용자 상호작용 패턴"""
    
    @staticmethod
    def create_stock_card_interactions():
        """주식 카드 상호작용 패턴"""
        return {
            "hover": {
                "effect": "elevation",
                "duration": "200ms",
                "shadow": "0 4px 8px rgba(0, 0, 0, 0.12)"
            },
            "click": {
                "feedback": "ripple",
                "duration": "300ms"
            },
            "drag": {
                "cursor": "grab",
                "feedback": "visual"
            }
        }
    
    @staticmethod
    def create_chart_interactions():
        """차트 상호작용 패턴"""
        return {
            "zoom": {
                "enabled": True,
                "mode": "xy",
                "sensitivity": "medium"
            },
            "pan": {
                "enabled": True,
                "constraint": "horizontal"
            },
            "crosshair": {
                "enabled": True,
                "mode": "vertical",
                "snap": True
            },
            "tooltip": {
                "trigger": "hover",
                "delay": "100ms",
                "format": "detailed"
            }
        }
    
    @staticmethod
    def create_filter_interactions():
        """필터 상호작용 패턴"""
        return {
            "multi_select": {
                "behavior": "checkbox",
                "search_enabled": True,
                "select_all": True
            },
            "range_slider": {
                "snap": True,
                "step": "auto",
                "live_update": True
            },
            "date_range": {
                "presets": ["1일", "1주", "1개월", "YTD"],
                "custom_range": True
            }
        }
```

### 5.2 애니메이션 및 전환 효과

```css
/* 애니메이션 정의 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
    from { transform: translateX(-100%); }
    to { transform: translateX(0); }
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}

/* 컴포넌트 애니메이션 클래스 */
.fade-in {
    animation: fadeIn 0.3s ease-out;
}

.slide-in {
    animation: slideIn 0.3s ease-out;
}

.pulse {
    animation: pulse 2s infinite;
}

.loading-shimmer {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 1000px 100%;
    animation: shimmer 2s infinite;
}

/* 상태 전환 */
.card {
    transition: all 0.2s ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.card:active {
    transform: translateY(0);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.button {
    transition: all 0.2s ease;
}

.button:hover {
    background-color: var(--primary-color);
    color: white;
}

.button:active {
    transform: scale(0.98);
}
```

## 6. 접근성 설계

### 6.1 키보드 내비게이션

```python
class AccessibilityFeatures:
    """접근성 기능"""
    
    @staticmethod
    def create_keyboard_navigation():
        """키보드 내비게이션 기능"""
        return {
            "tab_navigation": {
                "enabled": True,
                "focus_visible": True,
                "skip_links": True
            },
            "arrow_keys": {
                "enabled": True,
                "wrap_around": True
            },
            "shortcuts": {
                "search": "Ctrl+K",
                "refresh": "F5",
                "help": "?",
                "settings": "Ctrl+,"
            }
        }
    
    @staticmethod
    def create_screen_reader_support():
        """스크린 리더 지원"""
        return {
            "aria_labels": {
                "search_input": "주식, 센티먼트, 트렌드 검색",
                "search_button": "검색 실행",
                "filter_toggle": "고급 필터 토글",
                "chart_tabs": "차트 탭 내비게이션",
                "stock_card": "주식 정보 카드"
            },
            "live_regions": {
                "search_results": "검색 결과 영역",
                "chart_display": "차트 표시 영역",
                "sentiment_analysis": "센티먼트 분석 영역"
            },
            "descriptions": {
                "price_change": "가격 변동률",
                "sentiment_score": "센티먼트 점수",
                "trending_status": "트렌딩 상태"
            }
        }
    
    @staticmethod
    def create_visual_accessibility():
        """시각적 접근성 기능"""
        return {
            "high_contrast": {
                "enabled": True,
                "toggle": "Alt+H"
            },
            "font_scaling": {
                "enabled": True,
                "levels": ["small", "medium", "large", "extra-large"],
                "shortcuts": ["Ctrl+-", "Ctrl+0", "Ctrl+="]
            },
            "focus_indicators": {
                "visible": True,
                "thick": "2px",
                "color": "#1E88E5"
            },
            "color_blind_friendly": {
                "enabled": True,
                "palette": "deuteranopia"
            }
        }
```

## 7. 구현 계획

### 7.1 Phase 1: 기본 컴포넌트 구현 (1주일)

#### 7.1.1 통합 검색 컴포넌트
- UnifiedSearchComponent 클래스 구현
- 자동완성 기능 구현
- 고급 필터링 기능 구현

#### 7.1.2 기본 UI 컴포넌트
- 주식 정보 카드 컴포넌트
- 필터 컴포넌트
- 탭 내비게이션 컴포넌트

### 7.2 Phase 2: 차트 컴포넌트 구현 (1주일)

#### 7.2.1 통합 차트 컴포넌트
- UnifiedChartComponent 클래스 구현
- 가격 차트 기능 구현
- 센티먼트 차트 기능 구현

#### 7.2.2 고급 차트 기능
- 통합 차트 기능 구현
- 상관관계 분석 기능 구현
- 인터랙티브 차트 기능 구현

### 7.3 Phase 3: 사용자 경험 개선 (1주일)

#### 7.3.1 상호작용 및 애니메이션
- 상호작용 패턴 구현
- 애니메이션 및 전환 효과 구현
- 로딩 상태 및 피드백 구현

#### 7.3.2 접근성 기능
- 키보드 내비게이션 구현
- 스크린 리더 지원 구현
- 시각적 접근성 기능 구현

### 7.4 Phase 4: 반응형 디자인 및 최적화 (1주일)

#### 7.4.1 반응형 레이아웃
- 모바일 레이아웃 구현
- 태블릿 레이아웃 구현
- 데스크톱 레이아웃 구현

#### 7.4.2 성능 최적화
- 렌더링 성능 최적화
- 메모리 사용량 최적화
- 네트워크 요청 최적화

## 8. 기술적 고려사항

### 8.1 Streamlit 제약사항 해결
1. **상태 관리**: Session State를 활용한 상태 관리
2. **컴포넌트 재사용**: 모듈화된 컴포넌트 구조
3. **비동기 처리**: asyncio를 활용한 비동기 데이터 처리
4. **캐싱**: 데이터 캐싱으로 성능 최적화

### 8.2 성능 최적화
1. **지연 로딩**: 대용량 데이터 지연 로딩
2. **가상화**: 긴 목록 가상화
3. **메모이제이션**: 불필요한 렌더링 방지
4. **캐싱**: 컴포넌트 상태 캐싱

### 8.3 브라우저 호환성
1. **모던 브라우저**: 최신 브라우저 지원
2. **레거시 브라우저**: IE11 이상 지원 (필요시)
3. **모바일 브라우저**: iOS Safari, Android Chrome 지원
4. **데스크톱 브라우저**: Chrome, Firefox, Safari, Edge 지원

## 9. 성공 지표

### 9.1 기술적 지표
- 페이지 로드 시간: 2초 이하
- 인터랙션 응답 시간: 200ms 이하
- 모바일 호환성: 100% (주요 기능)
- 접근성 준수: WCAG 2.1 AA 준수

### 9.2 사용자 경험 지표
- 사용자 만족도: 4.5/5.0 이상
- 작업 완료율: 85% 이상
- 오류율: 1% 이하
- 학습 곡선: 30분 내 주요 기능 숙지

이 통합 대시보드 UI/UX 설계를 통해 Enhanced Stock Search와 Social Sentiment Tracker를 자연스럽게 통합하고, 사용자에게 직관적이고 효율적인 인터페이스를 제공할 수 있습니다.