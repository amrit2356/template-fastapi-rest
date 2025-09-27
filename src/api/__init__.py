"""
API module for the FastAPI REST API Template
"""

from .routes import router, root_router, get_dynamic_endpoints
from .handlers import GenericHandler, get_generic_handler
from .models import (
    BaseResponse,
    HealthCheckResponse,
    GenericRequest,
    ItemResponse,
    FileUploadRequest,
    FileUploadResponse,
    ErrorDetail,
    HealthStatus
)

__all__ = [
    "router",
    "root_router",
    "get_dynamic_endpoints",
    "GenericHandler", 
    "get_generic_handler",
    "BaseResponse",
    "HealthCheckResponse",
    "GenericRequest",
    "ItemResponse",
    "FileUploadRequest",
    "FileUploadResponse",
    "ErrorDetail",
    "HealthStatus"
]
