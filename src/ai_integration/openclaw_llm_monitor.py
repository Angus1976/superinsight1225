"""OpenClaw LLM Monitor - Extends existing LLM monitoring for OpenClaw gateways."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import threading

try:
    from src.ai.llm.health_monitor import HealthMonitor
    from src.ai.llm.audit_service import LLMAuditService, get_llm_audit_service
    from src.ai.llm_schemas import LLMMethod
except ImportError:
    from ai.llm.health_monitor import HealthMonitor
    from ai.llm.audit_service import LLMAuditService, get_llm_audit_service
    from ai.llm_schemas import LLMMethod

logger = logging.getLogger(__name__)

COST_PER_1K_TOKENS = {
    'openai': {'prompt': 0.0015, 'completion': 0.002},
    'qwen': {'prompt': 0.0008, 'completion': 0.0008},
    'ollama': {'prompt': 0.0, 'completion': 0.0},
}


class OpenClawPrometheusMetrics:
    """Prometheus metrics for OpenClaw LLM usage."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._requests_total: Dict[str, int] = defaultdict(int)
        self._tokens_total: Dict[str, int] = defaultdict(int)
        self._cost_total: Dict[str, float] = defaultdict(float)
        self._skill_executions_total: Dict[str, int] = defaultdict(int)
    
    def _labels_key(self, **labels) -> str:
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def inc_requests(self, gateway_id: str, skill_name: str, provider: str, status: str):
        with self._lock:
            key = self._labels_key(gateway_id=gateway_id, skill_name=skill_name, 
                                  provider=provider, status=status)
            self._requests_total[key] += 1
    
    def inc_tokens(self, gateway_id: str, skill_name: str, provider: str, 
                   token_type: str, count: int):
        with self._lock:
            key = self._labels_key(gateway_id=gateway_id, skill_name=skill_name,
                                  provider=provider, token_type=token_type)
            self._tokens_total[key] += count
    
    def inc_cost(self, gateway_id: str, skill_name: str, provider: str, cost: float):
        with self._lock:
            key = self._labels_key(gateway_id=gateway_id, skill_name=skill_name,
                                  provider=provider)
            self._cost_total[key] += cost
    
    def inc_skill_executions(self, gateway_id: str, skill_name: str):
        with self._lock:
            key = self._labels_key(gateway_id=gateway_id, skill_name=skill_name)
            self._skill_executions_total[key] += 1
    
    def export_prometheus(self) -> str:
        lines = []
        with self._lock:
            lines.append("# HELP llm_requests_total Total LLM requests by gateway and skill")
            lines.append("# TYPE llm_requests_total counter")
            for key, value in self._requests_total.items():
                labels = self._parse_labels_key(key)
                labels_str = self._format_labels(labels)
                lines.append(f"llm_requests_total{labels_str} {value}")
            
            lines.append("# HELP llm_tokens_total Total LLM tokens by gateway and skill")
            lines.append("# TYPE llm_tokens_total counter")
            for key, value in self._tokens_total.items():
                labels = self._parse_labels_key(key)
                labels_str = self._format_labels(labels)
                lines.append(f"llm_tokens_total{labels_str} {value}")
            
            lines.append("# HELP llm_cost_total Total LLM cost in USD by gateway and skill")
            lines.append("# TYPE llm_cost_total counter")
            for key, value in self._cost_total.items():
                labels = self._parse_labels_key(key)
                labels_str = self._format_labels(labels)
                lines.append(f"llm_cost_total{labels_str} {value}")
            
            lines.append("# HELP openclaw_skill_executions_total Total OpenClaw skill executions")
            lines.append("# TYPE openclaw_skill_executions_total counter")
            for key, value in self._skill_executions_total.items():
                labels = self._parse_labels_key(key)
                labels_str = self._format_labels(labels)
                lines.append(f"openclaw_skill_executions_total{labels_str} {value}")
        return "\n".join(lines)
    
    def _parse_labels_key(self, key: str) -> Dict[str, str]:
        if not key:
            return {}
        return dict(pair.split("=") for pair in key.split("|"))
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(pairs) + "}"
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'llm_requests_total': dict(self._requests_total),
                'llm_tokens_total': dict(self._tokens_total),
                'llm_cost_total': dict(self._cost_total),
                'openclaw_skill_executions_total': dict(self._skill_executions_total),
            }
    
    def reset(self):
        with self._lock:
            self._requests_total.clear()
            self._tokens_total.clear()
            self._cost_total.clear()
            self._skill_executions_total.clear()


class OpenClawLLMMonitor:
    """Monitors LLM usage for OpenClaw gateways."""
    
    def __init__(self, health_monitor=None, audit_service=None, config_manager=None):
        self.health_monitor = health_monitor
        self.audit_service = audit_service or get_llm_audit_service()
        self.config_manager = config_manager
        self._usage_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.prometheus_metrics = OpenClawPrometheusMetrics()
    
    async def record_gateway_usage(self, gateway_id, tenant_id, skill_name, provider,
                                   model, prompt_tokens, completion_tokens, latency_ms,
                                   success, error_message=None):
        """Record LLM usage for OpenClaw gateway."""
        try:
            total_tokens = prompt_tokens + completion_tokens
            cost = self._estimate_cost(provider, prompt_tokens, completion_tokens)
            
            record = {
                'gateway_id': gateway_id, 'tenant_id': tenant_id, 'skill_name': skill_name,
                'provider': provider.value, 'model': model, 'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens, 'total_tokens': total_tokens,
                'latency_ms': latency_ms, 'cost_usd': float(cost), 'success': success,
                'error_message': error_message, 'timestamp': datetime.utcnow().isoformat(),
            }
            
            if gateway_id not in self._usage_cache:
                self._usage_cache[gateway_id] = []
            self._usage_cache[gateway_id].append(record)
            
            # Update Prometheus metrics
            provider_name = self._map_provider_name(provider.value)
            status = 'success' if success else 'error'
            self.prometheus_metrics.inc_requests(gateway_id, skill_name, provider_name, status)
            self.prometheus_metrics.inc_tokens(gateway_id, skill_name, provider_name, 
                                              'prompt', prompt_tokens)
            self.prometheus_metrics.inc_tokens(gateway_id, skill_name, provider_name,
                                              'completion', completion_tokens)
            self.prometheus_metrics.inc_cost(gateway_id, skill_name, provider_name, float(cost))
            self.prometheus_metrics.inc_skill_executions(gateway_id, skill_name)
            
            if self.config_manager:
                await self.config_manager.log_usage(
                    method=provider, model=model, operation='generate', tenant_id=tenant_id,
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                    latency_ms=latency_ms, success=success)
        except Exception as e:
            logger.error(f"Failed to record gateway usage: {e}")
    
    def _estimate_cost(self, provider, prompt_tokens, completion_tokens):
        """Estimate cost using existing token tracking."""
        try:
            if provider == LLMMethod.CLOUD_OPENAI:
                prompt_cost = Decimal(str(prompt_tokens)) / Decimal('1000') * Decimal('0.0015')
                completion_cost = Decimal(str(completion_tokens)) / Decimal('1000') * Decimal('0.002')
                return prompt_cost + completion_cost
            elif provider == LLMMethod.CHINA_QWEN:
                total = Decimal(str(prompt_tokens + completion_tokens))
                return total / Decimal('1000') * Decimal('0.0008')
            elif provider == LLMMethod.LOCAL_OLLAMA:
                return Decimal('0.0')
            total = Decimal(str(prompt_tokens + completion_tokens))
            return total / Decimal('1000') * Decimal('0.001')
        except Exception as e:
            logger.warning(f"Failed to estimate cost: {e}")
            return Decimal('0.0')
    
    async def get_gateway_stats(self, gateway_id, start_time=None, end_time=None):
        """Get usage statistics querying existing audit logs."""
        try:
            records = self._usage_cache.get(gateway_id, [])
            
            if start_time or end_time:
                filtered = []
                for r in records:
                    rt = datetime.fromisoformat(r['timestamp'])
                    if start_time and rt < start_time:
                        continue
                    # Add 1 second buffer for end_time to handle timing issues
                    if end_time and rt > (end_time + timedelta(seconds=1)):
                        continue
                    filtered.append(r)
                records = filtered
            
            if not records:
                return {'gateway_id': gateway_id, 'total_requests': 0, 'successful_requests': 0,
                       'failed_requests': 0, 'success_rate': 0.0, 'total_tokens': 0,
                       'total_cost_usd': 0.0, 'avg_latency_ms': 0.0, 'by_skill': {},
                       'by_provider': {}, 'by_model': {}}
            
            total = len(records)
            success = sum(1 for r in records if r['success'])
            tokens = sum(r['total_tokens'] for r in records)
            cost = sum(r['cost_usd'] for r in records)
            latency = sum(r['latency_ms'] for r in records)
            
            by_skill, by_provider, by_model = {}, {}, {}
            for r in records:
                s = r['skill_name']
                if s not in by_skill:
                    by_skill[s] = {'requests': 0, 'tokens': 0, 'cost_usd': 0.0}
                by_skill[s]['requests'] += 1
                by_skill[s]['tokens'] += r['total_tokens']
                by_skill[s]['cost_usd'] += r['cost_usd']
                
                p = self._map_provider_name(r['provider'])
                if p not in by_provider:
                    by_provider[p] = {'requests': 0, 'tokens': 0, 'cost_usd': 0.0}
                by_provider[p]['requests'] += 1
                by_provider[p]['tokens'] += r['total_tokens']
                by_provider[p]['cost_usd'] += r['cost_usd']
                
                m = r['model']
                if m not in by_model:
                    by_model[m] = {'requests': 0, 'tokens': 0, 'cost_usd': 0.0}
                by_model[m]['requests'] += 1
                by_model[m]['tokens'] += r['total_tokens']
                by_model[m]['cost_usd'] += r['cost_usd']
            
            return {
                'gateway_id': gateway_id, 'total_requests': total,
                'successful_requests': success, 'failed_requests': total - success,
                'success_rate': round(success/total*100, 2) if total > 0 else 0.0,
                'total_tokens': tokens, 'total_cost_usd': round(cost, 4),
                'avg_latency_ms': round(latency/total, 2) if total > 0 else 0.0,
                'by_skill': by_skill, 'by_provider': by_provider, 'by_model': by_model,
            }
        except Exception as e:
            logger.error(f"Failed to get gateway stats: {e}")
            return {'gateway_id': gateway_id, 'error': str(e)}
    
    def _map_provider_name(self, provider_value):
        """Map provider enum value to display name."""
        mapping = {'cloud_openai': 'openai', 'cloud_azure': 'azure', 'china_qwen': 'qwen',
                  'china_zhipu': 'zhipu', 'china_baidu': 'baidu', 'china_hunyuan': 'hunyuan',
                  'local_ollama': 'ollama'}
        return mapping.get(provider_value, provider_value)
    
    async def get_all_gateways_stats(self, tenant_id=None):
        """Get usage statistics for all gateways."""
        try:
            gateways_stats, total_requests, total_tokens = {}, 0, 0
            for gid in self._usage_cache.keys():
                records = self._usage_cache[gid]
                if tenant_id:
                    records = [r for r in records if r['tenant_id'] == tenant_id]
                    if not records:
                        continue
                stats = await self.get_gateway_stats(gid)
                gateways_stats[gid] = stats
                total_requests += stats['total_requests']
                total_tokens += stats['total_tokens']
            
            result = {'total_gateways': len(gateways_stats), 'total_requests': total_requests,
                     'total_tokens': total_tokens, 'gateways': gateways_stats}
            if tenant_id:
                result['tenant_id'] = tenant_id
            return result
        except Exception as e:
            logger.error(f"Failed to get all gateways stats: {e}")
            return {'error': str(e)}
    
    async def get_provider_health(self, gateway_id, tenant_id):
        """Get provider health status."""
        if self.health_monitor is None:
            return {'error': 'Health monitor not available'}
        try:
            health_status = await self.health_monitor.get_all_health_status()
            return {'gateway_id': gateway_id, 'tenant_id': tenant_id, 'providers': health_status}
        except Exception as e:
            logger.error(f"Failed to get provider health: {e}")
            return {'error': str(e)}
    
    def clear_cache(self, gateway_id=None):
        """Clear usage cache."""
        if gateway_id:
            if gateway_id in self._usage_cache:
                del self._usage_cache[gateway_id]
                logger.info(f"Cleared cache for gateway {gateway_id}")
        else:
            self._usage_cache.clear()
            logger.info("Cleared all cache")


_openclaw_llm_monitor = None

def get_openclaw_llm_monitor(health_monitor=None, audit_service=None, config_manager=None):
    """Get or create the global OpenClaw LLM Monitor instance."""
    global _openclaw_llm_monitor
    if _openclaw_llm_monitor is None:
        _openclaw_llm_monitor = OpenClawLLMMonitor(health_monitor, audit_service, config_manager)
    return _openclaw_llm_monitor
