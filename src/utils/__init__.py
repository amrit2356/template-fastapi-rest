"""
Utilities module for the FastAPI REST API Template
"""

from .config.settings import settings
from .resources.logger import logger

__all__ = ["settings", "logger"]
