"""
Example integration of the security module with FastAPI.

This file demonstrates how to integrate the security module into a FastAPI application
with minimal code changes. The security is configured via config.yaml and automatically
applied to all endpoints.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional

# Import the security module
from . import SecurityManager, SecurityContext, create_security_manager_from_settings


def create_secure_app() -> FastAPI:
    """
    Create a FastAPI application with security middleware.
    
    Returns:
        FastAPI application instance with security enabled
    """
    app = FastAPI(
        title="Secure FastAPI Application",
        description="Example application with integrated security",
        version="1.0.0"
    )
    
    # Create security manager from settings
    security = create_security_manager_from_settings()
    
    # Add security middleware if enabled
    if security.is_enabled():
        SecurityMiddleware = security.get_middleware()
        app.add_middleware(SecurityMiddleware)
        print("✅ Security middleware added to application")
    else:
        print("⚠️ Security is disabled in configuration")
    
    return app, security


# Create the app and security manager
app, security_manager = create_secure_app()


# Dependency to get current user from security context
def get_current_user(request: Request) -> Optional[SecurityContext]:
    """
    Get the current user from the security context.
    
    Args:
        request: FastAPI request object
        
    Returns:
        SecurityContext object or None if not authenticated
    """
    return getattr(request.state, 'security_context', None)


# Dependency to require authentication
def require_auth(request: Request) -> SecurityContext:
    """
    Require authentication for the endpoint.
    
    Args:
        request: FastAPI request object
        
    Returns:
        SecurityContext object
        
    Raises:
        HTTPException: If not authenticated
    """
    security_context = get_current_user(request)
    if not security_context or not security_context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return security_context


# Public endpoints (no authentication required)
@app.get("/")
async def root():
    """Public root endpoint."""
    return {"message": "Welcome to the secure FastAPI application"}


@app.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {"status": "healthy", "security_enabled": security_manager.is_enabled()}


# Protected endpoints (authentication required)
@app.get("/api/v1/profile")
async def get_profile(current_user: SecurityContext = Depends(require_auth)):
    """Get user profile - requires authentication."""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "auth_type": current_user.auth_type,
        "roles": current_user.roles,
        "permissions": current_user.permissions
    }


@app.get("/api/v1/admin")
async def admin_endpoint(current_user: SecurityContext = Depends(require_auth)):
    """Admin endpoint - requires authentication."""
    # Check if user has admin role
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    return {"message": "Admin access granted", "user": current_user.username}


# Authentication endpoints
@app.post("/api/v1/auth/login")
async def login(username: str, password: str):
    """
    Login endpoint - creates JWT token.
    Note: This is a simplified example. In production, you should:
    1. Validate credentials against a database
    2. Hash passwords properly
    3. Implement proper user management
    """
    if not security_manager.is_enabled():
        return {"message": "Security is disabled"}
    
    # Simplified authentication (replace with real user validation)
    if username == "admin" and password == "admin123":
        # Create JWT token
        access_token = security_manager.create_jwt_token(
            user_id="1",
            username=username,
            roles=["admin", "user"],
            permissions=["read", "write", "admin"]
        )
        
        refresh_token = security_manager.create_refresh_token(
            user_id="1",
            username=username
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800  # 30 minutes
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@app.post("/api/v1/auth/api-key")
async def create_api_key(
    name: str,
    current_user: SecurityContext = Depends(require_auth)
):
    """
    Create API key endpoint - requires authentication.
    """
    if not security_manager.is_enabled():
        return {"message": "Security is disabled"}
    
    # Create API key
    api_key, api_key_data = security_manager.create_api_key(
        name=name,
        user_id=current_user.user_id,
        permissions=current_user.permissions
    )
    
    return {
        "api_key": api_key,
        "key_id": api_key_data.key_id,
        "name": api_key_data.name,
        "permissions": api_key_data.permissions,
        "created_at": api_key_data.created_at
    }


@app.get("/api/v1/auth/api-keys")
async def list_api_keys(current_user: SecurityContext = Depends(require_auth)):
    """
    List user's API keys - requires authentication.
    """
    if not security_manager.is_enabled():
        return {"message": "Security is disabled"}
    
    api_keys = security_manager.list_api_keys(user_id=current_user.user_id)
    
    return {
        "api_keys": [
            {
                "key_id": key.key_id,
                "name": key.name,
                "permissions": key.permissions,
                "is_active": key.is_active,
                "created_at": key.created_at,
                "last_used": key.last_used
            }
            for key in api_keys
        ]
    }


@app.delete("/api/v1/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: SecurityContext = Depends(require_auth)
):
    """
    Revoke API key - requires authentication.
    """
    if not security_manager.is_enabled():
        return {"message": "Security is disabled"}
    
    success = security_manager.revoke_api_key(key_id)
    
    if success:
        return {"message": f"API key {key_id} revoked successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@app.get("/api/v1/security/stats")
async def get_security_stats(current_user: SecurityContext = Depends(require_auth)):
    """
    Get security statistics - requires authentication.
    """
    if not security_manager.is_enabled():
        return {"message": "Security is disabled"}
    
    stats = security_manager.get_stats()
    return stats


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with security context."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting secure FastAPI application...")
    print(f"Security enabled: {security_manager.is_enabled()}")
    if security_manager.is_enabled():
        print(f"Auth type: {security_manager.get_config().get('auth_type', 'unknown')}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
