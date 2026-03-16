"""
BaseHandler — 所有 request_type Handler 的抽象基类。

每种 request_type（query / chat / decision / skill）实现此接口，
并注册到 RequestRouter 即可接入统一服务引擎。
"""

from abc import ABC, abstractmethod

from src.service_engine.schemas import ServiceRequest, ServiceResponse


class BaseHandler(ABC):
    """Abstract base class for all request type handlers."""

    @abstractmethod
    async def validate(self, request: ServiceRequest) -> None:
        """Validate type-specific parameters. Raise on failure."""
        ...

    @abstractmethod
    async def build_context(self, request: ServiceRequest) -> dict:
        """Build context for request processing."""
        ...

    @abstractmethod
    async def execute(
        self, request: ServiceRequest, context: dict
    ) -> ServiceResponse:
        """Execute the request and return response."""
        ...
