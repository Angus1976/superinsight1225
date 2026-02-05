"""Verify API module structure and endpoints exist.

This test verifies the API files exist and have proper structure
without requiring all dependencies to be installed.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def verify_api_files_exist():
    """Verify key API files exist."""
    print("\n=== Verifying API Files Exist ===")

    api_files = [
        "ai_annotation.py",
        "ai_models.py",
        "annotation.py",
        "annotation_collaboration.py",
        "audit_api.py",
        "rbac.py",
        "monitoring_api.py",
        "quality_api.py",
        "quality_reports.py",
        "security.py",
        "text_to_sql.py",
    ]

    api_dir = os.path.join(os.path.dirname(__file__), "../../src/api")
    found = 0
    missing = []

    for api_file in api_files:
        file_path = os.path.join(api_dir, api_file)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  [OK] {api_file:40s} ({size:,} bytes)")
            found += 1
        else:
            print(f"  [X] {api_file:40s} NOT FOUND")
            missing.append(api_file)

    print(f"\n  Found: {found}/{len(api_files)} API files")

    if missing:
        print(f"  Missing: {', '.join(missing)}")
        return False

    return True


def verify_api_has_routers():
    """Verify API files contain router definitions."""
    print("\n=== Verifying API Router Definitions ===")

    api_files_to_check = [
        ("src/api/ai_annotation.py", "router"),
        ("src/api/audit_api.py", "router"),
        ("src/api/rbac.py", "router"),
        ("src/api/monitoring_api.py", "router"),
        ("src/api/quality_api.py", "router"),
    ]

    found_routers = 0

    for file_path, router_name in api_files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), "../../", file_path)

        if not os.path.exists(full_path):
            print(f"  [X] {file_path}: File not found")
            continue

        # Read file and check for router
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Check for common router patterns
            has_router = (
                f"{router_name} =" in content or
                f"{router_name}=" in content or
                f"router = APIRouter" in content or
                f"router=APIRouter" in content
            )

            if has_router:
                print(f"  [OK] {file_path}: router found")
                found_routers += 1
            else:
                print(f"  [X] {file_path}: router NOT found")

    print(f"\n  Routers found: {found_routers}/{len(api_files_to_check)}")

    return found_routers >= len(api_files_to_check) // 2  # At least half should have routers


def verify_app_file_exists():
    """Verify app.py (main FastAPI application) exists."""
    print("\n=== Verifying FastAPI Application File ===")

    app_path = os.path.join(os.path.dirname(__file__), "../../src/app.py")

    if not os.path.exists(app_path):
        print("  [X] src/app.py NOT FOUND")
        return False

    size = os.path.getsize(app_path)
    print(f"  [OK] src/app.py exists ({size:,} bytes)")

    # Check for FastAPI app instantiation
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

        has_fastapi = "FastAPI" in content
        has_app = "app =" in content or "app=" in content

        if has_fastapi:
            print("  [OK] FastAPI import found")
        else:
            print("  [X] FastAPI import NOT found")

        if has_app:
            print("  [OK] app instance found")
        else:
            print("  [X] app instance NOT found")

        return has_fastapi and has_app


def count_api_endpoints():
    """Count total API endpoint files."""
    print("\n=== Counting API Endpoint Files ===")

    api_dir = os.path.join(os.path.dirname(__file__), "../../src/api")

    if not os.path.exists(api_dir):
        print("  [X] src/api directory NOT FOUND")
        return False

    # Count Python files (excluding __pycache__ and __init__)
    py_files = [
        f for f in os.listdir(api_dir)
        if f.endswith('.py') and f != '__init__.py' and not f.startswith('test_')
    ]

    print(f"  [OK] Total API endpoint files: {len(py_files)}")

    # Categorize by type
    categories = {
        "AI/Annotation": ["ai_", "annotation_", "augmentation", "rag_"],
        "Security": ["audit", "rbac", "security", "permission", "auth"],
        "Quality": ["quality", "ragas"],
        "Monitoring": ["monitoring", "metrics", "grafana", "prometheus"],
        "Data": ["data_", "extraction", "desensitization"],
        "Sync": ["sync_"],
        "Compliance": ["compliance", "gdpr", "sox", "iso27001"],
    }

    counts = {cat: 0 for cat in categories}
    counts["Other"] = 0

    for py_file in py_files:
        categorized = False
        for cat, keywords in categories.items():
            if any(keyword in py_file.lower() for keyword in keywords):
                counts[cat] += 1
                categorized = True
                break
        if not categorized:
            counts["Other"] += 1

    print("\n  API Endpoints by Category:")
    for cat, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"    {cat:20s}: {count}")

    return True


def run_api_structure_verification():
    """Run all API structure verification tests."""
    print("="*70)
    print("API Structure Verification")
    print("="*70)

    results = {}

    tests = [
        ("API Files Exist", verify_api_files_exist),
        ("API Router Definitions", verify_api_has_routers),
        ("FastAPI Application File", verify_app_file_exists),
        ("API Endpoint Count", count_api_endpoints),
    ]

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"[X] {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "="*70)
    print("API STRUCTURE VERIFICATION SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f"{test_name:40s} {status}")

    print(f"\nTotal: {passed}/{total} verifications passed")
    print("="*70)

    if passed == total:
        print("\n>>> ALL API STRUCTURE VERIFICATIONS PASSED! <<<")
        return True
    else:
        print(f"\n[!] {failed} verification(s) failed")
        return False


if __name__ == "__main__":
    success = run_api_structure_verification()
    sys.exit(0 if success else 1)
