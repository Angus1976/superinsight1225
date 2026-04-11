"""Ensure llm_configurations.provider and llm_applications / bindings exist (main branch)

Revision ID: 038_llm_apps_provider
Revises: 037_add_ai_workflows
Create Date: 2026-04-09

009_llm_app_binding 挂在 ai_annotation 分支，merge 到 037 的主线不会执行；此处幂等补齐 ORM 所需表与列。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "038_llm_apps_provider"
down_revision: Union[str, Sequence[str], None] = "037_add_ai_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    def _has(t: str) -> bool:
        return inspect(bind).has_table(t)

    def _cols(table: str) -> set:
        if not _has(table):
            return set()
        return {c["name"] for c in inspect(bind).get_columns(table)}

    # --- llm_configurations.provider ---
    if _has("llm_configurations"):
        cols = _cols("llm_configurations")
        if "provider" not in cols:
            op.add_column(
                "llm_configurations",
                sa.Column("provider", sa.String(50), nullable=True),
            )
            op.execute(
                text(
                    """
                    UPDATE llm_configurations SET provider = CASE
                      WHEN default_method ILIKE '%ollama%' THEN 'ollama'
                      WHEN default_method ILIKE '%openai%' THEN 'openai'
                      WHEN default_method ILIKE '%azure%' THEN 'azure'
                      ELSE COALESCE(NULLIF(config_data->>'provider',''), 'ollama')
                    END
                    WHERE provider IS NULL
                    """
                )
            )
            op.execute(
                text(
                    "UPDATE llm_configurations SET provider = 'ollama' WHERE provider IS NULL"
                )
            )
            op.alter_column("llm_configurations", "provider", nullable=False)

    # --- llm_applications + llm_application_bindings ---
    if not _has("llm_applications"):
        op.create_table(
            "llm_applications",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("llm_usage_pattern", sa.Text(), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "idx_llm_applications_code", "llm_applications", ["code"], unique=True
        )
        op.execute(
            text(
                """
            INSERT INTO llm_applications (code, name, description, llm_usage_pattern) VALUES
            ('structuring', 'Data Structuring', 'Schema inference and entity extraction from unstructured data', 'High-frequency, low-latency requests for real-time data processing'),
            ('knowledge_graph', 'Knowledge Graph', 'Knowledge graph construction and entity/relation extraction', 'Medium-frequency, high-quality extraction for graph building'),
            ('ai_assistant', 'AI Assistant', 'Intelligent assistant services for user interactions', 'High-frequency, conversational interactions with context awareness'),
            ('semantic_analysis', 'Semantic Analysis', 'Semantic analysis and text understanding services', 'Medium-frequency, analytical processing for deep understanding'),
            ('rag_agent', 'RAG Agent', 'Retrieval-augmented generation for context-aware responses', 'High-frequency, context-aware generation with retrieval'),
            ('text_to_sql', 'Text to SQL', 'Natural language to SQL query conversion', 'Medium-frequency, precise translation for database queries')
            """
            )
        )

    if not _has("llm_application_bindings"):
        op.create_table(
            "llm_application_bindings",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("llm_config_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column(
                "max_retries",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("3"),
            ),
            sa.Column(
                "timeout_seconds",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("30"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["llm_config_id"],
                ["llm_configurations.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["application_id"],
                ["llm_applications.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "application_id", "priority", name="uq_app_priority"
            ),
            sa.CheckConstraint(
                "priority >= 1 AND priority <= 99", name="ck_priority_range"
            ),
            sa.CheckConstraint(
                "max_retries >= 0 AND max_retries <= 10", name="ck_max_retries_range"
            ),
            sa.CheckConstraint("timeout_seconds > 0", name="ck_timeout_positive"),
        )
        op.create_index(
            "idx_bindings_app_priority",
            "llm_application_bindings",
            ["application_id", "priority"],
        )
        op.create_index(
            "idx_bindings_active", "llm_application_bindings", ["is_active"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("llm_application_bindings"):
        op.drop_index("idx_bindings_active", table_name="llm_application_bindings")
        op.drop_index(
            "idx_bindings_app_priority", table_name="llm_application_bindings"
        )
        op.drop_table("llm_application_bindings")
    if inspect(bind).has_table("llm_applications"):
        op.drop_index("idx_llm_applications_code", table_name="llm_applications")
        op.drop_table("llm_applications")
    if inspect(bind).has_table("llm_configurations"):
        cols = {c["name"] for c in inspect(bind).get_columns("llm_configurations")}
        if "provider" in cols:
            op.drop_column("llm_configurations", "provider")
