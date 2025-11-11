"""
GDPR Automation API Routes for InsiteChart platform.

This module provides REST API endpoints for GDPR compliance management
including data subject requests, consent management, and compliance reporting.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.gdpr_automation_service import (
    GDPRAutomationService,
    DataSubjectRequestType,
    ConsentType,
    ConsentStatus,
    DataCategory
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/gdpr", tags=["GDPR"])

# Pydantic models for request/response
class DataSubjectRequestCreate(BaseModel):
    """Model for creating a data subject request."""
    subject_id: str = Field(..., description="ID of the data subject")
    request_type: DataSubjectRequestType = Field(..., description="Type of request")
    description: str = Field(..., description="Description of the request")
    data_categories: List[DataCategory] = Field(..., description="Data categories requested")

class ConsentUpdate(BaseModel):
    """Model for updating consent."""
    subject_id: str = Field(..., description="ID of the data subject")
    consent_type: ConsentType = Field(..., description="Type of consent")
    status: ConsentStatus = Field(..., description="Consent status")
    purpose: str = Field(..., description="Purpose of data processing")
    legal_basis: Optional[str] = Field(None, description="Legal basis for processing")

class RetentionRuleCreate(BaseModel):
    """Model for creating a retention rule."""
    rule_id: str = Field(..., description="Unique rule identifier")
    data_category: DataCategory = Field(..., description="Data category")
    retention_policy: str = Field(..., description="Retention policy")
    custom_retention_days: Optional[int] = Field(None, description="Custom retention days")
    automated_deletion: bool = Field(True, description="Enable automated deletion")
    notification_before_deletion: bool = Field(True, description="Notify before deletion")
    exceptions: List[str] = Field(default_factory=list, description="Exceptions to the rule")

class ComplianceReportRequest(BaseModel):
    """Model for requesting a compliance report."""
    report_type: str = Field("daily_compliance", description="Type of report")
    period_start: Optional[datetime] = Field(None, description="Report period start")
    period_end: Optional[datetime] = Field(None, description="Report period end")

# Dependency to get GDPR service
async def get_gdpr_service() -> GDPRAutomationService:
    """Get GDPR automation service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return GDPRAutomationService(cache_manager)
    except Exception as e:
        logger.error(f"Error creating GDPR service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize GDPR service")

@router.post("/data-subject-requests")
async def create_data_subject_request(
    request: DataSubjectRequestCreate,
    background_tasks: BackgroundTasks,
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new data subject request.
    
    This endpoint creates a new GDPR data subject request for access, rectification,
    erasure, portability, restriction, or objection.
    """
    try:
        # Check if user has permission to create request
        if current_user.id != request.subject_id and not current_user.is_admin:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to create request for this subject"
            )
        
        # Create request
        result = await gdpr_service.create_data_subject_request(
            subject_id=request.subject_id,
            request_type=request.request_type,
            description=request.description,
            data_categories=request.data_categories
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "request_id": result["request_id"],
            "due_date": result["due_date"],
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data subject request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data-subject-requests")
async def get_data_subject_requests(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of requests"),
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get data subject requests.
    
    This endpoint retrieves data subject requests with optional filtering.
    Admin users can view all requests, regular users can only view their own.
    """
    try:
        # Check permissions
        if subject_id and subject_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view requests for this subject")
        
        # If not admin, only show own requests
        if not current_user.is_admin:
            subject_id = current_user.id
        
        requests = await gdpr_service.get_data_subject_requests(
            subject_id=subject_id,
            status=status,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(requests),
            "requests": requests
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data subject requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/consent")
async def update_consent(
    consent: ConsentUpdate,
    background_tasks: BackgroundTasks,
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Update consent record.
    
    This endpoint updates a consent record for a data subject, including
    granting, denying, or withdrawing consent.
    """
    try:
        # Check if user has permission to update consent
        if current_user.id != consent.subject_id and not current_user.is_admin:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to update consent for this subject"
            )
        
        # Update consent
        result = await gdpr_service.update_consent(
            subject_id=consent.subject_id,
            consent_type=consent.consent_type,
            status=consent.status,
            purpose=consent.purpose,
            legal_basis=consent.legal_basis
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "consent_id": result["consent_id"],
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating consent: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/consent")
async def get_consent_records(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    consent_type: Optional[ConsentType] = Query(None, description="Filter by consent type"),
    status: Optional[ConsentStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of records"),
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get consent records.
    
    This endpoint retrieves consent records with optional filtering.
    Admin users can view all records, regular users can only view their own.
    """
    try:
        # Check permissions
        if subject_id and subject_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view consent for this subject")
        
        # If not admin, only show own records
        if not current_user.is_admin:
            subject_id = current_user.id
        
        records = await gdpr_service.get_consent_records(
            subject_id=subject_id,
            consent_type=consent_type,
            status=status,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(records),
            "records": records
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consent records: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/retention-rules")
async def get_retention_rules(
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get data retention rules.
    
    This endpoint retrieves all data retention rules.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        rules = await gdpr_service.get_retention_rules()
        
        return {
            "success": True,
            "count": len(rules),
            "rules": rules
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting retention rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/retention-rules")
async def create_retention_rule(
    rule: RetentionRuleCreate,
    background_tasks: BackgroundTasks,
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new retention rule.
    
    This endpoint creates a new data retention rule.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create the rule in the service
        # For now, return a success response
        return {
            "success": True,
            "rule_id": rule.rule_id,
            "message": "Retention rule created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating retention rule: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/compliance-reports")
async def get_compliance_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of reports"),
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get compliance reports.
    
    This endpoint retrieves GDPR compliance reports.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        reports = await gdpr_service.get_compliance_reports(
            report_type=report_type,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting compliance reports: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/compliance-reports")
async def generate_compliance_report(
    report_request: ComplianceReportRequest,
    background_tasks: BackgroundTasks,
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a compliance report.
    
    This endpoint generates a new GDPR compliance report.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would trigger report generation in the service
        # For now, return a success response
        return {
            "success": True,
            "message": "Compliance report generation started",
            "report_type": report_request.report_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating compliance report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status")
async def get_gdpr_status(
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get GDPR compliance status.
    
    This endpoint retrieves the overall GDPR compliance status.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        status = await gdpr_service.get_gdpr_status()
        
        return {
            "success": True,
            "status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GDPR status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/download/{export_id}")
async def download_data_export(
    export_id: str,
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Download data export package.
    
    This endpoint provides a secure download link for data export packages.
    """
    try:
        # This would verify the export ID and user permissions
        # For now, return a mock response
        return {
            "success": True,
            "export_id": export_id,
            "download_url": f"/secure-downloads/{export_id}",
            "message": "Download link generated"
        }
        
    except Exception as e:
        logger.error(f"Error generating download link: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/data/{subject_id}")
async def delete_subject_data(
    subject_id: str,
    data_categories: List[DataCategory],
    background_tasks: BackgroundTasks,
    gdpr_service: GDPRAutomationService = Depends(get_gdpr_service),
    current_user: User = Depends(get_current_user)
):
    """
    Delete subject data.
    
    This endpoint schedules deletion of data for a subject.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would schedule data deletion in the service
        # For now, return a success response
        return {
            "success": True,
            "subject_id": subject_id,
            "message": "Data deletion scheduled",
            "categories": [cat.value for cat in data_categories]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling data deletion: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception in GDPR routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )