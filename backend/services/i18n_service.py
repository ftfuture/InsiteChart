"""
Internationalization (i18n) Service for InsiteChart platform.

This service provides multi-language support for the platform,
including translation management, locale detection, and
language-specific content delivery.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import asyncio
from enum import Enum

from ..cache.unified_cache import UnifiedCacheManager

# Configure logging
logger = logging.getLogger(__name__)

class Locale(Enum):
    """Supported locales."""
    ENGLISH = "en"
    KOREAN = "ko"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    RUSSIAN = "ru"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    ARABIC = "ar"
    HINDI = "hi"

class TranslationNamespace(Enum):
    """Translation namespaces."""
    COMMON = "common"
    UI = "ui"
    ERRORS = "errors"
    FINANCIAL = "financial"
    NOTIFICATIONS = "notifications"
    DASHBOARD = "dashboard"
    STOCKS = "stocks"
    SENTIMENT = "sentiment"
    ANALYTICS = "analytics"
    SETTINGS = "settings"

class I18nService:
    """
    Internationalization service for managing translations and locale support.
    """
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        """
        Initialize I18n service.
        
        Args:
            cache_manager: Unified cache manager instance
        """
        self.cache_manager = cache_manager
        self.translations: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.fallback_locale = Locale.ENGLISH
        self.default_locale = Locale.ENGLISH
        self.supported_locales = list(Locale)
        self.translations_dir = Path(__file__).parent.parent.parent / "locales"
        
        # Cache keys
        self.cache_prefix = "i18n:"
        self.translations_cache_key = f"{self.cache_prefix}translations"
        self.locale_cache_key = f"{self.cache_prefix}locale"
        
        # Initialize translations
        self._load_translations()
    
    async def initialize(self):
        """Initialize the i18n service."""
        try:
            logger.info("Initializing I18n service...")
            
            # Load translations from files
            await self._load_translation_files()
            
            # Cache translations
            await self._cache_translations()
            
            logger.info("I18n service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize I18n service: {str(e)}")
            raise
    
    def _load_translations(self):
        """Load default translations."""
        # Initialize translation structure
        for locale in self.supported_locales:
            self.translations[locale.value] = {}
            for namespace in TranslationNamespace:
                self.translations[locale.value][namespace.value] = {}
        
        # Load English fallback translations
        self._load_fallback_translations()
    
    def _load_fallback_translations(self):
        """Load fallback English translations."""
        fallback_translations = {
            Locale.ENGLISH.value: {
                TranslationNamespace.COMMON.value: {
                    "loading": "Loading...",
                    "error": "Error",
                    "success": "Success",
                    "cancel": "Cancel",
                    "confirm": "Confirm",
                    "save": "Save",
                    "delete": "Delete",
                    "edit": "Edit",
                    "view": "View",
                    "search": "Search",
                    "filter": "Filter",
                    "sort": "Sort",
                    "export": "Export",
                    "import": "Import",
                    "refresh": "Refresh",
                    "close": "Close",
                    "back": "Back",
                    "next": "Next",
                    "previous": "Previous",
                    "submit": "Submit",
                    "reset": "Reset",
                    "clear": "Clear",
                    "select": "Select",
                    "all": "All",
                    "none": "None",
                    "yes": "Yes",
                    "no": "No",
                    "ok": "OK",
                    "help": "Help",
                    "settings": "Settings",
                    "profile": "Profile",
                    "logout": "Logout",
                    "login": "Login",
                    "register": "Register",
                    "dashboard": "Dashboard",
                    "home": "Home"
                },
                TranslationNamespace.ERRORS.value: {
                    "network_error": "Network error occurred",
                    "server_error": "Server error occurred",
                    "not_found": "Resource not found",
                    "unauthorized": "Unauthorized access",
                    "forbidden": "Access forbidden",
                    "validation_error": "Validation error",
                    "timeout_error": "Request timeout",
                    "unknown_error": "Unknown error occurred",
                    "invalid_credentials": "Invalid credentials",
                    "account_locked": "Account locked",
                    "session_expired": "Session expired",
                    "maintenance_mode": "System under maintenance"
                },
                TranslationNamespace.FINANCIAL.value: {
                    "stock": "Stock",
                    "price": "Price",
                    "volume": "Volume",
                    "market_cap": "Market Cap",
                    "pe_ratio": "P/E Ratio",
                    "dividend": "Dividend",
                    "yield": "Yield",
                    "change": "Change",
                    "change_percent": "Change %",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "bid": "Bid",
                    "ask": "Ask",
                    "spread": "Spread",
                    "volatility": "Volatility",
                    "momentum": "Momentum",
                    "trend": "Trend",
                    "support": "Support",
                    "resistance": "Resistance",
                    "bullish": "Bullish",
                    "bearish": "Bearish",
                    "neutral": "Neutral"
                },
                TranslationNamespace.DASHBOARD.value: {
                    "portfolio": "Portfolio",
                    "watchlist": "Watchlist",
                    "market_overview": "Market Overview",
                    "trending_stocks": "Trending Stocks",
                    "top_gainers": "Top Gainers",
                    "top_losers": "Top Losers",
                    "most_active": "Most Active",
                    "market_indices": "Market Indices",
                    "sector_performance": "Sector Performance",
                    "news_feed": "News Feed",
                    "economic_calendar": "Economic Calendar",
                    "earnings_calendar": "Earnings Calendar",
                    "ipo_calendar": "IPO Calendar"
                },
                TranslationNamespace.STOCKS.value: {
                    "symbol": "Symbol",
                    "company_name": "Company Name",
                    "sector": "Sector",
                    "industry": "Industry",
                    "description": "Description",
                    "website": "Website",
                    "employees": "Employees",
                    "founded": "Founded",
                    "headquarters": "Headquarters",
                    "ceo": "CEO",
                    "market_cap": "Market Capitalization",
                    "revenue": "Revenue",
                    "net_income": "Net Income",
                    "eps": "Earnings Per Share",
                    "book_value": "Book Value",
                    "price_to_book": "Price to Book",
                    "debt_to_equity": "Debt to Equity",
                    "current_ratio": "Current Ratio",
                    "quick_ratio": "Quick Ratio"
                },
                TranslationNamespace.SENTIMENT.value: {
                    "sentiment": "Sentiment",
                    "positive": "Positive",
                    "negative": "Negative",
                    "neutral": "Neutral",
                    "score": "Score",
                    "confidence": "Confidence",
                    "social_media": "Social Media",
                    "news": "News",
                    "analyst_ratings": "Analyst Ratings",
                    "insider_trading": "Insider Trading",
                    "institutional_ownership": "Institutional Ownership",
                    "short_interest": "Short Interest",
                    "options_flow": "Options Flow",
                    "reddit_sentiment": "Reddit Sentiment",
                    "twitter_sentiment": "Twitter Sentiment"
                },
                TranslationNamespace.ANALYTICS.value: {
                    "analysis": "Analysis",
                    "technical": "Technical",
                    "fundamental": "Fundamental",
                    "quantitative": "Quantitative",
                    "correlation": "Correlation",
                    "regression": "Regression",
                    "forecasting": "Forecasting",
                    "machine_learning": "Machine Learning",
                    "pattern_recognition": "Pattern Recognition",
                    "anomaly_detection": "Anomaly Detection",
                    "risk_assessment": "Risk Assessment",
                    "portfolio_optimization": "Portfolio Optimization",
                    "backtesting": "Backtesting",
                    "monte_carlo": "Monte Carlo",
                    "value_at_risk": "Value at Risk"
                },
                TranslationNamespace.NOTIFICATIONS.value: {
                    "notifications": "Notifications",
                    "alerts": "Alerts",
                    "price_alert": "Price Alert",
                    "volume_alert": "Volume Alert",
                    "sentiment_alert": "Sentiment Alert",
                    "news_alert": "News Alert",
                    "earnings_alert": "Earnings Alert",
                    "dividend_alert": "Dividend Alert",
                    "split_alert": "Split Alert",
                    "rating_change": "Rating Change",
                    "target_price": "Target Price",
                    "recommendation": "Recommendation",
                    "upgrade": "Upgrade",
                    "downgrade": "Downgrade",
                    "initiation": "Initiation"
                },
                TranslationNamespace.SETTINGS.value: {
                    "preferences": "Preferences",
                    "language": "Language",
                    "theme": "Theme",
                    "timezone": "Timezone",
                    "currency": "Currency",
                    "date_format": "Date Format",
                    "time_format": "Time Format",
                    "number_format": "Number Format",
                    "notification_settings": "Notification Settings",
                    "email_notifications": "Email Notifications",
                    "push_notifications": "Push Notifications",
                    "sms_notifications": "SMS Notifications",
                    "privacy": "Privacy",
                    "security": "Security",
                    "two_factor_auth": "Two-Factor Authentication",
                    "api_keys": "API Keys",
                    "data_export": "Data Export"
                }
            }
        }
        
        # Apply fallback translations
        for locale, namespaces in fallback_translations.items():
            for namespace, translations in namespaces.items():
                self.translations[locale][namespace].update(translations)
    
    async def _load_translation_files(self):
        """Load translation files from disk."""
        try:
            if not self.translations_dir.exists():
                logger.warning(f"Translations directory not found: {self.translations_dir}")
                return
            
            # Load translation files for each locale
            for locale in self.supported_locales:
                locale_dir = self.translations_dir / locale.value
                if not locale_dir.exists():
                    continue
                
                # Load namespace files
                for namespace in TranslationNamespace:
                    file_path = locale_dir / f"{namespace.value}.json"
                    if file_path.exists():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                translations = json.load(f)
                                self.translations[locale.value][namespace.value].update(translations)
                                logger.debug(f"Loaded {len(translations)} translations for {locale.value}/{namespace.value}")
                        except Exception as e:
                            logger.error(f"Failed to load translation file {file_path}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to load translation files: {str(e)}")
    
    async def _cache_translations(self):
        """Cache translations for fast access."""
        try:
            cache_key = self.translations_cache_key
            await self.cache_manager.set(cache_key, self.translations, ttl=3600)  # 1 hour
            logger.debug("Translations cached successfully")
        except Exception as e:
            logger.error(f"Failed to cache translations: {str(e)}")
    
    async def get_translation(
        self,
        key: str,
        locale: Optional[Locale] = None,
        namespace: Optional[TranslationNamespace] = None,
        **kwargs
    ) -> str:
        """
        Get translation for a key.
        
        Args:
            key: Translation key
            locale: Target locale (uses default if not provided)
            namespace: Translation namespace (uses common if not provided)
            **kwargs: Variables for string interpolation
            
        Returns:
            Translated string
        """
        try:
            # Use defaults if not provided
            target_locale = locale or self.default_locale
            target_namespace = namespace or TranslationNamespace.COMMON
            
            # Try to get translation from cache first
            cache_key = f"{self.cache_prefix}translation:{target_locale.value}:{target_namespace.value}:{key}"
            cached_translation = await self.cache_manager.get(cache_key)
            
            if cached_translation:
                return self._interpolate_variables(cached_translation, **kwargs)
            
            # Get translation from memory
            translation = self._get_translation_from_memory(key, target_locale, target_namespace)
            
            # Cache the translation
            if translation:
                await self.cache_manager.set(cache_key, translation, ttl=1800)  # 30 minutes
            
            # Interpolate variables
            return self._interpolate_variables(translation, **kwargs)
            
        except Exception as e:
            logger.error(f"Failed to get translation for key '{key}': {str(e)}")
            return key  # Return key as fallback
    
    def _get_translation_from_memory(
        self,
        key: str,
        locale: Locale,
        namespace: TranslationNamespace
    ) -> Optional[str]:
        """Get translation from in-memory data."""
        try:
            # Try target locale first
            if locale.value in self.translations:
                if namespace.value in self.translations[locale.value]:
                    if key in self.translations[locale.value][namespace.value]:
                        return self.translations[locale.value][namespace.value][key]
            
            # Try fallback locale
            if locale != self.fallback_locale:
                if self.fallback_locale.value in self.translations:
                    if namespace.value in self.translations[self.fallback_locale.value]:
                        if key in self.translations[self.fallback_locale.value][namespace.value]:
                            return self.translations[self.fallback_locale.value][namespace.value][key]
            
            # Return key if not found
            return key
            
        except Exception as e:
            logger.error(f"Failed to get translation from memory: {str(e)}")
            return key
    
    def _interpolate_variables(self, text: str, **kwargs) -> str:
        """Interpolate variables in translation text."""
        try:
            if not kwargs:
                return text
            
            # Simple string interpolation
            for key, value in kwargs.items():
                text = text.replace(f"{{{key}}}", str(value))
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to interpolate variables: {str(e)}")
            return text
    
    async def get_translations(
        self,
        locale: Optional[Locale] = None,
        namespace: Optional[TranslationNamespace] = None
    ) -> Dict[str, Any]:
        """
        Get all translations for a locale and namespace.
        
        Args:
            locale: Target locale (uses default if not provided)
            namespace: Translation namespace (uses all if not provided)
            
        Returns:
            Dictionary of translations
        """
        try:
            target_locale = locale or self.default_locale
            
            # Check cache first
            cache_key = f"{self.cache_prefix}translations:{target_locale.value}"
            if namespace:
                cache_key += f":{namespace.value}"
            
            cached_translations = await self.cache_manager.get(cache_key)
            if cached_translations:
                return cached_translations
            
            # Get translations from memory
            if target_locale.value in self.translations:
                if namespace:
                    return self.translations[target_locale.value].get(namespace.value, {})
                else:
                    return self.translations[target_locale.value]
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get translations: {str(e)}")
            return {}
    
    async def detect_locale(self, accept_language: str) -> Locale:
        """
        Detect locale from Accept-Language header.
        
        Args:
            accept_language: Accept-Language header value
            
        Returns:
            Detected locale
        """
        try:
            if not accept_language:
                return self.default_locale
            
            # Parse Accept-Language header
            languages = []
            for item in accept_language.split(','):
                parts = item.strip().split(';')
                lang = parts[0].lower()
                quality = 1.0
                
                if len(parts) > 1 and parts[1].startswith('q='):
                    try:
                        quality = float(parts[1][2:])
                    except ValueError:
                        pass
                
                languages.append((lang, quality))
            
            # Sort by quality
            languages.sort(key=lambda x: x[1], reverse=True)
            
            # Find matching locale
            for lang, _ in languages:
                # Direct match
                for locale in self.supported_locales:
                    if locale.value.lower() == lang:
                        return locale
                
                # Partial match (e.g., 'en' matches 'en-US')
                for locale in self.supported_locales:
                    if locale.value.lower().startswith(lang):
                        return locale
            
            return self.default_locale
            
        except Exception as e:
            logger.error(f"Failed to detect locale: {str(e)}")
            return self.default_locale
    
    async def set_user_locale(self, user_id: str, locale: Locale) -> bool:
        """
        Set user's preferred locale.
        
        Args:
            user_id: User ID
            locale: Preferred locale
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = f"{self.cache_prefix}user_locale:{user_id}"
            await self.cache_manager.set(cache_key, locale.value, ttl=86400 * 30)  # 30 days
            return True
        except Exception as e:
            logger.error(f"Failed to set user locale: {str(e)}")
            return False
    
    async def get_user_locale(self, user_id: str) -> Optional[Locale]:
        """
        Get user's preferred locale.
        
        Args:
            user_id: User ID
            
        Returns:
            User's preferred locale or None
        """
        try:
            cache_key = f"{self.cache_prefix}user_locale:{user_id}"
            locale_value = await self.cache_manager.get(cache_key)
            
            if locale_value:
                for locale in Locale:
                    if locale.value == locale_value:
                        return locale
            
            return None
        except Exception as e:
            logger.error(f"Failed to get user locale: {str(e)}")
            return None
    
    async def get_supported_locales(self) -> List[Dict[str, str]]:
        """
        Get list of supported locales.
        
        Returns:
            List of supported locales with display names
        """
        try:
            locales = []
            for locale in self.supported_locales:
                display_name = await self.get_translation(
                    f"locale.{locale.value}",
                    locale=locale,
                    namespace=TranslationNamespace.COMMON
                )
                locales.append({
                    "code": locale.value,
                    "name": display_name or locale.value,
                    "native_name": self._get_native_name(locale)
                })
            
            return locales
        except Exception as e:
            logger.error(f"Failed to get supported locales: {str(e)}")
            return []
    
    def _get_native_name(self, locale: Locale) -> str:
        """Get native name for locale."""
        native_names = {
            Locale.ENGLISH: "English",
            Locale.KOREAN: "한국어",
            Locale.JAPANESE: "日本語",
            Locale.CHINESE_SIMPLIFIED: "简体中文",
            Locale.CHINESE_TRADITIONAL: "繁體中文",
            Locale.SPANISH: "Español",
            Locale.FRENCH: "Français",
            Locale.GERMAN: "Deutsch",
            Locale.RUSSIAN: "Русский",
            Locale.PORTUGUESE: "Português",
            Locale.ITALIAN: "Italiano",
            Locale.ARABIC: "العربية",
            Locale.HINDI: "हिन्दी"
        }
        return native_names.get(locale, locale.value)
    
    async def add_translation(
        self,
        key: str,
        value: str,
        locale: Locale,
        namespace: TranslationNamespace
    ) -> bool:
        """
        Add or update a translation.
        
        Args:
            key: Translation key
            value: Translation value
            locale: Target locale
            namespace: Translation namespace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update in-memory translation
            if locale.value not in self.translations:
                self.translations[locale.value] = {}
            if namespace.value not in self.translations[locale.value]:
                self.translations[locale.value][namespace.value] = {}
            
            self.translations[locale.value][namespace.value][key] = value
            
            # Update cache
            cache_key = f"{self.cache_prefix}translation:{locale.value}:{namespace.value}:{key}"
            await self.cache_manager.set(cache_key, value, ttl=1800)
            
            # Update translations cache
            await self._cache_translations()
            
            logger.info(f"Added translation: {locale.value}/{namespace.value}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add translation: {str(e)}")
            return False
    
    async def export_translations(self, locale: Optional[Locale] = None) -> Dict[str, Any]:
        """
        Export translations for backup or analysis.
        
        Args:
            locale: Specific locale to export (exports all if not provided)
            
        Returns:
            Exported translations
        """
        try:
            if locale:
                return self.translations.get(locale.value, {})
            else:
                return self.translations
        except Exception as e:
            logger.error(f"Failed to export translations: {str(e)}")
            return {}
    
    async def import_translations(
        self,
        translations: Dict[str, Any],
        overwrite: bool = False
    ) -> bool:
        """
        Import translations from backup or external source.
        
        Args:
            translations: Translations to import
            overwrite: Whether to overwrite existing translations
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for locale_code, namespaces in translations.items():
                # Validate locale
                try:
                    locale = Locale(locale_code)
                except ValueError:
                    logger.warning(f"Skipping invalid locale: {locale_code}")
                    continue
                
                for namespace_code, translation_dict in namespaces.items():
                    # Validate namespace
                    try:
                        namespace = TranslationNamespace(namespace_code)
                    except ValueError:
                        logger.warning(f"Skipping invalid namespace: {namespace_code}")
                        continue
                    
                    # Import translations
                    for key, value in translation_dict.items():
                        # Check if translation exists
                        existing_translation = self._get_translation_from_memory(key, locale, namespace)
                        if overwrite or existing_translation == key:
                            await self.add_translation(key, value, locale, namespace)
            
            # Update cache
            await self._cache_translations()
            
            logger.info("Translations imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import translations: {str(e)}")
            return False