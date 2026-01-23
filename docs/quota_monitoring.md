# LLM Provider Quota Monitoring

## Overview

The LLM Provider Quota Monitoring feature tracks API usage per configuration and sends alerts when approaching quota limits. This helps administrators proactively manage API costs and prevent service disruptions due to quota exhaustion.

**Validates Requirements: 10.4**

## Features

- **Real-time Quota Tracking**: Track API requests, tokens used, success/failure rates per configuration
- **Configurable Alert Thresholds**: Set custom alert thresholds (default: 80% of quota)
- **Background Monitoring**: Automatic periodic checks for quota violations
- **Alert Spam Prevention**: Prevents duplicate alerts within 1-hour window
- **Multiple Alert Handlers**: Support for multiple notification channels (email, Slack, webhooks, etc.)
- **Async-First Architecture**: Non-blocking monitoring using asyncio

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           LLMProviderManager                            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Quota Cache (per config_id)                     │  │
│  │  - total_requests                                 │  │
│  │  - successful_requests                            │  │
│  │  - failed_requests                                │  │
│  │  - total_tokens                                   │  │
│  │  - quota_limit                                    │  │
│  │  - alert_threshold_percent                        │  │
│  │  - last_alert_sent                                │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Background Monitoring Loop                       │  │
│  │  - Checks all quotas periodically                │  │
│  │  - Triggers alerts when threshold exceeded       │  │
│  │  - Prevents alert spam                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Alert Handlers                                   │  │
│  │  - Email notifications                            │  │
│  │  - Slack webhooks                                │  │
│  │  - Custom webhooks                               │  │
│  │  - SMS (Twilio)                                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Basic Setup

```python
from src.admin.llm_provider_manager import LLMProviderManager, QuotaInfo

# Initialize manager
manager = LLMProviderManager()

# Define alert handler
async def quota_alert_handler(config_id: str, quota: QuotaInfo):
    """Called when quota threshold is reached."""
    usage_percent = (quota.total_tokens / quota.quota_limit) * 100
    print(f"⚠️  Alert: {config_id} at {usage_percent:.1f}% quota usage")
    # Send notification via email, Slack, etc.

# Register alert handler
manager.add_alert_handler(quota_alert_handler)

# Set quota limit for a configuration
await manager.set_quota_limit(
    config_id="openai-prod",
    quota_limit=100000,  # 100k tokens
    alert_threshold_percent=80.0  # Alert at 80%
)

# Start background monitoring (checks every 60 seconds)
await manager.start_monitoring(interval=60)
```

### Tracking API Usage

```python
# After each API call, update quota usage
await manager.update_quota_usage(
    config_id="openai-prod",
    provider="openai",
    tokens_used=1500,
    success=True
)
```

### Getting Quota Status

```python
# Get status for specific configuration
status = await manager.get_quota_status("openai-prod")
print(f"Usage: {status['usage_percent']:.1f}%")
print(f"Tokens: {status['total_tokens']} / {status['quota_limit']}")
print(f"Alert Triggered: {status['alert_triggered']}")

# Get status for all configurations
all_statuses = await manager.get_all_quota_statuses()
for status in all_statuses:
    print(f"{status['config_id']}: {status['usage_percent']:.1f}%")
```

### Stopping Monitoring

```python
# Stop background monitoring
await manager.stop_monitoring()
```

## API Reference

### Methods

#### `add_alert_handler(handler: Callable[[str, QuotaInfo], None])`

Register a callback function to be called when quota alerts are triggered.

**Parameters:**
- `handler`: Callback function that receives `(config_id, quota_info)`

**Example:**
```python
def my_alert_handler(config_id: str, quota: QuotaInfo):
    send_email(f"Quota alert for {config_id}")

manager.add_alert_handler(my_alert_handler)
```

#### `remove_alert_handler(handler: Callable[[str, QuotaInfo], None])`

Remove a previously registered alert handler.

#### `set_quota_limit(config_id: str, quota_limit: int, alert_threshold_percent: float = 80.0)`

Set quota limit and alert threshold for a configuration.

**Parameters:**
- `config_id`: Configuration identifier
- `quota_limit`: Maximum quota in tokens
- `alert_threshold_percent`: Alert threshold (0-100), default 80%

**Raises:**
- `ValueError`: If threshold is not between 0 and 100

#### `start_monitoring(interval: int = 60)`

Start background quota monitoring task.

**Parameters:**
- `interval`: Check interval in seconds (default: 60)

#### `stop_monitoring()`

Stop background quota monitoring task.

#### `get_quota_status(config_id: str) -> Optional[Dict[str, Any]]`

Get detailed quota status for a configuration.

**Returns:**
```python
{
    "config_id": "openai-prod",
    "provider": "openai",
    "total_requests": 1000,
    "successful_requests": 995,
    "failed_requests": 5,
    "total_tokens": 85000,
    "quota_limit": 100000,
    "quota_remaining": 15000,
    "usage_percent": 85.0,
    "alert_threshold_percent": 80.0,
    "alert_triggered": True,
    "reset_at": "2026-02-01T00:00:00",
    "last_updated": "2026-01-22T10:30:00",
    "last_alert_sent": "2026-01-22T10:25:00"
}
```

#### `get_all_quota_statuses() -> List[Dict[str, Any]]`

Get quota status for all configurations.

#### `update_quota_usage(config_id: str, provider: str, tokens_used: int = 0, success: bool = True)`

Update quota usage after an API call.

**Parameters:**
- `config_id`: Configuration identifier
- `provider`: Provider name
- `tokens_used`: Number of tokens consumed
- `success`: Whether the request was successful

## Alert Handler Examples

### Email Notification

```python
import smtplib
from email.mime.text import MIMEText

async def email_alert_handler(config_id: str, quota: QuotaInfo):
    usage_percent = (quota.total_tokens / quota.quota_limit) * 100
    
    msg = MIMEText(
        f"Quota alert for {config_id}\n"
        f"Usage: {usage_percent:.1f}%\n"
        f"Tokens: {quota.total_tokens:,} / {quota.quota_limit:,}"
    )
    msg['Subject'] = f'Quota Alert: {config_id}'
    msg['From'] = 'alerts@example.com'
    msg['To'] = 'admin@example.com'
    
    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)

manager.add_alert_handler(email_alert_handler)
```

### Slack Webhook

```python
import aiohttp

async def slack_alert_handler(config_id: str, quota: QuotaInfo):
    usage_percent = (quota.total_tokens / quota.quota_limit) * 100
    
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    message = {
        "text": f"⚠️ Quota Alert: {config_id}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Quota Alert for {config_id}*\n"
                        f"• Usage: {usage_percent:.1f}%\n"
                        f"• Tokens: {quota.total_tokens:,} / {quota.quota_limit:,}\n"
                        f"• Provider: {quota.provider}"
                    )
                }
            }
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=message)

manager.add_alert_handler(slack_alert_handler)
```

### Custom Webhook

```python
import aiohttp

async def webhook_alert_handler(config_id: str, quota: QuotaInfo):
    webhook_url = "https://your-api.com/alerts"
    
    payload = {
        "alert_type": "quota_threshold",
        "config_id": config_id,
        "provider": quota.provider,
        "usage_percent": (quota.total_tokens / quota.quota_limit) * 100,
        "total_tokens": quota.total_tokens,
        "quota_limit": quota.quota_limit,
        "timestamp": quota.last_updated.isoformat()
    }
    
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=payload)

manager.add_alert_handler(webhook_alert_handler)
```

## Configuration Best Practices

### 1. Set Appropriate Thresholds

```python
# Production: Alert early to allow time for action
await manager.set_quota_limit("openai-prod", 100000, alert_threshold_percent=75.0)

# Development: Higher threshold for less critical environments
await manager.set_quota_limit("openai-dev", 10000, alert_threshold_percent=90.0)
```

### 2. Monitor Multiple Providers

```python
configs = [
    ("openai-prod", "openai", 100000, 75.0),
    ("anthropic-prod", "anthropic", 50000, 80.0),
    ("ollama-local", "ollama", 1000000, 95.0),  # Local has higher limit
]

for config_id, provider, limit, threshold in configs:
    await manager.update_quota_usage(config_id, provider, 0, True)
    await manager.set_quota_limit(config_id, limit, threshold)
```

### 3. Adjust Monitoring Interval

```python
# Production: Check frequently (every minute)
await manager.start_monitoring(interval=60)

# Development: Check less frequently (every 5 minutes)
await manager.start_monitoring(interval=300)
```

### 4. Handle Multiple Alert Channels

```python
# Register multiple handlers for redundancy
manager.add_alert_handler(email_alert_handler)
manager.add_alert_handler(slack_alert_handler)
manager.add_alert_handler(pagerduty_alert_handler)
```

## Integration with Monitoring Systems

### Prometheus Metrics

```python
from prometheus_client import Gauge

quota_usage_gauge = Gauge(
    'llm_quota_usage_percent',
    'LLM quota usage percentage',
    ['config_id', 'provider']
)

async def prometheus_handler(config_id: str, quota: QuotaInfo):
    usage_percent = (quota.total_tokens / quota.quota_limit) * 100
    quota_usage_gauge.labels(
        config_id=config_id,
        provider=quota.provider
    ).set(usage_percent)

manager.add_alert_handler(prometheus_handler)
```

### Grafana Dashboard

Create a Grafana dashboard to visualize quota usage:

```json
{
  "title": "LLM Quota Usage",
  "panels": [
    {
      "title": "Quota Usage by Provider",
      "targets": [
        {
          "expr": "llm_quota_usage_percent"
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Alerts Not Triggering

1. **Check if monitoring is running:**
   ```python
   print(f"Monitoring running: {manager._running}")
   ```

2. **Verify quota limit is set:**
   ```python
   quota = await manager.get_quota_usage(config_id)
   print(f"Quota limit: {quota.quota_limit}")
   ```

3. **Check alert handlers are registered:**
   ```python
   print(f"Alert handlers: {len(manager._alert_handlers)}")
   ```

### Alert Spam

Alerts are automatically rate-limited to once per hour per configuration. If you need to adjust this:

```python
# Modify the spam prevention window in _trigger_quota_alert
# Default: 3600 seconds (1 hour)
```

### Memory Usage

Quota cache is stored in memory. For large deployments, consider:

1. **Periodic cache cleanup:**
   ```python
   # Reset cache for inactive configurations
   await manager.reset_quota_cache(config_id)
   ```

2. **Persist to database:**
   ```python
   # Save quota info to database periodically
   async def persist_quotas():
       statuses = await manager.get_all_quota_statuses()
       await db.save_quota_statuses(statuses)
   ```

## Testing

See `tests/unit/test_llm_provider_manager.py` for comprehensive test examples:

```bash
# Run quota monitoring tests
pytest tests/unit/test_llm_provider_manager.py::TestQuotaMonitoring -v
```

## Example Application

See `examples/quota_monitoring_example.py` for a complete working example:

```bash
# Run the example
PYTHONPATH=. python3 examples/quota_monitoring_example.py
```

## Related Documentation

- [Admin Configuration Requirements](../.kiro/specs/admin-configuration/requirements.md)
- [Admin Configuration Design](../.kiro/specs/admin-configuration/design.md)
- [Async/Sync Safety Rules](../.kiro/steering/async-sync-safety.md)
- [LLM Provider Manager API](./api/llm_provider_manager.md)

## Support

For issues or questions:
- Check the [troubleshooting section](#troubleshooting)
- Review test cases in `tests/unit/test_llm_provider_manager.py`
- Consult the [design document](../.kiro/specs/admin-configuration/design.md)
