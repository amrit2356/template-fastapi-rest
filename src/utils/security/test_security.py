"""
Simple test script to verify the security module functionality.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.security import SecurityManager, AuthFactory, AuthType
from src.utils.security.models import SecurityConfig


def test_security_module():
    """Test basic security module functionality."""
    print("🧪 Testing Security Module...")
    
    # Test 1: Create SecurityManager with default config
    print("\n1. Testing SecurityManager creation...")
    try:
        # Create a test configuration
        test_config = {
            "enabled": True,
            "auth_type": "jwt",
            "jwt_secret_key": "test-secret-key-for-testing-only",
            "jwt_algorithm": "HS256",
            "jwt_access_token_expire_minutes": 30,
            "jwt_issuer": "test-app"
        }
        
        security = SecurityManager(test_config)
        print(f"   ✅ SecurityManager created successfully")
        print(f"   ✅ Security enabled: {security.is_enabled()}")
        print(f"   ✅ Auth handler available: {security.get_auth_handler() is not None}")
        
    except Exception as e:
        print(f"   ❌ Failed to create SecurityManager: {e}")
        return False
    
    # Test 2: Test JWT token creation
    print("\n2. Testing JWT token creation...")
    try:
        access_token = security.create_jwt_token(
            user_id="test_user_123",
            username="testuser",
            roles=["user", "admin"],
            permissions=["read", "write"]
        )
        
        if access_token:
            print(f"   ✅ JWT access token created: {access_token[:50]}...")
        else:
            print(f"   ❌ Failed to create JWT token")
            return False
            
        refresh_token = security.create_refresh_token("test_user_123", "testuser")
        if refresh_token:
            print(f"   ✅ JWT refresh token created: {refresh_token[:50]}...")
        else:
            print(f"   ❌ Failed to create refresh token")
            return False
            
    except Exception as e:
        print(f"   ❌ JWT token creation failed: {e}")
        return False
    
    # Test 3: Test API Key creation
    print("\n3. Testing API key creation...")
    try:
        result = security.create_api_key(
            name="Test API Key",
            user_id="test_user_123",
            permissions=["read", "write"]
        )
        
        if result is not None:
            api_key, key_data = result
            if api_key and key_data:
                print(f"   ✅ API key created: {api_key[:20]}...")
                print(f"   ✅ Key ID: {key_data.key_id}")
                print(f"   ✅ Key name: {key_data.name}")
            else:
                print(f"   ❌ Failed to create API key - invalid result")
                return False
        else:
            print(f"   ⚠️ API key creation not supported for JWT auth type (this is expected)")
            
    except Exception as e:
        print(f"   ❌ API key creation failed: {e}")
        return False
    
    # Test 4: Test AuthFactory
    print("\n4. Testing AuthFactory...")
    try:
        # Test JWT handler creation
        jwt_handler = AuthFactory.create_handler({
            "auth_type": "jwt",
            "jwt_secret_key": "test-secret-key",
            "jwt_algorithm": "HS256"
        })
        
        if jwt_handler:
            print(f"   ✅ JWT handler created: {type(jwt_handler).__name__}")
        else:
            print(f"   ❌ Failed to create JWT handler")
            return False
        
        # Test API Key handler creation
        api_key_handler = AuthFactory.create_handler({
            "auth_type": "api_key",
            "api_key_header": "X-API-Key"
        })
        
        if api_key_handler:
            print(f"   ✅ API Key handler created: {type(api_key_handler).__name__}")
        else:
            print(f"   ❌ Failed to create API Key handler")
            return False
        
        # Test Hybrid handler creation
        hybrid_handler = AuthFactory.create_handler({
            "auth_type": "hybrid",
            "jwt_secret_key": "test-secret-key",
            "jwt_algorithm": "HS256",
            "prefer_jwt": True
        })
        
        if hybrid_handler:
            print(f"   ✅ Hybrid handler created: {type(hybrid_handler).__name__}")
        else:
            print(f"   ❌ Failed to create Hybrid handler")
            return False
            
    except Exception as e:
        print(f"   ❌ AuthFactory test failed: {e}")
        return False
    
    # Test 5: Test SecurityConfig model
    print("\n5. Testing SecurityConfig model...")
    try:
        config_data = {
            "enabled": True,
            "auth_type": "jwt",
            "jwt_secret_key": "test-secret-key-for-validation-must-be-at-least-32-chars-long",
            "jwt_algorithm": "HS256",
            "jwt_access_token_expire_minutes": 30,
            "jwt_refresh_token_expire_days": 7,
            "jwt_issuer": "test-app",
            "api_key_header": "X-API-Key",
            "api_key_query_param": "api_key",
            "api_key_length": 32,
            "password_min_length": 8,
            "rate_limit_enabled": True,
            "rate_limit_requests_per_minute": 60,
            "excluded_paths": ["/docs", "/health"],
            "protected_paths": ["/api/v1"]
        }
        
        security_config = SecurityConfig(**config_data)
        print(f"   ✅ SecurityConfig created successfully")
        print(f"   ✅ Auth type: {security_config.auth_type}")
        print(f"   ✅ JWT issuer: {security_config.jwt_issuer}")
        print(f"   ✅ API key length: {security_config.api_key_length}")
        
    except Exception as e:
        print(f"   ❌ SecurityConfig test failed: {e}")
        return False
    
    # Test 6: Test statistics
    print("\n6. Testing security statistics...")
    try:
        stats = security.get_stats()
        print(f"   ✅ Security stats retrieved: {stats}")
        
    except Exception as e:
        print(f"   ❌ Statistics test failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Security module is working correctly.")
    return True


def test_disabled_security():
    """Test security module when disabled."""
    print("\n🧪 Testing Disabled Security...")
    
    try:
        disabled_config = {
            "enabled": False,
            "auth_type": "none"
        }
        
        security = SecurityManager(disabled_config)
        print(f"   ✅ Disabled SecurityManager created")
        print(f"   ✅ Security enabled: {security.is_enabled()}")
        print(f"   ✅ Auth handler: {security.get_auth_handler()}")
        
        # Test that no tokens can be created when disabled
        token = security.create_jwt_token("user", "username")
        if token is None:
            print(f"   ✅ JWT token creation correctly returns None when disabled")
        else:
            print(f"   ❌ JWT token creation should return None when disabled")
            return False
        
        result = security.create_api_key("test")
        if result is None:
            print(f"   ✅ API key creation correctly returns None when disabled")
        else:
            print(f"   ❌ API key creation should return None when disabled")
            return False
        
        print("   ✅ Disabled security test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Disabled security test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting Security Module Tests")
    print("=" * 50)
    
    # Run tests
    success = test_security_module()
    success &= test_disabled_security()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Security module is ready for use.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
