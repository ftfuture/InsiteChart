"""
API package for InsiteChart platform.

This package contains all API routes and related functionality.
"""

from .routes import router as api_router

__all__ = ["api_router"]