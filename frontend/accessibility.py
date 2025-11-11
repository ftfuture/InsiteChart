"""
접근성 기능 모듈

WCAG 2.1 표준을 준수하는 접근성 기능들을 제공합니다.
"""

import streamlit as st
from typing import Dict, Any, Optional

class AccessibilityManager:
    """접근성 관리자 클래스"""
    
    def __init__(self):
        self.high_contrast = False
        self.keyboard_nav = False
        self.screen_reader = False
        self.focus_visible = True
        self.font_size = "medium"
        
        # 세션 상태 초기화
        if 'accessibility_settings' not in st.session_state:
            st.session_state.accessibility_settings = {
                'high_contrast': False,
                'keyboard_nav': False,
                'screen_reader': True,
                'focus_visible': True,
                'font_size': 'medium'
            }
    
    def get_accessibility_css(self) -> str:
        """접근성 CSS 생성"""
        settings = st.session_state.accessibility_settings
        
        css = """
        /* 기본 접근성 스타일 */
        .accessible-focus {
            outline: 2px solid #FF6B35 !important;
            outline-offset: 2px !important;
        }
        
        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            background: #000;
            color: #fff;
            padding: 8px;
            text-decoration: none;
            border-radius: 0 0 4px 4px;
            z-index: 1000;
        }
        
        .skip-link:focus {
            top: 0;
        }
        
        /* 키보드 내비게이션 */
        .keyboard-nav {
            position: relative;
        }
        
        .keyboard-nav:focus {
            outline: 3px solid #0056b3;
            outline-offset: 2px;
        }
        
        /* 고대비 모드 */
        """
        
        if settings.get('high_contrast', False):
            css += """
            .high-contrast {
                filter: contrast(1.5) !important;
                background: #000 !important;
                color: #fff !important;
            }
            
            .high-contrast .stButton > button {
                background: #000 !important;
                color: #fff !important;
                border: 2px solid #fff !important;
            }
            
            .high-contrast .stTextInput > input {
                background: #000 !important;
                color: #fff !important;
                border: 1px solid #fff !important;
            }
            """
        
        # 폰트 크기 조정
        font_sizes = {
            'small': '14px',
            'medium': '16px',
            'large': '18px',
            'xlarge': '20px'
        }
        
        css += f"""
        body {{
            font-size: {font_sizes.get(settings.get('font_size', 'medium'), '16px')} !important;
            line-height: 1.5 !important;
        }}
        
        .accessible-text {{
            font-size: {font_sizes.get(settings.get('font_size', 'medium'), '16px')} !important;
        }}
        """
        
        return css
    
    def render_skip_links(self) -> None:
        """스킵 링크 렌더링"""
        st.markdown("""
        <a href="#main-content" class="skip-link">메인 콘텐츠로 바로가기</a>
        <a href="#search-section" class="skip-link">검색으로 바로가기</a>
        <a href="#chart-section" class="skip-link">차트로 바로가기</a>
        """, unsafe_allow_html=True)
    
    def render_accessibility_controls(self) -> None:
        """접근성 컨트롤 렌더링"""
        with st.expander("♿ 접근성 설정", expanded=False):
            # 고대비 모드
            high_contrast = st.checkbox(
                "🔆 고대비 모드",
                value=st.session_state.accessibility_settings.get('high_contrast', False),
                key="access_high_contrast"
            )
            
            # 폰트 크기
            font_size = st.selectbox(
                "📝 폰트 크기",
                options=['작게', '보통', '크게', '매우 크게'],
                index=['작게', '보통', '크게', '매우 크게'].index(
                    ['small', 'medium', 'large', 'xlarge'].index(
                        st.session_state.accessibility_settings.get('font_size', 'medium')
                    )
                ) if st.session_state.accessibility_settings.get('font_size', 'medium') in ['small', 'medium', 'large', 'xlarge'] else 1
                ],
                format_func=lambda x: {
                    'small': 'small',
                    'medium': 'medium', 
                    'large': 'large',
                    'xlarge': 'xlarge'
                }.get(x, 'medium'),
                key="access_font_size"
            )
            
            # 키보드 내비게이션
            keyboard_nav = st.checkbox(
                "⌨️ 키보드 내비게이션 모드",
                value=st.session_state.accessibility_settings.get('keyboard_nav', False),
                key="access_keyboard_nav"
            )
            
            # 스크린 리더 최적화
            screen_reader = st.checkbox(
                "🔊 스크린 리더 최적화",
                value=st.session_state.accessibility_settings.get('screen_reader', True),
                key="access_screen_reader"
            )
            
            # 설정 적용 버튼
            if st.button("적용", key="apply_accessibility"):
                self._update_settings(high_contrast, font_size, keyboard_nav, screen_reader)
                st.success("접근성 설정이 적용되었습니다.")
                st.rerun()
    
    def _update_settings(self, high_contrast: bool, font_size: str, 
                     keyboard_nav: bool, screen_reader: bool) -> None:
        """접근성 설정 업데이트"""
        st.session_state.accessibility_settings = {
            'high_contrast': high_contrast,
            'font_size': font_size,
            'keyboard_nav': keyboard_nav,
            'screen_reader': screen_reader,
            'focus_visible': True
        }
    
    def get_aria_labels(self) -> Dict[str, str]:
        """ARIA 레이블 반환"""
        return {
            'search_label': '주식 검색 입력',
            'search_description': '주식 이름, 심볼 또는 섹터로 검색',
            'ticker_label': '주식 심볼 입력',
            'ticker_description': '검색할 주식의 심볼을 입력',
            'period_label': '기간 선택',
            'period_description': '차트에 표시할 기간을 선택',
            'chart_label': '주식 가격 차트',
            'chart_description': '선택된 주식의 가격 변동을 보여주는 차트',
            'compare_label': '주식 비교',
            'compare_description': '여러 주식의 성과를 비교 분석',
            'watchlist_label': '감시 목록',
            'watchlist_description': '관심 있는 주식 목록'
        }
    
    def render_accessible_input(self, label: str, help_text: str = "", 
                          key: str = "", value: Any = None, **kwargs) -> Any:
        """접근성이 개선된 입력 컴포넌트"""
        aria_labels = self.get_aria_labels()
        
        # ARIA 레이블 추가
        aria_attrs = {
            'aria-label': aria_labels.get(f"{key}_label", label),
            'aria-describedby': f"{key}_help" if help_text else None,
            'role': 'textbox' if 'input' in kwargs.get('type', '') else 'combobox'
        }
        
        # 키보드 내비게이션 모드 확인
        if st.session_state.accessibility_settings.get('keyboard_nav', False):
            kwargs['tab_index'] = kwargs.get('tab_index', 0)
        
        return st.text_input(
            label=label,
            help=help_text,
            value=value,
            key=key,
            **kwargs
        )
    
    def render_accessible_button(self, label: str, help_text: str = "", 
                           key: str = "", **kwargs) -> bool:
        """접근성이 개선된 버튼 컴포넌트"""
        aria_labels = self.get_aria_labels()
        
        # ARIA 레이블 추가
        if 'aria_attrs' not in kwargs:
            kwargs['aria_attrs'] = {}
        
        kwargs['aria_attrs'].update({
            'aria-label': aria_labels.get(f"{key}_label", label),
            'aria-describedby': f"{key}_help" if help_text else None,
            'role': 'button'
        })
        
        # 키보드 내비게이션 모드 확인
        if st.session_state.accessibility_settings.get('keyboard_nav', False):
            kwargs['tab_index'] = kwargs.get('tab_index', 0)
        
        return st.button(label, help=help_text, key=key, **kwargs)
    
    def add_focus_management(self) -> None:
        """포커스 관리 스크립트 추가"""
        if st.session_state.accessibility_settings.get('focus_visible', True):
            focus_script = """
            <script>
            // 포커스 관리
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Tab') {
                    const focusableElements = document.querySelectorAll(
                        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    );
                    const firstElement = focusableElements[0];
                    const lastElement = focusableElements[focusableElements.length - 1];
                    
                    if (e.shiftKey) {
                        if (document.activeElement === firstElement) {
                            lastElement.focus();
                            e.preventDefault();
                        }
                    } else {
                        if (document.activeElement === lastElement) {
                            firstElement.focus();
                            e.preventDefault();
                        }
                    }
                }
            });
            
            // 포커스 가시화
            const style = document.createElement('style');
            style.textContent = `
                .accessible-focus {
                    outline: 2px solid #FF6B35 !important;
                    outline-offset: 2px !important;
                    box-shadow: 0 0 5px rgba(255, 107, 53, 0.5) !important;
                }
            `;
            document.head.appendChild(style);
            </script>
            """
            st.components.v1.html(focus_script, height=0)
    
    def render_keyboard_shortcuts(self) -> None:
        """키보드 단축키 안내 렌더링"""
        with st.expander("⌨️ 키보드 단축키", expanded=False):
            st.markdown("""
            ### 키보드 단축키
            
            | 기능 | 단축키 | 설명 |
            |--------|----------|------|
            | 페이지 새로고침 | Ctrl + R | 페이지를 새로고침 |
            | 검색으로 이동 | Alt + S | 검색 섹션으로 바로 이동 |
            | 차트로 이동 | Alt + C | 차트 섹션으로 바로 이동 |
            | 접근성 설정 | Alt + A | 접근성 설정 패널 열기 |
            | 메인 메뉴 | Alt + M | 메인 메뉴로 이동 |
            
            ### 탐색 단축키
            
            | 기능 | 단축키 | 설명 |
            |--------|----------|------|
            | 다음 요소 | Tab | 다음 포커스 가능 요소로 이동 |
            | 이전 요소 | Shift + Tab | 이전 포커스 가능 요소로 이동 |
            | 활성화 | Enter | 버튼 또는 링크 활성화 |
            | 선택 | Space | 체크박스 또는 라디오 버튼 선택 |
            """)
    
    def apply_accessibility_class(self, element_type: str) -> str:
        """요소 유형에 따른 접근성 클래스 반환"""
        base_class = "accessible-element"
        
        if st.session_state.accessibility_settings.get('high_contrast', False):
            base_class += " high-contrast"
        
        if st.session_state.accessibility_settings.get('keyboard_nav', False):
            base_class += " keyboard-nav"
        
        if st.session_state.accessibility_settings.get('screen_reader', True):
            base_class += " screen-reader-optimized"
        
        return base_class

# 전역 접근성 관리자 인스턴스
accessibility_manager = AccessibilityManager()