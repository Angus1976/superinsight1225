"""Tests for the backend endpoint discovery system."""

import pytest
from tests.endpoint_discovery import (
    extract_prefix,
    classify_endpoint,
    extract_endpoints,
    discover_endpoints,
    EndpointInfo,
    API_DIR,
)


# ---------------------------------------------------------------------------
# Unit tests for parsing helpers
# ---------------------------------------------------------------------------

class TestExtractPrefix:
    def test_extracts_prefix(self):
        content = 'router = APIRouter(prefix="/api/tasks", tags=["Tasks"])'
        assert extract_prefix(content) == "/api/tasks"

    def test_prefix_with_version(self):
        content = 'router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])'
        assert extract_prefix(content) == "/api/v1/admin"

    def test_no_prefix(self):
        content = "router = APIRouter(tags=['Misc'])"
        assert extract_prefix(content) == ""

    def test_empty_content(self):
        assert extract_prefix("") == ""


class TestClassifyEndpoint:
    def test_get_is_read(self):
        assert classify_endpoint("GET", "/api/tasks") == "Read"

    def test_post_is_create(self):
        assert classify_endpoint("POST", "/api/tasks") == "Create"

    def test_put_is_update(self):
        assert classify_endpoint("PUT", "/api/tasks/1") == "Update"

    def test_patch_is_update(self):
        assert classify_endpoint("PATCH", "/api/tasks/1") == "Update"

    def test_delete_is_delete(self):
        assert classify_endpoint("DELETE", "/api/tasks/1") == "Delete"

    def test_login_is_business(self):
        assert classify_endpoint("POST", "/api/auth/login") == "Business"

    def test_sync_is_business(self):
        assert classify_endpoint("POST", "/api/v1/sync/push") == "Business"

    def test_export_is_business(self):
        assert classify_endpoint("GET", "/api/export/csv") == "Business"

    def test_stats_is_business(self):
        assert classify_endpoint("GET", "/api/tasks/stats") == "Business"

    def test_batch_is_business(self):
        assert classify_endpoint("POST", "/api/tasks/batch/delete") == "Business"


class TestExtractEndpoints:
    SAMPLE_FILE = '''
router = APIRouter(prefix="/api/items", tags=["Items"])

@router.get("")
def list_items():
    pass

@router.post("")
async def create_item(request):
    pass

@router.get("/{item_id}")
def get_item(item_id: str):
    pass

@router.patch("/{item_id}")
def update_item(item_id: str):
    pass

@router.delete("/{item_id}")
def delete_item(item_id: str):
    pass
'''

    def test_extracts_all_endpoints(self):
        eps = extract_endpoints(self.SAMPLE_FILE, "items.py")
        assert len(eps) == 5

    def test_methods_correct(self):
        eps = extract_endpoints(self.SAMPLE_FILE, "items.py")
        methods = [e.method for e in eps]
        assert methods == ["GET", "POST", "GET", "PATCH", "DELETE"]

    def test_full_path_includes_prefix(self):
        eps = extract_endpoints(self.SAMPLE_FILE, "items.py")
        assert eps[0].full_path == "/api/items"
        assert eps[2].full_path == "/api/items/{item_id}"

    def test_handler_names(self):
        eps = extract_endpoints(self.SAMPLE_FILE, "items.py")
        handlers = [e.handler for e in eps]
        assert "list_items" in handlers
        assert "create_item" in handlers

    def test_categories_assigned(self):
        eps = extract_endpoints(self.SAMPLE_FILE, "items.py")
        cats = [e.category for e in eps]
        assert "Read" in cats
        assert "Create" in cats
        assert "Delete" in cats

    def test_source_file_set(self):
        eps = extract_endpoints(self.SAMPLE_FILE, "items.py")
        assert all(e.source_file == "items.py" for e in eps)

    def test_no_prefix_file(self):
        content = '''
router = APIRouter(tags=["Misc"])

@router.get("/health")
def health():
    pass
'''
        eps = extract_endpoints(content, "misc.py")
        assert len(eps) == 1
        assert eps[0].full_path == "/health"


# ---------------------------------------------------------------------------
# Integration tests against actual project files
# ---------------------------------------------------------------------------

class TestDiscoverEndpoints:
    def test_discovers_endpoints(self):
        report = discover_endpoints()
        assert report["summary"]["total_endpoints"] > 0

    def test_discovers_multiple_files(self):
        report = discover_endpoints()
        assert report["summary"]["total_files"] > 5

    def test_tasks_file_found(self):
        report = discover_endpoints()
        assert "tasks.py" in report["by_file"]

    def test_auth_file_found(self):
        report = discover_endpoints()
        # auth_simple.py or auth.py should be present
        auth_files = [f for f in report["by_file"] if "auth" in f]
        assert len(auth_files) > 0

    def test_report_has_all_keys(self):
        report = discover_endpoints()
        assert "endpoints" in report
        assert "by_file" in report
        assert "by_category" in report
        assert "summary" in report

    def test_summary_has_method_counts(self):
        report = discover_endpoints()
        methods = report["summary"]["by_method"]
        assert "GET" in methods
        assert "POST" in methods

    def test_summary_has_category_counts(self):
        report = discover_endpoints()
        cats = report["summary"]["by_category"]
        assert len(cats) > 0

    def test_crud_categories_present(self):
        report = discover_endpoints()
        cats = set(report["summary"]["by_category"].keys())
        # At minimum Read and Create should exist
        assert "Read" in cats
        assert "Create" in cats

    def test_nonexistent_dir_returns_empty(self):
        report = discover_endpoints("/nonexistent/path")
        assert report["summary"]["total_endpoints"] == 0

    def test_endpoint_dicts_have_required_fields(self):
        report = discover_endpoints()
        required = {"method", "path", "full_path", "handler", "category", "source_file"}
        for ep in report["endpoints"][:5]:
            assert required.issubset(ep.keys())
