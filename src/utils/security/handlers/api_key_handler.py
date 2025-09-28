"""
API Key authentication handler.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Request

from ..models import APIKeyData, SecurityContext, AuthType, SecurityLevel


class APIKeyHandler:
    """
    API Key authentication handler.
    Handles API key generation, validation, and user context extraction.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize API Key handler with configuration.
        
        Args:
            config: Security configuration dictionary
        """
        self.api_key_header = config.get("api_key_header", "X-API-Key")
        self.api_key_query_param = config.get("api_key_query_param", "api_key")
        self.api_key_length = config.get("api_key_length", 32)
        
        # In-memory storage for API keys (in production, use a database)
        self._api_keys: Dict[str, APIKeyData] = {}
        self._key_hashes: Dict[str, str] = {}  # hash -> key_id mapping
    
    def generate_api_key(self) -> str:
        """
        Generate a new API key.
        
        Returns:
            Generated API key string
        """
        return secrets.token_urlsafe(self.api_key_length)
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Args:
            api_key: API key string
            
        Returns:
            Hashed API key string
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def create_api_key(
        self,
        name: str,
        user_id: Optional[str] = None,
        permissions: List[str] = None,
        rate_limit: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> tuple[str, APIKeyData]:
        """
        Create a new API key.
        
        Args:
            name: Name/description for the API key
            user_id: Associated user ID
            permissions: List of permissions
            rate_limit: Rate limit per minute
            expires_at: Expiration datetime
            
        Returns:
            Tuple of (api_key, api_key_data)
        """
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        key_id = secrets.token_urlsafe(16)
        
        api_key_data = APIKeyData(
            key_id=key_id,
            name=name,
            user_id=user_id,
            permissions=permissions or [],
            rate_limit=rate_limit,
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Store the API key data and hash mapping
        self._api_keys[key_id] = api_key_data
        self._key_hashes[key_hash] = key_id
        
        return api_key, api_key_data
    
    def validate_api_key(self, api_key: str) -> Optional[APIKeyData]:
        """
        Validate an API key and return its data.
        
        Args:
            api_key: API key string to validate
            
        Returns:
            APIKeyData if valid, None if invalid
        """
        if not api_key:
            return None
        
        key_hash = self.hash_api_key(api_key)
        key_id = self._key_hashes.get(key_hash)
        
        if not key_id:
            return None
        
        api_key_data = self._api_keys.get(key_id)
        if not api_key_data:
            return None
        
        # Check if key is active
        if not api_key_data.is_active:
            return None
        
        # Check if key has expired
        if api_key_data.expires_at and api_key_data.expires_at < datetime.utcnow():
            return None
        
        # Update last used timestamp
        api_key_data.last_used = datetime.utcnow()
        
        return api_key_data
    
    def extract_api_key_from_request(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers or query parameters.
        
        Args:
            request: FastAPI request object
            
        Returns:
            API key string or None if not found
        """
        # Check header first
        api_key = request.headers.get(self.api_key_header)
        if api_key:
            return api_key
        
        # Check query parameter
        api_key = request.query_params.get(self.api_key_query_param)
        if api_key:
            return api_key
        
        return None
    
    def authenticate_request(self, request: Request) -> SecurityContext:
        """
        Authenticate a request using API key.
        
        Args:
            request: FastAPI request object
            
        Returns:
            SecurityContext object with authentication information
            
        Raises:
            HTTPException: If authentication fails
        """
        api_key = self.extract_api_key_from_request(request)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing API key. Provide it via {self.api_key_header} header or {self.api_key_query_param} query parameter"
            )
        
        api_key_data = self.validate_api_key(api_key)
        if not api_key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key"
            )
        
        return SecurityContext(
            user_id=api_key_data.user_id,
            username=api_key_data.name,  # Use API key name as username
            auth_type=AuthType.API_KEY,
            security_level=SecurityLevel.PROTECTED,
            permissions=api_key_data.permissions,
            roles=["api_key_user"],
            is_authenticated=True,
            is_authorized=True,
            request_id=request.headers.get("X-Request-ID"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent")
        )
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key by setting it as inactive.
        
        Args:
            key_id: API key ID to revoke
            
        Returns:
            True if revoked successfully, False if not found
        """
        if key_id in self._api_keys:
            self._api_keys[key_id].is_active = False
            return True
        return False
    
    def list_api_keys(self, user_id: Optional[str] = None) -> List[APIKeyData]:
        """
        List API keys, optionally filtered by user ID.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of API key data objects
        """
        keys = list(self._api_keys.values())
        
        if user_id:
            keys = [key for key in keys if key.user_id == user_id]
        
        return keys
    
    def get_api_key(self, key_id: str) -> Optional[APIKeyData]:
        """
        Get API key data by key ID.
        
        Args:
            key_id: API key ID
            
        Returns:
            API key data or None if not found
        """
        return self._api_keys.get(key_id)
    
    def update_api_key(
        self, 
        key_id: str, 
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """
        Update API key properties.
        
        Args:
            key_id: API key ID
            name: New name
            permissions: New permissions
            rate_limit: New rate limit
            expires_at: New expiration date
            is_active: New active status
            
        Returns:
            True if updated successfully, False if not found
        """
        if key_id not in self._api_keys:
            return False
        
        api_key_data = self._api_keys[key_id]
        
        if name is not None:
            api_key_data.name = name
        if permissions is not None:
            api_key_data.permissions = permissions
        if rate_limit is not None:
            api_key_data.rate_limit = rate_limit
        if expires_at is not None:
            api_key_data.expires_at = expires_at
        if is_active is not None:
            api_key_data.is_active = is_active
        
        return True
    
    def cleanup_expired_keys(self) -> int:
        """
        Remove expired API keys from storage.
        
        Returns:
            Number of keys removed
        """
        now = datetime.utcnow()
        expired_keys = []
        
        for key_id, api_key_data in self._api_keys.items():
            if api_key_data.expires_at and api_key_data.expires_at < now:
                expired_keys.append(key_id)
        
        for key_id in expired_keys:
            del self._api_keys[key_id]
            # Remove from hash mapping
            for hash_key, stored_key_id in list(self._key_hashes.items()):
                if stored_key_id == key_id:
                    del self._key_hashes[hash_key]
                    break
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get API key statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_keys = len(self._api_keys)
        active_keys = sum(1 for key in self._api_keys.values() if key.is_active)
        expired_keys = sum(
            1 for key in self._api_keys.values() 
            if key.expires_at and key.expires_at < datetime.utcnow()
        )
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "inactive_keys": total_keys - active_keys
        }
