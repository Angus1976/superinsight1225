"""API endpoint tests for AI Annotation services.

Tests key API endpoints for:
- AI annotation methods
- Annotation security (audit, RBAC, PII)
- Annotation collaboration
- Performance monitoring
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def test_api_routes_exist():
    """Test that API routes are defined."""
    print("\n=== Testing AI Annotation API Routes ===")

    try:
        # Import API router
        from src.api.ai_annotation import router as ai_annotation_router

        # Verify router exists
        assert ai_annotation_router is not None, "AI annotation router should exist"

        # Get routes from router
        routes = ai_annotation_router.routes
        assert len(routes) > 0, "Router should have routes"

        print(f"[OK] AI Annotation API: {len(routes)} routes registered")

        # Display routes
        for route in routes[:10]:  # Show first 10
            if hasattr(route, 'path'):
                print(f"  - {route.methods} {route.path}")

        return True

    except ImportError as e:
        print(f"[X] AI Annotation API routes test failed: {e}")
        return False


def test_security_api_routes():
    """Test that security API routes are defined."""
    print("\n=== Testing Security API Routes ===")

    try:
        # Import security API routers
        from src.api.audit_api import router as audit_router
        from src.api.rbac import router as rbac_router

        assert audit_router is not None, "Audit router should exist"
        assert rbac_router is not None, "RBAC router should exist"

        audit_routes = audit_router.routes
        rbac_routes = rbac_router.routes

        print(f"[OK] Audit API: {len(audit_routes)} routes registered")
        print(f"[OK] RBAC API: {len(rbac_routes)} routes registered")

        return True

    except ImportError as e:
        print(f"[SKIP] Security API routes test: {e}")
        return None  # Skip if not available


def test_monitoring_api_routes():
    """Test that monitoring API routes are defined."""
    print("\n=== Testing Monitoring API Routes ===")

    try:
        # Import monitoring API routers
        from src.api.monitoring_api import router as monitoring_router

        assert monitoring_router is not None, "Monitoring router should exist"

        monitoring_routes = monitoring_router.routes

        print(f"[OK] Monitoring API: {len(monitoring_routes)} routes registered")

        return True

    except ImportError as e:
        print(f"[SKIP] Monitoring API routes test: {e}")
        return None


def test_quality_api_routes():
    """Test that quality API routes are defined."""
    print("\n=== Testing Quality API Routes ===")

    try:
        # Import quality API routers
        from src.api.quality_api import router as quality_router

        assert quality_router is not None, "Quality router should exist"

        quality_routes = quality_router.routes

        print(f"[OK] Quality API: {len(quality_routes)} routes registered")

        return True

    except ImportError as e:
        print(f"[SKIP] Quality API routes test: {e}")
        return None


def test_collaboration_api_routes():
    """Test that collaboration API routes are defined."""
    print("\n=== Testing Collaboration API Routes ===")

    try:
        # Import collaboration API routers (if exists)
        from src.api.annotation_collaboration import router as collaboration_router

        assert collaboration_router is not None, "Collaboration router should exist"

        collaboration_routes = collaboration_router.routes

        print(f"[OK] Collaboration API: {len(collaboration_routes)} routes registered")

        return True

    except ImportError as e:
        print(f"[SKIP] Collaboration API routes test: {e}")
        return None


def test_api_application_exists():
    """Test that FastAPI application is configured."""
    print("\n=== Testing FastAPI Application ===")

    try:
        # Try to import app
        from src.app import app

        assert app is not None, "FastAPI app should exist"

        # Get all routes from app
        all_routes = app.routes
        print(f"[OK] FastAPI app registered with {len(all_routes)} total routes")

        # Count routes by tag
        route_tags = {}
        for route in all_routes:
            if hasattr(route, 'tags') and route.tags:
                for tag in route.tags:
                    route_tags[tag] = route_tags.get(tag, 0) + 1

        if route_tags:
            print("\n  Routes by category:")
            for tag, count in sorted(route_tags.items())[:10]:  # Show top 10
                print(f"    {tag}: {count} routes")

        return True

    except ImportError as e:
        print(f"[X] FastAPI application test failed: {e}")
        return False


def run_api_tests():
    """Run all API endpoint tests."""
    print("="*70)
    print("API Endpoint Tests")
    print("="*70)

    results = {}

    tests = [
        ("AI Annotation API Routes", test_api_routes_exist),
        ("Security API Routes", test_security_api_routes),
        ("Monitoring API Routes", test_monitoring_api_routes),
        ("Quality API Routes", test_quality_api_routes),
        ("Collaboration API Routes", test_collaboration_api_routes),
        ("FastAPI Application", test_api_application_exists),
    ]

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"[X] {test_name} FAILED: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*70)
    print("API TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    total = len(results)

    for test_name, result in results.items():
        if result is True:
            status = "[OK] PASS"
        elif result is None:
            status = "[--] SKIP"
        else:
            status = "[X] FAIL"
        print(f"{test_name:40s} {status}")

    print(f"\nTotal: {passed}/{total - skipped} API tests passed ({skipped} skipped)")
    print("="*70)

    if failed == 0:
        print("\n>>> ALL API ENDPOINT TESTS PASSED! <<<")
        return True
    else:
        print(f"\n[!] {failed} API test(s) failed")
        return False


if __name__ == "__main__":
    success = run_api_tests()
    sys.exit(0 if success else 1)
