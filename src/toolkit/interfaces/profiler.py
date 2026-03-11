"""
DataProfiler interface — orchestrates data profiling.

Analyzes data sources to produce comprehensive DataProfile objects,
generates fingerprints for caching, and estimates processing costs.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.toolkit.models.data_profile import CostEstimate, DataFingerprint, DataProfile


class ProfilingOptions(BaseModel):
    """Options controlling profiling behavior."""

    quick_mode: bool = Field(default=False, description="Only run quick analysis (< 10s)")
    sampling_mode: bool = Field(default=False, description="Use sampling instead of full scan")
    sample_size: int = Field(default=10000, ge=1, description="Number of records to sample")
    timeout_seconds: Optional[int] = Field(
        default=None, ge=1, description="Max profiling time in seconds"
    )


class DataSource(BaseModel):
    """Reference to a data source for profiling."""

    path: Optional[str] = Field(default=None, description="File path or URL")
    content: Optional[bytes] = Field(default=None, description="Raw content bytes")
    name: str = Field(default="unknown", description="Human-readable source name")
    metadata: dict = Field(default_factory=dict, description="Additional source metadata")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DataProfiler(ABC):
    """
    Interface for data profiling.

    Implementations analyze data sources and produce DataProfile objects
    containing type, quality, structure, and semantic information.
    """

    @abstractmethod
    async def analyze_data(
        self, data_source: DataSource, options: Optional[ProfilingOptions] = None
    ) -> DataProfile:
        """
        Analyze a data source and produce a comprehensive profile.

        Args:
            data_source: The data source to analyze.
            options: Optional profiling configuration.

        Returns:
            A DataProfile describing the data source.
        """
        ...

    @abstractmethod
    async def generate_fingerprint(self, data_source: DataSource) -> DataFingerprint:
        """
        Generate a deterministic fingerprint for a data source.

        The same data source must always produce the same fingerprint.

        Args:
            data_source: The data source to fingerprint.

        Returns:
            A DataFingerprint uniquely identifying the data.
        """
        ...

    @abstractmethod
    async def estimate_processing_cost(self, profile: DataProfile) -> CostEstimate:
        """
        Estimate the computational cost of processing a profiled data source.

        Args:
            profile: A previously generated DataProfile.

        Returns:
            A CostEstimate with time, memory, and monetary breakdowns.
        """
        ...
