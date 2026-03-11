"""
Unit tests for the toolkit API router — end-to-end wiring layer.

Tests the Upload → Profile → Route → Execute → Store → Results flow
plus pause/resume/cancel lifecycle endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.toolkit.api.router import router, _files, _profiles, _plans, _executions


@pytest.fixture
def app():
    """Create a fresh FastAPI app with the toolkit router."""
    application = FastAPI()
    application.include_router(router)
    return application


@pytest.fixture
def clear_stores():
    """Clear in-memory stores before each test."""
    _files.clear()
    _profiles.clear()
    _plans.clear()
    _executions.clear()
    yield
    _files.clear()
    _profiles.clear()
    _plans.clear()
    _executions.clear()


@pytest.fixture
async def client(app, clear_stores):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ------------------------------------------------------------------
# Upload endpoint
# ------------------------------------------------------------------

class TestUpload:
    async def test_upload_returns_file_id(self, client):
        resp = await client.post(
            "/api/toolkit/upload",
            files={"file": ("test.csv", b"a,b,c\n1,2,3", "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "file_id" in data
        assert data["filename"] == "test.csv"
        assert data["size"] == 11

    async def test_upload_stores_content(self, client):
        resp = await client.post(
            "/api/toolkit/upload",
            files={"file": ("data.txt", b"hello world", "text/plain")},
        )
        file_id = resp.json()["file_id"]
        assert file_id in _files
        assert _files[file_id]["content"] == b"hello world"


# ------------------------------------------------------------------
# Profile endpoint
# ------------------------------------------------------------------

class TestProfile:
    async def test_profile_not_found(self, client):
        resp = await client.post("/api/toolkit/profile/nonexistent")
        assert resp.status_code == 404

    async def test_profile_returns_data_profile(self, client):
        # Upload first
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("test.csv", b"col1,col2\n1,2\n3,4", "text/csv")},
        )
        file_id = upload.json()["file_id"]

        resp = await client.post(f"/api/toolkit/profile/{file_id}")
        assert resp.status_code == 200
        profile = resp.json()
        assert "basic_info" in profile
        assert "quality_metrics" in profile
        assert profile["basic_info"]["file_type"] == "csv"


# ------------------------------------------------------------------
# Route endpoint
# ------------------------------------------------------------------

class TestRoute:
    async def test_route_requires_profile(self, client):
        resp = await client.post("/api/toolkit/route/nonexistent")
        assert resp.status_code == 404

    async def test_route_returns_processing_plan(self, client):
        # Upload + profile
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("test.txt", b"some text content", "text/plain")},
        )
        file_id = upload.json()["file_id"]
        await client.post(f"/api/toolkit/profile/{file_id}")

        resp = await client.post(f"/api/toolkit/route/{file_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "candidates" in data
        assert "origin" in data
        plan = data["plan"]
        assert "stages" in plan
        assert "explanation" in plan


# ------------------------------------------------------------------
# Execute endpoint
# ------------------------------------------------------------------

class TestExecute:
    async def test_execute_requires_plan(self, client):
        resp = await client.post("/api/toolkit/execute/nonexistent")
        assert resp.status_code == 404

    async def test_execute_full_pipeline(self, client):
        # Upload → Profile → Route → Execute
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        file_id = upload.json()["file_id"]
        await client.post(f"/api/toolkit/profile/{file_id}")
        await client.post(f"/api/toolkit/route/{file_id}")

        resp = await client.post(f"/api/toolkit/execute/{file_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "execution_id" in data
        assert data["status"] in ("completed", "failed")

    async def test_execute_invalid_strategy_returns_400(self, client):
        """Passing a strategy_name not in candidates → 400."""
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("t.txt", b"hello", "text/plain")},
        )
        file_id = upload.json()["file_id"]
        await client.post(f"/api/toolkit/profile/{file_id}")
        await client.post(f"/api/toolkit/route/{file_id}")

        resp = await client.post(
            f"/api/toolkit/execute/{file_id}",
            params={"strategy_name": "nonexistent_strategy"},
        )
        assert resp.status_code == 400
        assert "nonexistent_strategy" in resp.json()["detail"]

    async def test_execute_valid_strategy_override(self, client):
        """Passing a valid candidate strategy_name succeeds."""
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("data.csv", b"a,b\n1,2\n3,4", "text/csv")},
        )
        file_id = upload.json()["file_id"]
        await client.post(f"/api/toolkit/profile/{file_id}")
        route_resp = await client.post(f"/api/toolkit/route/{file_id}")
        candidates = route_resp.json()["candidates"]

        # Skip if no candidates available
        if not candidates:
            pytest.skip("No candidates returned by route")

        # Pick the last candidate (likely different from top-ranked)
        chosen = candidates[-1]["name"]
        resp = await client.post(
            f"/api/toolkit/execute/{file_id}",
            params={"strategy_name": chosen},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("completed", "failed")


# ------------------------------------------------------------------
# Status / Results endpoints
# ------------------------------------------------------------------

class TestStatusAndResults:
    async def test_status_not_found(self, client):
        resp = await client.get("/api/toolkit/status/nonexistent")
        assert resp.status_code == 404

    async def test_results_not_found(self, client):
        resp = await client.get("/api/toolkit/results/nonexistent")
        assert resp.status_code == 404

    async def test_status_after_execute(self, client):
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("t.txt", b"data", "text/plain")},
        )
        file_id = upload.json()["file_id"]
        await client.post(f"/api/toolkit/profile/{file_id}")
        await client.post(f"/api/toolkit/route/{file_id}")
        exec_resp = await client.post(f"/api/toolkit/execute/{file_id}")
        eid = exec_resp.json()["execution_id"]

        status = await client.get(f"/api/toolkit/status/{eid}")
        assert status.status_code == 200
        assert status.json()["status"] in ("completed", "failed")


# ------------------------------------------------------------------
# Pause / Resume / Cancel
# ------------------------------------------------------------------

class TestLifecycle:
    async def _setup_execution(self, client):
        """Helper: run full pipeline and return execution_id."""
        upload = await client.post(
            "/api/toolkit/upload",
            files={"file": ("t.txt", b"data", "text/plain")},
        )
        fid = upload.json()["file_id"]
        await client.post(f"/api/toolkit/profile/{fid}")
        await client.post(f"/api/toolkit/route/{fid}")
        resp = await client.post(f"/api/toolkit/execute/{fid}")
        return resp.json()["execution_id"]

    async def test_pause_execution(self, client):
        eid = await self._setup_execution(client)
        resp = await client.post(f"/api/toolkit/pause/{eid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    async def test_resume_execution(self, client):
        eid = await self._setup_execution(client)
        await client.post(f"/api/toolkit/pause/{eid}")
        resp = await client.post(f"/api/toolkit/resume/{eid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    async def test_cancel_execution(self, client):
        eid = await self._setup_execution(client)
        resp = await client.post(f"/api/toolkit/cancel/{eid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_pause_not_found(self, client):
        resp = await client.post("/api/toolkit/pause/nonexistent")
        assert resp.status_code == 404

    async def test_resume_not_found(self, client):
        resp = await client.post("/api/toolkit/resume/nonexistent")
        assert resp.status_code == 404

    async def test_cancel_not_found(self, client):
        resp = await client.post("/api/toolkit/cancel/nonexistent")
        assert resp.status_code == 404
