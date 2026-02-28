"""Tests for the frontend component discovery system."""

import pytest
from tests.frontend_discovery import (
    extract_api_calls,
    extract_routes,
    discover_service_api_calls,
    discover_component_api_calls,
    discover_routes,
    discover_frontend_components,
    ApiCallInfo,
    RouteInfo,
    FRONTEND_SRC,
)


# ---------------------------------------------------------------------------
# Unit tests for parsing helpers
# ---------------------------------------------------------------------------

class TestExtractApiCalls:
    def test_extracts_get_call(self):
        content = "await apiClient.get<Task>('/api/tasks')"
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 1
        assert calls[0].method == "GET"
        assert calls[0].endpoint == "/api/tasks"

    def test_extracts_post_call(self):
        content = "await apiClient.post('/api/auth/login', payload)"
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_extracts_patch_call(self):
        content = "await apiClient.patch<Task>('/api/tasks/1', data)"
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 1
        assert calls[0].method == "PATCH"

    def test_extracts_delete_call(self):
        content = "await apiClient.delete('/api/tasks/1')"
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 1
        assert calls[0].method == "DELETE"

    def test_extracts_api_endpoint_constant(self):
        content = "await apiClient.get(API_ENDPOINTS.TASKS.BASE)"
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 1
        assert "API_ENDPOINTS" in calls[0].endpoint or "TASKS" in calls[0].endpoint

    def test_extracts_multiple_calls(self):
        content = """
        await apiClient.get('/api/tasks');
        await apiClient.post('/api/tasks', data);
        await apiClient.delete('/api/tasks/1');
        """
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 3

    def test_extracts_fetch_call(self):
        content = "fetch('/api/health')"
        calls = extract_api_calls(content, "test.ts")
        assert len(calls) == 1
        assert calls[0].endpoint == "/api/health"

    def test_empty_content(self):
        calls = extract_api_calls("", "test.ts")
        assert calls == []

    def test_source_file_set(self):
        content = "await apiClient.get('/api/tasks')"
        calls = extract_api_calls(content, "services/task.ts")
        assert calls[0].source_file == "services/task.ts"


class TestExtractRoutes:
    SAMPLE_ROUTER = """
const LoginPage = lazyWithPreload(() => import('@/pages/Login'));
const DashboardPage = lazyWithPreload(() => import('@/pages/Dashboard'));
const TasksPage = lazyWithPreload(() => import('@/pages/Tasks'));

export const routes = [
  { path: '/login', element: withMinimalSuspense(LoginPage) },
  { path: 'dashboard', element: withSuspense(DashboardPage, 'dashboard') },
  { path: 'tasks', element: withSuspense(TasksPage, 'table') },
];
"""

    def test_extracts_routes(self):
        routes = extract_routes(self.SAMPLE_ROUTER)
        assert len(routes) >= 3

    def test_route_paths(self):
        routes = extract_routes(self.SAMPLE_ROUTER)
        paths = [r.path for r in routes]
        assert "/login" in paths
        assert "dashboard" in paths
        assert "tasks" in paths

    def test_route_components(self):
        routes = extract_routes(self.SAMPLE_ROUTER)
        components = [r.component_name for r in routes]
        assert "LoginPage" in components
        assert "DashboardPage" in components

    def test_import_paths_resolved(self):
        routes = extract_routes(self.SAMPLE_ROUTER)
        login = [r for r in routes if r.component_name == "LoginPage"]
        assert len(login) == 1
        assert login[0].import_path == "@/pages/Login"

    def test_empty_content(self):
        routes = extract_routes("")
        assert routes == []


# ---------------------------------------------------------------------------
# Integration tests against actual project files
# ---------------------------------------------------------------------------

class TestDiscoverServiceApiCalls:
    def test_discovers_calls(self):
        calls = discover_service_api_calls()
        assert len(calls) > 0

    def test_finds_auth_calls(self):
        calls = discover_service_api_calls()
        auth_calls = [c for c in calls if "auth" in c.source_file.lower()]
        assert len(auth_calls) > 0

    def test_finds_task_calls(self):
        calls = discover_service_api_calls()
        task_calls = [c for c in calls if "task" in c.source_file.lower()]
        assert len(task_calls) > 0


class TestDiscoverRoutes:
    def test_discovers_routes(self):
        routes = discover_routes()
        assert len(routes) > 0

    def test_login_route_found(self):
        routes = discover_routes()
        paths = [r.path for r in routes]
        assert any("login" in p.lower() for p in paths)

    def test_dashboard_route_found(self):
        routes = discover_routes()
        paths = [r.path for r in routes]
        assert any("dashboard" in p for p in paths)


class TestDiscoverFrontendComponents:
    def test_returns_complete_report(self):
        report = discover_frontend_components()
        assert "service_api_calls" in report
        assert "component_api_calls" in report
        assert "routes" in report
        assert "route_component_map" in report
        assert "summary" in report

    def test_summary_counts(self):
        report = discover_frontend_components()
        s = report["summary"]
        assert s["total_service_api_calls"] > 0
        assert s["total_routes"] > 0
        assert s["unique_endpoints"] > 0

    def test_nonexistent_dir_returns_empty(self):
        report = discover_frontend_components("/nonexistent/path")
        assert report["summary"]["total_service_api_calls"] == 0
        assert report["summary"]["total_routes"] == 0

    def test_route_component_map_populated(self):
        report = discover_frontend_components()
        assert len(report["route_component_map"]) > 0
