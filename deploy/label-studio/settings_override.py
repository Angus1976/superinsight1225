# Label Studio SSO Settings Override
# This file is imported by Label Studio's settings to enable SSO

import os

# SSO Configuration
SSO_ENABLED = os.environ.get('LABEL_STUDIO_SSO_ENABLED', 'true').lower() == 'true'

if SSO_ENABLED:
    # Add label_studio_sso to installed apps
    INSTALLED_APPS_EXTRA = [
        'label_studio_sso',
        'rest_framework',
        'rest_framework.authtoken',
    ]
    
    # JWT SSO Configuration
    JWT_SSO_NATIVE_USER_ID_CLAIM = 'user_id'
    JWT_SSO_COOKIE_NAME = 'ls_auth_token'
    JWT_SSO_COOKIE_PATH = '/'
    JWT_SSO_TOKEN_PARAM = 'token'
    
    # Token expiry (10 minutes)
    SSO_TOKEN_EXPIRY = 600
    
    # Authentication backends
    AUTHENTICATION_BACKENDS_EXTRA = [
        'label_studio_sso.backends.JWTAuthenticationBackend',
    ]
    
    # Middleware
    MIDDLEWARE_EXTRA = [
        'label_studio_sso.middleware.JWTAutoLoginMiddleware',
    ]
