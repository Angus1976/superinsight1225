"""
OpenClaw LLM Bridge - Integrates existing LLM infrastructure with OpenClaw gateways.

This module bridges OpenClaw AI gateways with SuperInsight's existing LLM configuration
management system, enabling OpenClaw to use configured LLM providers (cloud, China, local).

Features:
- Maps LLMConfig to OpenClaw environment variables
- Converts LLMMethod to OpenClaw provider names
- Handles LLM requests using existing LLMSwitcher
- Monitors usage extending existing log_usage functionality
- Supports all existing providers: OpenAI, Azure, Qwen, Zhipu, Baidu, Hunyuan, Ollama

Reuses:
- LLMConfigManager: Configuration management
- LLMSwitcher: Unified LLM calling interface
- ChinaLLMProvider: China-based LLM providers
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from datetime import datetime

try:
    from src.ai.llm_config_manager import LLMConfigManager, get_config_manager
    from src.ai.llm_switcher import LLMSwitcher
    from src.ai.llm_schemas import (
        LLMConfig, LLMMethod, GenerateOptions, LLMResponse, LLMError
    )
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.ai.llm_config_manager import LLMConfigManager, get_config_manager
    from src.ai.llm_switcher import LLMSwitcher
    from src.ai.llm_schemas import (
        LLMConfig, LLMMethod, GenerateOptions, LLMResponse, LLMError
    )

logger = logging.getLogger(__name__)

# OpenClaw Core chat/completions 的 model 字段：``{provider}/{modelId}``（与 UI 中模型选择器一致）
_OPENCLAW_PROVIDER_PREFIX: Dict[str, str] = {
    "ollama": "ollama",
    "openai": "openai",
    "azure": "azure",
    "qwen": "qwen",
    "zhipu": "zhipu",
    "baidu": "baidu",
    "hunyuan": "hunyuan",
}


class OpenClawLLMBridge:
    """
    Bridges OpenClaw with existing LLM system.
    
    This class integrates OpenClaw AI gateways with SuperInsight's LLM infrastructure,
    allowing OpenClaw to use any configured LLM provider through a unified interface.
    
    **Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6**
    """
    
    # OpenClaw provider name mapping
    PROVIDER_MAPPING = {
        LLMMethod.LOCAL_OLLAMA: 'ollama',
        LLMMethod.CLOUD_OPENAI: 'openai',
        LLMMethod.CLOUD_AZURE: 'azure',
        LLMMethod.CHINA_QWEN: 'qwen',
        LLMMethod.CHINA_ZHIPU: 'zhipu',
        LLMMethod.CHINA_BAIDU: 'baidu',
        LLMMethod.CHINA_HUNYUAN: 'hunyuan',
    }
    
    def __init__(
        self,
        config_manager: Optional[LLMConfigManager] = None,
        llm_switcher: Optional[LLMSwitcher] = None,
    ):
        """
        Initialize the OpenClaw LLM Bridge.
        
        Args:
            config_manager: LLM configuration manager (uses global if None)
            llm_switcher: LLM switcher instance (creates new if None)
        """
        self.config_manager = config_manager or get_config_manager()
        self.llm_switcher = llm_switcher
        self._switcher_cache: Dict[str, LLMSwitcher] = {}
    
    def llm_config_to_openclaw_env(self, config: LLMConfig) -> Dict[str, str]:
        """将已解析的 ``LLMConfig`` 转为 OpenClaw 环境变量（同步、可单测）。"""
        env_vars = {
            'LLM_PROVIDER': self._map_provider(config.default_method),
            'LLM_API_ENDPOINT': self._get_endpoint(config),
            'LLM_MODEL': self._get_model(config),
            'LLM_TEMPERATURE': str(getattr(config, 'temperature', 0.7)),
            'LLM_MAX_TOKENS': str(getattr(config, 'max_tokens', 2048)),
        }
        api_key = self._get_api_key(config)
        if api_key:
            env_vars['LLM_API_KEY'] = api_key
        if config.default_method == LLMMethod.CLOUD_AZURE:
            env_vars['LLM_AZURE_DEPLOYMENT'] = config.cloud_config.azure_deployment or ''
            env_vars['LLM_AZURE_API_VERSION'] = config.cloud_config.azure_api_version
        return env_vars

    def openclaw_core_chat_model(self, env_vars: Dict[str, str]) -> str:
        """
        将 ``llm_config_to_openclaw_env`` 产物映射为 OpenClaw Core HTTP API 的 ``model`` 字符串。

        平台在管理台切换 LLM 行 / 覆盖 model 后，网关侧应使用此值调用 Core，而非写死 openclaw.json。
        """
        prov = (env_vars.get("LLM_PROVIDER") or "ollama").strip().lower()
        model = (env_vars.get("LLM_MODEL") or "").strip()
        if not model:
            return "openclaw/default"
        if "/" in model:
            return model
        prefix = _OPENCLAW_PROVIDER_PREFIX.get(prov, prov)
        return f"{prefix}/{model}"

    def sync_resolve_openclaw_chat_model_for_gateway(
        self,
        db: Session,
        gateway: Any,
    ) -> str:
        """
        根据网关中保存的 LLM 关联（及覆盖项）解析 Core 用 model，供 openclaw-gateway 注入请求体。

        解析失败时退回 ``openclaw/default``（由 Core 本地配置决定行为）。
        """
        try:
            from src.ai.llm_config_manager import resolve_llm_config_for_openclaw_sync

            cfg = gateway.configuration if gateway else None
            lc = (cfg or {}).get("llm_config") or {}
            if not isinstance(lc, dict):
                lc = {}
            pinned = lc.get("llm_configuration_id")
            pinned_s = str(pinned) if pinned else None
            tenant_id = getattr(gateway, "tenant_id", None) or ""
            resolved = resolve_llm_config_for_openclaw_sync(db, tenant_id, pinned_s)
            env_vars = self.llm_config_to_openclaw_env(resolved)
            # 与保存关联 / llm-link 一致：应用网关中已存的覆盖（勿重复写入 OPENCLAW_CORE_CHAT_MODEL）
            if lc.get("model_override"):
                env_vars["LLM_MODEL"] = str(lc["model_override"])
            if lc.get("temperature_override") is not None:
                env_vars["LLM_TEMPERATURE"] = str(lc["temperature_override"])
            if lc.get("max_tokens_override") is not None:
                env_vars["LLM_MAX_TOKENS"] = str(lc["max_tokens_override"])
            return self.openclaw_core_chat_model(env_vars)
        except Exception as e:
            logger.warning(
                "sync_resolve_openclaw_chat_model_for_gateway failed, using openclaw/default: %s",
                e,
            )
            return "openclaw/default"

    def sync_openclaw_llm_preview(
        self,
        db: Session,
        tenant_id: str,
        gateway: Any,
    ) -> Dict[str, str]:
        """
        供 AI 助手 service-status 等展示：当前租户 OpenClaw 通道将使用的 LLM 解析结果。

        优先级：网关上固定的 ``llm_configuration_id`` > ``openclaw`` 应用绑定 > 租户默认 LLM 行。
        """
        from src.ai.llm_config_manager import resolve_llm_config_for_openclaw_sync
        from src.ai.llm_application_channels import get_openclaw_primary_llm_configuration_row

        lc: Dict[str, Any] = {}
        if gateway is not None and getattr(gateway, "configuration", None):
            raw = (gateway.configuration or {}).get("llm_config")
            if isinstance(raw, dict):
                lc = raw
        pinned = lc.get("llm_configuration_id")
        pinned_s = str(pinned) if pinned else None

        config = resolve_llm_config_for_openclaw_sync(db, tenant_id or "", pinned_s)
        env_vars = self.llm_config_to_openclaw_env(config)
        if lc.get("model_override"):
            env_vars["LLM_MODEL"] = str(lc["model_override"])
        if lc.get("temperature_override") is not None:
            env_vars["LLM_TEMPERATURE"] = str(lc["temperature_override"])
        if lc.get("max_tokens_override") is not None:
            env_vars["LLM_MAX_TOKENS"] = str(lc["max_tokens_override"])
        core = self.openclaw_core_chat_model(env_vars)

        if pinned_s:
            source = "gateway_pinned"
        elif get_openclaw_primary_llm_configuration_row(db, tenant_id):
            source = "application_binding"
        else:
            source = "tenant_default_row"

        return {
            "channel": "openclaw_gateway",
            "application_code": "openclaw",
            "provider": env_vars.get("LLM_PROVIDER") or "",
            "model": env_vars.get("LLM_MODEL") or "",
            "openclaw_core_model": core,
            "source": source,
        }

    def sync_llm_direct_channel_preview(
        self,
        db: Session,
        tenant_id: str,
    ) -> Dict[str, str]:
        """
        **AI 助手 · LLM 直连** 通道预览（``ai_assistant`` 应用绑定 → 租户默认 → env）。

        与 ``get_llm_switcher(application_code='ai_assistant')`` 解析顺序一致（同步子集）。
        """
        from src.ai.llm_application_channels import (
            AI_ASSISTANT_LLM_APPLICATION_CODE,
            resolve_ai_assistant_direct_llm_config_sync,
        )

        cfg, source = resolve_ai_assistant_direct_llm_config_sync(db, tenant_id or "")
        env_vars = self.llm_config_to_openclaw_env(cfg)
        return {
            "channel": "ai_assistant_direct",
            "application_code": AI_ASSISTANT_LLM_APPLICATION_CODE,
            "provider": env_vars.get("LLM_PROVIDER") or "",
            "model": env_vars.get("LLM_MODEL") or "",
            "source": source,
        }

    async def get_openclaw_env_vars(
        self,
        gateway_id: str,
        tenant_id: str,
        llm_configuration_id: Optional[str] = None,
        sync_db: Optional[Session] = None,
    ) -> Dict[str, str]:
        """
        Generate OpenClaw environment variables from LLM config.
        
        Maps SuperInsight's LLMConfig to environment variables that OpenClaw
        can use to configure its LLM provider.
        
        Args:
            gateway_id: Gateway identifier
            tenant_id: Tenant identifier
            sync_db: 若传入 FastAPI 的同步 ``Session``，则用其解析 LLM 行（网关路由必选；
                全局 ``LLMConfigManager`` 往往无 ``AsyncSession``，否则会得到空配置→始终 Ollama）。
            
        Returns:
            Dictionary of environment variables for OpenClaw
            
        **Validates: Requirements 17.1, 17.4**
        """
        try:
            if sync_db is not None:
                from src.ai.llm_config_manager import resolve_llm_config_for_openclaw_sync
                config = resolve_llm_config_for_openclaw_sync(
                    sync_db, tenant_id, llm_configuration_id
                )
            elif llm_configuration_id:
                config = await self.config_manager.get_config_by_id(
                    tenant_id, llm_configuration_id
                )
            else:
                config = await self.config_manager.get_config(tenant_id)

            env_vars = self.llm_config_to_openclaw_env(config)
            env_vars["OPENCLAW_CORE_CHAT_MODEL"] = self.openclaw_core_chat_model(env_vars)

            logger.info(
                f"Generated OpenClaw env vars for gateway {gateway_id}, "
                f"provider: {env_vars['LLM_PROVIDER']}"
            )

            return env_vars
            
        except Exception as e:
            logger.exception(
                "Failed to generate OpenClaw env vars for gateway %s (pinned=%s): %s",
                gateway_id,
                llm_configuration_id,
                e,
            )
            # Return default configuration (仅作兜底；上游应修复配置解析，避免静默退回 Ollama)
            fb = {
                'LLM_PROVIDER': 'ollama',
                'LLM_API_ENDPOINT': 'http://ollama:11434',
                'LLM_MODEL': 'qwen:7b',
                'LLM_TEMPERATURE': '0.7',
                'LLM_MAX_TOKENS': '2048',
            }
            fb['OPENCLAW_CORE_CHAT_MODEL'] = self.openclaw_core_chat_model(fb)
            return fb
    
    def _map_provider(self, method: LLMMethod) -> str:
        """
        Map LLMMethod to OpenClaw provider name.
        
        Args:
            method: SuperInsight LLM method
            
        Returns:
            OpenClaw provider name
            
        **Validates: Requirements 17.2**
        """
        return self.PROVIDER_MAPPING.get(method, 'openai')
    
    def _get_endpoint(self, config: LLMConfig) -> str:
        """
        Get API endpoint for the configured LLM method.
        
        Args:
            config: LLM configuration
            
        Returns:
            API endpoint URL
        """
        method = config.default_method
        
        if method == LLMMethod.LOCAL_OLLAMA:
            return config.local_config.ollama_url
        elif method == LLMMethod.CLOUD_OPENAI:
            return config.cloud_config.openai_base_url
        elif method == LLMMethod.CLOUD_AZURE:
            return config.cloud_config.azure_endpoint or ''
        elif method == LLMMethod.CHINA_QWEN:
            return 'https://dashscope.aliyuncs.com/api/v1'
        elif method == LLMMethod.CHINA_ZHIPU:
            return 'https://open.bigmodel.cn/api/paas/v4'
        elif method == LLMMethod.CHINA_BAIDU:
            return 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1'
        elif method == LLMMethod.CHINA_HUNYUAN:
            return 'https://hunyuan.tencentcloudapi.com'
        else:
            return 'http://localhost:11434'
    
    def _get_model(self, config: LLMConfig) -> str:
        """
        Get default model for the configured LLM method.
        
        Args:
            config: LLM configuration
            
        Returns:
            Model name
        """
        method = config.default_method
        
        if method == LLMMethod.LOCAL_OLLAMA:
            return config.local_config.default_model
        elif method == LLMMethod.CLOUD_OPENAI:
            return config.cloud_config.openai_model
        elif method == LLMMethod.CLOUD_AZURE:
            return config.cloud_config.azure_deployment or 'gpt-35-turbo'
        elif method == LLMMethod.CHINA_QWEN:
            return config.china_config.qwen_model
        elif method == LLMMethod.CHINA_ZHIPU:
            return config.china_config.zhipu_model
        elif method == LLMMethod.CHINA_BAIDU:
            return config.china_config.baidu_model
        elif method == LLMMethod.CHINA_HUNYUAN:
            return config.china_config.hunyuan_model
        else:
            return 'qwen:7b'
    
    def _get_api_key(self, config: LLMConfig) -> Optional[str]:
        """
        Get API key for the configured LLM method.
        
        Args:
            config: LLM configuration
            
        Returns:
            API key or None
        """
        method = config.default_method
        
        if method == LLMMethod.CLOUD_OPENAI:
            return config.cloud_config.openai_api_key
        elif method == LLMMethod.CLOUD_AZURE:
            return config.cloud_config.azure_api_key
        elif method == LLMMethod.CHINA_QWEN:
            return config.china_config.qwen_api_key
        elif method == LLMMethod.CHINA_ZHIPU:
            return config.china_config.zhipu_api_key
        elif method == LLMMethod.CHINA_BAIDU:
            return config.china_config.baidu_api_key
        elif method == LLMMethod.CHINA_HUNYUAN:
            return config.china_config.hunyuan_secret_id
        else:
            return None
    
    async def handle_llm_request(
        self,
        gateway_id: str,
        tenant_id: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Handle LLM request from OpenClaw skill.
        
        Uses existing LLMSwitcher to process the request with automatic
        failover, retry logic, and usage logging.
        
        Args:
            gateway_id: Gateway identifier
            tenant_id: Tenant identifier
            prompt: Input prompt
            options: Generation options (optional)
            model: Model override (optional)
            system_prompt: System prompt (optional)
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            LLMError: If generation fails
            
        **Validates: Requirements 17.3, 17.5, 18.1**
        """
        try:
            # Get or create LLMSwitcher for this tenant
            switcher = await self._get_switcher(tenant_id)
            
            # Convert options dict to GenerateOptions
            gen_options = GenerateOptions(**(options or {}))
            
            # Generate response using existing LLMSwitcher
            response = await switcher.generate(
                prompt=prompt,
                options=gen_options,
                model=model,
                system_prompt=system_prompt,
            )
            
            # Log usage with gateway context
            await self.monitor_usage(gateway_id, tenant_id, response)
            
            logger.info(
                f"LLM request handled for gateway {gateway_id}, "
                f"model: {response.model}, tokens: {response.usage.total_tokens}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM request failed for gateway {gateway_id}: {e}")
            raise
    
    async def monitor_usage(
        self,
        gateway_id: str,
        tenant_id: str,
        response: LLMResponse,
    ) -> None:
        """
        Log LLM usage for monitoring.
        
        Extends existing log_usage functionality with gateway-specific metadata.
        
        Args:
            gateway_id: Gateway identifier
            tenant_id: Tenant identifier
            response: LLM response with usage data
            
        **Validates: Requirements 17.6, 19.1**
        """
        try:
            await self.config_manager.log_usage(
                method=response.provider,
                model=response.model,
                operation='generate',
                tenant_id=tenant_id,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                latency_ms=response.latency_ms,
                success=True,
            )
            
            logger.debug(
                f"Logged usage for gateway {gateway_id}: "
                f"{response.usage.total_tokens} tokens, "
                f"{response.latency_ms:.2f}ms latency"
            )
            
        except Exception as e:
            logger.warning(f"Failed to log usage for gateway {gateway_id}: {e}")
    
    async def _get_switcher(self, tenant_id: str) -> LLMSwitcher:
        """
        Get or create LLMSwitcher for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            LLMSwitcher instance
        """
        if tenant_id not in self._switcher_cache:
            switcher = LLMSwitcher(
                config_manager=self.config_manager,
                tenant_id=tenant_id,
            )
            await switcher.initialize()
            self._switcher_cache[tenant_id] = switcher
        
        return self._switcher_cache[tenant_id]
    
    async def get_llm_status(
        self,
        gateway_id: str,
        tenant_id: str,
        llm_configuration_id: Optional[str] = None,
        sync_db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Get LLM status for a gateway.
        
        Args:
            gateway_id: Gateway identifier
            tenant_id: Tenant identifier
            sync_db: 同步 ``Session``（与 ``get_openclaw_env_vars`` 相同，网关 API 应传入）
            
        Returns:
            Dictionary with LLM status information
            
        **Validates: Requirements 17.4, 19.2**
        """
        try:
            if sync_db is not None:
                from src.ai.llm_config_manager import resolve_llm_config_for_openclaw_sync
                config = resolve_llm_config_for_openclaw_sync(
                    sync_db, tenant_id, llm_configuration_id
                )
            elif llm_configuration_id:
                config = await self.config_manager.get_config_by_id(
                    tenant_id, llm_configuration_id, mask_keys=True
                )
            else:
                config = await self.config_manager.get_config(tenant_id, mask_keys=True)
            
            # Get switcher
            switcher = await self._get_switcher(tenant_id)
            
            # Get health status
            health_status = await switcher.health_check()
            
            return {
                'gateway_id': gateway_id,
                'tenant_id': tenant_id,
                'provider': self._map_provider(config.default_method),
                'model': self._get_model(config),
                'health': {
                    method.value: {
                        'available': status.available,
                        'latency_ms': status.latency_ms,
                        'error': status.error,
                    }
                    for method, status in health_status.items()
                },
                'enabled_methods': [m.value for m in config.enabled_methods],
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get LLM status for gateway {gateway_id}: {e}")
            return {
                'gateway_id': gateway_id,
                'tenant_id': tenant_id,
                'provider': 'unknown',
                'model': 'unknown',
                'health': {},
                'enabled_methods': [],
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
            }


# Singleton instance for global access
_openclaw_llm_bridge: Optional[OpenClawLLMBridge] = None


def get_openclaw_llm_bridge(
    config_manager: Optional[LLMConfigManager] = None,
    llm_switcher: Optional[LLMSwitcher] = None,
) -> OpenClawLLMBridge:
    """
    Get or create the global OpenClaw LLM Bridge instance.
    
    Args:
        config_manager: LLM configuration manager
        llm_switcher: LLM switcher instance
        
    Returns:
        OpenClawLLMBridge instance
    """
    global _openclaw_llm_bridge
    
    if _openclaw_llm_bridge is None:
        _openclaw_llm_bridge = OpenClawLLMBridge(config_manager, llm_switcher)
    
    return _openclaw_llm_bridge
