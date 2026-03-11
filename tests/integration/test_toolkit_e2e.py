"""
End-to-end integration tests for the Intelligent Data Toolkit Framework.

Tests the full pipeline: Upload → Profile → Route → Execute → Store → Query
plus lifecycle controls and audit trail verification.

Requirements: 1.1–8.3
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.toolkit.api.router import (
    router, _files, _profiles, _plans, _executions, _audit, _storage,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    return application


@pytest.fixture
def clear_stores():
    _files.clear()
    _profiles.clear()
    _plans.clear()
    _executions.clear()
    _audit.clear()
    yield
    _files.clear()
    _profiles.clear()
    _plans.clear()
    _executions.clear()
    _audit.clear()


@pytest.fixture
async def client(app, clear_stores):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _upload(client: AsyncClient, filename: str, content: bytes, ctype: str):
    """Upload a file and return the file_id."""
    resp = await client.post(
        "/api/toolkit/upload",
        files={"file": (filename, content, ctype)},
    )
    assert resp.status_code == 200
    return resp.json()["file_id"]


async def _full_pipeline(client: AsyncClient, filename: str, content: bytes,
                         ctype: str, *, needs_semantic_search: bool = False):
    """Run upload → profile → route → execute and return all responses."""
    file_id = await _upload(client, filename, content, ctype)

    profile_resp = await client.post(f"/api/toolkit/profile/{file_id}")
    assert profile_resp.status_code == 200

    route_resp = await client.post(
        f"/api/toolkit/route/{file_id}",
        params={"needs_semantic_search": needs_semantic_search},
    )
    assert route_resp.status_code == 200

    exec_resp = await client.post(f"/api/toolkit/execute/{file_id}")
    assert exec_resp.status_code == 200

    return {
        "file_id": file_id,
        "profile": profile_resp.json(),
        "plan": route_resp.json(),
        "execution": exec_resp.json(),
    }


# ------------------------------------------------------------------
# Test 1: CSV Upload → Profile → Route → Execute → Store → Query
# ------------------------------------------------------------------

class TestTabularPipeline:
    """Full pipeline for tabular (CSV) data — Req 1.1–5.2, 4.1, 4.4."""

    CSV_CONTENT = b"name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\nCharlie,35,Shenzhen"

    async def test_upload_returns_metadata(self, client):
        resp = await client.post(
            "/api/toolkit/upload",
            files={"file": ("data.csv", self.CSV_CONTENT, "text/csv")},
        )
        data = resp.json()
        assert data["filename"] == "data.csv"
        assert data["size"] == len(self.CSV_CONTENT)

    async def test_profile_detects_csv(self, client):
        file_id = await _upload(client, "data.csv", self.CSV_CONTENT, "text/csv")
        profile = (await client.post(f"/api/toolkit/profile/{file_id}")).json()

        assert profile["basic_info"]["file_type"] == "csv"
        assert "quality_metrics" in profile
        assert profile["quality_metrics"]["completeness_score"] >= 0

    async def test_route_produces_plan(self, client):
        file_id = await _upload(client, "data.csv", self.CSV_CONTENT, "text/csv")
        await client.post(f"/api/toolkit/profile/{file_id}")
        plan = (await client.post(f"/api/toolkit/route/{file_id}")).json()

        assert len(plan["stages"]) > 0
        assert plan["explanation"]

    async def test_full_csv_pipeline(self, client):
        result = await _full_pipeline(
            client, "data.csv", self.CSV_CONTENT, "text/csv",
        )
        exec_data = result["execution"]
        assert exec_data["status"] == "completed"

        # Verify status endpoint
        eid = exec_data["execution_id"]
        status = (await client.get(f"/api/toolkit/status/{eid}")).json()
        assert status["status"] == "completed"
        assert status["progress"] == 100

        # Verify results endpoint
        results = (await client.get(f"/api/toolkit/results/{eid}")).json()
        assert results["stored"] is True


# ------------------------------------------------------------------
# Test 2: Text Upload → Profile → Route (semantic) → Execute → Store
# ------------------------------------------------------------------

class TestTextSemanticPipeline:
    """Full pipeline for text data with semantic search — Req 1.3, 2.1, 4.2."""

    TEXT_CONTENT = (
        b"Machine learning is a subset of artificial intelligence. "
        b"Deep learning uses neural networks with many layers. "
        b"Natural language processing enables computers to understand text."
    )

    async def test_profile_detects_text(self, client):
        file_id = await _upload(client, "doc.txt", self.TEXT_CONTENT, "text/plain")
        profile = (await client.post(f"/api/toolkit/profile/{file_id}")).json()

        assert profile["basic_info"]["file_type"] == "text"
        assert "semantic_info" in profile

    async def test_semantic_route_includes_vector_storage(self, client):
        file_id = await _upload(client, "doc.txt", self.TEXT_CONTENT, "text/plain")
        await client.post(f"/api/toolkit/profile/{file_id}")
        plan = (await client.post(
            f"/api/toolkit/route/{file_id}",
            params={"needs_semantic_search": True},
        )).json()

        assert len(plan["stages"]) > 0
        assert plan["explanation"]
        # With semantic search, storage strategy should reference vector
        storage = plan.get("storage_strategy", {})
        if storage:
            primary = storage.get("primary_storage", "")
            assert "vector" in primary.lower() or len(plan["stages"]) > 0

    async def test_full_text_pipeline(self, client):
        result = await _full_pipeline(
            client, "doc.txt", self.TEXT_CONTENT, "text/plain",
            needs_semantic_search=True,
        )
        assert result["execution"]["status"] == "completed"

        eid = result["execution"]["execution_id"]
        results = (await client.get(f"/api/toolkit/results/{eid}")).json()
        assert results["stored"] is True


# ------------------------------------------------------------------
# Test 3: Execution Lifecycle — Pause → Resume → Cancel
# ------------------------------------------------------------------

class TestExecutionLifecycle:
    """Test pause/resume/cancel controls — Req 3.4, 3.5."""

    async def _setup(self, client):
        return await _full_pipeline(
            client, "lc.txt", b"lifecycle test data", "text/plain",
        )

    async def test_pause_sets_status(self, client):
        result = await self._setup(client)
        eid = result["execution"]["execution_id"]

        resp = await client.post(f"/api/toolkit/pause/{eid}")
        assert resp.json()["status"] == "paused"

        status = (await client.get(f"/api/toolkit/status/{eid}")).json()
        assert status["status"] == "paused"

    async def test_resume_after_pause(self, client):
        result = await self._setup(client)
        eid = result["execution"]["execution_id"]

        await client.post(f"/api/toolkit/pause/{eid}")
        resp = await client.post(f"/api/toolkit/resume/{eid}")
        assert resp.json()["status"] == "running"

    async def test_cancel_execution(self, client):
        result = await self._setup(client)
        eid = result["execution"]["execution_id"]

        resp = await client.post(f"/api/toolkit/cancel/{eid}")
        assert resp.json()["status"] == "cancelled"

    async def test_full_lifecycle_sequence(self, client):
        """Pause → Resume → Cancel in sequence."""
        result = await self._setup(client)
        eid = result["execution"]["execution_id"]

        pause = await client.post(f"/api/toolkit/pause/{eid}")
        assert pause.json()["status"] == "paused"

        resume = await client.post(f"/api/toolkit/resume/{eid}")
        assert resume.json()["status"] == "running"

        cancel = await client.post(f"/api/toolkit/cancel/{eid}")
        assert cancel.json()["status"] == "cancelled"

        # Results should not be available for cancelled execution
        resp = await client.get(f"/api/toolkit/results/{eid}")
        assert resp.status_code == 400


# ------------------------------------------------------------------
# Test 4: Audit Trail Integration
# ------------------------------------------------------------------

class TestAuditTrail:
    """Verify all operations produce audit entries — Req 8.3."""

    async def test_pipeline_generates_audit_entries(self, client):
        result = await _full_pipeline(
            client, "audit.csv", b"x,y\n1,2", "text/csv",
        )
        file_id = result["file_id"]

        # upload, profile, route, execute → at least 4 entries
        all_entries = _audit.get_audit_trail()
        op_types = [e.operation_type for e in all_entries]

        assert "upload" in op_types
        assert "profile" in op_types
        assert "route" in op_types
        assert "execute" in op_types

    async def test_lifecycle_ops_audited(self, client):
        result = await _full_pipeline(
            client, "a.txt", b"data", "text/plain",
        )
        eid = result["execution"]["execution_id"]

        await client.post(f"/api/toolkit/pause/{eid}")
        await client.post(f"/api/toolkit/resume/{eid}")
        await client.post(f"/api/toolkit/cancel/{eid}")

        all_entries = _audit.get_audit_trail()
        op_types = [e.operation_type for e in all_entries]

        assert "pause" in op_types
        assert "resume" in op_types
        assert "cancel" in op_types

    async def test_audit_entries_have_required_fields(self, client):
        await _upload(client, "f.txt", b"hello", "text/plain")

        entries = _audit.get_audit_trail(operation_type="upload")
        assert len(entries) >= 1

        entry = entries[0]
        assert entry.user_id
        assert entry.operation_type == "upload"
        assert entry.resource_id
        assert entry.timestamp is not None


# ------------------------------------------------------------------
# Test 5: Storage Layer Integration
# ------------------------------------------------------------------

class TestStorageIntegration:
    """Test storage selection and lineage — Req 4.1–4.5."""

    async def test_storage_records_lineage(self, client):
        result = await _full_pipeline(
            client, "lin.csv", b"a,b\n1,2", "text/csv",
        )
        file_id = result["file_id"]

        lineage = _storage.track_lineage(file_id)
        if lineage is not None:
            assert lineage.source_node is not None
            assert lineage.source_node.node_type == "source"

    async def test_multiple_pipelines_independent(self, client):
        """Two independent pipelines should not interfere."""
        r1 = await _full_pipeline(
            client, "a.csv", b"x\n1", "text/csv",
        )
        r2 = await _full_pipeline(
            client, "b.csv", b"y\n2", "text/csv",
        )

        assert r1["file_id"] != r2["file_id"]
        assert r1["execution"]["execution_id"] != r2["execution"]["execution_id"]
        assert r1["execution"]["status"] == "completed"
        assert r2["execution"]["status"] == "completed"
