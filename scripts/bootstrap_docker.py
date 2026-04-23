#!/usr/bin/env python3
"""
Docker / 本地一键：数据库迁移（Alembic 多 head）+ 幂等种子数据。

- 不会清空已有数据：Alembic 仅升级；用户 / LLM / AI 集成仅在对应表为空或缺行时插入。
- 在 app 容器或独立 db-migrate 容器中执行：DATABASE_URL 须指向 PostgreSQL。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("bootstrap")


def _wait_tcp(host: str, port: int, timeout_s: float = 120.0) -> None:
    import socket

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                return
        except OSError:
            time.sleep(1.0)
    raise RuntimeError(f"Timeout waiting for {host}:{port}")


def _parse_alembic_heads() -> list[str]:
    out = subprocess.check_output(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=str(ROOT),
        text=True,
    )
    revs: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("INFO"):
            continue
        # 例: 034_add_ai_data_source_config (sync_pipeline) (head)
        token = line.split()[0]
        if token and token[0].isalnum():
            revs.append(token)
    return revs


def _repair_alembic_version_table() -> None:
    """当 alembic_version 指向仓库中不存在的 revision 时，清空并写入当前仓库全部 heads（不删业务表）。"""
    from sqlalchemy import create_engine, text

    url = os.environ["DATABASE_URL"]
    heads = _parse_alembic_heads()
    if not heads:
        raise RuntimeError("无法解析 alembic heads，请检查 alembic 配置")

    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM alembic_version"))
        for h in heads:
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": h})
    logger.warning(
        "已重写 alembic_version 为当前仓库 heads: %s（保留业务数据；若 schema 与版本不一致请自行核对）",
        heads,
    )


def run_migrations() -> None:
    """执行 Alembic upgrade；若库中 version 指向已删除的 revision，可选修复 version 表后再 upgrade。"""
    cmd = [sys.executable, "-m", "alembic", "upgrade", "heads"]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode == 0:
        logger.info("Alembic upgrade heads 完成")
        return

    blob = (r.stderr or "") + (r.stdout or "")
    logger.error("Alembic upgrade 失败:\n%s", blob[-4000:])
    repair = os.getenv("ALEMBIC_AUTO_REPAIR_VERSION", "false").lower() in ("1", "true", "yes")
    if repair and "Can't locate revision" in blob:
        logger.warning("检测到缺失的 migration revision，正在修复 alembic_version 表…")
        _repair_alembic_version_table()
        subprocess.check_call(cmd, cwd=str(ROOT))
        logger.info("Alembic upgrade heads 完成（修复后）")
        return

    raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)


def seed_users() -> None:
    """创建演示用户。须与 src/api/auth_simple.py 一致使用原生 bcrypt，避免 passlib 与 bcrypt 版本不兼容时落到 SHA256。"""
    import bcrypt

    from src.database.connection import db_manager
    from src.security.models import UserModel, UserRole

    test_users = [
        {
            "username": "admin_user",
            "email": "admin@superinsight.local",
            "password": "Admin@123456",
            "full_name": "Administrator",
            "role": UserRole.ADMIN,
            "tenant_id": "default_tenant",
        },
        {
            "username": "business_expert",
            "email": "business@superinsight.local",
            "password": "Business@123456",
            "full_name": "Business Expert",
            "role": UserRole.BUSINESS_EXPERT,
            "tenant_id": "default_tenant",
        },
        {
            "username": "technical_expert",
            "email": "technical@superinsight.local",
            "password": "Technical@123456",
            "full_name": "Technical Expert",
            "role": UserRole.TECHNICAL_EXPERT,
            "tenant_id": "default_tenant",
        },
        {
            "username": "contractor",
            "email": "contractor@superinsight.local",
            "password": "Contractor@123456",
            "full_name": "Contractor User",
            "role": UserRole.CONTRACTOR,
            "tenant_id": "default_tenant",
        },
        {
            "username": "viewer",
            "email": "viewer@superinsight.local",
            "password": "Viewer@123456",
            "full_name": "Viewer User",
            "role": UserRole.VIEWER,
            "tenant_id": "default_tenant",
        },
    ]

    def _hash_pw(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    def _looks_like_sha256_hex(h: str) -> bool:
        if not h or len(h) != 64:
            return False
        try:
            int(h, 16)
            return True
        except ValueError:
            return False

    db_manager.initialize()
    created = 0
    skipped = 0
    repaired = 0
    with db_manager.get_session() as db:
        for u in test_users:
            exists = (
                db.query(UserModel)
                .filter(
                    (UserModel.username == u["username"]) | (UserModel.email == u["email"])
                )
                .first()
            )
            if exists:
                if _looks_like_sha256_hex(exists.password_hash):
                    exists.password_hash = _hash_pw(u["password"])
                    db.add(exists)
                    db.commit()
                    repaired += 1
                else:
                    skipped += 1
                continue
            user = UserModel(
                username=u["username"],
                email=u["email"],
                password_hash=_hash_pw(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                tenant_id=u["tenant_id"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created += 1
    logger.info("用户种子: 新建 %s, 跳过(已存在) %s, 修复错误哈希 %s", created, skipped, repaired)


def seed_llm_and_ai() -> None:
    from sqlalchemy import create_engine, inspect, text

    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        logger.info("跳过 LLM/AI 种子（非 PostgreSQL）")
        return

    engine = create_engine(url, future=True)
    insp = inspect(engine)
    if not insp.has_table("llm_configurations"):
        logger.info("无 llm_configurations 表，跳过 LLM 种子")
        return

    cols = {c["name"] for c in insp.get_columns("llm_configurations")}
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM llm_configurations")).scalar_one()
        if n > 0:
            logger.info("llm_configurations 已有 %s 条，跳过默认 LLM 插入", n)
        else:
            cfg = {
                "provider": "ollama",
                "base_url": os.getenv("OLLAMA_SEED_BASE_URL", "http://ollama:11434"),
                "model": os.getenv("OLLAMA_SEED_MODEL", "llama3.2"),
            }
            fields = ["id", "config_data", "default_method", "is_active", "is_default", "name", "description"]
            values = {
                "id": str(uuid.uuid4()),
                "config_data": json.dumps(cfg),
                "default_method": "local_ollama",
                "is_active": True,
                "is_default": True,
                "name": "Docker Ollama",
                "description": "bootstrap_docker.py 默认配置，可在管理后台修改",
            }
            if "tenant_id" in cols:
                fields.append("tenant_id")
                values["tenant_id"] = None
            if "provider" in cols:
                fields.append("provider")
                values["provider"] = "ollama"
            if "created_by" in cols:
                fields.append("created_by")
                values["created_by"] = None
            if "updated_by" in cols:
                fields.append("updated_by")
                values["updated_by"] = None

            col_sql = ", ".join(fields)
            placeholders = ", ".join(f":{f}" for f in fields)
            conn.execute(text(f"INSERT INTO llm_configurations ({col_sql}) VALUES ({placeholders})"), values)
            conn.commit()
            logger.info("已插入默认 llm_configurations (Ollama)")

    if insp.has_table("ai_gateways"):
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM ai_gateways")).scalar_one()
            if n > 0:
                logger.info("ai_gateways 已有数据，跳过")
            else:
                gid = str(uuid.uuid4())
                conn.execute(
                    text(
                        """
                        INSERT INTO ai_gateways (
                            id, name, gateway_type, tenant_id, status, configuration,
                            api_key_hash, api_secret_hash
                        ) VALUES (
                            :id, :name, 'openclaw', :tenant_id, 'inactive', CAST(:cfg AS jsonb),
                            'bootstrap-placeholder', 'bootstrap-placeholder'
                        )
                        """
                    ),
                    {
                        "id": gid,
                        "name": "Default Gateway (seed)",
                        "tenant_id": "default_tenant",
                        "cfg": json.dumps({"note": "请在管理后台填写真实密钥并启用"}),
                    },
                )
                conn.commit()
                logger.info("已插入占位 ai_gateways 行 id=%s", gid)

        if insp.has_table("ai_skills"):
            with engine.connect() as conn:
                n2 = conn.execute(text("SELECT COUNT(*) FROM ai_skills")).scalar_one()
                if n2 > 0:
                    logger.info("ai_skills 已有数据，跳过")
                else:
                    gw = conn.execute(text("SELECT id FROM ai_gateways LIMIT 1")).scalar_one_or_none()
                    if gw:
                        sid = str(uuid.uuid4())
                        conn.execute(
                            text(
                                """
                                INSERT INTO ai_skills (
                                    id, gateway_id, name, version, code_path, configuration,
                                    dependencies, status
                                ) VALUES (
                                    :id, :gw, :name, '0.1.0', '/app/skills/placeholder',
                                    CAST(:cfg AS jsonb), '[]'::jsonb, 'pending'
                                )
                                """
                            ),
                            {
                                "id": sid,
                                "gw": gw,
                                "name": "demo-skill",
                                "cfg": json.dumps({"description": "占位技能，可在后台替换为真实技能包"}),
                            },
                        )
                        conn.commit()
                        logger.info("已插入占位 ai_skills 行 id=%s", sid)


def main() -> int:
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    logger.info("等待数据库 %s:%s …", host, port)
    _wait_tcp(host, port)

    run_migrations()
    seed_users()
    try:
        seed_llm_and_ai()
    except Exception as e:
        logger.warning("LLM/AI 种子失败（可忽略后于后台配置）: %s", e)

    logger.info("bootstrap_docker 完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
