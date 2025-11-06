"""
Frontend package for InsiteChart platform.

This package contains all frontend components and utilities.
"""

from .api_client import InsiteChartAPIClient, get_api_client
from .utils import (
    format_currency,
    format_number,
    format_large_number,
    format_percentage,
    create_metric_card,
    create_sentiment_indicator,
    create_stock_chart,
    create_comparison_chart,
    display_stock_summary,
    create_data_table,
    create_download_button
)

__all__ = [
    "InsiteChartAPIClient",
    "get_api_client",
    "format_currency",
    "format_number",
    "format_large_number",
    "format_percentage",
    "create_metric_card",
    "create_sentiment_indicator",
    "create_stock_chart",
    "create_comparison_chart",
    "display_stock_summary",
    "create_data_table",
    "create_download_button"
]