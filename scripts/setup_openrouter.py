#!/usr/bin/env python3
"""
Setup OpenRouter LLM configurations in database.

Usage:
    OPENROUTER_API_KEY=sk-or-v1-xxx python scripts/setup_openrouter.py

Adds OpenAI/Gemini/Grok models via OpenRouter and binds them to ai_assistant application.
"""
import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# OpenRouter models to configure
OPENROUTER_MODELS = [
    {
        "id": "0a000001-0000-4000-a000-000000000001",
        "name": "OpenRouter GPT-4o",
        "model_name": "openai/gpt-4o",
        "description": "OpenAI GPT-4o via OpenRouter",
    },
    {
        "id": "0a000001-0000-4000-a000-000000000002",
        "name": "OpenRouter GPT-4o-mini",
        "model_name": "openai/gpt-4o-mini",
        "description": "OpenAI GPT-4o-mini via OpenRouter (cost-effective)",
    },
    {
        "id": "0a000001-0000-4000-a000-000000000003",
        "name": "OpenRouter Gemini 2.5 Flash",
        "model_name": "google/gemini-2.5-flash-preview",
        "description": "Google Gemini 2.5 Flash via OpenRouter",
    },
    {
        "id": "0a000001-0000-4000-a000-000000000004",
        "name": "OpenRouter Gemini 2.5 Pro",
        "model_name": "google/gemini-2.5-pro-preview",
        "description": "Google Gemini 2.5 Pro via OpenRouter",
    },
    {
        "id": "0a000001-0000-4000-a000-000000000005",
        "name": "OpenRouter Grok 3",
        "model_name": "x-ai/grok-3-beta",
        "description": "xAI Grok 3 via OpenRouter",
    },
    {
        "id": "0a000001-0000-4000-a000-000000000006",
        "name": "OpenRouter Claude 4 Sonnet",
        "model_name": "anthropic/claude-sonnet-4",
        "description": "Anthropic Claude 4 Sonnet via OpenRouter",
    },
]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    # Encrypt the API key
    from src.ai.encryption_service import get_encryption_service
    enc = get_encryption_service()
    encrypted_key = enc.encrypt(api_key)
    logger.info("✅ API key encrypted")

    # Connect to database
    from sqlalchemy import create_engine, text
    db_url = os.getenv("DATABASE_URL", "postgresql://superinsight:superinsight@localhost:5432/superinsight")
    engine = create_engine(db_url)

    with engine.begin() as conn:
        # Insert LLM configurations (idempotent)
        for model in OPENROUTER_MODELS:
            config_data = json.dumps({
                "base_url": OPENROUTER_BASE_URL,
                "provider": "openai",
                "model_name": model["model_name"],
                "api_key_encrypted": encrypted_key,
            })

            result = conn.execute(
                text("SELECT id FROM llm_configurations WHERE id = :id"),
                {"id": model["id"]},
            )
            if result.fetchone():
                # Update existing
                conn.execute(
                    text("""
                        UPDATE llm_configurations
                        SET config_data = :config_data, name = :name,
                            description = :desc, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": model["id"], "config_data": config_data,
                     "name": model["name"], "desc": model["description"]},
                )
                logger.info(f"  ↻ Updated: {model['name']}")
            else:
                conn.execute(
                    text("""
                        INSERT INTO llm_configurations
                            (id, provider, default_method, config_data, name,
                             description, is_active, is_default)
                        VALUES (:id, 'openai', 'cloud_openai', :config_data,
                                :name, :desc, true, false)
                    """),
                    {"id": model["id"], "config_data": config_data,
                     "name": model["name"], "desc": model["description"]},
                )
                logger.info(f"  ✅ Created: {model['name']}")

        # Bind GPT-4o-mini to ai_assistant as a fallback (priority after existing)
        ai_app = conn.execute(
            text("SELECT id FROM llm_applications WHERE code = 'ai_assistant'")
        ).fetchone()

        if ai_app:
            app_id = ai_app[0]
            # Get current max priority for ai_assistant
            max_p = conn.execute(
                text("""
                    SELECT COALESCE(MAX(priority), 0)
                    FROM llm_application_bindings
                    WHERE application_id = :app_id AND is_active = true
                """),
                {"app_id": app_id},
            ).scalar()

            # Bind GPT-4o-mini as next priority
            gpt4o_mini_id = "0a000001-0000-4000-a000-000000000002"
            existing = conn.execute(
                text("""
                    SELECT id FROM llm_application_bindings
                    WHERE application_id = :app_id AND llm_config_id = :cfg_id
                """),
                {"app_id": app_id, "cfg_id": gpt4o_mini_id},
            ).fetchone()

            if not existing:
                new_priority = max_p + 1
                conn.execute(
                    text("""
                        INSERT INTO llm_application_bindings
                            (application_id, llm_config_id, priority,
                             max_retries, timeout_seconds, is_active)
                        VALUES (:app_id, :cfg_id, :priority, 3, 60, true)
                    """),
                    {"app_id": app_id, "cfg_id": gpt4o_mini_id,
                     "priority": new_priority},
                )
                logger.info(f"  ✅ Bound GPT-4o-mini to ai_assistant (priority={new_priority})")
            else:
                logger.info(f"  ↻ GPT-4o-mini already bound to ai_assistant")

    logger.info("\n🎉 OpenRouter configuration complete")
    logger.info("Models available in LLM management UI for binding to applications")


if __name__ == "__main__":
    main()
