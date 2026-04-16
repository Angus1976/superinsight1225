#!/usr/bin/env python3
"""
将本地 Ollama 的 qwen2.5:7b 与 qwen2.5:1.5b 写入 llm_configurations 并绑定到全部活跃应用。

在 app 容器内执行（与数据库一致）::
    docker compose --profile docker-backend exec app python scripts/seed_local_ollama_qwen_configs.py

本机直连 Ollama（非 Docker 网络）时可设::
    export OLLAMA_BASE_URL=http://host.docker.internal:11434
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database.connection import db_manager
from src.database.seed_ollama_llm import seed_ollama_qwen_pair


def main() -> int:
    db_manager.initialize()
    with db_manager.get_session() as session:
        seed_ollama_qwen_pair(session)
    print(
        "OK: Ollama qwen2.5:7b + qwen2.5:1.5b 已写入；已注册 LLM 应用「openclaw」并对全部活跃应用（含 OpenClaw）完成绑定。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
