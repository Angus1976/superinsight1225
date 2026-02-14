#!/usr/bin/env python3
"""
AI Gateway Deployment Script

Deploys OpenClaw gateway using docker-compose with environment variable
injection from database configuration, LLM configuration, and health check verification.

Usage:
    python scripts/deploy_ai_gateway.py --gateway-id <gateway-id>
    python scripts/deploy_ai_gateway.py --gateway-id <gateway-id> --env-file .env.custom

Features:
- Fetches LLM config using existing LLMConfigManager
- Generates OpenClaw environment variables via OpenClawLLMBridge
- Injects LLM settings into docker-compose environment
- Reuses existing hot-reload functionality
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.models.ai_integration import AIGateway
from src.ai_integration.openclaw_llm_bridge import get_openclaw_llm_bridge


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Deploy AI gateway using docker-compose"
    )
    parser.add_argument(
        "--gateway-id",
        required=True,
        help="Gateway ID to deploy"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file path (default: .env)"
    )
    parser.add_argument(
        "--compose-file",
        default="docker-compose.ai-integration.yml",
        help="Docker compose file (default: docker-compose.ai-integration.yml)"
    )
    parser.add_argument(
        "--health-check-timeout",
        type=int,
        default=120,
        help="Health check timeout in seconds (default: 120)"
    )
    return parser.parse_args()


def fetch_gateway_config(
    gateway_id: str,
    db: Session
) -> Optional[AIGateway]:
    """Fetch gateway configuration from database."""
    gateway = db.query(AIGateway).filter(
        AIGateway.id == gateway_id
    ).first()
    
    if not gateway:
        print(f"Error: Gateway {gateway_id} not found")
        return None
    
    if gateway.status == "inactive":
        print(f"Warning: Gateway {gateway_id} is inactive")
    
    return gateway


async def build_environment_vars(gateway: AIGateway) -> Dict[str, str]:
    """
    Build environment variables from gateway configuration and LLM config.
    
    Fetches LLM config using existing LLMConfigManager and generates
    OpenClaw environment variables via OpenClawLLMBridge.
    
    **Validates: Requirements 17.4, 17.5**
    """
    env_vars = {
        "TENANT_ID": gateway.tenant_id,
        "OPENCLAW_API_KEY": gateway.api_key_hash,  # Will be actual key in production
    }
    
    # Extract configuration values
    config = gateway.configuration or {}
    
    # Fetch LLM configuration using OpenClawLLMBridge
    try:
        llm_bridge = get_openclaw_llm_bridge()
        llm_env_vars = await llm_bridge.get_openclaw_env_vars(
            gateway_id=gateway.id,
            tenant_id=gateway.tenant_id
        )
        
        # Merge LLM environment variables
        env_vars.update(llm_env_vars)
        print(f"✓ LLM configuration loaded: provider={llm_env_vars.get('LLM_PROVIDER')}, model={llm_env_vars.get('LLM_MODEL')}")
        
    except Exception as e:
        print(f"Warning: Failed to fetch LLM config, using defaults: {e}")
        # Fallback to default LLM configuration
        env_vars.update({
            "LLM_PROVIDER": "ollama",
            "LLM_API_ENDPOINT": "http://ollama:11434",
            "LLM_MODEL": "qwen:7b",
            "LLM_TEMPERATURE": "0.7",
            "LLM_MAX_TOKENS": "2048",
        })
    
    # Language configuration
    if "language" in config:
        lang_config = config["language"]
        env_vars["OPENCLAW_USER_LANGUAGE"] = lang_config.get("user_language", "zh-CN")
        env_vars["OPENCLAW_LOCALE"] = lang_config.get("locale", "zh-CN")
        if "system_prompt" in lang_config:
            env_vars["OPENCLAW_SYSTEM_PROMPT"] = lang_config["system_prompt"]
    else:
        # Default language settings
        env_vars["OPENCLAW_USER_LANGUAGE"] = "zh-CN"
        env_vars["OPENCLAW_LOCALE"] = "zh-CN"
    
    # Agent configuration
    if "agent" in config:
        agent_config = config["agent"]
        env_vars["OPENCLAW_AGENT_NAME"] = agent_config.get("name", "SuperInsight Assistant")
        env_vars["OPENCLAW_AGENT_DESCRIPTION"] = agent_config.get("description", "AI assistant for governed data access")
    else:
        env_vars["OPENCLAW_AGENT_NAME"] = "SuperInsight Assistant"
        env_vars["OPENCLAW_AGENT_DESCRIPTION"] = "AI assistant for governed data access"
    
    # Logging configuration
    if "logging" in config:
        log_config = config["logging"]
        env_vars["OPENCLAW_LOG_LEVEL"] = log_config.get("level", "info")
    else:
        env_vars["OPENCLAW_LOG_LEVEL"] = "info"
    
    return env_vars


def write_env_file(
    env_vars: Dict[str, str],
    env_file_path: str
) -> None:
    """Write environment variables to file."""
    with open(env_file_path, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"Environment variables written to {env_file_path}")


def deploy_with_docker_compose(
    compose_file: str,
    env_file: str
) -> bool:
    """Deploy gateway using docker-compose."""
    if not os.path.exists(compose_file):
        print(f"Error: Compose file {compose_file} not found")
        return False
    
    cmd = [
        "docker-compose",
        "-f", "docker-compose.yml",
        "-f", compose_file,
        "--env-file", env_file,
        "up", "-d"
    ]
    
    print(f"Deploying with command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        return False


def verify_health(
    timeout: int
) -> bool:
    """Verify gateway health after deployment."""
    gateway_url = "http://localhost:3000/health"
    agent_url = "http://localhost:8080/health"
    
    print(f"Waiting for services to be healthy (timeout: {timeout}s)...")
    
    start_time = time.time()
    gateway_healthy = False
    agent_healthy = False
    
    while time.time() - start_time < timeout:
        # Check gateway health
        if not gateway_healthy:
            try:
                result = subprocess.run(
                    ["curl", "-f", "-s", gateway_url],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    gateway_healthy = True
                    print("✓ OpenClaw gateway is healthy")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
        
        # Check agent health
        if not agent_healthy:
            try:
                result = subprocess.run(
                    ["curl", "-f", "-s", agent_url],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    agent_healthy = True
                    print("✓ OpenClaw agent is healthy")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
        
        if gateway_healthy and agent_healthy:
            return True
        
        time.sleep(5)
    
    if not gateway_healthy:
        print("✗ OpenClaw gateway health check failed")
    if not agent_healthy:
        print("✗ OpenClaw agent health check failed")
    
    return False


async def main_async() -> int:
    """Main deployment function (async)."""
    args = parse_arguments()
    
    print(f"Deploying AI gateway: {args.gateway_id}")
    
    # Fetch gateway configuration
    db = next(get_db())
    try:
        gateway = fetch_gateway_config(args.gateway_id, db)
        if not gateway:
            return 1
        
        print(f"Gateway: {gateway.name} (type: {gateway.gateway_type})")
        print(f"Tenant: {gateway.tenant_id}")
        
        # Build environment variables (now async to fetch LLM config)
        env_vars = await build_environment_vars(gateway)
        
        # Write environment file
        write_env_file(env_vars, args.env_file)
        
        # Deploy with docker-compose
        if not deploy_with_docker_compose(args.compose_file, args.env_file):
            return 1
        
        # Verify health
        if not verify_health(args.health_check_timeout):
            print("Warning: Health check failed, but deployment completed")
            print("Check logs: docker logs superinsight-openclaw-gateway")
            print("Check logs: docker logs superinsight-openclaw-agent")
            return 1
        
        print("\n✓ Deployment successful!")
        print(f"Gateway {gateway.name} is running and healthy")
        print(f"LLM Provider: {env_vars.get('LLM_PROVIDER')}")
        print(f"LLM Model: {env_vars.get('LLM_MODEL')}")
        
        return 0
        
    finally:
        db.close()


def main() -> int:
    """Main entry point."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
