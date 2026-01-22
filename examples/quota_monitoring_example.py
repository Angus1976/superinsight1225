"""
Example: LLM Provider Quota Monitoring

This example demonstrates how to use the quota monitoring functionality
in the LLMProviderManager to track API usage and receive alerts when
approaching quota limits.

Validates Requirements: 10.4
"""

import asyncio
import logging
from datetime import datetime

from src.admin.llm_provider_manager import LLMProviderManager, QuotaInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def quota_alert_handler(config_id: str, quota: QuotaInfo):
    """
    Alert handler that gets called when quota threshold is reached.
    
    This is where you would integrate with your notification system
    (email, Slack, SMS, etc.)
    """
    usage_percent = (quota.total_tokens / quota.quota_limit) * 100 if quota.quota_limit else 0
    
    logger.warning(
        f"⚠️  QUOTA ALERT for {config_id}:\n"
        f"   Provider: {quota.provider}\n"
        f"   Usage: {quota.total_tokens:,} / {quota.quota_limit:,} tokens ({usage_percent:.1f}%)\n"
        f"   Threshold: {quota.alert_threshold_percent}%\n"
        f"   Requests: {quota.total_requests} (Success: {quota.successful_requests}, Failed: {quota.failed_requests})\n"
        f"   Last Updated: {quota.last_updated}"
    )
    
    # Here you could send notifications via:
    # - Email (SMTP)
    # - Slack webhook
    # - SMS (Twilio)
    # - PagerDuty
    # - Custom webhook
    # await send_email_alert(config_id, quota)
    # await send_slack_alert(config_id, quota)


async def simulate_api_usage(manager: LLMProviderManager, config_id: str, provider: str):
    """Simulate API usage for demonstration."""
    logger.info(f"Simulating API usage for {config_id}...")
    
    # Simulate 10 API calls with varying token usage
    for i in range(10):
        tokens = 800 + (i * 100)  # Increasing token usage
        success = i % 10 != 9  # Last one fails
        
        await manager.update_quota_usage(
            config_id=config_id,
            provider=provider,
            tokens_used=tokens,
            success=success
        )
        
        logger.info(f"  API call {i+1}: {tokens} tokens, success={success}")
        await asyncio.sleep(0.1)  # Small delay between calls


async def main():
    """Main example function."""
    logger.info("=== LLM Provider Quota Monitoring Example ===\n")
    
    # Initialize the manager
    manager = LLMProviderManager()
    
    # Register alert handler
    manager.add_alert_handler(quota_alert_handler)
    logger.info("✓ Registered quota alert handler\n")
    
    # Configure quota limits for different providers
    configs = [
        ("openai-prod", "openai", 10000, 80.0),
        ("anthropic-dev", "anthropic", 5000, 75.0),
        ("ollama-local", "ollama", 20000, 90.0),
    ]
    
    logger.info("Configuring quota limits:")
    for config_id, provider, limit, threshold in configs:
        # Initialize quota tracking
        await manager.update_quota_usage(config_id, provider, 0, True)
        
        # Set quota limit and alert threshold
        await manager.set_quota_limit(config_id, limit, threshold)
        
        logger.info(f"  {config_id}: {limit:,} tokens, {threshold}% threshold")
    
    logger.info("")
    
    # Start background monitoring (checks every 5 seconds for demo)
    await manager.start_monitoring(interval=5)
    logger.info("✓ Started background quota monitoring (5s interval)\n")
    
    # Simulate API usage for OpenAI config (will trigger alert)
    await simulate_api_usage(manager, "openai-prod", "openai")
    logger.info("")
    
    # Display quota status for all configurations
    logger.info("Current quota status:")
    statuses = await manager.get_all_quota_statuses()
    
    for status in statuses:
        logger.info(
            f"\n  {status['config_id']} ({status['provider']}):\n"
            f"    Tokens: {status['total_tokens']:,} / {status['quota_limit']:,}\n"
            f"    Usage: {status['usage_percent']:.1f}%\n"
            f"    Alert Triggered: {status['alert_triggered']}\n"
            f"    Requests: {status['total_requests']} "
            f"(Success: {status['successful_requests']}, Failed: {status['failed_requests']})"
        )
    
    logger.info("\n")
    
    # Wait for monitoring to check quotas
    logger.info("Waiting for monitoring loop to check quotas...")
    await asyncio.sleep(6)
    
    # Get detailed status for specific config
    logger.info("\nDetailed status for openai-prod:")
    detailed_status = await manager.get_quota_status("openai-prod")
    if detailed_status:
        for key, value in detailed_status.items():
            logger.info(f"  {key}: {value}")
    
    # Stop monitoring
    await manager.stop_monitoring()
    logger.info("\n✓ Stopped quota monitoring")
    
    logger.info("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
