"""
JWT Bearer token authentication handler.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models import TokenData, SecurityContext, AuthType, SecurityLevel, SecurityError


class JWTHandler:
    """
    JWT Bearer token authentication handler.
    Handles JWT token creation, validation, and user context extraction.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize JWT handler with configuration.
        
        Args:
            config: Security configuration dictionary
        """
        self.secret_key = config.get("jwt_secret_key")
        self.algorithm = config.get("jwt_algorithm", "HS256")
        self.access_token_expire_minutes = config.get("jwt_access_token_expire_minutes", 30)
        self.refresh_token_expire_days = config.get("jwt_refresh_token_expire_days", 7)
        self.issuer = config.get("jwt_issuer", "fastapi-rest-template")
        
        if not self.secret_key:
            raise ValueError("JWT secret key is required")
        
        self.security = HTTPBearer(auto_error=False)
    
    def create_access_token(
        self, 
        user_id: str, 
        username: str, 
        roles: list = None, 
        permissions: list = None,
        additional_claims: Dict[str, Any] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User identifier
            username: Username
            roles: List of user roles
            permissions: List of user permissions
            additional_claims: Additional claims to include
            
        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "username": username,
            "user_id": user_id,
            "roles": roles or [],
            "permissions": permissions or [],
            "exp": expire,
            "iat": now,
            "iss": self.issuer,
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str, username: str) -> str:
        """
        Create a JWT refresh token.
        
        Args:
            user_id: User identifier
            username: Username
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "username": username,
            "user_id": user_id,
            "exp": expire,
            "iat": now,
            "iss": self.issuer,
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object with decoded token information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_iss": True}
            )
            
            # Verify issuer
            if payload.get("iss") != self.issuer:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer"
                )
            
            # Check token type
            token_type = payload.get("type", "access")
            if token_type not in ["access", "refresh"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return TokenData(
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                email=payload.get("email"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                exp=datetime.fromtimestamp(payload.get("exp", 0)),
                iat=datetime.fromtimestamp(payload.get("iat", 0)),
                iss=payload.get("iss"),
                sub=payload.get("sub")
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            JWT token string or None if not found
        """
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    def authenticate_request(self, request: Request) -> SecurityContext:
        """
        Authenticate a request using JWT token.
        
        Args:
            request: FastAPI request object
            
        Returns:
            SecurityContext object with authentication information
            
        Raises:
            HTTPException: If authentication fails
        """
        token = self.extract_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        try:
            token_data = self.verify_token(token)
            
            return SecurityContext(
                user_id=token_data.user_id,
                username=token_data.username,
                auth_type=AuthType.JWT,
                security_level=SecurityLevel.PROTECTED,
                permissions=token_data.permissions,
                roles=token_data.roles,
                is_authenticated=True,
                is_authorized=True,
                request_id=request.headers.get("X-Request-ID"),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent")
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token from a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token string
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            token_data = self.verify_token(refresh_token)
            
            if not token_data.user_id or not token_data.username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Create new access token
            return self.create_access_token(
                user_id=token_data.user_id,
                username=token_data.username,
                roles=token_data.roles,
                permissions=token_data.permissions
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token refresh failed: {str(e)}"
            )
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Get token information without verification (for debugging).
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with token information
        """
        try:
            # Decode without verification for debugging
            payload = jwt.decode(
                token, 
                options={"verify_signature": False}
            )
            
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "iss": payload.get("iss"),
                "type": payload.get("type")
            }
        except Exception as e:
            return {"error": str(e)}
