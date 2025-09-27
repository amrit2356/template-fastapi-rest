# /src/api/services.py

import os
import time
import uuid
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from ..core.server_manager import AIService, ServiceConfig
from ..core.process_manager import ProcessManager, ProcessData, ProcessState
from ..utils.resources.logger import logger
from ..utils.config.settings import settings


class GenericService(AIService):
    """
    Generic service that provides CRUD operations for any data type.
    This service can be extended or used as-is for basic data management.
    """
    
    def __init__(self, config: ServiceConfig, device: Optional[str] = None):
        super().__init__(config, device)
        self.data_store: Dict[str, Dict[str, Any]] = {}
        self.process_manager: Optional[ProcessManager] = None
    
    async def initialize(self) -> bool:
        """Initialize the generic service."""
        try:
            logger.info(f"Initializing {self.config.name}")
            
            # Initialize data store
            self.data_store = {}
            
            # Get process manager from config if available
            if hasattr(self, 'process_manager') and self.process_manager is None:
                # Process manager will be injected by server manager
                pass
            
            self.is_initialized = True
            logger.info(f"{self.config.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing {self.config.name}: {str(e)}", exc_info=True)
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the generic service."""
        try:
            logger.info(f"Shutting down {self.config.name}")
            self.is_shutting_down = True
            
            # Clean up data store if needed
            # In a real implementation, you might want to persist data here
            self.data_store.clear()
            
            logger.info(f"{self.config.name} shutdown complete")
            
        except Exception as e:
            logger.error(f"Error shutting down {self.config.name}: {str(e)}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status information."""
        return {
            "name": self.config.name,
            "initialized": self.is_initialized,
            "shutting_down": self.is_shutting_down,
            "data_count": len(self.data_store),
            "status": "healthy" if self.is_initialized and not self.is_shutting_down else "unhealthy"
        }
    
    def set_process_manager(self, process_manager: ProcessManager) -> None:
        """Set the process manager for this service."""
        self.process_manager = process_manager
    
    # --- CRUD Operations ---
    
    async def create_item(self, data: Dict[str, Any], project_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new item in the data store."""
        item_id = str(uuid.uuid4())
        
        # Add metadata
        item_data = {
            "id": item_id,
            "created_at": time.time(),
            "updated_at": time.time(),
            "project_id": project_id,
            **data
        }
        
        self.data_store[item_id] = item_data
        
        # Track process if process manager is available
        if self.process_manager:
            process_data = ProcessData(
                process_id=f"create_{item_id}",
                process_type="create_item",
                status=ProcessState.COMPLETED,
                metadata={
                    "service": self.config.name,
                    "item_id": item_id,
                    "project_id": project_id
                }
            )
            # Note: ProcessManager doesn't have add_process method, 
            # this would need to be implemented if process tracking is needed
            pass
        
        logger.info(f"Created item {item_id} in {self.config.name}")
        return item_data
    
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get an item by ID."""
        item = self.data_store.get(item_id)
        
        if item and self.process_manager:
            process_data = ProcessData(
                process_id=f"get_{item_id}",
                process_type="get_item",
                status=ProcessState.COMPLETED,
                metadata={
                    "service": self.config.name,
                    "item_id": item_id
                }
            )
            # Note: ProcessManager doesn't have add_process method, 
            # this would need to be implemented if process tracking is needed
            pass
        
        return item
    
    async def get_items(self, page: int = 1, page_size: int = 10, 
                       search: Optional[str] = None, sort_by: Optional[str] = None,
                       sort_order: str = "asc") -> Dict[str, Any]:
        """Get a list of items with pagination and filtering."""
        items = list(self.data_store.values())
        
        # Apply search filter
        if search:
            items = [
                item for item in items 
                if any(str(value).lower().find(search.lower()) != -1 
                      for value in item.values() if isinstance(value, str))
            ]
        
        # Apply sorting
        if sort_by and items:
            reverse = sort_order.lower() == "desc"
            try:
                items.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
            except (TypeError, KeyError):
                # If sorting fails, keep original order
                pass
        
        # Apply pagination
        total_count = len(items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = items[start_idx:end_idx]
        
        # Track process if process manager is available
        if self.process_manager:
            process_data = ProcessData(
                process_id=f"list_{uuid.uuid4().hex[:8]}",
                process_type="list_items",
                status=ProcessState.COMPLETED,
                metadata={
                    "service": self.config.name,
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "search": search
                }
            )
            # Note: ProcessManager doesn't have add_process method, 
            # this would need to be implemented if process tracking is needed
            pass
        
        return {
            "items": paginated_items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    
    async def update_item(self, item_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing item."""
        if item_id not in self.data_store:
            return None
        
        # Update the item
        self.data_store[item_id].update(data)
        self.data_store[item_id]["updated_at"] = time.time()
        
        # Track process if process manager is available
        if self.process_manager:
            process_data = ProcessData(
                process_id=f"update_{item_id}",
                process_type="update_item",
                status=ProcessState.COMPLETED,
                metadata={
                    "service": self.config.name,
                    "item_id": item_id
                }
            )
            # Note: ProcessManager doesn't have add_process method, 
            # this would need to be implemented if process tracking is needed
            pass
        
        logger.info(f"Updated item {item_id} in {self.config.name}")
        return self.data_store[item_id]
    
    async def delete_item(self, item_id: str) -> bool:
        """Delete an item by ID."""
        if item_id not in self.data_store:
            return False
        
        del self.data_store[item_id]
        
        # Track process if process manager is available
        if self.process_manager:
            process_data = ProcessData(
                process_id=f"delete_{item_id}",
                process_type="delete_item",
                status=ProcessState.COMPLETED,
                metadata={
                    "service": self.config.name,
                    "item_id": item_id
                }
            )
            # Note: ProcessManager doesn't have add_process method, 
            # this would need to be implemented if process tracking is needed
            pass
        
        logger.info(f"Deleted item {item_id} from {self.config.name}")
        return True
    
    async def process_file(self, file_path: str, project_id: str, 
                          filename: Optional[str] = None) -> Dict[str, Any]:
        """Process an uploaded file."""
        file_id = f"file_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Get file info
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Create file record
        file_data = {
            "id": file_id,
            "filename": filename or os.path.basename(file_path),
            "file_path": file_path,
            "file_size": file_size,
            "project_id": project_id,
            "created_at": time.time(),
            "status": "processed"
        }
        
        # Store file record
        self.data_store[file_id] = file_data
        
        # Track process if process manager is available
        if self.process_manager:
            process_data = ProcessData(
                process_id=f"process_file_{file_id}",
                process_type="process_file",
                status=ProcessState.COMPLETED,
                metadata={
                    "service": self.config.name,
                    "file_id": file_id,
                    "project_id": project_id,
                    "file_size": file_size
                },
                files=[file_path]
            )
            # Note: ProcessManager doesn't have add_process method, 
            # this would need to be implemented if process tracking is needed
            pass
        
        logger.info(f"Processed file {file_id} in {self.config.name}")
        return file_data


# Simplified - no service registry needed since we use server manager directly
