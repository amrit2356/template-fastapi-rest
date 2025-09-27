# /src/api/handlers.py

import os
import time
import uuid
from fastapi import Request, HTTPException, UploadFile
from pathlib import Path
from typing import Optional, Dict, Any

from ..core.managers import get_server_manager, get_process_manager
from .models import (
    GenericRequest, ItemResponse, HealthStatus, FileUploadRequest, FileUploadResponse
)
from ..services.services import GenericService
from ..utils.resources.logger import logger
from ..utils.config.settings import settings

class GenericHandler:
    """Simplified handler for core operations."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name

    def _generate_session_id(self) -> str:
        """Generate a unique session ID for tracking requests."""
        return str(uuid.uuid4())

    def _get_service(self, request: Request) -> GenericService:
        """Retrieves the service instance from the application state."""
        try:
            server_manager = get_server_manager(request)
            service = server_manager.get_service(self.service_name)
            if not service:
                raise HTTPException(
                    status_code=503, 
                    detail=f"{self.service_name} service is not available."
                )
            if hasattr(service, 'is_initialized') and not service.is_initialized:
                raise HTTPException(
                    status_code=503, 
                    detail=f"{self.service_name} service is not initialized."
                )
            
            # Ensure the service has access to process manager
            if isinstance(service, GenericService) and not service.process_manager:
                process_manager = get_process_manager(request)
                service.set_process_manager(process_manager)
            
            return service
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve {self.service_name} service: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Could not access the {self.service_name} service."
            )

    # --- Core Operations ---

    async def create_item(self, request_data: GenericRequest, request: Request) -> ItemResponse:
        """Create a new item."""
        session_id = self._generate_session_id()
        logger.info(f"Session {session_id}: Creating new item")
        
        service = self._get_service(request)
        
        try:
            result = await service.create_item(request_data.data, request_data.project_id)
            
            if result:
                logger.info(f"Session {session_id}: Item created successfully")
                return ItemResponse(
                    session_id=session_id,
                    status="success",
                    message="Item created successfully",
                    data=result
                )
            else:
                logger.error(f"Session {session_id}: Failed to create item")
                raise HTTPException(status_code=500, detail="Failed to create item")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session {session_id}: Error creating item: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_item(self, item_id: str, request: Request) -> ItemResponse:
        """Get a single item by ID."""
        session_id = self._generate_session_id()
        logger.info(f"Session {session_id}: Getting item with ID: {item_id}")
        
        service = self._get_service(request)
        
        try:
            result = await service.get_item(item_id)
            
            if result:
                logger.info(f"Session {session_id}: Item retrieved successfully")
                return ItemResponse(
                    session_id=session_id,
                    status="success",
                    message="Item retrieved successfully",
                    data=result
                )
            else:
                logger.error(f"Session {session_id}: Item not found")
                raise HTTPException(status_code=404, detail="Item not found")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session {session_id}: Error getting item: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def update_item(self, item_id: str, request_data: GenericRequest, 
                         request: Request) -> ItemResponse:
        """Update an existing item."""
        session_id = self._generate_session_id()
        logger.info(f"Session {session_id}: Updating item with ID: {item_id}")
        
        service = self._get_service(request)
        
        try:
            result = await service.update_item(item_id, request_data.data)
            
            if result:
                logger.info(f"Session {session_id}: Item updated successfully")
                return ItemResponse(
                    session_id=session_id,
                    status="success",
                    message="Item updated successfully",
                    data=result
                )
            else:
                logger.error(f"Session {session_id}: Item not found or update failed")
                raise HTTPException(status_code=404, detail="Item not found or update failed")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session {session_id}: Error updating item: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def delete_item(self, item_id: str, request: Request) -> Dict[str, Any]:
        """Delete an item by ID."""
        session_id = self._generate_session_id()
        logger.info(f"Session {session_id}: Deleting item with ID: {item_id}")
        
        service = self._get_service(request)
        
        try:
            success = await service.delete_item(item_id)
            
            if success:
                logger.info(f"Session {session_id}: Item deleted successfully")
                return {
                    "session_id": session_id,
                    "status": "success",
                    "message": "Item deleted successfully",
                    "deleted_id": item_id
                }
            else:
                logger.error(f"Session {session_id}: Item not found or delete failed")
                raise HTTPException(status_code=404, detail="Item not found or delete failed")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Session {session_id}: Error deleting item: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def upload_file(self, file: UploadFile, request_data: FileUploadRequest, 
                         request: Request) -> FileUploadResponse:
        """Upload a file and save it locally."""
        session_id = self._generate_session_id()
        logger.info(f"Session {session_id}: Uploading file: {file.filename}")
        
        try:
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Save to local directory
            upload_dir = settings.get("server_manager.directories.uploads", "runtime/uploads")
            os.makedirs(upload_dir, exist_ok=True)
            
            # Use custom filename or generate one
            if request_data.filename:
                filename = request_data.filename
            else:
                file_extension = Path(file.filename).suffix if file.filename else ""
                file_id = f"file_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                filename = f"{file_id}{file_extension}"
            
            file_path = os.path.join(upload_dir, filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Process file through service
            service = self._get_service(request)
            file_data = await service.process_file(file_path, request_data.project_id, filename)
            
            logger.info(f"Session {session_id}: File uploaded and processed successfully")
            return FileUploadResponse(
                session_id=session_id,
                status="success",
                message="File uploaded and processed successfully",
                file_id=file_data["id"],
                file_size=file_size,
                file_path=file_path
            )
                
        except Exception as e:
            logger.error(f"Session {session_id}: Error uploading file: {e}")
            raise HTTPException(status_code=500, detail="File upload failed")

# Dependency Injection factory
def get_generic_handler(service_name: str) -> GenericHandler:
    """Factory function to create a generic handler for a specific service."""
    return GenericHandler(service_name)