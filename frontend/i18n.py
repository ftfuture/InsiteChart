"""
국제화(i18n) 지원 모듈

다국어 지원을 위한 번역 기능과 로케일 관리를 제공합니다.
"""

import streamlit as st
from typing import Dict, Any, Optional
import json
import os

class I18nManager:
    """국제화 관리자 클래스"""
    
    def __init__(self):
        self.current_locale = "ko"  # 기본 언어: 한국어
        self.supported_locales = {
            "ko": "한국어",
            "en": "English",
            "ja": "日本語",
            "zh": "中文"
        }
        
        # 세션 상태 초기화
        if 'locale_settings' not in st.session_state:
            st.session_state.locale_settings = {
                'locale': self.current_locale,
                'auto_detect': True
            }
        
        # 번역 데이터 로드
        self.translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """번역 데이터 로드"""
        return {
            "ko": {
                "app_title": "인사이트차트 - 전문 주식 분석",
                "stock_search": "주식 검색",
                "stock_search_placeholder": "주식 이름, 심볼 또는 섹터로 검색",
                "ticker_input": "주식 심볼 입력",
                "ticker_placeholder": "검색할 주식의 심볼을 입력",
                "period_selection": "기간 선택",
                "chart_analysis": "차트 분석",
                "compare_stocks": "주식 비교",
                "market_overview": "시장 개요",
                "trending_stocks": "인기 주식",
                "market_sentiment": "시장 감성",
                "market_indices": "시장 지수",
                "system_info": "시스템 정보",
                "watchlist": "감시 목록",
                "add_to_watchlist": "감시 목록에 추가",
                "remove_from_watchlist": "감시 목록에서 제거",
                "high_price": "고가",
                "low_price": "저가",
                "avg_volume": "평균 거래량",
                "volatility": "변동성",
                "day_change": "일일 변동",
                "52w_high": "52주 최고가",
                "52w_low": "52주 최저가",
                "eps": "주당순이익",
                "dividend": "배당수익률",
                "performance_comparison": "성과 비교",
                "normalized_returns": "정규화된 수익률",
                "timeframe_1m": "1개월",
                "timeframe_3m": "3개월",
                "timeframe_6m": "6개월",
                "timeframe_1y": "1년",
                "timeframe_5y": "5년",
                "accessibility": "접근성",
                "high_contrast": "고대비 모드",
                "font_size": "폰트 크기",
                "small": "작게",
                "medium": "보통",
                "large": "크게",
                "xlarge": "매우 크게",
                "keyboard_navigation": "키보드 내비게이션",
                "screen_reader": "스크린 리더 최적화",
                "api_test": "API 테스트",
                "select_endpoint": "엔드포인트 선택",
                "test_endpoint": "엔드포인트 테스트",
                "connected": "연결됨",
                "connection_failed": "연결 실패",
                "search_results": "검색 결과",
                "no_results": "결과 없음",
                "unable_to_fetch": "데이터를 가져올 수 없음",
                "error_occurred": "오류가 발생했습니다",
                "keyboard_shortcuts": "키보드 단축키",
                "page_reload": "페이지 새로고침",
                "search_navigation": "검색으로 이동",
                "chart_navigation": "차트로 이동",
                "accessibility_settings": "접근성 설정",
                "apply_settings": "설정 적용",
                "settings_applied": "접근성 설정이 적용되었습니다.",
                "main_content": "메인 콘텐츠로 바로가기",
                "user_feedback": "사용자 피드백",
                "submit_feedback": "피드백 제출",
                "feedback_type": "피드백 유형",
                "feedback_description": "피드백 내용",
                "bug_report": "버그 보고",
                "feature_request": "기능 요청",
                "general_feedback": "일반 피드백",
                "submit": "제출",
                "thank_you": "감사합니다",
                "feedback_received": "피드백이 접수되었습니다.",
                "feedback_center": "피드백 센터",
                "feedback_history": "피드백 내역",
                "activity_summary": "활동 요약",
                "category": "카테고리",
                "priority": "우선순위",
                "low_priority": "낮음",
                "medium_priority": "보통",
                "high_priority": "높음",
                "critical_priority": "긴급",
                "satisfaction_rating": "만족도 평가",
                "feedback_title": "피드백 제목",
                "my_feedback": "내 피드백",
                "no_feedback": "제출된 피드백이 없습니다",
                "total_activities": "총 활동 수",
                "most_used_feature": "가장 많이 사용한 기능",
                "activity_by_type": "활동 유형별",
                "most_used_features": "가장 많이 사용한 기능들"
            },
            "en": {
                "app_title": "InsiteChart - Professional Stock Analysis",
                "stock_search": "Stock Search",
                "stock_search_placeholder": "Search by name, symbol, sector...",
                "ticker_input": "Stock Symbol Input",
                "ticker_placeholder": "Enter symbol to search",
                "period_selection": "Time Period Selection",
                "chart_analysis": "Chart Analysis",
                "compare_stocks": "Compare Stocks",
                "market_overview": "Market Overview",
                "trending_stocks": "Trending Stocks",
                "market_sentiment": "Market Sentiment",
                "market_indices": "Market Indices",
                "system_info": "System Information",
                "watchlist": "Watchlist",
                "add_to_watchlist": "Add to Watchlist",
                "remove_from_watchlist": "Remove from Watchlist",
                "high_price": "High Price",
                "low_price": "Low Price",
                "avg_volume": "Average Volume",
                "volatility": "Volatility",
                "day_change": "Day Change",
                "52w_high": "52W High",
                "52w_low": "52W Low",
                "eps": "EPS",
                "dividend": "Dividend",
                "performance_comparison": "Performance Comparison",
                "normalized_returns": "Normalized Returns",
                "timeframe_1m": "1 Month",
                "timeframe_3m": "3 Months",
                "timeframe_6m": "6 Months",
                "timeframe_1y": "1 Year",
                "timeframe_5y": "5 Years",
                "accessibility": "Accessibility",
                "high_contrast": "High Contrast Mode",
                "font_size": "Font Size",
                "small": "Small",
                "medium": "Medium",
                "large": "Large",
                "xlarge": "Extra Large",
                "keyboard_navigation": "Keyboard Navigation",
                "screen_reader": "Screen Reader Optimization",
                "api_test": "API Test",
                "select_endpoint": "Select Endpoint",
                "test_endpoint": "Test Endpoint",
                "connected": "Connected",
                "connection_failed": "Connection Failed",
                "search_results": "Search Results",
                "no_results": "No Results",
                "unable_to_fetch": "Unable to fetch data",
                "error_occurred": "An error occurred",
                "keyboard_shortcuts": "Keyboard Shortcuts",
                "page_reload": "Reload Page",
                "search_navigation": "Navigate to Search",
                "chart_navigation": "Navigate to Chart",
                "accessibility_settings": "Accessibility Settings",
                "apply_settings": "Apply Settings",
                "settings_applied": "Accessibility settings applied.",
                "main_content": "Skip to Main Content",
                "user_feedback": "User Feedback",
                "submit_feedback": "Submit Feedback",
                "feedback_type": "Feedback Type",
                "feedback_description": "Feedback Description",
                "bug_report": "Bug Report",
                "feature_request": "Feature Request",
                "general_feedback": "General Feedback",
                "submit": "Submit",
                "thank_you": "Thank You",
                "feedback_received": "Feedback received.",
                "feedback_center": "Feedback Center",
                "feedback_history": "Feedback History",
                "activity_summary": "Activity Summary",
                "category": "Category",
                "priority": "Priority",
                "low_priority": "Low",
                "medium_priority": "Medium",
                "high_priority": "High",
                "critical_priority": "Critical",
                "satisfaction_rating": "Satisfaction Rating",
                "feedback_title": "Feedback Title",
                "my_feedback": "My Feedback",
                "no_feedback": "No feedback submitted yet",
                "total_activities": "Total Activities",
                "most_used_feature": "Most Used Feature",
                "activity_by_type": "Activity by Type",
                "most_used_features": "Most Used Features"
            },
            "ja": {
                "app_title": "インサイトチャート - プロの株価分析",
                "stock_search": "株価検索",
                "stock_search_placeholder": "名前、シンボル、セクターで検索",
                "ticker_input": "株価シンボル入力",
                "ticker_placeholder": "検索する株価のシンボルを入力",
                "period_selection": "期間選択",
                "chart_analysis": "チャート分析",
                "compare_stocks": "株価比較",
                "market_overview": "市場概要",
                "trending_stocks": "トレンド株価",
                "market_sentiment": "市場センチメント",
                "market_indices": "市場指数",
                "system_info": "システム情報",
                "watchlist": "ウォッチリスト",
                "add_to_watchlist": "ウォッチリストに追加",
                "remove_from_watchlist": "ウォッチリストから削除",
                "high_price": "高値",
                "low_price": "安値",
                "avg_volume": "平均出来高",
                "volatility": "ボラティリティ",
                "day_change": "日次変動",
                "52w_high": "52週高値",
                "52w_low": "52週安値",
                "eps": "EPS",
                "dividend": "配当",
                "performance_comparison": "パフォーマンス比較",
                "normalized_returns": "正規化されたリターン",
                "timeframe_1m": "1ヶ月",
                "timeframe_3m": "3ヶ月",
                "timeframe_6m": "6ヶ月",
                "timeframe_1y": "1年",
                "timeframe_5y": "5年",
                "accessibility": "アクセシビリティ",
                "high_contrast": "ハイコントラストモード",
                "font_size": "フォントサイズ",
                "small": "小",
                "medium": "中",
                "large": "大",
                "xlarge": "特大",
                "keyboard_navigation": "キーボードナビゲーション",
                "screen_reader": "スクリーンリーダー最適化",
                "api_test": "APIテスト",
                "select_endpoint": "エンドポイント選択",
                "test_endpoint": "エンドポイントテスト",
                "connected": "接続済み",
                "connection_failed": "接続失敗",
                "search_results": "検索結果",
                "no_results": "結果なし",
                "unable_to_fetch": "データを取得できません",
                "error_occurred": "エラーが発生しました",
                "keyboard_shortcuts": "キーボードショートカット",
                "page_reload": "ページを再読み込み",
                "search_navigation": "検索に移動",
                "chart_navigation": "チャートに移動",
                "accessibility_settings": "アクセシビリティ設定",
                "apply_settings": "設定を適用",
                "settings_applied": "アクセシビリティ設定が適用されました。",
                "main_content": "メインコンテンツに移動",
                "user_feedback": "ユーザーフィードバック",
                "submit_feedback": "フィードバックを提出",
                "feedback_type": "フィードバックタイプ",
                "feedback_description": "フィードバック説明",
                "bug_report": "バグレポート",
                "feature_request": "機能リクエスト",
                "general_feedback": "一般フィードバック",
                "submit": "提出",
                "thank_you": "ありがとうございます",
                "feedback_received": "フィードバックを受信しました。",
                "feedback_center": "フィードバックセンター",
                "feedback_history": "フィードバック履歴",
                "activity_summary": "アクティビティ概要",
                "category": "カテゴリ",
                "priority": "優先度",
                "low_priority": "低",
                "medium_priority": "中",
                "high_priority": "高",
                "critical_priority": "緊急",
                "satisfaction_rating": "満足度評価",
                "feedback_title": "フィードバックタイトル",
                "my_feedback": "マイフィードバック",
                "no_feedback": "フィードバックがまだありません",
                "total_activities": "総アクティビティ数",
                "most_used_feature": "最も使用された機能",
                "activity_by_type": "タイプ別アクティビティ",
                "most_used_features": "最も使用された機能"
            },
            "zh": {
                "app_title": "图表 - 专业股票分析",
                "stock_search": "股票搜索",
                "stock_search_placeholder": "按名称、代码或行业搜索",
                "ticker_input": "股票代码输入",
                "ticker_placeholder": "输入要搜索的股票代码",
                "period_selection": "时间段选择",
                "chart_analysis": "图表分析",
                "compare_stocks": "比较股票",
                "market_overview": "市场概览",
                "trending_stocks": "热门股票",
                "market_sentiment": "市场情绪",
                "market_indices": "市场指数",
                "system_info": "系统信息",
                "watchlist": "关注列表",
                "add_to_watchlist": "添加到关注列表",
                "remove_from_watchlist": "从关注列表移除",
                "high_price": "最高价",
                "low_price": "最低价",
                "avg_volume": "平均成交量",
                "volatility": "波动性",
                "day_change": "日变化",
                "52w_high": "52周最高价",
                "52w_low": "52周最低价",
                "eps": "每股收益",
                "dividend": "股息",
                "performance_comparison": "性能比较",
                "normalized_returns": "标准化回报",
                "timeframe_1m": "1个月",
                "timeframe_3m": "3个月",
                "timeframe_6m": "6个月",
                "timeframe_1y": "1年",
                "timeframe_5y": "5年",
                "accessibility": "可访问性",
                "high_contrast": "高对比度模式",
                "font_size": "字体大小",
                "small": "小",
                "medium": "中",
                "large": "大",
                "xlarge": "特大",
                "keyboard_navigation": "键盘导航",
                "screen_reader": "屏幕阅读器优化",
                "api_test": "API测试",
                "select_endpoint": "选择端点",
                "test_endpoint": "测试端点",
                "connected": "已连接",
                "connection_failed": "连接失败",
                "search_results": "搜索结果",
                "no_results": "无结果",
                "unable_to_fetch": "无法获取数据",
                "error_occurred": "发生错误",
                "keyboard_shortcuts": "键盘快捷键",
                "page_reload": "重新加载页面",
                "search_navigation": "导航到搜索",
                "chart_navigation": "导航到图表",
                "accessibility_settings": "可访问性设置",
                "apply_settings": "应用设置",
                "settings_applied": "可访问性设置已应用。",
                "main_content": "跳转到主要内容",
                "user_feedback": "用户反馈",
                "submit_feedback": "提交反馈",
                "feedback_type": "反馈类型",
                "feedback_description": "反馈描述",
                "bug_report": "错误报告",
                "feature_request": "功能请求",
                "general_feedback": "一般反馈",
                "submit": "提交",
                "thank_you": "谢谢",
                "feedback_received": "反馈已收到。",
                "feedback_center": "反馈中心",
                "feedback_history": "反馈历史",
                "activity_summary": "活动摘要",
                "category": "类别",
                "priority": "优先级",
                "low_priority": "低",
                "medium_priority": "中",
                "high_priority": "高",
                "critical_priority": "紧急",
                "satisfaction_rating": "满意度评分",
                "feedback_title": "反馈标题",
                "my_feedback": "我的反馈",
                "no_feedback": "暂无反馈",
                "total_activities": "总活动数",
                "most_used_feature": "最常用功能",
                "activity_by_type": "按类型分组的活动",
                "most_used_features": "最常用功能"
            }
        }
    
    def get_text(self, key: str, **kwargs) -> str:
        """번역된 텍스트 반환"""
        locale = st.session_state.locale_settings.get('locale', self.current_locale)
        return self.translations.get(locale, {}).get(key, key)
    
    def format_currency(self, value: Any, decimals: int = 2) -> str:
        """통화 형식으로 번역"""
        locale = st.session_state.locale_settings.get('locale', self.current_locale)
        
        if isinstance(value, (int, float)) and value is not None:
            if locale == "ko":
                return f"{value:,.0f}원"
            elif locale == "ja":
                return f"¥{value:,.0f}"
            elif locale == "zh":
                return f"¥{value:,.0f}"
            else:  # 기본: 영어
                return f"${value:,.{decimals}f}"
        return self.get_text("no_results")
    
    def format_number(self, value: Any, decimals: int = 2) -> str:
        """숫자 형식으로 번역"""
        locale = st.session_state.locale_settings.get('locale', self.current_locale)
        
        if isinstance(value, (int, float)) and value is not None:
            if locale == "ko":
                return f"{value:,.0f}"
            elif locale == "ja":
                return f"{value:,.0f}"
            elif locale == "zh":
                return f"{value:,.0f}"
            else:  # 기본: 영어
                return f"{value:,.{decimals}f}"
        return self.get_text("no_results")
    
    def format_percentage(self, value: Any, decimals: int = 2) -> str:
        """백분율 형식으로 번역"""
        locale = st.session_state.locale_settings.get('locale', self.current_locale)
        
        if isinstance(value, (int, float)) and value is not None:
            formatted_value = value * 100
            if locale == "ko":
                return f"{formatted_value:.{decimals}f}%"
            elif locale == "ja":
                return f"{formatted_value:.{decimals}f}%"
            elif locale == "zh":
                return f"{formatted_value:.{decimals}f}%"
            else:  # 기본: 영어
                return f"{formatted_value:.{decimals}f}%"
        return self.get_text("no_results")
    
    def render_locale_selector(self) -> None:
        """언어 선택기 렌더링"""
        with st.expander("🌍 Language / 语言 / 言語", expanded=False):
            # 현재 언어 표시
            current_locale_name = self.supported_locales.get(
                st.session_state.locale_settings.get('locale', self.current_locale),
                self.current_locale
            )
            st.write(f"**{self.get_text('current_language')}:** {current_locale_name}")
            
            # 언어 선택
            selected_locale = st.selectbox(
                self.get_text("select_language"),
                options=list(self.supported_locales.values()),
                index=list(self.supported_locales.keys()).index(
                    st.session_state.locale_settings.get('locale', self.current_locale)
                ),
                format_func=lambda x: x,
                key="locale_selector"
            )
            
            # 자동 감지 옵션
            auto_detect = st.checkbox(
                self.get_text("auto_detect_language"),
                value=st.session_state.locale_settings.get('auto_detect', True),
                key="auto_detect"
            )
            
            # 적용 버튼
            if st.button(self.get_text("apply_language"), key="apply_locale"):
                locale_code = list(self.supported_locales.keys())[selected_locale]
                st.session_state.locale_settings = {
                    'locale': locale_code,
                    'auto_detect': auto_detect
                }
                st.success(self.get_text("language_applied"))
                st.rerun()
    
    def get_date_format(self) -> str:
        """날짜 형식 반환"""
        locale = st.session_state.locale_settings.get('locale', self.current_locale)
        
        date_formats = {
            "ko": "%Y년 %m월 %d일",
            "en": "%Y-%m-%d",
            "ja": "%Y年%m月%d日",
            "zh": "%Y年%m月%d日"
        }
        
        return date_formats.get(locale, "%Y-%m-%d")
    
    def get_time_format(self) -> str:
        """시간 형식 반환"""
        locale = st.session_state.locale_settings.get('locale', self.current_locale)
        
        time_formats = {
            "ko": "%H시 %M분",
            "en": "%I:%M %p",
            "ja": "%H時%M分",
            "zh": "%H时%M分"
        }
        
        return time_formats.get(locale, "%I:%M %p")

# 전역 i18n 관리자 인스턴스
i18n_manager = I18nManager()