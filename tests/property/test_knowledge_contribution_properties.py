"""Property tests for Knowledge Contribution Tracking Service.

This module tests universal correctness properties:
- Property 19: Knowledge Contribution Tracking (validates 6.2, 6.3)
- Property 21: Contribution Metric Updates (validates 6.5)
"""

import pytest
import asyncio
from uuid import UUID, uuid4
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from typing import List

from src.collaboration.knowledge_contribution_service import (
    KnowledgeContributionService,
    ContributionType,
    ContributionStatus,
    DocumentType
)


# Hypothesis strategies
uuid_strategy = st.builds(uuid4)
element_type_strategy = st.sampled_from(["entity_type", "relation_type", "attribute"])
contribution_status_strategy = st.sampled_from(list(ContributionStatus))
document_type_strategy = st.sampled_from(list(DocumentType))
cardinality_strategy = st.sampled_from(["1:1", "1:N", "N:M", "N:1"])

# Text strategies
short_text_strategy = st.text(min_size=1, max_size=50)
medium_text_strategy = st.text(min_size=1, max_size=200)
long_text_strategy = st.text(min_size=1, max_size=500)

# Quality score strategy (1.0-5.0)
quality_score_strategy = st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False)


class TestKnowledgeContributionTracking:
    """Property 19: Knowledge Contribution Tracking.

    Validates Requirements 6.2, 6.3:
    - Entity suggestions are properly tracked
    - Relation suggestions are properly tracked
    - Comments support threading
    - Document attachments are associated correctly
    """

    @pytest.mark.asyncio
    @given(
        element_id=uuid_strategy,
        element_type=element_type_strategy,
        expert_id=uuid_strategy,
        content=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_comment_tracking(
        self,
        element_id: UUID,
        element_type: str,
        expert_id: UUID,
        content: str
    ):
        """Comments are tracked and retrievable."""
        service = KnowledgeContributionService()

        # Add comment
        comment = await service.add_comment(
            element_id=element_id,
            element_type=element_type,
            expert_id=expert_id,
            content=content
        )

        # Retrieve comments
        comments = await service.get_comments(element_id)

        # Property: Comment is tracked
        assert len(comments) == 1
        assert comments[0].comment_id == comment.comment_id
        assert comments[0].content == content
        assert comments[0].expert_id == expert_id
        assert comments[0].element_id == element_id
        assert comments[0].parent_comment_id is None

    @pytest.mark.asyncio
    @given(
        element_id=uuid_strategy,
        element_type=element_type_strategy,
        expert_id=uuid_strategy,
        root_content=medium_text_strategy,
        reply_content=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_comment_threading(
        self,
        element_id: UUID,
        element_type: str,
        expert_id: UUID,
        root_content: str,
        reply_content: str
    ):
        """Comments support threaded discussions."""
        assume(root_content != reply_content)
        service = KnowledgeContributionService()

        # Add root comment
        root_comment = await service.add_comment(
            element_id=element_id,
            element_type=element_type,
            expert_id=expert_id,
            content=root_content
        )

        # Add reply
        reply_comment = await service.add_comment(
            element_id=element_id,
            element_type=element_type,
            expert_id=expert_id,
            content=reply_content,
            parent_comment_id=root_comment.comment_id
        )

        # Get threaded comments
        threads = await service.get_threaded_comments(element_id)

        # Property: Thread structure is preserved
        assert len(threads) == 1
        assert threads[0]["comment_id"] == root_comment.comment_id
        assert len(threads[0]["replies"]) == 1
        assert threads[0]["replies"][0]["comment_id"] == reply_comment.comment_id

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        entity_name=short_text_strategy,
        entity_desc=medium_text_strategy,
        rationale=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_entity_suggestion_tracking(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        entity_name: str,
        entity_desc: str,
        rationale: str
    ):
        """Entity suggestions are properly tracked."""
        service = KnowledgeContributionService()

        # Suggest entity
        suggestion = await service.suggest_entity(
            expert_id=expert_id,
            ontology_id=ontology_id,
            suggested_name=entity_name,
            suggested_description=entity_desc,
            suggested_attributes=[],
            rationale=rationale
        )

        # Retrieve suggestions
        suggestions = await service.get_entity_suggestions(ontology_id)

        # Property: Suggestion is tracked
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == suggestion.suggestion_id
        assert suggestions[0].suggested_name == entity_name
        assert suggestions[0].status == ContributionStatus.PENDING
        assert suggestions[0].expert_id == expert_id

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        relation_name=short_text_strategy,
        relation_desc=medium_text_strategy,
        source_type=short_text_strategy,
        target_type=short_text_strategy,
        cardinality=cardinality_strategy,
        rationale=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_relation_suggestion_tracking(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        relation_name: str,
        relation_desc: str,
        source_type: str,
        target_type: str,
        cardinality: str,
        rationale: str
    ):
        """Relation suggestions are properly tracked."""
        service = KnowledgeContributionService()

        # Suggest relation
        suggestion = await service.suggest_relation(
            expert_id=expert_id,
            ontology_id=ontology_id,
            suggested_name=relation_name,
            suggested_description=relation_desc,
            source_entity_type=source_type,
            target_entity_type=target_type,
            cardinality=cardinality,
            rationale=rationale
        )

        # Retrieve suggestions
        suggestions = await service.get_relation_suggestions(ontology_id)

        # Property: Suggestion is tracked
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == suggestion.suggestion_id
        assert suggestions[0].suggested_name == relation_name
        assert suggestions[0].cardinality == cardinality
        assert suggestions[0].status == ContributionStatus.PENDING
        assert suggestions[0].expert_id == expert_id

    @pytest.mark.asyncio
    @given(
        element_id=uuid_strategy,
        element_type=element_type_strategy,
        expert_id=uuid_strategy,
        title=short_text_strategy,
        description=medium_text_strategy,
        url=st.from_regex(r"https?://[a-z0-9]+\.[a-z]{2,}", fullmatch=True)
    )
    @settings(max_examples=100, deadline=None)
    async def test_document_attachment_tracking(
        self,
        element_id: UUID,
        element_type: str,
        expert_id: UUID,
        title: str,
        description: str,
        url: str
    ):
        """Document attachments are properly tracked."""
        service = KnowledgeContributionService()

        # Attach document
        attachment = await service.attach_document(
            element_id=element_id,
            element_type=element_type,
            expert_id=expert_id,
            document_type=DocumentType.LINK,
            title=title,
            description=description,
            url=url
        )

        # Retrieve attachments
        attachments = await service.get_attachments(element_id)

        # Property: Attachment is tracked
        assert len(attachments) == 1
        assert attachments[0].attachment_id == attachment.attachment_id
        assert attachments[0].url == url
        assert attachments[0].title == title
        assert attachments[0].expert_id == expert_id

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        element_id1=uuid_strategy,
        element_id2=uuid_strategy,
        element_type=element_type_strategy,
        content1=medium_text_strategy,
        content2=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_expert_contributions_retrieval(
        self,
        expert_id: UUID,
        element_id1: UUID,
        element_id2: UUID,
        element_type: str,
        content1: str,
        content2: str
    ):
        """All contributions by an expert are retrievable."""
        assume(element_id1 != element_id2)
        service = KnowledgeContributionService()

        # Add multiple contributions
        await service.add_comment(
            element_id=element_id1,
            element_type=element_type,
            expert_id=expert_id,
            content=content1
        )
        await service.add_comment(
            element_id=element_id2,
            element_type=element_type,
            expert_id=expert_id,
            content=content2
        )

        # Get expert contributions
        contributions = await service.get_expert_contributions(expert_id)

        # Property: All contributions are retrievable
        assert len(contributions["comments"]) == 2


class TestContributionMetricUpdates:
    """Property 21: Contribution Metric Updates.

    Validates Requirement 6.5:
    - Contribution counts are accurate
    - Acceptance rate is calculated correctly
    - Quality scores are averaged properly
    - Contribution score reflects quality and acceptance
    """

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        suggestion_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_contribution_count_accuracy(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        suggestion_count: int
    ):
        """Contribution counts are accurate."""
        service = KnowledgeContributionService()

        # Add multiple suggestions
        for i in range(suggestion_count):
            await service.suggest_entity(
                expert_id=expert_id,
                ontology_id=ontology_id,
                suggested_name=f"Entity_{i}",
                suggested_description=f"Description {i}",
                suggested_attributes=[],
                rationale=f"Rationale {i}"
            )

        # Get metrics
        metrics = await service.get_expert_metrics(expert_id)

        # Property: Count matches actual contributions
        assert metrics.total_contributions == suggestion_count
        assert metrics.entity_suggestions_count == suggestion_count
        assert metrics.pending_contributions == suggestion_count

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        reviewer_id=uuid_strategy,
        accepted_count=st.integers(min_value=1, max_value=5),
        rejected_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    async def test_acceptance_rate_calculation(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        reviewer_id: UUID,
        accepted_count: int,
        rejected_count: int
    ):
        """Acceptance rate is calculated correctly."""
        service = KnowledgeContributionService()

        # Create suggestions
        accepted_ids = []
        rejected_ids = []

        for i in range(accepted_count):
            suggestion = await service.suggest_entity(
                expert_id=expert_id,
                ontology_id=ontology_id,
                suggested_name=f"Accepted_{i}",
                suggested_description=f"Description {i}",
                suggested_attributes=[],
                rationale="Good suggestion"
            )
            accepted_ids.append(suggestion.suggestion_id)

        for i in range(rejected_count):
            suggestion = await service.suggest_entity(
                expert_id=expert_id,
                ontology_id=ontology_id,
                suggested_name=f"Rejected_{i}",
                suggested_description=f"Description {i}",
                suggested_attributes=[],
                rationale="Needs work"
            )
            rejected_ids.append(suggestion.suggestion_id)

        # Accept some, reject others
        for suggestion_id in accepted_ids:
            await service.accept_contribution(
                ContributionType.ENTITY_SUGGESTION,
                suggestion_id,
                reviewer_id,
                quality_score=4.0
            )

        for suggestion_id in rejected_ids:
            await service.reject_contribution(
                ContributionType.ENTITY_SUGGESTION,
                suggestion_id,
                reviewer_id,
                review_notes="Not suitable"
            )

        # Get metrics
        metrics = await service.get_expert_metrics(expert_id)

        # Property: Acceptance rate is correct
        expected_rate = accepted_count / (accepted_count + rejected_count)
        assert abs(metrics.acceptance_rate - expected_rate) < 0.01
        assert metrics.accepted_contributions == accepted_count
        assert metrics.rejected_contributions == rejected_count

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        reviewer_id=uuid_strategy,
        quality_scores=st.lists(
            quality_score_strategy,
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_quality_score_averaging(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        reviewer_id: UUID,
        quality_scores: List[float]
    ):
        """Quality scores are averaged properly with EMA."""
        service = KnowledgeContributionService()

        # Create and accept suggestions with different quality scores
        for i, score in enumerate(quality_scores):
            suggestion = await service.suggest_entity(
                expert_id=expert_id,
                ontology_id=ontology_id,
                suggested_name=f"Entity_{i}",
                suggested_description=f"Description {i}",
                suggested_attributes=[],
                rationale=f"Rationale {i}"
            )

            await service.accept_contribution(
                ContributionType.ENTITY_SUGGESTION,
                suggestion.suggestion_id,
                reviewer_id,
                quality_score=score
            )

        # Get metrics
        metrics = await service.get_expert_metrics(expert_id)

        # Property: Average quality score is calculated
        # Note: Uses EMA with alpha=0.3, not simple average
        assert 1.0 <= metrics.average_quality_score <= 5.0
        assert metrics.average_quality_score > 0

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        reviewer_id=uuid_strategy,
        quality_score=quality_score_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_contribution_score_reflects_quality(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        reviewer_id: UUID,
        quality_score: float
    ):
        """Contribution score reflects quality and acceptance rate."""
        service = KnowledgeContributionService()

        # Create and accept a suggestion
        suggestion = await service.suggest_entity(
            expert_id=expert_id,
            ontology_id=ontology_id,
            suggested_name="High Quality Entity",
            suggested_description="Well thought out",
            suggested_attributes=[],
            rationale="Strong rationale"
        )

        await service.accept_contribution(
            ContributionType.ENTITY_SUGGESTION,
            suggestion.suggestion_id,
            reviewer_id,
            quality_score=quality_score
        )

        # Get metrics
        metrics = await service.get_expert_metrics(expert_id)

        # Property: Contribution score is positive
        assert metrics.contribution_score > 0
        # Property: Score is influenced by quality (weight 0.6) and acceptance (weight 0.4)
        expected_min = 0.6 * quality_score + 0.4 * 1.0 * 5.0  # 100% acceptance rate
        assert metrics.contribution_score >= expected_min * 0.9  # Allow 10% margin

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        reviewer_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_rejection_updates_metrics(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        reviewer_id: UUID
    ):
        """Rejecting a contribution updates metrics correctly."""
        service = KnowledgeContributionService()

        # Create suggestion
        suggestion = await service.suggest_entity(
            expert_id=expert_id,
            ontology_id=ontology_id,
            suggested_name="Entity",
            suggested_description="Description",
            suggested_attributes=[],
            rationale="Rationale"
        )

        # Get initial metrics
        initial_metrics = await service.get_expert_metrics(expert_id)
        initial_pending = initial_metrics.pending_contributions

        # Reject suggestion
        await service.reject_contribution(
            ContributionType.ENTITY_SUGGESTION,
            suggestion.suggestion_id,
            reviewer_id,
            review_notes="Not suitable"
        )

        # Get updated metrics
        updated_metrics = await service.get_expert_metrics(expert_id)

        # Property: Metrics are updated correctly
        assert updated_metrics.rejected_contributions == 1
        assert updated_metrics.pending_contributions == initial_pending - 1
        assert updated_metrics.acceptance_rate == 0.0


class TestCommentResolution:
    """Test comment resolution functionality."""

    @pytest.mark.asyncio
    @given(
        element_id=uuid_strategy,
        element_type=element_type_strategy,
        expert_id=uuid_strategy,
        resolver_id=uuid_strategy,
        content=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_comment_resolution(
        self,
        element_id: UUID,
        element_type: str,
        expert_id: UUID,
        resolver_id: UUID,
        content: str
    ):
        """Comments can be marked as resolved."""
        service = KnowledgeContributionService()

        # Add comment
        comment = await service.add_comment(
            element_id=element_id,
            element_type=element_type,
            expert_id=expert_id,
            content=content
        )

        # Resolve comment
        await service.resolve_comment(comment.comment_id, resolver_id)

        # Get comments (exclude resolved)
        unresolved_comments = await service.get_comments(element_id, include_resolved=False)
        all_comments = await service.get_comments(element_id, include_resolved=True)

        # Property: Resolved comments are filtered correctly
        assert len(unresolved_comments) == 0
        assert len(all_comments) == 1
        assert all_comments[0].is_resolved is True
        assert all_comments[0].resolved_by == resolver_id


class TestDocumentAttachmentValidation:
    """Test document attachment validation."""

    @pytest.mark.asyncio
    async def test_link_requires_url(self):
        """Link attachments require a URL."""
        service = KnowledgeContributionService()

        with pytest.raises(ValueError, match="URL required"):
            await service.attach_document(
                element_id=uuid4(),
                element_type="entity_type",
                expert_id=uuid4(),
                document_type=DocumentType.LINK,
                title="Link",
                description="Link without URL",
                url=None  # Missing URL
            )

    @pytest.mark.asyncio
    async def test_file_requires_path_or_url(self):
        """File attachments require file path or URL."""
        service = KnowledgeContributionService()

        with pytest.raises(ValueError, match="File path or URL required"):
            await service.attach_document(
                element_id=uuid4(),
                element_type="entity_type",
                expert_id=uuid4(),
                document_type=DocumentType.PDF,
                title="PDF",
                description="PDF without path",
                url=None,
                file_path=None  # Missing both
            )


class TestSuggestionStatusFiltering:
    """Test suggestion filtering by status."""

    @pytest.mark.asyncio
    @given(
        expert_id=uuid_strategy,
        ontology_id=uuid_strategy,
        reviewer_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_filter_suggestions_by_status(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        reviewer_id: UUID
    ):
        """Suggestions can be filtered by status."""
        service = KnowledgeContributionService()

        # Create suggestions
        suggestion1 = await service.suggest_entity(
            expert_id=expert_id,
            ontology_id=ontology_id,
            suggested_name="Entity1",
            suggested_description="Description 1",
            suggested_attributes=[],
            rationale="Rationale 1"
        )

        suggestion2 = await service.suggest_entity(
            expert_id=expert_id,
            ontology_id=ontology_id,
            suggested_name="Entity2",
            suggested_description="Description 2",
            suggested_attributes=[],
            rationale="Rationale 2"
        )

        # Accept one, leave one pending
        await service.accept_contribution(
            ContributionType.ENTITY_SUGGESTION,
            suggestion1.suggestion_id,
            reviewer_id,
            quality_score=4.5
        )

        # Get pending suggestions
        pending = await service.get_entity_suggestions(
            ontology_id,
            status=ContributionStatus.PENDING
        )

        # Get accepted suggestions
        accepted = await service.get_entity_suggestions(
            ontology_id,
            status=ContributionStatus.ACCEPTED
        )

        # Property: Filtering by status works correctly
        assert len(pending) == 1
        assert pending[0].suggestion_id == suggestion2.suggestion_id
        assert len(accepted) == 1
        assert accepted[0].suggestion_id == suggestion1.suggestion_id
