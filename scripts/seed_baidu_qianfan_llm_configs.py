#!/usr/bin/env python3
"""
在数据库中写入百度千帆（Qianfan）V2 OpenAI 兼容配置。

官方文档（通用说明）:
  https://cloud.baidu.com/doc/qianfan-api/s/3m9b5lqft

认证与调用示例（Bearer + /v2/chat/completions）:
  https://cloud.baidu.com/doc/qianfan-api/s/ym9chdsy5

约定（与 curl 示例一致）:
  - base_url: https://qianfan.baidubce.com/v2
  - 实际请求: POST {base_url}/chat/completions
  - Header: Authorization: Bearer <API Key>
  - 可选 Header: appid（V2 应用 ID，见控制台「应用接入」）

必填环境变量:
  DATABASE_URL
  LLM_ENCRYPTION_KEY（与后端一致）
  BAIDU_QIANFAN_API_KEY（控制台完整 Key，勿提交 Git）

可选:
  QIANFAN_APP_ID        → 写入 config_data.qianfan_appid（发送 appid 头）
  QIANFAN_TENANT_ID     → 写入 llm_configurations.tenant_id（默认不写=全局）

用法:
  DATABASE_URL=... LLM_ENCRYPTION_KEY=... BAIDU_QIANFAN_API_KEY='bce-v3/...' \\
    python3 scripts/seed_baidu_qianfan_llm_configs.py

  # 同时为各应用创建 priority=1 的绑定（见下方 BIND_PLAN）
  ... python3 scripts/seed_baidu_qianfan_llm_configs.py --bind

  python3 scripts/seed_baidu_qianfan_llm_configs.py --dry-run
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

# 与文档示例一致：base 为 /v2，代码里拼接 /chat/completions
BASE_URL = "https://qianfan.baidubce.com/v2"
PROVIDER = "baidu_qianfan"

# (配置显示名, 模型 model 字段) — 以千帆控制台实际开通的模型名为准；文档示例为 ernie-3.5-8k
PRESETS: list[tuple[str, str]] = [
    ("千帆-通用对话", "ernie-4.0-8k"),
    ("千帆-长文本", "ernie-speed-128k"),
    ("千帆-高速低成本", "ernie-lite-8k"),
    ("千帆-Turbo", "ernie-4.0-turbo-8k"),
    ("千帆-语义分析", "ernie-3.5-8k"),
    ("千帆-知识图谱", "ernie-4.0-8k"),
]

# --bind 时：每条配置绑定到一个业务应用（各应用 priority=1）
BIND_PLAN: list[tuple[str, str]] = [
    ("千帆-通用对话", "structuring"),
    ("千帆-长文本", "rag_agent"),
    ("千帆-高速低成本", "text_to_sql"),
    ("千帆-Turbo", "ai_assistant"),
    ("千帆-语义分析", "semantic_analysis"),
    ("千帆-知识图谱", "knowledge_graph"),
]


def _build_config_data(api_key_encrypted: str) -> dict:
    app_id = os.environ.get("QIANFAN_APP_ID", "").strip()
    data = {
        "provider": PROVIDER,
        "api_key_encrypted": api_key_encrypted,
        "base_url": BASE_URL,
        "model_name": "",  # set per row
        "doc_ref": "https://cloud.baidu.com/doc/qianfan-api/s/3m9b5lqft",
        "auth_ref": "https://cloud.baidu.com/doc/qianfan-api/s/ym9chdsy5",
    }
    if app_id:
        data["qianfan_appid"] = app_id
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Baidu Qianfan LLM rows (DB)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--bind",
        action="store_true",
        help="Create llm_application_bindings (priority=1) per BIND_PLAN",
    )
    args = parser.parse_args()

    api_key = os.environ.get("BAIDU_QIANFAN_API_KEY", "").strip()
    if not api_key and not args.dry_run:
        print("BAIDU_QIANFAN_API_KEY is not set", file=sys.stderr)
        return 1

    if args.dry_run:
        print("将写入 base_url=", BASE_URL, "（请求路径 /v2/chat/completions）")
        for name, model in PRESETS:
            print(f"  - {name}  model={model}")
        if os.environ.get("QIANFAN_APP_ID"):
            print("  - 将附带 qianfan_appid（appid 请求头）")
        if args.bind:
            for cfg_name, app_code in BIND_PLAN:
                print(f"  - 绑定: {cfg_name} -> 应用 {app_code} (priority=1)")
        print("\n设置 DATABASE_URL、LLM_ENCRYPTION_KEY、BAIDU_QIANFAN_API_KEY 后去掉 --dry-run")
        return 0

    tenant_raw = os.environ.get("QIANFAN_TENANT_ID", "").strip()
    tenant_id = tenant_raw if tenant_raw else None

    db_manager.initialize()
    enc = get_encryption_service()

    try:
        with db_manager.get_session() as session:
            created_cfg = 0
            skipped = 0
            name_to_config: dict[str, LLMConfiguration] = {}

            blob = enc.encrypt(api_key)

            for name, model_name in PRESETS:
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

                cfg_data = _build_config_data(blob)
                cfg_data["model_name"] = model_name

                row = LLMConfiguration(
                    name=name,
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
                        timeout_seconds=60,
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
