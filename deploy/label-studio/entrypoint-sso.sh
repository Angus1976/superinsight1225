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
    
    # Register DRF authentication classes for API Bearer token support
    # SSOBearerAuthentication: direct Bearer JWT validation for backend-to-backend calls
    # JWTSSOSessionAuthentication: session-based (after middleware login)
    _sso_drf_classes = [
        'label_studio_sso.bearer_auth.SSOBearerAuthentication',
        'label_studio_sso.authentication.JWTSSOSessionAuthentication',
    ]
    if 'REST_FRAMEWORK' not in dir():
        REST_FRAMEWORK = {}
    _existing = list(REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', []))
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = _sso_drf_classes + _existing
    
    print("Label Studio SSO enabled")
EOF
    echo "SSO settings patched"
fi

# Create SSOBearerAuthentication DRF class for direct Bearer JWT validation
# This allows backend-to-backend API calls using Bearer <sso_jwt> header
# Dynamically detect Python version to avoid hardcoded path breakage
SSO_PKG_DIR=$(python3 -c "import label_studio_sso, os; print(os.path.dirname(label_studio_sso.__file__))" 2>/dev/null || echo "/label-studio/.venv/lib/python3.13/site-packages/label_studio_sso")
BEARER_AUTH_FILE="$SSO_PKG_DIR/bearer_auth.py"
BEARER_MARKER="# BEARER_AUTH_CREATED"

if [ -d "$SSO_PKG_DIR" ] && ! grep -q "$BEARER_MARKER" "$BEARER_AUTH_FILE" 2>/dev/null; then
    echo "Creating SSOBearerAuthentication for DRF..."
    
    cat > "$BEARER_AUTH_FILE" << 'BEARER_EOF'
# BEARER_AUTH_CREATED
"""
DRF Bearer JWT Authentication for Label Studio SSO.

Validates JWT tokens issued by /api/sso/token endpoint directly
from the Authorization: Bearer <token> header. This enables
backend-to-backend API calls without session/cookie overhead.
"""
import logging
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)
User = get_user_model()


class SSOBearerAuthentication(BaseAuthentication):
    """Authenticate DRF API requests using SSO JWT Bearer tokens."""

    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith(self.keyword + ' '):
            return None

        token = auth_header[len(self.keyword) + 1:]
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                audience='label-studio-sso',
                issuer='label-studio',
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('SSO token has expired')
        except jwt.InvalidTokenError as e:
            # Not an SSO token — let other backends try
            return None

        user_id = payload.get('user_id')
        email = payload.get('email')
        if not user_id and not email:
            return None

        try:
            if user_id:
                user = User.objects.get(pk=user_id)
            else:
                user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed('SSO user not found')

        logger.debug(f"SSO Bearer auth OK: user={user.email}")
        return (user, token)

    def authenticate_header(self, request):
        return self.keyword
BEARER_EOF
    echo "SSOBearerAuthentication created"
fi

# Patch jwt_auth/auth.py to add SSO Bearer JWT fallback
# LS views explicitly set authentication_classes=[TokenAuthenticationPhaseout, SessionAuthentication]
# which bypasses global DEFAULT_AUTHENTICATION_CLASSES. We patch TokenAuthenticationPhaseout
# to fall back to SSO Bearer JWT when legacy token auth fails/returns None.
JWT_AUTH_FILE="/label-studio/label_studio/jwt_auth/auth.py"
JWT_AUTH_MARKER="# SSO_BEARER_FALLBACK_PATCHED"

if [ -f "$JWT_AUTH_FILE" ] && ! grep -q "$JWT_AUTH_MARKER" "$JWT_AUTH_FILE" 2>/dev/null; then
    echo "Patching TokenAuthenticationPhaseout with SSO Bearer fallback..."

    cat >> "$JWT_AUTH_FILE" << 'JWT_PATCH_EOF'

# SSO_BEARER_FALLBACK_PATCHED
# Monkey-patch: add SSO Bearer JWT fallback to TokenAuthenticationPhaseout
# LS views hardcode authentication_classes, so global DRF settings are ignored.
# This makes TokenAuthenticationPhaseout try SSO Bearer JWT when legacy token fails.
import os as _patch_os
if _patch_os.environ.get('LABEL_STUDIO_SSO_ENABLED', 'false').lower() == 'true':
    _original_authenticate = TokenAuthenticationPhaseout.authenticate

    def _patched_authenticate(self, request):
        """Try legacy token first, fall back to SSO Bearer JWT."""
        from rest_framework.exceptions import AuthenticationFailed as _AuthFailed
        try:
            result = _original_authenticate(self, request)
            if result is not None:
                return result
        except _AuthFailed:
            pass  # Legacy token failed, try SSO Bearer

        # Try SSO Bearer JWT
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]
        if not token:
            return None

        try:
            import jwt as _jwt
            from django.conf import settings as _settings
            from django.contrib.auth import get_user_model as _get_user_model
            payload = _jwt.decode(
                token, _settings.SECRET_KEY,
                algorithms=['HS256'],
                audience='label-studio-sso',
                issuer='label-studio',
            )
            _User = _get_user_model()
            user_id = payload.get('user_id')
            email = payload.get('email')
            if user_id:
                user = _User.objects.get(pk=user_id)
            elif email:
                user = _User.objects.get(email=email)
            else:
                return None

            # Update CurrentContext like the original does
            try:
                from core.current_request import CurrentContext
                CurrentContext.set_user(user)
            except Exception:
                pass

            return (user, token)
        except Exception:
            return None

    TokenAuthenticationPhaseout.authenticate = _patched_authenticate
    logger.info('SSO Bearer JWT fallback patched into TokenAuthenticationPhaseout')
JWT_PATCH_EOF
    echo "TokenAuthenticationPhaseout SSO Bearer fallback patched"
fi

# Patch label-studio-sso views.py to support auto-create user
SSO_VIEWS_FILE="$SSO_PKG_DIR/views.py"
SSO_MARKER="# AUTO_CREATE_PATCHED"

if [ -f "$SSO_VIEWS_FILE" ] && ! grep -q "$SSO_MARKER" "$SSO_VIEWS_FILE" 2>/dev/null; then
    echo "Patching label-studio-sso for auto-create user..."
    
    # Replace the user lookup section to support auto-create
    python3 << 'PYTHON_SCRIPT'
import label_studio_sso, os
views_file = os.path.join(os.path.dirname(label_studio_sso.__file__), "views.py")

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
LS_STATIC_BUILD_DIR="/label-studio/label_studio/core/static_build"
# NOTE: base.html is at /label-studio/label_studio/templates/, NOT core/templates/
LS_TEMPLATE_DIR="/label-studio/label_studio/templates"
LS_BASE_TEMPLATE="$LS_TEMPLATE_DIR/base.html"
CUSTOM_DIR="/label-studio/custom"

# --- Patch: Copy i18n-inject.js to LS static directory ---
I18N_MARKER="SUPERINSIGHT_I18N_PATCH"
I18N_SRC="$CUSTOM_DIR/i18n-inject.js"
I18N_DEST="$LS_STATIC_DIR/i18n-inject.js"

if ! grep -q "$I18N_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    if [ -f "$I18N_SRC" ] && [ -d "$LS_STATIC_DIR" ] && [ -f "$LS_BASE_TEMPLATE" ]; then
        echo "Applying i18n injection patch..."
        cp "$I18N_SRC" "$I18N_DEST"
        # Also copy to static_build (Django collectstatic output) so it's actually served
        [ -d "$LS_STATIC_BUILD_DIR" ] && cp "$I18N_SRC" "$LS_STATIC_BUILD_DIR/i18n-inject.js"
        # Inject <script> tag before </body>
        sed -i "s|</body>|<!-- $I18N_MARKER --><script src=\"/static/i18n-inject.js\"></script>\n</body>|" "$LS_BASE_TEMPLATE"
        echo "i18n injection patch applied"
    else
        echo "ERROR: i18n patch failed - source ($I18N_SRC), static dir ($LS_STATIC_DIR), or template ($LS_BASE_TEMPLATE) not found"
    fi
else
    echo "i18n injection patch already applied, skipping"
fi

# --- Patch: Copy branding.css to LS static directory ---
CSS_MARKER="SUPERINSIGHT_BRANDING_CSS_PATCH"
CSS_SRC="$CUSTOM_DIR/branding.css"
CSS_DEST="$LS_STATIC_DIR/branding.css"

if ! grep -q "$CSS_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    if [ -f "$CSS_SRC" ] && [ -d "$LS_STATIC_DIR" ] && [ -f "$LS_BASE_TEMPLATE" ]; then
        echo "Applying branding CSS patch..."
        cp "$CSS_SRC" "$CSS_DEST"
        # Also copy to static_build (Django collectstatic output) so it's actually served
        [ -d "$LS_STATIC_BUILD_DIR" ] && cp "$CSS_SRC" "$LS_STATIC_BUILD_DIR/branding.css"
        # Inject <link> tag before </head>
        sed -i "s|</head>|<!-- $CSS_MARKER --><link rel=\"stylesheet\" href=\"/static/branding.css\">\n</head>|" "$LS_BASE_TEMPLATE"
        echo "Branding CSS patch applied"
    else
        echo "ERROR: branding CSS patch failed - source ($CSS_SRC), static dir ($LS_STATIC_DIR), or template ($LS_BASE_TEMPLATE) not found"
    fi
else
    echo "Branding CSS patch already applied, skipping"
fi

# --- Patch: Copy favicon to LS static directory ---
FAVICON_MARKER="SUPERINSIGHT_FAVICON_PATCH"
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
TITLE_MARKER="SUPERINSIGHT_TITLE_PATCH"

if ! grep -q "$TITLE_MARKER" "$LS_BASE_TEMPLATE" 2>/dev/null; then
    echo "Applying global brand replacement across all templates..."
    # Replace "Label Studio" in ALL HTML templates (title tags, text content, etc.)
    find /label-studio/label_studio -name "*.html" -exec \
        sed -i 's|Label Studio|问视间|g' {} \;
    # Add marker to base template so we don't re-run
    sed -i "s|</head>|<!-- $TITLE_MARKER -->\n</head>|" "$LS_BASE_TEMPLATE"
    echo "Global brand replacement applied"
else
    echo "Global brand replacement already applied, skipping"
fi

# --- NOTE: React bundle patching removed ---
# sed on minified JS bundles can corrupt them (different byte length for
# multi-byte UTF-8 chars breaks source maps & may crash the app).
# Brand replacement for the React SPA is handled entirely by:
#   1. branding.css  — hides SVG logo via CSS, injects brand text via ::before
#   2. i18n-inject.js — replaces text nodes + MutationObserver for dynamic content

# --- Patch simple.html: inject branding CSS + i18n JS (it extends different base) ---
LS_SIMPLE_TEMPLATE="$LS_TEMPLATE_DIR/simple.html"
if [ -f "$LS_SIMPLE_TEMPLATE" ] && ! grep -q "branding.css" "$LS_SIMPLE_TEMPLATE" 2>/dev/null; then
    echo "Patching simple.html with branding assets..."
    sed -i 's|</head>|<link rel="stylesheet" href="/static/branding.css">\n</head>|' "$LS_SIMPLE_TEMPLATE"
    sed -i 's|</body>|<script src="/static/i18n-inject.js"></script>\n</body>|' "$LS_SIMPLE_TEMPLATE"
    echo "simple.html patched"
fi

# --- Patch user_base.html templates ---
find /label-studio/label_studio/users -name "*.html" -exec grep -l "</head>" {} \; 2>/dev/null | while read tpl; do
    if ! grep -q "branding.css" "$tpl" 2>/dev/null; then
        sed -i 's|</head>|<link rel="stylesheet" href="/static/branding.css">\n</head>|' "$tpl"
        sed -i 's|</body>|<script src="/static/i18n-inject.js"></script>\n</body>|' "$tpl" 2>/dev/null
        echo "Patched: $tpl"
    fi
done

# --- Always ensure custom static files are in static_build (Django's served directory) ---
if [ -d "$LS_STATIC_BUILD_DIR" ]; then
    [ -f "$CUSTOM_DIR/i18n-inject.js" ] && cp "$CUSTOM_DIR/i18n-inject.js" "$LS_STATIC_BUILD_DIR/i18n-inject.js"
    [ -f "$CUSTOM_DIR/branding.css" ] && cp "$CUSTOM_DIR/branding.css" "$LS_STATIC_BUILD_DIR/branding.css"
    echo "Custom static files synced to static_build"
fi

# Run original entrypoint
exec /label-studio/deploy/docker-entrypoint.sh "$@"
