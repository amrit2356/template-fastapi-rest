"""
API module for the FastAPI REST API Template
"""

from .routes import router, get_dynamic_endpoints
from .handlers import GenericHandler, get_generic_handler
from .models import (
    BaseResponse,
    HealthResponse,
    ProcessRequest,
    ProcessResponse,
    ProcessStatusResponse,
    FileUploadResponse,
    ErrorResponse,
    ProcessState,
    ProcessType
)

__all__ = [
    "router",
    "get_dynamic_endpoints",
    "GenericHandler", 
    "get_generic_handler",
    "BaseResponse",
    "HealthResponse",
    "ProcessRequest",
    "ProcessResponse", 
    "ProcessStatusResponse",
    "FileUploadResponse",
    "ErrorResponse",
    "ProcessState",
    "ProcessType"
]
