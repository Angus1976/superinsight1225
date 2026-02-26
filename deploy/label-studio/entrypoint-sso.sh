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

# ============================================================
# SuperInsight Branding & i18n Patches
# ============================================================

LS_STATIC_DIR="/label-studio/label_studio/core/static"
LS_TEMPLATE_DIR="/label-studio/label_studio/templates"
LS_BASE_TEMPLATE="$LS_TEMPLATE_DIR/base.html"
CUSTOM_DIR="/label-studio/custom"

# --- Patch: Copy i18n-inject.js to LS static directory ---
I18N_MARKER="# SUPERINSIGHT_I18N_PATCH"
I18N_SRC="$CUSTOM_DIR/i18n-inject.js"
I18N_DEST="$LS_STATIC_DIR/i18n-inject.js"

if ! grep -q "$I18N_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    if [ -f "$I18N_SRC" ] && [ -d "$LS_STATIC_DIR" ] && [ -f "$LS_BASE_TEMPLATE" ]; then
        echo "Applying i18n injection patch..."
        cp "$I18N_SRC" "$I18N_DEST"
        # Inject <script> tag before </body>
        sed -i "/$I18N_MARKER/d" "$LS_BASE_TEMPLATE"
        sed -i "s|</body>|<script src=\"/static/i18n-inject.js\"></script> $I18N_MARKER\n</body>|" "$LS_BASE_TEMPLATE"
        echo "i18n injection patch applied"
    else
        echo "ERROR: i18n patch failed - source ($I18N_SRC), static dir ($LS_STATIC_DIR), or template ($LS_BASE_TEMPLATE) not found"
    fi
else
    echo "i18n injection patch already applied, skipping"
fi

# --- Patch: Copy branding.css to LS static directory ---
CSS_MARKER="# SUPERINSIGHT_BRANDING_CSS_PATCH"
CSS_SRC="$CUSTOM_DIR/branding.css"
CSS_DEST="$LS_STATIC_DIR/branding.css"

if ! grep -q "$CSS_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    if [ -f "$CSS_SRC" ] && [ -d "$LS_STATIC_DIR" ] && [ -f "$LS_BASE_TEMPLATE" ]; then
        echo "Applying branding CSS patch..."
        cp "$CSS_SRC" "$CSS_DEST"
        # Inject <link> tag before </head>
        sed -i "/$CSS_MARKER/d" "$LS_BASE_TEMPLATE"
        sed -i "s|</head>|<link rel=\"stylesheet\" href=\"/static/branding.css\"> $CSS_MARKER\n</head>|" "$LS_BASE_TEMPLATE"
        echo "Branding CSS patch applied"
    else
        echo "ERROR: branding CSS patch failed - source ($CSS_SRC), static dir ($LS_STATIC_DIR), or template ($LS_BASE_TEMPLATE) not found"
    fi
else
    echo "Branding CSS patch already applied, skipping"
fi

# --- Patch: Copy favicon to LS static directory ---
FAVICON_MARKER="# SUPERINSIGHT_FAVICON_PATCH"
FAVICON_SRC="$CUSTOM_DIR/favicon.svg"
FAVICON_DEST="$LS_STATIC_DIR/favicon.svg"
FAVICON_ICO_DEST="$LS_STATIC_DIR/favicon.ico"

if [ ! -f "$FAVICON_DEST" ] || ! grep -q "$FAVICON_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    if [ -f "$FAVICON_SRC" ] && [ -d "$LS_STATIC_DIR" ] && [ -f "$LS_BASE_TEMPLATE" ]; then
        echo "Applying favicon patch..."
        cp "$FAVICON_SRC" "$FAVICON_DEST"
        # Also copy as .ico fallback if original exists
        if [ -f "$FAVICON_ICO_DEST" ]; then
            cp "$FAVICON_SRC" "$FAVICON_ICO_DEST"
        fi
        # Replace existing favicon link or inject new one
        if grep -q "favicon" "$LS_BASE_TEMPLATE" 2>/dev/null; then
            sed -i 's|<link[^>]*rel="[^"]*icon[^"]*"[^>]*>|<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">|g' "$LS_BASE_TEMPLATE"
        fi
        # Add marker comment if not present
        if ! grep -q "$FAVICON_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
            sed -i "s|</head>|<!-- $FAVICON_MARKER -->\n</head>|" "$LS_BASE_TEMPLATE"
        fi
        echo "Favicon patch applied"
    else
        echo "ERROR: favicon patch failed - source ($FAVICON_SRC), static dir ($LS_STATIC_DIR), or template ($LS_BASE_TEMPLATE) not found"
    fi
else
    echo "Favicon patch already applied, skipping"
fi

# --- Patch: Replace <title> with 问视间 ---
TITLE_MARKER="# SUPERINSIGHT_TITLE_PATCH"

if ! grep -q "$TITLE_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    if [ -f "$LS_BASE_TEMPLATE" ]; then
        echo "Applying title patch..."
        # Replace title content
        sed -i 's|<title>[^<]*Label Studio[^<]*</title>|<title>问视间</title>|g' "$LS_BASE_TEMPLATE"
        # Add marker comment
        sed -i "s|</head>|<!-- $TITLE_MARKER -->\n</head>|" "$LS_BASE_TEMPLATE"
        echo "Title patch applied"
    else
        echo "ERROR: title patch failed - template ($LS_BASE_TEMPLATE) not found"
    fi
else
    echo "Title patch already applied, skipping"
fi

# Run original entrypoint
exec /label-studio/deploy/docker-entrypoint.sh "$@"
