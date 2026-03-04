#!/usr/bin/env python3
"""
Simple script to setup Ollama LLM configuration and bind to all applications.
Run this inside the app container.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from src.database.connection import db_manager
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding


# Define all AI applications
AI_APPLICATIONS = [
    {
        "code": "structuring",
        "name": "数据结构化",
        "description": "模式推断和实体提取",
        "llm_usage_pattern": "用于非结构化数据的结构化处理"
    },
    {
        "code": "knowledge_graph",
        "name": "知识图谱",
        "description": "知识图谱构建",
        "llm_usage_pattern": "用于从文本中提取实体和关系"
    },
    {
        "code": "ai_assistant",
        "name": "AI 助手",
        "description": "智能助手服务",
        "llm_usage_pattern": "用于对话式交互和智能建议"
    },
    {
        "code": "semantic_analysis",
        "name": "语义分析",
        "description": "语义分析服务",
        "llm_usage_pattern": "用于文本语义理解和分析"
    },
    {
        "code": "rag_agent",
        "name": "RAG 智能体",
        "description": "检索增强生成",
        "llm_usage_pattern": "用于基于知识库的问答"
    },
    {
        "code": "text_to_sql",
        "name": "文本转 SQL",
        "description": "自然语言转 SQL 查询",
        "llm_usage_pattern": "用于将自然语言转换为 SQL"
    }
]


def main():
    print("🚀 配置 Ollama LLM 和应用绑定")
    print("="*60)
    
    with db_manager.get_session() as session:
        # 1. Ensure all applications exist
        print("\n1️⃣ 确保所有 AI 应用已注册...")
        apps_dict = {}
        
        for app_def in AI_APPLICATIONS:
            result = session.execute(
                select(LLMApplication).where(LLMApplication.code == app_def["code"])
            )
            app = result.scalar_one_or_none()
            
            if app:
                print(f"   ✓ 应用已存在: {app_def['name']} ({app_def['code']})")
            else:
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
        
        # 2. Create or get Ollama configuration
        print("\n2️⃣ 创建或获取 Ollama 配置...")
        
        result = session.execute(
            select(LLMConfiguration).where(
                LLMConfiguration.name.like("%Ollama%"),
                LLMConfiguration.is_active == True
            )
        )
        ollama_config = result.scalars().first()
        
        if ollama_config:
            print(f"   ✓ 找到现有配置: {ollama_config.name}")
        else:
            config_data = {
                "provider": "ollama",
                "base_url": "http://localhost:11434",
                "model_name": "qwen2.5:1.5b",
                "api_key_encrypted": "",
            }
            
            ollama_config = LLMConfiguration(
                name="Ollama qwen2.5:1.5b",
                default_method="local_ollama",
                config_data=config_data,
                is_active=True,
                tenant_id=None
            )
            
            session.add(ollama_config)
            session.flush()
            session.commit()
            
            print(f"   ✓ 创建配置: {ollama_config.name}")
            print(f"      - 提供商: ollama")
            print(f"      - 地址: {config_data['base_url']}")
            print(f"      - 模型: {config_data['model_name']}")
        
        # 3. Bind Ollama to all applications
        print("\n3️⃣ 绑定 Ollama 到所有应用...")
        
        for app_code, app in apps_dict.items():
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
        
        # 4. Display summary
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
    
    print("\n✅ 配置完成！")
    print("\n💡 提示:")
    print("   - 所有应用现在都使用 Ollama 作为主要 LLM")
    print("   - 可以在管理界面添加云端 LLM 作为备用")
    print("   - 访问 http://localhost:5173/admin/llm-config 查看配置")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
