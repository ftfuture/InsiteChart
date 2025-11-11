# 사용자 경험 및 UI/UX 개선 영역 분석

## 1. 분석 개요

본 문서는 InsiteChart 프로젝트의 현재 사용자 경험(UX)과 사용자 인터페이스(UI)를 심층적으로 분석하여, 개선이 필요한 영역을 식별하고 구체적인 향상 방안을 제시합니다. 추가 기능 없이 현재 구현의 사용성과 접근성을 향상시키는 데 중점을 둡니다.

## 2. 현재 UI/UX 상태 분석

### 2.1 Streamlit 기반 현재 인터페이스

#### 2.1.1 강점
- **직관적인 레이아웃**: 왼쪽 검색/왓치리스트, 중앙 차트, 오른쪽 통계의 3단 구조
- **반응형 디자인**: 다양한 화면 크기에 대응하는 유연한 레이아웃
- **풍부한 차트 기능**: 캔들스틱, 라인, 영역 차트 및 다양한 기술적 지표
- **실시간 데이터 시각화**: Plotly를 통한 인터랙티브 차트 구현

#### 2.1.2 개선 기회
1. **로딩 상태 표시**: 데이터 로딩 시 사용자 피드백 부족
2. **오류 처리**: 사용자 친화적인 오류 메시지 및 복구 방안 부족
3. **키보드 내비게이션**: 마우스 의존적인 인터페이스로 키보드 사용성 저하
4. **모바일 최적화**: 모바일 환경에서의 사용성 제한
5. **접근성**: 스크린 리더 및 보조 기술 지원 부족

### 2.2 사용자 상호작용 분석

#### 2.2.1 현재 상태
- **검색 기능**: 기본적인 주식 검색 및 필터링
- **왓치리스트 관리**: 추가/삭제 기본 기능
- **차트 상호작용**: 확대/축소, 시간 프레임 선택
- **데이터 내보내기**: CSV 다운로드 기능

#### 2.2.2 개선 필요 영역
1. **검색 경험**: 자동완성, 검색 기록, 추천 기능 부족
2. **상태 관리**: 사용자 세션 및 상태 유지 기능 부족
3. **단축키**: 자주 사용하는 기능에 대한 단축키 부족
4. **드래그앤드롭**: 직관적인 데이터 조작 기능 부족
5. **컨텍스트 메뉴**: 마우스 오른쪽 클릭 메뉴 부족

## 3. 사용자 경험 개선 방안

### 3.1 로딩 상태 및 피드백 개선

#### 3.1.1 진행 상태 표시 시스템
```python
class LoadingStateManager:
    def __init__(self):
        self.loading_states = {}
        self.progress_callbacks = {}
    
    def start_loading(self, component_id: str, message: str = "로딩 중..."):
        """로딩 상태 시작"""
        self.loading_states[component_id] = {
            "message": message,
            "start_time": time.time(),
            "progress": 0,
            "stage": "initializing"
        }
        
        # 스피너와 메시지 표시
        with st.spinner(f"{message} ({component_id})"):
            # 로딩 상태 저장
            self._save_loading_state(component_id)
    
    def update_progress(self, component_id: str, progress: int, stage: str = None):
        """진행률 업데이트"""
        if component_id in self.loading_states:
            self.loading_states[component_id]["progress"] = progress
            if stage:
                self.loading_states[component_id]["stage"] = stage
            
            elapsed = time.time() - self.loading_states[component_id]["start_time"]
            
            # 진행률 바와 상태 메시지 표시
            st.progress(progress / 100)
            st.caption(f"{progress}% 완료 (경과 시간: {elapsed:.1f}초)")
            
            if stage:
                st.info(f"현재 단계: {stage}")
    
    def finish_loading(self, component_id: str, success: bool = True, message: str = None):
        """로딩 완료"""
        if component_id in self.loading_states:
            elapsed = time.time() - self.loading_states[component_id]["start_time"]
            
            if success:
                st.success(f"✅ {message or '작업 완료'} (소요 시간: {elapsed:.1f}초)")
            else:
                st.error(f"❌ {message or '작업 실패'} (소요 시간: {elapsed:.1f}초)")
            
            # 로딩 상태 정리
            del self.loading_states[component_id]

# 사용 예시
loading_manager = LoadingStateManager()

def load_stock_data(symbol: str):
    loading_manager.start_loading("stock_data", f"{symbol} 주식 데이터 로딩 중...")
    
    try:
        # 데이터 조회 (20%)
        loading_manager.update_progress("stock_data", 20, "데이터베이스 조회")
        stock_info = get_stock_info(symbol)
        
        # 감성 분석 (50%)
        loading_manager.update_progress("stock_data", 50, "감성 분석 중...")
        sentiment_data = get_sentiment_data(symbol)
        
        # 차트 생성 (80%)
        loading_manager.update_progress("stock_data", 80, "차트 생성 중...")
        chart_data = create_chart_data(stock_info, sentiment_data)
        
        # 완료 (100%)
        loading_manager.update_progress("stock_data", 100, "최종 데이터 통합")
        
        return {
            "stock_info": stock_info,
            "sentiment_data": sentiment_data,
            "chart_data": chart_data
        }
        
    except Exception as e:
        loading_manager.finish_loading("stock_data", False, f"데이터 로딩 실패: {str(e)}")
        return None
```

#### 3.1.2 스마트 로딩 전략
```python
class SmartLoadingStrategy:
    def __init__(self):
        self.loading_cache = {}
        self.priority_queue = []
    
    def preload_popular_data(self):
        """인기 데이터 선로딩"""
        popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
        
        # 백그라운드에서 인기 데이터 선로딩
        for symbol in popular_symbols:
            if symbol not in self.loading_cache:
                self.priority_queue.append({
                    "symbol": symbol,
                    "priority": "high",
                    "callback": self._preload_stock_data
                })
        
        # 우선순위별 데이터 로딩
        self._process_priority_queue()
    
    def _preload_stock_data(self, symbol: str):
        """주식 데이터 선로딩"""
        try:
            # 캐시에 데이터 미리 로드
            stock_data = fetch_stock_data(symbol)
            self.loading_cache[symbol] = {
                "data": stock_data,
                "timestamp": time.time(),
                "ttl": 300  # 5분
            }
        except Exception as e:
            logger.error(f"Preload failed for {symbol}: {str(e)}")
    
    def get_cached_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """선로딩된 데이터 반환"""
        if symbol in self.loading_cache:
            cached_item = self.loading_cache[symbol]
            
            # TTL 확인
            if time.time() - cached_item["timestamp"] < cached_item["ttl"]:
                return cached_item["data"]
            else:
                # 만료된 데이터 삭제
                del self.loading_cache[symbol]
        
        return None
```

### 3.2 오류 처리 및 복구 시스템

#### 3.2.1 사용자 친화적 오류 처리
```python
class UserFriendlyErrorHandler:
    def __init__(self):
        self.error_messages = {
            "network_error": {
                "title": "네트워크 연결 오류",
                "message": "서버에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.",
                "actions": [
                    {"text": "재시도", "action": "retry"},
                    {"text": "네트워크 설정", "action": "network_settings"}
                ]
            },
            "data_not_found": {
                "title": "데이터를 찾을 수 없음",
                "message": "요청한 정보를 찾을 수 없습니다. 다른 주식 심볼을 시도해보세요.",
                "actions": [
                    {"text": "다른 심볼 검색", "action": "search"},
                    {"text": "인기 주식 보기", "action": "popular_stocks"}
                ]
            },
            "rate_limit": {
                "title": "요청이 너무 많습니다",
                "message": "너무 많은 요청을 보내셨습니다. 잠시 후 다시 시도해주세요.",
                "actions": [
                    {"text": "알림 설정", "action": "notification_settings"},
                    {"text": "사용량 확인", "action": "usage_check"}
                ]
            },
            "server_error": {
                "title": "서버 오류",
                "message": "서버에서 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "actions": [
                    {"text": "다시 시도", "action": "retry"},
                    {"text": "문제 보고", "action": "report_issue"}
                ]
            }
        }
    
    def handle_error(self, error_type: str, details: str = None, retry_callback=None):
        """사용자 친화적 오류 처리"""
        error_info = self.error_messages.get(error_type, {
            "title": "알 수 없는 오류",
            "message": "문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "actions": [{"text": "다시 시도", "action": "retry"}]
        })
        
        # 오류 표시
        st.error(f"🚨 {error_info['title']}")
        st.info(error_info["message"])
        
        if details:
            with st.expander("상세 정보"):
                st.code(details)
        
        # 복구 작업 버튼
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 다시 시도", key="retry_action"):
                if retry_callback:
                    retry_callback()
        
        with col2:
            if st.button("🔍 다른 심볼 검색", key="search_action"):
                st.session_state.search_focus = True
        
        with col3:
            if st.button("📞 문제 보고", key="report_action"):
                st.session_state.show_issue_report = True
        
        # 추가 작업 버튼
        for i, action in enumerate(error_info["actions"]):
            if st.button(action["text"], key=f"error_action_{i}"):
                self._execute_error_action(action["action"])
    
    def _execute_error_action(self, action: str):
        """오류 복구 작업 실행"""
        if action == "retry":
            st.rerun()
        elif action == "search":
            st.session_state.search_focus = True
            st.rerun()
        elif action == "network_settings":
            st.session_state.show_network_settings = True
        elif action == "report_issue":
            st.session_state.show_issue_report = True
```

#### 3.2.2 자동 복구 시스템
```python
class AutoRecoverySystem:
    def __init__(self):
        self.retry_attempts = {}
        self.max_retries = 3
        self.backoff_factor = 2
        self.initial_delay = 1
    
    async def execute_with_retry(self, operation, operation_id: str, *args, **kwargs):
        """자동 재시도와 함께 작업 실행"""
        attempt = 0
        delay = self.initial_delay
        
        while attempt < self.max_retries:
            attempt += 1
            
            try:
                result = await operation(*args, **kwargs)
                
                # 성공 시 재시도 횟수 초기화
                if operation_id in self.retry_attempts:
                    del self.retry_attempts[operation_id]
                
                return result
                
            except Exception as e:
                self.retry_attempts[operation_id] = attempt
                
                if attempt < self.max_retries:
                    # 지수 백오프로 대기
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor
                    
                    logger.warning(f"Attempt {attempt} failed for {operation_id}: {str(e)}. Retrying in {delay}s...")
                else:
                    # 최종 실패
                    logger.error(f"All attempts failed for {operation_id}: {str(e)}")
                    raise e
    
    def get_retry_status(self, operation_id: str) -> Dict[str, Any]:
        """재시도 상태 확인"""
        if operation_id in self.retry_attempts:
            return {
                "attempts": self.retry_attempts[operation_id],
                "max_attempts": self.max_retries,
                "can_retry": self.retry_attempts[operation_id] < self.max_retries
            }
        return {"attempts": 0, "max_attempts": self.max_retries, "can_retry": True}
```

### 3.3 키보드 내비게이션 및 접근성 강화

#### 3.3.1 키보드 내비게이션 시스템
```python
class KeyboardNavigationManager:
    def __init__(self):
        self.shortcuts = {
            "Ctrl+K": "focus_search",
            "Ctrl+S": "save_to_watchlist",
            "Ctrl+R": "refresh_data",
            "F5": "refresh_data",
            "Escape": "clear_selection",
            "Arrow Up": "navigate_up",
            "Arrow Down": "navigate_down",
            "Arrow Left": "navigate_left",
            "Arrow Right": "navigate_right",
            "Enter": "select_item",
            "Tab": "next_focusable",
            "Shift+Tab": "prev_focusable"
        }
        
        self.focusable_elements = []
        self.current_focus_index = 0
    
    def add_keyboard_support(self):
        """키보드 내비게이션 지원 추가"""
        keyboard_js = """
        <script>
        document.addEventListener('keydown', function(e) {
            const shortcuts = {
                'ctrl+k': function() {
                    const searchInput = document.querySelector('[data-testid="stTextInput"]');
                    if (searchInput) searchInput.focus();
                },
                'escape': function() {
                    const activeElement = document.activeElement;
                    if (activeElement) activeElement.blur();
                },
                'arrowdown': function() {
                    const focusableElements = document.querySelectorAll('button, input, [tabindex]');
                    const currentIndex = Array.from(focusableElements).indexOf(document.activeElement);
                    const nextIndex = (currentIndex + 1) % focusableElements.length;
                    focusableElements[nextIndex].focus();
                },
                'arrowup': function() {
                    const focusableElements = document.querySelectorAll('button, input, [tabindex]');
                    const currentIndex = Array.from(focusableElements).indexOf(document.activeElement);
                    const prevIndex = currentIndex <= 0 ? focusableElements.length - 1 : currentIndex - 1;
                    focusableElements[prevIndex].focus();
                }
            };
            
            // 단축키 처리
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                shortcuts['ctrl+k']();
            } else if (e.key === 'Escape') {
                shortcuts['escape']();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                shortcuts['arrowdown']();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                shortcuts['arrowup']();
            }
        });
        </script>
        """
        
        st.markdown(keyboard_js, unsafe_allow_html=True)
    
    def add_focus_management(self):
        """포커스 관리 추가"""
        focus_management_js = """
        <script>
        // 포커스 가능한 요소에 tabindex 추가
        document.addEventListener('DOMContentLoaded', function() {
            const buttons = document.querySelectorAll('button');
            const inputs = document.querySelectorAll('input');
            
            buttons.forEach((button, index) => {
                button.setAttribute('tabindex', '0');
                button.setAttribute('data-focus-index', index);
            });
            
            inputs.forEach((input, index) => {
                input.setAttribute('tabindex', '0');
                input.setAttribute('data-focus-index', index + buttons.length);
            });
        });
        </script>
        """
        
        st.markdown(focus_management_js, unsafe_allow_html=True)
    
    def create_shortcuts_help(self):
        """단축키 도움말 생성"""
        with st.expander("⌨️ 키보드 단축키"):
            shortcuts_data = [
                {"키": "Ctrl+K", "기능": "검색창 포커스"},
                {"키": "Escape", "기능": "선택 해제"},
                {"키": "↑/↓", "기능": "위/아래 이동"},
                {"키": "Enter", "기능": "항목 선택"},
                {"키": "Tab", "기능": "다음 요소로 이동"},
                {"키": "Shift+Tab", "기능": "이전 요소로 이동"}
            ]
            
            for shortcut in shortcuts_data:
                st.markdown(f"**{shortcut['키']}**: {shortcut['기능']}")
```

#### 3.3.2 스크린 리더 및 보조 기술 지원
```python
class AccessibilityManager:
    def __init__(self):
        self.announcements = []
        self.current_focus_element = None
    
    def add_screen_reader_support(self):
        """스크린 리더 지원 추가"""
        screen_reader_js = """
        <script>
        // ARIA 라이브 리전 추가
        function announceToScreenReader(message) {
            const announcement = document.createElement('div');
            announcement.setAttribute('role', 'status');
            announcement.setAttribute('aria-live', 'polite');
            announcement.className = 'sr-only';
            announcement.textContent = message;
            
            document.body.appendChild(announcement);
            
            // 잠시 후 제거
            setTimeout(() => {
                document.body.removeChild(announcement);
            }, 1000);
        }
        
        // 페이지 로딩 완료 알림
        window.addEventListener('load', function() {
            announceToScreenReader('페이지 로딩이 완료되었습니다.');
        });
        
        // 데이터 변경 알림
        function announceDataChange(element, changeType) {
            const message = `${changeType}: ${element.textContent || element.value}`;
            announceToScreenReader(message);
        }
        
        // 전역 함수로 노출
        window.announceToScreenReader = announceToScreenReader;
        window.announceDataChange = announceDataChange;
        </script>
        
        <style>
        /* 스크린 리더 전용 스타일 */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        
        /* 포커스 시각적 표시 */
        *:focus {
            outline: 2px solid #0066cc;
            outline-offset: 2px;
        }
        
        /* 고대대비 모드 지원 */
        @media (prefers-contrast: high) {
            .stButton > button {
                border: 2px solid;
                background: white;
                color: black;
            }
        }
        
        /* 모션 감소 모드 지원 */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        </style>
        """
        
        st.markdown(screen_reader_js, unsafe_allow_html=True)
    
    def announce_data_change(self, message: str):
        """데이터 변경 알림"""
        announcement_js = f"""
        <script>
        window.announceToScreenReader('{message}');
        </script>
        """
        
        st.markdown(announcement_js, unsafe_allow_html=True)
    
    def add_accessibility_controls(self):
        """접근성 컨트롤 추가"""
        with st.expander("♿ 접근성 설정"):
            # 글자 크기 조절
            font_size = st.selectbox(
                "글자 크기",
                ["작게", "보통", "크게", "매우 크게"],
                index=1
            )
            
            # 고대대비 모드
            high_contrast = st.checkbox("고대대비 모드")
            
            # 모션 감소
            reduce_motion = st.checkbox("모션 감소")
            
            # 스크린 리더 최적화
            screen_reader_optimized = st.checkbox("스크린 리더 최적화")
            
            # 설정 저장
            if st.button("접근성 설정 저장"):
                accessibility_settings = {
                    "font_size": font_size,
                    "high_contrast": high_contrast,
                    "reduce_motion": reduce_motion,
                    "screen_reader_optimized": screen_reader_optimized
                }
                
                # 쿠키나 로컬 스토리지에 저장
                st.session_state.accessibility_settings = accessibility_settings
                
                st.success("접근성 설정이 저장되었습니다.")
                
                # 설정 적용
                self._apply_accessibility_settings(accessibility_settings)
    
    def _apply_accessibility_settings(self, settings: Dict[str, Any]):
        """접근성 설정 적용"""
        settings_js = f"""
        <script>
        // 글자 크기 적용
        document.documentElement.style.fontSize = '{settings['font_size']}';
        
        // 고대대비 모드 적용
        if ({settings['high_contrast']}) {{
            document.body.classList.add('high-contrast');
        }}
        
        // 모션 감소 적용
        if ({settings['reduce_motion']}) {{
            document.body.classList.add('reduce-motion');
        }}
        
        // 스크린 리더 최적화 적용
        if ({settings['screen_reader_optimized']}) {{
            document.body.classList.add('screen-reader-optimized');
        }}
        </script>
        """
        
        st.markdown(settings_js, unsafe_allow_html=True)
```

### 3.4 모바일 최적화 및 반응형 디자인

#### 3.4.1 모바일 최적화 전략
```python
class MobileOptimizationManager:
    def __init__(self):
        self.is_mobile = self._detect_mobile()
        self.touch_gestures = {}
    
    def _detect_mobile(self) -> bool:
        """모바일 기기 감지"""
        user_agent = st.experimental_get_query_params().get("user_agent", "")
        
        mobile_patterns = [
            "Android", "iPhone", "iPad", "iPod", "BlackBerry", 
            "Windows Phone", "Mobile", "webOS", "Opera Mini"
        ]
        
        return any(pattern in user_agent for pattern in mobile_patterns)
    
    def add_mobile_optimizations(self):
        """모바일 최적화 추가"""
        if self.is_mobile:
            # 모바일 전용 CSS
            mobile_css = """
            <style>
            /* 모바일 최적화 스타일 */
            @media (max-width: 768px) {
                .stSelectbox > div > div {
                    font-size: 16px !important; /* iOS 확대 방지 */
                }
                
                .stTextInput > div > input {
                    font-size: 16px !important;
                }
                
                .stButton > button {
                    min-height: 44px !important; /* 최소 터치 영역 */
                    font-size: 16px !important;
                }
                
                .stDataFrame {
                    font-size: 14px !important;
                }
                
                /* 모바일 전용 레이아웃 조정 */
                .element-container {
                    padding: 0.5rem !important;
                }
                
                /* 모바일에서 숨길 요소 */
                .desktop-only {
                    display: none !important;
                }
                
                /* 모바일 전용 요소 */
                .mobile-only {
                    display: block !important;
                }
            }
            
            /* 터치 제스처 최적화 */
            @media (hover: none) and (pointer: coarse) {
                .stButton > button:hover {
                    background-color: inherit !important;
                }
                
                .stButton > button:active {
                    background-color: #0066cc !important;
                }
            }
            </style>
            """
            
            st.markdown(mobile_css, unsafe_allow_html=True)
    
    def add_touch_gestures(self):
        """터치 제스처 지원 추가"""
        touch_gestures_js = """
        <script>
        // 터치 제스처 관리
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;
        
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        });
        
        document.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].clientX;
            touchEndY = e.changedTouches[0].clientY;
            
            // 스와이프 감지
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            const minSwipeDistance = 50;
            
            if (Math.abs(deltaX) > minSwipeDistance) {
                // 수평 스와이프
                if (deltaX > 0) {
                    window.dispatchEvent(new CustomEvent('swiperight'));
                } else {
                    window.dispatchEvent(new CustomEvent('swipeleft'));
                }
            }
            
            if (Math.abs(deltaY) > minSwipeDistance) {
                // 수직 스와이프
                if (deltaY > 0) {
                    window.dispatchEvent(new CustomEvent('swipedown'));
                } else {
                    window.dispatchEvent(new CustomEvent('swipeup'));
                }
            }
        });
        
        // 스와이프 이벤트 핸들러
        document.addEventListener('swiperight', function() {
            // 오른쪽 스와이프 처리 (다음 차트)
            console.log('Swipe right detected');
        });
        
        document.addEventListener('swipeleft', function() {
            // 왼쪽 스와이프 처리 (이전 차트)
            console.log('Swipe left detected');
        });
        
        document.addEventListener('swipeup', function() {
            // 위쪽 스와이프 처리 (확대)
            console.log('Swipe up detected');
        });
        
        document.addEventListener('swipedown', function() {
            // 아래쪽 스와이프 처리 (축소)
            console.log('Swipe down detected');
        });
        </script>
        """
        
        st.markdown(touch_gestures_js, unsafe_allow_html=True)
    
    def create_mobile_friendly_ui(self):
        """모바일 친화적 UI 생성"""
        if self.is_mobile:
            # 모바일 전용 네비게이션
            with st.sidebar:
                st.markdown("### 📱 모바일 메뉴")
                
                # 빠른 액션 버튼
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🔍 검색", use_container_width=True):
                        st.session_state.mobile_search_focus = True
                
                with col2:
                    if st.button("⭐ 즐겨찾기", use_container_width=True):
                        st.session_state.show_favorites = True
                
                # 터치 친화적 탭 내비게이션
                mobile_tabs = st.tabs(["차트", "뉴스", "왓치리스트"])
                
                with mobile_tabs[0]:
                    st.markdown("### 📈 차트")
                    # 모바일 최적화 차트
                    self._create_mobile_chart()
                
                with mobile_tabs[1]:
                    st.markdown("### 📰 뉴스")
                    # 모바일 최적화 뉴스
                    self._create_mobile_news()
                
                with mobile_tabs[2]:
                    st.markdown("### ⭐ 왓치리스트")
                    # 모바일 최적화 왓치리스트
                    self._create_mobile_watchlist()
    
    def _create_mobile_chart(self):
        """모바일 최적화 차트 생성"""
        # 더 작은 차트 크기
        chart_height = 300
        
        # 터치 제스처 지원
        chart_config = {
            "displayModeBar": False,
            "scrollZoom": True,
            "displayModeBar": False,
            "responsive": True
        }
        
        # 모바일 최적화 차트 생성
        fig = self._create_optimized_chart(chart_height, chart_config)
        st.plotly_chart(fig, config=chart_config, use_container_width=True)
    
    def _create_mobile_news(self):
        """모바일 최적화 뉴스 생성"""
        # 더 큰 텍스트와 터치 친화적 카드
        news_items = self._get_mobile_news()
        
        for item in news_items:
            with st.container():
                st.markdown(f"### {item['title']}")
                st.markdown(f"**{item['summary']}**")
                st.markdown(f"*{item['time']}*")
                
                # 터치 친화적 버튼
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📖 자세히", key=f"read_{item['id']}"):
                        st.session_state.selected_news = item
                
                with col2:
                    if st.button("🔗 공유", key=f"share_{item['id']}"):
                        st.session_state.share_news = item
    
    def _create_mobile_watchlist(self):
        """모바일 최적화 왓치리스트 생성"""
        # 스와이프 가능한 목록
        watchlist = self._get_watchlist()
        
        for i, stock in enumerate(watchlist):
            # 스와이프 가능한 카드
            with st.container():
                cols = st.columns([3, 1])
                
                with cols[0]:
                    st.markdown(f"**{stock['symbol']}**")
                    st.markdown(f"{stock['name']}")
                    st.markdown(f"${stock['price']:.2f}")
                
                with cols[1]:
                    # 스와이프 액션 버튼
                    if st.button("🗑️", key=f"remove_{i}"):
                        self._remove_from_watchlist(stock['symbol'])
```

### 3.5 검색 경험 개선

#### 3.5.1 스마트 검색 시스템
```python
class SmartSearchManager:
    def __init__(self):
        self.search_history = []
        self.popular_searches = []
        self.search_suggestions = {}
        self.search_analytics = {}
    
    def add_autocomplete_search(self):
        """자동완성 검색 추가"""
        # 검색 입력창
        search_query = st.text_input(
            "🔍 주식 검색",
            placeholder="심볼, 회사명, 섹터로 검색...",
            key="smart_search",
            help="자동완성을 위해 입력하세요"
        )
        
        if search_query:
            # 검색 제안 생성
            suggestions = self._generate_search_suggestions(search_query)
            
            if suggestions:
                # 검색 제안 표시
                for suggestion in suggestions:
                    if st.button(
                        f"🔍 {suggestion['symbol']} - {suggestion['name']}",
                        key=f"suggestion_{suggestion['symbol']}"
                    ):
                        st.session_state.selected_stock = suggestion['symbol']
                        st.rerun()
    
    def _generate_search_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """검색 제안 생성"""
        suggestions = []
        
        # 정확히 일치하는 심볼
        exact_matches = self._search_exact_symbols(query)
        suggestions.extend(exact_matches)
        
        # 부분 일치하는 심볼
        partial_matches = self._search_partial_symbols(query)
        suggestions.extend(partial_matches)
        
        # 회사명 검색
        company_matches = self._search_company_names(query)
        suggestions.extend(company_matches)
        
        # 인기 검색어 추천
        popular_matches = self._get_popular_searches(query)
        suggestions.extend(popular_matches)
        
        # 중복 제거 및 정렬
        unique_suggestions = []
        seen_symbols = set()
        
        for suggestion in suggestions:
            if suggestion['symbol'] not in seen_symbols:
                unique_suggestions.append(suggestion)
                seen_symbols.add(suggestion['symbol'])
        
        return unique_suggestions[:10]  # 최대 10개 제안
    
    def add_search_history(self, query: str, results: List[Dict[str, Any]]):
        """검색 기록 추가"""
        search_entry = {
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "result_count": len(results),
            "results": [r['symbol'] for r in results[:5]]  # 상위 5개 결과만 저장
        }
        
        # 검색 기록에 추가
        self.search_history.append(search_entry)
        
        # 최대 100개 기록 유지
        if len(self.search_history) > 100:
            self.search_history = self.search_history[-100:]
        
        # 검색 분석 업데이트
        self._update_search_analytics(query, len(results))
    
    def show_search_history(self):
        """검색 기록 표시"""
        if st.button("🕒 검색 기록"):
            with st.expander("최근 검색 기록"):
                for entry in reversed(self.search_history[-10:]):  # 최근 10개
                    cols = st.columns([3, 1])
                    
                    with cols[0]:
                        st.markdown(f"**{entry['query']}**")
                        st.markdown(f"*{entry['timestamp']}*")
                        st.markdown(f"{entry['result_count']}개 결과")
                    
                    with cols[1]:
                        if st.button("🔍 재검색", key=f"history_{entry['query']}"):
                            st.session_state.search_query = entry['query']
                            st.rerun()
    
    def add_trending_searches(self):
        """인기 검색어 추가"""
        trending_searches = self._get_trending_searches()
        
        if trending_searches:
            st.markdown("### 🔥 인기 검색")
            
            # 트렌딩 검색어 태그
            cols = st.columns(4)
            
            for i, search_term in enumerate(trending_searches[:8]):
                with cols[i % 4]:
                    if st.button(
                        f"🔥 {search_term}",
                        key=f"trending_{i}"
                    ):
                        st.session_state.search_query = search_term
                        st.rerun()
    
    def _update_search_analytics(self, query: str, result_count: int):
        """검색 분석 업데이트"""
        if query not in self.search_analytics:
            self.search_analytics[query] = {
                "search_count": 0,
                "total_results": 0,
                "first_searched": datetime.utcnow().isoformat()
            }
        
        self.search_analytics[query]["search_count"] += 1
        self.search_analytics[query]["total_results"] += result_count
```

## 4. 성능 최적화를 통한 UX 향상

### 4.1 지연 로딩 및 가상화
```python
class LazyLoadingManager:
    def __init__(self):
        self.loaded_components = {}
        self.loading_queue = []
    
    def add_lazy_loading(self, component_id: str, loader_func):
        """지연 로딩 컴포넌트 추가"""
        if component_id not in self.loaded_components:
            # 로딩 플레이스홀더 표시
            st.markdown(f"""
            <div id="{component_id}_placeholder" class="lazy-placeholder">
                <div class="loading-spinner"></div>
                <p>로딩 중...</p>
            </div>
            """, unsafe_allow_html=True)
            
            # JavaScript로 지연 로딩 구현
            lazy_loading_js = f"""
            <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const placeholder = document.getElementById('{component_id}_placeholder');
                
                // 뷰포트에 컴포넌트가 보일 때 로딩
                const observer = new IntersectionObserver(function(entries) {{
                    entries.forEach(function(entry) {{
                        if (entry.isIntersecting) {{
                            // 컴포넌트 로딩
                            loadComponent('{component_id}');
                            observer.unobserve(placeholder);
                        }}
                    }});
                }});
                
                observer.observe(placeholder);
            }});
            
            function loadComponent(componentId) {{
                // 실제 컴포넌트 로딩
                fetch(`/api/components/${{component_id}}`)
                    .then(response => response.text())
                    .then(html => {{
                        const placeholder = document.getElementById(componentId + '_placeholder');
                        placeholder.innerHTML = html;
                    }})
                    .catch(error => {{
                        console.error('Error loading component:', error);
                    }});
            }}
            </script>
            """
            
            st.markdown(lazy_loading_js, unsafe_allow_html=True)
    
    def add_virtual_scrolling(self, data_source: str, item_height: int = 50):
        """가상 스크롤링 추가"""
        virtual_scrolling_js = f"""
        <script>
        class VirtualScroll {{
            constructor(container, dataSource, itemHeight) {{
                this.container = container;
                this.dataSource = dataSource;
                this.itemHeight = itemHeight;
                this.visibleItems = [];
                this.startIndex = 0;
                this.endIndex = 0;
                
                this.init();
            }}
            
            init() {{
                this.container.addEventListener('scroll', this.handleScroll.bind(this));
                this.updateVisibleItems();
            }}
            
            handleScroll() {{
                const scrollTop = this.container.scrollTop;
                const containerHeight = this.container.clientHeight;
                
                this.startIndex = Math.floor(scrollTop / this.itemHeight);
                this.endIndex = Math.min(
                    this.startIndex + Math.ceil(containerHeight / this.itemHeight),
                    this.dataSource.length
                );
                
                this.updateVisibleItems();
            }}
            
            updateVisibleItems() {{
                const fragment = document.createDocumentFragment();
                
                for (let i = this.startIndex; i < this.endIndex; i++) {{
                    const item = this.dataSource[i];
                    const itemElement = this.createItemElement(item, i);
                    fragment.appendChild(itemElement);
                }}
                
                this.container.innerHTML = '';
                this.container.appendChild(fragment);
                
                // 컨테이너 높이 조정
                this.container.style.height = (this.dataSource.length * this.itemHeight) + 'px';
            }}
            
            createItemElement(item, index) {{
                const div = document.createElement('div');
                div.className = 'virtual-item';
                div.style.height = this.itemHeight + 'px';
                div.style.position = 'absolute';
                div.style.top = (index * this.itemHeight) + 'px';
                div.style.width = '100%';
                div.textContent = item.name || item.symbol;
                
                return div;
            }}
        }}
        
        // 가상 스크롤링 초기화
        const container = document.getElementById('virtual-scroll-container');
        const dataSource = {data_source};
        new VirtualScroll(container, dataSource, 50);
        </script>
        
        <style>
        .virtual-scroll-container {{
            height: 400px;
            overflow-y: auto;
            position: relative;
            border: 1px solid #ddd;
        }}
        
        .virtual-item {{
            box-sizing: border-box;
            border-bottom: 1px solid #eee;
            padding: 10px;
        }}
        </style>
        """
        
        st.markdown(virtual_scrolling_js, unsafe_allow_html=True)
```

## 5. 결론 및 우선순위

### 5.1 즉시 실행 필요 (1-2주 내)
1. **로딩 상태 표시 개선**
   - 진행률 표시 및 상태 메시지
   - 스마트 로딩 전략 구현
   - 로딩 실패 시 복구 방안 제공

2. **오류 처리 강화**
   - 사용자 친화적 오류 메시지
   - 자동 재시도 시스템
   - 구체적인 복구 작업 제공

3. **키보드 내비게이션**
   - 단축키 시스템 구현
   - 포커스 관리 개선
   - 단축키 도움말 제공

### 5.2 단기 실행 (2-4주 내)
1. **접근성 강화**
   - 스크린 리더 지원
   - 고대대비 모드
   - 모션 감소 옵션
   - 접근성 설정 저장

2. **모바일 최적화**
   - 터치 제스처 지원
   - 모바일 전용 UI
   - 반응형 디자인 개선
   - 모바일 성능 최적화

3. **검색 경험 개선**
   - 자동완성 기능
   - 검색 기록 관리
   - 인기 검색어 추천
   - 검색 분석 시스템

### 5.3 중장기 실행 (1-2개월 내)
1. **고급 상호작용**
   - 드래그앤드롭 기능
   - 컨텍스트 메뉴
   - 제스처 기반 상호작용
   - 멀티터치 지원

2. **개인화 기능**
   - 사용자 선호도 저장
   - 대시보드 커스터마이징
   - 레이아웃 개인화
   - 알림 설정 개인화

3. **성능 최적화**
   - 지연 로딩 구현
   - 가상 스크롤링
   - 컴포넌트 수준 캐싱
   - 렌더링 성능 최적화

이러한 사용자 경험 개선 방안들을 단계적으로 구현함으로써, InsiteChart는 **더 직관적이고 접근성이 뛰어나며, 모바일 환경에서도 탁월한 사용자 경험**을 제공할 수 있을 것입니다.