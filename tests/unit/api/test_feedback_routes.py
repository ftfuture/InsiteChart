"""
피드백 API 라우트 단위 테스트

이 모듈은 피드백 관련 API 엔드포인트의 개별 기능을 테스트합니다.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.api.feedback_routes import router


class TestFeedbackRoutes:
    """피드백 API 라우트 단위 테스트 클래스"""
    
    @pytest.fixture
    def app(self):
        """FastAPI 애플리케이션 픽스처"""
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트 픽스처"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_feedback_service(self):
        """모의 피드백 서비스 픽스처"""
        service = MagicMock()
        service.create_feedback = MagicMock()
        service.get_feedback_by_id = MagicMock()
        service.get_user_feedback = MagicMock()
        service.get_feedback_by_status = MagicMock()
        service.get_feedback_by_type = MagicMock()
        service.update_feedback_status = MagicMock()
        service.log_activity = MagicMock()
        service.track_user_behavior = MagicMock()
        service.get_user_activity_summary = MagicMock()
        service.get_platform_analytics = MagicMock()
        service.get_feedback_insights = MagicMock()
        service.get_feature_usage_stats = MagicMock()
        return service
    
    @pytest.fixture
    def regular_user(self):
        """일반 사용자 픽스처"""
        return {"sub": 123, "role": "user"}
    
    @pytest.fixture
    def admin_user(self):
        """관리자 사용자 픽스처"""
        return {"sub": 456, "role": "admin"}
    
    @pytest.fixture
    def sample_feedback_data(self):
        """샘플 피드백 데이터 픽스처"""
        return {
            "feedback_type": "bug_report",
            "title": "Test Bug Report",
            "description": "This is a detailed bug report for testing purposes",
            "category": "ui",
            "rating": 4,
            "priority": "medium"
        }
    
    @pytest.fixture
    def sample_activity_data(self):
        """샘플 활동 데이터 픽스처"""
        return {
            "activity_type": "feature_usage",
            "feature_name": "stock_chart",
            "action": "view",
            "metadata": {"symbol": "AAPL", "timeframe": "1d"},
            "duration": 120
        }
    
    @pytest.fixture
    def sample_behavior_data(self):
        """샘플 행동 데이터 픽스처"""
        return {
            "behavior_type": "click",
            "behavior_data": {
                "element": "chart_button",
                "position": {"x": 100, "y": 200}
            },
            "context": {
                "page": "dashboard",
                "section": "charts"
            }
        }
    
    def test_submit_feedback_success(self, client, mock_feedback_service, sample_feedback_data, regular_user):
        """피드백 제출 성공 테스트"""
        # 모의 피드백 객체 설정
        mock_feedback = MagicMock()
        mock_feedback.id = 1
        mock_feedback.user_id = regular_user["sub"]
        mock_feedback.feedback_type = sample_feedback_data["feedback_type"]
        mock_feedback.title = sample_feedback_data["title"]
        mock_feedback.description = sample_feedback_data["description"]
        mock_feedback.category = sample_feedback_data["category"]
        mock_feedback.rating = sample_feedback_data["rating"]
        mock_feedback.priority = sample_feedback_data["priority"]
        mock_feedback.status = "open"
        mock_feedback.response = None
        mock_feedback.responded_by = None
        mock_feedback.responded_at = None
        mock_feedback.created_at = datetime.utcnow()
        mock_feedback.updated_at = datetime.utcnow()
        
        mock_feedback_service.create_feedback.return_value = mock_feedback
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.post(
                "/api/v1/feedback/submit",
                json=sample_feedback_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["user_id"] == regular_user["sub"]
            assert data["feedback_type"] == sample_feedback_data["feedback_type"]
            assert data["title"] == sample_feedback_data["title"]
            assert data["description"] == sample_feedback_data["description"]
            assert data["category"] == sample_feedback_data["category"]
            assert data["rating"] == sample_feedback_data["rating"]
            assert data["priority"] == sample_feedback_data["priority"]
            assert data["status"] == "open"
            assert "created_at" in data
            assert "updated_at" in data
            
            # 서비스 호출 확인
            mock_feedback_service.create_feedback.assert_called_once_with(
                user_id=regular_user["sub"],
                feedback_type=sample_feedback_data["feedback_type"],
                title=sample_feedback_data["title"],
                description=sample_feedback_data["description"],
                category=sample_feedback_data["category"],
                rating=sample_feedback_data["rating"],
                priority=sample_feedback_data["priority"]
            )
    
    def test_submit_feedback_error(self, client, mock_feedback_service, sample_feedback_data, regular_user):
        """피드백 제출 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_feedback_service.create_feedback.side_effect = Exception("Database error")
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.post(
                "/api/v1/feedback/submit",
                json=sample_feedback_data
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to submit feedback" in data["detail"]
    
    def test_get_my_feedback_success(self, client, mock_feedback_service, regular_user):
        """내 피드백 가져오기 성공 테스트"""
        # 모의 피드백 목록 설정
        mock_feedback_list = []
        for i in range(5):
            feedback = MagicMock()
            feedback.id = i + 1
            feedback.user_id = regular_user["sub"]
            feedback.feedback_type = "bug_report"
            feedback.title = f"Bug Report {i + 1}"
            feedback.description = f"Description {i + 1}"
            feedback.category = "ui"
            feedback.rating = 4
            feedback.priority = "medium"
            feedback.status = "open"
            feedback.response = None
            feedback.responded_by = None
            feedback.responded_at = None
            feedback.created_at = datetime.utcnow()
            feedback.updated_at = datetime.utcnow()
            mock_feedback_list.append(feedback)
        
        mock_feedback_service.get_user_feedback.return_value = mock_feedback_list
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/my-feedback")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5
            
            for i, feedback_data in enumerate(data):
                assert feedback_data["id"] == i + 1
                assert feedback_data["user_id"] == regular_user["sub"]
                assert feedback_data["title"] == f"Bug Report {i + 1}"
                assert feedback_data["status"] == "open"
            
            # 서비스 호출 확인
            mock_feedback_service.get_user_feedback.assert_called_once_with(
                user_id=regular_user["sub"],
                limit=50,
                offset=0
            )
    
    def test_get_my_feedback_with_pagination(self, client, mock_feedback_service, regular_user):
        """페이지네이션과 함께 내 피드백 가져오기 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/my-feedback?limit=10&offset=20")
            
            assert response.status_code == 200
            
            # 서비스 호출 확인
            mock_feedback_service.get_user_feedback.assert_called_once_with(
                user_id=regular_user["sub"],
                limit=10,
                offset=20
            )
    
    def test_get_feedback_by_id_success_owner(self, client, mock_feedback_service, regular_user):
        """ID로 피드백 가져오기 (소유자) 성공 테스트"""
        # 모의 피드백 설정
        mock_feedback = MagicMock()
        mock_feedback.id = 1
        mock_feedback.user_id = regular_user["sub"]
        mock_feedback.feedback_type = "bug_report"
        mock_feedback.title = "Test Bug"
        mock_feedback.description = "Bug description"
        mock_feedback.category = "ui"
        mock_feedback.rating = 4
        mock_feedback.priority = "medium"
        mock_feedback.status = "open"
        mock_feedback.response = None
        mock_feedback.responded_by = None
        mock_feedback.responded_at = None
        mock_feedback.created_at = datetime.utcnow()
        mock_feedback.updated_at = datetime.utcnow()
        
        mock_feedback_service.get_feedback_by_id.return_value = mock_feedback
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/feedback/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["user_id"] == regular_user["sub"]
            assert data["title"] == "Test Bug"
            assert data["status"] == "open"
            
            # 서비스 호출 확인
            mock_feedback_service.get_feedback_by_id.assert_called_once_with(1)
    
    def test_get_feedback_by_id_success_admin(self, client, mock_feedback_service, admin_user, regular_user):
        """ID로 피드백 가져오기 (관리자) 성공 테스트"""
        # 모의 피드백 설정
        mock_feedback = MagicMock()
        mock_feedback.id = 1
        mock_feedback.user_id = regular_user["sub"]
        mock_feedback.feedback_type = "bug_report"
        mock_feedback.title = "Test Bug"
        mock_feedback.description = "Bug description"
        mock_feedback.category = "ui"
        mock_feedback.rating = 4
        mock_feedback.priority = "medium"
        mock_feedback.status = "open"
        mock_feedback.response = None
        mock_feedback.responded_by = None
        mock_feedback.responded_at = None
        mock_feedback.created_at = datetime.utcnow()
        mock_feedback.updated_at = datetime.utcnow()
        
        mock_feedback_service.get_feedback_by_id.return_value = mock_feedback
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.get("/api/v1/feedback/feedback/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["user_id"] == regular_user["sub"]
            assert data["title"] == "Test Bug"
            
            # 서비스 호출 확인
            mock_feedback_service.get_feedback_by_id.assert_called_once_with(1)
    
    def test_get_feedback_by_id_not_found(self, client, mock_feedback_service, regular_user):
        """ID로 피드백 가져오기 (찾을 수 없음) 테스트"""
        mock_feedback_service.get_feedback_by_id.return_value = None
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/feedback/999")
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Feedback not found"
            
            # 서비스 호출 확인
            mock_feedback_service.get_feedback_by_id.assert_called_once_with(999)
    
    def test_get_feedback_by_id_access_denied(self, client, mock_feedback_service, regular_user):
        """ID로 피드백 가져오기 (접근 거부) 테스트"""
        # 다른 사용자의 피드백 설정
        mock_feedback = MagicMock()
        mock_feedback.id = 1
        mock_feedback.user_id = 999  # 다른 사용자 ID
        mock_feedback.feedback_type = "bug_report"
        mock_feedback.title = "Test Bug"
        mock_feedback.description = "Bug description"
        mock_feedback.category = "ui"
        mock_feedback.rating = 4
        mock_feedback.priority = "medium"
        mock_feedback.status = "open"
        mock_feedback.response = None
        mock_feedback.responded_by = None
        mock_feedback.responded_at = None
        mock_feedback.created_at = datetime.utcnow()
        mock_feedback.updated_at = datetime.utcnow()
        
        mock_feedback_service.get_feedback_by_id.return_value = mock_feedback
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/feedback/1")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Access denied"
    
    def test_log_activity_success(self, client, mock_feedback_service, sample_activity_data, regular_user):
        """활동 로깅 성공 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.post(
                "/api/v1/feedback/log-activity",
                json=sample_activity_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Activity logged successfully"
            
            # 서비스 호출 확인
            mock_feedback_service.log_activity.assert_called_once_with(
                user_id=regular_user["sub"],
                activity_type=sample_activity_data["activity_type"],
                action=sample_activity_data["action"],
                feature_name=sample_activity_data["feature_name"],
                metadata=sample_activity_data["metadata"],
                duration=sample_activity_data["duration"]
            )
    
    def test_log_activity_error(self, client, mock_feedback_service, sample_activity_data, regular_user):
        """활동 로깅 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_feedback_service.log_activity.side_effect = Exception("Database error")
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.post(
                "/api/v1/feedback/log-activity",
                json=sample_activity_data
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to log activity" in data["detail"]
    
    def test_track_behavior_success(self, client, mock_feedback_service, sample_behavior_data, regular_user):
        """행동 추적 성공 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.post(
                "/api/v1/feedback/track-behavior",
                json=sample_behavior_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Behavior tracked successfully"
            
            # 서비스 호출 확인
            mock_feedback_service.track_user_behavior.assert_called_once_with(
                user_id=regular_user["sub"],
                behavior_type=sample_behavior_data["behavior_type"],
                behavior_data=sample_behavior_data["behavior_data"],
                context=sample_behavior_data["context"]
            )
    
    def test_track_behavior_error(self, client, mock_feedback_service, sample_behavior_data, regular_user):
        """행동 추적 오류 테스트"""
        # 모의 서비스에서 오류 발생
        mock_feedback_service.track_user_behavior.side_effect = Exception("Database error")
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.post(
                "/api/v1/feedback/track-behavior",
                json=sample_behavior_data
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to track behavior" in data["detail"]
    
    def test_get_my_activity_summary_success(self, client, mock_feedback_service, regular_user):
        """내 활동 요약 가져오기 성공 테스트"""
        # 모의 활동 요약 설정
        mock_summary = {
            "total_activities": 50,
            "activities_by_type": [
                {"type": "feature_usage", "count": 30},
                {"type": "login", "count": 5},
                {"type": "feedback_submitted", "count": 15}
            ],
            "most_used_features": [
                {"feature": "stock_chart", "usage_count": 20, "avg_duration": 120.5},
                {"feature": "sentiment_analysis", "usage_count": 10, "avg_duration": 85.0}
            ],
            "feedback_submitted": 15,
            "period_days": 30
        }
        
        mock_feedback_service.get_user_activity_summary.return_value = mock_summary
        
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/my-activity-summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_activities"] == 50
            assert len(data["activities_by_type"]) == 3
            assert data["activities_by_type"][0]["type"] == "feature_usage"
            assert data["activities_by_type"][0]["count"] == 30
            assert len(data["most_used_features"]) == 2
            assert data["most_used_features"][0]["feature"] == "stock_chart"
            assert data["feedback_submitted"] == 15
            assert data["period_days"] == 30
            
            # 서비스 호출 확인
            mock_feedback_service.get_user_activity_summary.assert_called_once_with(
                user_id=regular_user["sub"],
                days=30
            )
    
    def test_get_my_activity_summary_with_custom_days(self, client, mock_feedback_service, regular_user):
        """사용자 정의 기간과 함께 내 활동 요약 가져오기 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/my-activity-summary?days=60")
            
            assert response.status_code == 200
            
            # 서비스 호출 확인
            mock_feedback_service.get_user_activity_summary.assert_called_once_with(
                user_id=regular_user["sub"],
                days=60
            )
    
    def test_get_all_feedback_admin_success(self, client, mock_feedback_service, admin_user):
        """모든 피드백 가져오기 (관리자) 성공 테스트"""
        # 모의 피드백 목록 설정
        mock_feedback_list = []
        for i in range(5):
            feedback = MagicMock()
            feedback.id = i + 1
            feedback.user_id = i + 1
            feedback.feedback_type = "bug_report"
            feedback.title = f"Bug Report {i + 1}"
            feedback.description = f"Description {i + 1}"
            feedback.category = "ui"
            feedback.rating = 4
            feedback.priority = "medium"
            feedback.status = "open"
            feedback.response = None
            feedback.responded_by = None
            feedback.responded_at = None
            feedback.created_at = datetime.utcnow()
            feedback.updated_at = datetime.utcnow()
            mock_feedback_list.append(feedback)
        
        mock_feedback_service.get_feedback_by_status.return_value = mock_feedback_list
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.get("/api/v1/feedback/admin/all-feedback?status=open")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5
            
            for i, feedback_data in enumerate(data):
                assert feedback_data["id"] == i + 1
                assert feedback_data["title"] == f"Bug Report {i + 1}"
                assert feedback_data["status"] == "open"
            
            # 서비스 호출 확인
            mock_feedback_service.get_feedback_by_status.assert_called_once_with(
                status="open",
                limit=100,
                offset=0
            )
    
    def test_get_all_feedback_admin_access_denied(self, client, mock_feedback_service, regular_user):
        """모든 피드백 가져오기 (관리자 권한 없음) 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/admin/all-feedback")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Admin access required"
    
    def test_update_feedback_status_admin_success(self, client, mock_feedback_service, admin_user):
        """피드백 상태 업데이트 (관리자) 성공 테스트"""
        # 모의 업데이트된 피드백 설정
        mock_updated_feedback = MagicMock()
        mock_updated_feedback.id = 1
        mock_updated_feedback.status = "resolved"
        mock_updated_feedback.responded_by = admin_user["sub"]
        mock_updated_feedback.responded_at = datetime.utcnow()
        
        mock_feedback_service.update_feedback_status.return_value = mock_updated_feedback
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.put(
                "/api/v1/feedback/admin/feedback/1/status?status=resolved&response=Issue has been resolved"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Feedback status updated successfully"
            
            # 서비스 호출 확인
            mock_feedback_service.update_feedback_status.assert_called_once_with(
                feedback_id=1,
                status="resolved",
                responded_by=admin_user["sub"],
                response="Issue has been resolved"
            )
    
    def test_update_feedback_status_admin_not_found(self, client, mock_feedback_service, admin_user):
        """피드백 상태 업데이트 (관리자, 찾을 수 없음) 테스트"""
        mock_feedback_service.update_feedback_status.return_value = None
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.put(
                "/api/v1/feedback/admin/feedback/999/status?status=resolved"
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Feedback not found"
            
            # 서비스 호출 확인
            mock_feedback_service.update_feedback_status.assert_called_once_with(
                feedback_id=999,
                status="resolved",
                responded_by=admin_user["sub"],
                response=None
            )
    
    def test_update_feedback_status_admin_access_denied(self, client, mock_feedback_service, regular_user):
        """피드백 상태 업데이트 (관리자 권한 없음) 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.put(
                "/api/v1/feedback/admin/feedback/1/status?status=resolved"
            )
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Admin access required"
    
    def test_get_platform_analytics_admin_success(self, client, mock_feedback_service, admin_user):
        """플랫폼 분석 가져오기 (관리자) 성공 테스트"""
        # 모의 플랫폼 분석 설정
        mock_analytics = {
            "active_users": 100,
            "total_activities": 5000,
            "feedback_summary": [
                {"type": "bug_report", "status": "open", "count": 20, "avg_rating": 3.5},
                {"type": "feature_request", "status": "resolved", "count": 30, "avg_rating": 4.2}
            ],
            "feature_popularity": [
                {
                    "feature": "stock_chart",
                    "usage_count": 1000,
                    "unique_users": 80,
                    "avg_duration": 120.5,
                    "satisfaction_score": 4.1
                },
                {
                    "feature": "sentiment_analysis",
                    "usage_count": 800,
                    "unique_users": 60,
                    "avg_duration": 85.0,
                    "satisfaction_score": 3.8
                }
            ],
            "period_days": 30
        }
        
        mock_feedback_service.get_platform_analytics.return_value = mock_analytics
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.get("/api/v1/feedback/admin/platform-analytics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["active_users"] == 100
            assert data["total_activities"] == 5000
            assert len(data["feedback_summary"]) == 2
            assert len(data["feature_popularity"]) == 2
            assert data["period_days"] == 30
            
            # 서비스 호출 확인
            mock_feedback_service.get_platform_analytics.assert_called_once_with(days=30)
    
    def test_get_platform_analytics_admin_access_denied(self, client, mock_feedback_service, regular_user):
        """플랫폼 분석 가져오기 (관리자 권한 없음) 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/admin/platform-analytics")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Admin access required"
    
    def test_get_feedback_insights_admin_success(self, client, mock_feedback_service, admin_user):
        """피드백 인사이트 가져오기 (관리자) 성공 테스트"""
        # 모의 피드백 인사이트 설정
        mock_insights = {
            "feedback_by_category": [
                {"category": "ui", "count": 30, "avg_rating": 3.5},
                {"category": "performance", "count": 20, "avg_rating": 4.0}
            ],
            "high_priority_feedback": [
                {
                    "id": 1,
                    "title": "Critical Bug",
                    "category": "ui",
                    "priority": "high",
                    "created_at": "2023-01-01T00:00:00"
                }
            ],
            "unresolved_feedback": [
                {
                    "id": 2,
                    "title": "Feature Request",
                    "type": "feature_request",
                    "status": "open",
                    "created_at": "2023-01-02T00:00:00"
                }
            ],
            "period_days": 30
        }
        
        mock_feedback_service.get_feedback_insights.return_value = mock_insights
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.get("/api/v1/feedback/admin/feedback-insights")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["feedback_by_category"]) == 2
            assert data["feedback_by_category"][0]["category"] == "ui"
            assert data["feedback_by_category"][0]["count"] == 30
            assert len(data["high_priority_feedback"]) == 1
            assert data["high_priority_feedback"][0]["title"] == "Critical Bug"
            assert len(data["unresolved_feedback"]) == 1
            assert data["unresolved_feedback"][0]["title"] == "Feature Request"
            assert data["period_days"] == 30
            
            # 서비스 호출 확인
            mock_feedback_service.get_feedback_insights.assert_called_once_with(days=30)
    
    def test_get_feedback_insights_admin_access_denied(self, client, mock_feedback_service, regular_user):
        """피드백 인사이트 가져오기 (관리자 권한 없음) 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/admin/feedback-insights")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Admin access required"
    
    def test_get_feature_usage_admin_success(self, client, mock_feedback_service, admin_user):
        """기능 사용 통계 가져오기 (관리자) 성공 테스트"""
        # 모의 기능 사용 통계 설정
        mock_feature_usage = []
        for i in range(3):
            feature = MagicMock()
            feature.feature_name = f"feature_{i + 1}"
            feature.usage_count = (i + 1) * 100
            feature.unique_users = (i + 1) * 20
            feature.avg_duration = 100.0 + i * 10
            feature.satisfaction_score = 4.0 - i * 0.2
            feature.last_used = datetime.utcnow()
            mock_feature_usage.append(feature)
        
        mock_feedback_service.get_feature_usage_stats.return_value = mock_feature_usage
        
        with patch('backend.api.feedback_routes.require_auth', return_value=admin_user):
            response = client.get("/api/v1/feedback/admin/feature-usage")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            
            for i, feature_data in enumerate(data):
                assert feature_data["feature_name"] == f"feature_{i + 1}"
                assert feature_data["usage_count"] == (i + 1) * 100
                assert feature_data["unique_users"] == (i + 1) * 20
                assert feature_data["avg_duration"] == 100.0 + i * 10
                assert feature_data["satisfaction_score"] == 4.0 - i * 0.2
                assert "last_used" in feature_data
            
            # 서비스 호출 확인
            mock_feedback_service.get_feature_usage_stats.assert_called_once_with(limit=50, days=30)
    
    def test_get_feature_usage_admin_access_denied(self, client, mock_feedback_service, regular_user):
        """기능 사용 통계 가져오기 (관리자 권한 없음) 테스트"""
        with patch('backend.api.feedback_routes.require_auth', return_value=regular_user):
            response = client.get("/api/v1/feedback/admin/feature-usage")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Admin access required"