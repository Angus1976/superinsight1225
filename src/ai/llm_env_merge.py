"""
Merge environment-variable fallbacks into LLMConfig after database load.

Priority: explicit values in DB (llm_configurations.config_data) win; missing or
empty optional secrets/URLs are filled from standard env vars (OLLAMA_BASE_URL,
OPENAI_API_KEY, etc.).
"""

from __future__ import annotations

import os

from src.ai.llm_schemas import LLMConfig


def merge_llm_config_with_env_defaults(config: LLMConfig) -> LLMConfig:
    """Apply env fallbacks for fields not set (or empty) in ``config``."""
    d = config.model_dump()

    lc = dict(d.get("local_config") or {})
    if not (lc.get("ollama_url") or "").strip():
        lc["ollama_url"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if not (lc.get("default_model") or "").strip():
        lc["default_model"] = os.getenv("OLLAMA_MODEL", lc.get("default_model") or "qwen2.5vl:7b")
    d["local_config"] = lc

    cc = dict(d.get("cloud_config") or {})
    if not (cc.get("openai_api_key") or "").strip():
        k = os.getenv("OPENAI_API_KEY")
        if k:
            cc["openai_api_key"] = k
    if not (cc.get("openai_base_url") or "").strip():
        eb = os.getenv("OPENAI_BASE_URL")
        if eb:
            cc["openai_base_url"] = eb
    if not (cc.get("openai_model") or "").strip():
        em = os.getenv("OPENAI_MODEL")
        if em:
            cc["openai_model"] = em
    d["cloud_config"] = cc

    china = dict(d.get("china_config") or {})
    if not (china.get("qwen_api_key") or "").strip():
        qk = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if qk:
            china["qwen_api_key"] = qk
    d["china_config"] = china

    return LLMConfig(**d)
