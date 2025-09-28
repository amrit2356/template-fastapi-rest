"""
Auto-protection middleware for FastAPI applications.
"""

import time
from typing import Optional, Dict, Any, List, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .models import SecurityContext, SecurityLevel, SecurityError, SecurityEvent
from .auth_factory import AuthFactory


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Auto-protection middleware that automatically secures endpoints based on configuration.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        security_config: Dict[str, Any],
        excluded_paths: Optional[List[str]] = None,
        protected_paths: Optional[List[str]] = None,
        custom_auth_check: Optional[Callable] = None
    ):
        """
        Initialize security middleware.
        
        Args:
            app: FastAPI application instance
            security_config: Security configuration dictionary
            excluded_paths: List of paths to exclude from authentication
            protected_paths: List of paths that require authentication
            custom_auth_check: Custom authentication check function
        """
        super().__init__(app)
        self.security_config = security_config
        self.enabled = security_config.get("enabled", True)
        self.excluded_paths = excluded_paths or security_config.get("excluded_paths", [])
        self.protected_paths = protected_paths or security_config.get("protected_paths", [])
        self.custom_auth_check = custom_auth_check
        
        # Create auth handler if security is enabled
        self.auth_handler = None
        if self.enabled:
            try:
                self.auth_handler = AuthFactory.create_handler(security_config)
            except Exception as e:
                print(f"⚠️ Failed to create auth handler: {e}")
                self.enabled = False
        
        # Rate limiting storage (in production, use Redis)
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.rate_limit_enabled = security_config.get("rate_limit_enabled", True)
        self.rate_limit_requests_per_minute = security_config.get("rate_limit_requests_per_minute", 60)
        self.rate_limit_burst_size = security_config.get("rate_limit_burst_size", 10)
    
    def is_path_excluded(self, path: str) -> bool:
        """
        Check if a path is excluded from authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if path is excluded, False otherwise
        """
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        return False
    
    def is_path_protected(self, path: str) -> bool:
        """
        Check if a path requires authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if path is protected, False otherwise
        """
        # If no protected paths specified, protect all non-excluded paths
        if not self.protected_paths:
            return not self.is_path_excluded(path)
        
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client (for rate limiting).
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client identifier string
        """
        # Try to get user ID from security context if available
        if hasattr(request.state, 'security_context') and request.state.security_context:
            return request.state.security_context.user_id or request.client.host
        return request.client.host if request.client else "unknown"
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if within rate limit, False if exceeded
        """
        if not self.rate_limit_enabled:
            return True
        
        now = time.time()
        minute_window = int(now // 60)
        
        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = {
                "requests": [],
                "burst_tokens": self.rate_limit_burst_size,
                "last_refill": now
            }
        
        client_data = self.rate_limits[client_id]
        
        # Refill burst tokens
        time_passed = now - client_data["last_refill"]
        tokens_to_add = int(time_passed * self.rate_limit_requests_per_minute / 60)
        client_data["burst_tokens"] = min(
            self.rate_limit_burst_size,
            client_data["burst_tokens"] + tokens_to_add
        )
        client_data["last_refill"] = now
        
        # Clean old requests (older than 1 minute)
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if now - req_time < 60
        ]
        
        # Check if we can make a request
        if len(client_data["requests"]) >= self.rate_limit_requests_per_minute:
            return False
        
        if client_data["burst_tokens"] <= 0:
            return False
        
        # Add current request
        client_data["requests"].append(now)
        client_data["burst_tokens"] -= 1
        
        return True
    
    def create_security_context(self, request: Request) -> SecurityContext:
        """
        Create security context for the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            SecurityContext object
        """
        if not self.enabled or not self.auth_handler:
            return SecurityContext(
                auth_type="none",
                security_level=SecurityLevel.PUBLIC,
                is_authenticated=False,
                is_authorized=True,  # Allow all when disabled
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
        
        try:
            return self.auth_handler.authenticate_request(request)
        except HTTPException:
            # Authentication failed, return unauthenticated context
            return SecurityContext(
                auth_type="none",
                security_level=SecurityLevel.PUBLIC,
                is_authenticated=False,
                is_authorized=False,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
    
    def create_error_response(self, error: str, status_code: int, details: str = None) -> JSONResponse:
        """
        Create standardized error response.
        
        Args:
            error: Error type
            status_code: HTTP status code
            details: Error details
            
        Returns:
            JSONResponse with error information
        """
        security_error = SecurityError(
            error=error,
            error_description=details or error,
            error_code=str(status_code)
        )
        
        return JSONResponse(
            status_code=status_code,
            content=security_error.dict()
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through security middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response object
        """
        # Skip security if disabled
        if not self.enabled:
            return await call_next(request)
        
        path = request.url.path
        method = request.method
        
        # Check if path is excluded
        if self.is_path_excluded(path):
            return await call_next(request)
        
        # Check if path is protected
        if not self.is_path_protected(path):
            return await call_next(request)
        
        # Rate limiting check
        client_id = self.get_client_identifier(request)
        if not self.check_rate_limit(client_id):
            return self.create_error_response(
                "rate_limit_exceeded",
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Rate limit exceeded. Please try again later."
            )
        
        # Custom authentication check
        if self.custom_auth_check:
            try:
                custom_result = await self.custom_auth_check(request)
                if not custom_result:
                    return self.create_error_response(
                        "authentication_failed",
                        status.HTTP_401_UNAUTHORIZED,
                        "Custom authentication check failed"
                    )
            except Exception as e:
                return self.create_error_response(
                    "authentication_error",
                    status.HTTP_401_UNAUTHORIZED,
                    f"Custom authentication error: {str(e)}"
                )
        
        # Standard authentication
        try:
            security_context = self.create_security_context(request)
            
            # Check if authentication is required and successful
            if not security_context.is_authenticated:
                return self.create_error_response(
                    "authentication_required",
                    status.HTTP_401_UNAUTHORIZED,
                    "Authentication required for this endpoint"
                )
            
            # Check authorization
            if not security_context.is_authorized:
                return self.create_error_response(
                    "authorization_failed",
                    status.HTTP_403_FORBIDDEN,
                    "Insufficient permissions for this endpoint"
                )
            
            # Store security context in request state
            request.state.security_context = security_context
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response.headers["X-Security-Context"] = "authenticated"
            response.headers["X-Auth-Type"] = security_context.auth_type
            
            return response
            
        except HTTPException as e:
            return self.create_error_response(
                "authentication_failed",
                e.status_code,
                e.detail
            )
        except Exception as e:
            return self.create_error_response(
                "internal_error",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Security middleware error: {str(e)}"
            )


def create_security_middleware(
    security_config: Dict[str, Any],
    excluded_paths: Optional[List[str]] = None,
    protected_paths: Optional[List[str]] = None,
    custom_auth_check: Optional[Callable] = None
) -> type:
    """
    Factory function to create security middleware class.
    
    Args:
        security_config: Security configuration dictionary
        excluded_paths: List of paths to exclude from authentication
        protected_paths: List of paths that require authentication
        custom_auth_check: Custom authentication check function
        
    Returns:
        SecurityMiddleware class configured with the given parameters
    """
    class ConfiguredSecurityMiddleware(SecurityMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(
                app,
                security_config,
                excluded_paths,
                protected_paths,
                custom_auth_check
            )
    
    return ConfiguredSecurityMiddleware
