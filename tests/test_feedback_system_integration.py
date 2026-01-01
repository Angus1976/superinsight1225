"""
Integration tests for the feedback system.

Tests:
- Feedback collection to processing flow
- Processing to improvement engine integration
- Customer relationship tracking
- Pattern detection and improvement initiatives
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from src.feedback.collector import (
    FeedbackCollector, FeedbackSource, FeedbackCategory,
    SentimentType, FeedbackStatus, Feedback
)
from src.feedback.processor import (
    FeedbackProcessor, ProcessingTask, ProcessingStatus,
    ProcessingPriority, Solution
)
from src.feedback.improvement_engine import (
    ImprovementEngine, ImprovementType, ImprovementStatus,
    ImpactLevel, Pattern, ImprovementInitiative
)


class TestFeedbackCollectorIntegration:
    """Integration tests for FeedbackCollector."""

    @pytest.fixture
    def collector(self):
        """Create a feedback collector instance."""
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_collect_feedback_with_sentiment_analysis(self, collector):
        """Test feedback collection with automatic sentiment analysis."""
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="The quality of annotations is excellent! Great work on the accuracy.",
            submitter_id="customer_1",
            tenant_id="tenant_1"
        )

        assert feedback is not None
        assert feedback.sentiment == SentimentType.POSITIVE
        assert feedback.sentiment_score > 0
        assert feedback.category == FeedbackCategory.QUALITY
        assert "quality_related" in feedback.tags

    @pytest.mark.asyncio
    async def test_collect_negative_feedback(self, collector):
        """Test negative feedback detection."""
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="This is terrible. So many errors and the system is very slow.",
            submitter_id="customer_2",
            tenant_id="tenant_1"
        )

        assert feedback is not None
        assert feedback.sentiment == SentimentType.NEGATIVE
        assert feedback.sentiment_score < 0
        assert FeedbackCategory.COMPLAINT in [feedback.category] or feedback.sentiment_score < -0.2

    @pytest.mark.asyncio
    async def test_feedback_category_auto_detection(self, collector):
        """Test automatic category detection."""
        # Quality feedback
        quality_feedback = await collector.collect_feedback(
            source=FeedbackSource.ANNOTATOR,
            content="Found accuracy issues in the guidelines",
            submitter_id="annotator_1"
        )
        assert quality_feedback.category == FeedbackCategory.QUALITY

        # Tool feedback
        tool_feedback = await collector.collect_feedback(
            source=FeedbackSource.ANNOTATOR,
            content="The system interface has a bug that prevents saving",
            submitter_id="annotator_2"
        )
        assert tool_feedback.category == FeedbackCategory.TOOL

    @pytest.mark.asyncio
    async def test_feedback_listing_with_filters(self, collector):
        """Test feedback listing with various filters."""
        # Create multiple feedbacks
        for i in range(5):
            await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=f"Test feedback {i}",
                tenant_id="tenant_1"
            )

        for i in range(3):
            await collector.collect_feedback(
                source=FeedbackSource.ANNOTATOR,
                content=f"Annotator feedback {i}",
                tenant_id="tenant_1"
            )

        # Test source filter
        customer_feedbacks, total = await collector.list_feedbacks(
            source=FeedbackSource.CUSTOMER
        )
        assert total == 5

        # Test tenant filter
        all_feedbacks, total = await collector.list_feedbacks(
            tenant_id="tenant_1"
        )
        assert total == 8

    @pytest.mark.asyncio
    async def test_feedback_statistics(self, collector):
        """Test feedback statistics generation."""
        # Create feedbacks with different sentiments
        positive_content = "Great work! Excellent quality and very accurate."
        negative_content = "Terrible quality. So many errors and problems."
        neutral_content = "The task has been completed."

        for content in [positive_content, negative_content, neutral_content]:
            await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=content,
                tenant_id="tenant_1"
            )

        stats = await collector.get_feedback_statistics(tenant_id="tenant_1")

        assert stats["total_feedbacks"] == 3
        assert "by_sentiment" in stats
        assert stats["by_sentiment"]["positive"] >= 1
        assert stats["by_sentiment"]["negative"] >= 1


class TestFeedbackProcessorIntegration:
    """Integration tests for FeedbackProcessor."""

    @pytest.fixture
    def collector(self):
        """Create a feedback collector instance."""
        return FeedbackCollector()

    @pytest.fixture
    def processor(self, collector):
        """Create a feedback processor instance."""
        return FeedbackProcessor(collector)

    @pytest.mark.asyncio
    async def test_create_processing_task_from_feedback(self, collector, processor):
        """Test creating a processing task from feedback."""
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="There are quality issues with the annotations. Please fix.",
            submitter_id="customer_1"
        )

        task = await processor.create_processing_task(feedback, auto_assign=False)

        assert task is not None
        assert task.feedback_id == feedback.id
        assert task.status == ProcessingStatus.QUEUED
        assert task.sla_deadline is not None
        assert len(task.keywords) > 0
        assert len(task.suggested_solutions) > 0

    @pytest.mark.asyncio
    async def test_priority_determination(self, collector, processor):
        """Test priority determination based on feedback characteristics."""
        # Negative complaint should be urgent
        complaint_feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="I am very unhappy with this. This is a serious complaint about quality.",
            category=FeedbackCategory.COMPLAINT
        )
        complaint_task = await processor.create_processing_task(complaint_feedback, auto_assign=False)
        assert complaint_task.priority in [ProcessingPriority.URGENT, ProcessingPriority.HIGH]

        # Positive suggestion should be low priority
        suggestion_feedback = await collector.collect_feedback(
            source=FeedbackSource.ANNOTATOR,
            content="I have a suggestion for improvement. Everything is working well.",
            category=FeedbackCategory.SUGGESTION
        )
        suggestion_task = await processor.create_processing_task(suggestion_feedback, auto_assign=False)
        assert suggestion_task.priority in [ProcessingPriority.LOW, ProcessingPriority.MEDIUM]

    @pytest.mark.asyncio
    async def test_handler_registration_and_assignment(self, collector, processor):
        """Test handler registration and task assignment."""
        # Register handlers
        await processor.register_handler(
            handler_id="handler_1",
            name="Quality Handler",
            expertise=["quality", "accuracy"],
            max_workload=5
        )
        await processor.register_handler(
            handler_id="handler_2",
            name="Tool Handler",
            expertise=["tool", "system"],
            max_workload=5
        )

        # Create and assign feedback
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="Quality issues found in annotations",
            category=FeedbackCategory.QUALITY
        )

        task = await processor.create_processing_task(feedback, auto_assign=True)

        # Handler should be assigned based on expertise
        assert task.assigned_to is not None
        assert task.status == ProcessingStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_task_resolution_flow(self, collector, processor):
        """Test complete task resolution flow."""
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="Minor quality issue found",
            submitter_id="customer_1"
        )

        task = await processor.create_processing_task(feedback, auto_assign=False)

        # Update status to in progress
        await processor.update_task_status(
            task.id,
            ProcessingStatus.IN_PROGRESS,
            notes="Started working on issue"
        )

        # Resolve the task
        await processor.resolve_task(
            task.id,
            resolution="Issue has been fixed and verified"
        )

        # Verify resolution
        updated_task = await processor.get_task(task.id)
        assert updated_task["status"] == ProcessingStatus.RESOLVED.value
        assert updated_task["resolution"] is not None
        assert updated_task["resolution_time"] is not None

    @pytest.mark.asyncio
    async def test_sla_breach_detection(self, collector, processor):
        """Test SLA breach detection."""
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="Urgent issue needs fixing"
        )

        task = await processor.create_processing_task(feedback, auto_assign=False)

        # Manually set SLA deadline to past
        processor._tasks[task.id].sla_deadline = datetime.now() - timedelta(hours=1)

        breached = await processor.check_sla_breaches()
        assert len(breached) > 0
        assert task.id in [t.id for t in breached]

    @pytest.mark.asyncio
    async def test_satisfaction_survey(self, collector, processor):
        """Test customer satisfaction survey submission."""
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="Issue reported"
        )

        task = await processor.create_processing_task(feedback, auto_assign=False)
        await processor.resolve_task(task.id, "Resolved")

        survey = await processor.submit_satisfaction_survey(
            feedback_id=feedback.id,
            task_id=task.id,
            overall_score=4.5,
            response_speed_score=4.0,
            solution_quality_score=5.0,
            communication_score=4.5,
            comments="Great service!"
        )

        assert survey is not None
        assert survey.overall_score == 4.5

        # Check statistics
        stats = await processor.get_satisfaction_statistics()
        assert stats["total_surveys"] >= 1


class TestImprovementEngineIntegration:
    """Integration tests for ImprovementEngine."""

    @pytest.fixture
    def collector(self):
        """Create a feedback collector instance."""
        return FeedbackCollector()

    @pytest.fixture
    def processor(self, collector):
        """Create a feedback processor instance."""
        return FeedbackProcessor(collector)

    @pytest.fixture
    def engine(self, collector, processor):
        """Create an improvement engine instance."""
        return ImprovementEngine(collector, processor)

    @pytest.mark.asyncio
    async def test_pattern_detection(self, collector, engine):
        """Test pattern detection from similar feedbacks."""
        # Create similar negative feedbacks
        for i in range(5):
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=f"Quality issue #{i}: Found errors in the annotations",
                category=FeedbackCategory.QUALITY
            )
            await engine.analyze_feedback_pattern(feedback)

        patterns = await engine.list_patterns(category=FeedbackCategory.QUALITY)
        assert len(patterns) > 0

        # Check pattern occurrence count
        quality_pattern = patterns[0]
        assert quality_pattern["occurrence_count"] >= 1

    @pytest.mark.asyncio
    async def test_impact_assessment(self, collector, engine):
        """Test feedback impact assessment."""
        feedbacks = []
        feedback_ids = []

        # Create mix of positive and negative feedbacks
        for i in range(10):
            content = "This is terrible!" if i < 7 else "Great work!"
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=content,
                submitter_id=f"customer_{i}"
            )
            feedbacks.append(feedback)
            feedback_ids.append(feedback.id)

        assessment = await engine.assess_feedback_impact(feedback_ids, feedbacks)

        assert assessment is not None
        assert assessment.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]
        assert assessment.risk_score > 0.3
        assert assessment.customer_impact_count == 10
        assert len(assessment.recommendations) > 0

    @pytest.mark.asyncio
    async def test_improvement_initiative_creation(self, engine):
        """Test improvement initiative creation."""
        initiative = await engine.create_improvement_initiative(
            title="Quality Improvement Program",
            description="Address recurring quality issues",
            improvement_type=ImprovementType.QUALITY,
            priority=ImpactLevel.HIGH,
            owner="quality_manager_1"
        )

        assert initiative is not None
        assert initiative.status == ImprovementStatus.PROPOSED
        assert len(initiative.action_items) > 0
        assert len(initiative.success_metrics) > 0
        assert initiative.target_completion is not None

    @pytest.mark.asyncio
    async def test_initiative_lifecycle(self, engine):
        """Test initiative status updates through lifecycle."""
        initiative = await engine.create_improvement_initiative(
            title="Process Improvement",
            description="Improve annotation workflow",
            improvement_type=ImprovementType.PROCESS
        )

        # Progress through statuses
        await engine.update_initiative_status(
            initiative.id,
            ImprovementStatus.APPROVED
        )
        await engine.update_initiative_status(
            initiative.id,
            ImprovementStatus.IN_PROGRESS
        )
        await engine.update_initiative_status(
            initiative.id,
            ImprovementStatus.IMPLEMENTED,
            actual_outcomes=["Process time reduced by 20%"]
        )

        updated = await engine.get_initiative(initiative.id)
        assert updated["status"] == ImprovementStatus.IMPLEMENTED.value
        assert len(updated["actual_outcomes"]) > 0
        assert updated["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_customer_relationship_tracking(self, collector, engine):
        """Test customer relationship updates from feedback."""
        customer_id = "vip_customer_1"

        # Submit multiple feedbacks
        for i in range(5):
            sentiment = "positive" if i < 3 else "negative"
            content = "Great service!" if sentiment == "positive" else "Not happy!"
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=content,
                submitter_id=customer_id
            )
            await engine.update_customer_relationship(feedback)

        relationship = await engine.get_customer_relationship(customer_id)

        assert relationship is not None
        assert relationship["total_feedback_count"] == 5
        assert relationship["positive_feedback_count"] == 3
        assert relationship["negative_feedback_count"] == 2
        assert relationship["satisfaction_trend"] in ["improving", "stable", "declining"]

    @pytest.mark.asyncio
    async def test_at_risk_customer_identification(self, collector, engine):
        """Test at-risk customer identification."""
        # Create high-risk customer
        for i in range(5):
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content="This is terrible! Very unhappy!",
                submitter_id="risky_customer"
            )
            await engine.update_customer_relationship(feedback)

        at_risk = await engine.list_at_risk_customers(risk_level="high")
        assert len(at_risk) > 0
        assert "risky_customer" in [c["customer_id"] for c in at_risk]

    @pytest.mark.asyncio
    async def test_effectiveness_evaluation(self, collector, engine):
        """Test initiative effectiveness evaluation."""
        initiative = await engine.create_improvement_initiative(
            title="Test Initiative",
            description="For testing effectiveness",
            improvement_type=ImprovementType.QUALITY
        )

        # Simulate positive post-implementation feedback
        post_feedbacks = []
        for i in range(10):
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content="Much better now! Great improvement!"
            )
            post_feedbacks.append(feedback)

        effectiveness = await engine.evaluate_initiative_effectiveness(
            initiative.id,
            post_feedbacks
        )

        assert effectiveness > 0.5
        updated = await engine.get_initiative(initiative.id)
        assert updated["status"] == ImprovementStatus.VERIFIED.value


class TestEndToEndFeedbackFlow:
    """End-to-end integration tests for the complete feedback flow."""

    @pytest.fixture
    def system(self):
        """Create complete feedback system."""
        collector = FeedbackCollector()
        processor = FeedbackProcessor(collector)
        engine = ImprovementEngine(collector, processor)
        return collector, processor, engine

    @pytest.mark.asyncio
    async def test_complete_feedback_to_improvement_flow(self, system):
        """Test complete flow from feedback collection to improvement."""
        collector, processor, engine = system

        # Register handler
        await processor.register_handler(
            handler_id="handler_1",
            name="Quality Handler",
            expertise=["quality"],
            max_workload=10
        )

        # Step 1: Collect feedback
        feedback = await collector.collect_feedback(
            source=FeedbackSource.CUSTOMER,
            content="Quality issue: annotations have many errors that need fixing",
            submitter_id="customer_1",
            tenant_id="tenant_1"
        )

        # Step 2: Create processing task
        task = await processor.create_processing_task(feedback, auto_assign=True)
        assert task.status == ProcessingStatus.ASSIGNED

        # Step 3: Analyze pattern
        pattern = await engine.analyze_feedback_pattern(feedback)
        assert pattern is not None

        # Step 4: Track customer relationship
        relationship = await engine.update_customer_relationship(feedback)
        assert relationship.total_feedback_count >= 1

        # Step 5: Resolve task
        await processor.resolve_task(
            task.id,
            resolution="Errors have been corrected"
        )

        # Step 6: Submit satisfaction survey
        survey = await processor.submit_satisfaction_survey(
            feedback_id=feedback.id,
            task_id=task.id,
            overall_score=4.0,
            response_speed_score=4.0,
            solution_quality_score=4.0,
            communication_score=4.0
        )

        # Step 7: Create improvement initiative if needed
        if pattern and pattern.occurrence_count >= 3:
            initiative = await engine.create_improvement_initiative(
                title="Quality Error Reduction",
                description="Address recurring quality errors",
                improvement_type=ImprovementType.QUALITY,
                source_feedback_ids=[feedback.id],
                pattern_id=pattern.id
            )
            assert initiative is not None

        # Verify final state
        final_task = await processor.get_task(task.id)
        assert final_task["status"] == ProcessingStatus.RESOLVED.value
        assert final_task["satisfaction_score"] == 4.0

    @pytest.mark.asyncio
    async def test_recurring_issue_triggers_improvement(self, system):
        """Test that recurring issues trigger improvement initiatives."""
        collector, processor, engine = system

        # Create multiple similar feedbacks to trigger pattern action
        for i in range(5):
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=f"Tool bug #{i}: System crashes when saving",
                category=FeedbackCategory.TOOL,
                submitter_id=f"customer_{i}"
            )
            await engine.analyze_feedback_pattern(feedback)

        # Check for patterns needing action
        patterns = await engine.list_patterns(category=FeedbackCategory.TOOL)
        active_patterns = [p for p in patterns if p["needs_action"]]

        # Check for auto-created initiatives
        initiatives = await engine.list_initiatives(
            improvement_type=ImprovementType.PREVENTIVE
        )

        # Either pattern needs action or initiative was created
        assert len(active_patterns) > 0 or len(initiatives) > 0

    @pytest.mark.asyncio
    async def test_statistics_across_system(self, system):
        """Test statistics generation across the system."""
        collector, processor, engine = system

        # Create some data
        for i in range(5):
            feedback = await collector.collect_feedback(
                source=FeedbackSource.CUSTOMER,
                content=f"Test feedback {i}",
                submitter_id=f"customer_{i}"
            )
            task = await processor.create_processing_task(feedback, auto_assign=False)
            await processor.resolve_task(task.id, f"Resolved {i}")
            await engine.update_customer_relationship(feedback)

        # Get all statistics
        collector_stats = await collector.get_feedback_statistics()
        processor_stats = await processor.get_processing_statistics()
        engine_stats = await engine.get_improvement_statistics()

        assert collector_stats["total_feedbacks"] >= 5
        assert processor_stats["total_tasks"] >= 5
        assert engine_stats["customer_risk"]["total_tracked"] >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
