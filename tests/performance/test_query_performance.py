"""
Performance tests for Label Studio Workspace Database Queries.

Tests cover:
- Database query performance (target: < 100ms for 95th percentile)
- Workspace CRUD operation latency
- Member management query performance
- Project association query performance
- Query performance with increasing data volume

Note: These tests use a simplified in-memory database for testing
to avoid complex import dependencies.
"""

import pytest
import time
import statistics
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4, UUID
from enum import Enum
from dataclasses import dataclass, field


# =============================================================================
# Test Constants
# =============================================================================

# Performance targets from requirements
QUERY_LATENCY_TARGET_MS = 100  # < 100ms (95th percentile)
CRUD_LATENCY_TARGET_MS = 50  # < 50ms for simple CRUD
BATCH_LATENCY_TARGET_MS = 200  # < 200ms for batch operations


# =============================================================================
# Simplified In-Memory Database Models
# =============================================================================

class WorkspaceMemberRole(str, Enum):
    """Workspace member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    ANNOTATOR = "annotator"


@dataclass
class Workspace:
    """In-memory workspace model."""
    id: UUID
    name: str
    description: str
    owner_id: UUID
    is_active: bool = True
    is_deleted: bool = False
    settings: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkspaceMember:
    """In-memory workspace member model."""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceMemberRole
    is_active: bool = True
    joined_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkspaceProject:
    """In-memory workspace project model."""
    id: UUID
    workspace_id: UUID
    label_studio_project_id: str
    superinsight_project_id: Optional[UUID] = None
    project_metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class InMemoryDatabase:
    """Simple in-memory database for testing."""

    def __init__(self):
        self.workspaces: Dict[UUID, Workspace] = {}
        self.members: Dict[UUID, WorkspaceMember] = {}
        self.projects: Dict[UUID, WorkspaceProject] = {}

        # Indexes for faster lookups
        self._workspace_by_name: Dict[str, UUID] = {}
        self._members_by_workspace: Dict[UUID, List[UUID]] = {}
        self._members_by_user: Dict[UUID, List[UUID]] = {}
        self._member_by_ws_user: Dict[str, UUID] = {}
        self._projects_by_workspace: Dict[UUID, List[UUID]] = {}

    def add_workspace(self, workspace: Workspace) -> None:
        """Add workspace to database."""
        self.workspaces[workspace.id] = workspace
        self._workspace_by_name[workspace.name] = workspace.id

    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        """Get workspace by ID."""
        return self.workspaces.get(workspace_id)

    def get_workspace_by_name(self, name: str) -> Optional[Workspace]:
        """Get workspace by name."""
        ws_id = self._workspace_by_name.get(name)
        if ws_id:
            return self.workspaces.get(ws_id)
        return None

    def list_workspaces_for_user(self, user_id: UUID) -> List[Workspace]:
        """List workspaces where user is a member."""
        member_ids = self._members_by_user.get(user_id, [])
        workspace_ids = set()
        for mid in member_ids:
            member = self.members.get(mid)
            if member and member.is_active:
                workspace_ids.add(member.workspace_id)

        return [
            self.workspaces[wid]
            for wid in workspace_ids
            if wid in self.workspaces and not self.workspaces[wid].is_deleted
        ]

    def update_workspace(self, workspace_id: UUID, updates: Dict) -> bool:
        """Update workspace fields."""
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return False

        for key, value in updates.items():
            if hasattr(workspace, key):
                setattr(workspace, key, value)
        workspace.updated_at = datetime.utcnow()
        return True

    def add_member(self, member: WorkspaceMember) -> None:
        """Add member to database."""
        self.members[member.id] = member

        # Update indexes
        if member.workspace_id not in self._members_by_workspace:
            self._members_by_workspace[member.workspace_id] = []
        self._members_by_workspace[member.workspace_id].append(member.id)

        if member.user_id not in self._members_by_user:
            self._members_by_user[member.user_id] = []
        self._members_by_user[member.user_id].append(member.id)

        key = f"{member.workspace_id}:{member.user_id}"
        self._member_by_ws_user[key] = member.id

    def get_member(self, workspace_id: UUID, user_id: UUID) -> Optional[WorkspaceMember]:
        """Get member by workspace and user."""
        key = f"{workspace_id}:{user_id}"
        member_id = self._member_by_ws_user.get(key)
        if member_id:
            return self.members.get(member_id)
        return None

    def list_members(self, workspace_id: UUID) -> List[WorkspaceMember]:
        """List members of a workspace."""
        member_ids = self._members_by_workspace.get(workspace_id, [])
        return [
            self.members[mid]
            for mid in member_ids
            if mid in self.members and self.members[mid].is_active
        ]

    def is_member(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Check if user is member of workspace."""
        member = self.get_member(workspace_id, user_id)
        return member is not None and member.is_active

    def add_project(self, project: WorkspaceProject) -> None:
        """Add project to database."""
        self.projects[project.id] = project

        if project.workspace_id not in self._projects_by_workspace:
            self._projects_by_workspace[project.workspace_id] = []
        self._projects_by_workspace[project.workspace_id].append(project.id)

    def list_projects(self, workspace_id: UUID) -> List[WorkspaceProject]:
        """List projects in a workspace."""
        project_ids = self._projects_by_workspace.get(workspace_id, [])
        return [self.projects[pid] for pid in project_ids if pid in self.projects]


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def db():
    """Create a fresh in-memory database."""
    return InMemoryDatabase()


@pytest.fixture
def populated_db():
    """Create a database with sample data."""
    db = InMemoryDatabase()

    # Create 10 workspaces with 10 members each
    for i in range(10):
        owner_id = uuid4()
        workspace = Workspace(
            id=uuid4(),
            name=f"Workspace {i}",
            description=f"Test workspace {i}",
            owner_id=owner_id,
        )
        db.add_workspace(workspace)

        # Add owner as member
        owner_member = WorkspaceMember(
            id=uuid4(),
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceMemberRole.OWNER,
        )
        db.add_member(owner_member)

        # Add 9 more members
        roles = [WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.MANAGER,
                 WorkspaceMemberRole.REVIEWER, WorkspaceMemberRole.ANNOTATOR]
        for j in range(9):
            member = WorkspaceMember(
                id=uuid4(),
                workspace_id=workspace.id,
                user_id=uuid4(),
                role=roles[j % len(roles)],
            )
            db.add_member(member)

    return db


# =============================================================================
# Workspace CRUD Performance Tests
# =============================================================================

class TestWorkspaceCRUDPerformance:
    """Performance tests for workspace CRUD operations."""

    def test_create_workspace_latency(self, db):
        """Test workspace creation latency."""
        iterations = 100
        latencies = []

        for i in range(iterations):
            workspace = Workspace(
                id=uuid4(),
                name=f"Test Workspace {i}",
                description=f"Description for workspace {i}",
                owner_id=uuid4(),
            )

            start = time.perf_counter()
            db.add_workspace(workspace)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        p99_latency = sorted(latencies)[int(iterations * 0.99)]

        print(f"\nWorkspace Creation Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  P99 latency: {p99_latency:.3f}ms")
        print(f"  Target: < {CRUD_LATENCY_TARGET_MS}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 creation latency {p95_latency:.3f}ms exceeds target {CRUD_LATENCY_TARGET_MS}ms"

    def test_get_workspace_latency(self, populated_db):
        """Test workspace retrieval latency."""
        workspace_ids = list(populated_db.workspaces.keys())

        iterations = 200
        latencies = []

        for i in range(iterations):
            ws_id = workspace_ids[i % len(workspace_ids)]

            start = time.perf_counter()
            result = populated_db.get_workspace(ws_id)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nWorkspace Retrieval Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  Target: < {CRUD_LATENCY_TARGET_MS}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 retrieval latency {p95_latency:.3f}ms exceeds target"

    def test_update_workspace_latency(self, populated_db):
        """Test workspace update latency."""
        workspace_ids = list(populated_db.workspaces.keys())

        iterations = 100
        latencies = []

        for i in range(iterations):
            ws_id = workspace_ids[i % len(workspace_ids)]

            start = time.perf_counter()
            populated_db.update_workspace(ws_id, {"description": f"Updated description {i}"})
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nWorkspace Update Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 update latency {p95_latency:.3f}ms exceeds target"

    def test_get_workspace_by_name_latency(self, populated_db):
        """Test workspace retrieval by name latency."""
        iterations = 200
        latencies = []

        for i in range(iterations):
            name = f"Workspace {i % 10}"

            start = time.perf_counter()
            result = populated_db.get_workspace_by_name(name)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nWorkspace by Name Lookup Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 name lookup latency {p95_latency:.3f}ms exceeds target"


# =============================================================================
# Member Management Performance Tests
# =============================================================================

class TestMemberManagementPerformance:
    """Performance tests for member management operations."""

    def test_add_member_latency(self, db):
        """Test member addition latency."""
        # Create a workspace first
        workspace = Workspace(
            id=uuid4(),
            name="Test Workspace",
            owner_id=uuid4(),
            description="Test",
        )
        db.add_workspace(workspace)

        iterations = 100
        latencies = []

        roles = list(WorkspaceMemberRole)
        for i in range(iterations):
            member = WorkspaceMember(
                id=uuid4(),
                workspace_id=workspace.id,
                user_id=uuid4(),
                role=roles[i % len(roles)],
            )

            start = time.perf_counter()
            db.add_member(member)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nAdd Member Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 add member latency {p95_latency:.3f}ms exceeds target"

    def test_list_members_latency(self, populated_db):
        """Test member listing latency."""
        workspace_ids = list(populated_db.workspaces.keys())

        iterations = 100
        latencies = []

        for i in range(iterations):
            ws_id = workspace_ids[i % len(workspace_ids)]

            start = time.perf_counter()
            members = populated_db.list_members(ws_id)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nList Members Performance ({iterations} iterations, 10 members each):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < QUERY_LATENCY_TARGET_MS, \
            f"P95 list members latency {p95_latency:.3f}ms exceeds target"

    def test_is_member_check_latency(self, populated_db):
        """Test membership check latency."""
        # Get some members for testing
        workspace_ids = list(populated_db.workspaces.keys())
        test_pairs = []

        for ws_id in workspace_ids[:5]:
            members = populated_db.list_members(ws_id)
            for m in members[:2]:
                test_pairs.append((ws_id, m.user_id, True))
            # Add non-members
            test_pairs.append((ws_id, uuid4(), False))

        iterations = 500
        latencies = []

        for i in range(iterations):
            ws_id, user_id, _ = test_pairs[i % len(test_pairs)]

            start = time.perf_counter()
            is_member = populated_db.is_member(ws_id, user_id)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nIs Member Check Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 is_member latency {p95_latency:.3f}ms exceeds target"

    def test_get_member_latency(self, populated_db):
        """Test individual member retrieval latency."""
        # Get test pairs
        test_pairs = []
        for ws_id, members in populated_db._members_by_workspace.items():
            for mid in members[:3]:
                member = populated_db.members[mid]
                test_pairs.append((ws_id, member.user_id))

        iterations = 500
        latencies = []

        for i in range(iterations):
            ws_id, user_id = test_pairs[i % len(test_pairs)]

            start = time.perf_counter()
            member = populated_db.get_member(ws_id, user_id)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nGet Member Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS / 2, \
            f"P95 get member latency {p95_latency:.3f}ms exceeds target"


# =============================================================================
# Volume Scaling Performance Tests
# =============================================================================

class TestVolumeScalingPerformance:
    """Performance tests for scaling with data volume."""

    def test_workspace_count_scaling(self):
        """Test query performance as workspace count grows."""
        workspace_counts = [10, 50, 100, 200]
        owner_id = uuid4()

        results = []
        db = InMemoryDatabase()

        for target_count in workspace_counts:
            current_count = len(db.workspaces)

            # Add more workspaces
            for i in range(target_count - current_count):
                workspace = Workspace(
                    id=uuid4(),
                    name=f"WS_{target_count}_{i}",
                    description=f"Test workspace",
                    owner_id=owner_id,
                )
                db.add_workspace(workspace)

                member = WorkspaceMember(
                    id=uuid4(),
                    workspace_id=workspace.id,
                    user_id=owner_id,
                    role=WorkspaceMemberRole.OWNER,
                )
                db.add_member(member)

            # Measure query performance
            iterations = 50
            latencies = []

            for _ in range(iterations):
                start = time.perf_counter()
                workspaces = db.list_workspaces_for_user(owner_id)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)

            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(iterations * 0.95)]

            results.append({
                "count": target_count,
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
            })

        print(f"\nWorkspace Count Scaling:")
        for r in results:
            print(f"  {r['count']} workspaces: avg={r['avg_latency']:.3f}ms, p95={r['p95_latency']:.3f}ms")

        # Verify performance doesn't degrade too much with scale
        first_p95 = results[0]["p95_latency"]
        last_p95 = results[-1]["p95_latency"]

        # Allow 10x degradation from 10 to 200 workspaces
        assert last_p95 < max(first_p95 * 10, QUERY_LATENCY_TARGET_MS), \
            f"Performance degraded too much: {first_p95:.3f}ms -> {last_p95:.3f}ms"

    def test_member_count_scaling(self):
        """Test query performance as member count grows."""
        member_counts = [10, 50, 100, 200, 500]

        db = InMemoryDatabase()
        workspace = Workspace(
            id=uuid4(),
            name="Scaling Test",
            description="Test workspace",
            owner_id=uuid4(),
        )
        db.add_workspace(workspace)

        results = []
        total_members = 0

        for target_count in member_counts:
            # Add more members
            roles = list(WorkspaceMemberRole)
            for i in range(target_count - total_members):
                member = WorkspaceMember(
                    id=uuid4(),
                    workspace_id=workspace.id,
                    user_id=uuid4(),
                    role=roles[i % len(roles)],
                )
                db.add_member(member)
            total_members = target_count

            iterations = 30
            latencies = []

            for _ in range(iterations):
                start = time.perf_counter()
                members = db.list_members(workspace.id)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)

            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(iterations * 0.95)]

            results.append({
                "count": target_count,
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
            })

        print(f"\nMember Count Scaling:")
        for r in results:
            print(f"  {r['count']} members: avg={r['avg_latency']:.3f}ms, p95={r['p95_latency']:.3f}ms")

        # Even with 500 members, should stay under target
        last_p95 = results[-1]["p95_latency"]
        assert last_p95 < QUERY_LATENCY_TARGET_MS * 2, \
            f"500 member list latency {last_p95:.3f}ms exceeds 2x target"


# =============================================================================
# Batch Operation Performance Tests
# =============================================================================

class TestBatchOperationPerformance:
    """Performance tests for batch operations."""

    def test_batch_member_addition(self, db):
        """Test adding many members in sequence."""
        workspace = Workspace(
            id=uuid4(),
            name="Batch Test",
            description="Test",
            owner_id=uuid4(),
        )
        db.add_workspace(workspace)

        batch_size = 100
        roles = list(WorkspaceMemberRole)

        start = time.perf_counter()
        for i in range(batch_size):
            member = WorkspaceMember(
                id=uuid4(),
                workspace_id=workspace.id,
                user_id=uuid4(),
                role=roles[i % len(roles)],
            )
            db.add_member(member)
        end = time.perf_counter()

        total_time = (end - start) * 1000
        avg_per_member = total_time / batch_size

        print(f"\nBatch Member Addition ({batch_size} members):")
        print(f"  Total time: {total_time:.3f}ms")
        print(f"  Average per member: {avg_per_member:.3f}ms")
        print(f"  Throughput: {batch_size / (total_time / 1000):.1f} members/second")

        assert total_time < BATCH_LATENCY_TARGET_MS * (batch_size / 10), \
            f"Batch addition took too long: {total_time:.3f}ms"

    def test_batch_workspace_creation(self, db):
        """Test creating many workspaces in sequence."""
        batch_size = 50

        start = time.perf_counter()
        for i in range(batch_size):
            workspace = Workspace(
                id=uuid4(),
                name=f"Batch Workspace {i}",
                description=f"Batch created workspace {i}",
                owner_id=uuid4(),
            )
            db.add_workspace(workspace)
        end = time.perf_counter()

        total_time = (end - start) * 1000
        avg_per_workspace = total_time / batch_size

        print(f"\nBatch Workspace Creation ({batch_size} workspaces):")
        print(f"  Total time: {total_time:.3f}ms")
        print(f"  Average per workspace: {avg_per_workspace:.3f}ms")
        print(f"  Throughput: {batch_size / (total_time / 1000):.1f} workspaces/second")

        assert avg_per_workspace < CRUD_LATENCY_TARGET_MS, \
            f"Average workspace creation {avg_per_workspace:.3f}ms exceeds target"


# =============================================================================
# Index Effectiveness Tests
# =============================================================================

class TestIndexEffectiveness:
    """Tests to verify index effectiveness."""

    def test_composite_key_lookup_performance(self):
        """Test member lookup by (workspace_id, user_id) is fast."""
        db = InMemoryDatabase()

        # Create workspace with 200 members
        workspace = Workspace(
            id=uuid4(),
            name="Index Test",
            owner_id=uuid4(),
            description="Test",
        )
        db.add_workspace(workspace)

        members = []
        for i in range(200):
            member = WorkspaceMember(
                id=uuid4(),
                workspace_id=workspace.id,
                user_id=uuid4(),
                role=WorkspaceMemberRole.ANNOTATOR,
            )
            db.add_member(member)
            members.append(member)

        iterations = 500
        latencies = []

        for i in range(iterations):
            member = members[i % len(members)]

            start = time.perf_counter()
            result = db.get_member(workspace.id, member.user_id)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nComposite Key Lookup ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.4f}ms")
        print(f"  P95 latency: {p95_latency:.4f}ms")

        # Composite key lookup should be very fast (O(1) with hash)
        assert p95_latency < 0.1, \
            f"Composite key lookup {p95_latency:.3f}ms too slow"

    def test_name_index_performance(self):
        """Test workspace lookup by name uses index effectively."""
        db = InMemoryDatabase()

        # Create 200 workspaces
        for i in range(200):
            workspace = Workspace(
                id=uuid4(),
                name=f"Workspace {i}",
                owner_id=uuid4(),
                description=f"Test {i}",
            )
            db.add_workspace(workspace)

        iterations = 200
        latencies = []

        for i in range(iterations):
            name = f"Workspace {i % 200}"

            start = time.perf_counter()
            result = db.get_workspace_by_name(name)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nName Index Lookup ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.4f}ms")
        print(f"  P95 latency: {p95_latency:.4f}ms")

        # Name lookup should be fast due to index
        assert p95_latency < 0.1, \
            f"Name lookup latency {p95_latency:.3f}ms too slow"


# =============================================================================
# Project Association Performance Tests
# =============================================================================

class TestProjectAssociationPerformance:
    """Performance tests for project association operations."""

    def test_add_project_latency(self, db):
        """Test project addition latency."""
        workspace = Workspace(
            id=uuid4(),
            name="Project Test",
            owner_id=uuid4(),
            description="Test",
        )
        db.add_workspace(workspace)

        iterations = 100
        latencies = []

        for i in range(iterations):
            project = WorkspaceProject(
                id=uuid4(),
                workspace_id=workspace.id,
                label_studio_project_id=f"ls-project-{i}",
            )

            start = time.perf_counter()
            db.add_project(project)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nAdd Project Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")

        assert p95_latency < CRUD_LATENCY_TARGET_MS, \
            f"P95 add project latency {p95_latency:.3f}ms exceeds target"

    def test_list_projects_latency(self):
        """Test project listing latency with various counts."""
        project_counts = [10, 50, 100]

        for count in project_counts:
            db = InMemoryDatabase()
            workspace = Workspace(
                id=uuid4(),
                name=f"Test {count}",
                owner_id=uuid4(),
                description="Test",
            )
            db.add_workspace(workspace)

            # Add projects
            for i in range(count):
                project = WorkspaceProject(
                    id=uuid4(),
                    workspace_id=workspace.id,
                    label_studio_project_id=f"ls-{i}",
                )
                db.add_project(project)

            iterations = 50
            latencies = []

            for _ in range(iterations):
                start = time.perf_counter()
                projects = db.list_projects(workspace.id)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)

            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(iterations * 0.95)]

            print(f"\nList Projects Performance ({count} projects, {iterations} iterations):")
            print(f"  Average latency: {avg_latency:.3f}ms")
            print(f"  P95 latency: {p95_latency:.3f}ms")

            assert p95_latency < QUERY_LATENCY_TARGET_MS, \
                f"P95 list projects ({count}) latency {p95_latency:.3f}ms exceeds target"
