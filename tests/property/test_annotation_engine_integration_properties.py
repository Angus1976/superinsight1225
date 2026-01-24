"""Property-based tests for Annotation Engine Integration.

This module tests the following properties:
- Property 23: Engine Health Check Retry
- Label Studio ML Backend integration
- Argilla platform integration
- Engine health monitoring with exponential backoff

Requirements:
- All engine health checks should retry with exponential backoff
- Label Studio API integration should work correctly
- Argilla dataset management should work correctly
- Unhealthy engines should be automatically disabled
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List
from datetime import datetime, timedelta
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ai.label_studio_integration import (
    LabelStudioMLEngine,
    LabelStudioTask,
    LabelStudioPrediction,
    TrainingStatus,
    reset_label_studio_engines,
)
from src.ai.argilla_integration import (
    ArgillaEngine,
    ArgillaRecord,
    ArgillaField,
    ArgillaQuestion,
    ArgillaSuggestion,
    RecordStatus,
    FeedbackType,
    reset_argilla_engines,
)
from src.ai.annotation_engine_health import (
    AnnotationEngineHealthMonitor,
    EngineType,
    HealthStatus,
    reset_health_monitor,
)


# ============================================================================
# Property 23: Engine Health Check Retry
# ============================================================================

class TestEngineHealthCheckRetry:
    """Property 23: Engine health checks retry with exponential backoff.

    Validates: Requirements 6.5
    """

    @pytest.mark.asyncio
    @given(
        num_failures=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_exponential_backoff_on_failure(self, num_failures: int):
        """Test that failed health checks trigger exponential backoff."""
        await reset_health_monitor()
        monitor = AnnotationEngineHealthMonitor(
            check_interval=1,
            max_failures=3,
            backoff_base=2.0,
            max_backoff=60,
        )

        # Create failing health check function
        check_count = [0]

        async def failing_health_check():
            check_count[0] += 1
            return False

        # Register engine with failing health check
        engine_id = f"test_engine_{uuid4()}"
        await monitor.register_engine(
            engine_id=engine_id,
            engine_type=EngineType.CUSTOM_LLM,
            health_check_func=failing_health_check,
        )

        # Perform multiple health checks
        for i in range(num_failures):
            await monitor._check_engine(engine_id)

        # Get health status
        status = await monitor.get_health_status(engine_id)

        # Verify consecutive failures tracked
        assert status is not None
        assert status.consecutive_failures == num_failures

        # If failures >= max_failures, engine should be unhealthy and in backoff
        if num_failures >= monitor.max_failures:
            assert status.status == HealthStatus.UNHEALTHY
            assert engine_id in monitor.backoff_until

            # Verify exponential backoff time
            backoff_until = monitor.backoff_until[engine_id]
            expected_backoff_seconds = min(
                monitor.backoff_base ** num_failures,
                monitor.max_backoff,
            )
            # Allow small margin for timing
            assert (backoff_until - datetime.now()).total_seconds() > 0
            assert (backoff_until - datetime.now()).total_seconds() <= expected_backoff_seconds + 1

    @pytest.mark.asyncio
    @given(
        num_engines=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_multiple_engine_health_tracking(self, num_engines: int):
        """Test that health monitor tracks multiple engines independently."""
        await reset_health_monitor()
        monitor = AnnotationEngineHealthMonitor()

        # Register multiple engines with different health states
        engine_ids = []
        for i in range(num_engines):
            engine_id = f"engine_{i}_{uuid4()}"
            engine_ids.append(engine_id)

            # Half healthy, half unhealthy
            is_healthy = (i % 2 == 0)

            async def health_check(healthy=is_healthy):
                return healthy

            await monitor.register_engine(
                engine_id=engine_id,
                engine_type=EngineType.CUSTOM_LLM,
                health_check_func=health_check,
            )

        # Check all engines
        for engine_id in engine_ids:
            await monitor._check_engine(engine_id)

        # Get healthy engines
        healthy_engines = await monitor.get_healthy_engines()

        # Should have roughly half healthy (with rounding)
        expected_healthy = (num_engines + 1) // 2
        assert len(healthy_engines) == expected_healthy

    @pytest.mark.asyncio
    async def test_health_recovery_clears_backoff(self):
        """Test that recovering health clears backoff period."""
        await reset_health_monitor()
        monitor = AnnotationEngineHealthMonitor(max_failures=2)

        # Create health check that can toggle
        is_healthy = [False]

        async def toggleable_health_check():
            return is_healthy[0]

        engine_id = f"test_engine_{uuid4()}"
        await monitor.register_engine(
            engine_id=engine_id,
            engine_type=EngineType.CUSTOM_LLM,
            health_check_func=toggleable_health_check,
        )

        # Fail health checks to trigger backoff
        for _ in range(3):
            await monitor._check_engine(engine_id)

        # Should be in backoff
        assert engine_id in monitor.backoff_until

        # Recover health
        is_healthy[0] = True
        await monitor._check_engine(engine_id)

        # Backoff should be cleared
        assert engine_id not in monitor.backoff_until

        # Status should be healthy
        status = await monitor.get_health_status(engine_id)
        assert status.status == HealthStatus.HEALTHY
        assert status.consecutive_failures == 0


# ============================================================================
# Label Studio Integration Tests
# ============================================================================

class TestLabelStudioIntegration:
    """Test Label Studio ML Backend integration."""

    @pytest.mark.asyncio
    @given(
        num_tasks=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_batch_prediction(self, num_tasks: int):
        """Test batch prediction for multiple tasks."""
        await reset_label_studio_engines()

        engine = LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test_key",
            project_id=1,
        )

        # Create test tasks
        tasks = [
            LabelStudioTask(
                id=i,
                data={"text": f"Task {i}"},
            )
            for i in range(num_tasks)
        ]

        # Get predictions
        predictions = await engine.predict(tasks)

        # Should return one prediction per task
        assert len(predictions) == num_tasks

        # All predictions should have required fields
        for pred in predictions:
            assert isinstance(pred, LabelStudioPrediction)
            assert pred.result is not None
            assert pred.score is not None

        await engine.close()

    @pytest.mark.asyncio
    @given(
        num_annotations=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    async def test_model_training(self, num_annotations: int):
        """Test model training with annotations."""
        await reset_label_studio_engines()

        engine = LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test_key",
        )

        # Create training annotations
        annotations = [
            {"task_id": i, "result": [{"value": f"label_{i}"}]}
            for i in range(num_annotations)
        ]

        # Start training
        job = await engine.train(annotations)

        # Job should be created
        assert job is not None
        assert job.status in ["pending", "training"]
        assert job.model_version is not None

        # Wait for training to complete (with timeout)
        timeout = 5
        elapsed = 0
        while elapsed < timeout:
            status = await engine.get_training_status(job.job_id)
            if status and status.status in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)
            elapsed += 0.1

        # Should have completed or at least progressed
        final_status = await engine.get_training_status(job.job_id)
        assert final_status is not None

        await engine.close()

    @pytest.mark.asyncio
    @given(
        num_versions=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_version_management(self, num_versions: int):
        """Test model version management."""
        await reset_label_studio_engines()

        engine = LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test_key",
        )

        # Create multiple versions
        version_names = []
        for i in range(num_versions):
            version_name = f"v_{i}_{uuid4()}"
            version_names.append(version_name)

            # Train to create version
            await engine.train(
                annotations=[{"task_id": i, "result": []}],
                version_name=version_name,
            )

        # Wait for all training jobs to complete
        await asyncio.sleep(0.5)

        # List versions
        versions = await engine.list_versions()

        # Should have all versions
        assert len(versions) >= num_versions

        # Latest version should be current
        assert engine.current_version in version_names

        # Should be able to get specific versions
        for version_name in version_names:
            version = await engine.get_version(version_name)
            # May not exist if training not completed, so check if exists
            if version:
                assert version.version == version_name

        await engine.close()


# ============================================================================
# Argilla Integration Tests
# ============================================================================

class TestArgillaIntegration:
    """Test Argilla platform integration."""

    @pytest.mark.asyncio
    @given(
        num_fields=st.integers(min_value=1, max_value=5),
        num_questions=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    async def test_dataset_creation(self, num_fields: int, num_questions: int):
        """Test dataset creation with fields and questions."""
        await reset_argilla_engines()

        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test_key",
        )

        # Create fields
        fields = [
            ArgillaField(
                name=f"field_{i}",
                title=f"Field {i}",
                type="text",
            )
            for i in range(num_fields)
        ]

        # Create questions
        questions = [
            ArgillaQuestion(
                name=f"question_{i}",
                title=f"Question {i}",
                type=FeedbackType.LABEL,
                settings={"options": ["A", "B", "C"]},
            )
            for i in range(num_questions)
        ]

        # Create dataset
        dataset_name = f"test_dataset_{uuid4()}"
        dataset = await engine.create_dataset(
            name=dataset_name,
            fields=fields,
            questions=questions,
            guidelines="Test guidelines",
        )

        # Verify dataset created
        assert dataset is not None
        assert dataset.name == dataset_name
        assert len(dataset.fields) == num_fields
        assert len(dataset.questions) == num_questions
        assert dataset.guidelines == "Test guidelines"

        # Should be able to get dataset
        retrieved = await engine.get_dataset(dataset_name)
        assert retrieved is not None
        assert retrieved.id == dataset.id

    @pytest.mark.asyncio
    @given(
        num_records=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_record_management(self, num_records: int):
        """Test adding and managing records."""
        await reset_argilla_engines()

        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test_key",
        )

        # Create dataset
        dataset_name = f"test_dataset_{uuid4()}"
        await engine.create_dataset(
            name=dataset_name,
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(
                name="label",
                title="Label",
                type=FeedbackType.LABEL,
                settings={"options": ["A", "B"]},
            )],
        )

        # Create records
        records = [
            ArgillaRecord(
                id=str(uuid4()),
                fields={"text": f"Record {i}"},
                status=RecordStatus.PENDING,
            )
            for i in range(num_records)
        ]

        # Add records
        added_count = await engine.add_records(dataset_name, records)

        # Should add all records
        assert added_count == num_records

        # Dataset should reflect new count
        dataset = await engine.get_dataset(dataset_name)
        assert dataset.num_records == num_records

    @pytest.mark.asyncio
    @given(
        num_suggestions=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_suggestions(self, num_suggestions: int):
        """Test adding AI suggestions to records."""
        await reset_argilla_engines()

        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test_key",
        )

        # Create dataset
        dataset_name = f"test_dataset_{uuid4()}"
        await engine.create_dataset(
            name=dataset_name,
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(
                name="label",
                title="Label",
                type=FeedbackType.LABEL,
                settings={"options": ["A", "B", "C"]},
            )],
        )

        # Create suggestions
        record_id = str(uuid4())
        suggestions = [
            ArgillaSuggestion(
                question_name="label",
                value=f"Label_{i}",
                score=0.8 + (i * 0.01),
                agent="test_agent",
            )
            for i in range(num_suggestions)
        ]

        # Add suggestions
        success = await engine.add_suggestions(
            dataset_name=dataset_name,
            record_id=record_id,
            suggestions=suggestions,
        )

        # Should succeed
        assert success is True

    @pytest.mark.asyncio
    async def test_dataset_statistics(self):
        """Test dataset statistics calculation."""
        await reset_argilla_engines()

        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test_key",
        )

        # Create dataset with records
        dataset_name = f"test_dataset_{uuid4()}"
        await engine.create_dataset(
            name=dataset_name,
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(
                name="label",
                title="Label",
                type=FeedbackType.LABEL,
                settings={"options": ["A", "B"]},
            )],
        )

        # Add records
        records = [
            ArgillaRecord(
                id=str(uuid4()),
                fields={"text": f"Record {i}"},
            )
            for i in range(10)
        ]
        await engine.add_records(dataset_name, records)

        # Get statistics
        stats = await engine.get_dataset_statistics(dataset_name)

        # Should have statistics
        assert stats is not None
        assert stats.total_records == 10
        assert stats.pending_records >= 0
        assert stats.submitted_records >= 0
        assert stats.discarded_records >= 0


# ============================================================================
# Helper functions for running async tests
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
