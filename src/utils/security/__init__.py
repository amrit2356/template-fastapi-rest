"""
Security module for FastAPI applications.

This module provides a comprehensive security system that can be easily configured
via config.yaml and integrated into FastAPI applications without writing additional code.

Features:
- JWT Bearer token authentication
- API Key authentication  
- Hybrid authentication (JWT + API Key)
- Auto-protection middleware
- Rate limiting
- Configurable security levels
- Easy enable/disable via configuration

Usage:
    from src.utils.security import SecurityManager
    
    # Initialize security manager
    security = SecurityManager()
    
    # Add middleware to FastAPI app
    app.add_middleware(security.get_middleware())
    
    # Or use individual components
    auth_handler = security.get_auth_handler()
    security_context = auth_handler.authenticate_request(request)
"""

from typing import Dict, Any, Optional, List
from .models import (
    SecurityConfig, 
    AuthType, 
    SecurityLevel, 
    SecurityContext,
    TokenData,
    APIKeyData,
    AuthRequest,
    AuthResponse,
    APIKeyRequest,
    APIKeyResponse,
    SecurityError,
    SecurityMetrics,
    SecurityEvent
)
from .auth_factory import AuthFactory
from .middleware import SecurityMiddleware, create_security_middleware
from .handlers import JWTHandler, APIKeyHandler, HybridHandler


class SecurityManager:
    """
    Main security manager class that provides a unified interface for all security features.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize security manager.
        
        Args:
            config: Security configuration dictionary. If None, will be loaded from settings.
        """
        self.config = config or {}
        self.auth_handler = None
        self.middleware_class = None
        self._initialized = False
        
        if self.config:
            self._initialize()
    
    def _initialize(self):
        """Initialize security components based on configuration."""
        if self._initialized:
            return
        
        try:
            # Create auth handler if security is enabled
            if self.config.get("enabled", True):
                self.auth_handler = AuthFactory.create_handler(self.config)
            
            # Create middleware class
            self.middleware_class = create_security_middleware(self.config)
            
            self._initialized = True
            
        except Exception as e:
            print(f"⚠️ Failed to initialize security manager: {e}")
            self._initialized = False
    
    def get_auth_handler(self):
        """
        Get the authentication handler.
        
        Returns:
            Authentication handler instance or None if disabled
        """
        if not self._initialized:
            self._initialize()
        return self.auth_handler
    
    def get_middleware(self):
        """
        Get the security middleware class.
        
        Returns:
            SecurityMiddleware class
        """
        if not self._initialized:
            self._initialize()
        return self.middleware_class
    
    def is_enabled(self) -> bool:
        """
        Check if security is enabled.
        
        Returns:
            True if security is enabled, False otherwise
        """
        return self.config.get("enabled", True) and self._initialized
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current security configuration.
        
        Returns:
            Security configuration dictionary
        """
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update security configuration and reinitialize.
        
        Args:
            new_config: New security configuration
        """
        self.config.update(new_config)
        self._initialized = False
        self._initialize()
    
    def create_jwt_token(
        self, 
        user_id: str, 
        username: str, 
        roles: list = None, 
        permissions: list = None,
        additional_claims: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Create a JWT access token.
        
        Args:
            user_id: User identifier
            username: Username
            roles: List of user roles
            permissions: List of user permissions
            additional_claims: Additional claims to include
            
        Returns:
            JWT access token string or None if not available
        """
        if not self.auth_handler:
            return None
        
        if hasattr(self.auth_handler, 'create_access_token'):
            return self.auth_handler.create_access_token(
                user_id, username, roles, permissions, additional_claims
            )
        elif hasattr(self.auth_handler, 'create_jwt_token'):
            return self.auth_handler.create_jwt_token(
                user_id, username, roles, permissions, additional_claims
            )
        
        return None
    
    def create_refresh_token(self, user_id: str, username: str) -> Optional[str]:
        """
        Create a JWT refresh token.
        
        Args:
            user_id: User identifier
            username: Username
            
        Returns:
            JWT refresh token string or None if not available
        """
        if not self.auth_handler:
            return None
        
        if hasattr(self.auth_handler, 'create_refresh_token'):
            return self.auth_handler.create_refresh_token(user_id, username)
        
        return None
    
    def create_api_key(
        self,
        name: str,
        user_id: Optional[str] = None,
        permissions: list = None,
        rate_limit: Optional[int] = None,
        expires_at: Optional[Any] = None
    ) -> Optional[tuple[str, Any]]:
        """
        Create an API key.
        
        Args:
            name: Name/description for the API key
            user_id: Associated user ID
            permissions: List of permissions
            rate_limit: Rate limit per minute
            expires_at: Expiration datetime
            
        Returns:
            Tuple of (api_key, api_key_data) or None if not available
        """
        if not self.auth_handler:
            return None
        
        if hasattr(self.auth_handler, 'create_api_key'):
            return self.auth_handler.create_api_key(
                name, user_id, permissions, rate_limit, expires_at
            )
        elif hasattr(self.auth_handler, 'get_api_key_handler'):
            # For hybrid handler, get the API key handler
            api_key_handler = self.auth_handler.get_api_key_handler()
            if api_key_handler and hasattr(api_key_handler, 'create_api_key'):
                return api_key_handler.create_api_key(
                    name, user_id, permissions, rate_limit, expires_at
                )
        
        return None
    
    def list_api_keys(self, user_id: Optional[str] = None) -> List[Any]:
        """
        List API keys.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of API key data objects
        """
        if not self.auth_handler:
            return []
        
        if hasattr(self.auth_handler, 'list_api_keys'):
            return self.auth_handler.list_api_keys(user_id)
        
        return []
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: API key ID to revoke
            
        Returns:
            True if revoked successfully, False otherwise
        """
        if not self.auth_handler:
            return False
        
        if hasattr(self.auth_handler, 'revoke_api_key'):
            return self.auth_handler.revoke_api_key(key_id)
        
        return False
    
    def get_cors_config(self) -> Dict[str, Any]:
        """
        Get CORS configuration from security settings.
        
        Returns:
            Dictionary with CORS configuration
        """
        return {
            "allow_origins": self.config.get("cors_allow_origins", ["http://localhost:3000"]),
            "allow_credentials": self.config.get("cors_allow_credentials", True),
            "allow_methods": self.config.get("cors_allow_methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
            "allow_headers": self.config.get("cors_allow_headers", ["*"]),
            "expose_headers": self.config.get("cors_allow_headers", ["*"])  # Use same as allow_headers
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get security statistics.
        
        Returns:
            Dictionary with security statistics
        """
        if not self.auth_handler:
            return {"enabled": False}
        
        stats = {
            "enabled": self.is_enabled(),
            "auth_type": self.config.get("auth_type", "none"),
            "rate_limit_enabled": self.config.get("rate_limit_enabled", False)
        }
        
        if hasattr(self.auth_handler, 'get_stats'):
            handler_stats = self.auth_handler.get_stats()
            stats.update(handler_stats)
        
        return stats


# Convenience functions for easy integration
def create_security_manager(config: Optional[Dict[str, Any]] = None) -> SecurityManager:
    """
    Create a security manager instance.
    
    Args:
        config: Security configuration dictionary
        
    Returns:
        SecurityManager instance
    """
    return SecurityManager(config)


def get_security_config_from_settings() -> Dict[str, Any]:
    """
    Get security configuration from settings manager.
    
    Returns:
        Security configuration dictionary
    """
    try:
        from ..config.settings import settings
        return settings.get("security", {})
    except ImportError:
        return {}


def create_security_manager_from_settings() -> SecurityManager:
    """
    Create a security manager using configuration from settings.
    
    Returns:
        SecurityManager instance
    """
    config = get_security_config_from_settings()
    return SecurityManager(config)


# Export main classes and functions
__all__ = [
    # Main classes
    "SecurityManager",
    "SecurityConfig",
    "SecurityMiddleware",
    
    # Models
    "AuthType",
    "SecurityLevel", 
    "SecurityContext",
    "TokenData",
    "APIKeyData",
    "AuthRequest",
    "AuthResponse",
    "APIKeyRequest",
    "APIKeyResponse",
    "SecurityError",
    "SecurityMetrics",
    "SecurityEvent",
    
    # Handlers
    "JWTHandler",
    "APIKeyHandler", 
    "HybridHandler",
    
    # Factory and utilities
    "AuthFactory",
    "create_security_middleware",
    "create_security_manager",
    "get_security_config_from_settings",
    "create_security_manager_from_settings"
]