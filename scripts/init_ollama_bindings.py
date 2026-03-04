#!/usr/bin/env python3
"""
Initialize Ollama LLM bindings for all applications.

This script:
1. Creates an Ollama LLM configuration
2. Binds it to all 6 applications with appropriate priorities
3. Tests the connection to ensure Ollama is accessible

Usage:
    python scripts/init_ollama_bindings.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import db_manager
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.ai.encryption_service import get_encryption_service
import httpx


async def test_ollama_connection(base_url: str = "http://localhost:11434") -> bool:
    """Test if Ollama is accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                print(f"✅ Ollama is accessible at {base_url}")
                print(f"   Available models: {[m['name'] for m in models]}")
                return True
            else:
                print(f"❌ Ollama returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama at {base_url}: {e}")
        return False


async def get_or_create_ollama_config(session: AsyncSession) -> LLMConfiguration:
    """Get existing Ollama config or create a new one."""
    encryption_service = get_encryption_service()
    
    # Check if Ollama config already exists
    result = await session.execute(
        select(LLMConfiguration).where(
            LLMConfiguration.config_data['provider'].astext == "ollama",
            LLMConfiguration.is_active == True
        )
    )
    existing_config = result.scalars().first()
    
    if existing_config:
        print(f"✅ Found existing Ollama configuration: {existing_config.name}")
        return existing_config
    
    # Create new Ollama configuration
    config_data = {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "model_name": "llama3:8b",
        "api_key": "",  # Ollama doesn't require API key
    }
    
    ollama_config = LLMConfiguration(
        name="Ollama Llama3 Local",
        default_method="local_ollama",
        config_data=config_data,
        is_active=True,
        tenant_id=None  # Global configuration
    )
    
    session.add(ollama_config)
    await session.flush()
    
    print(f"✅ Created Ollama configuration: {ollama_config.name}")
    return ollama_config


async def get_all_applications(session: AsyncSession) -> list[LLMApplication]:
    """Get all registered applications."""
    result = await session.execute(
        select(LLMApplication).where(LLMApplication.is_active == True)
    )
    return list(result.scalars().all())


async def create_binding_if_not_exists(
    session: AsyncSession,
    llm_config: LLMConfiguration,
    application: LLMApplication,
    priority: int,
    max_retries: int,
    timeout_seconds: int
) -> bool:
    """Create a binding if it doesn't already exist."""
    # Check if binding already exists
    result = await session.execute(
        select(LLMApplicationBinding).where(
            LLMApplicationBinding.llm_config_id == llm_config.id,
            LLMApplicationBinding.application_id == application.id
        )
    )
    existing_binding = result.scalars().first()
    
    if existing_binding:
        print(f"   ⚠️  Binding already exists for {application.code} (priority {existing_binding.priority})")
        return False
    
    # Create new binding
    binding = LLMApplicationBinding(
        llm_config_id=llm_config.id,
        application_id=application.id,
        priority=priority,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
        is_active=True
    )
    
    session.add(binding)
    print(f"   ✅ Created binding for {application.code} (priority {priority})")
    return True


async def init_ollama_bindings():
    """Main function to initialize Ollama bindings."""
    print("=" * 70)
    print("Initializing Ollama LLM Bindings")
    print("=" * 70)
    print()
    
    # Step 1: Test Ollama connection
    print("Step 1: Testing Ollama connection...")
    if not await test_ollama_connection():
        print()
        print("❌ Ollama is not accessible. Please ensure:")
        print("   1. Ollama is installed: https://ollama.ai")
        print("   2. Ollama service is running: ollama serve")
        print("   3. At least one model is pulled: ollama pull llama3:8b")
        print()
        return False
    print()
    
    # Step 2: Create or get Ollama configuration
    print("Step 2: Setting up Ollama configuration...")
    async with db_manager.get_async_session() as session:
        try:
            ollama_config = await get_or_create_ollama_config(session)
            print()
            
            # Step 3: Get all applications
            print("Step 3: Loading applications...")
            applications = await get_all_applications(session)
            print(f"✅ Found {len(applications)} applications")
            print()
            
            # Step 4: Create bindings for each application
            print("Step 4: Creating bindings...")
            
            # Application-specific configurations
            binding_configs = {
                "structuring": {"priority": 1, "max_retries": 3, "timeout": 30},
                "knowledge_graph": {"priority": 1, "max_retries": 2, "timeout": 60},
                "ai_assistant": {"priority": 1, "max_retries": 3, "timeout": 20},
                "semantic_analysis": {"priority": 1, "max_retries": 2, "timeout": 45},
                "rag_agent": {"priority": 1, "max_retries": 3, "timeout": 30},
                "text_to_sql": {"priority": 1, "max_retries": 2, "timeout": 30},
            }
            
            created_count = 0
            for app in applications:
                config = binding_configs.get(app.code, {"priority": 1, "max_retries": 3, "timeout": 30})
                
                print(f"\n   {app.name} ({app.code}):")
                if await create_binding_if_not_exists(
                    session,
                    ollama_config,
                    app,
                    config["priority"],
                    config["max_retries"],
                    config["timeout"]
                ):
                    created_count += 1
            
            # Commit all changes
            await session.commit()
            
            print()
            print("=" * 70)
            print(f"✅ Initialization complete!")
            print(f"   - Created {created_count} new bindings")
            print(f"   - All {len(applications)} applications are now configured to use Ollama")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Access the admin UI at: http://localhost:5173/admin/llm-config")
            print("2. Test the configuration by running a structuring job")
            print("3. Monitor logs for LLM requests")
            print()
            
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            return False


async def show_current_status():
    """Show current binding status."""
    print("\n" + "=" * 70)
    print("Current LLM Configuration Status")
    print("=" * 70)
    print()
    
    async with db_manager.get_async_session() as session:
        # Get all applications
        apps_result = await session.execute(
            select(LLMApplication).where(LLMApplication.is_active == True)
        )
        applications = list(apps_result.scalars().all())
        
        # Get all bindings
        bindings_result = await session.execute(
            select(LLMApplicationBinding)
            .join(LLMConfiguration)
            .join(LLMApplication)
            .where(LLMApplicationBinding.is_active == True)
            .order_by(LLMApplication.code, LLMApplicationBinding.priority)
        )
        bindings = list(bindings_result.scalars().all())
        
        # Group bindings by application
        app_bindings = {}
        for binding in bindings:
            app_code = binding.application.code
            if app_code not in app_bindings:
                app_bindings[app_code] = []
            app_bindings[app_code].append(binding)
        
        # Display status
        for app in applications:
            app_bindings_list = app_bindings.get(app.code, [])
            status = "✅ Configured" if app_bindings_list else "⚠️  Not Configured"
            
            print(f"{status} {app.name} ({app.code})")
            if app_bindings_list:
                for binding in app_bindings_list:
                    config = binding.llm_config
                    print(f"   Priority {binding.priority}: {config.name} ({config.provider})")
            print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Ollama LLM bindings")
    parser.add_argument("--status", action="store_true", help="Show current binding status")
    args = parser.parse_args()
    
    if args.status:
        asyncio.run(show_current_status())
    else:
        success = asyncio.run(init_ollama_bindings())
        sys.exit(0 if success else 1)
