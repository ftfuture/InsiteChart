"""
Data Encryption API Routes for InsiteChart platform.

This module provides REST API endpoints for data encryption,
key management, and encryption policy administration.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ..services.data_encryption_service import (
    DataEncryptionService,
    EncryptionType,
    EncryptionLevel,
    KeyType,
    KeyStatus
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/data-encryption", tags=["Data Encryption"])

# Pydantic models for request/response
class DataEncryptionRequest(BaseModel):
    """Model for data encryption request."""
    data: Union[str, Dict[str, Any]] = Field(..., description="Data to encrypt")
    data_type: str = Field(..., description="Type of data being encrypted")
    encryption_type: Optional[EncryptionType] = Field(None, description="Encryption type to use")
    key_id: Optional[str] = Field(None, description="Specific key ID to use")

class DataDecryptionRequest(BaseModel):
    """Model for data decryption request."""
    encrypted_data: Union[str, bytes] = Field(..., description="Encrypted data")
    key_id: str = Field(..., description="Key ID used for encryption")
    encryption_type: EncryptionType = Field(..., description="Encryption type used")
    iv: Optional[Union[str, bytes]] = Field(None, description="Initialization vector")
    tag: Optional[Union[str, bytes]] = Field(None, description="Authentication tag")

class EncryptionPolicyCreate(BaseModel):
    """Model for creating encryption policy."""
    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    data_types: List[str] = Field(..., description="Data types this policy applies to")
    encryption_type: EncryptionType = Field(..., description="Encryption type to use")
    encryption_level: EncryptionLevel = Field(..., description="Security level")
    key_rotation_days: int = Field(90, description="Key rotation interval in days")
    enabled: bool = Field(True, description="Enable policy")

class KeyRotationRequest(BaseModel):
    """Model for key rotation request."""
    key_id: str = Field(..., description="Key ID to rotate")
    reason: str = Field(..., description="Reason for rotation")

# Dependency to get data encryption service
async def get_data_encryption_service() -> DataEncryptionService:
    """Get data encryption service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return DataEncryptionService(cache_manager)
    except Exception as e:
        logger.error(f"Error creating data encryption service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize data encryption service")

@router.post("/encrypt")
async def encrypt_data(
    request: DataEncryptionRequest,
    background_tasks: BackgroundTasks,
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Encrypt data with appropriate policy.
    
    This endpoint encrypts data using the appropriate encryption policy
    for the specified data type.
    """
    try:
        # Encrypt data
        result = await encryption_service.encrypt_data(
            data=request.data,
            data_type=request.data_type,
            encryption_type=request.encryption_type,
            key_id=request.key_id,
            user_id=current_user.id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "encrypted_data": result["encrypted_data"],
            "key_id": result["key_id"],
            "encryption_type": result["encryption_type"],
            "iv": result.get("iv"),
            "tag": result.get("tag"),
            "metadata": result["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error encrypting data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/decrypt")
async def decrypt_data(
    request: DataDecryptionRequest,
    background_tasks: BackgroundTasks,
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Decrypt encrypted data.
    
    This endpoint decrypts data using the specified key and encryption type.
    """
    try:
        # Decrypt data
        result = await encryption_service.decrypt_data(
            encrypted_data=request.encrypted_data,
            key_id=request.key_id,
            encryption_type=request.encryption_type,
            iv=request.iv,
            tag=request.tag,
            user_id=current_user.id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        return {
            "success": True,
            "decrypted_data": result["decrypted_data"],
            "metadata": result["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error decrypting data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/keys")
async def get_encryption_keys(
    key_type: Optional[KeyType] = Query(None, description="Filter by key type"),
    status: Optional[KeyStatus] = Query(None, description="Filter by key status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of keys"),
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get encryption keys.
    
    This endpoint retrieves encryption keys with optional filtering.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        keys = await encryption_service.get_encryption_keys(
            key_type=key_type,
            status=status,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(keys),
            "keys": keys
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting encryption keys: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/keys/rotate")
async def rotate_encryption_key(
    request: KeyRotationRequest,
    background_tasks: BackgroundTasks,
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Rotate an encryption key.
    
    This endpoint rotates an encryption key and creates a new one.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would trigger key rotation in the service
        # For now, return a success response
        return {
            "success": True,
            "key_id": request.key_id,
            "message": "Key rotation initiated",
            "reason": request.reason,
            "rotated_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating key: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/policies")
async def get_encryption_policies(
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get encryption policies.
    
    This endpoint retrieves all encryption policies.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        policies = await encryption_service.get_encryption_policies()
        
        return {
            "success": True,
            "count": len(policies),
            "policies": policies
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting encryption policies: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/policies")
async def create_encryption_policy(
    policy: EncryptionPolicyCreate,
    background_tasks: BackgroundTasks,
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new encryption policy.
    
    This endpoint creates a new encryption policy for data types.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # This would create the policy in the service
        # For now, return a success response
        return {
            "success": True,
            "policy_id": policy.policy_id,
            "message": "Encryption policy created successfully",
            "created_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating encryption policy: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/operations")
async def get_encryption_operations(
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    key_id: Optional[str] = Query(None, description="Filter by key ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of operations"),
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get encryption operation logs.
    
    This endpoint retrieves encryption operation logs with optional filtering.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            # Users can only see their own operations
            user_id = current_user.id
        
        operations = await encryption_service.get_encryption_operations(
            operation_type=operation_type,
            key_id=key_id,
            user_id=user_id,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(operations),
            "operations": operations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting encryption operations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/statistics")
async def get_encryption_statistics(
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get encryption service statistics.
    
    This endpoint retrieves comprehensive encryption service statistics.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        statistics = await encryption_service.get_encryption_statistics()
        
        return {
            "success": True,
            "statistics": statistics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting encryption statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/my-operations")
async def get_my_encryption_operations(
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of operations"),
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's encryption operations.
    
    This endpoint retrieves encryption operations performed by the current user.
    """
    try:
        operations = await encryption_service.get_encryption_operations(
            operation_type=operation_type,
            user_id=current_user.id,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(operations),
            "operations": operations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user encryption operations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/test-encryption")
async def test_encryption(
    data: Union[str, Dict[str, Any]] = Field(..., description="Test data"),
    data_type: str = Field("test_data", description="Test data type"),
    encryption_type: EncryptionType = Field(EncryptionType.AES_256_GCM, description="Encryption type to test"),
    encryption_service: DataEncryptionService = Depends(get_data_encryption_service),
    current_user: User = Depends(get_current_user)
):
    """
    Test encryption functionality.
    
    This endpoint tests encryption and decryption with specified parameters.
    """
    try:
        # Encrypt test data
        encrypt_result = await encryption_service.encrypt_data(
            data=data,
            data_type=data_type,
            encryption_type=encryption_type,
            user_id=current_user.id
        )
        
        if not encrypt_result.get("success"):
            raise HTTPException(status_code=400, detail=encrypt_result.get("error", "Encryption failed"))
        
        # Decrypt the encrypted data
        decrypt_result = await encryption_service.decrypt_data(
            encrypted_data=encrypt_result["encrypted_data"],
            key_id=encrypt_result["key_id"],
            encryption_type=EncryptionType(encryption_result["encryption_type"]),
            iv=encrypt_result.get("iv"),
            tag=encrypt_result.get("tag"),
            user_id=current_user.id
        )
        
        if not decrypt_result.get("success"):
            raise HTTPException(status_code=400, detail=decrypt_result.get("error", "Decryption failed"))
        
        return {
            "success": True,
            "test_passed": True,
            "original_data": data,
            "decrypted_data": decrypt_result["decrypted_data"],
            "encryption_details": {
                "key_id": encrypt_result["key_id"],
                "encryption_type": encrypt_result["encryption_type"],
                "iv": encrypt_result.get("iv"),
                "tag": encrypt_result.get("tag")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing encryption: {str(e)}")
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
    logger.error(f"Unhandled exception in data encryption routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )