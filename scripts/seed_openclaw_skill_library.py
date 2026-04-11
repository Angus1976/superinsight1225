#!/usr/bin/env python3
"""Bootstrap default OpenClaw gateway + ClawHub skill catalog + admin permissions.

Usage (DATABASE_URL set, from repo root):
  python3 scripts/seed_openclaw_skill_library.py
  SEED_TENANT_ID=default_tenant python3 scripts/seed_openclaw_skill_library.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import db_manager
from src.ai_integration.openclaw_bootstrap import bootstrap_openclaw_skill_library


def main() -> int:
    tenant_id = os.environ.get("SEED_TENANT_ID", "default_tenant")
    db_manager.initialize()
    try:
        with db_manager.get_session() as session:
            result = bootstrap_openclaw_skill_library(session, tenant_id)
            print(result)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
