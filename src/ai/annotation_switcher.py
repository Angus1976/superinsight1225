"""
Annotation Method Switcher for SuperInsight platform.

Provides unified interface for switching between different AI annotation methods
including LLM, ML Backend, Argilla, and third-party tools.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from uuid import uuid4
from abc import ABC, abstractmethod
from enum import Enum

from src.ai.annotation_plugin_interface import (
    AnnotationType,
    AnnotationTask,
    AnnotationResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Annotation Method Types
# ============================================================================

class AnnotationMethodType(str, Enum):
    """Available annotation method types."""
    LLM = "llm"
    ML_BACKEND = "ml_backend"
    ARGILLA = "argilla"
    THIRD_PARTY = "third_party"
    CUSTOM = "custom"


class MethodInfo:
    """Information about an annotation method."""
    
    def __init__(
        self,
        name: str,
        method_type: AnnotationMethodType,
        description: str = "",
        supported_types: Optional[List[AnnotationType]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.method_type = method_type
        self.description = description
        self.supported_types = supported_types or list(AnnotationType)
        self.config = config or {}
        self.enabled = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "method_type": self.method_type.value,
            "description": self.description,
            "supported_types": [t.value for t in self.supported_types],
            "config": self.config,
            "enabled": self.enabled,
        }


class MethodStats:
    """Statistics for an annotation method."""
    
    def __init__(self, name: str):
        self.name = name
        self.total_calls = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_tasks = 0
        self.total_latency_ms = 0.0
        self.latencies: List[float] = []
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls
    
    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)
    
    def record_call(
        self,
        success: bool,
        task_count: int,
        latency_ms: float,
    ) -> None:
        """Record a method call."""
        self.total_calls += 1
        self.total_tasks += task_count
        self.total_latency_ms += latency_ms
        self.latencies.append(latency_ms)
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # Keep only last 1000 latencies
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "total_tasks": self.total_tasks,
            "avg_latency_ms": self.avg_latency_ms,
        }


# ============================================================================
# Annotation Method Interface
# ============================================================================

class AnnotationMethod(ABC):
    """Abstract base class for annotation methods."""
    
    @abstractmethod
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        **kwargs
    ) -> List[AnnotationResult]:
        """
        Execute annotation.
        
        Args:
            tasks: List of tasks to annotate
            annotation_type: Type of annotation
            **kwargs: Additional parameters
            
        Returns:
            List of annotation results
        """
        pass
    
    @abstractmethod
    def get_info(self) -> MethodInfo:
        """Get method information."""
        pass
    
    def supports_type(self, annotation_type: AnnotationType) -> bool:
        """Check if method supports annotation type."""
        info = self.get_info()
        return annotation_type in info.supported_types


# ============================================================================
# Built-in Method Implementations
# ============================================================================

class LLMAnnotationMethod(AnnotationMethod):
    """LLM-based annotation method."""
    
    def __init__(self, llm_service: Optional[Any] = None):
        self.llm_service = llm_service
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        **kwargs
    ) -> List[AnnotationResult]:
        """Annotate using LLM."""
        results = []
        
        for task in tasks:
            # Placeholder - would call actual LLM service
            result = AnnotationResult(
                task_id=task.id,
                annotation_data={"label": "llm_generated"},
                confidence=0.8,
                method_used="llm",
            )
            results.append(result)
        
        return results
    
    def get_info(self) -> MethodInfo:
        return MethodInfo(
            name="llm",
            method_type=AnnotationMethodType.LLM,
            description="LLM-based annotation using configured language models",
            supported_types=list(AnnotationType),
        )


class MLBackendAnnotationMethod(AnnotationMethod):
    """ML Backend annotation method (Label Studio compatible)."""
    
    def __init__(self, ml_backend_url: Optional[str] = None):
        self.ml_backend_url = ml_backend_url
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        **kwargs
    ) -> List[AnnotationResult]:
        """Annotate using ML Backend."""
        results = []
        
        for task in tasks:
            # Placeholder - would call actual ML Backend
            result = AnnotationResult(
                task_id=task.id,
                annotation_data={"label": "ml_backend_generated"},
                confidence=0.75,
                method_used="ml_backend",
            )
            results.append(result)
        
        return results
    
    def get_info(self) -> MethodInfo:
        return MethodInfo(
            name="ml_backend",
            method_type=AnnotationMethodType.ML_BACKEND,
            description="Label Studio ML Backend integration",
            supported_types=[
                AnnotationType.TEXT_CLASSIFICATION,
                AnnotationType.NER,
                AnnotationType.SENTIMENT,
            ],
        )


class ArgillaAnnotationMethod(AnnotationMethod):
    """Argilla annotation method."""
    
    def __init__(self, argilla_client: Optional[Any] = None):
        self.argilla_client = argilla_client
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        **kwargs
    ) -> List[AnnotationResult]:
        """Annotate using Argilla."""
        results = []
        
        for task in tasks:
            # Placeholder - would call actual Argilla
            result = AnnotationResult(
                task_id=task.id,
                annotation_data={"label": "argilla_generated"},
                confidence=0.85,
                method_used="argilla",
            )
            results.append(result)
        
        return results
    
    def get_info(self) -> MethodInfo:
        return MethodInfo(
            name="argilla",
            method_type=AnnotationMethodType.ARGILLA,
            description="Argilla data labeling platform integration",
            supported_types=list(AnnotationType),
        )


# ============================================================================
# Method Comparison Report
# ============================================================================

class MethodComparisonReport:
    """Report comparing multiple annotation methods."""
    
    def __init__(self):
        self.report_id = str(uuid4())
        self.created_at = datetime.utcnow()
        self.methods_compared: List[str] = []
        self.task_count = 0
        self.results: Dict[str, Dict[str, Any]] = {}
        self.winner: Optional[str] = None
    
    def add_method_result(
        self,
        method_name: str,
        success: bool,
        latency_ms: float,
        avg_confidence: float,
        results: List[AnnotationResult],
    ) -> None:
        """Add results for a method."""
        self.methods_compared.append(method_name)
        self.results[method_name] = {
            "success": success,
            "latency_ms": latency_ms,
            "avg_confidence": avg_confidence,
            "result_count": len(results),
        }
    
    def determine_winner(self) -> str:
        """Determine the best method based on results."""
        if not self.results:
            return ""
        
        # Score based on success, confidence, and latency
        scores = {}
        for name, data in self.results.items():
            if not data["success"]:
                scores[name] = 0
                continue
            
            # Higher confidence is better, lower latency is better
            confidence_score = data["avg_confidence"] * 100
            latency_score = max(0, 100 - data["latency_ms"] / 10)
            scores[name] = confidence_score + latency_score
        
        self.winner = max(scores, key=scores.get) if scores else ""
        return self.winner
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "created_at": self.created_at.isoformat(),
            "methods_compared": self.methods_compared,
            "task_count": self.task_count,
            "results": self.results,
            "winner": self.winner,
        }


# ============================================================================
# Method Switch Log
# ============================================================================

class MethodSwitchLog:
    """Log entry for method switches."""
    
    def __init__(
        self,
        from_method: str,
        to_method: str,
        reason: str = "",
    ):
        self.id = str(uuid4())
        self.from_method = from_method
        self.to_method = to_method
        self.reason = reason
        self.switched_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_method": self.from_method,
            "to_method": self.to_method,
            "reason": self.reason,
            "switched_at": self.switched_at.isoformat(),
        }


# ============================================================================
# Annotation Method Switcher
# ============================================================================

class AnnotationMethodSwitcher:
    """
    Annotation Method Switcher.
    
    Provides unified interface for switching between different AI annotation
    methods with hot-switching, comparison, and logging capabilities.
    """
    
    def __init__(self):
        """Initialize the method switcher."""
        self._methods: Dict[str, AnnotationMethod] = {}
        self._stats: Dict[str, MethodStats] = {}
        self._default_method: str = "llm"
        self._switch_logs: List[MethodSwitchLog] = []
        self._lock = asyncio.Lock()
        
        # Register built-in methods
        self._register_builtin_methods()
    
    def _register_builtin_methods(self) -> None:
        """Register built-in annotation methods."""
        self.register_method("llm", LLMAnnotationMethod())
        self.register_method("ml_backend", MLBackendAnnotationMethod())
        self.register_method("argilla", ArgillaAnnotationMethod())
    
    # ========================================================================
    # Method Registration
    # ========================================================================
    
    def register_method(
        self,
        name: str,
        method: AnnotationMethod,
    ) -> None:
        """
        Register an annotation method.
        
        Args:
            name: Method name
            method: Method instance
        """
        self._methods[name] = method
        self._stats[name] = MethodStats(name)
        logger.info(f"Registered annotation method: {name}")
    
    def unregister_method(self, name: str) -> None:
        """
        Unregister an annotation method.
        
        Args:
            name: Method name
        """
        if name in self._methods:
            del self._methods[name]
            if name in self._stats:
                del self._stats[name]
            logger.info(f"Unregistered annotation method: {name}")
    
    # ========================================================================
    # Method Access
    # ========================================================================
    
    def get_method(self, name: str) -> Optional[AnnotationMethod]:
        """
        Get a method by name.
        
        Args:
            name: Method name
            
        Returns:
            AnnotationMethod or None
        """
        return self._methods.get(name)
    
    def list_available_methods(self) -> List[str]:
        """
        List all available method names.
        
        Returns:
            List of method names
        """
        return list(self._methods.keys())
    
    def get_method_info(self, name: str) -> Optional[MethodInfo]:
        """
        Get method information.
        
        Args:
            name: Method name
            
        Returns:
            MethodInfo or None
        """
        method = self._methods.get(name)
        if method:
            return method.get_info()
        return None
    
    def list_methods_info(self) -> List[MethodInfo]:
        """
        List information for all methods.
        
        Returns:
            List of MethodInfo
        """
        return [m.get_info() for m in self._methods.values()]
    
    # ========================================================================
    # Default Method Management
    # ========================================================================
    
    def get_current_method(self) -> str:
        """
        Get current default method name.
        
        Returns:
            Default method name
        """
        return self._default_method
    
    def switch_method(
        self,
        method: str,
        reason: str = "",
    ) -> bool:
        """
        Switch the default method.
        
        Args:
            method: New default method name
            reason: Reason for switching
            
        Returns:
            True if switch successful
        """
        if method not in self._methods:
            logger.warning(f"Cannot switch to unknown method: {method}")
            return False
        
        old_method = self._default_method
        self._default_method = method
        
        # Log the switch
        log = MethodSwitchLog(old_method, method, reason)
        self._switch_logs.append(log)
        
        # Keep only last 1000 logs
        if len(self._switch_logs) > 1000:
            self._switch_logs = self._switch_logs[-1000:]
        
        logger.info(f"Switched default method from {old_method} to {method}")
        return True
    
    def get_switch_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get method switch history.
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of switch log dictionaries
        """
        return [log.to_dict() for log in self._switch_logs[-limit:]]
    
    # ========================================================================
    # Annotation Execution
    # ========================================================================
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        method: Optional[str] = None,
        **kwargs
    ) -> List[AnnotationResult]:
        """
        Execute annotation using specified or default method.
        
        Args:
            tasks: List of tasks to annotate
            annotation_type: Type of annotation
            method: Optional method name (uses default if not specified)
            **kwargs: Additional parameters
            
        Returns:
            List of annotation results
        """
        # Determine method to use (specified method takes priority)
        method_name = method or self._default_method
        
        annotation_method = self._methods.get(method_name)
        if not annotation_method:
            raise ValueError(f"Unknown annotation method: {method_name}")
        
        # Check if method supports annotation type
        if not annotation_method.supports_type(annotation_type):
            raise ValueError(
                f"Method {method_name} does not support {annotation_type}"
            )
        
        start_time = time.time()
        success = False
        
        try:
            results = await annotation_method.annotate(
                tasks, annotation_type, **kwargs
            )
            success = True
            return results
            
        finally:
            # Record statistics
            latency_ms = (time.time() - start_time) * 1000
            if method_name in self._stats:
                self._stats[method_name].record_call(
                    success, len(tasks), latency_ms
                )
    
    # ========================================================================
    # Method Comparison
    # ========================================================================
    
    async def compare_methods(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        methods: Optional[List[str]] = None,
    ) -> MethodComparisonReport:
        """
        Compare multiple annotation methods on the same tasks.
        
        Args:
            tasks: List of tasks to annotate
            annotation_type: Type of annotation
            methods: Optional list of methods to compare (all if not specified)
            
        Returns:
            MethodComparisonReport
        """
        report = MethodComparisonReport()
        report.task_count = len(tasks)
        
        methods_to_compare = methods or list(self._methods.keys())
        
        for method_name in methods_to_compare:
            method = self._methods.get(method_name)
            if not method:
                continue
            
            if not method.supports_type(annotation_type):
                continue
            
            start_time = time.time()
            success = False
            results = []
            avg_confidence = 0.0
            
            try:
                results = await method.annotate(tasks, annotation_type)
                success = True
                
                if results:
                    avg_confidence = sum(r.confidence for r in results) / len(results)
                    
            except Exception as e:
                logger.warning(f"Method {method_name} failed: {e}")
            
            latency_ms = (time.time() - start_time) * 1000
            
            report.add_method_result(
                method_name,
                success,
                latency_ms,
                avg_confidence,
                results,
            )
        
        report.determine_winner()
        return report
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    def get_method_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a method.
        
        Args:
            name: Method name
            
        Returns:
            Statistics dictionary or None
        """
        stats = self._stats.get(name)
        if stats:
            return stats.to_dict()
        return None
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all methods.

        Returns:
            Dictionary mapping method names to statistics
        """
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    # ========================================================================
    # Engine Comparison (Task 11.5)
    # ========================================================================

    async def run_ab_test(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        method_a: str,
        method_b: str,
        sample_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run A/B test comparing two methods on sample data.

        Args:
            tasks: List of tasks to test
            annotation_type: Type of annotation
            method_a: First method name
            method_b: Second method name
            sample_size: Optional sample size (uses all if not specified)

        Returns:
            A/B test results with performance comparison
        """
        # Use sample of tasks if specified
        test_tasks = tasks[:sample_size] if sample_size else tasks

        results = {
            "test_id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "sample_size": len(test_tasks),
            "annotation_type": annotation_type.value,
            "method_a": {"name": method_a},
            "method_b": {"name": method_b},
        }

        # Test method A
        try:
            start_a = time.time()
            results_a = await self.annotate(test_tasks, annotation_type, method=method_a)
            latency_a = (time.time() - start_a) * 1000

            avg_conf_a = sum(r.confidence for r in results_a) / len(results_a) if results_a else 0
            results["method_a"].update({
                "success": True,
                "latency_ms": latency_a,
                "avg_confidence": avg_conf_a,
                "result_count": len(results_a),
            })
        except Exception as e:
            results["method_a"].update({
                "success": False,
                "error": str(e),
            })

        # Test method B
        try:
            start_b = time.time()
            results_b = await self.annotate(test_tasks, annotation_type, method=method_b)
            latency_b = (time.time() - start_b) * 1000

            avg_conf_b = sum(r.confidence for r in results_b) / len(results_b) if results_b else 0
            results["method_b"].update({
                "success": True,
                "latency_ms": latency_b,
                "avg_confidence": avg_conf_b,
                "result_count": len(results_b),
            })
        except Exception as e:
            results["method_b"].update({
                "success": False,
                "error": str(e),
            })

        # Determine winner
        results["recommendation"] = self._determine_ab_winner(
            results["method_a"], results["method_b"]
        )

        return results

    def _determine_ab_winner(
        self,
        result_a: Dict[str, Any],
        result_b: Dict[str, Any],
    ) -> str:
        """Determine A/B test winner based on results."""
        if not result_a.get("success") and not result_b.get("success"):
            return "neither"
        if not result_a.get("success"):
            return result_b.get("name", "method_b")
        if not result_b.get("success"):
            return result_a.get("name", "method_a")

        # Score: 60% confidence, 40% latency (inverse)
        score_a = result_a.get("avg_confidence", 0) * 0.6
        score_b = result_b.get("avg_confidence", 0) * 0.6

        # Normalize latency scores (lower is better)
        lat_a = result_a.get("latency_ms", 1000)
        lat_b = result_b.get("latency_ms", 1000)
        max_lat = max(lat_a, lat_b, 1)
        score_a += (1 - lat_a / max_lat) * 0.4
        score_b += (1 - lat_b / max_lat) * 0.4

        if score_a > score_b:
            return result_a.get("name", "method_a")
        elif score_b > score_a:
            return result_b.get("name", "method_b")
        return "tie"

    def generate_performance_report(
        self,
        methods: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate performance comparison report for methods.

        Args:
            methods: Optional list of methods (all if not specified)

        Returns:
            Performance comparison report
        """
        methods_to_report = methods or list(self._methods.keys())

        report = {
            "report_id": str(uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "methods": {},
            "ranking": [],
        }

        method_scores = []

        for name in methods_to_report:
            stats = self._stats.get(name)
            info = self.get_method_info(name)

            if stats and info:
                method_data = {
                    "name": name,
                    "type": info.method_type.value,
                    "stats": stats.to_dict(),
                    "enabled": info.enabled,
                    "supported_types": [t.value for t in info.supported_types],
                }
                report["methods"][name] = method_data

                # Calculate score for ranking
                score = stats.success_rate * 0.5
                if stats.avg_latency_ms > 0:
                    score += (1 - min(stats.avg_latency_ms, 1000) / 1000) * 0.3
                score += min(stats.total_calls / 100, 1) * 0.2  # Experience factor
                method_scores.append((name, score))

        # Sort by score descending
        method_scores.sort(key=lambda x: x[1], reverse=True)
        report["ranking"] = [name for name, _ in method_scores]

        return report

    # ========================================================================
    # Hot-Reload Support (Task 11.7)
    # ========================================================================

    async def hot_reload_method(
        self,
        name: str,
        new_method: AnnotationMethod,
    ) -> bool:
        """
        Hot-reload a method without service interruption.

        Args:
            name: Method name to reload
            new_method: New method instance

        Returns:
            True if reload successful
        """
        async with self._lock:
            if name not in self._methods:
                logger.warning(f"Cannot hot-reload unknown method: {name}")
                return False

            old_method = self._methods[name]
            old_info = old_method.get_info()
            new_info = new_method.get_info()

            # Preserve statistics
            old_stats = self._stats.get(name)

            # Replace method
            self._methods[name] = new_method

            # Log the reload
            log = MethodSwitchLog(
                f"{name}:v_old",
                f"{name}:v_new",
                reason="hot_reload"
            )
            self._switch_logs.append(log)

            logger.info(f"Hot-reloaded method: {name}")
            return True

    async def add_method_dynamically(
        self,
        name: str,
        method: AnnotationMethod,
    ) -> bool:
        """
        Dynamically add a new method at runtime.

        Args:
            name: Method name
            method: Method instance

        Returns:
            True if addition successful
        """
        async with self._lock:
            if name in self._methods:
                logger.warning(f"Method {name} already exists, use hot_reload instead")
                return False

            self._methods[name] = method
            self._stats[name] = MethodStats(name)

            logger.info(f"Dynamically added method: {name}")
            return True

    async def remove_method_dynamically(
        self,
        name: str,
    ) -> bool:
        """
        Dynamically remove a method at runtime.

        Args:
            name: Method name

        Returns:
            True if removal successful
        """
        async with self._lock:
            if name not in self._methods:
                logger.warning(f"Method {name} does not exist")
                return False

            # Don't allow removing the default method
            if name == self._default_method:
                logger.warning(f"Cannot remove default method: {name}")
                return False

            del self._methods[name]
            if name in self._stats:
                del self._stats[name]

            logger.info(f"Dynamically removed method: {name}")
            return True

    # ========================================================================
    # Format Compatibility (Task 11.9)
    # ========================================================================

    def normalize_annotation_format(
        self,
        annotation_data: Dict[str, Any],
        source_format: str,
        target_format: str = "standard",
    ) -> Dict[str, Any]:
        """
        Normalize annotation data from one format to another.

        Supported formats:
        - standard: SuperInsight internal format
        - label_studio: Label Studio JSON format
        - argilla: Argilla record format
        - spacy: spaCy Doc format
        - brat: BRAT standoff format

        Args:
            annotation_data: Input annotation data
            source_format: Source format name
            target_format: Target format name

        Returns:
            Normalized annotation data
        """
        # First convert to standard format if needed
        if source_format != "standard":
            annotation_data = self._convert_to_standard(annotation_data, source_format)

        # Then convert to target format if needed
        if target_format != "standard":
            annotation_data = self._convert_from_standard(annotation_data, target_format)

        return annotation_data

    def _convert_to_standard(
        self,
        data: Dict[str, Any],
        source_format: str,
    ) -> Dict[str, Any]:
        """Convert from source format to standard format."""
        converters = {
            "label_studio": self._from_label_studio,
            "argilla": self._from_argilla,
            "spacy": self._from_spacy,
            "brat": self._from_brat,
        }

        converter = converters.get(source_format)
        if converter:
            return converter(data)

        logger.warning(f"Unknown source format: {source_format}, returning as-is")
        return data

    def _convert_from_standard(
        self,
        data: Dict[str, Any],
        target_format: str,
    ) -> Dict[str, Any]:
        """Convert from standard format to target format."""
        converters = {
            "label_studio": self._to_label_studio,
            "argilla": self._to_argilla,
            "spacy": self._to_spacy,
            "brat": self._to_brat,
        }

        converter = converters.get(target_format)
        if converter:
            return converter(data)

        logger.warning(f"Unknown target format: {target_format}, returning as-is")
        return data

    def _from_label_studio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Label Studio format to standard."""
        result = {
            "id": data.get("id", str(uuid4())),
            "text": data.get("data", {}).get("text", ""),
            "annotations": [],
        }

        for annotation in data.get("annotations", []):
            for ann_result in annotation.get("result", []):
                if ann_result.get("type") == "labels":
                    value = ann_result.get("value", {})
                    result["annotations"].append({
                        "label": value.get("labels", [""])[0],
                        "start": value.get("start", 0),
                        "end": value.get("end", 0),
                        "text": value.get("text", ""),
                    })

        return result

    def _to_label_studio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert standard format to Label Studio."""
        result = {
            "id": data.get("id"),
            "data": {"text": data.get("text", "")},
            "annotations": [{
                "result": []
            }]
        }

        for i, ann in enumerate(data.get("annotations", [])):
            result["annotations"][0]["result"].append({
                "id": f"result_{i}",
                "type": "labels",
                "value": {
                    "start": ann.get("start", 0),
                    "end": ann.get("end", 0),
                    "text": ann.get("text", ""),
                    "labels": [ann.get("label", "")],
                },
                "from_name": "label",
                "to_name": "text",
            })

        return result

    def _from_argilla(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Argilla format to standard."""
        result = {
            "id": data.get("id", str(uuid4())),
            "text": data.get("text", ""),
            "annotations": [],
        }

        for entity in data.get("prediction", {}).get("entities", []):
            result["annotations"].append({
                "label": entity.get("label", ""),
                "start": entity.get("start", 0),
                "end": entity.get("end", 0),
                "text": entity.get("text", ""),
            })

        return result

    def _to_argilla(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert standard format to Argilla."""
        result = {
            "id": data.get("id"),
            "text": data.get("text", ""),
            "prediction": {
                "entities": []
            }
        }

        for ann in data.get("annotations", []):
            result["prediction"]["entities"].append({
                "label": ann.get("label", ""),
                "start": ann.get("start", 0),
                "end": ann.get("end", 0),
                "text": ann.get("text", ""),
            })

        return result

    def _from_spacy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert spaCy format to standard."""
        result = {
            "id": data.get("id", str(uuid4())),
            "text": data.get("text", ""),
            "annotations": [],
        }

        for ent in data.get("ents", []):
            text = data.get("text", "")[ent.get("start", 0):ent.get("end", 0)]
            result["annotations"].append({
                "label": ent.get("label", ""),
                "start": ent.get("start", 0),
                "end": ent.get("end", 0),
                "text": text,
            })

        return result

    def _to_spacy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert standard format to spaCy."""
        result = {
            "text": data.get("text", ""),
            "ents": []
        }

        for ann in data.get("annotations", []):
            result["ents"].append({
                "label": ann.get("label", ""),
                "start": ann.get("start", 0),
                "end": ann.get("end", 0),
            })

        return result

    def _from_brat(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BRAT format to standard."""
        result = {
            "id": data.get("id", str(uuid4())),
            "text": data.get("text", ""),
            "annotations": [],
        }

        for entity in data.get("entities", []):
            # BRAT format: [[start, end], label, text]
            spans = entity.get("spans", [[0, 0]])
            result["annotations"].append({
                "label": entity.get("label", ""),
                "start": spans[0][0] if spans else 0,
                "end": spans[0][1] if spans else 0,
                "text": entity.get("text", ""),
            })

        return result

    def _to_brat(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert standard format to BRAT."""
        result = {
            "text": data.get("text", ""),
            "entities": []
        }

        for i, ann in enumerate(data.get("annotations", [])):
            result["entities"].append({
                "id": f"T{i+1}",
                "label": ann.get("label", ""),
                "spans": [[ann.get("start", 0), ann.get("end", 0)]],
                "text": ann.get("text", ""),
            })

        return result

    def migrate_annotations_on_switch(
        self,
        annotations: List[Dict[str, Any]],
        from_method: str,
        to_method: str,
    ) -> List[Dict[str, Any]]:
        """
        Migrate annotations when switching between methods.

        Args:
            annotations: List of annotations to migrate
            from_method: Source method name
            to_method: Target method name

        Returns:
            Migrated annotations
        """
        # Determine source and target formats based on method type
        format_map = {
            "llm": "standard",
            "ml_backend": "label_studio",
            "argilla": "argilla",
        }

        source_format = format_map.get(from_method, "standard")
        target_format = format_map.get(to_method, "standard")

        if source_format == target_format:
            return annotations

        migrated = []
        for ann in annotations:
            migrated.append(
                self.normalize_annotation_format(ann, source_format, target_format)
            )

        logger.info(
            f"Migrated {len(annotations)} annotations from {from_method} to {to_method}"
        )
        return migrated

    # ========================================================================
    # Fallback Management
    # ========================================================================

    def get_fallback_method(
        self,
        failed_method: str,
        annotation_type: AnnotationType,
    ) -> Optional[str]:
        """
        Get fallback method when primary method fails.

        Args:
            failed_method: Method that failed
            annotation_type: Annotation type being performed

        Returns:
            Fallback method name or None
        """
        # Priority order for fallbacks
        fallback_priority = ["llm", "ml_backend", "argilla", "custom"]

        for method_name in fallback_priority:
            if method_name == failed_method:
                continue

            method = self._methods.get(method_name)
            if method and method.supports_type(annotation_type):
                info = method.get_info()
                if info.enabled:
                    return method_name

        return None


# ============================================================================
# Alias for backward compatibility
# ============================================================================

AnnotationSwitcher = AnnotationMethodSwitcher


# ============================================================================
# Singleton Instance
# ============================================================================

_switcher_instance: Optional[AnnotationMethodSwitcher] = None


def get_method_switcher() -> AnnotationMethodSwitcher:
    """
    Get or create the method switcher instance.
    
    Returns:
        AnnotationMethodSwitcher instance
    """
    global _switcher_instance
    
    if _switcher_instance is None:
        _switcher_instance = AnnotationMethodSwitcher()
    
    return _switcher_instance
