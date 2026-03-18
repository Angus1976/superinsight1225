#!/usr/bin/env python3
"""
Direct SQL migration: Create ai_workflows table.

Bypasses Alembic's migration runner to avoid multi-head conflicts
(duplicate revisions at 009, 011, 033, 036). After creating the table,
stamps the Alembic version so future migrations stay in sync.

Usage:
    python scripts/migrate_add_ai_workflows.py          # run migration
    python scripts/migrate_add_ai_workflows.py --check   # dry-run check
    python scripts/migrate_add_ai_workflows.py --down     # rollback
"""

import os
import sys
import logging
import argparse

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text, inspect
from src.config.settings import settings

logger = logging.getLogger(__name__)

REVISION_ID = "037_add_ai_workflows"
TABLE_NAME = "ai_workflows"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ai_workflows (
    id              VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL UNIQUE,
    description     TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'enabled',
    is_preset       BOOLEAN NOT NULL DEFAULT FALSE,
    skill_ids       JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_source_auth JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_modes    JSONB NOT NULL DEFAULT '[]'::jsonb,
    visible_roles   JSONB NOT NULL DEFAULT '[]'::jsonb,
    preset_prompt   TEXT,
    name_en         VARCHAR(255),
    description_en  TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by      VARCHAR(100)
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_workflow_status ON ai_workflows (status);",
    "CREATE INDEX IF NOT EXISTS idx_workflow_name ON ai_workflows (name);",
]

DROP_TABLE_SQL = """
DROP INDEX IF EXISTS idx_workflow_name;
DROP INDEX IF EXISTS idx_workflow_status;
DROP TABLE IF EXISTS ai_workflows;
"""


def table_exists(engine) -> bool:
    """Check whether ai_workflows table already exists."""
    inspector = inspect(engine)
    return TABLE_NAME in inspector.get_table_names()


def stamp_alembic(engine, revision: str) -> None:
    """Insert or update the Alembic version stamp."""
    with engine.begin() as conn:
        # Ensure alembic_version table exists
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "  version_num VARCHAR(32) NOT NULL,"
            "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        ))
        # Remove old stamp if present, then insert new one
        conn.execute(text(
            "DELETE FROM alembic_version WHERE version_num = :rev"
        ), {"rev": revision})
        conn.execute(text(
            "INSERT INTO alembic_version (version_num) VALUES (:rev)"
        ), {"rev": revision})
    logger.info("Stamped Alembic version: %s", revision)


def unstamp_alembic(engine, revision: str) -> None:
    """Remove the Alembic version stamp for this migration."""
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM alembic_version WHERE version_num = :rev"
        ), {"rev": revision})
    logger.info("Removed Alembic stamp: %s", revision)


def run_upgrade(engine) -> None:
    """Create ai_workflows table and indexes, then stamp Alembic."""
    if table_exists(engine):
        logger.info("Table '%s' already exists — skipping creation.", TABLE_NAME)
        stamp_alembic(engine, REVISION_ID)
        return

    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        for idx_sql in CREATE_INDEXES_SQL:
            conn.execute(text(idx_sql))

    logger.info("Created table '%s' with indexes.", TABLE_NAME)
    stamp_alembic(engine, REVISION_ID)


def run_downgrade(engine) -> None:
    """Drop ai_workflows table and remove Alembic stamp."""
    with engine.begin() as conn:
        conn.execute(text(DROP_TABLE_SQL))

    logger.info("Dropped table '%s' and indexes.", TABLE_NAME)
    unstamp_alembic(engine, REVISION_ID)


def run_check(engine) -> None:
    """Dry-run: report current state without making changes."""
    exists = table_exists(engine)
    status = "EXISTS" if exists else "MISSING"
    print(f"Table '{TABLE_NAME}': {status}")

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT version_num FROM alembic_version WHERE version_num = :rev"
        ), {"rev": REVISION_ID})
        stamped = result.fetchone() is not None

    stamp_status = "STAMPED" if stamped else "NOT STAMPED"
    print(f"Alembic revision '{REVISION_ID}': {stamp_status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Direct SQL migration for ai_workflows table"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Dry-run: check current state without changes",
    )
    parser.add_argument(
        "--down", action="store_true",
        help="Rollback: drop table and remove Alembic stamp",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    db_url = settings.database.database_url
    logger.info("Connecting to: %s", db_url.split("@")[-1] if "@" in db_url else db_url)
    engine = create_engine(db_url)

    if args.check:
        run_check(engine)
    elif args.down:
        run_downgrade(engine)
        print(f"✅ Rollback complete — table '{TABLE_NAME}' dropped.")
    else:
        run_upgrade(engine)
        print(f"✅ Migration complete — table '{TABLE_NAME}' ready.")

        # After table creation, seed default and preset workflows.
        # Requires a SQLAlchemy session for WorkflowService.
        try:
            from sqlalchemy.orm import Session as SASession
            with SASession(engine) as session:
                from src.ai.workflow_service import WorkflowService
                svc = WorkflowService(session)
                defaults = svc.generate_default_workflows()
                presets = svc.create_preset_workflows()
                print(
                    f"  → Created {len(defaults)} default workflow(s), "
                    f"{len(presets)} preset workflow(s)."
                )
        except Exception as exc:
            logger.warning("Seeding workflows failed (run manually): %s", exc)
            print(f"⚠️  Workflow seeding skipped: {exc}")

    engine.dispose()


if __name__ == "__main__":
    main()
