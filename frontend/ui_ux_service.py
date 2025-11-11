"""
UI/UX Service for InsiteChart platform.

This service provides enhanced UI/UX features including
responsive design, accessibility, theme management,
and user experience optimization.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import asyncio

from .api_client import APIClient
from .i18n import I18nClient

# Configure logging
logger = logging.getLogger(__name__)

class Theme(Enum):
    """Available themes."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    HIGH_CONTRAST = "high_contrast"
    SEPIA = "sepia"

class ColorScheme(Enum):
    """Color schemes for accessibility."""
    DEFAULT = "default"
    PROTANOPIA = "protanopia"
    DEUTERANOPIA = "deuteranopia"
    TRITANOPIA = "tritanopia"
    ACHROMATOPSIA = "achromatopsia"

class FontSize(Enum):
    """Font size options."""
    EXTRA_SMALL = "xs"
    SMALL = "sm"
    MEDIUM = "md"
    LARGE = "lg"
    EXTRA_LARGE = "xl"
    EXTRA_EXTRA_LARGE = "2xl"

class AnimationSpeed(Enum):
    """Animation speed options."""
    NONE = "none"
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"

class LayoutDensity(Enum):
    """Layout density options."""
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"

class UIUXService:
    """
    UI/UX service for managing user interface and experience features.
    """
    
    def __init__(self, api_client: APIClient, i18n_client: I18nClient):
        """
        Initialize UI/UX service.
        
        Args:
            api_client: API client instance
            i18n_client: Internationalization client instance
        """
        self.api_client = api_client
        self.i18n_client = i18n_client
        self.current_theme = Theme.LIGHT
        self.current_color_scheme = ColorScheme.DEFAULT
        self.current_font_size = FontSize.MEDIUM
        self.current_animation_speed = AnimationSpeed.NORMAL
        self.current_layout_density = LayoutDensity.COMFORTABLE
        
        # UI state
        self.sidebar_collapsed = False
        self.notifications_enabled = True
        self.sound_enabled = True
        self.vibration_enabled = False
        
        # Accessibility settings
        self.screen_reader_enabled = False
        self.keyboard_navigation = True
        self.focus_visible = True
        self.reduce_motion = False
        
        # Custom CSS variables
        self.css_variables = {}
        
        # Event listeners
        self.event_listeners = {}
        
        # Initialize service
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize UI/UX service."""
        try:
            logger.info("Initializing UI/UX service...")
            
            # Load user preferences
            self._load_user_preferences()
            
            # Apply initial theme
            self._apply_theme()
            
            # Setup event listeners
            self._setup_event_listeners()
            
            # Initialize CSS variables
            self._initialize_css_variables()
            
            logger.info("UI/UX service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize UI/UX service: {str(e)}")
    
    async def set_theme(self, theme: Theme) -> bool:
        """
        Set the current theme.
        
        Args:
            theme: Theme to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.current_theme = theme
            await self._apply_theme()
            await self._save_user_preferences()
            
            # Emit theme change event
            await self._emit_event("theme_changed", {"theme": theme.value})
            
            logger.info(f"Theme set to: {theme.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set theme: {str(e)}")
            return False
    
    async def _apply_theme(self):
        """Apply the current theme to the UI."""
        try:
            # Remove existing theme classes
            for theme in Theme:
                self._remove_css_class(f"theme-{theme.value}")
            
            # Add new theme class
            self._add_css_class(f"theme-{self.current_theme.value}")
            
            # Update CSS variables
            theme_variables = self._get_theme_variables()
            self._update_css_variables(theme_variables)
            
            # Apply color scheme
            await self._apply_color_scheme()
            
        except Exception as e:
            logger.error(f"Failed to apply theme: {str(e)}")
    
    def _get_theme_variables(self) -> Dict[str, str]:
        """Get CSS variables for the current theme."""
        theme_variables = {
            Theme.LIGHT: {
                "--bg-primary": "#ffffff",
                "--bg-secondary": "#f8f9fa",
                "--bg-tertiary": "#e9ecef",
                "--text-primary": "#212529",
                "--text-secondary": "#6c757d",
                "--text-tertiary": "#adb5bd",
                "--border-primary": "#dee2e6",
                "--border-secondary": "#ced4da",
                "--accent-primary": "#007bff",
                "--accent-secondary": "#6c757d",
                "--success": "#28a745",
                "--warning": "#ffc107",
                "--error": "#dc3545",
                "--info": "#17a2b8"
            },
            Theme.DARK: {
                "--bg-primary": "#1a1a1a",
                "--bg-secondary": "#2d2d2d",
                "--bg-tertiary": "#404040",
                "--text-primary": "#ffffff",
                "--text-secondary": "#b3b3b3",
                "--text-tertiary": "#808080",
                "--border-primary": "#404040",
                "--border-secondary": "#595959",
                "--accent-primary": "#0d6efd",
                "--accent-secondary": "#6c757d",
                "--success": "#198754",
                "--warning": "#ffc107",
                "--error": "#dc3545",
                "--info": "#0dcaf0"
            },
            Theme.HIGH_CONTRAST: {
                "--bg-primary": "#000000",
                "--bg-secondary": "#1a1a1a",
                "--bg-tertiary": "#333333",
                "--text-primary": "#ffffff",
                "--text-secondary": "#cccccc",
                "--text-tertiary": "#999999",
                "--border-primary": "#ffffff",
                "--border-secondary": "#cccccc",
                "--accent-primary": "#ffff00",
                "--accent-secondary": "#00ffff",
                "--success": "#00ff00",
                "--warning": "#ffff00",
                "--error": "#ff0000",
                "--info": "#00ffff"
            },
            Theme.SEPIA: {
                "--bg-primary": "#f4f1ea",
                "--bg-secondary": "#e8e2d5",
                "--bg-tertiary": "#dcd3c0",
                "--text-primary": "#5c4b37",
                "--text-secondary": "#8b7355",
                "--text-tertiary": "#a68b6d",
                "--border-primary": "#dcd3c0",
                "--border-secondary": "#c9bfa8",
                "--accent-primary": "#8b4513",
                "--accent-secondary": "#a0522d",
                "--success": "#6b8e23",
                "--warning": "#cd853f",
                "--error": "#8b4513",
                "--info": "#4682b4"
            }
        }
        
        return theme_variables.get(self.current_theme, theme_variables[Theme.LIGHT])
    
    async def set_color_scheme(self, color_scheme: ColorScheme) -> bool:
        """
        Set the color scheme for accessibility.
        
        Args:
            color_scheme: Color scheme to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.current_color_scheme = color_scheme
            await self._apply_color_scheme()
            await self._save_user_preferences()
            
            # Emit color scheme change event
            await self._emit_event("color_scheme_changed", {"color_scheme": color_scheme.value})
            
            logger.info(f"Color scheme set to: {color_scheme.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set color scheme: {str(e)}")
            return False
    
    async def _apply_color_scheme(self):
        """Apply the current color scheme."""
        try:
            # Remove existing color scheme classes
            for scheme in ColorScheme:
                self._remove_css_class(f"color-scheme-{scheme.value}")
            
            # Add new color scheme class
            self._add_css_class(f"color-scheme-{self.current_color_scheme.value}")
            
            # Apply color scheme specific filters
            if self.current_color_scheme != ColorScheme.DEFAULT:
                filter_styles = self._get_color_scheme_filters()
                self._apply_css_filters(filter_styles)
            else:
                self._remove_css_filters()
            
        except Exception as e:
            logger.error(f"Failed to apply color scheme: {str(e)}")
    
    def _get_color_scheme_filters(self) -> str:
        """Get CSS filters for color scheme."""
        filters = {
            ColorScheme.PROTANOPIA: "url(#protanopia-filter)",
            ColorScheme.DEUTERANOPIA: "url(#deuteranopia-filter)",
            ColorScheme.TRITANOPIA: "url(#tritanopia-filter)",
            ColorScheme.ACHROMATOPSIA: "grayscale(100%)"
        }
        
        return filters.get(self.current_color_scheme, "")
    
    async def set_font_size(self, font_size: FontSize) -> bool:
        """
        Set the font size.
        
        Args:
            font_size: Font size to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.current_font_size = font_size
            await self._apply_font_size()
            await self._save_user_preferences()
            
            # Emit font size change event
            await self._emit_event("font_size_changed", {"font_size": font_size.value})
            
            logger.info(f"Font size set to: {font_size.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set font size: {str(e)}")
            return False
    
    async def _apply_font_size(self):
        """Apply the current font size."""
        try:
            # Remove existing font size classes
            for size in FontSize:
                self._remove_css_class(f"font-size-{size.value}")
            
            # Add new font size class
            self._add_css_class(f"font-size-{self.current_font_size.value}")
            
            # Update root font size
            font_sizes = {
                FontSize.EXTRA_SMALL: "12px",
                FontSize.SMALL: "14px",
                FontSize.MEDIUM: "16px",
                FontSize.LARGE: "18px",
                FontSize.EXTRA_LARGE: "20px",
                FontSize.EXTRA_EXTRA_LARGE: "22px"
            }
            
            root_font_size = font_sizes.get(self.current_font_size, "16px")
            self._set_css_variable("--root-font-size", root_font_size)
            
        except Exception as e:
            logger.error(f"Failed to apply font size: {str(e)}")
    
    async def set_animation_speed(self, speed: AnimationSpeed) -> bool:
        """
        Set the animation speed.
        
        Args:
            speed: Animation speed to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.current_animation_speed = speed
            await self._apply_animation_speed()
            await self._save_user_preferences()
            
            # Emit animation speed change event
            await self._emit_event("animation_speed_changed", {"speed": speed.value})
            
            logger.info(f"Animation speed set to: {speed.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set animation speed: {str(e)}")
            return False
    
    async def _apply_animation_speed(self):
        """Apply the current animation speed."""
        try:
            # Remove existing animation speed classes
            for speed in AnimationSpeed:
                self._remove_css_class(f"animation-speed-{speed.value}")
            
            # Add new animation speed class
            self._add_css_class(f"animation-speed-{self.current_animation_speed.value}")
            
            # Update animation duration variables
            animation_durations = {
                AnimationSpeed.NONE: "0ms",
                AnimationSpeed.SLOW: "500ms",
                AnimationSpeed.NORMAL: "300ms",
                AnimationSpeed.FAST: "150ms"
            }
            
            duration = animation_durations.get(self.current_animation_speed, "300ms")
            self._set_css_variable("--animation-duration", duration)
            
        except Exception as e:
            logger.error(f"Failed to apply animation speed: {str(e)}")
    
    async def set_layout_density(self, density: LayoutDensity) -> bool:
        """
        Set the layout density.
        
        Args:
            density: Layout density to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.current_layout_density = density
            await self._apply_layout_density()
            await self._save_user_preferences()
            
            # Emit layout density change event
            await self._emit_event("layout_density_changed", {"density": density.value})
            
            logger.info(f"Layout density set to: {density.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set layout density: {str(e)}")
            return False
    
    async def _apply_layout_density(self):
        """Apply the current layout density."""
        try:
            # Remove existing layout density classes
            for density in LayoutDensity:
                self._remove_css_class(f"layout-density-{density.value}")
            
            # Add new layout density class
            self._add_css_class(f"layout-density-{self.current_layout_density.value}")
            
            # Update spacing variables
            spacing_values = {
                LayoutDensity.COMPACT: {
                    "--spacing-xs": "2px",
                    "--spacing-sm": "4px",
                    "--spacing-md": "8px",
                    "--spacing-lg": "12px",
                    "--spacing-xl": "16px"
                },
                LayoutDensity.COMFORTABLE: {
                    "--spacing-xs": "4px",
                    "--spacing-sm": "8px",
                    "--spacing-md": "12px",
                    "--spacing-lg": "16px",
                    "--spacing-xl": "20px"
                },
                LayoutDensity.SPACIOUS: {
                    "--spacing-xs": "8px",
                    "--spacing-sm": "12px",
                    "--spacing-md": "16px",
                    "--spacing-lg": "20px",
                    "--spacing-xl": "24px"
                }
            }
            
            spacing = spacing_values.get(self.current_layout_density, spacing_values[LayoutDensity.COMFORTABLE])
            for variable, value in spacing.items():
                self._set_css_variable(variable, value)
            
        except Exception as e:
            logger.error(f"Failed to apply layout density: {str(e)}")
    
    async def toggle_sidebar(self) -> bool:
        """
        Toggle sidebar visibility.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.sidebar_collapsed = not self.sidebar_collapsed
            
            if self.sidebar_collapsed:
                self._add_css_class("sidebar-collapsed")
            else:
                self._remove_css_class("sidebar-collapsed")
            
            await self._save_user_preferences()
            
            # Emit sidebar toggle event
            await self._emit_event("sidebar_toggled", {"collapsed": self.sidebar_collapsed})
            
            logger.info(f"Sidebar toggled: {'collapsed' if self.sidebar_collapsed else 'expanded'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to toggle sidebar: {str(e)}")
            return False
    
    async def set_accessibility_option(self, option: str, enabled: bool) -> bool:
        """
        Set accessibility option.
        
        Args:
            option: Accessibility option name
            enabled: Whether the option is enabled
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update accessibility setting
            if option == "screen_reader":
                self.screen_reader_enabled = enabled
                self._update_screen_reader(enabled)
            elif option == "keyboard_navigation":
                self.keyboard_navigation = enabled
                self._update_keyboard_navigation(enabled)
            elif option == "focus_visible":
                self.focus_visible = enabled
                self._update_focus_visible(enabled)
            elif option == "reduce_motion":
                self.reduce_motion = enabled
                self._update_reduce_motion(enabled)
            
            await self._save_user_preferences()
            
            # Emit accessibility change event
            await self._emit_event("accessibility_changed", {"option": option, "enabled": enabled})
            
            logger.info(f"Accessibility option '{option}' set to: {enabled}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set accessibility option: {str(e)}")
            return False
    
    def _update_screen_reader(self, enabled: bool):
        """Update screen reader settings."""
        if enabled:
            self._add_css_class("screen-reader-enabled")
            self._add_aria_labels()
        else:
            self._remove_css_class("screen-reader-enabled")
    
    def _update_keyboard_navigation(self, enabled: bool):
        """Update keyboard navigation settings."""
        if enabled:
            self._add_css_class("keyboard-navigation-enabled")
            self._add_keyboard_shortcuts()
        else:
            self._remove_css_class("keyboard-navigation-enabled")
    
    def _update_focus_visible(self, enabled: bool):
        """Update focus visible settings."""
        if enabled:
            self._add_css_class("focus-visible-enabled")
        else:
            self._remove_css_class("focus-visible-enabled")
    
    def _update_reduce_motion(self, enabled: bool):
        """Update reduce motion settings."""
        if enabled:
            self._add_css_class("reduce-motion-enabled")
            self._set_css_variable("--animation-duration", "0ms")
        else:
            self._remove_css_class("reduce-motion-enabled")
            # Apply current animation speed synchronously
            animation_durations = {
                AnimationSpeed.NONE: "0ms",
                AnimationSpeed.SLOW: "500ms",
                AnimationSpeed.NORMAL: "300ms",
                AnimationSpeed.FAST: "150ms"
            }
            duration = animation_durations.get(self.current_animation_speed, "300ms")
            self._set_css_variable("--animation-duration", duration)
    
    def _load_user_preferences(self):
        """Load user preferences from storage."""
        try:
            # This would load from local storage or API
            # For now, use default values
            pass
        except Exception as e:
            logger.error(f"Failed to load user preferences: {str(e)}")
    
    async def _save_user_preferences(self):
        """Save user preferences to storage."""
        try:
            preferences = {
                "theme": self.current_theme.value,
                "color_scheme": self.current_color_scheme.value,
                "font_size": self.current_font_size.value,
                "animation_speed": self.current_animation_speed.value,
                "layout_density": self.current_layout_density.value,
                "sidebar_collapsed": self.sidebar_collapsed,
                "notifications_enabled": self.notifications_enabled,
                "sound_enabled": self.sound_enabled,
                "vibration_enabled": self.vibration_enabled,
                "screen_reader_enabled": self.screen_reader_enabled,
                "keyboard_navigation": self.keyboard_navigation,
                "focus_visible": self.focus_visible,
                "reduce_motion": self.reduce_motion
            }
            
            # Save to local storage or API
            await self.api_client.post("/api/v1/user/preferences", preferences)
            
        except Exception as e:
            logger.error(f"Failed to save user preferences: {str(e)}")
    
    def _setup_event_listeners(self):
        """Setup event listeners for UI changes."""
        try:
            # Listen for system theme changes
            if hasattr(window, 'matchMedia'):
                dark_mode_query = window.matchMedia('(prefers-color-scheme: dark)')
                dark_mode_query.addListener(self._handle_system_theme_change)
            
            # Listen for system font size changes
            if hasattr(window, 'matchMedia'):
                font_size_query = window.matchMedia('(prefers-reduced-data: reduce)')
                font_size_query.addListener(self._handle_system_font_size_change)
            
        except Exception as e:
            logger.error(f"Failed to setup event listeners: {str(e)}")
    
    def _handle_system_theme_change(self, event):
        """Handle system theme change."""
        try:
            if self.current_theme == Theme.AUTO:
                if event.matches:
                    # Dark mode preferred
                    self._apply_theme_variables(Theme.DARK)
                else:
                    # Light mode preferred
                    self._apply_theme_variables(Theme.LIGHT)
        except Exception as e:
            logger.error(f"Failed to handle system theme change: {str(e)}")
    
    def _initialize_css_variables(self):
        """Initialize CSS variables."""
        try:
            # Set initial CSS variables
            self._update_css_variables(self._get_theme_variables())
            
            # Initialize accessibility variables
            self._set_css_variable("--focus-outline-width", "2px")
            self._set_css_variable("--focus-outline-color", "#007bff")
            self._set_css_variable("--border-radius", "4px")
            self._set_css_variable("--box-shadow", "0 2px 4px rgba(0, 0, 0, 0.1)")
            
        except Exception as e:
            logger.error(f"Failed to initialize CSS variables: {str(e)}")
    
    def _add_css_class(self, class_name: str):
        """Add CSS class to body element."""
        try:
            document.body.classList.add(class_name)
        except Exception as e:
            logger.error(f"Failed to add CSS class: {str(e)}")
    
    def _remove_css_class(self, class_name: str):
        """Remove CSS class from body element."""
        try:
            document.body.classList.remove(class_name)
        except Exception as e:
            logger.error(f"Failed to remove CSS class: {str(e)}")
    
    def _set_css_variable(self, variable: str, value: str):
        """Set CSS variable value."""
        try:
            document.documentElement.style.setProperty(variable, value)
            self.css_variables[variable] = value
        except Exception as e:
            logger.error(f"Failed to set CSS variable: {str(e)}")
    
    def _update_css_variables(self, variables: Dict[str, str]):
        """Update multiple CSS variables."""
        try:
            for variable, value in variables.items():
                self._set_css_variable(variable, value)
        except Exception as e:
            logger.error(f"Failed to update CSS variables: {str(e)}")
    
    async def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """Emit UI event."""
        try:
            if event_name in self.event_listeners:
                for listener in self.event_listeners[event_name]:
                    await listener(data)
        except Exception as e:
            logger.error(f"Failed to emit event: {str(e)}")
    
    def add_event_listener(self, event_name: str, callback):
        """Add event listener."""
        try:
            if event_name not in self.event_listeners:
                self.event_listeners[event_name] = []
            self.event_listeners[event_name].append(callback)
        except Exception as e:
            logger.error(f"Failed to add event listener: {str(e)}")
    
    def remove_event_listener(self, event_name: str, callback):
        """Remove event listener."""
        try:
            if event_name in self.event_listeners:
                self.event_listeners[event_name].remove(callback)
        except Exception as e:
            logger.error(f"Failed to remove event listener: {str(e)}")
    
    async def get_ui_preferences(self) -> Dict[str, Any]:
        """
        Get current UI preferences.
        
        Returns:
            Dictionary of current UI preferences
        """
        try:
            return {
                "theme": self.current_theme.value,
                "color_scheme": self.current_color_scheme.value,
                "font_size": self.current_font_size.value,
                "animation_speed": self.current_animation_speed.value,
                "layout_density": self.current_layout_density.value,
                "sidebar_collapsed": self.sidebar_collapsed,
                "notifications_enabled": self.notifications_enabled,
                "sound_enabled": self.sound_enabled,
                "vibration_enabled": self.vibration_enabled,
                "screen_reader_enabled": self.screen_reader_enabled,
                "keyboard_navigation": self.keyboard_navigation,
                "focus_visible": self.focus_visible,
                "reduce_motion": self.reduce_motion,
                "css_variables": self.css_variables
            }
        except Exception as e:
            logger.error(f"Failed to get UI preferences: {str(e)}")
            return {}
    
    async def reset_to_defaults(self) -> bool:
        """
        Reset all UI settings to defaults.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Reset all settings to defaults
            self.current_theme = Theme.LIGHT
            self.current_color_scheme = ColorScheme.DEFAULT
            self.current_font_size = FontSize.MEDIUM
            self.current_animation_speed = AnimationSpeed.NORMAL
            self.current_layout_density = LayoutDensity.COMFORTABLE
            self.sidebar_collapsed = False
            self.notifications_enabled = True
            self.sound_enabled = True
            self.vibration_enabled = False
            self.screen_reader_enabled = False
            self.keyboard_navigation = True
            self.focus_visible = True
            self.reduce_motion = False
            
            # Apply all changes
            await self._apply_theme()
            await self._apply_font_size()
            await self._apply_animation_speed()
            await self._apply_layout_density()
            
            # Save preferences
            await self._save_user_preferences()
            
            # Emit reset event
            await self._emit_event("ui_reset", {})
            
            logger.info("UI settings reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset UI settings: {str(e)}")
            return False