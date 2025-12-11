# 사용자 피드백 시스템 분석 보고서

## 1. 개요

본 보고서는 InsiteChart 프로젝트의 사용자 피드백 시스템 현황을 분석하고, 개선 방안을 제시합니다. 현재 구현된 피드백 시스템은 기본적인 기능을 갖추고 있으나, 몇 가지 개선이 필요한 부분이 있습니다.

## 2. 현재 피드백 시스템 구조

### 2.1 아키텍처 개요

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend    │    │   Backend API  │    │   Database     │
│                │    │                │    │                │
│ Streamlit UI  │◄──►│ Feedback API   │◄──►│ PostgreSQL     │
│ Feedback      │    │ Routes         │    │ Models         │
│ Dashboard     │    │                │    │                │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 주요 구성 요소

#### 2.2.1 데이터 모델
- **UserFeedback**: 사용자 피드백 기본 정보
- **UserActivity**: 사용자 활동 로그
- **FeatureUsage**: 기능 사용 통계
- **UserBehavior**: 사용자 행동 추적 데이터

#### 2.2.2 서비스 계층
- **FeedbackService**: 피드백 관리 비즈니스 로직
- **FeedbackClient**: 프론트엔드 API 클라이언트
- **Feedback Routes**: API 엔드포인트

#### 2.2.3 UI 컴포넌트
- **피드백 제출 폼**: 사용자 피드백 수집
- **피드백 내역**: 제출된 피드백 조회
- **활동 요약**: 사용자 활동 통계

## 3. 현재 구현 상세 분석

### 3.1 데이터 모델 분석

#### 3.1.1 UserFeedback 모델
```python
class UserFeedback(Base):
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # bug_report, feature_request, general, ui_ux
    category = Column(String(100), nullable=True)  # chart, sentiment_analysis, performance, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 stars for feature satisfaction
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(20), default="open")  # open, in_progress, resolved, closed
    response = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**강점:**
- 필수 필드와 선택적 필드가 적절히 구분됨
- 상태 관리를 위한 `status` 필드 존재
- 우선순위 관리를 위한 `priority` 필드 존재
- 만족도 평가를 위한 `rating` 필드 존재

**개선점:**
- 피드백 태그/키워드 기능 부재
- 첨부 파일 지원 부재
- 익명 피드백 기능 부재
- 피드백 간의 관계(연관성) 관리 기능 부재

#### 3.1.2 UserActivity 모델
```python
class UserActivity(Base):
    __tablename__ = "user_activity"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), nullable=True)
    activity_type = Column(String(50), nullable=False)
    feature_name = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False)
    metadata = Column(JSON, nullable=True)
    duration = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**강점:**
- 유연한 메타데이터 저장을 위한 JSON 필드
- 세션 추적 기능
- 활동 지속 시간 측정

**개선점:**
- 활동 경로(사용자 이동 경로) 추적 기능 부재
- A/B 테스트 관련 데이터 구조 부재
- 성능 메트릭 수집 기능 제한적

### 3.2 API 엔드포인트 분석

#### 3.2.1 현재 구현된 엔드포인트
| 엔드포인트 | 기능 | 인증 | 상태 |
|------------|------|------|------|
| `POST /api/v1/feedback/submit` | 피드백 제출 | 필수 | ✅ 완료 |
| `GET /api/v1/feedback/my-feedback` | 내 피드백 조회 | 필수 | ✅ 완료 |
| `GET /api/v1/feedback/feedback/{id}` | 특정 피드백 조회 | 필수 | ✅ 완료 |
| `POST /api/v1/feedback/log-activity` | 활동 로깅 | 필수 | ✅ 완료 |
| `POST /api/v1/feedback/track-behavior` | 행동 추적 | 필수 | ✅ 완료 |
| `GET /api/v1/feedback/my-activity-summary` | 활동 요약 | 필수 | ✅ 완료 |
| `GET /api/v1/feedback/admin/all-feedback` | 전체 피드백 조회 | 관리자 | ✅ 완료 |
| `PUT /api/v1/feedback/admin/feedback/{id}/status` | 피드백 상태 업데이트 | 관리자 | ✅ 완료 |
| `GET /api/v1/feedback/admin/platform-analytics` | 플랫폼 분석 | 관리자 | ✅ 완료 |
| `GET /api/v1/feedback/admin/feedback-insights` | 피드백 인사이트 | 관리자 | ✅ 완료 |
| `GET /api/v1/feedback/admin/feature-usage` | 기능 사용 통계 | 관리자 | ✅ 완료 |

**강점:**
- 사용자와 관리자 기능이 명확히 분리됨
- CRUD 연산이 모두 구현됨
- 분석 및 인사이트 기능이 포함됨

**개선점:**
- 피드백 검색 및 필터링 기능 제한적
- 피드백 추천 기능 부재
- 실시간 알림 기능 부재
- 피드백 투표/평가 기능 부재

#### 3.2.2 요청/응답 형식 분석
```python
# 피드백 제출 요청
class FeedbackCreate(BaseModel):
    feedback_type: str = Field(..., description="Type of feedback")
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    category: Optional[str] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    priority: str = Field("medium")
```

**강점:**
- Pydantic을 통한 데이터 검증
- 적절한 필드 제약 조건
- 명확한 필드 설명

**개선점:**
- 표준 API 응답 형식과 불일치
- 에러 코드 체계 부재
- API 버전 관리 정책 부재

### 3.3 프론트엔드 구현 분석

#### 3.3.1 UI 컴포넌트 구조
```python
def render_feedback_dashboard(auth_token: Optional[str] = None):
    """Render complete feedback dashboard."""
    st.markdown("## 💬 피드백 센터")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📝 피드백 제출", 
        "📋 피드백 내역", 
        "📊 활동 요약"
    ])
    
    with tab1:
        render_feedback_form(auth_token)
    
    with tab2:
        render_feedback_history(auth_token)
    
    with tab3:
        render_activity_summary(auth_token)
```

**강점:**
- 직관적인 탭 기반 UI 구조
- 한국어 지원
- 실시간 피드백 제출 기능

**개선점:**
- 반응형 디자인 부족
- 접근성 기능 제한적
- 실시간 업데이트 기능 부재
- 모바일 최적화 부족

#### 3.3.2 피드백 폼 분석
```python
def render_feedback_form(auth_token: Optional[str] = None):
    """Render feedback submission form."""
    with st.form("feedback_form"):
        # Feedback type
        feedback_type = st.selectbox(
            "피드백 유형",
            options=["bug_report", "feature_request", "general", "ui_ux"],
            format_func=lambda x: {
                "bug_report": "🐛 버그 리포트",
                "feature_request": "💡 기능 요청",
                "general": "💬 일반 피드백",
                "ui_ux": "🎨 UI/UX 개선"
            }[x]
        )
        
        # Category
        category = st.selectbox(
            "카테고리",
            options=["", "chart", "sentiment_analysis", "performance", "search", "watchlist", "other"]
        )
        
        # Rating
        rating = st.slider(
            "만족도 평가",
            min_value=1,
            max_value=5,
            value=5,
            help="1점 (매우 불만족) - 5점 (매우 만족)"
        )
```

**강점:**
- 직관적인 피드백 유형 선택
- 이모지를 통한 시각적 개선
- 만족도 평가 기능

**개선점:**
- 첨부 파일 업로드 기능 부재
- 피드백 초안/임시 저장 기능 부재
- 실시간 유효성 검사 부족
- 자동 완성 기능 부재

## 4. 피드백 시스템 개선 방안

### 4.1 데이터 모델 확장

#### 4.1.1 향상된 피드백 모델
```python
class EnhancedUserFeedback(Base):
    """향상된 사용자 피드백 모델"""
    __tablename__ = "enhanced_user_feedback"
    
    # 기존 필드
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 익명 허용
    feedback_type = Column(String(50), nullable=False)
    category = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="open")
    response = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    
    # 새로운 필드
    tags = Column(JSON, nullable=True)  # 피드백 태그
    attachments = Column(JSON, nullable=True)  # 첨부 파일 정보
    anonymous = Column(Boolean, default=False)  # 익명 여부
    upvotes = Column(Integer, default=0)  # 추천 수
    downvotes = Column(Integer, default=0)  # 비추천 수
    views = Column(Integer, default=0)  # 조회 수
    related_feedback = Column(JSON, nullable=True)  # 연관 피드백 ID 목록
    environment = Column(String(50), nullable=True)  # 사용 환경 (browser, os, etc.)
    reproduction_steps = Column(Text, nullable=True)  # 재현 단계
    expected_behavior = Column(Text, nullable=True)  # 예상 동작
    actual_behavior = Column(Text, nullable=True)  # 실제 동작
    severity = Column(String(20), nullable=True)  # 심각도
    reproducibility = Column(String(20), nullable=True)  # 재현성
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # 관계
    user = relationship("User", back_populates="feedback")
    responder = relationship("User", foreign_keys=[responded_by])
    comments = relationship("FeedbackComment", back_populates="feedback")
    attachments = relationship("FeedbackAttachment", back_populates="feedback")
```

#### 4.1.2 피드백 댓글 모델
```python
class FeedbackComment(Base):
    """피드백 댓글 모델"""
    __tablename__ = "feedback_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("enhanced_user_feedback.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # 내부 댓글 여부
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    feedback = relationship("EnhancedUserFeedback", back_populates="comments")
    user = relationship("User")
```

#### 4.1.3 피드백 첨부 파일 모델
```python
class FeedbackAttachment(Base):
    """피드백 첨부 파일 모델"""
    __tablename__ = "feedback_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("enhanced_user_feedback.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    feedback = relationship("EnhancedUserFeedback", back_populates="attachments")
    uploader = relationship("User")
```

### 4.2 API 엔드포인트 확장

#### 4.2.1 새로운 엔드포인트 제안
| 엔드포인트 | 기능 | 설명 |
|------------|------|------|
| `POST /api/v1/feedback/submit-with-attachments` | 첨부 파일 포함 피드백 제출 | 파일 업로드와 피드백 제출을 동시에 처리 |
| `GET /api/v1/feedback/search` | 피드백 검색 | 키워드, 태그, 카테고리로 피드백 검색 |
| `POST /api/v1/feedback/{id}/upvote` | 피드백 추천 | 유용한 피드백에 추천 |
| `POST /api/v1/feedback/{id}/comment` | 피드백 댓글 추가 | 피드백에 댓글 달기 |
| `GET /api/v1/feedback/{id}/comments` | 피드백 댓글 조회 | 특정 피드백의 댓글 목록 |
| `POST /api/v1/feedback/{id}/subscribe` | 피드백 구독 | 특정 피드백 업데이트 알림 |
| `GET /api/v1/feedback/similar/{id}` | 유사 피드백 조회 | 연관성 있는 피드백 추천 |
| `POST /api/v1/feedback/draft` | 임시 피드백 저장 | 나중에 제출할 피드백 임시 저장 |
| `GET /api/v1/feedback/drafts` | 임시 피드백 목록 | 사용자의 임시 저장된 피드백 목록 |
| `POST /api/v1/feedback/bulk-submit` | 일괄 피드백 제출 | 여러 피드백을 한 번에 제출 |

#### 4.2.2 향상된 API 응답 형식
```python
# 표준 응답 형식
class StandardAPIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str
    timestamp: datetime
    request_id: Optional[str] = None  # 요청 추적 ID
    
# 페이지네이션 응답
class PaginatedResponse(BaseModel):
    success: bool
    data: List[Any]
    pagination: PaginationInfo
    message: str
    timestamp: datetime
    
class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool
```

### 4.3 프론트엔드 개선

#### 4.3.1 향상된 피드백 폼
```python
def render_enhanced_feedback_form(auth_token: Optional[str] = None):
    """향상된 피드백 제출 폼"""
    st.markdown("### 📝 향상된 피드백 제출")
    
    with st.form("enhanced_feedback_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 기본 정보
            feedback_type = st.selectbox(
                "피드백 유형",
                options=["bug_report", "feature_request", "general", "ui_ux"],
                format_func=lambda x: {
                    "bug_report": "🐛 버그 리포트",
                    "feature_request": "💡 기능 요청",
                    "general": "💬 일반 피드백",
                    "ui_ux": "🎨 UI/UX 개선"
                }[x]
            )
            
            title = st.text_input(
                "제목 *",
                max_chars=255,
                help="피드백의 간결한 제목을 입력하세요"
            )
            
            category = st.selectbox(
                "카테고리",
                options=["", "chart", "sentiment_analysis", "performance", "search", "watchlist", "other"],
                format_func=lambda x: {
                    "": "선택 안함",
                    "chart": "📊 차트",
                    "sentiment_analysis": "💭 감성 분석",
                    "performance": "⚡ 성능",
                    "search": "🔍 검색",
                    "watchlist": "⭐ 감시 목록",
                    "other": "기타"
                }[x] if x else "선택 안함"
            )
            
            priority = st.selectbox(
                "우선순위",
                options=["low", "medium", "high", "critical"],
                format_func=lambda x: {
                    "low": "🟢 낮음",
                    "medium": "🟡 보통",
                    "high": "🟠 높음",
                    "critical": "🔴 긴급"
                }[x]
            )
            
            # 버그 리포트 추가 필드
            if feedback_type == "bug_report":
                severity = st.selectbox(
                    "심각도",
                    options=["trivial", "minor", "major", "critical", "blocker"],
                    format_func=lambda x: {
                        "trivial": "🟢 사소함",
                        "minor": "🟡 사소함",
                        "major": "🟠 중요함",
                        "critical": "🔴 심각함",
                        "blocker": "⚫ 차단됨"
                    }[x]
                )
                
                reproducibility = st.selectbox(
                    "재현성",
                    options=["always", "sometimes", "rarely", "unable"],
                    format_func=lambda x: {
                        "always": "항상 재현됨",
                        "sometimes": "때때로 재현됨",
                        "rarely": "드물게 재현됨",
                        "unable": "재현 불가"
                    }[x]
                )
                
                reproduction_steps = st.text_area(
                    "재현 단계",
                    height=100,
                    help="문제를 재현하는 구체적인 단계를 입력하세요"
                )
                
                expected_behavior = st.text_area(
                    "예상 동작",
                    height=100,
                    help="정상적으로 동작해야 하는 방식을 설명하세요"
                )
                
                actual_behavior = st.text_area(
                    "실제 동작",
                    height=100,
                    help="실제로 발생한 동작을 설명하세요"
                )
        
        with col2:
            # 추가 정보
            anonymous = st.checkbox("익명으로 제출", help="사용자 정보를 숨기고 제출합니다")
            
            rating = st.slider(
                "만족도 평가",
                min_value=1,
                max_value=5,
                value=5,
                help="1점 (매우 불만족) - 5점 (매우 만족)"
            )
            
            # 태그 입력
            tags_input = st.text_input(
                "태그",
                help="쉼표로 구분하여 태그를 입력하세요 (예: UI, 버그, 성능)"
            )
            
            # 첨부 파일
            uploaded_files = st.file_uploader(
                "첨부 파일",
                accept_multiple_files=True,
                type=['png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'log'],
                help="스크린샷, 로그 파일 등을 첨부하세요"
            )
            
            # 환경 정보 자동 수집
            environment_info = {
                "browser": st.session_state.get('browser_info', 'Unknown'),
                "os": st.session_state.get('os_info', 'Unknown'),
                "screen_resolution": st.session_state.get('screen_resolution', 'Unknown'),
                "user_agent": st.session_state.get('user_agent', 'Unknown')
            }
            
            with st.expander("환경 정보"):
                st.json(environment_info)
        
        # 상세 설명
        description = st.text_area(
            "상세 설명 *",
            height=200,
            help="피드백에 대한 상세한 내용을 입력하세요"
        )
        
        # 제출 버튼
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            save_draft = st.form_submit_button("임시 저장", type="secondary")
        
        with col2:
            preview = st.form_submit_button("미리보기", type="secondary")
        
        with col3:
            submitted = st.form_submit_button("제출", type="primary")
        
        # 처리 로직
        if submitted:
            if not title or not description:
                st.error("제목과 상세 설명은 필수 항목입니다.")
                return
            
            # 태그 처리
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
            
            # 파일 업로드 처리
            attachments = []
            if uploaded_files:
                for file in uploaded_files:
                    # 파일 업로드 로직
                    attachment_info = upload_feedback_file(file, auth_token)
                    if attachment_info:
                        attachments.append(attachment_info)
            
            # 피드백 제출
            feedback_data = {
                "feedback_type": feedback_type,
                "title": title,
                "description": description,
                "category": category if category else None,
                "rating": rating,
                "priority": priority,
                "tags": tags,
                "anonymous": anonymous,
                "attachments": attachments,
                "environment": environment_info
            }
            
            # 버그 리포트 추가 정보
            if feedback_type == "bug_report":
                feedback_data.update({
                    "severity": severity,
                    "reproducibility": reproducibility,
                    "reproduction_steps": reproduction_steps,
                    "expected_behavior": expected_behavior,
                    "actual_behavior": actual_behavior
                })
            
            # API 호출
            result = submit_enhanced_feedback(feedback_data, auth_token)
            
            if result.get("success", True):
                st.success("✅ 피드백이 성공적으로 제출되었습니다!")
                st.balloons()
                
                # 활동 로깅
                log_feedback_activity(feedback_data, auth_token)
            else:
                st.error(f"❌ 피드백 제출 실패: {result.get('error', '알 수 없는 오류')}")
        
        elif save_draft:
            # 임시 저장 로직
            draft_data = {
                "feedback_type": feedback_type,
                "title": title,
                "description": description,
                "category": category,
                "rating": rating,
                "priority": priority,
                "tags": tags,
                "created_at": datetime.now().isoformat()
            }
            
            result = save_feedback_draft(draft_data, auth_token)
            
            if result.get("success", True):
                st.success("📝 임시 저장되었습니다.")
            else:
                st.error(f"❌ 임시 저장 실패: {result.get('error', '알 수 없는 오류')}")
        
        elif preview:
            # 미리보기 로직
            st.markdown("### 📋 피드백 미리보기")
            preview_data = {
                "feedback_type": feedback_type,
                "title": title,
                "description": description,
                "category": category,
                "rating": rating,
                "priority": priority,
                "tags": tags,
                "anonymous": anonymous
            }
            
            render_feedback_preview(preview_data)
```

### 4.4 실시간 알림 시스템

#### 4.4.1 WebSocket 기반 알림
```python
class FeedbackNotificationService:
    """피드백 실시간 알림 서비스"""
    
    def __init__(self, websocket_manager, cache_manager):
        self.websocket_manager = websocket_manager
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    async def notify_feedback_submitted(self, feedback_id: int, feedback_data: Dict):
        """새 피드백 제출 알림"""
        notification = {
            "type": "feedback_submitted",
            "feedback_id": feedback_id,
            "title": feedback_data["title"],
            "category": feedback_data["category"],
            "priority": feedback_data["priority"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 관리자에게 알림
        await self.websocket_manager.broadcast_to_role("admin", notification)
        
        # 사용자에게 확인 알림
        user_notification = {
            "type": "feedback_confirmation",
            "message": "피드백이 성공적으로 제출되었습니다.",
            "feedback_id": feedback_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.websocket_manager.send_to_user(
            feedback_data["user_id"], 
            user_notification
        )
    
    async def notify_feedback_updated(self, feedback_id: int, update_data: Dict):
        """피드백 업데이트 알림"""
        notification = {
            "type": "feedback_updated",
            "feedback_id": feedback_id,
            "update_type": update_data["update_type"],  # status_change, comment_added, etc.
            "message": update_data["message"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 피드백 작성자에게 알림
        await self.websocket_manager.send_to_user(
            update_data["user_id"],
            notification
        )
        
        # 구독자에게 알림
        await self.websocket_manager.broadcast_to_subscribers(
            f"feedback_{feedback_id}",
            notification
        )
    
    async def notify_similar_feedback(self, feedback_id: int, similar_feedback: List[Dict]):
        """유사 피드백 알림"""
        notification = {
            "type": "similar_feedback_found",
            "feedback_id": feedback_id,
            "similar_feedback": similar_feedback,
            "message": f"유사한 피드백 {len(similar_feedback)}건을 찾았습니다.",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.websocket_manager.send_to_user(
            feedback_id,  # 피드백 ID를 사용자 ID로 가정
            notification
        )
```

#### 4.4.2 알림 설정 관리
```python
class NotificationSettingsService:
    """알림 설정 관리 서비스"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    def get_user_notification_settings(self, user_id: int) -> Dict[str, Any]:
        """사용자 알림 설정 조회"""
        settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id
        ).first()
        
        if not settings:
            return self.get_default_notification_settings()
        
        return {
            "email_notifications": settings.email_notifications,
            "push_notifications": settings.push_notifications,
            "feedback_submitted": settings.feedback_submitted,
            "feedback_updated": settings.feedback_updated,
            "feedback_commented": settings.feedback_commented,
            "similar_feedback": settings.similar_feedback,
            "digest_frequency": settings.digest_frequency,  # daily, weekly, monthly
            "quiet_hours": {
                "enabled": settings.quiet_hours_enabled,
                "start": settings.quiet_hours_start,
                "end": settings.quiet_hours_end
            }
        }
    
    def update_notification_settings(self, user_id: int, settings: Dict[str, Any]):
        """알림 설정 업데이트"""
        user_settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id
        ).first()
        
        if not user_settings:
            user_settings = UserNotificationSettings(user_id=user_id)
            self.db.add(user_settings)
        
        # 설정 업데이트
        user_settings.email_notifications = settings.get("email_notifications", True)
        user_settings.push_notifications = settings.get("push_notifications", True)
        user_settings.feedback_submitted = settings.get("feedback_submitted", True)
        user_settings.feedback_updated = settings.get("feedback_updated", True)
        user_settings.feedback_commented = settings.get("feedback_commented", True)
        user_settings.similar_feedback = settings.get("similar_feedback", True)
        user_settings.digest_frequency = settings.get("digest_frequency", "daily")
        
        quiet_hours = settings.get("quiet_hours", {})
        user_settings.quiet_hours_enabled = quiet_hours.get("enabled", False)
        user_settings.quiet_hours_start = quiet_hours.get("start", "22:00")
        user_settings.quiet_hours_end = quiet_hours.get("end", "08:00")
        
        self.db.commit()
        
        return user_settings
    
    def get_default_notification_settings(self) -> Dict[str, Any]:
        """기본 알림 설정"""
        return {
            "email_notifications": True,
            "push_notifications": True,
            "feedback_submitted": True,
            "feedback_updated": True,
            "feedback_commented": True,
            "similar_feedback": True,
            "digest_frequency": "daily",
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00"
            }
        }
```

### 4.5 피드백 분석 및 인사이트 강화

#### 4.5.1 고급 분석 기능
```python
class AdvancedFeedbackAnalytics:
    """고급 피드백 분석 서비스"""
    
    def __init__(self, db_session, cache_manager):
        self.db = db_session
        self.cache = cache_manager
        self.logger = logging.getLogger(__name__)
    
    def get_feedback_trends(self, days: int = 30) -> Dict[str, Any]:
        """피드백 트렌드 분석"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 일별 피드백 추이
        daily_feedback = self.db.query(
            func.date(UserFeedback.created_at).label('date'),
            func.count(UserFeedback.id).label('count'),
            func.avg(UserFeedback.rating).label('avg_rating')
        ).filter(
            UserFeedback.created_at >= cutoff_date
        ).group_by(func.date(UserFeedback.created_at)).all()
        
        # 카테고리별 트렌드
        category_trends = self.db.query(
            UserFeedback.category,
            func.date(UserFeedback.created_at).label('date'),
            func.count(UserFeedback.id).label('count')
        ).filter(
            and_(
                UserFeedback.created_at >= cutoff_date,
                UserFeedback.category.isnot(None)
            )
        ).group_by(UserFeedback.category, func.date(UserFeedback.created_at)).all()
        
        # 우선순위별 트렌드
        priority_trends = self.db.query(
            UserFeedback.priority,
            func.date(UserFeedback.created_at).label('date'),
            func.count(UserFeedback.id).label('count')
        ).filter(
            UserFeedback.created_at >= cutoff_date
        ).group_by(UserFeedback.priority, func.date(UserFeedback.created_at)).all()
        
        return {
            "daily_feedback": [
                {
                    "date": str(date),
                    "count": count,
                    "avg_rating": float(avg_rating) if avg_rating else 0
                }
                for date, count, avg_rating in daily_feedback
            ],
            "category_trends": self._group_trend_data(category_trends),
            "priority_trends": self._group_trend_data(priority_trends),
            "period_days": days
        }
    
    def get_feedback_sentiment_analysis(self, days: int = 30) -> Dict[str, Any]:
        """피드백 감성 분석"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 피드백 텍스트 감성 분석
        feedback_texts = self.db.query(UserFeedback.description, UserFeedback.rating).filter(
            UserFeedback.created_at >= cutoff_date
        ).all()
        
        # 감성 분석 로직 (실제로는 NLP 라이브러리 사용)
        sentiment_scores = []
        for description, rating in feedback_texts:
            # 간단한 키워드 기반 감성 분석
            positive_keywords = ['좋', '만족', '훌륭', '감사', '편리', '유용', '빠르']
            negative_keywords = ['나쁘', '불편', '어렵', '느리', '버그', '오류', '문제']
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in description)
            negative_count = sum(1 for keyword in negative_keywords if keyword in description)
            
            if positive_count > negative_count:
                sentiment = "positive"
            elif negative_count > positive_count:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            sentiment_scores.append({
                "sentiment": sentiment,
                "rating": rating,
                "description_length": len(description)
            })
        
        # 감성 분석 결과 집계
        sentiment_summary = {
            "positive": len([s for s in sentiment_scores if s["sentiment"] == "positive"]),
            "negative": len([s for s in sentiment_scores if s["sentiment"] == "negative"]),
            "neutral": len([s for s in sentiment_scores if s["sentiment"] == "neutral"])
        }
        
        # 감성과 평점의 상관관계
        sentiment_rating_correlation = self._calculate_sentiment_rating_correlation(sentiment_scores)
        
        return {
            "sentiment_summary": sentiment_summary,
            "sentiment_rating_correlation": sentiment_rating_correlation,
            "total_analyzed": len(sentiment_scores),
            "period_days": days
        }
    
    def get_feedback_heatmap_data(self, days: int = 30) -> Dict[str, Any]:
        """피드백 히트맵 데이터 생성"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 시간대별 피드백 분포
        hourly_feedback = self.db.query(
            func.extract('hour', UserFeedback.created_at).label('hour'),
            func.extract('dow', UserFeedback.created_at).label('day_of_week'),
            func.count(UserFeedback.id).label('count')
        ).filter(
            UserFeedback.created_at >= cutoff_date
        ).group_by(
            func.extract('hour', UserFeedback.created_at),
            func.extract('dow', UserFeedback.created_at)
        ).all()
        
        # 히트맵 데이터 구조화
        heatmap_data = {}
        for hour, day, count in hourly_feedback:
            if day not in heatmap_data:
                heatmap_data[day] = {}
            heatmap_data[day][hour] = count
        
        return {
            "heatmap_data": heatmap_data,
            "max_count": max([count for _, _, count in hourly_feedback]) if hourly_feedback else 0,
            "period_days": days
        }
    
    def get_feedback_ai_insights(self, days: int = 30) -> Dict[str, Any]:
        """AI 기반 피드백 인사이트"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 최근 피드백 데이터
        recent_feedback = self.db.query(UserFeedback).filter(
            UserFeedback.created_at >= cutoff_date
        ).all()
        
        # 클러스터링을 통한 피드백 그룹화
        feedback_clusters = self._cluster_feedback(recent_feedback)
        
        # 주요 토픽 추출
        topics = self._extract_topics(recent_feedback)
        
        # 예측 분석
        predictions = self._predict_feedback_trends(recent_feedback)
        
        return {
            "clusters": feedback_clusters,
            "topics": topics,
            "predictions": predictions,
            "total_analyzed": len(recent_feedback),
            "period_days": days
        }
    
    def _cluster_feedback(self, feedback_list: List[UserFeedback]) -> List[Dict[str, Any]]:
        """피드백 클러스터링 (간단한 구현)"""
        # 실제로는 K-means, DBSCAN 등 머신러닝 알고리즘 사용
        clusters = []
        
        # 카테고리별 그룹화
        category_groups = {}
        for feedback in feedback_list:
            category = feedback.category or "general"
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(feedback)
        
        for category, items in category_groups.items():
            if len(items) >= 3:  # 3개 이상인 경우에만 클러스터로 간주
                clusters.append({
                    "cluster_id": len(clusters),
                    "category": category,
                    "size": len(items),
                    "avg_rating": sum(f.rating or 0 for f in items) / len(items),
                    "common_keywords": self._extract_common_keywords(items),
                    "sample_items": [
                        {
                            "id": f.id,
                            "title": f.title,
                            "description": f.description[:100] + "..."
                        }
                        for f in items[:3]
                    ]
                })
        
        return clusters
    
    def _extract_topics(self, feedback_list: List[UserFeedback]) -> List[Dict[str, Any]]:
        """주요 토픽 추출"""
        # 실제로는 LDA, NMF 등 토픽 모델링 기법 사용
        # 여기서는 간단한 키워드 빈도 분석 사용
        
        all_text = " ".join([f.title + " " + f.description for f in feedback_list])
        
        # 키워드 추출 (간단한 구현)
        common_words = {'의', '가', '을', '를', '이', '가', '은', '는', '과', '와', '및', '등'}
        words = [word for word in all_text.split() if word not in common_words and len(word) > 1]
        
        # 단어 빈도 계산
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 상위 토픽 추출
        top_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [
            {
                "topic": word,
                "frequency": freq,
                "relevance_score": freq / len(feedback_list)
            }
            for word, freq in top_topics
        ]
    
    def _predict_feedback_trends(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """피드백 트렌드 예측"""
        # 실제로는 시계열 분석, 회귀 모델 등 사용
        # 여기서는 간단한 추세 기반 예측
        
        # 일별 피드백 수 계산
        daily_counts = {}
        for feedback in feedback_list:
            date = feedback.created_at.date()
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        if len(daily_counts) < 7:
            return {"trend": "insufficient_data"}
        
        # 최근 7일 평균 vs 이전 7일 평균
        dates = sorted(daily_counts.keys())
        recent_avg = sum(daily_counts[date] for date in dates[-7:]) / 7
        previous_avg = sum(daily_counts[date] for date in dates[-14:-7]) / 7 if len(dates) >= 14 else recent_avg
        
        trend_direction = "stable"
        if recent_avg > previous_avg * 1.2:
            trend_direction = "increasing"
        elif recent_avg < previous_avg * 0.8:
            trend_direction = "decreasing"
        
        return {
            "trend": trend_direction,
            "recent_average": recent_avg,
            "previous_average": previous_avg,
            "confidence": "medium"  # 실제로는 통계적 신뢰도 계산
        }
```

## 5. 구현 로드맵

### 5.1 단계별 구현 계획

#### 5.1.1 1단계: 기본 기능 강화 (2주)
- **데이터 모델 확장**
  - 첨부 파일 지원
  - 태그 기능
  - 익명 피드백
  - 피드백 댓글

- **API 엔드포인트 확장**
  - 첨부 파일 업로드
  - 피드백 검색
  - 표준 응답 형식 적용

- **프론트엔드 개선**
  - 첨부 파일 업로드 UI
  - 태그 입력 기능
  - 익명 제출 옵션

#### 5.1.2 2단계: 고급 기능 구현 (3주)
- **실시간 알림 시스템**
  - WebSocket 기반 알림
  - 알림 설정 관리
  - 이메일/Push 알림

- **고급 분석 기능**
  - 피드백 트렌드 분석
  - 감성 분석
  - 히트맵 시각화

- **AI 기반 기능**
  - 피드백 클러스터링
  - 토픽 추출
  - 트렌드 예측

#### 5.1.3 3단계: 자동화 및 지능화 (2주)
- **자동 분류 및 라우팅**
  - 피드백 자동 카테고리 분류
  - 우선순위 자동 할당
  - 담당자 자동 지정

- **스마트 추천 시스템**
  - 유사 피드백 추천
  - 솔루션 제안
  - 자동 응답 초안

- **대시보드 고도화**
  - 실시간 모니터링
  - 인터랙티브 리포트
  - 사용자 정의 위젯

### 5.2 기술적 구현 고려사항

#### 5.2.1 성능 최적화
- **데이터베이스 최적화**
  - 적절한 인덱스 설계
  - 파티셔닝 전략
  - 캐싱 계층 구축

- **API 성능**
  - 비동기 처리
  - 페이지네이션 최적화
  - 응답 시간 모니터링

- **프론트엔드 성능**
  - 지연 로딩
  - 가상 스크롤
  - 이미지 최적화

#### 5.2.2 확장성 고려
- **마이크로서비스 아키텍처**
  - 피드백 서비스 분리
  - 이벤트 기반 통신
  - 독립적 배포

- **클라우드 네이티브**
  - 컨테이너화
  - 오토스케일링
  - 관리형 서비스 활용

## 6. 성공 지표 및 KPI

### 6.1 사용자 참여 지표
- **피드백 제출율**: 활성 사용자 대비 피드백 제출 비율 목표 15%
- **피드백 품질**: 평균 평점 4.0/5.0 이상
- **반복 제출율**: 동일 사용자의 재피드백 비율 30% 이상
- **응답 만족도**: 피드백 응답에 대한 만족도 85% 이상

### 6.2 운영 효율 지표
- **처리 시간**: 평균 피드백 처리 시간 24시간 이내
- **자동화율**: 자동 분류/라우팅률 70% 이상
- **재현율**: 버그 리포트 재현율 60% 이상
- **해결율**: 월간 피드백 해결률 80% 이상

### 6.3 비즈니스 가치 지표
- **제품 개선 기여도**: 피드백 기반 제품 개선 건수 월 10건 이상
- **사용자 유지율**: 피드백 제출자의 재방문율 80% 이상
- **CS 비용 절감**: 피드백 시스템을 통한 고객 지원 비용 20% 절감
- **제품 만족도**: 전체 제품 만족도 10% 향상

## 7. 결론 및 권장 사항

### 7.1 현재 상태 요약

InsiteChart의 피드백 시스템은 기본적인 기능을 잘 갖추고 있으며, 다음과 같은 강점이 있습니다:

1. **완전한 CRUD 연산**: 피드백 생성, 조회, 수정, 삭제 기능이 모두 구현됨
2. **역할 기반 접근 제어**: 사용자와 관리자 권한이 명확히 분리됨
3. **분석 기능**: 기본적인 통계 및 인사이트 기능 제공
4. **활동 추적**: 사용자 행동 및 활동 로깅 기능
5. **국제화 지원**: 한국어 UI 및 다국어 처리 기능

### 7.2 개선 필요 사항

다음과 같은 개선이 필요합니다:

1. **고급 기능 부재**: 첨부 파일, 태깅, 익명 피드백 등 고급 기능 부족
2. **실시간 기능 부재**: 실시간 알림, 협업 기능 부재
3. **분석 기능 제한**: 고급 분석, AI 기반 인사이트 기능 부족
4. **사용자 경험**: 모바일 최적화, 반응형 디자인 개선 필요
5. **자동화 부족**: 수동 처리가 많아 운영 효율이 낮음

### 7.3 최종 권장 사항

#### 7.3.1 단기적 개선 (1-2개월)
1. **핵심 기능 강화**: 첨부 파일, 태깅, 검색 기능 구현
2. **UI/UX 개선**: 반응형 디자인, 모바일 최적화
3. **API 표준화**: 표준 응답 형식, 에러 처리 개선
4. **실시간 알림**: WebSocket 기반 알림 시스템 구현

#### 7.3.2 중기적 개선 (3-6개월)
1. **AI 기반 분석**: 감성 분석, 토픽 추출, 트렌드 예측
2. **자동화 시스템**: 자동 분류, 라우팅, 답변 제안
3. **고급 대시보드**: 실시간 모니터링, 인터랙티브 리포트
4. **통합 확장**: 타 시스템과의 연동, API 확장

#### 7.3.3 장기적 발전 (6개월 이상)
1. **마이크로서비스화**: 피드백 시스템 독립적 운영
2. **머신러닝 고도화**: 정교한 예측 모델, 개인화 추천
3. **생태계 구축**: 제3자 개발자를 위한 플러그인 생태계
4. **글로벌 확장**: 다국어 지원, 지역화 전략

이러한 개선 방안을 통해 InsiteChart의 피드백 시스템는 사용자 참여를 극대화하고, 제품 개선에 실질적인 기여를 하며, 운영 효율을 크게 향상시킬 수 있을 것입니다.