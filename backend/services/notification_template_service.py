"""
Notification Template Service for InsiteChart platform.

This service manages notification templates for different types
of notifications and supports multiple languages.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..cache.unified_cache import UnifiedCacheManager
from ..models.unified_models import NotificationChannel
from .notification_types import NotificationPriority


class TemplateLanguage(str, Enum):
    """Supported template languages."""
    ENGLISH = "en"
    KOREAN = "ko"
    JAPANESE = "ja"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"


class TemplateType(str, Enum):
    """Template types."""
    PRICE_ALERT = "price_alert"
    SENTIMENT_ALERT = "sentiment_alert"
    TRENDING_ALERT = "trending_alert"
    VOLUME_SPIKE = "volume_spike"
    MARKET_EVENT = "market_event"
    SYSTEM_NOTIFICATION = "system_notification"
    WELCOME = "welcome"
    ERROR = "error"


@dataclass
class NotificationTemplate:
    """Notification template data model."""
    id: str
    name: str
    type: TemplateType
    title_template: str
    message_template: str
    language: TemplateLanguage = TemplateLanguage.ENGLISH
    channel: NotificationChannel = NotificationChannel.WEBSOCKET
    variables: List[str] = field(default_factory=list)
    default_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.WEBSOCKET])
    default_priority: NotificationPriority = NotificationPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    priority: int = 1  # Lower number = higher priority
    
    def render(self, variables: Dict[str, Any]) -> tuple[str, str]:
        """Render template with variables."""
        try:
            title = self.title_template.format(**variables)
            message = self.message_template.format(**variables)
            return title, message
        except KeyError as e:
            raise ValueError(f"Missing variable in template: {str(e)}")


@dataclass
class RenderedTemplate:
    """Rendered notification template."""
    template_id: str
    title: str
    message: str
    language: TemplateLanguage
    variables: Dict[str, Any]
    rendered_at: datetime = field(default_factory=datetime.utcnow)


class NotificationTemplateService:
    """Notification template service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Template storage
        self.templates: Dict[str, NotificationTemplate] = {}
        
        # Cache TTL settings
        self.template_cache_ttl = 3600  # 1 hour
        self.rendered_cache_ttl = 300  # 5 minutes
        
        self.logger.info("NotificationTemplateService initialized")
    
    async def initialize(self):
        """Initialize the template service with default templates."""
        try:
            # Load default templates
            await self._load_default_templates()
            
            # Load custom templates from cache
            await self._load_custom_templates()
            
            self.logger.info("NotificationTemplateService initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NotificationTemplateService: {str(e)}")
            raise
    
    async def _load_default_templates(self):
        """Load default notification templates."""
        try:
            default_templates = [
                # Price Alert Templates
                NotificationTemplate(
                    id="price_alert_en",
                    name="Price Alert Template",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Price Alert: {symbol}",
                    message_template="{symbol} has moved by {change_pct:.2f}% to ${current_price:.2f}",
                    variables=["symbol", "change_pct", "current_price"]
                ),
                NotificationTemplate(
                    id="price_alert_ko",
                    name="가격 알림 템플릿",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="가격 알림: {symbol}",
                    message_template="{symbol}이 {change_pct:.2f}% 변동하여 ${current_price:.2f}이 되었습니다",
                    variables=["symbol", "change_pct", "current_price"]
                ),
                
                # Sentiment Alert Templates
                NotificationTemplate(
                    id="sentiment_alert_en",
                    name="Sentiment Alert Template",
                    type=TemplateType.SENTIMENT_ALERT,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Sentiment Alert: {symbol}",
                    message_template="{symbol} is showing {sentiment_type} sentiment ({sentiment_score:.2f})",
                    variables=["symbol", "sentiment_type", "sentiment_score"]
                ),
                NotificationTemplate(
                    id="sentiment_alert_ko",
                    name="감성 알림 템플릿",
                    type=TemplateType.SENTIMENT_ALERT,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="감성 알림: {symbol}",
                    message_template="{symbol}이 {sentiment_type} 감성을 보입니다 ({sentiment_score:.2f})",
                    variables=["symbol", "sentiment_type", "sentiment_score"]
                ),
                
                # Trending Alert Templates
                NotificationTemplate(
                    id="trending_alert_en",
                    name="Trending Alert Template",
                    type=TemplateType.TRENDING_ALERT,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Trending Alert: {symbol}",
                    message_template="{symbol} is now trending with score {trend_score:.1f}",
                    variables=["symbol", "trend_score"]
                ),
                NotificationTemplate(
                    id="trending_alert_ko",
                    name="트렌드 알림 템플릿",
                    type=TemplateType.TRENDING_ALERT,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="트렌드 알림: {symbol}",
                    message_template="{symbol}이 점수 {trend_score:.1f}로 트렌드 중입니다",
                    variables=["symbol", "trend_score"]
                ),
                
                # Volume Spike Templates
                NotificationTemplate(
                    id="volume_spike_en",
                    name="Volume Spike Template",
                    type=TemplateType.VOLUME_SPIKE,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Volume Spike: {symbol}",
                    message_template="{symbol} volume is {volume_ratio:.1f}x average ({spike_intensity} spike)",
                    variables=["symbol", "volume_ratio", "spike_intensity"]
                ),
                NotificationTemplate(
                    id="volume_spike_ko",
                    name="거래량 급증 템플릿",
                    type=TemplateType.VOLUME_SPIKE,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="거래량 급증: {symbol}",
                    message_template="{symbol} 거래량이 평균의 {volume_ratio:.1f}배입니다 ({spike_intensity} 급증)",
                    variables=["symbol", "volume_ratio", "spike_intensity"]
                ),
                
                # Market Event Templates
                NotificationTemplate(
                    id="market_event_en",
                    name="Market Event Template",
                    type=TemplateType.MARKET_EVENT,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Market Event: {market_change:+.2f}%",
                    message_template="Market moved by {market_change:+.2f}%",
                    variables=["market_change"]
                ),
                NotificationTemplate(
                    id="market_event_ko",
                    name="시장 이벤트 템플릿",
                    type=TemplateType.MARKET_EVENT,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="시장 이벤트: {market_change:+.2f}%",
                    message_template="시장이 {market_change:+.2f}% 변동했습니다",
                    variables=["market_change"]
                ),
                
                # System Notification Templates
                NotificationTemplate(
                    id="system_notification_en",
                    name="System Notification Template",
                    type=TemplateType.SYSTEM_NOTIFICATION,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="System Notification",
                    message_template="{message}",
                    variables=["message"]
                ),
                NotificationTemplate(
                    id="system_notification_ko",
                    name="시스템 알림 템플릿",
                    type=TemplateType.SYSTEM_NOTIFICATION,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="시스템 알림",
                    message_template="{message}",
                    variables=["message"]
                ),
                
                # Welcome Templates
                NotificationTemplate(
                    id="welcome_en",
                    name="Welcome Template",
                    type=TemplateType.WELCOME,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Welcome to InsiteChart",
                    message_template="You are now connected to real-time notifications",
                    variables=[]
                ),
                NotificationTemplate(
                    id="welcome_ko",
                    name="환영 템플릿",
                    type=TemplateType.WELCOME,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="InsiteChart에 오신 것을 환영합니다",
                    message_template="실시간 알림에 연결되었습니다",
                    variables=[]
                ),

                # Japanese Templates
                NotificationTemplate(
                    id="price_alert_ja",
                    name="価格アラートテンプレート",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.JAPANESE,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="価格アラート: {symbol}",
                    message_template="{symbol}が{change_pct:.2f}%変動して${current_price:.2f}になりました",
                    variables=["symbol", "change_pct", "current_price"]
                ),
                NotificationTemplate(
                    id="sentiment_alert_ja",
                    name="センチメントアラートテンプレート",
                    type=TemplateType.SENTIMENT_ALERT,
                    language=TemplateLanguage.JAPANESE,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="センチメントアラート: {symbol}",
                    message_template="{symbol}は{sentiment_type}センチメント({sentiment_score:.2f})を示しています",
                    variables=["symbol", "sentiment_type", "sentiment_score"]
                ),

                # Chinese Templates
                NotificationTemplate(
                    id="price_alert_zh",
                    name="价格警报模板",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.CHINESE,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="价格警报: {symbol}",
                    message_template="{symbol}已变动{change_pct:.2f}%至${current_price:.2f}",
                    variables=["symbol", "change_pct", "current_price"]
                ),
                NotificationTemplate(
                    id="sentiment_alert_zh",
                    name="情感警报模板",
                    type=TemplateType.SENTIMENT_ALERT,
                    language=TemplateLanguage.CHINESE,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="情感警报: {symbol}",
                    message_template="{symbol}显示{sentiment_type}情感({sentiment_score:.2f})",
                    variables=["symbol", "sentiment_type", "sentiment_score"]
                ),

                # Spanish Templates
                NotificationTemplate(
                    id="price_alert_es",
                    name="Plantilla de Alerta de Precio",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.SPANISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Alerta de Precio: {symbol}",
                    message_template="{symbol} ha cambiado {change_pct:.2f}% a ${current_price:.2f}",
                    variables=["symbol", "change_pct", "current_price"]
                ),

                # French Templates
                NotificationTemplate(
                    id="price_alert_fr",
                    name="Modèle d'Alerte de Prix",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.FRENCH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Alerte de Prix: {symbol}",
                    message_template="{symbol} a changé de {change_pct:.2f}% à ${current_price:.2f}",
                    variables=["symbol", "change_pct", "current_price"]
                ),

                # German Templates
                NotificationTemplate(
                    id="price_alert_de",
                    name="Preisalert-Vorlage",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.GERMAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Preisalert: {symbol}",
                    message_template="{symbol} hat sich um {change_pct:.2f}% auf ${current_price:.2f} geändert",
                    variables=["symbol", "change_pct", "current_price"]
                ),

                # Portuguese Templates
                NotificationTemplate(
                    id="price_alert_pt",
                    name="Modelo de Alerta de Preço",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.PORTUGUESE,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Alerta de Preço: {symbol}",
                    message_template="{symbol} mudou {change_pct:.2f}% para ${current_price:.2f}",
                    variables=["symbol", "change_pct", "current_price"]
                ),

                # Russian Templates
                NotificationTemplate(
                    id="price_alert_ru",
                    name="Шаблон Ценового Оповещения",
                    type=TemplateType.PRICE_ALERT,
                    language=TemplateLanguage.RUSSIAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Ценовое оповещение: {symbol}",
                    message_template="{symbol} изменился на {change_pct:.2f}% до ${current_price:.2f}",
                    variables=["symbol", "change_pct", "current_price"]
                ),

                # Error Templates for all languages
                NotificationTemplate(
                    id="error_en",
                    name="Error Template",
                    type=TemplateType.ERROR,
                    language=TemplateLanguage.ENGLISH,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="Error",
                    message_template="An error occurred: {error_message}",
                    variables=["error_message"]
                ),
                NotificationTemplate(
                    id="error_ko",
                    name="오류 템플릿",
                    type=TemplateType.ERROR,
                    language=TemplateLanguage.KOREAN,
                    channel=NotificationChannel.WEBSOCKET,
                    title_template="오류",
                    message_template="오류가 발생했습니다: {error_message}",
                    variables=["error_message"]
                )
            ]
            
            # Store templates
            for template in default_templates:
                self.templates[template.id] = template
            
            self.logger.info(f"Loaded {len(default_templates)} default templates")
            
        except Exception as e:
            self.logger.error(f"Error loading default templates: {str(e)}")
    
    async def _load_custom_templates(self):
        """Load custom templates from cache."""
        try:
            # Get custom templates from cache
            cached_templates = await self.cache_manager.get("custom_notification_templates")
            
            if cached_templates:
                for template_data in cached_templates:
                    template = NotificationTemplate(
                        id=template_data["id"],
                        type=TemplateType(template_data["type"]),
                        language=TemplateLanguage(template_data["language"]),
                        channel=NotificationChannel(template_data["channel"]),
                        title_template=template_data["title_template"],
                        message_template=template_data["message_template"],
                        variables=template_data.get("variables", []),
                        created_at=datetime.fromisoformat(template_data["created_at"]),
                        updated_at=datetime.fromisoformat(template_data["updated_at"]),
                        is_active=template_data.get("is_active", True),
                        priority=template_data.get("priority", 1)
                    )
                    self.templates[template.id] = template
                
                self.logger.info(f"Loaded {len(cached_templates)} custom templates")
            
        except Exception as e:
            self.logger.error(f"Error loading custom templates: {str(e)}")
    
    async def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        try:
            # Check cache first
            cache_key = f"template:{template_id}"
            cached_template = await self.cache_manager.get(cache_key)
            
            if cached_template:
                return NotificationTemplate(**cached_template)
            
            # Get from memory
            template = self.templates.get(template_id)
            
            if template:
                # Cache the template
                await self.cache_manager.set(
                    cache_key,
                    template.__dict__,
                    ttl=self.template_cache_ttl
                )
            
            return template
            
        except Exception as e:
            self.logger.error(f"Error getting template {template_id}: {str(e)}")
            return None
    
    async def get_best_template(
        self,
        template_type: TemplateType,
        language: TemplateLanguage,
        channel: NotificationChannel
    ) -> Optional[NotificationTemplate]:
        """Get best template for type, language, and channel."""
        try:
            # Filter templates by criteria
            matching_templates = [
                template for template in self.templates.values()
                if (template.type == template_type and
                    template.language == language and
                    template.channel == channel and
                    template.is_active)
            ]
            
            if not matching_templates:
                # Fallback to English if no matching template
                matching_templates = [
                    template for template in self.templates.values()
                    if (template.type == template_type and
                        template.language == TemplateLanguage.ENGLISH and
                        template.channel == channel and
                        template.is_active)
                ]
            
            if not matching_templates:
                return None
            
            # Sort by priority (lower number = higher priority)
            matching_templates.sort(key=lambda x: x.priority)
            
            return matching_templates[0]
            
        except Exception as e:
            self.logger.error(f"Error getting best template: {str(e)}")
            return None
    
    async def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> Optional[RenderedTemplate]:
        """Render template with variables."""
        try:
            # Get template
            template = await self.get_template(template_id)
            
            if not template:
                return None
            
            # Check cache first
            cache_key = f"rendered:{template_id}:{hash(str(sorted(variables.items())))}"
            cached_rendered = await self.cache_manager.get(cache_key)
            
            if cached_rendered:
                return RenderedTemplate(**cached_rendered)
            
            # Render template
            try:
                title = template.title_template.format(**variables)
                message = template.message_template.format(**variables)
            except KeyError as e:
                self.logger.error(f"Missing variable in template {template_id}: {str(e)}")
                return None
            
            rendered = RenderedTemplate(
                template_id=template_id,
                title=title,
                message=message,
                language=template.language,
                variables=variables
            )
            
            # Cache rendered template
            await self.cache_manager.set(
                cache_key,
                rendered.__dict__,
                ttl=self.rendered_cache_ttl
            )
            
            return rendered
            
        except Exception as e:
            self.logger.error(f"Error rendering template {template_id}: {str(e)}")
            return None
    
    async def create_template(self, template: NotificationTemplate) -> bool:
        """Create a new template."""
        try:
            # Validate template
            if not await self._validate_template(template):
                return False
            
            # Add to storage
            self.templates[template.id] = template
            
            # Cache the template
            cache_key = f"template:{template.id}"
            await self.cache_manager.set(
                cache_key,
                template.__dict__,
                ttl=self.template_cache_ttl
            )
            
            # Update custom templates cache
            await self._update_custom_templates_cache()
            
            self.logger.info(f"Created template: {template.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating template: {str(e)}")
            return False
    
    async def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing template."""
        try:
            template = self.templates.get(template_id)
            
            if not template:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            # Update timestamp
            template.updated_at = datetime.utcnow()
            
            # Cache the updated template
            cache_key = f"template:{template_id}"
            await self.cache_manager.set(
                cache_key,
                template.__dict__,
                ttl=self.template_cache_ttl
            )
            
            # Update custom templates cache
            await self._update_custom_templates_cache()
            
            self.logger.info(f"Updated template: {template_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating template {template_id}: {str(e)}")
            return False
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        try:
            if template_id not in self.templates:
                return False
            
            # Remove from storage
            del self.templates[template_id]
            
            # Remove from cache
            cache_key = f"template:{template_id}"
            await self.cache_manager.delete(cache_key)
            
            # Update custom templates cache
            await self._update_custom_templates_cache()
            
            self.logger.info(f"Deleted template: {template_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting template {template_id}: {str(e)}")
            return False
    
    async def list_templates(
        self,
        template_type: Optional[TemplateType] = None,
        language: Optional[TemplateLanguage] = None,
        channel: Optional[NotificationChannel] = None,
        active_only: bool = True
    ) -> List[NotificationTemplate]:
        """List templates with optional filters."""
        try:
            templates = list(self.templates.values())
            
            # Apply filters
            if template_type:
                templates = [t for t in templates if t.type == template_type]
            
            if language:
                templates = [t for t in templates if t.language == language]
            
            if channel:
                templates = [t for t in templates if t.channel == channel]
            
            if active_only:
                templates = [t for t in templates if t.is_active]
            
            # Sort by priority and type
            templates.sort(key=lambda x: (x.type.value, x.priority))
            
            return templates
            
        except Exception as e:
            self.logger.error(f"Error listing templates: {str(e)}")
            return []
    
    async def _validate_template(self, template: NotificationTemplate) -> bool:
        """Validate template structure and content."""
        try:
            # Check required fields
            if not template.id or not template.title_template or not template.message_template:
                return False
            
            # Check template syntax
            try:
                template.title_template.format(**{var: "" for var in template.variables})
                template.message_template.format(**{var: "" for var in template.variables})
            except KeyError:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Template validation error: {str(e)}")
            return False
    
    async def _update_custom_templates_cache(self):
        """Update custom templates cache."""
        try:
            # Get custom templates (non-default)
            custom_templates = [
                template.__dict__ for template in self.templates.values()
                if not template.id.startswith(("price_alert_", "sentiment_alert_", "trending_alert_", 
                                       "volume_spike_", "market_event_", "system_notification_", "welcome_"))
            ]
            
            # Update cache
            await self.cache_manager.set(
                "custom_notification_templates",
                custom_templates,
                ttl=self.template_cache_ttl
            )
            
        except Exception as e:
            self.logger.error(f"Error updating custom templates cache: {str(e)}")
    
    async def get_template_stats(self) -> Dict[str, Any]:
        """Get template statistics."""
        try:
            templates = list(self.templates.values())
            
            # Calculate statistics
            total_templates = len(templates)
            active_templates = len([t for t in templates if t.is_active])
            
            # Group by type
            type_counts = {}
            for template in templates:
                type_counts[template.type.value] = type_counts.get(template.type.value, 0) + 1
            
            # Group by language
            language_counts = {}
            for template in templates:
                language_counts[template.language.value] = language_counts.get(template.language.value, 0) + 1
            
            # Group by channel
            channel_counts = {}
            for template in templates:
                channel_counts[template.channel.value] = channel_counts.get(template.channel.value, 0) + 1
            
            return {
                "total_templates": total_templates,
                "active_templates": active_templates,
                "inactive_templates": total_templates - active_templates,
                "type_distribution": type_counts,
                "language_distribution": language_counts,
                "channel_distribution": channel_counts,
                "last_updated": max((t.updated_at for t in templates), default=datetime.utcnow()).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting template stats: {str(e)}")
            return {}