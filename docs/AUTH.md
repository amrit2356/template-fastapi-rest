# Security Module

A comprehensive, production-grade security module for FastAPI applications that provides authentication, authorization, and security middleware with minimal code integration.

## Features

- **Multiple Authentication Methods**: JWT Bearer tokens, API Keys, and Hybrid authentication
- **Auto-Protection Middleware**: Automatically secures endpoints based on configuration
- **Rate Limiting**: Built-in rate limiting with configurable limits
- **Easy Configuration**: Configure everything via `config.yaml` - no code changes needed
- **Production Ready**: Secure by default with proper error handling and logging
- **Flexible**: Easy to enable/disable and customize for different environments

## Quick Start

### 1. Configuration

Configure security in `src/utils/config/config.yaml`:

```yaml
security:
  # Enable/disable security
  enabled: true
  
  # Authentication type: jwt, api_key, hybrid, none
  auth_type: "jwt"
  
  # JWT Configuration
  jwt_secret_key: "${JWT_SECRET_KEY}"
  jwt_algorithm: "HS256"
  jwt_access_token_expire_minutes: 30
  jwt_refresh_token_expire_days: 7
  
  # API Key Configuration
  api_key_header: "X-API-Key"
  api_key_query_param: "api_key"
  api_key_length: 32
  
  # Rate Limiting
  rate_limit_enabled: true
  rate_limit_requests_per_minute: 60
  
  # Path Configuration
  excluded_paths: ["/docs", "/health", "/metrics"]
  protected_paths: ["/api/v1"]
```

### 2. Integration

Add security to your FastAPI app with just a few lines:

```python
from fastapi import FastAPI
from src.utils.security import create_security_manager_from_settings

app = FastAPI()

# Create security manager
security = create_security_manager_from_settings()

# Add middleware if enabled
if security.is_enabled():
    SecurityMiddleware = security.get_middleware()
    app.add_middleware(SecurityMiddleware)
```

### 3. Usage

That's it! Your app is now secured. All endpoints matching `protected_paths` will require authentication.

## Authentication Methods

### JWT Authentication

```python
# Create JWT token
token = security.create_jwt_token(
    user_id="123",
    username="john_doe",
    roles=["user", "admin"],
    permissions=["read", "write"]
)

# Use in requests
headers = {"Authorization": f"Bearer {token}"}
```

### API Key Authentication

```python
# Create API key
api_key, key_data = security.create_api_key(
    name="My API Key",
    user_id="123",
    permissions=["read", "write"]
)

# Use in requests
headers = {"X-API-Key": api_key}
# Or as query parameter: ?api_key=your_key_here
```

### Hybrid Authentication

Supports both JWT and API Key authentication. Tries JWT first, falls back to API Key.

## Configuration Options

### Security Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable security module |
| `auth_type` | str | `"jwt"` | Authentication method: `jwt`, `api_key`, `hybrid`, `none` |
| `default_security_level` | str | `"protected"` | Default security level for endpoints |

### JWT Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `jwt_secret_key` | str | Required | Secret key for JWT signing |
| `jwt_algorithm` | str | `"HS256"` | JWT signing algorithm |
| `jwt_access_token_expire_minutes` | int | `30` | Access token expiration |
| `jwt_refresh_token_expire_days` | int | `7` | Refresh token expiration |
| `jwt_issuer` | str | `"fastapi-rest-template"` | JWT issuer claim |

### API Key Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `api_key_header` | str | `"X-API-Key"` | Header name for API key |
| `api_key_query_param` | str | `"api_key"` | Query parameter name |
| `api_key_length` | int | `32` | API key length |

### Rate Limiting

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `rate_limit_enabled` | bool | `true` | Enable rate limiting |
| `rate_limit_requests_per_minute` | int | `60` | Requests per minute limit |
| `rate_limit_burst_size` | int | `10` | Burst allowance |

### Path Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `excluded_paths` | list | `["/docs", "/health"]` | Paths that don't require auth |
| `protected_paths` | list | `["/api/v1"]` | Paths that require authentication |

## Advanced Usage

### Custom Authentication Check

```python
async def custom_auth_check(request: Request) -> bool:
    # Your custom authentication logic
    return True

# Create middleware with custom check
SecurityMiddleware = create_security_middleware(
    security_config=config,
    custom_auth_check=custom_auth_check
)
```

### Getting Security Context

```python
from fastapi import Request, Depends

def get_current_user(request: Request):
    return getattr(request.state, 'security_context', None)

@app.get("/protected")
async def protected_endpoint(user: SecurityContext = Depends(get_current_user)):
    return {"user_id": user.user_id, "username": user.username}
```

### Creating Tokens Programmatically

```python
# JWT tokens
access_token = security.create_jwt_token(
    user_id="123",
    username="john",
    roles=["user"],
    permissions=["read"]
)

refresh_token = security.create_refresh_token("123", "john")

# API keys
api_key, key_data = security.create_api_key(
    name="Service API Key",
    user_id="123",
    permissions=["read", "write"],
    rate_limit=100
)
```

## Security Context

The security context provides information about the authenticated user:

```python
class SecurityContext:
    user_id: Optional[str]
    username: Optional[str]
    auth_type: AuthType
    security_level: SecurityLevel
    permissions: List[str]
    roles: List[str]
    is_authenticated: bool
    is_authorized: bool
    request_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
```

## Error Handling

The module provides standardized error responses:

```json
{
    "error": "authentication_required",
    "error_description": "Authentication required for this endpoint",
    "error_code": "401",
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123"
}
```

## Environment Variables

Set these environment variables for production:

```bash
export JWT_SECRET_KEY="your-super-secret-key-here"
export ENVIRONMENT="production"
```

## Disabling Security

To disable security completely:

```yaml
security:
  enabled: false
```

Or set `auth_type` to `"none"`:

```yaml
security:
  enabled: true
  auth_type: "none"
```

## Production Considerations

1. **Secret Keys**: Use strong, random secret keys in production
2. **HTTPS**: Always use HTTPS in production
3. **Rate Limiting**: Adjust rate limits based on your needs
4. **Monitoring**: Monitor authentication failures and rate limit hits
5. **Token Expiration**: Set appropriate token expiration times
6. **API Key Management**: Implement proper API key lifecycle management

## Example Application

See `example_integration.py` for a complete example of integrating the security module into a FastAPI application.

## Troubleshooting

### Common Issues

1. **"JWT secret key is required"**: Set the `JWT_SECRET_KEY` environment variable
2. **"Authentication required"**: Check that your endpoint path is in `protected_paths`
3. **"Rate limit exceeded"**: Adjust `rate_limit_requests_per_minute` in config
4. **"Invalid token"**: Check token format and expiration

### Debug Mode

Enable debug logging to see security events:

```yaml
logging:
  level: "debug"
```

## API Reference

### SecurityManager

Main class for managing security features.

```python
security = SecurityManager(config)
```

### Methods

- `get_auth_handler()`: Get authentication handler
- `get_middleware()`: Get security middleware class
- `is_enabled()`: Check if security is enabled
- `create_jwt_token()`: Create JWT access token
- `create_refresh_token()`: Create JWT refresh token
- `create_api_key()`: Create API key
- `list_api_keys()`: List user's API keys
- `revoke_api_key()`: Revoke API key
- `get_stats()`: Get security statistics

### Handlers

- `JWTHandler`: JWT Bearer token authentication
- `APIKeyHandler`: API Key authentication
- `HybridHandler`: Combined JWT + API Key authentication

### Models

- `SecurityConfig`: Security configuration model
- `SecurityContext`: Security context for requests
- `TokenData`: JWT token data
- `APIKeyData`: API key data
- `AuthRequest/Response`: Authentication request/response models
