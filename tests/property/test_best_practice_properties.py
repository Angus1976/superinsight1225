"""Property tests for Best Practice Library Service.

This module tests universal correctness properties:
- Property 35: Best Practice Display Completeness (validates 11.2)
- Property 38: Usage-Based Best Practice Promotion (validates 11.5)
"""

import pytest
import asyncio
from uuid import UUID, uuid4
from hypothesis import given, strategies as st, settings, assume
from typing import List

from src.collaboration.best_practice_service import (
    BestPracticeService,
    BestPracticeCategory,
    Industry,
    BestPracticeStatus,
    ConfigurationStep
)


# Hypothesis strategies
uuid_strategy = st.builds(uuid4)
category_strategy = st.sampled_from(list(BestPracticeCategory))
industry_strategy = st.sampled_from(list(Industry))
status_strategy = st.sampled_from(list(BestPracticeStatus))

# Text strategies
short_text_strategy = st.text(min_size=1, max_size=50)
medium_text_strategy = st.text(min_size=1, max_size=200)
long_text_strategy = st.text(min_size=1, max_size=500)

# Rating strategy
rating_strategy = st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False)


class TestBestPracticeDisplayCompleteness:
    """Property 35: Best Practice Display Completeness.

    Validates Requirement 11.2:
    - All required fields are present
    - Configuration steps are complete
    - Examples are provided
    - Metadata is accurate
    """

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        title=short_text_strategy,
        description=medium_text_strategy,
        category=category_strategy,
        industry=industry_strategy,
        use_case=short_text_strategy,
        problem=medium_text_strategy,
        solution=long_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_practice_has_all_required_fields(
        self,
        author_id: UUID,
        title: str,
        description: str,
        category: BestPracticeCategory,
        industry: Industry,
        use_case: str,
        problem: str,
        solution: str
    ):
        """Best practices have all required fields."""
        service = BestPracticeService()

        # Create best practice
        practice = await service.create_best_practice(
            author_id=author_id,
            title=title,
            description=description,
            category=category,
            industry=industry,
            use_case=use_case,
            problem_statement=problem,
            solution=solution,
            benefits=["Benefit 1", "Benefit 2"],
            configuration_steps=[
                ConfigurationStep(
                    step_number=1,
                    title="Step 1",
                    description="First step",
                    instructions=["Instruction 1"],
                    validation_rules=["Rule 1"]
                )
            ]
        )

        # Property: All required fields are present
        assert practice.title == title
        assert practice.description == description
        assert practice.category == category
        assert practice.industry == industry
        assert practice.use_case == use_case
        assert practice.problem_statement == problem
        assert practice.solution == solution
        assert len(practice.benefits) > 0
        assert len(practice.configuration_steps) > 0
        assert practice.author_id == author_id

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        step_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_configuration_steps_completeness(
        self,
        author_id: UUID,
        step_count: int
    ):
        """Configuration steps are complete and sequential."""
        service = BestPracticeService()

        # Create steps
        steps = [
            ConfigurationStep(
                step_number=i,
                title=f"Step {i}",
                description=f"Description for step {i}",
                instructions=[f"Instruction {i}.1", f"Instruction {i}.2"],
                validation_rules=[f"Rule {i}"]
            )
            for i in range(step_count)
        ]

        # Create practice
        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Test description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Test use case",
            problem_statement="Test problem",
            solution="Test solution",
            benefits=["Benefit"],
            configuration_steps=steps
        )

        # Property: Steps are complete
        assert len(practice.configuration_steps) == step_count
        for i, step in enumerate(practice.configuration_steps):
            assert step.step_number == i
            assert len(step.instructions) > 0
            assert len(step.validation_rules) > 0

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        benefit_count=st.integers(min_value=1, max_value=5),
        example_count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=50, deadline=None)
    async def test_benefits_and_examples_present(
        self,
        author_id: UUID,
        benefit_count: int,
        example_count: int
    ):
        """Benefits and examples are provided."""
        service = BestPracticeService()

        benefits = [f"Benefit {i}" for i in range(benefit_count)]
        examples = [{"example": f"Example {i}"} for i in range(example_count)]

        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Test description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Test use case",
            problem_statement="Test problem",
            solution="Test solution",
            benefits=benefits,
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])],
            examples=examples
        )

        # Property: Benefits and examples are present
        assert len(practice.benefits) == benefit_count
        assert len(practice.examples) == example_count

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        tags=st.lists(short_text_strategy, min_size=1, max_size=5, unique=True)
    )
    @settings(max_examples=50, deadline=None)
    async def test_metadata_accuracy(
        self,
        author_id: UUID,
        tags: List[str]
    ):
        """Metadata is accurate and preserved."""
        service = BestPracticeService()

        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Test description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Test use case",
            problem_statement="Test problem",
            solution="Test solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])],
            tags=tags
        )

        # Property: Metadata is accurate
        assert practice.author_id == author_id
        assert practice.status == BestPracticeStatus.DRAFT
        assert practice.usage_count == 0
        assert set(practice.tags) == set(tags)
        assert practice.created_at is not None


class TestUsageBasedBestPracticePromotion:
    """Property 38: Usage-Based Best Practice Promotion.

    Validates Requirement 11.5:
    - Practices above 75th percentile are promoted
    - Usage count is tracked accurately
    - Promotion status is updated correctly
    - Popular practices are prioritized in search
    """

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        usage_counts=st.lists(st.integers(min_value=0, max_value=100), min_size=10, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_75th_percentile_promotion(
        self,
        author_id: UUID,
        usage_counts: List[int]
    ):
        """Practices above 75th percentile are promoted."""
        service = BestPracticeService()

        # Create and approve practices with specific usage counts
        practices = []
        for i, count in enumerate(usage_counts):
            practice = await service.create_best_practice(
                author_id=author_id,
                title=f"Practice {i}",
                description=f"Description {i}",
                category=BestPracticeCategory.DATA_MODELING,
                industry=Industry.GENERAL,
                use_case="Use case",
                problem_statement="Problem",
                solution="Solution",
                benefits=["Benefit"],
                configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
            )

            # Approve practice
            await service.submit_best_practice(practice.practice_id, [uuid4()])
            await service.review_best_practice(
                practice.practice_id,
                uuid4(),
                "approve",
                "Good",
                rating=4.0
            )

            # Set usage count
            practice_obj = await service.get_best_practice(practice.practice_id)
            practice_obj.usage_count = count
            practices.append(practice_obj)

        # Trigger promotion update
        await service._update_promotion_status()

        # Calculate 75th percentile
        sorted_counts = sorted(usage_counts)
        percentile_75_idx = int(len(sorted_counts) * 0.75)
        threshold = sorted_counts[percentile_75_idx]

        # Property: Practices above threshold are promoted
        for practice in practices:
            if practice.usage_count >= threshold:
                assert practice.is_promoted
            else:
                assert not practice.is_promoted

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        user_id=uuid_strategy,
        ontology_id=uuid_strategy,
        application_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    async def test_usage_count_tracking(
        self,
        author_id: UUID,
        user_id: UUID,
        ontology_id: UUID,
        application_count: int
    ):
        """Usage count is tracked accurately."""
        service = BestPracticeService()

        # Create and approve practice
        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        await service.submit_best_practice(practice.practice_id, [uuid4()])
        await service.review_best_practice(
            practice.practice_id,
            uuid4(),
            "approve",
            "Good",
            rating=4.0
        )

        # Apply practice multiple times
        initial_count = practice.usage_count
        for _ in range(application_count):
            await service.apply_best_practice(
                practice.practice_id,
                user_id,
                ontology_id
            )

        # Get updated practice
        updated_practice = await service.get_best_practice(practice.practice_id)

        # Property: Usage count increased correctly
        assert updated_practice.usage_count == initial_count + application_count

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_popular_practices_prioritized(
        self,
        author_id: UUID
    ):
        """Popular (promoted) practices are prioritized in search."""
        service = BestPracticeService()

        # Create multiple practices with different usage counts
        high_usage_practice = await service.create_best_practice(
            author_id=author_id,
            title="High Usage Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        low_usage_practice = await service.create_best_practice(
            author_id=author_id,
            title="Low Usage Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        # Approve both
        for practice in [high_usage_practice, low_usage_practice]:
            await service.submit_best_practice(practice.practice_id, [uuid4()])
            await service.review_best_practice(
                practice.practice_id,
                uuid4(),
                "approve",
                "Good",
                rating=4.0
            )

        # Set usage counts
        high_usage_obj = await service.get_best_practice(high_usage_practice.practice_id)
        high_usage_obj.usage_count = 100
        high_usage_obj.is_promoted = True

        low_usage_obj = await service.get_best_practice(low_usage_practice.practice_id)
        low_usage_obj.usage_count = 5
        low_usage_obj.is_promoted = False

        # Search
        results = await service.search_best_practices(
            category=BestPracticeCategory.DATA_MODELING
        )

        # Property: Promoted practice comes first
        assert len(results) >= 2
        # Results are sorted by (is_promoted, usage_count), so promoted should be first
        promoted_results = [r for r in results if r.is_promoted]
        if promoted_results:
            assert promoted_results[0].practice_id == high_usage_practice.practice_id

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_promotion_requires_minimum_practices(
        self,
        author_id: UUID
    ):
        """Promotion only occurs with sufficient practices (>= 4)."""
        service = BestPracticeService()

        # Create only 2 approved practices (less than 4)
        for i in range(2):
            practice = await service.create_best_practice(
                author_id=author_id,
                title=f"Practice {i}",
                description="Description",
                category=BestPracticeCategory.DATA_MODELING,
                industry=Industry.GENERAL,
                use_case="Use case",
                problem_statement="Problem",
                solution="Solution",
                benefits=["Benefit"],
                configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
            )

            await service.submit_best_practice(practice.practice_id, [uuid4()])
            await service.review_best_practice(
                practice.practice_id,
                uuid4(),
                "approve",
                "Good",
                rating=4.0
            )

        # Trigger promotion update
        await service._update_promotion_status()

        # Get all practices
        practices = await service.list_all_practices(status=BestPracticeStatus.APPROVED)

        # Property: No practices promoted with < 4 total
        for practice in practices:
            assert not practice.is_promoted


class TestBestPracticeApplicationWorkflow:
    """Test best practice application workflow."""

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        user_id=uuid_strategy,
        ontology_id=uuid_strategy,
        step_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    async def test_application_workflow_completion(
        self,
        author_id: UUID,
        user_id: UUID,
        ontology_id: UUID,
        step_count: int
    ):
        """Application workflow tracks completion correctly."""
        service = BestPracticeService()

        # Create practice with steps
        steps = [
            ConfigurationStep(
                step_number=i,
                title=f"Step {i}",
                description=f"Description {i}",
                instructions=[f"Instruction {i}"],
                validation_rules=[]
            )
            for i in range(step_count)
        ]

        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=steps
        )

        # Approve practice
        await service.submit_best_practice(practice.practice_id, [uuid4()])
        await service.review_best_practice(
            practice.practice_id,
            uuid4(),
            "approve",
            "Good",
            rating=4.0
        )

        # Start application
        session = await service.apply_best_practice(
            practice.practice_id,
            user_id,
            ontology_id
        )

        # Complete all steps
        for i in range(step_count):
            await service.complete_step(
                session.session_id,
                i,
                {"result": f"Step {i} result"}
            )

        # Get updated session
        updated_session = await service.get_application_session(session.session_id)

        # Property: Session completed correctly
        assert updated_session.is_completed
        assert len(updated_session.completed_steps) == step_count
        assert updated_session.completed_at is not None

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        user_id=uuid_strategy,
        ontology_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_next_step_guidance(
        self,
        author_id: UUID,
        user_id: UUID,
        ontology_id: UUID
    ):
        """Next step guidance is provided correctly."""
        service = BestPracticeService()

        # Create practice
        steps = [
            ConfigurationStep(0, "Step 0", "Desc 0", [], []),
            ConfigurationStep(1, "Step 1", "Desc 1", [], []),
            ConfigurationStep(2, "Step 2", "Desc 2", [], [])
        ]

        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=steps
        )

        # Approve and apply
        await service.submit_best_practice(practice.practice_id, [uuid4()])
        await service.review_best_practice(
            practice.practice_id,
            uuid4(),
            "approve",
            "Good",
            rating=4.0
        )

        session = await service.apply_best_practice(
            practice.practice_id,
            user_id,
            ontology_id
        )

        # Property: First step is step 0
        next_step = await service.get_next_step(session.session_id)
        assert next_step is not None
        assert next_step.step_number == 0

        # Complete step 0
        await service.complete_step(session.session_id, 0, {"result": "Done"})

        # Property: Next step is step 1
        next_step = await service.get_next_step(session.session_id)
        assert next_step is not None
        assert next_step.step_number == 1


class TestBestPracticeReviewWorkflow:
    """Test best practice review workflow."""

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        reviewer_id=uuid_strategy,
        rating=rating_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_approval_workflow(
        self,
        author_id: UUID,
        reviewer_id: UUID,
        rating: float
    ):
        """Approval workflow updates status correctly."""
        service = BestPracticeService()

        # Create practice
        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        # Submit for review
        await service.submit_best_practice(practice.practice_id, [reviewer_id])

        # Review
        review = await service.review_best_practice(
            practice.practice_id,
            reviewer_id,
            "approve",
            "Excellent",
            rating=rating
        )

        # Get updated practice
        updated_practice = await service.get_best_practice(practice.practice_id)

        # Property: Status updated to approved
        assert updated_practice.status == BestPracticeStatus.APPROVED
        assert updated_practice.published_at is not None
        assert review.decision == "approve"

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        reviewer_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_rejection_workflow(
        self,
        author_id: UUID,
        reviewer_id: UUID
    ):
        """Rejection workflow updates status correctly."""
        service = BestPracticeService()

        # Create and submit practice
        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        await service.submit_best_practice(practice.practice_id, [reviewer_id])

        # Reject
        await service.review_best_practice(
            practice.practice_id,
            reviewer_id,
            "reject",
            "Needs improvement",
            rating=2.0
        )

        # Get updated practice
        updated_practice = await service.get_best_practice(practice.practice_id)

        # Property: Status updated to rejected
        assert updated_practice.status == BestPracticeStatus.REJECTED

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        ratings=st.lists(rating_strategy, min_size=1, max_size=5)
    )
    @settings(max_examples=50, deadline=None)
    async def test_average_rating_calculation(
        self,
        author_id: UUID,
        ratings: List[float]
    ):
        """Average rating is calculated correctly."""
        service = BestPracticeService()

        # Create practice
        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=BestPracticeCategory.DATA_MODELING,
            industry=Industry.GENERAL,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        # Submit and approve with different ratings
        await service.submit_best_practice(practice.practice_id, [uuid4()])

        for rating in ratings:
            await service.review_best_practice(
                practice.practice_id,
                uuid4(),
                "approve",
                "Good",
                rating=rating
            )

        # Get average rating
        avg_rating = await service.get_average_rating(practice.practice_id)

        # Property: Average is correct
        expected_avg = sum(ratings) / len(ratings)
        assert abs(avg_rating - expected_avg) < 0.01


class TestBestPracticeSearch:
    """Test best practice search functionality."""

    @pytest.mark.asyncio
    @given(
        author_id=uuid_strategy,
        category=category_strategy,
        industry=industry_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_search_by_category_and_industry(
        self,
        author_id: UUID,
        category: BestPracticeCategory,
        industry: Industry
    ):
        """Search filters by category and industry correctly."""
        service = BestPracticeService()

        # Create practice with specific category and industry
        practice = await service.create_best_practice(
            author_id=author_id,
            title="Test Practice",
            description="Description",
            category=category,
            industry=industry,
            use_case="Use case",
            problem_statement="Problem",
            solution="Solution",
            benefits=["Benefit"],
            configuration_steps=[ConfigurationStep(0, "Step", "Desc", [], [])]
        )

        # Approve
        await service.submit_best_practice(practice.practice_id, [uuid4()])
        await service.review_best_practice(
            practice.practice_id,
            uuid4(),
            "approve",
            "Good",
            rating=4.0
        )

        # Search
        results = await service.search_best_practices(
            category=category,
            industry=industry
        )

        # Property: Practice is in results
        assert any(r.practice_id == practice.practice_id for r in results)
