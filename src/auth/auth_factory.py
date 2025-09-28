"""
Authentication factory for creating auth handlers based on configuration.
"""

from typing import Dict, Any, Optional
from .models import AuthType, SecurityConfig
from .handlers import JWTHandler, APIKeyHandler, HybridHandler


class AuthFactory:
    """
    Factory class for creating authentication handlers based on configuration.
    """
    
    @staticmethod
    def create_handler(config: Dict[str, Any]) -> Any:
        """
        Create an authentication handler based on the configuration.
        
        Args:
            config: Security configuration dictionary
            
        Returns:
            Authentication handler instance
            
        Raises:
            ValueError: If auth_type is not supported
        """
        auth_type = config.get("auth_type", AuthType.JWT)
        
        if isinstance(auth_type, str):
            auth_type = AuthType(auth_type)
        
        if auth_type == AuthType.JWT:
            return JWTHandler(config)
        elif auth_type == AuthType.API_KEY:
            return APIKeyHandler(config)
        elif auth_type == AuthType.HYBRID:
            return HybridHandler(config)
        elif auth_type == AuthType.NONE:
            return None
        else:
            raise ValueError(f"Unsupported authentication type: {auth_type}")
    
    @staticmethod
    def create_handler_from_security_config(security_config: SecurityConfig) -> Any:
        """
        Create an authentication handler from a SecurityConfig object.
        
        Args:
            security_config: SecurityConfig object
            
        Returns:
            Authentication handler instance
        """
        config_dict = security_config.dict()
        return AuthFactory.create_handler(config_dict)
    
    @staticmethod
    def get_supported_auth_types() -> list:
        """
        Get list of supported authentication types.
        
        Returns:
            List of supported AuthType values
        """
        return [AuthType.JWT, AuthType.API_KEY, AuthType.HYBRID, AuthType.NONE]
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        Validate authentication configuration.
        
        Args:
            config: Security configuration dictionary
            
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            auth_type = config.get("auth_type", AuthType.JWT)
            
            if isinstance(auth_type, str):
                auth_type = AuthType(auth_type)
            
            # Validate required fields based on auth type
            if auth_type == AuthType.JWT:
                if not config.get("jwt_secret_key"):
                    return False
            elif auth_type == AuthType.API_KEY:
                # API Key doesn't require additional config validation
                pass
            elif auth_type == AuthType.HYBRID:
                if not config.get("jwt_secret_key"):
                    return False
            elif auth_type == AuthType.NONE:
                # No validation needed for disabled auth
                pass
            else:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def get_default_config(auth_type: AuthType = AuthType.JWT) -> Dict[str, Any]:
        """
        Get default configuration for a specific authentication type.
        
        Args:
            auth_type: Authentication type
            
        Returns:
            Default configuration dictionary
        """
        base_config = {
            "enabled": True,
            "default_security_level": "protected",
            "password_min_length": 8,
            "password_require_uppercase": True,
            "password_require_lowercase": True,
            "password_require_numbers": True,
            "password_require_special_chars": True,
            "session_timeout_minutes": 30,
            "max_login_attempts": 5,
            "lockout_duration_minutes": 15,
            "rate_limit_enabled": True,
            "rate_limit_requests_per_minute": 60,
            "rate_limit_burst_size": 10,
            "cors_allow_origins": ["http://localhost:3000"],
            "cors_allow_credentials": True,
            "cors_allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "cors_allow_headers": ["*"],
            "excluded_paths": ["/docs", "/redoc", "/openapi.json", "/health", "/metrics"],
            "protected_paths": ["/api/v1"]
        }
        
        if auth_type == AuthType.JWT:
            base_config.update({
                "auth_type": AuthType.JWT,
                "jwt_secret_key": "your-secret-key-change-this-in-production",
                "jwt_algorithm": "HS256",
                "jwt_access_token_expire_minutes": 30,
                "jwt_refresh_token_expire_days": 7,
                "jwt_issuer": "fastapi-rest-template"
            })
        elif auth_type == AuthType.API_KEY:
            base_config.update({
                "auth_type": AuthType.API_KEY,
                "api_key_header": "X-API-Key",
                "api_key_query_param": "api_key",
                "api_key_length": 32
            })
        elif auth_type == AuthType.HYBRID:
            base_config.update({
                "auth_type": AuthType.HYBRID,
                "prefer_jwt": True,
                "jwt_secret_key": "your-secret-key-change-this-in-production",
                "jwt_algorithm": "HS256",
                "jwt_access_token_expire_minutes": 30,
                "jwt_refresh_token_expire_days": 7,
                "jwt_issuer": "fastapi-rest-template",
                "api_key_header": "X-API-Key",
                "api_key_query_param": "api_key",
                "api_key_length": 32
            })
        elif auth_type == AuthType.NONE:
            base_config.update({
                "auth_type": AuthType.NONE,
                "enabled": False
            })
        
        return base_config
