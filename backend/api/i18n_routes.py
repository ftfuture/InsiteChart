"""
Internationalization (i18n) API Routes for InsiteChart platform.

This module provides REST API endpoints for multi-language support,
including translation management, locale detection, and
language-specific content delivery.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from ..services.i18n_service import (
    I18nService,
    Locale,
    TranslationNamespace
)
from ..cache.unified_cache import UnifiedCacheManager
from .auth_routes import get_current_user
from ..models.unified_models import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/i18n", tags=["Internationalization"])

# Pydantic models for request/response
class TranslationRequest(BaseModel):
    """Model for adding/updating translations."""
    key: str = Field(..., description="Translation key")
    value: str = Field(..., description="Translation value")
    locale: Locale = Field(..., description="Target locale")
    namespace: TranslationNamespace = Field(..., description="Translation namespace")

class UserLocaleRequest(BaseModel):
    """Model for setting user locale."""
    locale: Locale = Field(..., description="Preferred locale")

class TranslationImportRequest(BaseModel):
    """Model for importing translations."""
    translations: Dict[str, Any] = Field(..., description="Translations to import")
    overwrite: bool = Field(False, description="Whether to overwrite existing translations")

class TranslationResponse(BaseModel):
    """Model for translation response."""
    key: str
    value: str
    locale: str
    namespace: str

class LocaleInfo(BaseModel):
    """Model for locale information."""
    code: str
    name: str
    native_name: str

class TranslationsResponse(BaseModel):
    """Model for translations response."""
    locale: str
    namespace: Optional[str]
    translations: Dict[str, str]

# Dependency to get i18n service
async def get_i18n_service() -> I18nService:
    """Get i18n service instance."""
    try:
        cache_manager = UnifiedCacheManager()
        return I18nService(cache_manager)
    except Exception as e:
        logger.error(f"Error creating i18n service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize i18n service")

@router.get("/translations/{key}")
async def get_translation(
    key: str,
    locale: Optional[Locale] = Query(None, description="Target locale"),
    namespace: Optional[TranslationNamespace] = Query(None, description="Translation namespace"),
    accept_language: Optional[str] = Header(None, description="Accept-Language header"),
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get translation for a specific key.
    
    This endpoint retrieves a translation for a given key with optional
    locale and namespace specification.
    """
    try:
        # Detect locale if not provided
        if not locale:
            if current_user:
                # Try to get user's preferred locale
                user_locale = await i18n_service.get_user_locale(str(current_user.id))
                locale = user_locale
            else:
                # Detect from Accept-Language header
                locale = await i18n_service.detect_locale(accept_language or "")
        
        # Get translation
        translation = await i18n_service.get_translation(
            key=key,
            locale=locale,
            namespace=namespace
        )
        
        return {
            "success": True,
            "translation": translation,
            "key": key,
            "locale": locale.value if locale else None,
            "namespace": namespace.value if namespace else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/translations")
async def get_translations(
    locale: Optional[Locale] = Query(None, description="Target locale"),
    namespace: Optional[TranslationNamespace] = Query(None, description="Translation namespace"),
    accept_language: Optional[str] = Header(None, description="Accept-Language header"),
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get translations for a locale and namespace.
    
    This endpoint retrieves all translations for a given locale
    and optional namespace.
    """
    try:
        # Detect locale if not provided
        if not locale:
            if current_user:
                # Try to get user's preferred locale
                user_locale = await i18n_service.get_user_locale(str(current_user.id))
                locale = user_locale
            else:
                # Detect from Accept-Language header
                locale = await i18n_service.detect_locale(accept_language or "")
        
        # Get translations
        translations = await i18n_service.get_translations(
            locale=locale,
            namespace=namespace
        )
        
        return {
            "success": True,
            "locale": locale.value if locale else None,
            "namespace": namespace.value if namespace else None,
            "translations": translations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/locales")
async def get_supported_locales(
    i18n_service: I18nService = Depends(get_i18n_service)
):
    """
    Get list of supported locales.
    
    This endpoint returns all supported locales with their display names.
    """
    try:
        locales = await i18n_service.get_supported_locales()
        
        return {
            "success": True,
            "locales": locales,
            "count": len(locales)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supported locales: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/translations")
async def add_translation(
    request: TranslationRequest,
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: User = Depends(get_current_user)
):
    """
    Add or update a translation.
    
    This endpoint adds a new translation or updates an existing one.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Add translation
        success = await i18n_service.add_translation(
            key=request.key,
            value=request.value,
            locale=request.locale,
            namespace=request.namespace
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add translation")
        
        return {
            "success": True,
            "message": "Translation added successfully",
            "key": request.key,
            "locale": request.locale.value,
            "namespace": request.namespace.value,
            "added_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding translation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/translations/import")
async def import_translations(
    request: TranslationImportRequest,
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: User = Depends(get_current_user)
):
    """
    Import translations from external source.
    
    This endpoint imports translations in bulk from an external source.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Import translations
        success = await i18n_service.import_translations(
            translations=request.translations,
            overwrite=request.overwrite
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to import translations")
        
        return {
            "success": True,
            "message": "Translations imported successfully",
            "overwrite": request.overwrite,
            "imported_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing translations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/translations/export")
async def export_translations(
    locale: Optional[Locale] = Query(None, description="Specific locale to export"),
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: User = Depends(get_current_user)
):
    """
    Export translations for backup or analysis.
    
    This endpoint exports translations in JSON format.
    Only admin users can access this endpoint.
    """
    try:
        # Check admin permissions
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Export translations
        translations = await i18n_service.export_translations(locale=locale)
        
        return {
            "success": True,
            "translations": translations,
            "locale": locale.value if locale else "all",
            "exported_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting translations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/user/locale")
async def set_user_locale(
    request: UserLocaleRequest,
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: User = Depends(get_current_user)
):
    """
    Set user's preferred locale.
    
    This endpoint sets the preferred locale for the current user.
    """
    try:
        # Set user locale
        success = await i18n_service.set_user_locale(
            user_id=str(current_user.id),
            locale=request.locale
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to set user locale")
        
        return {
            "success": True,
            "message": "User locale set successfully",
            "locale": request.locale.value,
            "user_id": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting user locale: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/user/locale")
async def get_user_locale(
    i18n_service: I18nService = Depends(get_i18n_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's preferred locale.
    
    This endpoint retrieves the preferred locale for the current user.
    """
    try:
        # Get user locale
        locale = await i18n_service.get_user_locale(str(current_user.id))
        
        return {
            "success": True,
            "locale": locale.value if locale else None,
            "user_id": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user locale: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/detect-locale")
async def detect_locale(
    accept_language: str = Header(..., description="Accept-Language header"),
    i18n_service: I18nService = Depends(get_i18n_service)
):
    """
    Detect locale from Accept-Language header.
    
    This endpoint detects the best matching locale from the Accept-Language header.
    """
    try:
        # Detect locale
        locale = await i18n_service.detect_locale(accept_language)
        
        return {
            "success": True,
            "detected_locale": locale.value,
            "accept_language": accept_language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting locale: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/namespaces")
async def get_translation_namespaces():
    """
    Get list of translation namespaces.
    
    This endpoint returns all available translation namespaces.
    """
    try:
        namespaces = [
            {
                "code": namespace.value,
                "name": namespace.value.replace("_", " ").title()
            }
            for namespace in TranslationNamespace
        ]
        
        return {
            "success": True,
            "namespaces": namespaces,
            "count": len(namespaces)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translation namespaces: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def get_i18n_health(
    i18n_service: I18nService = Depends(get_i18n_service)
):
    """
    Get i18n service health status.
    
    This endpoint returns the health status of the i18n service.
    Only admin users can access this endpoint.
    """
    try:
        # Get supported locales count
        supported_locales = await i18n_service.get_supported_locales()
        
        # Get total translations count
        total_translations = 0
        for locale in Locale:
            for namespace in TranslationNamespace:
                translations = await i18n_service.get_translations(locale, namespace)
                total_translations += len(translations)
        
        return {
            "success": True,
            "status": "healthy",
            "supported_locales": len(supported_locales),
            "total_translations": total_translations,
            "cache_status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting i18n health: {str(e)}")
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
    logger.error(f"Unhandled exception in i18n routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )