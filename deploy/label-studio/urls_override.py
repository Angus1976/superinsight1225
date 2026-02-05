# URL patterns for Label Studio SSO
# This file adds SSO endpoints to Label Studio

from django.urls import path, include

# SSO URL patterns to be added
sso_urlpatterns = [
    path('api/sso/', include('label_studio_sso.urls')),
]
