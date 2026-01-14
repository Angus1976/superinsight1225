"""
Third-party Text-to-SQL tool adapters.

This module provides adapters for various third-party Text-to-SQL tools:
- REST API adapter for HTTP-based services
- gRPC adapter for gRPC-based services
- Vanna.ai adapter example
"""

from .rest_adapter import RESTAPIPlugin
from .grpc_adapter import GRPCPlugin

__all__ = [
    "RESTAPIPlugin",
    "GRPCPlugin",
]
