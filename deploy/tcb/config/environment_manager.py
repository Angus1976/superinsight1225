"""
TCB Environment Manager

Manages environment configuration and tenant resource limits for TCB deployment.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path


class EnvironmentManager:
    """Manages TCB environment configuration and tenant resources."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "deploy/tcb/config/multi-env-config.yaml"
        self.tenant_configs = {}
        self.load_configuration()
    
    def load_configuration(self):
        """Load environment configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self.tenant_configs = config.get('tenants', {})
        except Exception as e:
            print(f"Failed to load configuration: {e}")
            self.tenant_configs = {}
    
    def get_tenant_config(self) -> Dict[str, Any]:
        """Get tenant configuration."""
        return self.tenant_configs
    
    def get_tenant_resource_limits(self, tenant_id: str) -> Dict[str, Any]:
        """Get resource limits for a specific tenant."""
        tenant_config = self.tenant_configs.get(tenant_id, {})
        return {
            'max_cpu': tenant_config.get('max_cpu', '1000m'),
            'max_memory': tenant_config.get('max_memory', '2Gi'),
            'max_storage': tenant_config.get('max_storage', '50Gi'),
            'max_concurrent_tasks': tenant_config.get('max_concurrent_tasks', 25)
        }
    
    def set_tenant_resource_limits(self, tenant_id: str, limits: Dict[str, Any]):
        """Set resource limits for a tenant."""
        if tenant_id not in self.tenant_configs:
            self.tenant_configs[tenant_id] = {}
        
        self.tenant_configs[tenant_id].update(limits)
        self.save_configuration()
    
    def save_configuration(self):
        """Save configuration to file."""
        try:
            config = {'tenants': self.tenant_configs}
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        except Exception as e:
            print(f"Failed to save configuration: {e}")