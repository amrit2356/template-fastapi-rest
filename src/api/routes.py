# /src/api/routes.py

import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from src.api.handlers import GenericHandler, get_generic_handler
from src.api.models import (
    ErrorDetail, 
    GenericRequest, 
    ItemResponse,
    HealthCheckResponse,
    FileUploadRequest,
    FileUploadResponse
)
from src.utils.config.settings import settings
from src.utils.resources.logger import logger

# Initialize router
router = APIRouter(prefix=settings.get_api_prefix(), tags=settings.get_api_tags())

# Create upload directory
UPLOAD_DIR = Path(settings.get("server_manager.directories.uploads", "runtime/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- Core Production Endpoints ---

@router.get("/health", response_model=HealthCheckResponse, summary="Health Check")
async def health_check(request: Request):
    """
    Production health check endpoint.
    Returns service status and system information.
    """
    try:
        from src.core.managers import get_server_manager, get_process_manager
        
        server_mgr = get_server_manager(request)
        process_mgr = get_process_manager(request)
        
        # Get service statuses
        services_status = {}
        if server_mgr:
            services_status = {name: service.get_status() for name, service in server_mgr.services.items()}
        
        # Determine overall health
        overall_status = "healthy"
        if not services_status or not all(s.get("initialized", False) for s in services_status.values()):
            overall_status = "unhealthy"
        
        return HealthCheckResponse(
            session_id=str(uuid.uuid4()),
            status=overall_status,
            service_name=settings.get("app.name", "FastAPI Service"),
            version=settings.get("app.version", "1.0.0"),
            services=services_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@router.post("/data", response_model=ItemResponse, summary="Create Data")
async def create_data(
    request_data: GenericRequest,
    request: Request,
    handler: GenericHandler = Depends(lambda: get_generic_handler("item_service"))
):
    """
    Create new data item.
    Production endpoint for data creation.
    """
    return await handler.create_item(request_data, request)

@router.get("/data/{item_id}", response_model=ItemResponse, summary="Get Data")
async def get_data(
    item_id: str,
    request: Request,
    handler: GenericHandler = Depends(lambda: get_generic_handler("item_service"))
):
    """
    Get data item by ID.
    Production endpoint for data retrieval.
    """
    return await handler.get_item(item_id, request)

@router.put("/data/{item_id}", response_model=ItemResponse, summary="Update Data")
async def update_data(
    item_id: str,
    request_data: GenericRequest,
    request: Request,
    handler: GenericHandler = Depends(lambda: get_generic_handler("item_service"))
):
    """
    Update existing data item.
    Production endpoint for data updates.
    """
    return await handler.update_item(item_id, request_data, request)

@router.delete("/data/{item_id}", summary="Delete Data")
async def delete_data(
    item_id: str,
    request: Request,
    handler: GenericHandler = Depends(lambda: get_generic_handler("item_service"))
):
    """
    Delete data item by ID.
    Production endpoint for data deletion.
    """
    return await handler.delete_item(item_id, request)

@router.post("/upload", response_model=FileUploadResponse, summary="Upload File")
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="File to upload"),
    project_id: str = Form(..., description="Project ID"),
    filename: Optional[str] = Form(default=None, description="Custom filename"),
    handler: GenericHandler = Depends(lambda: get_generic_handler("document_service"))
):
    """
    Upload file endpoint.
    Production endpoint for file uploads.
    """
    request_data = FileUploadRequest(
        project_id=project_id,
        filename=filename
    )
    return await handler.upload_file(file, request_data, request)

@router.get("/status", summary="System Status")
async def get_status(request: Request):
    """
    Get system status and metrics.
    Production endpoint for monitoring.
    """
    try:
        from src.core.managers import get_server_manager, get_process_manager
        
        server_mgr = get_server_manager(request)
        process_mgr = get_process_manager(request)
        
        return {
            "status": "operational",
            "timestamp": time.time(),
            "server": server_mgr.get_server_status() if server_mgr else None,
            "processes": process_mgr.get_metrics() if process_mgr else None,
            "services": {name: service.get_status() for name, service in server_mgr.services.items()} if server_mgr else {}
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")

# --- Utility Endpoints ---

@router.get("/info", summary="API Information")
async def get_api_info():
    """
    Get API information and available endpoints.
    """
    return {
        "name": settings.get("app.name", "FastAPI Service"),
        "version": settings.get("app.version", "1.0.0"),
        "description": "Production-ready API service",
        "endpoints": {
            "health": "GET /health - Service health check",
            "create": "POST /data - Create data item",
            "get": "GET /data/{id} - Get data item",
            "update": "PUT /data/{id} - Update data item", 
            "delete": "DELETE /data/{id} - Delete data item",
            "upload": "POST /upload - Upload file",
            "status": "GET /status - System status",
            "info": "GET /info - API information"
        }
    }


def get_dynamic_endpoints():
    """
    Dynamically extracts endpoint information from the FastAPI router.
    Returns a structured dictionary of all available endpoints.
    """
    endpoints = {}
    api_prefix = settings.get_api_prefix()
    
    # Get all routes from the API router
    for route in router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            # Extract route information
            path = route.path
            methods = list(route.methods - {'HEAD', 'OPTIONS'})  # Exclude HEAD and OPTIONS
            
            # Get route metadata
            summary = getattr(route, 'summary', None)
            description = getattr(route, 'description', None)
            
            # Extract endpoint name from path (remove prefix and convert to readable format)
            endpoint_name = path.replace(f'{api_prefix}/', '').replace('/', '_').replace('-', '_')
            
            # Categorize endpoints based on current structure
            if path.startswith(f'{api_prefix}/health'):
                category = 'health'
                endpoint_key = 'health_check'
            elif path.startswith(f'{api_prefix}/status'):
                category = 'monitoring'
                endpoint_key = 'status'
            elif path.startswith(f'{api_prefix}/info'):
                category = 'monitoring'
                endpoint_key = 'info'
            elif path.startswith(f'{api_prefix}/data'):
                category = 'data'
                endpoint_key = endpoint_name.replace('data_', '')
            elif path.startswith(f'{api_prefix}/upload'):
                category = 'files'
                endpoint_key = 'upload'
            else:
                category = 'other'
                endpoint_key = endpoint_name
            
            # Initialize category if it doesn't exist
            if category not in endpoints:
                endpoints[category] = {}
            
            # Add endpoint information
            endpoints[category][endpoint_key] = {
                "method": methods[0] if methods else "GET",  # Use first method if multiple
                "path": path,
                "description": description or f"{methods[0] if methods else 'GET'} {path}",
                "summary": summary or f"Endpoint for {path}"
            }
    
    return endpoints

