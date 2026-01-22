"""
Property-based tests for Expert Management Service.

Tests Properties from ontology-expert-collaboration specification:
- Property 1: Expert Profile Data Integrity
- Property 2: Expertise Area Validation
- Property 28: Expert Recommendation Relevance
"""

import asyncio
from datetime import datetime
from typing import List, Set
from uuid import UUID, uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

# Import the module under test
import sys
sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tests/", 1)[0] + "/src")

from collaboration.expert_service import (
    ExpertService,
    ExpertProfile,
    ExpertProfileCreate,
    ExpertProfileUpdate,
    ExpertSearchFilter,
    ExpertRecommendation,
    ContributionMetrics,
    ExpertiseArea,
    CertificationType,
    ExpertStatus,
    AvailabilityLevel,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def expertise_area_strategy(draw) -> ExpertiseArea:
    """Generate valid expertise area."""
    return draw(st.sampled_from(list(ExpertiseArea)))


@st.composite
def expertise_areas_strategy(draw) -> List[ExpertiseArea]:
    """Generate list of unique expertise areas."""
    areas = draw(st.lists(
        expertise_area_strategy(),
        min_size=1,
        max_size=5,
        unique=True,
    ))
    return areas


@st.composite
def certification_strategy(draw) -> CertificationType:
    """Generate valid certification type."""
    return draw(st.sampled_from(list(CertificationType)))


@st.composite
def certifications_strategy(draw) -> List[CertificationType]:
    """Generate list of certifications."""
    return draw(st.lists(
        certification_strategy(),
        min_size=0,
        max_size=3,
        unique=True,
    ))


@st.composite
def language_strategy(draw) -> str:
    """Generate language code."""
    return draw(st.sampled_from(["zh-CN", "en-US", "ja-JP", "ko-KR", "de-DE"]))


@st.composite
def languages_strategy(draw) -> List[str]:
    """Generate list of languages."""
    return draw(st.lists(
        language_strategy(),
        min_size=1,
        max_size=3,
        unique=True,
    ))


@st.composite
def expert_name_strategy(draw) -> str:
    """Generate expert name."""
    first_names = ["张三", "李四", "王五", "John", "Jane", "Alice", "Bob"]
    last_names = ["Engineer", "Architect", "Specialist", "Expert"]
    first = draw(st.sampled_from(first_names))
    last = draw(st.sampled_from(last_names))
    return f"{first} {last}"


@st.composite
def email_strategy(draw) -> str:
    """Generate unique email."""
    unique_id = draw(st.integers(min_value=1, max_value=1000000))
    domain = draw(st.sampled_from(["example.com", "test.org", "company.cn"]))
    return f"expert{unique_id}@{domain}"


@st.composite
def expert_profile_create_strategy(draw) -> ExpertProfileCreate:
    """Generate expert profile creation data."""
    return ExpertProfileCreate(
        name=draw(expert_name_strategy()),
        email=draw(email_strategy()),
        expertise_areas=draw(expertise_areas_strategy()),
        certifications=draw(certifications_strategy()),
        languages=draw(languages_strategy()),
        department=draw(st.one_of(
            st.none(),
            st.sampled_from(["Engineering", "Research", "Operations"]),
        )),
        title=draw(st.one_of(
            st.none(),
            st.sampled_from(["Senior Engineer", "Architect", "Manager"]),
        )),
        bio=draw(st.one_of(st.none(), st.text(min_size=10, max_size=100))),
    )


@st.composite
def quality_score_strategy(draw) -> float:
    """Generate quality score."""
    return draw(st.floats(min_value=0.0, max_value=100.0))


# =============================================================================
# Property 1: Expert Profile Data Integrity
# =============================================================================

class TestExpertProfileDataIntegrity:
    """
    Property 1: Expert Profile Data Integrity

    Validates that:
    1. Created profiles contain all required fields
    2. Email uniqueness is enforced
    3. Updated profiles preserve data correctly
    4. Deleted profiles are properly removed
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return ExpertService()

    @given(profile_data=expert_profile_create_strategy())
    @settings(max_examples=30, deadline=None)
    def test_created_profile_contains_all_fields(
        self,
        profile_data: ExpertProfileCreate,
    ):
        """Property: Created profiles contain all input data."""
        service = ExpertService()

        async def run_test():
            profile = await service.create_expert(profile_data)

            assert profile.name == profile_data.name
            assert profile.email == profile_data.email.lower()
            assert set(profile.expertise_areas) == set(profile_data.expertise_areas)
            assert set(profile.certifications) == set(profile_data.certifications)
            assert set(profile.languages) == set(profile_data.languages)
            assert profile.department == profile_data.department
            assert profile.title == profile_data.title

        asyncio.run(run_test())

    @given(
        profile1_data=expert_profile_create_strategy(),
        profile2_data=expert_profile_create_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_email_uniqueness_enforced(
        self,
        profile1_data: ExpertProfileCreate,
        profile2_data: ExpertProfileCreate,
    ):
        """Property: Email uniqueness is enforced."""
        service = ExpertService()

        # Make emails the same
        profile2_data.email = profile1_data.email

        async def run_test():
            await service.create_expert(profile1_data)

            # Second creation with same email should fail
            with pytest.raises(ValueError, match="already exists"):
                await service.create_expert(profile2_data)

        asyncio.run(run_test())

    @given(
        profile_data=expert_profile_create_strategy(),
        new_name=expert_name_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_update_preserves_unchanged_fields(
        self,
        profile_data: ExpertProfileCreate,
        new_name: str,
    ):
        """Property: Update preserves fields not being updated."""
        service = ExpertService()

        async def run_test():
            profile = await service.create_expert(profile_data)
            original_email = profile.email
            original_expertise = profile.expertise_areas

            update_data = ExpertProfileUpdate(name=new_name)
            updated = await service.update_expert(profile.id, update_data)

            assert updated is not None
            assert updated.name == new_name
            assert updated.email == original_email  # Preserved
            assert updated.expertise_areas == original_expertise  # Preserved

        asyncio.run(run_test())

    @given(profile_data=expert_profile_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_deleted_profile_not_retrievable(
        self,
        profile_data: ExpertProfileCreate,
    ):
        """Property: Deleted profiles cannot be retrieved."""
        service = ExpertService()

        async def run_test():
            profile = await service.create_expert(profile_data)
            profile_id = profile.id

            # Delete
            deleted = await service.delete_expert(profile_id)
            assert deleted is True

            # Cannot retrieve
            result = await service.get_expert(profile_id)
            assert result is None

        asyncio.run(run_test())


# =============================================================================
# Property 2: Expertise Area Validation
# =============================================================================

class TestExpertiseAreaValidation:
    """
    Property 2: Expertise Area Validation

    Validates that:
    1. Only valid expertise areas are accepted
    2. At least one expertise area is required
    3. Duplicate expertise areas are rejected
    """

    @given(areas=expertise_areas_strategy())
    @settings(max_examples=30, deadline=None)
    def test_valid_expertise_areas_accepted(
        self,
        areas: List[ExpertiseArea],
    ):
        """Property: Valid expertise areas are accepted."""
        # This should not raise
        profile = ExpertProfileCreate(
            name="Test Expert",
            email=f"test{uuid4().hex[:8]}@example.com",
            expertise_areas=areas,
        )
        assert len(profile.expertise_areas) == len(areas)

    def test_empty_expertise_areas_rejected(self):
        """Property: Empty expertise areas list is rejected."""
        with pytest.raises(ValueError):
            ExpertProfileCreate(
                name="Test Expert",
                email="test@example.com",
                expertise_areas=[],
            )

    @given(area=expertise_area_strategy())
    @settings(max_examples=20, deadline=None)
    def test_duplicate_expertise_areas_rejected(
        self,
        area: ExpertiseArea,
    ):
        """Property: Duplicate expertise areas are rejected."""
        with pytest.raises(ValueError, match="unique"):
            ExpertProfileCreate(
                name="Test Expert",
                email="test@example.com",
                expertise_areas=[area, area],  # Duplicate
            )


# =============================================================================
# Property 28: Expert Recommendation Relevance
# =============================================================================

class TestExpertRecommendationRelevance:
    """
    Property 28: Expert Recommendation Relevance

    Validates that:
    1. Recommended experts have matching expertise
    2. Experts are ranked by relevance (expertise match, quality, availability)
    3. Fallback recommendations include related expertise areas
    4. Empty results when no matching experts
    """

    @pytest.fixture
    def service_with_experts(self):
        """Create service with pre-populated experts."""
        service = ExpertService()

        async def setup():
            # Finance expert
            await service.create_expert(ExpertProfileCreate(
                name="Finance Expert",
                email="finance@test.com",
                expertise_areas=[ExpertiseArea.FINANCE, ExpertiseArea.COMPLIANCE],
            ))
            # Healthcare expert
            await service.create_expert(ExpertProfileCreate(
                name="Healthcare Expert",
                email="healthcare@test.com",
                expertise_areas=[ExpertiseArea.HEALTHCARE, ExpertiseArea.PRIVACY],
            ))
            # Data expert
            await service.create_expert(ExpertProfileCreate(
                name="Data Expert",
                email="data@test.com",
                expertise_areas=[ExpertiseArea.DATA_MODELING, ExpertiseArea.KNOWLEDGE_GRAPH],
            ))
            return service

        return asyncio.run(setup())

    @given(
        required_expertise=expertise_areas_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_recommended_experts_have_matching_expertise(
        self,
        required_expertise: List[ExpertiseArea],
    ):
        """Property: All recommended experts have at least one matching expertise."""
        service = ExpertService()

        async def run_test():
            # Create experts with various expertise
            for i, area in enumerate(list(ExpertiseArea)[:5]):
                await service.create_expert(ExpertProfileCreate(
                    name=f"Expert {i}",
                    email=f"expert{i}@test.com",
                    expertise_areas=[area],
                ))

            recommendations = await service.recommend_experts(
                required_expertise=required_expertise,
                max_results=10,
                include_fallback=False,
            )

            # All non-fallback recommendations must have matching expertise
            required_set = set(required_expertise)
            for rec in recommendations:
                if not rec.is_fallback:
                    matching = set(rec.matching_expertise)
                    assert matching.issubset(required_set), \
                        f"Matching expertise {matching} not subset of required {required_set}"

        asyncio.run(run_test())

    @given(
        required_expertise=expertise_areas_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_recommendations_sorted_by_score(
        self,
        required_expertise: List[ExpertiseArea],
    ):
        """Property: Recommendations are sorted by overall score (descending)."""
        service = ExpertService()

        async def run_test():
            # Create experts with various expertise
            for i, area in enumerate(list(ExpertiseArea)[:5]):
                await service.create_expert(ExpertProfileCreate(
                    name=f"Expert {i}",
                    email=f"expert{i}@test.com",
                    expertise_areas=[area],
                ))

            recommendations = await service.recommend_experts(
                required_expertise=required_expertise,
                max_results=10,
            )

            if len(recommendations) > 1:
                scores = [r.overall_score for r in recommendations]
                assert scores == sorted(scores, reverse=True), \
                    "Recommendations not sorted by score"

        asyncio.run(run_test())

    def test_fallback_includes_related_expertise(self):
        """Property: Fallback recommendations include related expertise areas."""
        service = ExpertService()

        async def run_test():
            # Create expert with related expertise only
            # COMPLIANCE is related to FINANCE
            await service.create_expert(ExpertProfileCreate(
                name="Compliance Expert",
                email="compliance@test.com",
                expertise_areas=[ExpertiseArea.COMPLIANCE],
            ))

            # Search for FINANCE (should find COMPLIANCE via fallback)
            recommendations = await service.recommend_experts(
                required_expertise=[ExpertiseArea.FINANCE],
                max_results=5,
                include_fallback=True,
            )

            # Should have fallback recommendation
            fallback_recs = [r for r in recommendations if r.is_fallback]
            assert len(fallback_recs) > 0, "No fallback recommendations found"

        asyncio.run(run_test())

    @given(required_expertise=expertise_areas_strategy())
    @settings(max_examples=20, deadline=None)
    def test_empty_results_when_no_matching_experts(
        self,
        required_expertise: List[ExpertiseArea],
    ):
        """Property: Empty results returned when no experts match."""
        service = ExpertService()

        async def run_test():
            # No experts added
            recommendations = await service.recommend_experts(
                required_expertise=required_expertise,
                max_results=5,
                include_fallback=False,
            )

            assert len(recommendations) == 0

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Contribution Metrics
# =============================================================================

class TestContributionMetrics:
    """
    Tests for contribution metrics update and calculation.
    """

    @given(
        initial_score=quality_score_strategy(),
        new_score=quality_score_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_quality_score_updates_correctly(
        self,
        initial_score: float,
        new_score: float,
    ):
        """Property: Quality score updates with exponential moving average."""
        service = ExpertService()

        async def run_test():
            profile = await service.create_expert(ExpertProfileCreate(
                name="Test Expert",
                email=f"test{uuid4().hex[:8]}@test.com",
                expertise_areas=[ExpertiseArea.FINANCE],
            ))

            # Update with first score
            await service.update_contribution_metrics(
                profile.id,
                "entity",
                accepted=True,
                quality_score=initial_score,
            )

            # Update with second score
            metrics = await service.update_contribution_metrics(
                profile.id,
                "entity",
                accepted=True,
                quality_score=new_score,
            )

            assert metrics is not None
            # Quality score should be between initial and new (EMA)
            min_score = min(initial_score, new_score)
            max_score = max(initial_score, new_score)
            assert min_score <= metrics.quality_score <= max_score

        asyncio.run(run_test())

    @given(
        accepted_count=st.integers(min_value=1, max_value=50),
        rejected_count=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=20, deadline=None)
    def test_acceptance_rate_calculated_correctly(
        self,
        accepted_count: int,
        rejected_count: int,
    ):
        """Property: Acceptance rate is calculated correctly."""
        service = ExpertService()

        async def run_test():
            profile = await service.create_expert(ExpertProfileCreate(
                name="Test Expert",
                email=f"test{uuid4().hex[:8]}@test.com",
                expertise_areas=[ExpertiseArea.FINANCE],
            ))

            # Add accepted contributions
            for _ in range(accepted_count):
                await service.update_contribution_metrics(
                    profile.id, "entity", accepted=True
                )

            # Add rejected contributions
            for _ in range(rejected_count):
                await service.update_contribution_metrics(
                    profile.id, "entity", accepted=False
                )

            metrics = await service.get_contribution_metrics(profile.id)

            assert metrics is not None
            assert metrics.accepted_contributions == accepted_count
            assert metrics.rejected_contributions == rejected_count

            expected_rate = accepted_count / (accepted_count + rejected_count) * 100
            assert abs(metrics.acceptance_rate - expected_rate) < 0.01

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Search and Filtering
# =============================================================================

class TestSearchAndFiltering:
    """
    Tests for expert search and filtering functionality.
    """

    @given(
        filter_area=expertise_area_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_filter_by_expertise_returns_matching_experts(
        self,
        filter_area: ExpertiseArea,
    ):
        """Property: Filtering by expertise returns only matching experts."""
        service = ExpertService()

        async def run_test():
            # Create experts with different expertise
            matching_expert = await service.create_expert(ExpertProfileCreate(
                name="Matching Expert",
                email=f"match{uuid4().hex[:8]}@test.com",
                expertise_areas=[filter_area],
            ))

            # Create non-matching expert with different area
            other_areas = [a for a in ExpertiseArea if a != filter_area]
            if other_areas:
                await service.create_expert(ExpertProfileCreate(
                    name="Other Expert",
                    email=f"other{uuid4().hex[:8]}@test.com",
                    expertise_areas=[other_areas[0]],
                ))

            # Filter
            filter_params = ExpertSearchFilter(expertise_areas=[filter_area])
            results = await service.list_experts(filter_params=filter_params)

            # All results should have the filter area
            for expert in results:
                assert filter_area in expert.expertise_areas

        asyncio.run(run_test())


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
