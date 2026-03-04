#!/usr/bin/env python3
"""
Setup Ollama LLM for all AI applications.

This script:
1. Creates an Ollama LLM configuration
2. Ensures all 6 AI applications are registered
3. Binds Ollama to all applications with priority 1
4. Tests the connection

Usage:
    python scripts/setup_ollama_for_all_apps.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.connection import db_manager
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
import httpx


# Define all AI applications in the system
AI_APPLICATIONS = [
    {
        "code": "structuring",
        "name": "数据结构化",
        "description": "模式推断和实体提取",
        "llm_usage_pattern": "用于非结构化数据的结构化处理，包括模式推断、实体提取等"
    },
    {
        "code": "knowledge_graph",
        "name": "知识图谱",
        "description": "知识图谱构建",
        "llm_usage_pattern": "用于从文本中提取实体和关系，构建知识图谱"
    },
    {
        "code": "ai_assistant",
        "name": "AI 助手",
        "description": "智能助手服务",
        "llm_usage_pattern": "用于对话式交互，回答用户问题，提供智能建议"
    },
    {
        "code": "semantic_analysis",
        "name": "语义分析",
        "description": "语义分析服务",
        "llm_usage_pattern": "用于文本语义理解、情感分析、主题提取等"
    },
    {
        "code": "rag_agent",
        "name": "RAG 智能体",
        "description": "检索增强生成",
        "llm_usage_pattern": "用于基于知识库的问答，结合检索和生成"
    },
    {
        "code": "text_to_sql",
        "name": "文本转 SQL",
        "description": "自然语言转 SQL 查询",
        "llm_usage_pattern": "用于将自然语言问题转换为 SQL 查询语句"
    }
]


async def test_ollama_connection(base_url: str = "http://localhost:11434") -> tuple[bool, list]:
    """Test if Ollama is accessible and get available models."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                print(f"✅ Ollama 可访问: {base_url}")
                print(f"   可用模型: {model_names}")
                return True, model_names
            else:
                print(f"❌ Ollama 返回状态码 {response.status_code}")
                return False, []
    except Exception as e:
        print(f"❌ 无法连接到 Ollama ({base_url}): {e}")
        return False, []


async def ensure_applications_exist(session: Session) -> dict[str, LLMApplication]:
    """Ensure all AI applications are registered in database."""
    print("\n📋 检查并创建 AI 应用...")
    
    apps_dict = {}
    for app_def in AI_APPLICATIONS:
        # Check if application exists
        result = session.execute(
            select(LLMApplication).where(LLMApplication.code == app_def["code"])
        )
        app = result.scalar_one_or_none()
        
        if app:
            print(f"   ✓ 应用已存在: {app_def['name']} ({app_def['code']})")
        else:
            # Create application
            app = LLMApplication(
                code=app_def["code"],
                name=app_def["name"],
                description=app_def["description"],
                llm_usage_pattern=app_def["llm_usage_pattern"],
                is_active=True
            )
            session.add(app)
            session.flush()
            print(f"   ✓ 创建应用: {app_def['name']} ({app_def['code']})")
        
        apps_dict[app_def["code"]] = app
    
    session.commit()
    return apps_dict


async def get_or_create_ollama_config(
    session: Session,
    model_name: str = "qwen2.5:7b"
) -> LLMConfiguration:
    """Get existing Ollama config or create a new one."""
    print("\n🔧 配置 Ollama LLM...")
    
    # Check if Ollama config already exists
    result = session.execute(
        select(LLMConfiguration).where(
            LLMConfiguration.name.like("%Ollama%"),
            LLMConfiguration.is_active == True
        )
    )
    existing_config = result.scalars().first()
    
    if existing_config:
        print(f"   ✓ 找到现有配置: {existing_config.name}")
        return existing_config
    
    # Create new Ollama configuration
    config_data = {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "model_name": model_name,
        "api_key_encrypted": "",  # Ollama doesn't require API key
    }
    
    ollama_config = LLMConfiguration(
        name=f"Ollama {model_name}",
        default_method="local_ollama",
        config_data=config_data,
        is_active=True,
        tenant_id=None  # Global configuration
    )
    
    session.add(ollama_config)
    session.flush()
    session.commit()
    
    print(f"   ✓ 创建配置: {ollama_config.name}")
    print(f"      - 提供商: ollama")
    print(f"      - 地址: {config_data['base_url']}")
    print(f"      - 模型: {config_data['model_name']}")
    
    return ollama_config


async def bind_ollama_to_all_apps(
    session: Session,
    ollama_config: LLMConfiguration,
    apps_dict: dict[str, LLMApplication]
) -> None:
    """Bind Ollama to all applications with priority 1."""
    print("\n🔗 绑定 Ollama 到所有应用...")
    
    for app_code, app in apps_dict.items():
        # Check if binding already exists
        result = session.execute(
            select(LLMApplicationBinding).where(
                LLMApplicationBinding.application_id == app.id,
                LLMApplicationBinding.llm_config_id == ollama_config.id
            )
        )
        existing_binding = result.scalar_one_or_none()
        
        if existing_binding:
            print(f"   ✓ 绑定已存在: {app.name} -> Ollama (优先级: {existing_binding.priority})")
            continue
        
        # Create binding with priority 1
        binding = LLMApplicationBinding(
            llm_config_id=ollama_config.id,
            application_id=app.id,
            priority=1,
            max_retries=3,
            timeout_seconds=60,
            is_active=True
        )
        
        session.add(binding)
        print(f"   ✓ 创建绑定: {app.name} -> Ollama (优先级: 1)")
    
    session.commit()


async def display_summary(
    session: Session,
    ollama_config: LLMConfiguration,
    apps_dict: dict[str, LLMApplication]
) -> None:
    """Display configuration summary."""
    print("\n" + "="*60)
    print("📊 配置摘要")
    print("="*60)
    
    print(f"\n🔧 LLM 配置:")
    print(f"   名称: {ollama_config.name}")
    print(f"   ID: {ollama_config.id}")
    print(f"   提供商: {ollama_config.config_data.get('provider')}")
    print(f"   地址: {ollama_config.config_data.get('base_url')}")
    print(f"   模型: {ollama_config.config_data.get('model_name')}")
    
    print(f"\n📱 应用绑定:")
    for app_code, app in apps_dict.items():
        result = session.execute(
            select(LLMApplicationBinding)
            .where(LLMApplicationBinding.application_id == app.id)
            .order_by(LLMApplicationBinding.priority)
        )
        bindings = result.scalars().all()
        
        print(f"\n   {app.name} ({app_code}):")
        if bindings:
            for binding in bindings:
                config_name = ollama_config.name if binding.llm_config_id == ollama_config.id else "其他配置"
                print(f"      - 优先级 {binding.priority}: {config_name}")
        else:
            print(f"      - 无绑定")
    
    print("\n" + "="*60)


async def main():
    """Main execution function."""
    print("🚀 开始配置 Ollama LLM 和应用绑定")
    print("="*60)
    
    # Test Ollama connection
    print("\n1️⃣ 测试 Ollama 连接...")
    is_connected, models = await test_ollama_connection()
    
    if not is_connected:
        print("\n❌ 无法连接到 Ollama，请确保:")
        print("   1. Ollama 容器正在运行: docker compose ps ollama")
        print("   2. Ollama 服务已启动")
        print("   3. 网络连接正常")
        return 1
    
    # Select model
    model_name = "qwen2.5:7b"
    if models:
        # Prefer qwen2.5:7b, fallback to first available
        if any("qwen2.5" in m for m in models):
            model_name = next(m for m in models if "qwen2.5" in m)
        else:
            model_name = models[0]
        print(f"   使用模型: {model_name}")
    
    # Initialize database session
    with db_manager.get_session() as session:
        # Ensure all applications exist
        print("\n2️⃣ 确保所有 AI 应用已注册...")
        apps_dict = await ensure_applications_exist(session)
        
        # Create or get Ollama configuration
        print("\n3️⃣ 创建或获取 Ollama 配置...")
        ollama_config = await get_or_create_ollama_config(session, model_name)
        
        # Bind Ollama to all applications
        print("\n4️⃣ 绑定 Ollama 到所有应用...")
        await bind_ollama_to_all_apps(session, ollama_config, apps_dict)
        
        # Display summary
        await display_summary(session, ollama_config, apps_dict)
    
    print("\n✅ 配置完成！")
    print("\n💡 提示:")
    print("   - 所有应用现在都使用 Ollama 作为主要 LLM")
    print("   - 可以在管理界面添加云端 LLM 作为备用")
    print("   - 访问 http://localhost:5173/admin/llm-config 查看配置")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
