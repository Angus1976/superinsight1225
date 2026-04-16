#!/usr/bin/env python3
"""
插入或更新一条千帆 OpenAI 兼容 LLM 配置（密钥仅来自环境变量，不落盘）。

环境变量:
  QIANFAN_KEY      必填，控制台完整 API Key（bce-v3/ALTAK-...）
  LLM_ROW_NAME     可选，llm_configurations.name，默认 APIKey-20260318102854
  QIANFAN_MODEL    可选，默认 ernie-3.5-8k

在 app 容器内执行（需 DATABASE_URL / LLM_ENCRYPTION_KEY 与后端一致）:
  export QIANFAN_KEY='...'
  export PYTHONPATH=/app
  cd /app && python3 scripts/insert_qianfan_llm_row_from_env.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from src.database.connection import db_manager
from src.models.llm_configuration import LLMConfiguration
from src.ai.encryption_service import get_encryption_service

PROVIDER = "baidu_qianfan"
BASE = "https://qianfan.baidubce.com/v2"


def main() -> int:
    key = os.environ.get("QIANFAN_KEY", "").strip()
    if not key:
        print("Set QIANFAN_KEY", file=sys.stderr)
        return 1

    name = os.environ.get("LLM_ROW_NAME", "APIKey-20260318102854").strip()
    model = os.environ.get("QIANFAN_MODEL", "ernie-3.5-8k").strip()

    db_manager.initialize()
    enc = get_encryption_service()
    blob = enc.encrypt(key)
    cfg = {
        "provider": PROVIDER,
        "api_key_encrypted": blob,
        "base_url": BASE,
        "model_name": model,
        "doc_ref": "https://cloud.baidu.com/doc/qianfan-api/s/3m9b5lqft",
    }

    with db_manager.get_session() as session:
        ex = session.execute(
            select(LLMConfiguration).where(LLMConfiguration.name == name)
        ).scalar_one_or_none()
        if ex:
            ex.provider = PROVIDER
            ex.default_method = PROVIDER
            ex.config_data = cfg
            ex.is_active = True
            print("updated", name, str(ex.id))
        else:
            row = LLMConfiguration(
                name=name,
                provider=PROVIDER,
                default_method=PROVIDER,
                config_data=cfg,
                tenant_id=None,
                is_active=True,
            )
            session.add(row)
            session.flush()
            print("inserted", name, str(row.id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
