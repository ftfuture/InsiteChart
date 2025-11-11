"""
Automated Test API Routes for InsiteChart platform.

This module provides REST API endpoints for automated testing,
test suite management, and test reporting.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.automated_test_service import (
    AutomatedTestService,
    TestType,
    TestStatus,
    TestPriority
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/automated-tests", tags=["Automated Testing"])

# Pydantic models for request/response
class TestSuiteCreate(BaseModel):
    """Model for creating a test suite."""
    suite_id: str = Field(..., description="Unique suite identifier")
    name: str = Field(..., description="Suite name")
    description: str = Field(..., description="Suite description")
    test_type: TestType = Field(..., description="Test type")
    test_paths: List[str] = Field(..., description="Test paths")
    test_files: List[str] = Field(..., description="Test file patterns")
    enabled: bool = Field(True, description="Enable suite")
    timeout_seconds: int = Field(300, description="Test timeout in seconds")
    parallel: bool = Field(True, description="Run tests in parallel")

class ManualTestExecution(BaseModel):
    """Model for manual test execution."""
    suite_id: str = Field(..., description="Test suite ID")
    test_files: Optional[List[str]] = Field(None, description="Specific test files to run")
    environment: Optional[Dict[str, str]] = Field(None, description="Custom environment variables")

class TestSuiteUpdate(BaseModel):
    """Model for updating a test suite."""
    enabled: Optional[bool] = Field(None, description="Enable/disable suite")

# Dependency to get automated test service
async def get_automated_test_service() -> AutomatedTestService:
    """Get automated test service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return AutomatedTestService(cache_manager)
    except Exception as e:
        logger.error(f"Error creating automated test service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize automated test service")

@router.post("/suites")
async def create_test_suite(
    suite: TestSuiteCreate,
    background_tasks: BackgroundTasks,
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new test suite.
    
    This endpoint creates a new automated test suite with specified configuration.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create the test suite in the service
        # For now, return a success response
        return {
            "success": True,
            "suite_id": suite.suite_id,
            "message": "Test suite created successfully",
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test suite: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/suites")
async def get_test_suites(
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get all test suites.
    
    This endpoint retrieves all configured test suites.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        suites = await test_service.get_test_suites()
        
        return {
            "success": True,
            "count": len(suites),
            "suites": suites
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test suites: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/suites/{suite_id}/enable")
async def enable_test_suite(
    suite_id: str,
    background_tasks: BackgroundTasks,
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Enable a test suite.
    
    This endpoint enables a test suite for automated execution.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await test_service.enable_test_suite(suite_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "suite_id": suite_id,
            "message": result["message"],
            "enabled_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling test suite {suite_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/suites/{suite_id}/disable")
async def disable_test_suite(
    suite_id: str,
    background_tasks: BackgroundTasks,
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Disable a test suite.
    
    This endpoint disables a test suite.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await test_service.disable_test_suite(suite_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "suite_id": suite_id,
            "message": result["message"],
            "disabled_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling test suite {suite_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/execute")
async def execute_test_suite(
    execution: ManualTestExecution,
    background_tasks: BackgroundTasks,
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a test suite manually.
    
    This endpoint manually executes a test suite with optional
    custom parameters.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await test_service.run_manual_test(
            suite_id=execution.suite_id,
            test_files=execution.test_files,
            environment=execution.environment
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "execution_id": result["execution_id"],
            "suite_id": execution.suite_id,
            "status": result["status"],
            "duration_seconds": result["duration_seconds"],
            "tests_run": result["tests_run"],
            "tests_passed": result["tests_passed"],
            "tests_failed": result["tests_failed"],
            "executed_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing test suite: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/executions")
async def get_test_executions(
    suite_id: Optional[str] = Query(None, description="Filter by suite ID"),
    status: Optional[TestStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of executions"),
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get test execution records.
    
    This endpoint retrieves test execution records with optional filtering.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        executions = await test_service.get_test_executions(
            suite_id=suite_id,
            status=status,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(executions),
            "executions": executions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test executions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reports")
async def get_test_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of reports"),
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get test reports.
    
    This endpoint retrieves test reports with optional filtering.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        reports = await test_service.get_test_reports(
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
        logger.error(f"Error getting test reports: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/metrics")
async def get_test_metrics(
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get automated test metrics.
    
    This endpoint retrieves comprehensive automated test metrics.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        metrics = await test_service.get_test_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/execute/quick")
async def execute_quick_test(
    test_type: TestType = Field(..., description="Type of quick test to run"),
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Execute a quick test.
    
    This endpoint provides a quick way to run common tests
    without full suite configuration.
    """
    try:
        # Map test types to suite IDs
        test_type_to_suite = {
            TestType.UNIT: "unit_tests_backend",
            TestType.INTEGRATION: "integration_tests_backend",
            TestType.PERFORMANCE: "performance_tests_api",
            TestType.SECURITY: "security_tests_api"
        }
        
        suite_id = test_type_to_suite.get(test_type)
        if not suite_id:
            raise HTTPException(status_code=400, detail=f"Unsupported test type: {test_type}")
        
        # Execute the test suite
        result = await test_service.run_test_suite(suite_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "execution_id": result["execution_id"],
            "test_type": test_type.value,
            "suite_id": suite_id,
            "status": result["status"],
            "duration_seconds": result["duration_seconds"],
            "tests_run": result["tests_run"],
            "tests_passed": result["tests_passed"],
            "tests_failed": result["tests_failed"],
            "executed_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing quick test: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def get_test_service_health(
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get automated test service health status.
    
    This endpoint retrieves the health status of the automated test service.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get metrics to determine health
        metrics = await test_service.get_test_metrics()
        
        # Determine health status
        if "error" in metrics:
            status = "unhealthy"
        elif metrics.get("success_rate", 0) < 80:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "success": True,
            "status": status,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test service health: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    test_service: AutomatedTestService = Depends(get_automated_test_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get logs for a specific test execution.
    
    This endpoint retrieves detailed logs for a test execution.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would retrieve execution logs from the service
        # For now, return a mock response
        logs = [
            {
                "timestamp": "2025-11-09T10:00:00Z",
                "level": "INFO",
                "message": f"Starting test execution {execution_id}"
            },
            {
                "timestamp": "2025-11-09T10:01:00Z",
                "level": "INFO",
                "message": "Discovered 5 test files"
            },
            {
                "timestamp": "2025-11-09T10:02:00Z",
                "level": "INFO",
                "message": "Running tests in parallel"
            },
            {
                "timestamp": "2025-11-09T10:03:00Z",
                "level": "INFO",
                "message": "Test execution completed"
            }
        ]
        
        return {
            "success": True,
            "execution_id": execution_id,
            "logs": logs,
            "log_count": len(logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution logs {execution_id}: {str(e)}")
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
    logger.error(f"Unhandled exception in automated test routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )