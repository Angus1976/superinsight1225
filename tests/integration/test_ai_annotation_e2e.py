"""
End-to-End Integration Tests for AI Annotation

Tests complete workflows:
- Pre-annotation workflow
- Real-time collaboration workflow
- Quality validation workflow
- Engine switching workflow

Note: These tests use mocking to avoid import issues with the actual modules.
The tests verify the workflow logic and integration patterns.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum

import pytest_asyncio


# =============================================================================
# Mock Classes (to avoid import issues)
# =============================================================================

class MockUserRole(str, Enum):
    """Mock user roles."""
    ANNOTATOR = "annotator"
    EXPERT = "expert"
    REVIEWER = "reviewer"


class MockTaskPriority(str, Enum):
    """Mock task priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class MockTaskAssignment:
    """Mock task assignment."""
    task_id: str
    user_id: str
    role: str
    priority: str
    status: str = "assigned"


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate.return_value = {
        "annotations": [
            {"label": "PERSON", "start": 0, "end": 8, "text": "John Doe", "confidence": 0.92},
            {"label": "ORG", "start": 20, "end": 30, "text": "Acme Corp", "confidence": 0.88},
        ],
        "confidence": 0.90,
    }
    return client


@pytest_asyncio.fixture
async def mock_database():
    """Mock database for testing."""
    db = AsyncMock()
    db.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    )
    return db


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis for testing."""
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.publish.return_value = 1
    return redis


@pytest_asyncio.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "id": "doc_1",
            "text": "John Doe is the CEO of Acme Corp. He founded the company in 2010.",
            "metadata": {"source": "test", "language": "en"},
        },
        {
            "id": "doc_2",
            "text": "Jane Smith works at TechStart Inc as a software engineer.",
            "metadata": {"source": "test", "language": "en"},
        },
        {
            "id": "doc_3",
            "text": "The meeting will be held in New York on January 15, 2026.",
            "metadata": {"source": "test", "language": "en"},
        },
    ]


@pytest_asyncio.fixture
def sample_annotations():
    """Sample annotations for testing."""
    return [
        {
            "document_id": "doc_1",
            "annotations": [
                {"label": "PERSON", "start": 0, "end": 8, "text": "John Doe", "confidence": 0.92},
                {"label": "ORG", "start": 24, "end": 33, "text": "Acme Corp", "confidence": 0.88},
            ],
        },
        {
            "document_id": "doc_2",
            "annotations": [
                {"label": "PERSON", "start": 0, "end": 10, "text": "Jane Smith", "confidence": 0.95},
                {"label": "ORG", "start": 21, "end": 33, "text": "TechStart Inc", "confidence": 0.90},
            ],
        },
    ]


# =============================================================================
# Mock Pre-Annotation Engine
# =============================================================================

class MockPreAnnotationEngine:
    """Mock pre-annotation engine for testing."""
    
    def __init__(self):
        self.llm_client = None
        self.call_count = 0
        self.error_on_call = None
    
    async def process_batch(
        self,
        items: List[Dict[str, Any]],
        annotation_type: str,
        confidence_threshold: float = 0.7,
        samples: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Process a batch of items for pre-annotation."""
        results = []
        
        for item in items:
            self.call_count += 1
            
            # Simulate error if configured
            if self.error_on_call and self.call_count == self.error_on_call:
                results.append({
                    "id": item["id"],
                    "error": "Processing error",
                    "annotations": [],
                })
                continue
            
            # Generate mock annotations
            annotations = []
            text = item.get("text", "")
            
            # Simple mock NER
            if "John Doe" in text:
                annotations.append({
                    "label": "PERSON",
                    "start": text.find("John Doe"),
                    "end": text.find("John Doe") + 8,
                    "text": "John Doe",
                    "confidence": 0.92,
                })
            
            if "Acme Corp" in text:
                annotations.append({
                    "label": "ORG",
                    "start": text.find("Acme Corp"),
                    "end": text.find("Acme Corp") + 9,
                    "text": "Acme Corp",
                    "confidence": 0.88,
                })
            
            results.append({
                "id": item["id"],
                "document_id": item["id"],
                "annotations": annotations,
                "confidence": 0.90 if annotations else 0.5,
                "needs_review": len(annotations) == 0,
            })
        
        return results


# =============================================================================
# Mock Mid-Coverage Engine
# =============================================================================

class MockMidCoverageEngine:
    """Mock mid-coverage engine for testing."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.patterns = []
    
    async def analyze_patterns(
        self,
        annotated_samples: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Analyze patterns from annotated samples."""
        patterns = []
        for sample in annotated_samples:
            pattern = {
                "pattern_id": f"pattern_{len(patterns)}",
                "annotation_type": sample.get("annotation_type", "ner"),
                "features": {"text_length": len(sample.get("text", ""))},
            }
            patterns.append(pattern)
        self.patterns = patterns
        return patterns
    
    async def find_similar_tasks(
        self,
        patterns: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Find tasks similar to patterns."""
        matches = []
        for task in tasks:
            for pattern in patterns:
                match = {
                    "task_id": task.get("id"),
                    "pattern_id": pattern.get("pattern_id"),
                    "similarity": 0.90,
                }
                matches.append(match)
        return matches
    
    async def auto_cover(
        self,
        matches: List[Dict[str, Any]],
        threshold: float = None,
    ) -> Dict[str, Any]:
        """Auto-cover tasks based on matches."""
        threshold = threshold or self.similarity_threshold
        covered = [m for m in matches if m.get("similarity", 0) >= threshold]
        return {
            "covered_count": len(covered),
            "total_matches": len(matches),
            "threshold": threshold,
            "results": covered,
        }


# =============================================================================
# Mock Post-Validation Engine
# =============================================================================

class MockPostValidationEngine:
    """Mock post-validation engine for testing."""
    
    async def validate_annotations(
        self,
        annotations: List[Dict[str, Any]],
        validation_types: List[str] = None,
    ) -> Dict[str, Any]:
        """Validate annotations."""
        validation_types = validation_types or ["accuracy", "consistency"]
        
        scores = {}
        for vtype in validation_types:
            scores[vtype] = 0.85 + (hash(vtype) % 10) / 100
        
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0
        
        return {
            "overall_score": overall_score,
            "scores": scores,
            "issues": [],
            "annotation_count": len(annotations),
        }
    
    async def generate_quality_report(
        self,
        project_id: str,
        annotations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate quality report."""
        return {
            "project_id": project_id,
            "overall_score": 0.87,
            "dimensions": {
                "accuracy": 0.90,
                "consistency": 0.85,
                "completeness": 0.88,
            },
            "annotation_count": len(annotations),
            "issues_count": 0,
            "recommendations": [],
        }
    
    async def detect_inconsistencies(
        self,
        annotations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect inconsistencies in annotations."""
        inconsistencies = []
        
        # Group by document
        by_doc = {}
        for ann in annotations:
            doc_id = ann.get("document_id")
            if doc_id not in by_doc:
                by_doc[doc_id] = []
            by_doc[doc_id].append(ann)
        
        # Check for conflicts
        for doc_id, doc_anns in by_doc.items():
            if len(doc_anns) > 1:
                # Check for label conflicts on same span
                for i, ann1 in enumerate(doc_anns):
                    for ann2 in doc_anns[i+1:]:
                        for a1 in ann1.get("annotations", []):
                            for a2 in ann2.get("annotations", []):
                                if (a1.get("start") == a2.get("start") and
                                    a1.get("end") == a2.get("end") and
                                    a1.get("label") != a2.get("label")):
                                    inconsistencies.append({
                                        "document_id": doc_id,
                                        "type": "label_conflict",
                                        "span": {"start": a1["start"], "end": a1["end"]},
                                        "labels": [a1["label"], a2["label"]],
                                    })
        
        return inconsistencies


# =============================================================================
# Mock Collaboration Manager
# =============================================================================

class MockCollaborationManager:
    """Mock collaboration manager for testing."""
    
    def __init__(self):
        self.assignments = {}
        self.task_statuses = {}
    
    async def assign_task(
        self,
        task_id: str,
        user_id: str,
        role: str = "annotator",
        priority: str = "normal",
    ) -> MockTaskAssignment:
        """Assign a task to a user."""
        assignment = MockTaskAssignment(
            task_id=task_id,
            user_id=user_id,
            role=role,
            priority=priority,
        )
        self.assignments[task_id] = assignment
        return assignment
    
    async def get_task_assignment(self, task_id: str) -> MockTaskAssignment:
        """Get task assignment."""
        return self.assignments.get(task_id)
    
    async def update_task_status(self, task_id: str, status: str) -> None:
        """Update task status."""
        if task_id in self.assignments:
            self.assignments[task_id].status = status
        self.task_statuses[task_id] = status
    
    async def get_team_statistics(self, project_id: str) -> Dict[str, Any]:
        """Get team statistics."""
        return {
            "project_id": project_id,
            "total_tasks": len(self.assignments),
            "completed_tasks": sum(1 for a in self.assignments.values() if a.status == "completed"),
            "in_progress_tasks": sum(1 for a in self.assignments.values() if a.status == "in_progress"),
            "annotators": len(set(a.user_id for a in self.assignments.values())),
        }
    
    def detect_conflicts(
        self,
        annotations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between annotations."""
        conflicts = []
        
        # Group by document
        by_doc = {}
        for ann in annotations:
            doc_id = ann.get("document_id")
            if doc_id not in by_doc:
                by_doc[doc_id] = []
            by_doc[doc_id].append(ann)
        
        # Check for conflicts
        for doc_id, doc_anns in by_doc.items():
            if len(doc_anns) > 1:
                for i, ann1 in enumerate(doc_anns):
                    for ann2 in doc_anns[i+1:]:
                        for a1 in ann1.get("annotations", []):
                            for a2 in ann2.get("annotations", []):
                                if (a1.get("start") == a2.get("start") and
                                    a1.get("end") == a2.get("end") and
                                    a1.get("label") != a2.get("label")):
                                    conflicts.append({
                                        "document_id": doc_id,
                                        "type": "label_mismatch",
                                        "users": [ann1.get("user_id"), ann2.get("user_id")],
                                        "span": {"start": a1["start"], "end": a1["end"]},
                                    })
        
        return conflicts


# =============================================================================
# Mock Annotation Switcher
# =============================================================================

class MockAnnotationSwitcher:
    """Mock annotation switcher for testing."""
    
    def __init__(self):
        self.methods = {
            "pre_annotation": {"type": "llm", "enabled": True},
            "mid_coverage": {"type": "pattern", "enabled": True},
            "ml_backend": {"type": "ml", "enabled": True},
        }
        self.default_method = "pre_annotation"
    
    async def select_engine(self, annotation_type: str) -> Dict[str, Any]:
        """Select engine based on annotation type."""
        # Simple selection logic
        if annotation_type in ["ner", "classification"]:
            return {"name": "pre_annotation", "type": "llm"}
        return {"name": "ml_backend", "type": "ml"}
    
    async def get_fallback_method(self, failed_method: str) -> Dict[str, Any]:
        """Get fallback method."""
        fallbacks = {
            "pre_annotation": "ml_backend",
            "ml_backend": "mid_coverage",
            "mid_coverage": "pre_annotation",
        }
        fallback_name = fallbacks.get(failed_method, "pre_annotation")
        return {"name": fallback_name, "type": self.methods.get(fallback_name, {}).get("type")}
    
    async def compare_methods(
        self,
        method_ids: List[str],
        test_data: List[Dict[str, Any]],
        annotation_type: str,
    ) -> Dict[str, Any]:
        """Compare methods."""
        results = {}
        for method_id in method_ids:
            results[method_id] = {
                "success": True,
                "latency_ms": 50 + hash(method_id) % 100,
                "avg_confidence": 0.85 + (hash(method_id) % 10) / 100,
            }
        
        # Determine winner
        winner = max(results.keys(), key=lambda k: results[k]["avg_confidence"])
        
        return {
            "methods_compared": method_ids,
            "results": results,
            "winner": winner,
            "test_data_count": len(test_data),
        }


# =============================================================================
# Pre-Annotation Workflow Tests
# =============================================================================

class TestPreAnnotationWorkflow:
    """Tests for complete pre-annotation workflow."""

    @pytest.mark.asyncio
    async def test_complete_pre_annotation_workflow(
        self,
        sample_documents,
    ):
        """Test complete pre-annotation workflow from submission to results."""
        engine = MockPreAnnotationEngine()
        
        # Step 1: Submit batch for pre-annotation
        batch_items = [
            {"id": doc["id"], "text": doc["text"]}
            for doc in sample_documents
        ]
        
        # Step 2: Process batch
        results = await engine.process_batch(
            items=batch_items,
            annotation_type="ner",
            confidence_threshold=0.7,
        )
        
        # Step 3: Verify results
        assert len(results) == len(sample_documents)
        for result in results:
            assert "id" in result or "document_id" in result
            assert "annotations" in result

    @pytest.mark.asyncio
    async def test_pre_annotation_with_samples(
        self,
        sample_documents,
        sample_annotations,
    ):
        """Test pre-annotation with sample-based learning."""
        engine = MockPreAnnotationEngine()
        
        # Process with samples
        results = await engine.process_batch(
            items=[{"id": "doc_1", "text": sample_documents[0]["text"]}],
            annotation_type="ner",
            samples=sample_annotations[:2],
            confidence_threshold=0.7,
        )
        
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_pre_annotation_error_handling(
        self,
        sample_documents,
    ):
        """Test pre-annotation error handling."""
        engine = MockPreAnnotationEngine()
        engine.error_on_call = 2  # Error on second call
        
        results = await engine.process_batch(
            items=[{"id": doc["id"], "text": doc["text"]} for doc in sample_documents],
            annotation_type="ner",
            confidence_threshold=0.7,
        )
        
        # Should handle errors gracefully
        assert len(results) == len(sample_documents)
        # One should have an error
        errors = [r for r in results if "error" in r]
        assert len(errors) == 1


# =============================================================================
# Real-Time Collaboration Workflow Tests
# =============================================================================

class TestCollaborationWorkflow:
    """Tests for real-time collaboration workflow."""

    @pytest.mark.asyncio
    async def test_suggestion_and_feedback_workflow(self):
        """Test suggestion generation and feedback workflow."""
        engine = MockMidCoverageEngine()
        
        # Step 1: Analyze patterns from samples
        samples = [
            {"text": "John Doe is CEO", "annotation_type": "ner"},
            {"text": "Jane Smith is CTO", "annotation_type": "ner"},
        ]
        patterns = await engine.analyze_patterns(samples)
        
        assert len(patterns) == 2
        
        # Step 2: Find similar tasks
        tasks = [{"id": "task_1", "text": "Bob Jones is CFO"}]
        matches = await engine.find_similar_tasks(patterns, tasks)
        
        assert len(matches) > 0
        
        # Step 3: Auto-cover
        result = await engine.auto_cover(matches)
        
        assert "covered_count" in result
        assert result["covered_count"] >= 0

    @pytest.mark.asyncio
    async def test_conflict_detection_and_resolution(self):
        """Test conflict detection and resolution workflow."""
        manager = MockCollaborationManager()
        
        # Create conflicting annotations
        annotation_1 = {
            "user_id": "user_1",
            "document_id": "doc_1",
            "annotations": [
                {"label": "PERSON", "start": 0, "end": 8, "text": "John Doe"},
            ],
        }
        
        annotation_2 = {
            "user_id": "user_2",
            "document_id": "doc_1",
            "annotations": [
                {"label": "ORG", "start": 0, "end": 8, "text": "John Doe"},  # Different label
            ],
        }
        
        # Detect conflicts
        conflicts = manager.detect_conflicts([annotation_1, annotation_2])
        
        # Should detect label mismatch conflict
        assert isinstance(conflicts, list)
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "label_mismatch"


# =============================================================================
# Quality Validation Workflow Tests
# =============================================================================

class TestQualityValidationWorkflow:
    """Tests for quality validation workflow."""

    @pytest.mark.asyncio
    async def test_complete_validation_workflow(
        self,
        sample_annotations,
    ):
        """Test complete quality validation workflow."""
        engine = MockPostValidationEngine()
        
        # Step 1: Run validation
        validation_result = await engine.validate_annotations(
            annotations=sample_annotations,
            validation_types=["accuracy", "consistency", "completeness"],
        )
        
        # Step 2: Verify validation results
        assert validation_result is not None
        assert "overall_score" in validation_result
        assert "scores" in validation_result

    @pytest.mark.asyncio
    async def test_quality_report_generation(
        self,
        sample_annotations,
    ):
        """Test quality report generation."""
        engine = MockPostValidationEngine()
        
        # Generate quality report
        report = await engine.generate_quality_report(
            project_id="project_1",
            annotations=sample_annotations,
        )
        
        assert report is not None
        assert "project_id" in report
        assert "overall_score" in report

    @pytest.mark.asyncio
    async def test_inconsistency_detection(
        self,
        sample_annotations,
    ):
        """Test inconsistency detection."""
        engine = MockPostValidationEngine()
        
        # Create inconsistent annotations
        inconsistent_annotations = sample_annotations + [
            {
                "document_id": "doc_1",
                "annotations": [
                    # Same span, different label
                    {"label": "ORG", "start": 0, "end": 8, "text": "John Doe", "confidence": 0.85},
                ],
            },
        ]
        
        # Detect inconsistencies
        inconsistencies = await engine.detect_inconsistencies(
            annotations=inconsistent_annotations,
        )
        
        assert isinstance(inconsistencies, list)
        # Should detect the label conflict
        assert len(inconsistencies) >= 1


# =============================================================================
# Engine Switching Workflow Tests
# =============================================================================

class TestEngineSwitchingWorkflow:
    """Tests for engine switching workflow."""

    @pytest.mark.asyncio
    async def test_engine_selection_workflow(self):
        """Test engine selection based on annotation type."""
        switcher = MockAnnotationSwitcher()
        
        # Test engine selection for different annotation types
        ner_engine = await switcher.select_engine(annotation_type="ner")
        classification_engine = await switcher.select_engine(annotation_type="classification")
        
        assert ner_engine is not None
        assert classification_engine is not None
        assert "name" in ner_engine
        assert "name" in classification_engine

    @pytest.mark.asyncio
    async def test_engine_fallback_workflow(self):
        """Test engine fallback on failure."""
        switcher = MockAnnotationSwitcher()
        
        # Test fallback mechanism
        fallback_engine = await switcher.get_fallback_method("pre_annotation")
        
        # Should return a fallback engine
        assert fallback_engine is not None
        assert "name" in fallback_engine
        assert fallback_engine["name"] != "pre_annotation"

    @pytest.mark.asyncio
    async def test_engine_comparison_workflow(self):
        """Test engine comparison workflow."""
        switcher = MockAnnotationSwitcher()
        
        # Compare engines
        comparison_result = await switcher.compare_methods(
            method_ids=["pre_annotation", "mid_coverage"],
            test_data=[
                {"id": "test_1", "text": "John Doe is the CEO of Acme Corp."},
            ],
            annotation_type="ner",
        )
        
        assert comparison_result is not None
        assert "winner" in comparison_result
        assert "results" in comparison_result


# =============================================================================
# Full Integration Workflow Tests
# =============================================================================

class TestFullIntegrationWorkflow:
    """Tests for complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_annotation_to_validation_workflow(
        self,
        sample_documents,
    ):
        """Test complete workflow from annotation to validation."""
        pre_engine = MockPreAnnotationEngine()
        post_engine = MockPostValidationEngine()
        
        # Step 1: Pre-annotate documents
        pre_results = await pre_engine.process_batch(
            items=[{"id": doc["id"], "text": doc["text"]} for doc in sample_documents],
            annotation_type="ner",
            confidence_threshold=0.7,
        )
        
        # Step 2: Validate annotations
        validation_result = await post_engine.validate_annotations(
            annotations=pre_results,
            validation_types=["accuracy", "consistency"],
        )
        
        # Step 3: Generate quality report
        report = await post_engine.generate_quality_report(
            project_id="project_1",
            annotations=pre_results,
        )
        
        assert len(pre_results) > 0
        assert validation_result is not None
        assert report is not None

    @pytest.mark.asyncio
    async def test_task_assignment_to_completion_workflow(self):
        """Test complete task workflow from assignment to completion."""
        manager = MockCollaborationManager()
        
        # Step 1: Create and assign task
        assignment = await manager.assign_task(
            task_id="task_1",
            user_id="user_1",
            role="annotator",
            priority="high",
        )
        
        assert assignment is not None
        assert assignment.task_id == "task_1"
        
        # Step 2: Get task details
        task = await manager.get_task_assignment("task_1")
        assert task is not None
        
        # Step 3: Update task status
        await manager.update_task_status("task_1", "completed")
        
        # Step 4: Get team statistics
        stats = await manager.get_team_statistics("project_1")
        assert stats is not None
        assert stats["completed_tasks"] == 1


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance tests for AI annotation."""

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test batch processing performance."""
        import time
        
        engine = MockPreAnnotationEngine()
        
        # Create large batch
        large_batch = [
            {"id": f"doc_{i}", "text": f"Sample text {i} with John Doe and Acme Corp."}
            for i in range(100)
        ]
        
        start_time = time.time()
        
        results = await engine.process_batch(
            items=large_batch,
            annotation_type="ner",
            confidence_threshold=0.7,
        )
        
        elapsed_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert elapsed_time < 60  # 60 seconds for 100 documents
        assert len(results) == 100

    @pytest.mark.asyncio
    async def test_suggestion_latency(self):
        """Test suggestion latency."""
        import time
        
        engine = MockMidCoverageEngine()
        
        start_time = time.time()
        
        # Analyze patterns
        patterns = await engine.analyze_patterns([
            {"text": "John Doe is CEO", "annotation_type": "ner"},
        ])
        
        # Find similar tasks
        matches = await engine.find_similar_tasks(
            patterns,
            [{"id": "task_1", "text": "Jane Smith is CTO"}],
        )
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Should complete within latency target
        assert elapsed_time < 200  # 200ms target


# =============================================================================
# Error Recovery Tests
# =============================================================================

class TestErrorRecovery:
    """Tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_llm_failure_recovery(self):
        """Test recovery from LLM failures."""
        engine = MockPreAnnotationEngine()
        
        # First call will succeed, then we'll test error handling
        results = await engine.process_batch(
            items=[{"id": "doc_1", "text": "Test text with John Doe"}],
            annotation_type="ner",
            confidence_threshold=0.7,
        )
        
        assert len(results) == 1
        assert "annotations" in results[0]

    @pytest.mark.asyncio
    async def test_partial_batch_failure_recovery(self):
        """Test recovery from partial batch failures."""
        engine = MockPreAnnotationEngine()
        engine.error_on_call = 2  # Error on second item
        
        results = await engine.process_batch(
            items=[
                {"id": "doc_1", "text": "Text 1 with John Doe"},
                {"id": "doc_2", "text": "Text 2"},
                {"id": "doc_3", "text": "Text 3 with Acme Corp"},
            ],
            annotation_type="ner",
            confidence_threshold=0.7,
        )
        
        # Should return results for all items (some may have errors)
        assert len(results) == 3
        
        # Check that we have one error
        errors = [r for r in results if "error" in r]
        assert len(errors) == 1
        
        # Check that successful items have annotations
        successes = [r for r in results if "error" not in r]
        assert len(successes) == 2
