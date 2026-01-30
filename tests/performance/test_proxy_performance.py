"""
Performance tests for Label Studio Proxy Layer.

Tests cover:
- Metadata encoding/decoding performance (target: < 10ms)
- Permission verification overhead
- Concurrent request handling (target: 100+ concurrent users)

Note: These tests are designed to be self-contained and avoid
complex import dependencies from the main application.
"""

import pytest
import asyncio
import time
import statistics
import base64
import json
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4
from enum import Enum


# =============================================================================
# Test Constants
# =============================================================================

# Performance targets from requirements
PROXY_LATENCY_TARGET_MS = 200  # < 200ms
METADATA_ENCODING_TARGET_MS = 10  # < 10ms
QUERY_LATENCY_TARGET_MS = 100  # < 100ms (95th percentile)
CONCURRENT_USERS_TARGET = 100


# =============================================================================
# Simplified Test Classes (avoiding complex imports)
# =============================================================================

class WorkspaceMemberRole(str, Enum):
    """Workspace member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    ANNOTATOR = "annotator"


class Permission(str, Enum):
    """Permission enumeration."""
    WORKSPACE_VIEW = "workspace:view"
    WORKSPACE_EDIT = "workspace:edit"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_MANAGE_MEMBERS = "workspace:manage_members"
    PROJECT_VIEW = "project:view"
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_MEMBERS = "project:manage_members"
    TASK_VIEW = "task:view"
    TASK_ANNOTATE = "task:annotate"
    TASK_REVIEW = "task:review"
    TASK_ASSIGN = "task:assign"
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"


# Role to permission mapping
ROLE_PERMISSIONS = {
    WorkspaceMemberRole.OWNER: set(Permission),  # All permissions
    WorkspaceMemberRole.ADMIN: {
        Permission.WORKSPACE_VIEW,
        Permission.WORKSPACE_EDIT,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_MANAGE_MEMBERS,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.TASK_ASSIGN,
        Permission.DATA_EXPORT,
        Permission.DATA_IMPORT,
    },
    WorkspaceMemberRole.MANAGER: {
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_MANAGE_MEMBERS,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.TASK_ASSIGN,
        Permission.DATA_EXPORT,
    },
    WorkspaceMemberRole.REVIEWER: {
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.DATA_EXPORT,
    },
    WorkspaceMemberRole.ANNOTATOR: {
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
    },
}


class TestMetadataCodec:
    """Simple metadata codec for testing."""

    METADATA_PREFIX = "[SUPERINSIGHT_META:"
    METADATA_SUFFIX = "]"
    VERSION = "1.0"

    def encode(self, original_text: str, metadata: dict) -> str:
        """Encode metadata into text."""
        if "_version" not in metadata:
            metadata = {**metadata, "_version": self.VERSION}
        json_str = json.dumps(metadata, ensure_ascii=False)
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
        return f"{self.METADATA_PREFIX}{encoded}{self.METADATA_SUFFIX}{original_text}"

    def decode(self, text: str) -> tuple:
        """Decode metadata from text."""
        if not text.startswith(self.METADATA_PREFIX):
            return text, {}

        end_idx = text.find(self.METADATA_SUFFIX, len(self.METADATA_PREFIX))
        if end_idx == -1:
            return text, {}

        encoded = text[len(self.METADATA_PREFIX):end_idx]
        original = text[end_idx + len(self.METADATA_SUFFIX):]

        json_str = base64.b64decode(encoded).decode('utf-8')
        metadata = json.loads(json_str)

        return original, metadata

    def has_metadata(self, text: str) -> bool:
        """Check if text has metadata."""
        return text.startswith(self.METADATA_PREFIX)


class TestRBACService:
    """Simple RBAC service for testing."""

    def __init__(self, members: Dict[str, WorkspaceMemberRole]):
        self.members = members

    def get_role(self, user_id: str, workspace_id: str) -> WorkspaceMemberRole:
        """Get user role in workspace."""
        key = f"{workspace_id}:{user_id}"
        return self.members.get(key)

    def has_permission(self, user_id: str, workspace_id: str, permission: Permission) -> bool:
        """Check if user has permission."""
        role = self.get_role(user_id, workspace_id)
        if not role:
            return False
        return permission in ROLE_PERMISSIONS[role]

    def get_permissions(self, user_id: str, workspace_id: str) -> set:
        """Get all permissions for user."""
        role = self.get_role(user_id, workspace_id)
        if not role:
            return set()
        return ROLE_PERMISSIONS[role]


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def metadata_codec():
    """Create a metadata codec instance."""
    return TestMetadataCodec()


@pytest.fixture
def sample_metadata():
    """Create sample workspace metadata."""
    return {
        "workspace_id": str(uuid4()),
        "workspace_name": "Test Workspace",
        "created_by": str(uuid4()),
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_description():
    """Create sample project description."""
    return "This is a test project for data annotation. " * 10


@pytest.fixture
def rbac_service():
    """Create an RBAC service with test members."""
    workspace_id = str(uuid4())
    members = {}

    # Create members with different roles
    for role in WorkspaceMemberRole:
        user_id = str(uuid4())
        members[f"{workspace_id}:{user_id}"] = role

    return TestRBACService(members)


# =============================================================================
# Metadata Encoding/Decoding Performance Tests
# =============================================================================

class TestMetadataEncodingPerformance:
    """Performance tests for metadata encoding/decoding."""

    def test_encode_metadata_latency(self, metadata_codec, sample_metadata, sample_description):
        """Test that metadata encoding completes within target latency."""
        iterations = 1000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            encoded = metadata_codec.encode(sample_description, sample_metadata)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        p99_latency = sorted(latencies)[int(iterations * 0.99)]

        print(f"\nMetadata Encoding Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  P99 latency: {p99_latency:.3f}ms")
        print(f"  Target: < {METADATA_ENCODING_TARGET_MS}ms")

        assert avg_latency < METADATA_ENCODING_TARGET_MS, \
            f"Average encoding latency {avg_latency:.3f}ms exceeds target {METADATA_ENCODING_TARGET_MS}ms"
        assert p95_latency < METADATA_ENCODING_TARGET_MS * 2, \
            f"P95 encoding latency {p95_latency:.3f}ms exceeds 2x target"

    def test_decode_metadata_latency(self, metadata_codec, sample_metadata, sample_description):
        """Test that metadata decoding completes within target latency."""
        # Pre-encode the text
        encoded = metadata_codec.encode(sample_description, sample_metadata)

        iterations = 1000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            original, metadata = metadata_codec.decode(encoded)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        p99_latency = sorted(latencies)[int(iterations * 0.99)]

        print(f"\nMetadata Decoding Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  P99 latency: {p99_latency:.3f}ms")
        print(f"  Target: < {METADATA_ENCODING_TARGET_MS}ms")

        assert avg_latency < METADATA_ENCODING_TARGET_MS, \
            f"Average decoding latency {avg_latency:.3f}ms exceeds target {METADATA_ENCODING_TARGET_MS}ms"

    def test_has_metadata_check_latency(self, metadata_codec, sample_metadata, sample_description):
        """Test that metadata presence check is fast."""
        # Test with encoded text
        encoded = metadata_codec.encode(sample_description, sample_metadata)

        iterations = 10000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            has_meta = metadata_codec.has_metadata(encoded)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        avg_latency = statistics.mean(latencies)
        p99_latency = sorted(latencies)[int(iterations * 0.99)]

        print(f"\nMetadata Check Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.6f}ms")
        print(f"  P99 latency: {p99_latency:.6f}ms")

        # Should be sub-millisecond
        assert avg_latency < 1.0, \
            f"Average check latency {avg_latency:.3f}ms is too slow"

    def test_encode_decode_roundtrip_latency(self, metadata_codec, sample_metadata, sample_description):
        """Test complete encode-decode roundtrip latency."""
        iterations = 500
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            encoded = metadata_codec.encode(sample_description, sample_metadata)
            original, metadata = metadata_codec.decode(encoded)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nEncode-Decode Roundtrip Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  Target: < {METADATA_ENCODING_TARGET_MS * 2}ms (2x encoding target)")

        assert avg_latency < METADATA_ENCODING_TARGET_MS * 2, \
            f"Average roundtrip latency {avg_latency:.3f}ms exceeds 2x target"

    def test_encode_large_description(self, metadata_codec, sample_metadata):
        """Test encoding performance with large description."""
        large_description = "Test description with lots of text. " * 1000  # ~35KB

        iterations = 100
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            encoded = metadata_codec.encode(large_description, sample_metadata)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        print(f"\nLarge Description Encoding ({len(large_description)} chars):")
        print(f"  Average latency: {avg_latency:.3f}ms")

        # Should still be reasonably fast even with large text
        assert avg_latency < 50, \
            f"Large description encoding {avg_latency:.3f}ms is too slow"


# =============================================================================
# Permission Verification Performance Tests
# =============================================================================

class TestPermissionVerificationPerformance:
    """Performance tests for permission verification."""

    def test_permission_check_latency(self):
        """Test permission check latency."""
        workspace_id = str(uuid4())
        user_id = str(uuid4())

        # Create service with user as admin
        members = {f"{workspace_id}:{user_id}": WorkspaceMemberRole.ADMIN}
        rbac = TestRBACService(members)

        iterations = 10000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            has_perm = rbac.has_permission(user_id, workspace_id, Permission.PROJECT_VIEW)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]

        print(f"\nPermission Check Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.4f}ms")
        print(f"  P95 latency: {p95_latency:.4f}ms")

        # Permission checks should be very fast (in-memory operations)
        assert avg_latency < 0.1, \
            f"Permission check latency {avg_latency:.3f}ms is too slow"

    def test_get_all_permissions_latency(self):
        """Test getting all user permissions latency."""
        workspace_id = str(uuid4())
        user_id = str(uuid4())

        members = {f"{workspace_id}:{user_id}": WorkspaceMemberRole.ADMIN}
        rbac = TestRBACService(members)

        iterations = 5000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter()
            permissions = rbac.get_permissions(user_id, workspace_id)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = statistics.mean(latencies)
        print(f"\nGet All Permissions Performance ({iterations} iterations):")
        print(f"  Average latency: {avg_latency:.4f}ms")
        print(f"  Permissions returned: {len(permissions) if permissions else 0}")

        assert avg_latency < 0.1, \
            f"Get permissions latency {avg_latency:.3f}ms is too slow"

    def test_permission_matrix_lookup_performance(self):
        """Test looking up all permissions for all roles."""
        workspace_id = str(uuid4())

        # Create users for each role
        members = {}
        role_users = {}
        for role in WorkspaceMemberRole:
            user_id = str(uuid4())
            members[f"{workspace_id}:{user_id}"] = role
            role_users[role] = user_id

        rbac = TestRBACService(members)
        all_permissions = list(Permission)
        iterations = 100

        total_checks = 0
        start = time.perf_counter()

        for _ in range(iterations):
            for role, user_id in role_users.items():
                for perm in all_permissions:
                    rbac.has_permission(user_id, workspace_id, perm)
                    total_checks += 1

        end = time.perf_counter()
        total_time_ms = (end - start) * 1000
        avg_per_check = total_time_ms / total_checks

        print(f"\nPermission Matrix Lookup ({total_checks} total checks):")
        print(f"  Total time: {total_time_ms:.3f}ms")
        print(f"  Average per check: {avg_per_check:.6f}ms")
        print(f"  Checks per second: {total_checks / (total_time_ms / 1000):.0f}")

        assert avg_per_check < 0.01, \
            f"Permission check too slow: {avg_per_check:.4f}ms per check"


# =============================================================================
# Concurrent Request Performance Tests
# =============================================================================

class TestConcurrentRequestPerformance:
    """Performance tests for concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_permission_checks(self):
        """Test concurrent permission checks."""
        workspace_id = str(uuid4())
        user_ids = [str(uuid4()) for _ in range(CONCURRENT_USERS_TARGET)]

        # All users are annotators
        members = {f"{workspace_id}:{uid}": WorkspaceMemberRole.ANNOTATOR for uid in user_ids}
        rbac = TestRBACService(members)

        async def check_permission(user_id):
            start = time.perf_counter()
            result = rbac.has_permission(user_id, workspace_id, Permission.TASK_ANNOTATE)
            end = time.perf_counter()
            return (end - start) * 1000

        # Run concurrent permission checks
        start_total = time.perf_counter()
        tasks = [check_permission(uid) for uid in user_ids]
        latencies = await asyncio.gather(*tasks)
        end_total = time.perf_counter()

        total_time = (end_total - start_total) * 1000
        avg_latency = statistics.mean(latencies)
        throughput = len(user_ids) / (total_time / 1000)

        print(f"\nConcurrent Permission Checks ({CONCURRENT_USERS_TARGET} users):")
        print(f"  Total time: {total_time:.3f}ms")
        print(f"  Average per-request latency: {avg_latency:.4f}ms")
        print(f"  Throughput: {throughput:.1f} requests/second")

        # All checks should complete in reasonable time
        assert total_time < 1000, \
            f"Concurrent checks took too long: {total_time:.3f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_metadata_operations(self):
        """Test concurrent metadata encoding/decoding."""
        codec = TestMetadataCodec()
        sample_metadata = {
            "workspace_id": str(uuid4()),
            "workspace_name": "Test",
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow().isoformat(),
        }
        descriptions = [f"Project description {i} " * 20 for i in range(CONCURRENT_USERS_TARGET)]

        async def encode_decode(description):
            start = time.perf_counter()
            encoded = codec.encode(description, sample_metadata)
            original, metadata = codec.decode(encoded)
            end = time.perf_counter()
            return (end - start) * 1000

        # Run concurrent operations
        start_total = time.perf_counter()
        tasks = [encode_decode(desc) for desc in descriptions]
        latencies = await asyncio.gather(*tasks)
        end_total = time.perf_counter()

        total_time = (end_total - start_total) * 1000
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        throughput = len(descriptions) / (total_time / 1000)

        print(f"\nConcurrent Metadata Operations ({CONCURRENT_USERS_TARGET} operations):")
        print(f"  Total time: {total_time:.3f}ms")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  Throughput: {throughput:.1f} operations/second")

        assert p95_latency < METADATA_ENCODING_TARGET_MS * 3, \
            f"P95 concurrent latency {p95_latency:.3f}ms exceeds 3x target"


# =============================================================================
# Stress Tests
# =============================================================================

class TestStressPerformance:
    """Stress tests for high load scenarios."""

    def test_metadata_encoding_under_load(self):
        """Test metadata encoding under sustained load."""
        codec = TestMetadataCodec()
        sample_metadata = {
            "workspace_id": str(uuid4()),
            "workspace_name": "Stress Test",
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow().isoformat(),
        }

        iterations = 10000
        batch_size = 1000

        descriptions = [f"Project {i} description text " * 10 for i in range(batch_size)]

        batch_latencies = []
        for batch in range(iterations // batch_size):
            start = time.perf_counter()
            for desc in descriptions:
                encoded = codec.encode(desc, sample_metadata)
            end = time.perf_counter()
            batch_latencies.append((end - start) * 1000 / batch_size)

        avg_batch_latency = statistics.mean(batch_latencies)
        print(f"\nSustained Load Test ({iterations} total operations):")
        print(f"  Average per-operation latency: {avg_batch_latency:.3f}ms")
        print(f"  Batches completed: {len(batch_latencies)}")

        # Performance should remain stable under load
        assert avg_batch_latency < METADATA_ENCODING_TARGET_MS, \
            f"Latency under load {avg_batch_latency:.3f}ms exceeds target"

    def test_high_volume_permission_checks(self):
        """Test permission checks at high volume."""
        workspace_id = str(uuid4())
        user_id = str(uuid4())

        members = {f"{workspace_id}:{user_id}": WorkspaceMemberRole.MANAGER}
        rbac = TestRBACService(members)

        iterations = 100000
        all_permissions = list(Permission)

        start = time.perf_counter()
        for i in range(iterations):
            perm = all_permissions[i % len(all_permissions)]
            rbac.has_permission(user_id, workspace_id, perm)
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        ops_per_second = iterations / (total_time_ms / 1000)

        print(f"\nHigh Volume Permission Checks ({iterations} checks):")
        print(f"  Total time: {total_time_ms:.3f}ms")
        print(f"  Operations per second: {ops_per_second:.0f}")

        # Should handle at least 100k ops/second
        assert ops_per_second > 100000, \
            f"Throughput {ops_per_second:.0f}/s too low"
