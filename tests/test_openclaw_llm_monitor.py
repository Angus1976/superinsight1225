"""
Unit tests for OpenClawLLMMonitor.

Tests the OpenClaw-specific LLM monitoring functionality including:
- Gateway usage recording
- Statistics aggregation
- Cost estimation
- Provider health status

**Feature: ai-application-integration**
**Validates: Requirements 19.1, 19.2, 19.6**
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from src.ai_integration.openclaw_llm_monitor import (
    OpenClawLLMMonitor,
    get_openclaw_llm_monitor,
    COST_PER_1K_TOKENS,
)
from src.ai.llm_schemas import LLMMethod


@pytest.fixture
def mock_audit_service():
    """Create mock audit service."""
    service = Mock()
    return service


@pytest.fixture
def mock_config_manager():
    """Create mock config manager."""
    manager = Mock()
    manager.log_usage = AsyncMock()
    return manager


@pytest.fixture
def monitor(mock_audit_service, mock_config_manager):
    """Create a fresh monitor instance for each test."""
    monitor = OpenClawLLMMonitor(
        audit_service=mock_audit_service,
        health_monitor=None,
        config_manager=mock_config_manager,
    )
    monitor.clear_cache()
    return monitor


@pytest.mark.asyncio
async def test_record_gateway_usage(monitor):
    """Test recording gateway LLM usage."""
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='data-query',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=250.5,
        success=True,
    )
    
    # Verify usage was recorded in cache
    assert 'gateway-1' in monitor._usage_cache
    assert len(monitor._usage_cache['gateway-1']) == 1
    
    record = monitor._usage_cache['gateway-1'][0]
    assert record['gateway_id'] == 'gateway-1'
    assert record['tenant_id'] == 'tenant-1'
    assert record['skill_name'] == 'data-query'
    assert record['provider'] == 'cloud_openai'  # Enum value, not mapped name
    assert record['model'] == 'gpt-3.5-turbo'
    assert record['prompt_tokens'] == 100
    assert record['completion_tokens'] == 50
    assert record['total_tokens'] == 150
    assert record['latency_ms'] == 250.5
    assert record['success'] is True
    assert record['cost_usd'] > 0


@pytest.mark.asyncio
async def test_record_multiple_gateway_usage(monitor):
    """Test recording usage for multiple gateways."""
    # Record for gateway-1
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Record for gateway-2
    await monitor.record_gateway_usage(
        gateway_id='gateway-2',
        tenant_id='tenant-1',
        skill_name='skill-b',
        provider=LLMMethod.CHINA_QWEN,
        model='qwen-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    # Verify both gateways have records
    assert len(monitor._usage_cache) == 2
    assert 'gateway-1' in monitor._usage_cache
    assert 'gateway-2' in monitor._usage_cache


@pytest.mark.asyncio
async def test_estimate_cost_openai(monitor):
    """Test cost estimation for OpenAI."""
    cost = monitor._estimate_cost(
        provider=LLMMethod.CLOUD_OPENAI,
        prompt_tokens=1000,
        completion_tokens=500,
    )
    
    # OpenAI: $0.0015/1K prompt + $0.002/1K completion
    expected = Decimal('1.0') * Decimal('0.0015') + Decimal('0.5') * Decimal('0.002')
    assert cost == expected


@pytest.mark.asyncio
async def test_estimate_cost_qwen(monitor):
    """Test cost estimation for Qwen."""
    cost = monitor._estimate_cost(
        provider=LLMMethod.CHINA_QWEN,
        prompt_tokens=1000,
        completion_tokens=500,
    )
    
    # Qwen: $0.0008/1K for both
    expected = Decimal('1.0') * Decimal('0.0008') + Decimal('0.5') * Decimal('0.0008')
    assert cost == expected


@pytest.mark.asyncio
async def test_estimate_cost_ollama(monitor):
    """Test cost estimation for Ollama (free)."""
    cost = monitor._estimate_cost(
        provider=LLMMethod.LOCAL_OLLAMA,
        prompt_tokens=1000,
        completion_tokens=500,
    )
    
    assert cost == Decimal('0.0')


@pytest.mark.asyncio
async def test_get_gateway_stats_empty(monitor):
    """Test getting stats for gateway with no usage."""
    stats = await monitor.get_gateway_stats('gateway-1')
    
    assert stats['gateway_id'] == 'gateway-1'
    assert stats['total_requests'] == 0
    assert stats['total_tokens'] == 0
    assert stats['total_cost_usd'] == 0.0
    assert stats['avg_latency_ms'] == 0.0
    assert stats['success_rate'] == 0.0


@pytest.mark.asyncio
async def test_get_gateway_stats_single_request(monitor):
    """Test getting stats for gateway with single request."""
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=250.0,
        success=True,
    )
    
    stats = await monitor.get_gateway_stats('gateway-1')
    
    assert stats['gateway_id'] == 'gateway-1'
    assert stats['total_requests'] == 1
    assert stats['total_tokens'] == 150
    assert stats['avg_latency_ms'] == 250.0
    assert stats['success_rate'] == 100.0
    assert stats['successful_requests'] == 1
    assert stats['failed_requests'] == 0


@pytest.mark.asyncio
async def test_get_gateway_stats_multiple_requests(monitor):
    """Test getting stats for gateway with multiple requests."""
    # Record 3 successful requests
    for i in range(3):
        await monitor.record_gateway_usage(
            gateway_id='gateway-1',
            tenant_id='tenant-1',
            skill_name='skill-a',
            provider=LLMMethod.CLOUD_OPENAI,
            model='gpt-3.5-turbo',
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=200.0 + i * 50,
            success=True,
        )
    
    # Record 1 failed request (with prompt tokens but no completion)
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=0,
        latency_ms=100.0,
        success=False,
        error_message='Rate limit exceeded',
    )
    
    stats = await monitor.get_gateway_stats('gateway-1')
    
    assert stats['total_requests'] == 4
    assert stats['total_tokens'] == 550  # 3 * 150 + 100
    assert stats['success_rate'] == 75.0  # 3/4
    assert stats['successful_requests'] == 3
    assert stats['failed_requests'] == 1


@pytest.mark.asyncio
async def test_get_gateway_stats_by_skill(monitor):
    """Test stats aggregation by skill."""
    # Record for skill-a
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Record for skill-b
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-b',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    stats = await monitor.get_gateway_stats('gateway-1')
    
    assert 'skill-a' in stats['by_skill']
    assert 'skill-b' in stats['by_skill']
    assert stats['by_skill']['skill-a']['requests'] == 1
    assert stats['by_skill']['skill-a']['tokens'] == 150
    assert stats['by_skill']['skill-b']['requests'] == 1
    assert stats['by_skill']['skill-b']['tokens'] == 300


@pytest.mark.asyncio
async def test_get_gateway_stats_by_provider(monitor):
    """Test stats aggregation by provider."""
    # Record for OpenAI
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Record for Qwen
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CHINA_QWEN,
        model='qwen-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    stats = await monitor.get_gateway_stats('gateway-1')
    
    assert 'openai' in stats['by_provider']
    assert 'qwen' in stats['by_provider']
    assert stats['by_provider']['openai']['requests'] == 1
    assert stats['by_provider']['openai']['tokens'] == 150
    assert stats['by_provider']['qwen']['requests'] == 1
    assert stats['by_provider']['qwen']['tokens'] == 300


@pytest.mark.asyncio
async def test_get_gateway_stats_by_model(monitor):
    """Test stats aggregation by model."""
    # Record for gpt-3.5-turbo
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Record for gpt-4
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-4',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=400.0,
        success=True,
    )
    
    stats = await monitor.get_gateway_stats('gateway-1')
    
    assert 'gpt-3.5-turbo' in stats['by_model']
    assert 'gpt-4' in stats['by_model']
    assert stats['by_model']['gpt-3.5-turbo']['requests'] == 1
    assert stats['by_model']['gpt-3.5-turbo']['tokens'] == 150
    assert stats['by_model']['gpt-4']['requests'] == 1
    assert stats['by_model']['gpt-4']['tokens'] == 300


@pytest.mark.asyncio
async def test_get_gateway_stats_time_range(monitor):
    """Test filtering stats by time range."""
    now = datetime.utcnow()
    
    # Record usage with custom timestamp (simulate old record)
    record = {
        'gateway_id': 'gateway-1',
        'tenant_id': 'tenant-1',
        'skill_name': 'skill-a',
        'provider': 'openai',
        'model': 'gpt-3.5-turbo',
        'prompt_tokens': 100,
        'completion_tokens': 50,
        'total_tokens': 150,
        'latency_ms': 200.0,
        'cost_usd': 0.25,
        'success': True,
        'error_message': None,
        'timestamp': (now - timedelta(hours=48)).isoformat(),
    }
    monitor._usage_cache['gateway-1'] = [record]
    
    # Record recent usage
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Get stats for last 24 hours (should only include recent record)
    stats = await monitor.get_gateway_stats(
        'gateway-1',
        start_time=now - timedelta(hours=24),
        end_time=now,
    )
    
    assert stats['total_requests'] == 1  # Only recent record


@pytest.mark.asyncio
async def test_get_all_gateways_stats(monitor):
    """Test getting stats for all gateways."""
    # Record for gateway-1
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Record for gateway-2
    await monitor.record_gateway_usage(
        gateway_id='gateway-2',
        tenant_id='tenant-1',
        skill_name='skill-b',
        provider=LLMMethod.CHINA_QWEN,
        model='qwen-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    stats = await monitor.get_all_gateways_stats()
    
    assert stats['total_gateways'] == 2
    assert stats['total_requests'] == 2
    assert stats['total_tokens'] == 450  # 150 + 300
    assert 'gateway-1' in stats['gateways']
    assert 'gateway-2' in stats['gateways']


@pytest.mark.asyncio
async def test_get_all_gateways_stats_filtered_by_tenant(monitor):
    """Test filtering all gateways stats by tenant."""
    # Record for tenant-1
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    # Record for tenant-2
    await monitor.record_gateway_usage(
        gateway_id='gateway-2',
        tenant_id='tenant-2',
        skill_name='skill-b',
        provider=LLMMethod.CHINA_QWEN,
        model='qwen-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    # Get stats for tenant-1 only
    stats = await monitor.get_all_gateways_stats(tenant_id='tenant-1')
    
    assert stats['tenant_id'] == 'tenant-1'
    assert stats['total_gateways'] == 1
    assert 'gateway-1' in stats['gateways']
    assert 'gateway-2' not in stats['gateways']


@pytest.mark.asyncio
async def test_get_provider_health_no_monitor(monitor):
    """Test getting provider health when health monitor is not available."""
    health = await monitor.get_provider_health('gateway-1', 'tenant-1')
    
    assert 'error' in health
    assert health['error'] == 'Health monitor not available'


@pytest.mark.asyncio
async def test_clear_cache_specific_gateway(monitor):
    """Test clearing cache for specific gateway."""
    # Record for two gateways
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    await monitor.record_gateway_usage(
        gateway_id='gateway-2',
        tenant_id='tenant-1',
        skill_name='skill-b',
        provider=LLMMethod.CHINA_QWEN,
        model='qwen-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    # Clear only gateway-1
    monitor.clear_cache('gateway-1')
    
    assert 'gateway-1' not in monitor._usage_cache
    assert 'gateway-2' in monitor._usage_cache


@pytest.mark.asyncio
async def test_clear_cache_all(monitor):
    """Test clearing cache for all gateways."""
    # Record for two gateways
    await monitor.record_gateway_usage(
        gateway_id='gateway-1',
        tenant_id='tenant-1',
        skill_name='skill-a',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-3.5-turbo',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=200.0,
        success=True,
    )
    
    await monitor.record_gateway_usage(
        gateway_id='gateway-2',
        tenant_id='tenant-1',
        skill_name='skill-b',
        provider=LLMMethod.CHINA_QWEN,
        model='qwen-turbo',
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=300.0,
        success=True,
    )
    
    # Clear all
    monitor.clear_cache()
    
    assert len(monitor._usage_cache) == 0


def test_get_openclaw_llm_monitor_singleton():
    """Test singleton pattern for monitor."""
    monitor1 = get_openclaw_llm_monitor()
    monitor2 = get_openclaw_llm_monitor()
    
    assert monitor1 is monitor2


# ============================================================================
# Prometheus Metrics Tests
# ============================================================================

def test_prometheus_metrics_initialization():
    """Test Prometheus metrics initialization."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    assert metrics._requests_total == {}
    assert metrics._tokens_total == {}
    assert metrics._cost_total == {}
    assert metrics._skill_executions_total == {}


def test_prometheus_metrics_inc_requests():
    """Test incrementing request counter."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    metrics.inc_requests('gateway1', 'skill1', 'openai', 'success')
    metrics.inc_requests('gateway1', 'skill1', 'openai', 'success')
    metrics.inc_requests('gateway1', 'skill1', 'openai', 'error')
    
    metrics_dict = metrics.get_metrics_dict()
    
    # Check that counters are incremented correctly
    assert len(metrics_dict['llm_requests_total']) == 2  # 2 unique label combinations
    
    # Find the success counter
    success_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|status=success'
    error_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|status=error'
    
    assert metrics_dict['llm_requests_total'][success_key] == 2
    assert metrics_dict['llm_requests_total'][error_key] == 1


def test_prometheus_metrics_inc_tokens():
    """Test incrementing token counter."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    metrics.inc_tokens('gateway1', 'skill1', 'openai', 'prompt', 100)
    metrics.inc_tokens('gateway1', 'skill1', 'openai', 'prompt', 50)
    metrics.inc_tokens('gateway1', 'skill1', 'openai', 'completion', 200)
    
    metrics_dict = metrics.get_metrics_dict()
    
    prompt_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|token_type=prompt'
    completion_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|token_type=completion'
    
    assert metrics_dict['llm_tokens_total'][prompt_key] == 150
    assert metrics_dict['llm_tokens_total'][completion_key] == 200


def test_prometheus_metrics_inc_cost():
    """Test incrementing cost counter."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    metrics.inc_cost('gateway1', 'skill1', 'openai', 0.05)
    metrics.inc_cost('gateway1', 'skill1', 'openai', 0.03)
    metrics.inc_cost('gateway1', 'skill2', 'qwen', 0.01)
    
    metrics_dict = metrics.get_metrics_dict()
    
    skill1_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1'
    skill2_key = 'gateway_id=gateway1|provider=qwen|skill_name=skill2'
    
    assert abs(metrics_dict['llm_cost_total'][skill1_key] - 0.08) < 0.001
    assert abs(metrics_dict['llm_cost_total'][skill2_key] - 0.01) < 0.001


def test_prometheus_metrics_inc_skill_executions():
    """Test incrementing skill execution counter."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    metrics.inc_skill_executions('gateway1', 'skill1')
    metrics.inc_skill_executions('gateway1', 'skill1')
    metrics.inc_skill_executions('gateway1', 'skill2')
    
    metrics_dict = metrics.get_metrics_dict()
    
    skill1_key = 'gateway_id=gateway1|skill_name=skill1'
    skill2_key = 'gateway_id=gateway1|skill_name=skill2'
    
    assert metrics_dict['openclaw_skill_executions_total'][skill1_key] == 2
    assert metrics_dict['openclaw_skill_executions_total'][skill2_key] == 1


def test_prometheus_metrics_export_format():
    """Test Prometheus export format."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    metrics.inc_requests('gateway1', 'skill1', 'openai', 'success')
    metrics.inc_tokens('gateway1', 'skill1', 'openai', 'prompt', 100)
    metrics.inc_cost('gateway1', 'skill1', 'openai', 0.05)
    metrics.inc_skill_executions('gateway1', 'skill1')
    
    export = metrics.export_prometheus()
    
    # Check that export contains all metric types
    assert '# HELP llm_requests_total' in export
    assert '# TYPE llm_requests_total counter' in export
    assert 'llm_requests_total{gateway_id="gateway1",provider="openai",skill_name="skill1",status="success"} 1' in export
    
    assert '# HELP llm_tokens_total' in export
    assert '# TYPE llm_tokens_total counter' in export
    assert 'llm_tokens_total{gateway_id="gateway1",provider="openai",skill_name="skill1",token_type="prompt"} 100' in export
    
    assert '# HELP llm_cost_total' in export
    assert '# TYPE llm_cost_total counter' in export
    assert 'llm_cost_total{gateway_id="gateway1",provider="openai",skill_name="skill1"} 0.05' in export
    
    assert '# HELP openclaw_skill_executions_total' in export
    assert '# TYPE openclaw_skill_executions_total counter' in export
    assert 'openclaw_skill_executions_total{gateway_id="gateway1",skill_name="skill1"} 1' in export


def test_prometheus_metrics_multiple_gateways():
    """Test metrics with multiple gateways and skills."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    # Gateway 1, Skill 1
    metrics.inc_requests('gateway1', 'skill1', 'openai', 'success')
    metrics.inc_tokens('gateway1', 'skill1', 'openai', 'prompt', 100)
    
    # Gateway 1, Skill 2
    metrics.inc_requests('gateway1', 'skill2', 'qwen', 'success')
    metrics.inc_tokens('gateway1', 'skill2', 'qwen', 'prompt', 200)
    
    # Gateway 2, Skill 1
    metrics.inc_requests('gateway2', 'skill1', 'openai', 'success')
    metrics.inc_tokens('gateway2', 'skill1', 'openai', 'prompt', 150)
    
    metrics_dict = metrics.get_metrics_dict()
    
    # Should have 3 unique request combinations
    assert len(metrics_dict['llm_requests_total']) == 3
    
    # Should have 3 unique token combinations
    assert len(metrics_dict['llm_tokens_total']) == 3


def test_prometheus_metrics_reset():
    """Test resetting metrics."""
    from src.ai_integration.openclaw_llm_monitor import OpenClawPrometheusMetrics
    
    metrics = OpenClawPrometheusMetrics()
    
    metrics.inc_requests('gateway1', 'skill1', 'openai', 'success')
    metrics.inc_tokens('gateway1', 'skill1', 'openai', 'prompt', 100)
    metrics.inc_cost('gateway1', 'skill1', 'openai', 0.05)
    metrics.inc_skill_executions('gateway1', 'skill1')
    
    # Verify metrics exist
    metrics_dict = metrics.get_metrics_dict()
    assert len(metrics_dict['llm_requests_total']) > 0
    
    # Reset
    metrics.reset()
    
    # Verify all metrics are cleared
    metrics_dict = metrics.get_metrics_dict()
    assert len(metrics_dict['llm_requests_total']) == 0
    assert len(metrics_dict['llm_tokens_total']) == 0
    assert len(metrics_dict['llm_cost_total']) == 0
    assert len(metrics_dict['openclaw_skill_executions_total']) == 0


@pytest.mark.asyncio
async def test_monitor_updates_prometheus_metrics(monitor):
    """Test that monitor updates Prometheus metrics on usage recording."""
    await monitor.record_gateway_usage(
        gateway_id='gateway1',
        tenant_id='tenant1',
        skill_name='skill1',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-4',
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=500,
        success=True
    )
    
    metrics_dict = monitor.prometheus_metrics.get_metrics_dict()
    
    # Check requests counter
    success_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|status=success'
    assert metrics_dict['llm_requests_total'][success_key] == 1
    
    # Check tokens counters
    prompt_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|token_type=prompt'
    completion_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|token_type=completion'
    assert metrics_dict['llm_tokens_total'][prompt_key] == 100
    assert metrics_dict['llm_tokens_total'][completion_key] == 50
    
    # Check cost counter
    cost_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1'
    assert cost_key in metrics_dict['llm_cost_total']
    assert metrics_dict['llm_cost_total'][cost_key] > 0
    
    # Check skill executions counter
    skill_key = 'gateway_id=gateway1|skill_name=skill1'
    assert metrics_dict['openclaw_skill_executions_total'][skill_key] == 1


@pytest.mark.asyncio
async def test_monitor_prometheus_metrics_with_errors(monitor):
    """Test Prometheus metrics with error status."""
    await monitor.record_gateway_usage(
        gateway_id='gateway1',
        tenant_id='tenant1',
        skill_name='skill1',
        provider=LLMMethod.CLOUD_OPENAI,
        model='gpt-4',
        prompt_tokens=100,
        completion_tokens=0,
        latency_ms=500,
        success=False,
        error_message='API error'
    )
    
    metrics_dict = monitor.prometheus_metrics.get_metrics_dict()
    
    # Check error status is recorded
    error_key = 'gateway_id=gateway1|provider=openai|skill_name=skill1|status=error'
    assert metrics_dict['llm_requests_total'][error_key] == 1
