"""Integration-test hooks.

``test_llm_backward_compatibility`` exercises the process-global ``db_manager`` singleton.
That can leave SQLAlchemy metadata / engine bindings in a state where other tests that
use an isolated in-memory SQLite session (e.g. ``test_legacy_api_compat``) no longer see
rows on ``EnhancedDataModel``. Running LLM backward-compat tests last avoids flaky 404s
when the full ``tests/integration/`` suite runs in one process.
"""


def pytest_collection_modifyitems(items):
    """Run legacy compat API tests first and LLM backward-compat tests last.

    Several modules touch the process-global ``db_manager`` singleton; that can
    confuse isolated SQLite fixtures. Ordering avoids flaky EnhancedDataModel
    lookups and keeps LLM DB setup from colliding with other LLM integration tests.
    """

    def _key(item):
        path = str(getattr(item, "path", None) or getattr(item, "fspath", "") or "")
        if "test_legacy_api_compat.py" in path:
            return (-1, path, item.nodeid)
        if "test_llm_backward_compatibility.py" in path:
            return (1, path, item.nodeid)
        return (0, path, item.nodeid)

    items.sort(key=_key)
