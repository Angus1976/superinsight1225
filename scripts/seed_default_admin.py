#!/usr/bin/env python3
"""
Insert default dev admin if users table has no admin@superinsight.local.

Usage (from repo root, with DATABASE_URL set — e.g. Docker host):
  DATABASE_URL=postgresql://superinsight:password@localhost:5432/superinsight \\
    python3 scripts/seed_default_admin.py

  注意：若本机也装了 PostgreSQL 并占用 5432，上述 URL 可能连到「本机库」而非 Docker 内 postgres。
  此时应在 app 容器内执行（见下），或改用仅 Docker 暴露的端口/网络。

Reset password for existing admin (dev only):
  DATABASE_URL=... python3 scripts/seed_default_admin.py --force

Inside app container (postgres hostname is `postgres`; 与 compose 中 app 使用同一数据库):
  docker exec -w /app superinsight-app python scripts/seed_default_admin.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@superinsight.local")
    password = os.environ.get("SEED_ADMIN_PASSWORD", "Admin@123456")
    tenant_id = os.environ.get("SEED_ADMIN_TENANT_ID", "default_tenant")

    try:
        import bcrypt
    except ImportError:
        print("bcrypt is required", file=sys.stderr)
        return 1

    from uuid import uuid4

    engine = create_engine(url)
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    force = "--force" in sys.argv or os.environ.get("SEED_FORCE_UPDATE", "").lower() in (
        "1",
        "true",
        "yes",
    )

    with engine.begin() as conn:
        n = conn.execute(
            text("SELECT COUNT(*) FROM users WHERE LOWER(email) = LOWER(:e)"),
            {"e": email},
        ).scalar()
        if n and int(n) > 0:
            if force:
                conn.execute(
                    text("UPDATE users SET password_hash = :ph, updated_at = NOW() WHERE LOWER(email) = LOWER(:e)"),
                    {"ph": pw_hash, "e": email},
                )
                print(f"Updated password for {email} (use SEED_ADMIN_PASSWORD or default Admin@123456)")
                return 0
            print(f"Already exists: {email} (skip)")
            return 0

        uid = str(uuid4())
        # role：仅 000_core_tables 时为 varchar；若已跑安全相关迁移则为 userrole 枚举，直接写入字面量即可
        conn.execute(
            text(
                """
                INSERT INTO users (
                    id, username, email, password_hash, full_name,
                    role, tenant_id, is_active, created_at, updated_at
                )
                VALUES (
                    CAST(:id AS uuid), :username, :email, :ph, :fn,
                    :role, :tid, true, NOW(), NOW()
                )
                """
            ),
            {
                "id": uid,
                "username": "admin_user",
                "email": email,
                "ph": pw_hash,
                "fn": "Administrator",
                "role": "admin",
                "tid": tenant_id,
            },
        )
        print(f"Seeded admin: {email} / (password from SEED_ADMIN_PASSWORD or default)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
