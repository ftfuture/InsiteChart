"""
API routes for user feedback and analytics system.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..middleware.auth_middleware import require_auth
from ..services.feedback_service import feedback_service

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


# Pydantic models for request/response
class FeedbackCreate(BaseModel):
    feedback_type: str = Field(..., description="Type of feedback: bug_report, feature_request, general, ui_ux")
    title: str = Field(..., min_length=1, max_length=255, description="Feedback title")
    description: str = Field(..., min_length=1, description="Detailed feedback description")
    category: Optional[str] = Field(None, description="Feedback category: chart, sentiment_analysis, performance, etc.")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Satisfaction rating (1-5 stars)")
    priority: str = Field("medium", description="Priority: low, medium, high, critical")


class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    feedback_type: str
    category: Optional[str]
    title: str
    description: str
    rating: Optional[int]
    priority: str
    status: str
    response: Optional[str]
    responded_by: Optional[int]
    responded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ActivityLog(BaseModel):
    activity_type: str
    feature_name: Optional[str]
    action: str
    metadata: Optional[Dict[str, Any]]
    duration: Optional[int]


class BehaviorData(BaseModel):
    behavior_type: str
    behavior_data: Dict[str, Any]
    context: Optional[Dict[str, Any]]


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    current_user: dict = Depends(require_auth)
):
    """Submit new user feedback."""
    try:
        feedback_entry = feedback_service.create_feedback(
            user_id=current_user.get("sub"),
            feedback_type=feedback.feedback_type,
            title=feedback.title,
            description=feedback.description,
            category=feedback.category,
            rating=feedback.rating,
            priority=feedback.priority
        )
        
        return FeedbackResponse(
            id=feedback_entry.id,
            user_id=feedback_entry.user_id,
            feedback_type=feedback_entry.feedback_type,
            category=feedback_entry.category,
            title=feedback_entry.title,
            description=feedback_entry.description,
            rating=feedback_entry.rating,
            priority=feedback_entry.priority,
            status=feedback_entry.status,
            response=feedback_entry.response,
            responded_by=feedback_entry.responded_by,
            responded_at=feedback_entry.responded_at,
            created_at=feedback_entry.created_at,
            updated_at=feedback_entry.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/my-feedback", response_model=List[FeedbackResponse])
async def get_my_feedback(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_auth)
):
    """Get feedback submitted by the current user."""
    try:
        feedback_list = feedback_service.get_user_feedback(
            user_id=current_user.get("sub"),
            limit=limit,
            offset=offset
        )
        
        return [
            FeedbackResponse(
                id=feedback.id,
                user_id=feedback.user_id,
                feedback_type=feedback.feedback_type,
                category=feedback.category,
                title=feedback.title,
                description=feedback.description,
                rating=feedback.rating,
                priority=feedback.priority,
                status=feedback.status,
                response=feedback.response,
                responded_by=feedback.responded_by,
                responded_at=feedback.responded_at,
                created_at=feedback.created_at,
                updated_at=feedback.updated_at
            )
            for feedback in feedback_list
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feedback: {str(e)}")


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    current_user: dict = Depends(require_auth)
):
    """Get specific feedback by ID."""
    try:
        feedback = feedback_service.get_feedback_by_id(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Check if user owns the feedback or is admin
        if feedback.user_id != current_user.get("sub") and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FeedbackResponse(
            id=feedback.id,
            user_id=feedback.user_id,
            feedback_type=feedback.feedback_type,
            category=feedback.category,
            title=feedback.title,
            description=feedback.description,
            rating=feedback.rating,
            priority=feedback.priority,
            status=feedback.status,
            response=feedback.response,
            responded_by=feedback.responded_by,
            responded_at=feedback.responded_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feedback: {str(e)}")


@router.post("/log-activity")
async def log_activity(
    activity: ActivityLog,
    current_user: dict = Depends(require_auth)
):
    """Log user activity for analytics."""
    try:
        feedback_service.log_activity(
            user_id=current_user.get("sub"),
            activity_type=activity.activity_type,
            action=activity.action,
            feature_name=activity.feature_name,
            metadata=activity.metadata,
            duration=activity.duration
        )
        
        return {"message": "Activity logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log activity: {str(e)}")


@router.post("/track-behavior")
async def track_behavior(
    behavior: BehaviorData,
    current_user: dict = Depends(require_auth)
):
    """Track user behavior for analytics."""
    try:
        feedback_service.track_user_behavior(
            user_id=current_user.get("sub"),
            behavior_type=behavior.behavior_type,
            behavior_data=behavior.behavior_data,
            context=behavior.context
        )
        
        return {"message": "Behavior tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track behavior: {str(e)}")


@router.get("/my-activity-summary")
async def get_my_activity_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(require_auth)
):
    """Get activity summary for the current user."""
    try:
        summary = feedback_service.get_user_activity_summary(
            user_id=current_user.get("sub"),
            days=days
        )
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity summary: {str(e)}")


# Admin-only endpoints
@router.get("/admin/all-feedback", response_model=List[FeedbackResponse])
async def get_all_feedback(
    status: Optional[str] = Query(None, description="Filter by status"),
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_auth)
):
    """Get all feedback (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        if status:
            feedback_list = feedback_service.get_feedback_by_status(
                status=status,
                limit=limit,
                offset=offset
            )
        elif feedback_type:
            feedback_list = feedback_service.get_feedback_by_type(
                feedback_type=feedback_type,
                limit=limit,
                offset=offset
            )
        else:
            # Get all feedback (would need to implement this method)
            feedback_list = []
        
        return [
            FeedbackResponse(
                id=feedback.id,
                user_id=feedback.user_id,
                feedback_type=feedback.feedback_type,
                category=feedback.category,
                title=feedback.title,
                description=feedback.description,
                rating=feedback.rating,
                priority=feedback.priority,
                status=feedback.status,
                response=feedback.response,
                responded_by=feedback.responded_by,
                responded_at=feedback.responded_at,
                created_at=feedback.created_at,
                updated_at=feedback.updated_at
            )
            for feedback in feedback_list
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feedback: {str(e)}")


@router.put("/admin/feedback/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: int,
    status: str = Query(..., description="New status: open, in_progress, resolved, closed"),
    response: Optional[str] = Query(None, description="Admin response"),
    current_user: dict = Depends(require_auth)
):
    """Update feedback status (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        updated_feedback = feedback_service.update_feedback_status(
            feedback_id=feedback_id,
            status=status,
            responded_by=current_user.get("sub"),
            response=response
        )
        
        if not updated_feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        return {"message": "Feedback status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update feedback: {str(e)}")


@router.get("/admin/platform-analytics")
async def get_platform_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(require_auth)
):
    """Get platform-wide analytics (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        analytics = feedback_service.get_platform_analytics(days=days)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/admin/feedback-insights")
async def get_feedback_insights(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(require_auth)
):
    """Get feedback insights (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        insights = feedback_service.get_feedback_insights(days=days)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/admin/feature-usage")
async def get_feature_usage(
    limit: int = Query(50, ge=1, le=100),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(require_auth)
):
    """Get feature usage statistics (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        feature_usage = feedback_service.get_feature_usage_stats(limit=limit, days=days)
        
        return [
            {
                "feature_name": feature.feature_name,
                "usage_count": feature.usage_count,
                "unique_users": feature.unique_users,
                "avg_duration": feature.avg_duration,
                "satisfaction_score": feature.satisfaction_score,
                "last_used": feature.last_used
            }
            for feature in feature_usage
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feature usage: {str(e)}")