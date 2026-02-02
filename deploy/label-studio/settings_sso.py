# Label Studio SSO Settings
# This file is imported at the end of label_studio.py to enable SSO

import os

SSO_ENABLED = os.environ.get('LABEL_STUDIO_SSO_ENABLED', 'true').lower() == 'true'

if SSO_ENABLED:
    # JWT SSO Configuration
    JWT_SSO_NATIVE_USER_ID_CLAIM = 'user_id'
    JWT_SSO_COOKIE_NAME = 'ls_auth_token'
    JWT_SSO_COOKIE_PATH = '/'
    JWT_SSO_TOKEN_PARAM = 'token'
    
    # Token expiry (10 minutes)
    SSO_TOKEN_EXPIRY = 600
