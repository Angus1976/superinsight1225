#!/usr/bin/env python3
"""
Label Studio Enterprise Workspace Smoke Test Script

This script performs smoke tests to verify the workspace deployment.

Usage:
    python smoke_test_workspace.py [--api-url URL] [--token TOKEN]

Example:
    python smoke_test_workspace.py --api-url http://localhost:8000 --token your-jwt-token
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import uuid4

try:
    import requests
except ImportError:
    print("Error: 'requests' module is required. Install with: pip install requests")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TestConfig:
    """Test configuration."""
    api_url: str
    token: str
    timeout: int = 30
    verbose: bool = False


@dataclass
class TestResult:
    """Test result."""
    name: str
    passed: bool
    duration_ms: float
    message: str = ""
    details: Optional[dict] = None


# =============================================================================
# Test Client
# =============================================================================

class WorkspaceTestClient:
    """HTTP client for workspace API tests."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.base_url = f"{config.api_url}/api/ls-workspaces"
        self.headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request."""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", self.config.timeout)

        if self.config.verbose:
            print(f"  {method} {url}")

        return requests.request(method, url, **kwargs)

    def create_workspace(self, name: str, description: str = "") -> dict:
        """Create a workspace."""
        resp = self._request("POST", "", json={
            "name": name,
            "description": description,
        })
        resp.raise_for_status()
        return resp.json()

    def list_workspaces(self) -> dict:
        """List workspaces."""
        resp = self._request("GET", "")
        resp.raise_for_status()
        return resp.json()

    def get_workspace(self, workspace_id: str) -> dict:
        """Get workspace details."""
        resp = self._request("GET", f"/{workspace_id}")
        resp.raise_for_status()
        return resp.json()

    def update_workspace(self, workspace_id: str, data: dict) -> dict:
        """Update workspace."""
        resp = self._request("PUT", f"/{workspace_id}", json=data)
        resp.raise_for_status()
        return resp.json()

    def delete_workspace(self, workspace_id: str) -> None:
        """Delete workspace."""
        resp = self._request("DELETE", f"/{workspace_id}")
        resp.raise_for_status()

    def get_permissions(self, workspace_id: str) -> dict:
        """Get user permissions for workspace."""
        resp = self._request("GET", f"/{workspace_id}/permissions")
        resp.raise_for_status()
        return resp.json()

    def list_members(self, workspace_id: str) -> dict:
        """List workspace members."""
        resp = self._request("GET", f"/{workspace_id}/members")
        resp.raise_for_status()
        return resp.json()

    def list_projects(self, workspace_id: str) -> dict:
        """List workspace projects."""
        resp = self._request("GET", f"/{workspace_id}/projects")
        resp.raise_for_status()
        return resp.json()


# =============================================================================
# Smoke Tests
# =============================================================================

class SmokeTestRunner:
    """Smoke test runner."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.client = WorkspaceTestClient(config)
        self.results: List[TestResult] = []
        self.test_workspace_id: Optional[str] = None

    def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test and record result."""
        start = time.perf_counter()
        try:
            test_func()
            duration = (time.perf_counter() - start) * 1000
            result = TestResult(name=name, passed=True, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            result = TestResult(
                name=name,
                passed=False,
                duration_ms=duration,
                message=str(e)
            )

        self.results.append(result)
        return result

    def test_api_health(self):
        """Test API health endpoint."""
        resp = requests.get(
            f"{self.config.api_url}/health",
            timeout=self.config.timeout
        )
        assert resp.status_code == 200, f"Health check failed: {resp.status_code}"

    def test_create_workspace(self):
        """Test workspace creation."""
        name = f"SmokeTest-{uuid4().hex[:8]}"
        workspace = self.client.create_workspace(
            name=name,
            description="Smoke test workspace"
        )

        assert "id" in workspace, "No workspace ID returned"
        assert workspace["name"] == name, "Workspace name mismatch"

        self.test_workspace_id = workspace["id"]

    def test_list_workspaces(self):
        """Test workspace listing."""
        result = self.client.list_workspaces()

        assert "items" in result, "No items in response"
        assert "total" in result, "No total in response"
        assert isinstance(result["items"], list), "Items is not a list"

    def test_get_workspace(self):
        """Test getting workspace details."""
        assert self.test_workspace_id, "No test workspace created"

        workspace = self.client.get_workspace(self.test_workspace_id)

        assert workspace["id"] == self.test_workspace_id
        assert "name" in workspace
        assert "owner_id" in workspace

    def test_update_workspace(self):
        """Test updating workspace."""
        assert self.test_workspace_id, "No test workspace created"

        updated = self.client.update_workspace(
            self.test_workspace_id,
            {"description": "Updated by smoke test"}
        )

        assert updated["description"] == "Updated by smoke test"

    def test_get_permissions(self):
        """Test getting user permissions."""
        assert self.test_workspace_id, "No test workspace created"

        perms = self.client.get_permissions(self.test_workspace_id)

        assert "permissions" in perms, "No permissions in response"
        assert "role" in perms, "No role in response"
        assert "workspace:view" in perms["permissions"], "Missing view permission"

    def test_list_members(self):
        """Test listing workspace members."""
        assert self.test_workspace_id, "No test workspace created"

        result = self.client.list_members(self.test_workspace_id)

        assert "items" in result, "No items in response"
        assert len(result["items"]) >= 1, "Owner should be a member"

    def test_list_projects(self):
        """Test listing workspace projects."""
        assert self.test_workspace_id, "No test workspace created"

        result = self.client.list_projects(self.test_workspace_id)

        assert "items" in result, "No items in response"
        assert "total" in result, "No total in response"

    def test_delete_workspace(self):
        """Test deleting workspace."""
        assert self.test_workspace_id, "No test workspace created"

        self.client.delete_workspace(self.test_workspace_id)

        # Verify deletion
        try:
            self.client.get_workspace(self.test_workspace_id)
            raise AssertionError("Workspace should be deleted")
        except requests.HTTPError as e:
            assert e.response.status_code == 404, f"Expected 404, got {e.response.status_code}"

        self.test_workspace_id = None

    def cleanup(self):
        """Cleanup test data."""
        if self.test_workspace_id:
            try:
                self.client.delete_workspace(self.test_workspace_id)
            except Exception:
                pass

    def run_all_tests(self) -> Tuple[int, int]:
        """Run all smoke tests."""
        tests = [
            ("API Health Check", self.test_api_health),
            ("Create Workspace", self.test_create_workspace),
            ("List Workspaces", self.test_list_workspaces),
            ("Get Workspace", self.test_get_workspace),
            ("Update Workspace", self.test_update_workspace),
            ("Get Permissions", self.test_get_permissions),
            ("List Members", self.test_list_members),
            ("List Projects", self.test_list_projects),
            ("Delete Workspace", self.test_delete_workspace),
        ]

        print("\n" + "=" * 60)
        print("  Label Studio Workspace Smoke Tests")
        print("  API URL:", self.config.api_url)
        print("  Date:", datetime.now().isoformat())
        print("=" * 60 + "\n")

        passed = 0
        failed = 0

        for name, test_func in tests:
            result = self.run_test(name, test_func)

            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"  {status}  {name} ({result.duration_ms:.1f}ms)")

            if not result.passed:
                print(f"         Error: {result.message}")
                failed += 1
            else:
                passed += 1

        # Cleanup
        self.cleanup()

        # Print summary
        print("\n" + "-" * 60)
        print(f"  Results: {passed} passed, {failed} failed")
        print("-" * 60 + "\n")

        return passed, failed


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Label Studio Workspace Smoke Tests"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="JWT authentication token"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    config = TestConfig(
        api_url=args.api_url.rstrip("/"),
        token=args.token,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    runner = SmokeTestRunner(config)
    passed, failed = runner.run_all_tests()

    # Exit with error code if any tests failed
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
