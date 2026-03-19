#!/usr/bin/env python3
"""
Setup 3 LLM providers with priority-based failover.

Priority 1: Baidu Cloud (ERNIE)
Priority 2: Ollama qwen2.5:7b (local GPU)
Priority 3: DeepSeek Cloud

Usage (inside app container):
    python scripts/setup_llm_providers.py
    python scripts/setup_llm_providers.py --status   # show current config
"""

import os
import sys
import argparse

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import select
from src.database.connection import db_manager
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.ai.encryption_service import get_encryption_service


# ---------------------------------------------------------------------------
# Provider definitions — API keys read from env vars, never hardcoded
# ---------------------------------------------------------------------------
PROVIDERS = [
    {
        "name": "百度千帆 ERNIE",
        "provider": "openai",
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "model_name": "ernie-4.0-8k",
        "api_key_env": "BAIDU_API_KEY",
        "api_key_fallback": "PLACEHOLDER_CHANGE_ME",
        "priority": 1,
        "timeout": 30,
        "max_retries": 2,
    },
    {
        "name": "Ollama qwen2.5:7b",
        "provider": "ollama",
        "base_url": "http://ollama:11434/v1",
        "model_name": "qwen2.5:7b",
        "api_key_env": None,
        "api_key_fallback": "ollama",
        "priority": 2,
        "timeout": 60,
        "max_retries": 1,
    },
    {
        "name": "DeepSeek Cloud",
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "api_key_fallback": "PLACEHOLDER_CHANGE_ME",
        "priority": 3,
        "timeout": 30,
        "max_retries": 2,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_config(session, provider_def, encryption_service):
    """Get existing config by name or create new. Returns (config, created)."""
    result = session.execute(
        select(LLMConfiguration).where(
            LLMConfiguration.name == provider_def["name"],
            LLMConfiguration.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False

    api_key_raw = (
        os.environ.get(provider_def["api_key_env"], provider_def["api_key_fallback"])
        if provider_def["api_key_env"]
        else provider_def["api_key_fallback"]
    )
    api_key_encrypted = encryption_service.encrypt(api_key_raw)

    config = LLMConfiguration(
        name=provider_def["name"],
        provider=provider_def["provider"],
        default_method=provider_def["provider"],
        config_data={
            "provider": provider_def["provider"],
            "api_key_encrypted": api_key_encrypted,
            "base_url": provider_def["base_url"],
            "model_name": provider_def["model_name"],
        },
        is_active=True,
    )
    session.add(config)
    session.flush()
    return config, True


def bind_config_to_apps(session, config, apps, provider_def):
    """Bind config to all apps with given priority. Skip existing."""
    bound = 0
    for app in apps:
        exists = session.execute(
            select(LLMApplicationBinding).where(
                LLMApplicationBinding.application_id == app.id,
                LLMApplicationBinding.llm_config_id == config.id,
            )
        ).scalar_one_or_none()
        if exists:
            continue

        # Check if priority slot is taken for this app
        priority_taken = session.execute(
            select(LLMApplicationBinding).where(
                LLMApplicationBinding.application_id == app.id,
                LLMApplicationBinding.priority == provider_def["priority"],
            )
        ).scalar_one_or_none()
        if priority_taken:
            print(f"  ⚠ 优先级 {provider_def['priority']} 已被占用 ({app.name})，跳过")
            continue

        binding = LLMApplicationBinding(
            llm_config_id=config.id,
            application_id=app.id,
            priority=provider_def["priority"],
            max_retries=provider_def["max_retries"],
            timeout_seconds=provider_def["timeout"],
            is_active=True,
        )
        session.add(binding)
        bound += 1
    return bound


def deactivate_old_ollama(session):
    """Deactivate old qwen2.5:1.5b configs so 7b takes over."""
    result = session.execute(
        select(LLMConfiguration).where(
            LLMConfiguration.name.like("%1.5b%"),
            LLMConfiguration.is_active == True,
        )
    )
    old_configs = result.scalars().all()
    for cfg in old_configs:
        cfg.is_active = False
        print(f"  ⏹ 停用旧配置: {cfg.name}")
    return len(old_configs)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def show_status(session):
    """Display current LLM config and bindings."""
    print("\n" + "=" * 60)
    print("当前 LLM 配置状态")
    print("=" * 60)

    configs = session.execute(
        select(LLMConfiguration).where(LLMConfiguration.is_active == True)
    ).scalars().all()

    if not configs:
        print("  (无活跃配置)")
        return

    for cfg in configs:
        model = (cfg.config_data or {}).get("model_name", "?")
        print(f"\n  📦 {cfg.name}  |  provider={cfg.provider}  model={model}")

        bindings = session.execute(
            select(LLMApplicationBinding)
            .where(
                LLMApplicationBinding.llm_config_id == cfg.id,
                LLMApplicationBinding.is_active == True,
            )
            .order_by(LLMApplicationBinding.priority)
        ).scalars().all()

        if bindings:
            for b in bindings:
                app = session.get(LLMApplication, b.application_id)
                app_name = app.name if app else str(b.application_id)
                print(f"     └─ 优先级 {b.priority}  →  {app_name}  (timeout={b.timeout_seconds}s)")
        else:
            print("     └─ (未绑定应用)")

    print()


def run_setup(session):
    """Create configs and bind to all apps."""
    encryption_service = get_encryption_service()

    # Load all active apps
    apps = session.execute(
        select(LLMApplication).where(LLMApplication.is_active == True)
    ).scalars().all()

    if not apps:
        print("❌ 没有找到活跃的 LLM 应用，请先运行 init_ollama_bindings.py")
        return 1

    print(f"📋 找到 {len(apps)} 个活跃应用")

    # Deactivate old 1.5b
    deactivated = deactivate_old_ollama(session)
    if deactivated:
        print(f"  停用了 {deactivated} 个旧 1.5b 配置")

    # Create/get each provider and bind
    for pdef in PROVIDERS:
        config, created = get_or_create_config(session, pdef, encryption_service)
        status = "✅ 新建" if created else "♻️ 已存在"
        print(f"\n{status}: {pdef['name']}  (优先级 {pdef['priority']})")

        bound = bind_config_to_apps(session, config, apps, pdef)
        if bound:
            print(f"  绑定了 {bound} 个应用")

    session.commit()
    print("\n✅ LLM 配置完成")
    show_status(session)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Setup LLM providers")
    parser.add_argument("--status", action="store_true", help="Show current config")
    args = parser.parse_args()

    db_manager.initialize()
    session = db_manager.get_session()

    try:
        if args.status:
            show_status(session)
        else:
            return run_setup(session)
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
