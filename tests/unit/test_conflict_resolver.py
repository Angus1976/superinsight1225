"""
Unit tests for Conflict Resolver.

Tests the ConflictResolver class for:
- Conflict detection
- Voting mechanism
- Expert resolution
- Conflict reporting

Validates: Requirements 5.4 (Conflict Resolution)
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.collaboration.conflict_resolver import ConflictResolver


class TestConflictDetection:
    """Tests for conflict detection functionality."""

    @pytest.fixture
    def resolver(self):
        """Create a ConflictResolver instance for testing."""
        return ConflictResolver()

    @pytest.mark.asyncio
    async def test_detect_no_conflicts_identical_annotations(self, resolver):
        """Test that identical annotations produce no conflicts."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER", "start": 0, "end": 5}},
            {"id": "v2", "annotation": {"label": "PER", "start": 0, "end": 5}},
        ]
        
        conflicts = await resolver.detect_conflicts("task_1", versions)
        
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_label_mismatch_conflict(self, resolver):
        """Test detection of label mismatch conflicts."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER", "start": 0, "end": 5}},
            {"id": "v2", "annotation": {"label": "ORG", "start": 0, "end": 5}},
        ]
        
        conflicts = await resolver.detect_conflicts("task_1", versions)
        
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "label_mismatch"
        assert conflicts[0]["status"] == "unresolved"

    @pytest.mark.asyncio
    async def test_detect_boundary_mismatch_conflict(self, resolver):
        """Test detection of boundary mismatch conflicts."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER", "start": 0, "end": 5}},
            {"id": "v2", "annotation": {"label": "PER", "start": 0, "end": 10}},
        ]
        
        conflicts = await resolver.detect_conflicts("task_1", versions)
        
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "boundary_mismatch"

    @pytest.mark.asyncio
    async def test_detect_content_mismatch_conflict(self, resolver):
        """Test detection of content mismatch conflicts."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER", "start": 0, "end": 5, "text": "John"}},
            {"id": "v2", "annotation": {"label": "PER", "start": 0, "end": 5, "text": "Jane"}},
        ]
        
        conflicts = await resolver.detect_conflicts("task_1", versions)
        
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "content_mismatch"

    @pytest.mark.asyncio
    async def test_detect_multiple_conflicts(self, resolver):
        """Test detection of multiple conflicts from multiple versions."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
            {"id": "v3", "annotation": {"label": "LOC"}},
        ]
        
        conflicts = await resolver.detect_conflicts("task_1", versions)
        
        # 3 versions should produce 3 pairwise conflicts
        assert len(conflicts) == 3

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_notification(self):
        """Test that conflicts trigger notifications."""
        notification_service = AsyncMock()
        resolver = ConflictResolver(notification_service=notification_service)
        
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        
        await resolver.detect_conflicts("task_1", versions)
        
        notification_service.notify_conflicts.assert_called_once_with("task_1", 1)

    @pytest.mark.asyncio
    async def test_detect_conflicts_empty_versions(self, resolver):
        """Test detection with empty version list."""
        conflicts = await resolver.detect_conflicts("task_1", [])
        
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_conflicts_single_version(self, resolver):
        """Test detection with single version (no conflicts possible)."""
        versions = [{"id": "v1", "annotation": {"label": "PER"}}]
        
        conflicts = await resolver.detect_conflicts("task_1", versions)
        
        assert len(conflicts) == 0


class TestVotingMechanism:
    """Tests for voting-based conflict resolution."""

    @pytest.fixture
    def resolver(self):
        """Create a ConflictResolver instance for testing."""
        return ConflictResolver()

    @pytest_asyncio.fixture
    async def conflict_id(self, resolver):
        """Create a conflict and return its ID."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        conflicts = await resolver.detect_conflicts("task_1", versions)
        return conflicts[0]["id"]

    @pytest.mark.asyncio
    async def test_vote_creates_vote_record(self, resolver, conflict_id):
        """Test that voting creates a vote record."""
        vote = await resolver.vote(conflict_id, "user_1", "version1")
        
        assert vote["conflict_id"] == conflict_id
        assert vote["voter_id"] == "user_1"
        assert vote["choice"] == "version1"
        assert "voted_at" in vote

    @pytest.mark.asyncio
    async def test_vote_updates_conflict_status(self, resolver, conflict_id):
        """Test that voting updates conflict status to 'voting'."""
        await resolver.vote(conflict_id, "user_1", "version1")
        
        conflict = await resolver.get_conflict(conflict_id)
        assert conflict["status"] == "voting"

    @pytest.mark.asyncio
    async def test_vote_update_existing_vote(self, resolver, conflict_id):
        """Test that voting again updates existing vote."""
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_1", "version2")
        
        votes = await resolver.get_votes(conflict_id)
        
        assert len(votes) == 1
        assert votes[0]["choice"] == "version2"

    @pytest.mark.asyncio
    async def test_get_votes(self, resolver, conflict_id):
        """Test getting all votes for a conflict."""
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_2", "version2")
        await resolver.vote(conflict_id, "user_3", "version1")
        
        votes = await resolver.get_votes(conflict_id)
        
        assert len(votes) == 3

    @pytest.mark.asyncio
    async def test_resolve_by_voting_success(self, resolver, conflict_id):
        """Test successful voting resolution."""
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_2", "version1")
        await resolver.vote(conflict_id, "user_3", "version2")
        
        resolution = await resolver.resolve_by_voting(conflict_id, min_votes=3)
        
        assert resolution["method"] == "voting"
        assert resolution["result"]["winner"] == "version1"
        assert resolution["vote_counts"]["version1"] == 2
        assert resolution["vote_counts"]["version2"] == 1

    @pytest.mark.asyncio
    async def test_resolve_by_voting_updates_status(self, resolver, conflict_id):
        """Test that voting resolution updates conflict status."""
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_2", "version1")
        await resolver.vote(conflict_id, "user_3", "version1")
        
        await resolver.resolve_by_voting(conflict_id, min_votes=3)
        
        conflict = await resolver.get_conflict(conflict_id)
        assert conflict["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_by_voting_insufficient_votes(self, resolver, conflict_id):
        """Test that resolution fails with insufficient votes."""
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_2", "version1")
        
        with pytest.raises(ValueError, match="Not enough votes"):
            await resolver.resolve_by_voting(conflict_id, min_votes=3)

    @pytest.mark.asyncio
    async def test_resolve_by_voting_tie_breaker(self, resolver, conflict_id):
        """Test voting resolution with tie (first most common wins)."""
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_2", "version2")
        await resolver.vote(conflict_id, "user_3", "version1")
        await resolver.vote(conflict_id, "user_4", "version2")
        
        resolution = await resolver.resolve_by_voting(conflict_id, min_votes=4)
        
        # Counter.most_common returns first encountered in case of tie
        assert resolution["result"]["winner"] in ["version1", "version2"]


class TestExpertResolution:
    """Tests for expert-based conflict resolution."""

    @pytest.fixture
    def resolver(self):
        """Create a ConflictResolver instance for testing."""
        return ConflictResolver()

    @pytest_asyncio.fixture
    async def conflict_id(self, resolver):
        """Create a conflict and return its ID."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        conflicts = await resolver.detect_conflicts("task_1", versions)
        return conflicts[0]["id"]

    @pytest.mark.asyncio
    async def test_resolve_by_expert(self, resolver, conflict_id):
        """Test expert resolution."""
        decision = {"chosen_version": "v1", "reason": "More accurate"}
        
        resolution = await resolver.resolve_by_expert(
            conflict_id,
            expert_id="expert_1",
            decision=decision
        )
        
        assert resolution["method"] == "expert"
        assert resolution["expert_id"] == "expert_1"
        assert resolution["result"] == decision

    @pytest.mark.asyncio
    async def test_resolve_by_expert_updates_status(self, resolver, conflict_id):
        """Test that expert resolution updates conflict status."""
        await resolver.resolve_by_expert(
            conflict_id,
            expert_id="expert_1",
            decision={"chosen_version": "v1"}
        )
        
        conflict = await resolver.get_conflict(conflict_id)
        assert conflict["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_get_resolution(self, resolver, conflict_id):
        """Test getting resolution after expert decision."""
        decision = {"chosen_version": "v1"}
        await resolver.resolve_by_expert(conflict_id, "expert_1", decision)
        
        resolution = await resolver.get_resolution(conflict_id)
        
        assert resolution is not None
        assert resolution["expert_id"] == "expert_1"


class TestConflictReporting:
    """Tests for conflict report generation."""

    @pytest.fixture
    def resolver(self):
        """Create a ConflictResolver instance for testing."""
        return ConflictResolver()

    @pytest.mark.asyncio
    async def test_generate_empty_report(self, resolver):
        """Test report generation with no conflicts."""
        report = await resolver.generate_conflict_report("project_1")
        
        assert report["project_id"] == "project_1"
        assert report["total_conflicts"] == 0
        assert report["resolved_conflicts"] == 0
        assert report["unresolved_conflicts"] == 0

    @pytest.mark.asyncio
    async def test_generate_report_with_conflicts(self, resolver):
        """Test report generation with conflicts."""
        # Create some conflicts
        versions1 = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        versions2 = [
            {"id": "v3", "annotation": {"label": "LOC", "start": 0, "end": 5}},
            {"id": "v4", "annotation": {"label": "LOC", "start": 0, "end": 10}},
        ]
        
        await resolver.detect_conflicts("task_1", versions1)
        await resolver.detect_conflicts("task_2", versions2)
        
        report = await resolver.generate_conflict_report("project_1")
        
        assert report["total_conflicts"] == 2
        assert report["unresolved_conflicts"] == 2
        assert "label_mismatch" in report["conflict_types"]
        assert "boundary_mismatch" in report["conflict_types"]

    @pytest.mark.asyncio
    async def test_generate_report_with_resolutions(self, resolver):
        """Test report generation with resolved conflicts."""
        # Create and resolve conflicts
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        conflicts = await resolver.detect_conflicts("task_1", versions)
        conflict_id = conflicts[0]["id"]
        
        # Resolve by voting
        await resolver.vote(conflict_id, "user_1", "version1")
        await resolver.vote(conflict_id, "user_2", "version1")
        await resolver.vote(conflict_id, "user_3", "version1")
        await resolver.resolve_by_voting(conflict_id, min_votes=3)
        
        report = await resolver.generate_conflict_report("project_1")
        
        assert report["total_conflicts"] == 1
        assert report["resolved_conflicts"] == 1
        assert report["unresolved_conflicts"] == 0
        assert report["resolution_methods"]["voting"] == 1

    @pytest.mark.asyncio
    async def test_generate_report_mixed_resolutions(self, resolver):
        """Test report with both voting and expert resolutions."""
        # Create two conflicts
        versions1 = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        versions2 = [
            {"id": "v3", "annotation": {"label": "LOC"}},
            {"id": "v4", "annotation": {"label": "DATE"}},
        ]
        
        conflicts1 = await resolver.detect_conflicts("task_1", versions1)
        conflicts2 = await resolver.detect_conflicts("task_2", versions2)
        
        # Resolve first by voting
        conflict_id1 = conflicts1[0]["id"]
        await resolver.vote(conflict_id1, "user_1", "version1")
        await resolver.vote(conflict_id1, "user_2", "version1")
        await resolver.vote(conflict_id1, "user_3", "version1")
        await resolver.resolve_by_voting(conflict_id1, min_votes=3)
        
        # Resolve second by expert
        conflict_id2 = conflicts2[0]["id"]
        await resolver.resolve_by_expert(conflict_id2, "expert_1", {"chosen": "v3"})
        
        report = await resolver.generate_conflict_report("project_1")
        
        assert report["total_conflicts"] == 2
        assert report["resolved_conflicts"] == 2
        assert report["resolution_methods"]["voting"] == 1
        assert report["resolution_methods"]["expert"] == 1


class TestConflictRetrieval:
    """Tests for conflict retrieval functionality."""

    @pytest.fixture
    def resolver(self):
        """Create a ConflictResolver instance for testing."""
        return ConflictResolver()

    @pytest.mark.asyncio
    async def test_get_conflict_exists(self, resolver):
        """Test getting an existing conflict."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        conflicts = await resolver.detect_conflicts("task_1", versions)
        conflict_id = conflicts[0]["id"]
        
        conflict = await resolver.get_conflict(conflict_id)
        
        assert conflict is not None
        assert conflict["id"] == conflict_id
        assert conflict["task_id"] == "task_1"

    @pytest.mark.asyncio
    async def test_get_conflict_not_exists(self, resolver):
        """Test getting a non-existent conflict."""
        conflict = await resolver.get_conflict("non_existent_id")
        
        assert conflict is None

    @pytest.mark.asyncio
    async def test_get_votes_no_votes(self, resolver):
        """Test getting votes when none exist."""
        votes = await resolver.get_votes("non_existent_conflict")
        
        assert votes == []

    @pytest.mark.asyncio
    async def test_get_resolution_not_resolved(self, resolver):
        """Test getting resolution for unresolved conflict."""
        versions = [
            {"id": "v1", "annotation": {"label": "PER"}},
            {"id": "v2", "annotation": {"label": "ORG"}},
        ]
        conflicts = await resolver.detect_conflicts("task_1", versions)
        conflict_id = conflicts[0]["id"]
        
        resolution = await resolver.get_resolution(conflict_id)
        
        assert resolution is None
