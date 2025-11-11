"""
User feedback and analytics service for InsiteChart platform.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from ..models.database_models import (
    UserFeedback, UserActivity, FeatureUsage, UserBehavior, User
)
from ..database import get_db, SessionLocal


class FeedbackService:
    """Service for managing user feedback and analytics."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def create_feedback(
        self,
        user_id: int,
        feedback_type: str,
        title: str,
        description: str,
        category: Optional[str] = None,
        rating: Optional[int] = None,
        priority: str = "medium"
    ) -> UserFeedback:
        """Create a new user feedback entry."""
        feedback = UserFeedback(
            user_id=user_id,
            feedback_type=feedback_type,
            category=category,
            title=title,
            description=description,
            rating=rating,
            priority=priority,
            status="open"
        )
        
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        
        # Log activity
        self.log_activity(
            user_id=user_id,
            activity_type="feedback_submitted",
            feature_name=category or "general",
            action="submit",
            metadata={
                "feedback_id": feedback.id,
                "feedback_type": feedback_type,
                "category": category,
                "rating": rating
            }
        )
        
        return feedback
    
    def get_feedback_by_id(self, feedback_id: int) -> Optional[UserFeedback]:
        """Get feedback by ID."""
        return self.db.query(UserFeedback).filter(
            UserFeedback.id == feedback_id
        ).first()
    
    def get_user_feedback(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserFeedback]:
        """Get feedback submitted by a specific user."""
        return self.db.query(UserFeedback).filter(
            UserFeedback.user_id == user_id
        ).order_by(desc(UserFeedback.created_at)).offset(offset).limit(limit).all()
    
    def get_feedback_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserFeedback]:
        """Get feedback by status."""
        return self.db.query(UserFeedback).filter(
            UserFeedback.status == status
        ).order_by(desc(UserFeedback.created_at)).offset(offset).limit(limit).all()
    
    def get_feedback_by_type(
        self,
        feedback_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserFeedback]:
        """Get feedback by type."""
        return self.db.query(UserFeedback).filter(
            UserFeedback.feedback_type == feedback_type
        ).order_by(desc(UserFeedback.created_at)).offset(offset).limit(limit).all()
    
    def update_feedback_status(
        self,
        feedback_id: int,
        status: str,
        responded_by: Optional[int] = None,
        response: Optional[str] = None
    ) -> Optional[UserFeedback]:
        """Update feedback status and optionally add response."""
        feedback = self.get_feedback_by_id(feedback_id)
        if not feedback:
            return None
        
        feedback.status = status
        if responded_by:
            feedback.responded_by = responded_by
            feedback.responded_at = datetime.utcnow()
        if response:
            feedback.response = response
        
        self.db.commit()
        self.db.refresh(feedback)
        
        return feedback
    
    def log_activity(
        self,
        user_id: int,
        activity_type: str,
        action: str,
        feature_name: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration: Optional[int] = None
    ) -> UserActivity:
        """Log user activity."""
        activity = UserActivity(
            user_id=user_id,
            session_id=session_id,
            activity_type=activity_type,
            feature_name=feature_name,
            action=action,
            metadata=metadata or {},
            duration=duration
        )
        
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        
        # Update feature usage statistics
        if feature_name:
            self.update_feature_usage(feature_name, duration)
        
        return activity
    
    def update_feature_usage(
        self,
        feature_name: str,
        duration: Optional[int] = None
    ) -> FeatureUsage:
        """Update feature usage statistics."""
        feature = self.db.query(FeatureUsage).filter(
            FeatureUsage.feature_name == feature_name
        ).first()
        
        if not feature:
            feature = FeatureUsage(
                feature_name=feature_name,
                usage_count=1,
                unique_users=1,
                avg_duration=duration or 0,
                last_used=datetime.utcnow()
            )
            self.db.add(feature)
        else:
            feature.usage_count += 1
            if duration:
                # Update average duration
                total_duration = feature.avg_duration * (feature.usage_count - 1) + duration
                feature.avg_duration = total_duration / feature.usage_count
            feature.last_used = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(feature)
        
        return feature
    
    def get_feature_usage_stats(
        self,
        limit: int = 50,
        days: int = 30
    ) -> List[FeatureUsage]:
        """Get feature usage statistics for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(FeatureUsage).filter(
            FeatureUsage.last_used >= cutoff_date
        ).order_by(desc(FeatureUsage.usage_count)).limit(limit).all()
    
    def track_user_behavior(
        self,
        user_id: int,
        behavior_type: str,
        behavior_data: Dict[str, Any],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> UserBehavior:
        """Track user behavior for analytics."""
        behavior = UserBehavior(
            user_id=user_id,
            session_id=session_id,
            behavior_type=behavior_type,
            behavior_metadata=behavior_data,
            context=context or {}
        )
        
        self.db.add(behavior)
        self.db.commit()
        self.db.refresh(behavior)
        
        return behavior
    
    def get_user_activity_summary(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get summary of user activity for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Total activities
        total_activities = self.db.query(UserActivity).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= cutoff_date
            )
        ).count()
        
        # Activities by type
        activities_by_type = self.db.query(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        ).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= cutoff_date
            )
        ).group_by(UserActivity.activity_type).all()
        
        # Most used features
        feature_usage = self.db.query(
            UserActivity.feature_name,
            func.count(UserActivity.id).label('usage_count'),
            func.avg(UserActivity.duration).label('avg_duration')
        ).filter(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.feature_name.isnot(None),
                UserActivity.created_at >= cutoff_date
            )
        ).group_by(UserActivity.feature_name).order_by(
            desc('usage_count')
        ).limit(10).all()
        
        # Feedback submitted
        feedback_count = self.db.query(UserFeedback).filter(
            and_(
                UserFeedback.user_id == user_id,
                UserFeedback.created_at >= cutoff_date
            )
        ).count()
        
        return {
            "total_activities": total_activities,
            "activities_by_type": [
                {"type": activity_type, "count": count}
                for activity_type, count in activities_by_type
            ],
            "most_used_features": [
                {
                    "feature": feature,
                    "usage_count": usage_count,
                    "avg_duration": float(avg_duration) if avg_duration else 0
                }
                for feature, usage_count, avg_duration in feature_usage
            ],
            "feedback_submitted": feedback_count,
            "period_days": days
        }
    
    def get_platform_analytics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get platform-wide analytics for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Active users
        active_users = self.db.query(UserActivity.user_id).filter(
            UserActivity.created_at >= cutoff_date
        ).distinct().count()
        
        # Total activities
        total_activities = self.db.query(UserActivity).filter(
            UserActivity.created_at >= cutoff_date
        ).count()
        
        # Feedback summary
        feedback_summary = self.db.query(
            UserFeedback.feedback_type,
            UserFeedback.status,
            func.count(UserFeedback.id).label('count'),
            func.avg(UserFeedback.rating).label('avg_rating')
        ).filter(
            UserFeedback.created_at >= cutoff_date
        ).group_by(UserFeedback.feedback_type, UserFeedback.status).all()
        
        # Feature popularity
        feature_popularity = self.db.query(
            FeatureUsage.feature_name,
            FeatureUsage.usage_count,
            FeatureUsage.unique_users,
            FeatureUsage.avg_duration,
            FeatureUsage.satisfaction_score
        ).order_by(desc(FeatureUsage.usage_count)).limit(20).all()
        
        return {
            "active_users": active_users,
            "total_activities": total_activities,
            "feedback_summary": [
                {
                    "type": feedback_type,
                    "status": status,
                    "count": count,
                    "avg_rating": float(avg_rating) if avg_rating else None
                }
                for feedback_type, status, count, avg_rating in feedback_summary
            ],
            "feature_popularity": [
                {
                    "feature": feature,
                    "usage_count": usage_count,
                    "unique_users": unique_users,
                    "avg_duration": avg_duration,
                    "satisfaction_score": satisfaction_score
                }
                for feature, usage_count, unique_users, avg_duration, satisfaction_score in feature_popularity
            ],
            "period_days": days
        }
    
    def get_feedback_insights(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get insights from user feedback."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Feedback by category
        feedback_by_category = self.db.query(
            UserFeedback.category,
            func.count(UserFeedback.id).label('count'),
            func.avg(UserFeedback.rating).label('avg_rating')
        ).filter(
            and_(
                UserFeedback.created_at >= cutoff_date,
                UserFeedback.category.isnot(None)
            )
        ).group_by(UserFeedback.category).all()
        
        # High priority feedback
        high_priority_feedback = self.db.query(UserFeedback).filter(
            and_(
                UserFeedback.created_at >= cutoff_date,
                UserFeedback.priority.in_(["high", "critical"])
            )
        ).order_by(desc(UserFeedback.created_at)).limit(10).all()
        
        # Unresolved feedback
        unresolved_feedback = self.db.query(UserFeedback).filter(
            UserFeedback.status.in_(["open", "in_progress"])
        ).order_by(desc(UserFeedback.created_at)).limit(20).all()
        
        return {
            "feedback_by_category": [
                {
                    "category": category,
                    "count": count,
                    "avg_rating": float(avg_rating) if avg_rating else None
                }
                for category, count, avg_rating in feedback_by_category
            ],
            "high_priority_feedback": [
                {
                    "id": feedback.id,
                    "title": feedback.title,
                    "category": feedback.category,
                    "priority": feedback.priority,
                    "created_at": feedback.created_at.isoformat()
                }
                for feedback in high_priority_feedback
            ],
            "unresolved_feedback": [
                {
                    "id": feedback.id,
                    "title": feedback.title,
                    "type": feedback.feedback_type,
                    "status": feedback.status,
                    "created_at": feedback.created_at.isoformat()
                }
                for feedback in unresolved_feedback
            ],
            "period_days": days
        }
    
    def close(self):
        """Close database session."""
        self.db.close()


# Global feedback service instance
feedback_service = FeedbackService()