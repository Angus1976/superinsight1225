"""
Third-party annotation tool adapters.

This package contains adapters for integrating with external annotation tools
like Prodigy, Doccano, CVAT, Labelbox, and Scale AI.
"""

from .base_adapter import BaseAnnotationAdapter
from .rest_adapter import RESTAnnotationAdapter
from .prodigy_adapter import ProdigyAdapter, create_prodigy_adapter

__all__ = [
    "BaseAnnotationAdapter",
    "RESTAnnotationAdapter",
    "ProdigyAdapter",
    "create_prodigy_adapter",
]
