"""
Security-related Pydantic models for authentication and authorization.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class AuthType(str, Enum):
    """Authentication types supported by the security module."""
    JWT = "jwt"
    API_KEY = "api_key"
    HYBRID = "hybrid"
    NONE = "none"


class SecurityLevel(str, Enum):
    """Security levels for different endpoints."""
    PUBLIC = "public"
    PROTECTED = "protected"
    RESTRICTED = "restricted"
    ADMIN = "admin"


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
    iss: Optional[str] = None
    sub: Optional[str] = None


class APIKeyData(BaseModel):
    """API Key data structure."""
    key_id: str
    name: str
    user_id: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


class SecurityConfig(BaseModel):
    """Security configuration model."""
    enabled: bool = True
    auth_type: AuthType = AuthType.JWT
    default_security_level: SecurityLevel = SecurityLevel.PROTECTED
    
    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "fastapi-rest-template"
    
    # API Key Configuration
    api_key_header: str = "X-API-Key"
    api_key_query_param: str = "api_key"
    api_key_length: int = 32
    
    # Security Policies
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special_chars: bool = True
    
    # Session Management
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10
    
    # CORS Configuration
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    cors_allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    
    # Excluded paths (no authentication required)
    excluded_paths: List[str] = Field(default_factory=lambda: [
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/health",
        "/metrics"
    ])
    
    # Protected paths (require authentication)
    protected_paths: List[str] = Field(default_factory=lambda: ["/api/v1"])
    
    @validator('jwt_secret_key')
    def validate_jwt_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters long')
        return v
    
    @validator('api_key_length')
    def validate_api_key_length(cls, v):
        if v < 16 or v > 64:
            raise ValueError('API key length must be between 16 and 64 characters')
        return v


class AuthRequest(BaseModel):
    """Authentication request model."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    remember_me: bool = False


class AuthResponse(BaseModel):
    """Authentication response model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    roles: List[str] = Field(default_factory=list)


class APIKeyRequest(BaseModel):
    """API Key creation request model."""
    name: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API Key response model."""
    key_id: str
    api_key: str
    name: str
    user_id: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class SecurityContext(BaseModel):
    """Security context for request processing."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    auth_type: AuthType
    security_level: SecurityLevel
    permissions: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    is_authenticated: bool = False
    is_authorized: bool = False
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SecurityError(BaseModel):
    """Security error response model."""
    error: str
    error_description: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class SecurityMetrics(BaseModel):
    """Security metrics for monitoring."""
    total_requests: int = 0
    authenticated_requests: int = 0
    failed_authentications: int = 0
    rate_limited_requests: int = 0
    blocked_requests: int = 0
    active_sessions: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class SecurityEvent(BaseModel):
    """Security event for logging and monitoring."""
    event_type: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = "info"  # info, warning, error, critical
