"""
TCB Environment Configuration Manager.

Provides multi-environment configuration management for TCB deployments
with secrets management, validation, and environment-specific settings.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigValidationError(Exception):
    """Configuration validation error."""
    pass


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment."""
    name: Environment
    tcb_env_id: str
    tcb_region: str = "ap-shanghai"
    min_instances: int = 1
    max_instances: int = 10
    cpu: int = 2
    memory: int = 4096
    debug: bool = False
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_backup: bool = True
    backup_retention_days: int = 7
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecretConfig:
    """Secret configuration."""
    name: str
    required: bool = True
    env_var: str = ""
    default: Optional[str] = None
    description: str = ""


class TCBEnvConfigManager:
    """
    Environment configuration manager for TCB deployments.
    
    Features:
    - Multi-environment support (dev, test, staging, prod)
    - Secrets management
    - Configuration validation
    - Environment variable handling
    - Configuration export/import
    """
    
    # Required secrets for TCB deployment
    REQUIRED_SECRETS = [
        SecretConfig("TCB_SECRET_ID", True, "TCB_SECRET_ID", description="TCB API Secret ID"),
        SecretConfig("TCB_SECRET_KEY", True, "TCB_SECRET_KEY", description="TCB API Secret Key"),
        SecretConfig("POSTGRES_PASSWORD", True, "POSTGRES_PASSWORD", description="PostgreSQL password"),
        SecretConfig("SECRET_KEY", True, "SECRET_KEY", description="Application secret key"),
        SecretConfig("JWT_SECRET_KEY", True, "JWT_SECRET_KEY", description="JWT signing key"),
    ]
    
    # Optional secrets
    OPTIONAL_SECRETS = [
        SecretConfig("HUNYUAN_API_KEY", False, "HUNYUAN_API_KEY", description="Tencent Hunyuan API key"),
        SecretConfig("COS_SECRET_ID", False, "COS_SECRET_ID", description="COS Secret ID"),
        SecretConfig("COS_SECRET_KEY", False, "COS_SECRET_KEY", description="COS Secret Key"),
        SecretConfig("ALERT_WEBHOOK_URL", False, "ALERT_WEBHOOK_URL", description="Alert webhook URL"),
    ]
    
    def __init__(self):
        self.environments: Dict[Environment, EnvironmentConfig] = {}
        self.current_environment: Optional[Environment] = None
        self._secrets_cache: Dict[str, str] = {}
        
        # Register default environments
        self._register_default_environments()
        
        logger.info("TCBEnvConfigManager initialized")
    
    def _register_default_environments(self):
        """Register default environment configurations."""
        defaults = [
            EnvironmentConfig(
                name=Environment.DEVELOPMENT,
                tcb_env_id="${TCB_ENV_ID_DEV}",
                min_instances=1,
                max_instances=2,
                cpu=1,
                memory=2048,
                debug=True,
                log_level="DEBUG",
                enable_backup=False
            ),
            EnvironmentConfig(
                name=Environment.TESTING,
                tcb_env_id="${TCB_ENV_ID_TEST}",
                min_instances=1,
                max_instances=3,
                cpu=1,
                memory=2048,
                debug=True,
                log_level="DEBUG",
                enable_backup=False
            ),
            EnvironmentConfig(
                name=Environment.STAGING,
                tcb_env_id="${TCB_ENV_ID_STAGING}",
                min_instances=1,
                max_instances=5,
                cpu=2,
                memory=4096,
                debug=False,
                log_level="INFO",
                enable_backup=True,
                backup_retention_days=3
            ),
            EnvironmentConfig(
                name=Environment.PRODUCTION,
                tcb_env_id="${TCB_ENV_ID_PROD}",
                min_instances=2,
                max_instances=10,
                cpu=2,
                memory=4096,
                debug=False,
                log_level="WARNING",
                enable_backup=True,
                backup_retention_days=30
            )
        ]
        
        for config in defaults:
            self.environments[config.name] = config
    
    def set_environment(self, env: Environment):
        """Set the current environment."""
        if env not in self.environments:
            raise ValueError(f"Unknown environment: {env}")
        self.current_environment = env
        logger.info(f"Set current environment to: {env.value}")
    
    def get_environment_config(self, env: Optional[Environment] = None) -> EnvironmentConfig:
        """Get configuration for an environment."""
        env = env or self.current_environment
        if not env:
            raise ValueError("No environment specified or set")
        return self.environments[env]
    
    def update_environment_config(self, env: Environment, updates: Dict[str, Any]):
        """Update environment configuration."""
        if env not in self.environments:
            raise ValueError(f"Unknown environment: {env}")
        
        config = self.environments[env]
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                config.custom_settings[key] = value
        
        logger.info(f"Updated configuration for environment: {env.value}")
    
    def validate_configuration(self, env: Optional[Environment] = None) -> Dict[str, Any]:
        """Validate configuration for an environment."""
        env = env or self.current_environment
        if not env:
            raise ValueError("No environment specified or set")
        
        config = self.environments[env]
        errors = []
        warnings = []
        
        # Validate TCB env ID
        if not config.tcb_env_id or config.tcb_env_id.startswith("${"):
            resolved = self._resolve_env_var(config.tcb_env_id)
            if not resolved:
                errors.append(f"TCB_ENV_ID not configured for {env.value}")
        
        # Validate instance counts
        if config.min_instances < 1:
            errors.append("min_instances must be at least 1")
        if config.max_instances < config.min_instances:
            errors.append("max_instances must be >= min_instances")
        
        # Validate resources
        if config.cpu < 1:
            errors.append("CPU must be at least 1")
        if config.memory < 512:
            errors.append("Memory must be at least 512MB")
        
        # Validate required secrets
        for secret in self.REQUIRED_SECRETS:
            value = os.getenv(secret.env_var)
            if not value:
                errors.append(f"Required secret {secret.name} not set")
        
        # Check optional secrets
        for secret in self.OPTIONAL_SECRETS:
            value = os.getenv(secret.env_var)
            if not value:
                warnings.append(f"Optional secret {secret.name} not set")
        
        # Production-specific validations
        if env == Environment.PRODUCTION:
            if config.debug:
                errors.append("Debug mode should be disabled in production")
            if config.min_instances < 2:
                warnings.append("Production should have at least 2 min_instances for HA")
            if not config.enable_backup:
                errors.append("Backup must be enabled in production")
        
        return {
            "valid": len(errors) == 0,
            "environment": env.value,
            "errors": errors,
            "warnings": warnings
        }
    
    def _resolve_env_var(self, value: str) -> Optional[str]:
        """Resolve environment variable reference."""
        if not value:
            return None
        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.getenv(var_name)
        return value
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret value."""
        # Check cache first
        if secret_name in self._secrets_cache:
            return self._secrets_cache[secret_name]
        
        # Try environment variable
        value = os.getenv(secret_name)
        if value:
            self._secrets_cache[secret_name] = value
            return value
        
        return None
    
    def set_secret(self, secret_name: str, value: str):
        """Set a secret value (in memory only)."""
        self._secrets_cache[secret_name] = value
        os.environ[secret_name] = value
    
    def get_all_secrets_status(self) -> Dict[str, Any]:
        """Get status of all secrets."""
        required_status = {}
        for secret in self.REQUIRED_SECRETS:
            value = os.getenv(secret.env_var)
            required_status[secret.name] = {
                "configured": bool(value),
                "required": True,
                "description": secret.description
            }
        
        optional_status = {}
        for secret in self.OPTIONAL_SECRETS:
            value = os.getenv(secret.env_var)
            optional_status[secret.name] = {
                "configured": bool(value),
                "required": False,
                "description": secret.description
            }
        
        return {
            "required": required_status,
            "optional": optional_status,
            "all_required_configured": all(s["configured"] for s in required_status.values())
        }
    
    def generate_env_file(self, env: Environment, output_path: str) -> str:
        """Generate .env file for an environment."""
        config = self.environments[env]
        
        lines = [
            f"# TCB Environment Configuration for {env.value}",
            f"# Generated by TCBEnvConfigManager",
            "",
            "# TCB Settings",
            f"TCB_ENV_ID={self._resolve_env_var(config.tcb_env_id) or ''}",
            f"TCB_REGION={config.tcb_region}",
            "",
            "# Instance Configuration",
            f"TCB_MIN_INSTANCES={config.min_instances}",
            f"TCB_MAX_INSTANCES={config.max_instances}",
            f"TCB_CPU={config.cpu}",
            f"TCB_MEMORY={config.memory}",
            "",
            "# Application Settings",
            f"ENVIRONMENT={env.value}",
            f"DEBUG={str(config.debug).lower()}",
            f"LOG_LEVEL={config.log_level}",
            "",
            "# Features",
            f"ENABLE_METRICS={str(config.enable_metrics).lower()}",
            f"ENABLE_BACKUP={str(config.enable_backup).lower()}",
            f"BACKUP_RETENTION_DAYS={config.backup_retention_days}",
            "",
            "# Secrets (set these manually)",
            "# TCB_SECRET_ID=",
            "# TCB_SECRET_KEY=",
            "# POSTGRES_PASSWORD=",
            "# SECRET_KEY=",
            "# JWT_SECRET_KEY=",
        ]
        
        content = "\n".join(lines)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Generated env file: {output_path}")
        return output_path
    
    def export_cloudbaserc(self, env: Environment, output_path: str) -> str:
        """Export cloudbaserc.json for an environment."""
        config = self.environments[env]
        
        cloudbaserc = {
            "version": "2.0",
            "envId": self._resolve_env_var(config.tcb_env_id) or config.tcb_env_id,
            "region": config.tcb_region,
            "framework": {
                "name": f"superinsight-{env.value}",
                "plugins": {
                    "container": {
                        "use": "@cloudbase/framework-plugin-container",
                        "inputs": {
                            "serviceName": f"superinsight-{env.value}",
                            "dockerfilePath": "./deploy/tcb/Dockerfile.fullstack",
                            "containerPort": 8000,
                            "cpu": config.cpu,
                            "mem": config.memory,
                            "minNum": config.min_instances,
                            "maxNum": config.max_instances,
                            "envVariables": {
                                "ENVIRONMENT": env.value,
                                "DEBUG": str(config.debug).lower(),
                                "LOG_LEVEL": config.log_level,
                                "ENABLE_METRICS": str(config.enable_metrics).lower(),
                                "ENABLE_BACKUP": str(config.enable_backup).lower()
                            }
                        }
                    }
                }
            }
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(cloudbaserc, f, indent=2)
        
        logger.info(f"Exported cloudbaserc: {output_path}")
        return output_path
    
    def get_deployment_config(self, env: Optional[Environment] = None) -> Dict[str, Any]:
        """Get complete deployment configuration."""
        env = env or self.current_environment
        if not env:
            raise ValueError("No environment specified or set")
        
        config = self.environments[env]
        
        return {
            "environment": env.value,
            "tcb": {
                "env_id": self._resolve_env_var(config.tcb_env_id),
                "region": config.tcb_region
            },
            "scaling": {
                "min_instances": config.min_instances,
                "max_instances": config.max_instances
            },
            "resources": {
                "cpu": config.cpu,
                "memory_mb": config.memory
            },
            "application": {
                "debug": config.debug,
                "log_level": config.log_level
            },
            "features": {
                "metrics": config.enable_metrics,
                "backup": config.enable_backup,
                "backup_retention_days": config.backup_retention_days
            },
            "custom": config.custom_settings
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get configuration manager statistics."""
        secrets_status = self.get_all_secrets_status()
        
        return {
            "environments_configured": len(self.environments),
            "current_environment": self.current_environment.value if self.current_environment else None,
            "secrets_configured": secrets_status["all_required_configured"],
            "required_secrets_count": len(self.REQUIRED_SECRETS),
            "optional_secrets_count": len(self.OPTIONAL_SECRETS)
        }


# Global environment config manager
tcb_env_config_manager: Optional[TCBEnvConfigManager] = None


def initialize_tcb_env_config_manager() -> TCBEnvConfigManager:
    """Initialize the global TCB environment config manager."""
    global tcb_env_config_manager
    tcb_env_config_manager = TCBEnvConfigManager()
    return tcb_env_config_manager


def get_tcb_env_config_manager() -> Optional[TCBEnvConfigManager]:
    """Get the global TCB environment config manager."""
    return tcb_env_config_manager
