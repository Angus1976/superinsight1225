#!/usr/bin/env python3
"""
在数据库中写入 DeepSeek OpenAI 兼容配置（多模型条目，便于按场景绑定）。

官方 API（OpenAI 兼容）:
  https://api-docs.deepseek.com/

约定:
  - base_url: https://api.deepseek.com/v1
  - 请求: POST {base_url}/chat/completions
  - Header: Authorization: Bearer <API Key>

必填环境变量:
  DATABASE_URL
  LLM_ENCRYPTION_KEY（与后端一致）
  DEEPSEEK_API_KEY（控制台 API Key，勿提交 Git）

可选:
  DEEPSEEK_TENANT_ID  → 写入 llm_configurations.tenant_id（默认不写=全局）

用法:
  DATABASE_URL=... LLM_ENCRYPTION_KEY=... DEEPSEEK_API_KEY='sk-...' \\
    python3 scripts/seed_deepseek_llm_configs.py

  python3 scripts/seed_deepseek_llm_configs.py --bind   # 为部分应用建 priority=1 绑定
  python3 scripts/seed_deepseek_llm_configs.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from uuid import uuid4

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import select

from src.database.connection import db_manager
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.ai.encryption_service import get_encryption_service

BASE_URL = "https://api.deepseek.com/v1"
PROVIDER = "deepseek"
DOC_REF = "https://api-docs.deepseek.com/"

# (显示名, model 字段, 说明)
PRESETS: list[tuple[str, str, str]] = [
    ("DeepSeek-通用对话", "deepseek-chat", "通用对话与日常任务"),
    ("DeepSeek-代码助手", "deepseek-coder", "代码、SQL、脚本与技术问答"),
    ("DeepSeek-推理-R1", "deepseek-reasoner", "复杂推理与深度分析（R1）"),
]

# --bind：每条配置对应一个业务应用（priority=1），其余应用在管理台自行绑定
BIND_PLAN: list[tuple[str, str]] = [
    ("DeepSeek-通用对话", "structuring"),
    ("DeepSeek-代码助手", "text_to_sql"),
    ("DeepSeek-推理-R1", "semantic_analysis"),
]


def _build_config_data(api_key_encrypted: str, model_name: str) -> dict:
    return {
        "provider": PROVIDER,
        "api_key_encrypted": api_key_encrypted,
        "base_url": BASE_URL,
        "model_name": model_name,
        "doc_ref": DOC_REF,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DeepSeek LLM rows (DB)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--bind",
        action="store_true",
        help="Create llm_application_bindings (priority=1) per BIND_PLAN",
    )
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key and not args.dry_run:
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1

    if args.dry_run:
        print("将写入 base_url=", BASE_URL)
        for name, model, desc in PRESETS:
            print(f"  - {name}  model={model}  ({desc})")
        if args.bind:
            for cfg_name, app_code in BIND_PLAN:
                print(f"  - 绑定: {cfg_name} -> 应用 {app_code} (priority=1)")
        print("\n设置 DATABASE_URL、LLM_ENCRYPTION_KEY、DEEPSEEK_API_KEY 后去掉 --dry-run")
        return 0

    tenant_raw = os.environ.get("DEEPSEEK_TENANT_ID", "").strip()
    tenant_id = tenant_raw if tenant_raw else None

    db_manager.initialize()
    enc = get_encryption_service()

    try:
        with db_manager.get_session() as session:
            created_cfg = 0
            skipped = 0
            name_to_config: dict[str, LLMConfiguration] = {}

            blob = enc.encrypt(api_key)

            for name, model_name, description in PRESETS:
                exists = session.execute(
                    select(LLMConfiguration).where(
                        LLMConfiguration.name == name,
                        LLMConfiguration.is_active == True,  # noqa: E712
                    )
                ).scalar_one_or_none()
                if exists:
                    print(f"跳过（已存在）: {name}")
                    skipped += 1
                    name_to_config[name] = exists
                    continue

                cfg_data = _build_config_data(blob, model_name)

                row = LLMConfiguration(
                    name=name,
                    description=description,
                    provider=PROVIDER,
                    default_method=PROVIDER,
                    config_data=cfg_data,
                    tenant_id=tenant_id,
                    is_active=True,
                )
                session.add(row)
                session.flush()
                name_to_config[name] = row
                created_cfg += 1
                print(f"已创建 LLM 配置: {name}  model={model_name}")

            if args.bind:
                bound = 0
                for cfg_name, app_code in BIND_PLAN:
                    cfg = name_to_config.get(cfg_name)
                    if not cfg:
                        print(f"跳过绑定（未找到配置）: {cfg_name}", file=sys.stderr)
                        continue
                    app = session.execute(
                        select(LLMApplication).where(LLMApplication.code == app_code)
                    ).scalar_one_or_none()
                    if not app:
                        print(f"跳过绑定（未找到应用）: {app_code}", file=sys.stderr)
                        continue
                    dup = session.execute(
                        select(LLMApplicationBinding).where(
                            LLMApplicationBinding.application_id == app.id,
                            LLMApplicationBinding.priority == 1,
                        )
                    ).scalar_one_or_none()
                    if dup:
                        print(
                            f"应用 {app_code} 已有 priority=1 绑定，跳过 "
                            f"(id={dup.id})"
                        )
                        continue
                    b = LLMApplicationBinding(
                        id=uuid4(),
                        llm_config_id=cfg.id,
                        application_id=app.id,
                        priority=1,
                        max_retries=3,
                        timeout_seconds=120 if "推理" in cfg_name else 60,
                        is_active=True,
                    )
                    session.add(b)
                    bound += 1
                    print(f"已绑定: {cfg_name} -> {app_code} (priority=1)")
                print(f"新建绑定 {bound} 条")

            print(f"\n完成: 新建配置 {created_cfg} 条，跳过已存在 {skipped} 条。")
        return 0
    except Exception as e:
        print(f"失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
