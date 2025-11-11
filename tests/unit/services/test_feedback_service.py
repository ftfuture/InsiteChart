"""
피드백 서비스 단위 테스트

이 모듈은 피드백 서비스의 개별 기능을 테스트합니다.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.services.feedback_service import FeedbackService
from backend.models.database_models import (
    UserFeedback, UserActivity, FeatureUsage, UserBehavior, User
)


class TestFeedbackService:
    """피드백 서비스 단위 테스트 클래스"""
    
    @pytest.fixture
    def mock_db_session(self):
        """모의 데이터베이스 세션 픽스처"""
        # 인메모리 SQLite 데이터베이스 사용
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        # 모델 생성
        from backend.models.database_models import Base
        Base.metadata.create_all(engine)
        
        # 세션 생성
        session = Session(bind=engine)
        yield session
        session.close()
    
    @pytest.fixture
    def feedback_service(self, mock_db_session):
        """피드백 서비스 픽스처"""
        with patch('backend.services.feedback_service.SessionLocal', return_value=mock_db_session):
            service = FeedbackService()
            service.db = mock_db_session
            return service
    
    @pytest.fixture
    def sample_user(self, mock_db_session):
        """샘플 사용자 픽스처"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role="user",
            is_active=True,
            created_at=datetime.utcnow()
        )
        mock_db_session.add(user)
        mock_db_session.commit()
        mock_db_session.refresh(user)
        return user
    
    @pytest.fixture
    def sample_feedback(self, sample_user):
        """샘플 피드백 픽스처"""
        return {
            "user_id": sample_user.id,
            "feedback_type": "bug_report",
            "title": "Test Bug Report",
            "description": "This is a test bug report with detailed description",
            "category": "ui",
            "rating": 4,
            "priority": "medium"
        }
    
    def test_create_feedback_success(self, feedback_service, sample_feedback):
        """피드백 생성 성공 테스트"""
        feedback = feedback_service.create_feedback(**sample_feedback)
        
        assert feedback is not None
        assert feedback.id is not None
        assert feedback.user_id == sample_feedback["user_id"]
        assert feedback.feedback_type == sample_feedback["feedback_type"]
        assert feedback.title == sample_feedback["title"]
        assert feedback.description == sample_feedback["description"]
        assert feedback.category == sample_feedback["category"]
        assert feedback.rating == sample_feedback["rating"]
        assert feedback.priority == sample_feedback["priority"]
        assert feedback.status == "open"
        assert feedback.created_at is not None
        assert feedback.updated_at is not None
    
    def test_create_feedback_minimal_data(self, feedback_service, sample_user):
        """최소 데이터로 피드백 생성 테스트"""
        minimal_feedback = {
            "user_id": sample_user.id,
            "feedback_type": "general",
            "title": "Simple Feedback",
            "description": "Simple description"
        }
        
        feedback = feedback_service.create_feedback(**minimal_feedback)
        
        assert feedback is not None
        assert feedback.user_id == sample_user.id
        assert feedback.feedback_type == "general"
        assert feedback.title == "Simple Feedback"
        assert feedback.description == "Simple description"
        assert feedback.category is None
        assert feedback.rating is None
        assert feedback.priority == "medium"  # 기본값
        assert feedback.status == "open"
    
    def test_get_feedback_by_id_success(self, feedback_service, sample_feedback):
        """ID로 피드백 가져오기 성공 테스트"""
        # 피드백 생성
        created_feedback = feedback_service.create_feedback(**sample_feedback)
        
        # ID로 피드백 조회
        retrieved_feedback = feedback_service.get_feedback_by_id(created_feedback.id)
        
        assert retrieved_feedback is not None
        assert retrieved_feedback.id == created_feedback.id
        assert retrieved_feedback.user_id == sample_feedback["user_id"]
        assert retrieved_feedback.title == sample_feedback["title"]
    
    def test_get_feedback_by_id_not_found(self, feedback_service):
        """존재하지 않는 ID로 피드백 가져오기 테스트"""
        non_existent_id = 99999
        feedback = feedback_service.get_feedback_by_id(non_existent_id)
        
        assert feedback is None
    
    def test_get_user_feedback_success(self, feedback_service, sample_user, sample_feedback):
        """사용자 피드백 가져오기 성공 테스트"""
        # 여러 피드백 생성
        feedback1 = feedback_service.create_feedback(**sample_feedback)
        
        feedback2_data = sample_feedback.copy()
        feedback2_data["title"] = "Second Feedback"
        feedback2 = feedback_service.create_feedback(**feedback2_data)
        
        # 사용자 피드백 조회
        user_feedbacks = feedback_service.get_user_feedback(sample_user.id)
        
        assert len(user_feedbacks) == 2
        assert user_feedbacks[0].id == feedback2.id  # 최신순 정렬
        assert user_feedbacks[1].id == feedback1.id
        assert all(f.user_id == sample_user.id for f in user_feedbacks)
    
    def test_get_user_feedback_with_pagination(self, feedback_service, sample_user, sample_feedback):
        """페이지네이션과 함께 사용자 피드백 가져오기 테스트"""
        # 여러 피드백 생성
        for i in range(10):
            feedback_data = sample_feedback.copy()
            feedback_data["title"] = f"Feedback {i}"
            feedback_service.create_feedback(**feedback_data)
        
        # 페이지네이션으로 조회
        first_page = feedback_service.get_user_feedback(sample_user.id, limit=5, offset=0)
        second_page = feedback_service.get_user_feedback(sample_user.id, limit=5, offset=5)
        
        assert len(first_page) == 5
        assert len(second_page) == 5
        
        # 중복 없음 확인
        first_page_ids = {f.id for f in first_page}
        second_page_ids = {f.id for f in second_page}
        assert len(first_page_ids.intersection(second_page_ids)) == 0
    
    def test_get_feedback_by_status_success(self, feedback_service, sample_feedback):
        """상태별 피드백 가져오기 성공 테스트"""
        # 피드백 생성
        feedback1 = feedback_service.create_feedback(**sample_feedback)
        
        # 상태 업데이트
        feedback_service.update_feedback_status(feedback1.id, "in_progress")
        
        # 상태별 피드백 조회
        open_feedbacks = feedback_service.get_feedback_by_status("open")
        in_progress_feedbacks = feedback_service.get_feedback_by_status("in_progress")
        
        assert len(open_feedbacks) == 0  # 업데이트된 피드백은 open 상태가 아님
        assert len(in_progress_feedbacks) == 1
        assert in_progress_feedbacks[0].id == feedback1.id
    
    def test_get_feedback_by_type_success(self, feedback_service, sample_feedback):
        """타입별 피드백 가져오기 성공 테스트"""
        # 다른 타입의 피드백 생성
        feedback1 = feedback_service.create_feedback(**sample_feedback)
        
        feedback2_data = sample_feedback.copy()
        feedback2_data["feedback_type"] = "feature_request"
        feedback2_data["title"] = "Feature Request"
        feedback2 = feedback_service.create_feedback(**feedback2_data)
        
        # 타입별 피드백 조회
        bug_reports = feedback_service.get_feedback_by_type("bug_report")
        feature_requests = feedback_service.get_feedback_by_type("feature_request")
        
        assert len(bug_reports) == 1
        assert len(feature_requests) == 1
        assert bug_reports[0].id == feedback1.id
        assert feature_requests[0].id == feedback2.id
    
    def test_update_feedback_status_success(self, feedback_service, sample_feedback):
        """피드백 상태 업데이트 성공 테스트"""
        # 피드백 생성
        feedback = feedback_service.create_feedback(**sample_feedback)
        original_status = feedback.status
        original_updated_at = feedback.updated_at
        
        # 상태 업데이트
        updated_feedback = feedback_service.update_feedback_status(
            feedback.id, 
            "resolved", 
            responded_by=sample_feedback["user_id"],
            response="Issue has been resolved"
        )
        
        assert updated_feedback is not None
        assert updated_feedback.id == feedback.id
        assert updated_feedback.status == "resolved"
        assert updated_feedback.status != original_status
        assert updated_feedback.responded_by == sample_feedback["user_id"]
        assert updated_feedback.response == "Issue has been resolved"
        assert updated_feedback.responded_at is not None
        assert updated_feedback.updated_at > original_updated_at
    
    def test_update_feedback_status_not_found(self, feedback_service):
        """존재하지 않는 피드백 상태 업데이트 테스트"""
        non_existent_id = 99999
        updated_feedback = feedback_service.update_feedback_status(non_existent_id, "resolved")
        
        assert updated_feedback is None
    
    def test_log_activity_success(self, feedback_service, sample_user):
        """활동 로깅 성공 테스트"""
        activity = feedback_service.log_activity(
            user_id=sample_user.id,
            activity_type="feature_usage",
            action="view_chart",
            feature_name="stock_chart",
            metadata={"symbol": "AAPL", "timeframe": "1d"},
            duration=120
        )
        
        assert activity is not None
        assert activity.id is not None
        assert activity.user_id == sample_user.id
        assert activity.activity_type == "feature_usage"
        assert activity.action == "view_chart"
        assert activity.feature_name == "stock_chart"
        assert activity.metadata["symbol"] == "AAPL"
        assert activity.metadata["timeframe"] == "1d"
        assert activity.duration == 120
        assert activity.created_at is not None
    
    def test_log_activity_minimal_data(self, feedback_service, sample_user):
        """최소 데이터로 활동 로깅 테스트"""
        activity = feedback_service.log_activity(
            user_id=sample_user.id,
            activity_type="login",
            action="user_login"
        )
        
        assert activity is not None
        assert activity.user_id == sample_user.id
        assert activity.activity_type == "login"
        assert activity.action == "user_login"
        assert activity.feature_name is None
        assert activity.metadata == {}
        assert activity.duration is None
    
    def test_update_feature_usage_new_feature(self, feedback_service):
        """새 기능 사용 통계 업데이트 테스트"""
        feature = feedback_service.update_feature_usage("new_feature", duration=100)
        
        assert feature is not None
        assert feature.feature_name == "new_feature"
        assert feature.usage_count == 1
        assert feature.unique_users == 1
        assert feature.avg_duration == 100
        assert feature.last_used is not None
    
    def test_update_feature_usage_existing_feature(self, feedback_service):
        """기존 기능 사용 통계 업데이트 테스트"""
        # 첫 번째 사용
        feature1 = feedback_service.update_feature_usage("existing_feature", duration=100)
        
        # 두 번째 사용
        feature2 = feedback_service.update_feature_usage("existing_feature", duration=200)
        
        assert feature1.id == feature2.id  # 동일한 기능 레코드
        assert feature2.usage_count == 2
        assert feature2.unique_users == 1
        assert feature2.avg_duration == 150  # (100 + 200) / 2
        assert feature2.last_used > feature1.last_used
    
    def test_get_feature_usage_stats_success(self, feedback_service, sample_user):
        """기능 사용 통계 가져오기 성공 테스트"""
        # 다른 기능 사용 기록
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "feature_a", duration=100)
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "feature_b", duration=150)
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "feature_a", duration=120)
        
        # 기능 사용 통계 조회
        stats = feedback_service.get_feature_usage_stats(limit=10)
        
        assert len(stats) >= 2
        # 사용 횟수로 내림차순 정렬
        assert stats[0].usage_count >= stats[1].usage_count
    
    def test_track_user_behavior_success(self, feedback_service, sample_user):
        """사용자 행동 추적 성공 테스트"""
        behavior_data = {
            "click_position": {"x": 100, "y": 200},
            "element_type": "button",
            "page": "dashboard"
        }
        
        context = {
            "page_url": "/dashboard",
            "referrer": "/login"
        }
        
        behavior = feedback_service.track_user_behavior(
            user_id=sample_user.id,
            behavior_type="click",
            behavior_data=behavior_data,
            context=context
        )
        
        assert behavior is not None
        assert behavior.id is not None
        assert behavior.user_id == sample_user.id
        assert behavior.behavior_type == "click"
        assert behavior.behavior_metadata["click_position"]["x"] == 100
        assert behavior.behavior_metadata["element_type"] == "button"
        assert behavior.context["page_url"] == "/dashboard"
        assert behavior.context["referrer"] == "/login"
        assert behavior.created_at is not None
    
    def test_get_user_activity_summary_success(self, feedback_service, sample_user):
        """사용자 활동 요약 가져오기 성공 테스트"""
        # 다양한 활동 기록
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "chart", duration=100)
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "table", duration=50)
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "chart", duration=120)
        feedback_service.log_activity(sample_user.id, "login", "user_login")
        
        feedback_data = {
            "user_id": sample_user.id,
            "feedback_type": "bug_report",
            "title": "Test Bug",
            "description": "Bug description"
        }
        feedback_service.create_feedback(**feedback_data)
        
        # 활동 요약 조회
        summary = feedback_service.get_user_activity_summary(sample_user.id)
        
        assert "total_activities" in summary
        assert "activities_by_type" in summary
        assert "most_used_features" in summary
        assert "feedback_submitted" in summary
        assert "period_days" in summary
        
        assert summary["total_activities"] == 5  # 4 활동 + 1 피드백
        assert summary["feedback_submitted"] == 1
        
        # 활동 타입별 그룹화 확인
        activity_types = {item["type"]: item["count"] for item in summary["activities_by_type"]}
        assert activity_types.get("feature_usage", 0) == 3
        assert activity_types.get("login", 0) == 1
        
        # 가장 많이 사용된 기능 확인
        most_used = summary["most_used_features"]
        assert len(most_used) >= 1
        assert most_used[0]["feature"] == "chart"  # 가장 많이 사용된 기능
        assert most_used[0]["usage_count"] == 2
    
    def test_get_platform_analytics_success(self, feedback_service, sample_user):
        """플랫폼 분석 가져오기 성공 테스트"""
        # 다양한 활동 및 피드백 생성
        feedback_service.log_activity(sample_user.id, "feature_usage", "view", "chart")
        feedback_service.log_activity(sample_user.id, "login", "user_login")
        
        feedback_data = {
            "user_id": sample_user.id,
            "feedback_type": "bug_report",
            "title": "Test Bug",
            "description": "Bug description",
            "rating": 3
        }
        feedback_service.create_feedback(**feedback_data)
        
        # 플랫폼 분석 조회
        analytics = feedback_service.get_platform_analytics()
        
        assert "active_users" in analytics
        assert "total_activities" in analytics
        assert "feedback_summary" in analytics
        assert "feature_popularity" in analytics
        assert "period_days" in analytics
        
        assert analytics["active_users"] == 1
        assert analytics["total_activities"] == 3  # 2 활동 + 1 피드백
        
        # 피드백 요약 확인
        feedback_summary = analytics["feedback_summary"]
        assert len(feedback_summary) >= 1
        bug_report_summary = next(
            (item for item in feedback_summary 
             if item["type"] == "bug_report" and item["status"] == "open"), 
            None
        )
        assert bug_report_summary is not None
        assert bug_report_summary["count"] == 1
        assert bug_report_summary["avg_rating"] == 3
    
    def test_get_feedback_insights_success(self, feedback_service, sample_user):
        """피드백 인사이트 가져오기 성공 테스트"""
        # 다양한 피드백 생성
        feedback_data1 = {
            "user_id": sample_user.id,
            "feedback_type": "bug_report",
            "title": "UI Bug",
            "description": "UI issue",
            "category": "ui",
            "rating": 2,
            "priority": "high"
        }
        feedback_service.create_feedback(**feedback_data1)
        
        feedback_data2 = {
            "user_id": sample_user.id,
            "feedback_type": "feature_request",
            "title": "New Feature",
            "description": "Feature request",
            "category": "performance",
            "rating": 4,
            "priority": "medium"
        }
        feedback_service.create_feedback(**feedback_data2)
        
        # 피드백 인사이트 조회
        insights = feedback_service.get_feedback_insights()
        
        assert "feedback_by_category" in insights
        assert "high_priority_feedback" in insights
        assert "unresolved_feedback" in insights
        assert "period_days" in insights
        
        # 카테고리별 피드백 확인
        feedback_by_category = insights["feedback_by_category"]
        assert len(feedback_by_category) >= 2
        
        ui_category = next(
            (item for item in feedback_by_category if item["category"] == "ui"), 
            None
        )
        assert ui_category is not None
        assert ui_category["count"] == 1
        assert ui_category["avg_rating"] == 2
        
        # 높은 우선순위 피드백 확인
        high_priority = insights["high_priority_feedback"]
        assert len(high_priority) >= 1
        assert high_priority[0]["priority"] == "high"
        
        # 미해결 피드백 확인
        unresolved = insights["unresolved_feedback"]
        assert len(unresolved) >= 2  # 모든 피드백은 기본적으로 "open" 상태