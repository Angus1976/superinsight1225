"""
QualityAnalyzer interface — assesses data quality dimensions.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from pydantic import BaseModel, Field

from src.toolkit.models.data_profile import QualityMetrics


class ConsistencyReport(BaseModel):
    """Report on data consistency issues."""

    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall consistency score")
    issues: List[str] = Field(default_factory=list, description="Detected consistency issues")


class Anomaly(BaseModel):
    """A single detected anomaly in the data."""

    field: str = Field(..., description="Field where anomaly was found")
    row_index: int = Field(..., ge=0, description="Row index of the anomaly")
    value: Any = Field(default=None, description="The anomalous value")
    reason: str = Field(default="", description="Why this is considered anomalous")


class QualityAnalyzer(ABC):
    """
    Interface for data quality analysis.

    Implementations assess completeness, consistency, detect anomalies,
    and produce overall quality metrics.
    """

    @abstractmethod
    async def analyze_completeness(self, data: Any) -> float:
        """
        Analyze data completeness (ratio of non-null values).

        Args:
            data: The dataset to analyze.

        Returns:
            Completeness score between 0.0 and 1.0.
        """
        ...

    @abstractmethod
    async def analyze_consistency(self, data: Any) -> ConsistencyReport:
        """
        Analyze data consistency across fields and records.

        Args:
            data: The dataset to analyze.

        Returns:
            A ConsistencyReport with score and issues.
        """
        ...

    @abstractmethod
    async def detect_anomalies(self, data: Any) -> List[Anomaly]:
        """
        Detect anomalous values in the dataset.

        Args:
            data: The dataset to analyze.

        Returns:
            A list of detected Anomaly objects.
        """
        ...

    @abstractmethod
    async def assess_data_quality(self, data: Any) -> QualityMetrics:
        """
        Produce an overall quality assessment combining all dimensions.

        Args:
            data: The dataset to analyze.

        Returns:
            Aggregated QualityMetrics.
        """
        ...
