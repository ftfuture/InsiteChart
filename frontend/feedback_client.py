"""
Frontend client for user feedback system.
"""

import streamlit as st
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class FeedbackClient:
    """Client for interacting with the feedback API."""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.api_base = f"{backend_url}/api/v1/feedback"
    
    def submit_feedback(
        self,
        feedback_type: str,
        title: str,
        description: str,
        category: Optional[str] = None,
        rating: Optional[int] = None,
        priority: str = "medium",
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit new feedback."""
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        data = {
            "feedback_type": feedback_type,
            "title": title,
            "description": description,
            "category": category,
            "rating": rating,
            "priority": priority
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/submit",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def get_my_feedback(
        self,
        limit: int = 50,
        offset: int = 0,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's feedback."""
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            response = requests.get(
                f"{self.api_base}/my-feedback",
                params={"limit": limit, "offset": offset},
                headers=headers
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def log_activity(
        self,
        activity_type: str,
        action: str,
        feature_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration: Optional[int] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log user activity."""
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        data = {
            "activity_type": activity_type,
            "action": action,
            "feature_name": feature_name,
            "metadata": metadata,
            "duration": duration
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/log-activity",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def get_activity_summary(
        self,
        days: int = 30,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user activity summary."""
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            response = requests.get(
                f"{self.api_base}/my-activity-summary",
                params={"days": days},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}


# Global feedback client instance
feedback_client = FeedbackClient()


def render_feedback_form(auth_token: Optional[str] = None):
    """Render feedback submission form."""
    st.markdown("### 📝 피드백 제출")
    
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
        
        # Priority
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
        
        # Rating (for feature satisfaction)
        rating = st.slider(
            "만족도 평가",
            min_value=1,
            max_value=5,
            value=5,
            help="1점 (매우 불만족) - 5점 (매우 만족)"
        )
        
        # Title
        title = st.text_input(
            "제목",
            max_chars=255,
            help="피드백의 간결한 제목을 입력하세요"
        )
        
        # Description
        description = st.text_area(
            "상세 설명",
            height=150,
            help="피드백에 대한 상세한 내용을 입력하세요"
        )
        
        # Submit button
        submitted = st.form_submit_button("피드백 제출", type="primary")
        
        if submitted:
            if not title or not description:
                st.error("제목과 상세 설명은 필수 항목입니다.")
                return
            
            # Submit feedback
            result = feedback_client.submit_feedback(
                feedback_type=feedback_type,
                title=title,
                description=description,
                category=category if category else None,
                rating=rating,
                priority=priority,
                auth_token=auth_token
            )
            
            if result.get("success", True):
                st.success("✅ 피드백이 성공적으로 제출되었습니다!")
                st.balloons()
                
                # Log activity
                feedback_client.log_activity(
                    activity_type="feedback_submitted",
                    action="submit",
                    feature_name=category,
                    metadata={
                        "feedback_type": feedback_type,
                        "rating": rating,
                        "priority": priority
                    },
                    auth_token=auth_token
                )
            else:
                st.error(f"❌ 피드백 제출 실패: {result.get('error', '알 수 없는 오류')}")


def render_feedback_history(auth_token: Optional[str] = None):
    """Render user's feedback history."""
    st.markdown("### 📋 내 피드백 내역")
    
    # Get user's feedback
    result = feedback_client.get_my_feedback(auth_token=auth_token)
    
    if not result.get("success", False):
        st.error(f"피드백 내역을 불러올 수 없습니다: {result.get('error', '알 수 없는 오류')}")
        return
    
    feedback_list = result.get("data", [])
    
    if not feedback_list:
        st.info("제출한 피드백이 없습니다.")
        return
    
    # Display feedback
    for feedback in feedback_list:
        with st.expander(f"📝 {feedback['title']} ({feedback['status']})"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Feedback details
                st.markdown(f"**유형:** {feedback['feedback_type']}")
                if feedback['category']:
                    st.markdown(f"**카테고리:** {feedback['category']}")
                st.markdown(f"**우선순위:** {feedback['priority']}")
                st.markdown(f"**상태:** {feedback['status']}")
                
                if feedback['rating']:
                    stars = "⭐" * feedback['rating']
                    st.markdown(f"**만족도:** {stars} ({feedback['rating']}/5)")
                
                st.markdown("**상세 설명:**")
                st.write(feedback['description'])
                
                if feedback['response']:
                    st.markdown("**관리자 답변:**")
                    st.info(feedback['response'])
            
            with col2:
                # Timestamps
                created_at = datetime.fromisoformat(feedback['created_at'].replace('Z', '+00:00'))
                st.markdown(f"**제출일:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                
                if feedback['responded_at']:
                    responded_at = datetime.fromisoformat(feedback['responded_at'].replace('Z', '+00:00'))
                    st.markdown(f"**답변일:** {responded_at.strftime('%Y-%m-%d %H:%M')}")


def render_activity_summary(auth_token: Optional[str] = None):
    """Render user activity summary."""
    st.markdown("### 📊 활동 요약")
    
    # Get activity summary
    result = feedback_client.get_activity_summary(auth_token=auth_token)
    
    if "error" in result:
        st.error(f"활동 요약을 불러올 수 없습니다: {result['error']}")
        return
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "총 활동 수",
            result.get("total_activities", 0),
            delta=f"최근 {result.get('period_days', 30)}일"
        )
    
    with col2:
        st.metric(
            "가장 많이 사용한 기능",
            result.get("most_used_features", [{}])[0].get("feature", "없음") if result.get("most_used_features") else "없음"
        )
    
    with col3:
        st.metric(
            "제출한 피드백",
            result.get("feedback_submitted", 0)
        )
    
    # Activities by type
    if result.get("activities_by_type"):
        st.markdown("#### 활동 유형별 분포")
        
        activities_by_type = result["activities_by_type"]
        activity_types = [item["type"] for item in activities_by_type]
        activity_counts = [item["count"] for item in activities_by_type]
        
        # Create a simple bar chart using Streamlit's native chart
        activity_data = {
            "활동 유형": activity_types,
            "횟수": activity_counts
        }
        st.bar_chart(activity_data)
    
    # Most used features
    if result.get("most_used_features"):
        st.markdown("#### 가장 많이 사용한 기능")
        
        for i, feature in enumerate(result["most_used_features"][:5]):
            st.write(f"{i+1}. **{feature['feature']}** - {feature['usage_count']}회 사용")
            if feature.get('avg_duration'):
                avg_minutes = feature['avg_duration'] / 60
                st.write(f"   평균 사용 시간: {avg_minutes:.1f}분")


def render_feedback_dashboard(auth_token: Optional[str] = None):
    """Render complete feedback dashboard."""
    st.markdown("## 💬 피드백 센터")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📝 피드백 제출", "📋 피드백 내역", "📊 활동 요약"])
    
    with tab1:
        render_feedback_form(auth_token)
    
    with tab2:
        render_feedback_history(auth_token)
    
    with tab3:
        render_activity_summary(auth_token)


def auto_log_activity(
    activity_type: str,
    action: str,
    feature_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    auth_token: Optional[str] = None
):
    """Automatically log user activity (call this from various parts of the app)."""
    try:
        feedback_client.log_activity(
            activity_type=activity_type,
            action=action,
            feature_name=feature_name,
            metadata=metadata,
            auth_token=auth_token
        )
    except Exception as e:
        # Silently fail to not disrupt user experience
        print(f"Failed to log activity: {e}")