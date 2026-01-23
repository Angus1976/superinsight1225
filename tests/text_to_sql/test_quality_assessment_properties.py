"""
Property-based tests for Text-to-SQL Quality Assessment Module.

Tests Properties 38-39 from text-to-sql-methods specification:
- Property 38: User Feedback Collection
- Property 39: Ragas Quality Assessment
"""

import asyncio
import json
from datetime import datetime
from typing import List
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

# Import the module under test
import sys
sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tests/", 1)[0] + "/src")

from text_to_sql.quality_assessment import (
    QualityAssessmentService,
    QualityConfig,
    RagasQualityAssessor,
    QualityAssessment,
    UserFeedback,
    TrainingExample,
    FeedbackRating,
    QualityDimension,
    ExportFormat,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def query_strategy(draw) -> str:
    """Generate natural language query."""
    templates = [
        "Show me all {entity} from {table}",
        "Find {entity} where {condition}",
        "Count the number of {entity}",
        "List {entity} ordered by {field}",
        "Get the total {aggregate} of {entity}",
    ]
    template = draw(st.sampled_from(templates))
    entity = draw(st.sampled_from(["users", "orders", "products", "customers"]))
    table = draw(st.sampled_from(["users_table", "orders_table", "products_table"]))
    condition = draw(st.sampled_from(["status = 'active'", "id > 100", "created_at > '2024-01-01'"]))
    field = draw(st.sampled_from(["id", "name", "created_at"]))
    aggregate = draw(st.sampled_from(["sum", "count", "average"]))
    return template.format(entity=entity, table=table, condition=condition, field=field, aggregate=aggregate)


@st.composite
def sql_strategy(draw) -> str:
    """Generate SQL statement."""
    return draw(st.sampled_from([
        "SELECT * FROM users;",
        "SELECT id, name FROM orders WHERE status = 'active';",
        "SELECT COUNT(*) FROM products;",
        "SELECT * FROM customers ORDER BY created_at DESC;",
        "SELECT SUM(amount) FROM orders WHERE date > '2024-01-01';",
    ]))


@st.composite
def database_type_strategy(draw) -> str:
    """Generate database type."""
    return draw(st.sampled_from(["postgresql", "mysql", "oracle", "sqlserver"]))


@st.composite
def feedback_rating_strategy(draw) -> FeedbackRating:
    """Generate feedback rating."""
    return draw(st.sampled_from(list(FeedbackRating)))


@st.composite
def user_id_strategy(draw) -> str:
    """Generate user ID."""
    return f"user_{draw(st.integers(min_value=1, max_value=1000))}"


# =============================================================================
# Property 38: User Feedback Collection
# =============================================================================

class TestUserFeedbackCollection:
    """
    Property 38: User Feedback Collection

    Validates that:
    1. User feedback is stored correctly
    2. Feedback ratings are preserved
    3. Corrected SQL creates training examples
    4. Feedback statistics are accurate
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return QualityAssessmentService()

    @given(
        query=query_strategy(),
        sql=sql_strategy(),
        rating=feedback_rating_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_feedback_stored_correctly(
        self,
        query: str,
        sql: str,
        rating: FeedbackRating,
        user_id: str,
    ):
        """Property: User feedback is stored with all fields."""
        service = QualityAssessmentService()

        async def run_test():
            feedback = await service.submit_feedback(
                query=query,
                generated_sql=sql,
                rating=rating,
                user_id=user_id,
                comment="Test comment",
                database_type="postgresql",
            )

            assert feedback.query == query
            assert feedback.generated_sql == sql
            assert feedback.rating == rating
            assert feedback.user_id == user_id
            assert feedback.comment == "Test comment"

            # Verify can retrieve
            feedback_list = await service.get_feedback(limit=10)
            assert any(f.id == feedback.id for f in feedback_list)

        asyncio.run(run_test())

    @given(
        query=query_strategy(),
        generated_sql=sql_strategy(),
        corrected_sql=sql_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_corrected_sql_creates_training_example(
        self,
        query: str,
        generated_sql: str,
        corrected_sql: str,
        user_id: str,
    ):
        """Property: Corrected SQL creates training example."""
        assume(generated_sql != corrected_sql)  # Ensure correction is different

        service = QualityAssessmentService()

        async def run_test():
            await service.submit_feedback(
                query=query,
                generated_sql=generated_sql,
                corrected_sql=corrected_sql,
                rating=FeedbackRating.PARTIALLY_CORRECT,
                user_id=user_id,
                database_type="postgresql",
            )

            # Check training data was created
            stats = await service.get_training_data_statistics()
            assert stats["total_examples"] >= 1

            # Export and verify
            export_data = await service.export_training_data(
                format=ExportFormat.JSONL,
                min_quality_score=0.0,
            )

            assert corrected_sql in export_data

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_feedback_statistics_accurate(self):
        """Property: Feedback statistics accurately reflect stored feedback."""
        service = QualityAssessmentService()

        # Submit feedback with known distribution
        ratings = [
            FeedbackRating.CORRECT,
            FeedbackRating.CORRECT,
            FeedbackRating.CORRECT,
            FeedbackRating.PARTIALLY_CORRECT,
            FeedbackRating.PARTIALLY_CORRECT,
            FeedbackRating.INCORRECT,
        ]

        for i, rating in enumerate(ratings):
            await service.submit_feedback(
                query=f"query {i}",
                generated_sql=f"SELECT {i}",
                rating=rating,
                user_id=f"user_{i}",
            )

        stats = await service.get_feedback_statistics()

        assert stats.total_feedback == 6
        assert stats.correct_count == 3
        assert stats.partially_correct_count == 2
        assert stats.incorrect_count == 1

    @given(
        num_feedback=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=10, deadline=None)
    def test_feedback_filter_by_rating(self, num_feedback: int):
        """Property: Feedback can be filtered by rating."""
        service = QualityAssessmentService()

        async def run_test():
            correct_count = 0
            for i in range(num_feedback):
                rating = FeedbackRating.CORRECT if i % 2 == 0 else FeedbackRating.INCORRECT
                if rating == FeedbackRating.CORRECT:
                    correct_count += 1

                await service.submit_feedback(
                    query=f"query {i}",
                    generated_sql=f"SELECT {i}",
                    rating=rating,
                    user_id=f"user_{i}",
                )

            # Filter by CORRECT
            correct_feedback = await service.get_feedback(
                rating=FeedbackRating.CORRECT
            )

            assert len(correct_feedback) == correct_count

            # All results should be CORRECT
            for f in correct_feedback:
                assert f.rating == FeedbackRating.CORRECT

        asyncio.run(run_test())


# =============================================================================
# Property 39: Ragas Quality Assessment
# =============================================================================

class TestRagasQualityAssessment:
    """
    Property 39: Ragas Quality Assessment

    Validates that:
    1. Quality assessment produces scores for all dimensions
    2. Scores are within valid range [0, 1]
    3. Overall score is weighted average of dimensions
    4. High-quality SQL produces high scores
    """

    @pytest.fixture
    def assessor(self):
        """Create fresh assessor instance."""
        return RagasQualityAssessor()

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return QualityAssessmentService()

    @given(
        query=query_strategy(),
        sql=sql_strategy(),
        database_type=database_type_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_assessment_has_all_dimensions(
        self,
        query: str,
        sql: str,
        database_type: str,
    ):
        """Property: Assessment includes scores for all evaluated dimensions."""
        service = QualityAssessmentService()

        async def run_test():
            assessment = await service.assess_quality(
                query=query,
                generated_sql=sql,
                database_type=database_type,
            )

            # Should have syntax, faithfulness, and relevance scores
            dimensions = {s.dimension for s in assessment.scores}

            assert QualityDimension.SYNTAX in dimensions
            assert QualityDimension.FAITHFULNESS in dimensions
            assert QualityDimension.RELEVANCE in dimensions

        asyncio.run(run_test())

    @given(
        query=query_strategy(),
        sql=sql_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_scores_within_valid_range(
        self,
        query: str,
        sql: str,
    ):
        """Property: All scores are within [0, 1] range."""
        service = QualityAssessmentService()

        async def run_test():
            assessment = await service.assess_quality(
                query=query,
                generated_sql=sql,
            )

            for score in assessment.scores:
                assert 0.0 <= score.score <= 1.0, \
                    f"{score.dimension} score {score.score} out of range"
                assert 0.0 <= score.confidence <= 1.0, \
                    f"{score.dimension} confidence {score.confidence} out of range"

            assert 0.0 <= assessment.overall_score <= 1.0

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_valid_sql_has_high_syntax_score(self):
        """Property: Valid SQL syntax produces high syntax score."""
        service = QualityAssessmentService()

        valid_sql = "SELECT id, name FROM users WHERE status = 'active';"

        assessment = await service.assess_quality(
            query="Show active users",
            generated_sql=valid_sql,
        )

        syntax_score = assessment.get_score(QualityDimension.SYNTAX)
        assert syntax_score is not None
        assert syntax_score >= 0.8, f"Valid SQL should have high syntax score, got {syntax_score}"

    @pytest.mark.asyncio
    async def test_invalid_sql_has_low_syntax_score(self):
        """Property: Invalid SQL syntax produces low syntax score."""
        service = QualityAssessmentService()

        invalid_sql = "SELEC * FORM users WHER"  # Invalid SQL

        assessment = await service.assess_quality(
            query="Show users",
            generated_sql=invalid_sql,
        )

        syntax_score = assessment.get_score(QualityDimension.SYNTAX)
        assert syntax_score is not None
        assert syntax_score < 0.5, f"Invalid SQL should have low syntax score, got {syntax_score}"

    @pytest.mark.asyncio
    async def test_matching_expected_sql_has_high_faithfulness(self):
        """Property: SQL matching expected has high faithfulness score."""
        service = QualityAssessmentService()

        sql = "SELECT * FROM users WHERE status = 'active';"

        assessment = await service.assess_quality(
            query="Show active users",
            generated_sql=sql,
            expected_sql=sql,  # Same as generated
        )

        faithfulness_score = assessment.get_score(QualityDimension.FAITHFULNESS)
        assert faithfulness_score is not None
        assert faithfulness_score >= 0.9, \
            f"Matching SQL should have high faithfulness, got {faithfulness_score}"


# =============================================================================
# Additional Property Tests: Training Data Export
# =============================================================================

class TestTrainingDataExport:
    """
    Tests for training data export functionality.
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return QualityAssessmentService()

    @pytest.mark.asyncio
    async def test_high_quality_assessments_create_training_data(self):
        """Property: High quality assessments automatically create training examples."""
        config = QualityConfig(min_quality_for_training=0.5)
        service = QualityAssessmentService(config=config)

        # Create assessments
        for i in range(5):
            await service.assess_quality(
                query=f"Show all records {i}",
                generated_sql=f"SELECT * FROM table{i};",
                database_type="postgresql",
            )

        stats = await service.get_training_data_statistics()
        assert stats["total_examples"] >= 1

    @pytest.mark.asyncio
    async def test_export_jsonl_format(self):
        """Property: JSONL export is valid JSON Lines format."""
        config = QualityConfig(min_quality_for_training=0.0)
        service = QualityAssessmentService(config=config)

        # Add some assessments
        await service.assess_quality(
            query="Show users",
            generated_sql="SELECT * FROM users;",
            database_type="postgresql",
        )

        export_data = await service.export_training_data(
            format=ExportFormat.JSONL,
            min_quality_score=0.0,
        )

        # Each line should be valid JSON
        for line in export_data.strip().split("\n"):
            if line:
                record = json.loads(line)
                assert "query" in record
                assert "sql" in record
                assert "database_type" in record

    @given(
        min_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=10, deadline=None)
    def test_export_respects_quality_filter(self, min_score: float):
        """Property: Export respects minimum quality score filter."""
        config = QualityConfig(min_quality_for_training=0.0)
        service = QualityAssessmentService(config=config)

        async def run_test():
            # Add assessments
            for i in range(5):
                await service.assess_quality(
                    query=f"Query {i}",
                    generated_sql=f"SELECT * FROM table{i};",
                    database_type="postgresql",
                )

            export_data = await service.export_training_data(
                format=ExportFormat.JSONL,
                min_quality_score=min_score,
            )

            # Parse and verify all exported items meet threshold
            for line in export_data.strip().split("\n"):
                if line:
                    record = json.loads(line)
                    if "quality_score" in record:
                        assert record["quality_score"] >= min_score

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Quality Report
# =============================================================================

class TestQualityReport:
    """
    Tests for quality report generation.
    """

    @pytest.mark.asyncio
    async def test_report_includes_all_sections(self):
        """Property: Quality report includes all required sections."""
        service = QualityAssessmentService()

        # Add some data
        await service.assess_quality(
            query="Show users",
            generated_sql="SELECT * FROM users;",
            database_type="postgresql",
            method_used="template",
        )

        await service.submit_feedback(
            query="Show orders",
            generated_sql="SELECT * FROM orders;",
            rating=FeedbackRating.CORRECT,
            user_id="user_1",
        )

        report = await service.generate_quality_report(period_days=7)

        assert "generated_at" in report
        assert "period_days" in report
        assert "assessments" in report
        assert "feedback" in report
        assert "training_data" in report

        assert "total" in report["assessments"]
        assert "average_overall_score" in report["assessments"]
        assert "by_method" in report["assessments"]

    @pytest.mark.asyncio
    async def test_report_method_breakdown_accurate(self):
        """Property: Report method breakdown is accurate."""
        service = QualityAssessmentService()

        # Add assessments with different methods
        for i in range(3):
            await service.assess_quality(
                query=f"Query {i}",
                generated_sql=f"SELECT {i};",
                method_used="template",
            )

        for i in range(2):
            await service.assess_quality(
                query=f"Query LLM {i}",
                generated_sql=f"SELECT llm_{i};",
                method_used="llm",
            )

        report = await service.generate_quality_report(period_days=7)

        by_method = report["assessments"]["by_method"]

        assert "template" in by_method
        assert "llm" in by_method
        assert by_method["template"]["count"] == 3
        assert by_method["llm"]["count"] == 2


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
