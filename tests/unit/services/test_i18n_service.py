"""
Unit tests for Internationalization (i18n) Service.

This module tests the i18n service functionality including
translation management, locale detection, and
language-specific content delivery.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.services.i18n_service import (
    I18nService,
    Locale,
    TranslationNamespace
)
from backend.cache.unified_cache import UnifiedCacheManager


class TestI18nService:
    """Test cases for I18nService."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create mock cache manager."""
        return Mock(spec=UnifiedCacheManager)
    
    @pytest.fixture
    def i18n_service(self, cache_manager):
        """Create i18n service instance."""
        return I18nService(cache_manager)
    
    @pytest.mark.asyncio
    async def test_initialize_service(self, i18n_service):
        """Test service initialization."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value={})
        i18n_service.cache_manager.set = AsyncMock()
        
        # Initialize service
        await i18n_service.initialize()
        
        # Verify initialization
        assert len(i18n_service.translations) > 0
        assert Locale.ENGLISH.value in i18n_service.translations
        assert Locale.KOREAN.value in i18n_service.translations
        assert TranslationNamespace.COMMON.value in i18n_service.translations[Locale.ENGLISH.value]
    
    @pytest.mark.asyncio
    async def test_get_translation_english(self, i18n_service):
        """Test getting English translation."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Get translation
        translation = await i18n_service.get_translation(
            key="loading",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        
        # Verify result
        assert translation == "Loading..."
    
    @pytest.mark.asyncio
    async def test_get_translation_korean(self, i18n_service):
        """Test getting Korean translation."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Add Korean translation
        await i18n_service.add_translation(
            key="loading",
            value="로딩 중...",
            locale=Locale.KOREAN,
            namespace=TranslationNamespace.COMMON
        )
        
        # Get translation
        translation = await i18n_service.get_translation(
            key="loading",
            locale=Locale.KOREAN,
            namespace=TranslationNamespace.COMMON
        )
        
        # Verify result
        assert translation == "로딩 중..."
    
    @pytest.mark.asyncio
    async def test_get_translation_fallback(self, i18n_service):
        """Test translation fallback to English."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Try to get translation for non-existent key in Korean
        translation = await i18n_service.get_translation(
            key="non_existent_key",
            locale=Locale.KOREAN,
            namespace=TranslationNamespace.COMMON
        )
        
        # Verify fallback to key
        assert translation == "non_existent_key"
    
    @pytest.mark.asyncio
    async def test_get_translation_with_variables(self, i18n_service):
        """Test translation with variable interpolation."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Add translation with variables
        await i18n_service.add_translation(
            key="welcome_message",
            value="Hello {name}, welcome to {app_name}!",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        
        # Get translation with variables
        translation = await i18n_service.get_translation(
            key="welcome_message",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON,
            name="John",
            app_name="InsiteChart"
        )
        
        # Verify result
        assert translation == "Hello John, welcome to InsiteChart!"
    
    @pytest.mark.asyncio
    async def test_get_translations_namespace(self, i18n_service):
        """Test getting all translations for a namespace."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value={})
        i18n_service.cache_manager.set = AsyncMock()
        
        # Get translations
        translations = await i18n_service.get_translations(
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        
        # Verify result
        assert isinstance(translations, dict)
        assert "loading" in translations
        assert "error" in translations
        assert "success" in translations
    
    @pytest.mark.asyncio
    async def test_get_translations_all_namespaces(self, i18n_service):
        """Test getting all translations for a locale."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value={})
        i18n_service.cache_manager.set = AsyncMock()
        
        # Get translations
        translations = await i18n_service.get_translations(locale=Locale.ENGLISH)
        
        # Verify result
        assert isinstance(translations, dict)
        assert TranslationNamespace.COMMON.value in translations
        assert TranslationNamespace.ERRORS.value in translations
        assert TranslationNamespace.FINANCIAL.value in translations
    
    @pytest.mark.asyncio
    async def test_detect_locale_from_accept_language(self, i18n_service):
        """Test locale detection from Accept-Language header."""
        # Test English detection
        locale = await i18n_service.detect_locale("en-US,en;q=0.9")
        assert locale == Locale.ENGLISH
        
        # Test Korean detection
        locale = await i18n_service.detect_locale("ko-KR,ko;q=0.9")
        assert locale == Locale.KOREAN
        
        # Test Japanese detection
        locale = await i18n_service.detect_locale("ja-JP,ja;q=0.9")
        assert locale == Locale.JAPANESE
        
        # Test fallback to default
        locale = await i18n_service.detect_locale("unknown-LANG")
        assert locale == i18n_service.default_locale
    
    @pytest.mark.asyncio
    async def test_set_user_locale(self, i18n_service):
        """Test setting user's preferred locale."""
        # Mock cache operations
        i18n_service.cache_manager.set = AsyncMock()
        
        # Set user locale
        result = await i18n_service.set_user_locale("user123", Locale.KOREAN)
        
        # Verify result
        assert result is True
        i18n_service.cache_manager.set.assert_called_with(
            "i18n:user_locale:user123",
            Locale.KOREAN.value,
            ttl=86400 * 30  # 30 days
        )
    
    @pytest.mark.asyncio
    async def test_get_user_locale(self, i18n_service):
        """Test getting user's preferred locale."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=Locale.KOREAN.value)
        
        # Get user locale
        locale = await i18n_service.get_user_locale("user123")
        
        # Verify result
        assert locale == Locale.KOREAN
    
    @pytest.mark.asyncio
    async def test_get_user_locale_not_found(self, i18n_service):
        """Test getting user locale when not found."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        
        # Get user locale
        locale = await i18n_service.get_user_locale("user123")
        
        # Verify result
        assert locale is None
    
    @pytest.mark.asyncio
    async def test_get_supported_locales(self, i18n_service):
        """Test getting supported locales."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Get supported locales
        locales = await i18n_service.get_supported_locales()
        
        # Verify result
        assert isinstance(locales, list)
        assert len(locales) > 0
        
        # Check structure of locale info
        locale_info = locales[0]
        assert "code" in locale_info
        assert "name" in locale_info
        assert "native_name" in locale_info
        
        # Check for specific locales
        locale_codes = [locale["code"] for locale in locales]
        assert Locale.ENGLISH.value in locale_codes
        assert Locale.KOREAN.value in locale_codes
        assert Locale.JAPANESE.value in locale_codes
    
    @pytest.mark.asyncio
    async def test_add_translation(self, i18n_service):
        """Test adding a new translation."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Add translation
        result = await i18n_service.add_translation(
            key="test_key",
            value="Test Value",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        
        # Verify result
        assert result is True
        assert i18n_service.translations[Locale.ENGLISH.value][TranslationNamespace.COMMON.value]["test_key"] == "Test Value"
    
    @pytest.mark.asyncio
    async def test_add_translation_existing(self, i18n_service):
        """Test updating an existing translation."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Add initial translation
        await i18n_service.add_translation(
            key="update_test",
            value="Original Value",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        
        # Update translation
        result = await i18n_service.add_translation(
            key="update_test",
            value="Updated Value",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        
        # Verify result
        assert result is True
        assert i18n_service.translations[Locale.ENGLISH.value][TranslationNamespace.COMMON.value]["update_test"] == "Updated Value"
    
    @pytest.mark.asyncio
    async def test_export_translations(self, i18n_service):
        """Test exporting translations."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value={})
        
        # Export all translations
        all_translations = await i18n_service.export_translations()
        
        # Verify result
        assert isinstance(all_translations, dict)
        assert Locale.ENGLISH.value in all_translations
        assert TranslationNamespace.COMMON.value in all_translations[Locale.ENGLISH.value]
        
        # Export specific locale
        english_translations = await i18n_service.export_translations(locale=Locale.ENGLISH)
        
        # Verify result
        assert isinstance(english_translations, dict)
        assert TranslationNamespace.COMMON.value in english_translations
        assert TranslationNamespace.ERRORS.value in english_translations
    
    @pytest.mark.asyncio
    async def test_import_translations(self, i18n_service):
        """Test importing translations."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Prepare import data
        import_data = {
            Locale.KOREAN.value: {
                TranslationNamespace.COMMON.value: {
                    "loading": "로딩 중...",
                    "error": "오류",
                    "success": "성공"
                }
            }
        }
        
        # Import translations
        result = await i18n_service.import_translations(import_data, overwrite=False)
        
        # Verify result
        assert result is True
        assert i18n_service.translations[Locale.KOREAN.value][TranslationNamespace.COMMON.value]["loading"] == "로딩 중..."
        assert i18n_service.translations[Locale.KOREAN.value][TranslationNamespace.COMMON.value]["error"] == "오류"
    
    @pytest.mark.asyncio
    async def test_import_translations_overwrite(self, i18n_service):
        """Test importing translations with overwrite."""
        # Mock cache operations
        i18n_service.cache_manager.get = AsyncMock(return_value=None)
        i18n_service.cache_manager.set = AsyncMock()
        
        # Add existing translation
        await i18n_service.add_translation(
            key="existing_key",
            value="Original Value",
            locale=Locale.KOREAN,
            namespace=TranslationNamespace.COMMON
        )
        
        # Prepare import data with overwrite
        import_data = {
            Locale.KOREAN.value: {
                TranslationNamespace.COMMON.value: {
                    "existing_key": "Overwritten Value",
                    "new_key": "New Value"
                }
            }
        }
        
        # Import translations with overwrite
        result = await i18n_service.import_translations(import_data, overwrite=True)
        
        # Verify result
        assert result is True
        assert i18n_service.translations[Locale.KOREAN.value][TranslationNamespace.COMMON.value]["existing_key"] == "Overwritten Value"
        assert i18n_service.translations[Locale.KOREAN.value][TranslationNamespace.COMMON.value]["new_key"] == "New Value"
    
    def test_get_native_name(self, i18n_service):
        """Test getting native names for locales."""
        # Test English
        assert i18n_service._get_native_name(Locale.ENGLISH) == "English"
        
        # Test Korean
        assert i18n_service._get_native_name(Locale.KOREAN) == "한국어"
        
        # Test Japanese
        assert i18n_service._get_native_name(Locale.JAPANESE) == "日本語"
        
        # Test Chinese Simplified
        assert i18n_service._get_native_name(Locale.CHINESE_SIMPLIFIED) == "简体中文"
        
        # Test Chinese Traditional
        assert i18n_service._get_native_name(Locale.CHINESE_TRADITIONAL) == "繁體中文"
    
    def test_interpolate_variables(self, i18n_service):
        """Test variable interpolation in translations."""
        # Test with variables
        text = "Hello {name}, you have {count} messages."
        result = i18n_service._interpolate_variables(text, name="John", count=5)
        assert result == "Hello John, you have 5 messages."
        
        # Test without variables
        text = "Simple message"
        result = i18n_service._interpolate_variables(text)
        assert result == "Simple message"
        
        # Test with missing variables
        text = "Hello {name}, missing {missing_var}"
        result = i18n_service._interpolate_variables(text, name="John")
        assert result == "Hello John, missing {missing_var}"
    
    def test_get_translation_from_memory(self, i18n_service):
        """Test getting translation from in-memory data."""
        # Test existing translation
        translation = i18n_service._get_translation_from_memory(
            key="loading",
            locale=Locale.ENGLISH,
            namespace=TranslationNamespace.COMMON
        )
        assert translation == "Loading..."
        
        # Test non-existing translation
        translation = i18n_service._get_translation_from_memory(
            key="non_existent",
            locale=Locale.KOREAN,
            namespace=TranslationNamespace.COMMON
        )
        assert translation == "non_existent"
    
    def test_locale_enum(self):
        """Test Locale enum values."""
        # Test specific locales
        assert Locale.ENGLISH.value == "en"
        assert Locale.KOREAN.value == "ko"
        assert Locale.JAPANESE.value == "ja"
        assert Locale.CHINESE_SIMPLIFIED.value == "zh-CN"
        assert Locale.CHINESE_TRADITIONAL.value == "zh-TW"
        assert Locale.SPANISH.value == "es"
        assert Locale.FRENCH.value == "fr"
        assert Locale.GERMAN.value == "de"
        assert Locale.RUSSIAN.value == "ru"
        assert Locale.PORTUGUESE.value == "pt"
        assert Locale.ITALIAN.value == "it"
        assert Locale.ARABIC.value == "ar"
        assert Locale.HINDI.value == "hi"
    
    def test_translation_namespace_enum(self):
        """Test TranslationNamespace enum values."""
        # Test specific namespaces
        assert TranslationNamespace.COMMON.value == "common"
        assert TranslationNamespace.UI.value == "ui"
        assert TranslationNamespace.ERRORS.value == "errors"
        assert TranslationNamespace.FINANCIAL.value == "financial"
        assert TranslationNamespace.NOTIFICATIONS.value == "notifications"
        assert TranslationNamespace.DASHBOARD.value == "dashboard"
        assert TranslationNamespace.STOCKS.value == "stocks"
        assert TranslationNamespace.SENTIMENT.value == "sentiment"
        assert TranslationNamespace.ANALYTICS.value == "analytics"
        assert TranslationNamespace.SETTINGS.value == "settings"