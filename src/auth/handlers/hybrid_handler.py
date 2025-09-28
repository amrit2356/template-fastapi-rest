"""
Hybrid authentication handler combining JWT and API Key authentication.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request

from .jwt_handler import JWTHandler
from .api_key_handler import APIKeyHandler
from ..models import SecurityContext, AuthType, SecurityLevel


class HybridHandler:
    """
    Hybrid authentication handler that supports both JWT and API Key authentication.
    Tries JWT first, then falls back to API Key if JWT is not available.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize hybrid handler with configuration.
        
        Args:
            config: Security configuration dictionary
        """
        self.jwt_handler = JWTHandler(config)
        self.api_key_handler = APIKeyHandler(config)
        self.prefer_jwt = config.get("prefer_jwt", True)
    
    def authenticate_request(self, request: Request) -> SecurityContext:
        """
        Authenticate a request using hybrid method (JWT or API Key).
        
        Args:
            request: FastAPI request object
            
        Returns:
            SecurityContext object with authentication information
            
        Raises:
            HTTPException: If authentication fails
        """
        # Try JWT authentication first if preferred
        if self.prefer_jwt:
            try:
                return self.jwt_handler.authenticate_request(request)
            except HTTPException as jwt_error:
                # If JWT fails, try API Key
                try:
                    return self.api_key_handler.authenticate_request(request)
                except HTTPException:
                    # Both failed, return the JWT error as it's more descriptive
                    raise jwt_error
        else:
            # Try API Key first
            try:
                return self.api_key_handler.authenticate_request(request)
            except HTTPException as api_error:
                # If API Key fails, try JWT
                try:
                    return self.jwt_handler.authenticate_request(request)
                except HTTPException:
                    # Both failed, return the API Key error
                    raise api_error
    
    def get_available_auth_methods(self, request: Request) -> Dict[str, bool]:
        """
        Check which authentication methods are available in the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary indicating which auth methods are available
        """
        jwt_token = self.jwt_handler.extract_token_from_request(request)
        api_key = self.api_key_handler.extract_api_key_from_request(request)
        
        return {
            "jwt_available": jwt_token is not None,
            "api_key_available": api_key is not None,
            "jwt_token": jwt_token is not None,
            "api_key": api_key is not None
        }
    
    def create_jwt_token(
        self, 
        user_id: str, 
        username: str, 
        roles: list = None, 
        permissions: list = None,
        additional_claims: Dict[str, Any] = None
    ) -> str:
        """
        Create a JWT access token (delegates to JWT handler).
        
        Args:
            user_id: User identifier
            username: Username
            roles: List of user roles
            permissions: List of user permissions
            additional_claims: Additional claims to include
            
        Returns:
            JWT access token string
        """
        return self.jwt_handler.create_access_token(
            user_id, username, roles, permissions, additional_claims
        )
    
    def create_refresh_token(self, user_id: str, username: str) -> str:
        """
        Create a JWT refresh token (delegates to JWT handler).
        
        Args:
            user_id: User identifier
            username: Username
            
        Returns:
            JWT refresh token string
        """
        return self.jwt_handler.create_refresh_token(user_id, username)
    
    def create_api_key(
        self,
        name: str,
        user_id: Optional[str] = None,
        permissions: list = None,
        rate_limit: Optional[int] = None,
        expires_at: Optional[Any] = None
    ) -> tuple[str, Any]:
        """
        Create an API key (delegates to API Key handler).
        
        Args:
            name: Name/description for the API key
            user_id: Associated user ID
            permissions: List of permissions
            rate_limit: Rate limit per minute
            expires_at: Expiration datetime
            
        Returns:
            Tuple of (api_key, api_key_data)
        """
        return self.api_key_handler.create_api_key(
            name, user_id, permissions, rate_limit, expires_at
        )
    
    def verify_jwt_token(self, token: str):
        """
        Verify a JWT token (delegates to JWT handler).
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object with decoded token information
        """
        return self.jwt_handler.verify_token(token)
    
    def validate_api_key(self, api_key: str):
        """
        Validate an API key (delegates to API Key handler).
        
        Args:
            api_key: API key string to validate
            
        Returns:
            APIKeyData if valid, None if invalid
        """
        return self.api_key_handler.validate_api_key(api_key)
    
    def get_jwt_handler(self) -> JWTHandler:
        """
        Get the JWT handler instance.
        
        Returns:
            JWTHandler instance
        """
        return self.jwt_handler
    
    def get_api_key_handler(self) -> APIKeyHandler:
        """
        Get the API Key handler instance.
        
        Returns:
            APIKeyHandler instance
        """
        return self.api_key_handler
    
    def list_api_keys(self, user_id: Optional[str] = None):
        """
        List API keys (delegates to API Key handler).
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of API key data objects
        """
        return self.api_key_handler.list_api_keys(user_id)
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key (delegates to API Key handler).
        
        Args:
            key_id: API key ID to revoke
            
        Returns:
            True if revoked successfully, False if not found
        """
        return self.api_key_handler.revoke_api_key(key_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get combined statistics from both handlers.
        
        Returns:
            Dictionary with combined statistics
        """
        api_key_stats = self.api_key_handler.get_stats()
        
        return {
            "auth_methods": ["jwt", "api_key"],
            "prefer_jwt": self.prefer_jwt,
            "api_key_stats": api_key_stats,
            "jwt_available": True,
            "api_key_available": True
        }
