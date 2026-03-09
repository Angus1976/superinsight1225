"""
AI Trial Service for Data Lifecycle Management

Enables AI assistants to perform trial calculations on data at any
lifecycle stage. Provides read-only data access, performance metrics
calculation, trial comparison, and cancellation support.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import copy
import hashlib
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    TrialStatus,
    DataStage,
    ResourceType,
    OperationType,
    OperationResult,
    Action,
)
from src.services.audit_logger import AuditLogger


class TrialConfig:
    """Configuration for creating an AI trial."""

    def __init__(
        self,
        name: str,
        data_stage: DataStage,
        model_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        sample_size: Optional[int] = None,
    ):
        self.name = name
        self.data_stage = data_stage
        self.model_name = model_name
        self.parameters = parameters or {}
        self.sample_size = sample_size


class TrialResult:
    """Result of a completed AI trial."""

    def __init__(
        self,
        trial_id: str,
        metrics: Dict[str, float],
        predictions: List[Dict],
        execution_time: float,
        data_quality_score: float,
        completed_at: Optional[datetime] = None,
    ):
        self.trial_id = trial_id
        self.metrics = metrics
        self.predictions = predictions
        self.execution_time = execution_time
        self.data_quality_score = data_quality_score
        self.completed_at = completed_at or datetime.utcnow()


class Trial:
    """In-memory AI trial tracking."""

    def __init__(
        self,
        id: str,
        config: TrialConfig,
        status: TrialStatus = TrialStatus.CREATED,
        created_by: str = "",
        created_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[TrialResult] = None,
        error: Optional[str] = None,
        data_snapshot: Optional[List[Dict]] = None,
    ):
        self.id = id
        self.config = config
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.started_at = started_at
        self.completed_at = completed_at
        self.result = result
        self.error = error
        self.data_snapshot = data_snapshot


class ComparisonResult:
    """Result of comparing multiple trials."""

    def __init__(
        self,
        trial_ids: List[str],
        metrics_comparison: List[Dict[str, Any]],
        best_trial_id: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ):
        self.trial_ids = trial_ids
        self.metrics_comparison = metrics_comparison
        self.best_trial_id = best_trial_id
        self.summary = summary or {}


class AITrialService:
    """
    AI Trial Service for performing trial calculations on data.

    Uses in-memory dict tracking (same pattern as EnhancementService).
    All data access is read-only — source data is deep-copied into
    a snapshot before any trial execution.

    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """

    def __init__(self, db: Session):
        self.db = db
        self.audit_logger = AuditLogger(db)
        self._trials: Dict[str, Trial] = {}

    # ================================================================
    # Public API
    # ================================================================

    def create_trial(
        self, config: TrialConfig, created_by: str
    ) -> Trial:
        """
        Create a new AI trial.

        Validates: Requirements 7.2
        """
        if not config.name or not config.name.strip():
            raise ValueError("Trial name is required")
        if not config.model_name or not config.model_name.strip():
            raise ValueError("Model name is required")
        if not created_by or not created_by.strip():
            raise ValueError("created_by is required")
        if config.sample_size is not None and config.sample_size < 1:
            raise ValueError("sample_size must be at least 1")

        trial_id = str(uuid4())
        trial = Trial(
            id=trial_id,
            config=config,
            status=TrialStatus.CREATED,
            created_by=created_by,
        )
        self._trials[trial_id] = trial

        self.audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=created_by,
            resource_type=ResourceType.TRIAL,
            resource_id=trial_id,
            action=Action.TRIAL,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                "action": "create_trial",
                "name": config.name,
                "data_stage": config.data_stage.value,
                "model_name": config.model_name,
            },
        )
        return trial

    def execute_trial(
        self,
        trial_id: str,
        source_data: List[Dict[str, Any]],
    ) -> TrialResult:
        """
        Execute an AI trial on a read-only snapshot of source data.

        Takes a deep copy of source_data to guarantee immutability.

        Validates: Requirements 7.1, 7.3, 7.5
        """
        trial = self._get_trial(trial_id)
        if trial.status != TrialStatus.CREATED:
            raise ValueError(
                f"Cannot execute trial: status is {trial.status.value}"
            )

        # Deep-copy source data for immutability (Req 7.1, 7.5)
        trial.data_snapshot = copy.deepcopy(source_data)
        trial.status = TrialStatus.RUNNING
        trial.started_at = datetime.utcnow()

        start_time = time.monotonic()
        try:
            # Apply sample_size limit
            data = trial.data_snapshot
            if trial.config.sample_size and len(data) > trial.config.sample_size:
                data = data[: trial.config.sample_size]

            predictions = self._generate_predictions(
                data, trial.config.model_name, trial.config.parameters
            )
            metrics = self._calculate_metrics(data, predictions)
            execution_time = time.monotonic() - start_time
            data_quality = self._assess_data_quality(data)

            result = TrialResult(
                trial_id=trial_id,
                metrics=metrics,
                predictions=predictions,
                execution_time=round(execution_time, 4),
                data_quality_score=data_quality,
            )

            trial.status = TrialStatus.COMPLETED
            trial.completed_at = datetime.utcnow()
            trial.result = result

            self.audit_logger.log_operation(
                operation_type=OperationType.READ,
                user_id=trial.created_by,
                resource_type=ResourceType.TRIAL,
                resource_id=trial_id,
                action=Action.TRIAL,
                result=OperationResult.SUCCESS,
                duration=int(execution_time * 1000),
                details={
                    "action": "execute_trial",
                    "data_stage": trial.config.data_stage.value,
                    "sample_count": len(data),
                    "accuracy": metrics.get("accuracy", 0),
                },
            )
            return result

        except Exception as e:
            trial.status = TrialStatus.FAILED
            trial.error = str(e)
            trial.completed_at = datetime.utcnow()

            self.audit_logger.log_operation(
                operation_type=OperationType.READ,
                user_id=trial.created_by,
                resource_type=ResourceType.TRIAL,
                resource_id=trial_id,
                action=Action.TRIAL,
                result=OperationResult.FAILURE,
                duration=0,
                error=str(e),
                details={"action": "execute_trial_failed"},
            )
            raise

    def get_trial_result(self, trial_id: str) -> TrialResult:
        """
        Get the result of a completed trial.

        Validates: Requirements 7.6
        """
        trial = self._get_trial(trial_id)
        if trial.status != TrialStatus.COMPLETED:
            raise ValueError(
                f"Trial not completed: status is {trial.status.value}"
            )
        if trial.result is None:
            raise ValueError("Trial has no result")
        return trial.result

    def compare_trials(self, trial_ids: List[str]) -> ComparisonResult:
        """
        Compare multiple completed trials side-by-side.

        Validates: Requirements 7.4
        """
        if len(trial_ids) < 2:
            raise ValueError("At least 2 trial IDs required for comparison")

        metrics_comparison: List[Dict[str, Any]] = []
        best_accuracy = -1.0
        best_trial_id: Optional[str] = None

        for tid in trial_ids:
            trial = self._get_trial(tid)
            if trial.status != TrialStatus.COMPLETED or trial.result is None:
                raise ValueError(f"Trial {tid} is not completed")

            entry = {
                "trial_id": tid,
                "name": trial.config.name,
                "data_stage": trial.config.data_stage.value,
                "model_name": trial.config.model_name,
                "metrics": trial.result.metrics,
                "execution_time": trial.result.execution_time,
                "data_quality_score": trial.result.data_quality_score,
            }
            metrics_comparison.append(entry)

            accuracy = trial.result.metrics.get("accuracy", 0)
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_trial_id = tid

        summary = self._build_comparison_summary(metrics_comparison)

        return ComparisonResult(
            trial_ids=trial_ids,
            metrics_comparison=metrics_comparison,
            best_trial_id=best_trial_id,
            summary=summary,
        )

    def cancel_trial(self, trial_id: str) -> None:
        """
        Cancel a created or running trial.

        Validates: Requirements 7.5
        """
        trial = self._get_trial(trial_id)
        if trial.status not in (TrialStatus.CREATED, TrialStatus.RUNNING):
            raise ValueError(
                f"Cannot cancel trial: status is {trial.status.value}"
            )

        trial.status = TrialStatus.FAILED
        trial.error = "Cancelled by user"
        trial.completed_at = datetime.utcnow()

        self.audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=trial.created_by,
            resource_type=ResourceType.TRIAL,
            resource_id=trial_id,
            action=Action.TRIAL,
            result=OperationResult.SUCCESS,
            duration=0,
            details={"action": "cancel_trial"},
        )

    def get_trial(self, trial_id: str) -> Trial:
        """Get a trial by ID."""
        return self._get_trial(trial_id)

    def list_trials(self) -> List[Trial]:
        """List all tracked trials."""
        return list(self._trials.values())

    # ================================================================
    # Internal helpers
    # ================================================================

    def _get_trial(self, trial_id: str) -> Trial:
        trial = self._trials.get(trial_id)
        if not trial:
            raise ValueError(f"Trial {trial_id} not found")
        return trial

    def _generate_predictions(
        self,
        data: List[Dict[str, Any]],
        model_name: str,
        parameters: Dict[str, Any],
    ) -> List[Dict]:
        """
        Simulate AI model predictions based on data quality.

        This is a simulation — real ML is not invoked. Metrics are
        derived deterministically from data content so tests are stable.
        """
        predictions = []
        for idx, item in enumerate(data):
            quality = self._item_quality(item)
            confidence = min(0.5 + quality * 0.5, 1.0)
            predicted_label = "positive" if confidence > 0.6 else "negative"
            actual_label = item.get("label", predicted_label)

            predictions.append(
                {
                    "index": idx,
                    "predicted": predicted_label,
                    "actual": actual_label,
                    "confidence": round(confidence, 4),
                }
            )
        return predictions

    def _calculate_metrics(
        self,
        data: List[Dict[str, Any]],
        predictions: List[Dict],
    ) -> Dict[str, float]:
        """Calculate accuracy, precision, recall, F1 from predictions."""
        if not predictions:
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
            }

        tp = fp = fn = tn = 0
        for pred in predictions:
            p = pred["predicted"]
            a = pred["actual"]
            if p == "positive" and a == "positive":
                tp += 1
            elif p == "positive" and a != "positive":
                fp += 1
            elif p != "positive" and a == "positive":
                fn += 1
            else:
                tn += 1

        total = tp + fp + fn + tn
        accuracy = (tp + tn) / total if total else 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }

    def _assess_data_quality(self, data: List[Dict[str, Any]]) -> float:
        """Assess overall data quality score (0-1)."""
        if not data:
            return 0.0
        total = sum(self._item_quality(item) for item in data)
        return round(total / len(data), 4)

    def _item_quality(self, item: Dict[str, Any]) -> float:
        """Score a single data item's quality based on field richness."""
        if not item:
            return 0.0
        filled = sum(1 for v in item.values() if v is not None and v != "")
        return min(filled / max(len(item), 1), 1.0)

    def _build_comparison_summary(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build aggregate summary across compared trials."""
        metric_keys = ["accuracy", "precision", "recall", "f1_score"]
        summary: Dict[str, Any] = {}
        for key in metric_keys:
            values = [
                e["metrics"].get(key, 0) for e in entries
            ]
            summary[key] = {
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "avg": round(sum(values) / len(values), 4),
            }
        return summary
