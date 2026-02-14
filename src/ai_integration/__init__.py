"""
AI Application Integration module for SuperInsight Platform.

This module provides integration with AI assistant gateways like OpenClaw,
enabling conversational access to governed data through custom skills.
"""

from src.ai_integration.auth import (
    APICredentials,
    generate_api_key,
    generate_api_secret,
    hash_credential,
    verify_credential,
    generate_credentials,
    validate_credentials,
)

__all__ = [
    "APICredentials",
    "generate_api_key",
    "generate_api_secret",
    "hash_credential",
    "verify_credential",
    "generate_credentials",
    "validate_credentials",
]
