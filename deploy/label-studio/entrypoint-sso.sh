#!/bin/bash
set -e

# Patch Label Studio settings to include SSO (only once)
SETTINGS_FILE="/label-studio/label_studio/core/settings/label_studio.py"
MARKER="# SSO_PATCHED_BY_SUPERINSIGHT"

if ! grep -q "$MARKER" "$SETTINGS_FILE" 2>/dev/null; then
    echo "Patching Label Studio settings for SSO..."
    
    cat >> "$SETTINGS_FILE" << 'EOF'

# SSO_PATCHED_BY_SUPERINSIGHT
# SSO Configuration added by SuperInsight
import os as _sso_os

if _sso_os.environ.get('LABEL_STUDIO_SSO_ENABLED', 'false').lower() == 'true':
    # Only add label_studio_sso (authtoken already exists in Label Studio)
    if 'label_studio_sso' not in INSTALLED_APPS:
        INSTALLED_APPS = list(INSTALLED_APPS) + ['label_studio_sso']
    
    AUTHENTICATION_BACKENDS = [
        'label_studio_sso.backends.JWTAuthenticationBackend',
    ] + list(AUTHENTICATION_BACKENDS)
    
    MIDDLEWARE = list(MIDDLEWARE) + [
        'label_studio_sso.middleware.JWTAutoLoginMiddleware',
    ]
    
    JWT_SSO_NATIVE_USER_ID_CLAIM = 'user_id'
    JWT_SSO_COOKIE_NAME = 'ls_auth_token'
    JWT_SSO_COOKIE_PATH = '/'
    JWT_SSO_TOKEN_PARAM = 'token'
    SSO_TOKEN_EXPIRY = 600
    SSO_AUTO_CREATE_USER = True  # Enable auto-create user
    
    print("Label Studio SSO enabled")
EOF
    echo "SSO settings patched"
fi

# Patch label-studio-sso views.py to support auto-create user
SSO_VIEWS_FILE="/label-studio/.venv/lib/python3.13/site-packages/label_studio_sso/views.py"
SSO_MARKER="# AUTO_CREATE_PATCHED"

if [ -f "$SSO_VIEWS_FILE" ] && ! grep -q "$SSO_MARKER" "$SSO_VIEWS_FILE" 2>/dev/null; then
    echo "Patching label-studio-sso for auto-create user..."
    
    # Replace the user lookup section to support auto-create
    python3 << 'PYTHON_SCRIPT'
import re

views_file = "/label-studio/.venv/lib/python3.13/site-packages/label_studio_sso/views.py"

with open(views_file, 'r') as f:
    content = f.read()

# Find and replace the user lookup section
old_code = '''        # 4. Validate user exists (no auto-create)
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {email}")
        except User.DoesNotExist:
            logger.warning(f"User not found: {email}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"User not found: {email}",
                    "error_code": "USER_NOT_FOUND",
                    "email": email,
                },
                status=422,
            )'''

new_code = '''        # 4. Get or create user (auto-create if enabled)
        # AUTO_CREATE_PATCHED
        auto_create = getattr(settings, "SSO_AUTO_CREATE_USER", False)
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {email}")
        except User.DoesNotExist:
            if auto_create:
                # Auto-create user
                username = data.get("username") or email.split("@")[0]
                first_name = data.get("first_name", "")
                last_name = data.get("last_name", "")
                
                # Ensure unique username
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                user = User.objects.create(
                    email=email,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                )
                logger.info(f"User auto-created: {email} (username: {username})")
            else:
                logger.warning(f"User not found: {email}")
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"User not found: {email}",
                        "error_code": "USER_NOT_FOUND",
                        "email": email,
                    },
                    status=422,
                )'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(views_file, 'w') as f:
        f.write(content)
    print("label-studio-sso patched for auto-create user")
else:
    print("Could not find target code to patch, may already be patched")
PYTHON_SCRIPT
    
    echo "SSO auto-create patch complete"
fi

# Patch URLs (only once)
URLS_FILE="/label-studio/label_studio/core/urls.py"
if ! grep -q "label_studio_sso" "$URLS_FILE" 2>/dev/null; then
    echo "Patching Label Studio URLs for SSO..."
    
    # Add include import if needed
    if ! grep -q "from django.urls import.*include" "$URLS_FILE"; then
        sed -i 's/from django.urls import path/from django.urls import path, include/' "$URLS_FILE"
    fi
    
    # Add SSO URL pattern
    sed -i "/^urlpatterns = \[/a\\    path('api/sso/', include('label_studio_sso.urls'))," "$URLS_FILE"
    echo "SSO URLs patched"
fi

# Run original entrypoint
exec /label-studio/deploy/docker-entrypoint.sh "$@"
