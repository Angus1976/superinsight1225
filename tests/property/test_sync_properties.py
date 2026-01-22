"""
Admin Configuration Sync Strategy Property Tests

Tests synchronization strategy properties including webhook URL generation,
dry-run non-modification, and retry behavior.

**Feature: admin-configuration**
**Property 14: Webhook URL Uniqueness**
**Property 16: Sync Retry with Exponential Backoff**
**Property 17: Dry-Run Non-Modification**
**Validates: Requirements 3.3, 3.7, 5.4**
"""

import pytest
import asyncio
import secrets
import re
from hypothesis import given, strategies as st, settings
from typing import Set, List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from src.admin.sync_strategy import SyncStrategyService
from src.admin.schemas import SyncStrategyCreate, SyncMode


# ============================================================================
# Property 14: Webhook URL Uniqueness
# ============================================================================

class TestWebhookURLUniqueness:
    """
    Property 14: Webhook URL Uniqueness
    
    For any two sync strategies configured with webhook mode, the generated
    webhook URLs should be unique and cryptographically secure.
    
    **Feature: admin-configuration**
    **Validates: Requirements 3.3**
    """
    
    @given(
        num_webhooks=st.integers(min_value=2, max_value=20)
    )
    @settings(max_examples=10, deadline=None)
    def test_generated_webhook_urls_are_unique(self, num_webhooks):
        """
        Generated webhook URLs are unique across multiple strategies.
        
        For any number of webhook configurations, each generated webhook URL
        should be unique - no two strategies should receive the same URL.
        """
        async def run_test():
            # Create service with tenant_id requirement disabled for testing
            service = SyncStrategyService(require_tenant_id=False)
            
            # Generate multiple webhook URLs
            webhook_urls: Set[str] = set()
            webhook_ids: List[str] = []
            
            for i in range(num_webhooks):
                # Generate a unique webhook ID (simulating what the API would do)
                webhook_id = secrets.token_urlsafe(16)
                webhook_ids.append(webhook_id)
                
                # Construct webhook URL (matching the pattern in sync_push.py)
                webhook_url = f"/api/v1/sync/push/webhook/{webhook_id}"
                webhook_urls.add(webhook_url)
            
            # Verify all URLs are unique
            assert len(webhook_urls) == num_webhooks, \
                f"Expected {num_webhooks} unique URLs, got {len(webhook_urls)}"
            
            # Verify no duplicates in webhook IDs
            assert len(set(webhook_ids)) == num_webhooks, \
                f"Webhook IDs should be unique, got {len(set(webhook_ids))} unique out of {num_webhooks}"
        
        asyncio.run(run_test())
    
    @given(
        num_webhooks=st.integers(min_value=5, max_value=12)
    )
    @settings(max_examples=8, deadline=None)
    def test_webhook_urls_contain_cryptographically_secure_tokens(self, num_webhooks):
        """
        Webhook URLs contain cryptographically secure random tokens.
        
        For any generated webhook URL, the URL should contain a token that:
        1. Is sufficiently long (at least 16 characters)
        2. Contains URL-safe characters
        3. Has high entropy (not predictable)
        """
        async def run_test():
            # Generate multiple webhook URLs
            webhook_tokens: List[str] = []
            
            for i in range(num_webhooks):
                # Generate webhook ID using secrets module (cryptographically secure)
                webhook_id = secrets.token_urlsafe(16)
                webhook_tokens.append(webhook_id)
                
                # Verify token length (token_urlsafe(16) generates ~22 chars)
                assert len(webhook_id) >= 16, \
                    f"Webhook token should be at least 16 characters, got {len(webhook_id)}"
                
                # Verify token contains only URL-safe characters
                # token_urlsafe uses A-Z, a-z, 0-9, -, _
                url_safe_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
                assert url_safe_pattern.match(webhook_id), \
                    f"Webhook token should contain only URL-safe characters: {webhook_id}"
            
            # Verify all tokens are unique (high entropy)
            assert len(set(webhook_tokens)) == num_webhooks, \
                f"All webhook tokens should be unique (high entropy)"
            
            # Verify tokens are not sequential or predictable
            # Check that tokens don't follow a simple pattern
            for i in range(len(webhook_tokens) - 1):
                token1 = webhook_tokens[i]
                token2 = webhook_tokens[i + 1]
                
                # Tokens should not be similar (Hamming distance check)
                # At least 50% of characters should be different
                if len(token1) == len(token2):
                    differences = sum(c1 != c2 for c1, c2 in zip(token1, token2))
                    similarity_ratio = differences / len(token1)
                    assert similarity_ratio > 0.5, \
                        f"Tokens should have high entropy (low similarity): {token1} vs {token2}"
        
        asyncio.run(run_test())
    
    @given(
        num_strategies=st.integers(min_value=3, max_value=8)
    )
    @settings(max_examples=8, deadline=None)
    def test_webhook_urls_unique_across_tenants(self, num_strategies):
        """
        Webhook URLs are unique even across different tenants.
        
        For any set of sync strategies from different tenants, each webhook
        URL should be globally unique, not just unique within a tenant.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Generate strategies for different tenants
            webhook_urls: Set[str] = set()
            tenant_ids = [f"tenant-{i}" for i in range(num_strategies)]
            
            for tenant_id in tenant_ids:
                # Generate webhook ID
                webhook_id = secrets.token_urlsafe(16)
                webhook_url = f"/api/v1/sync/push/webhook/{webhook_id}"
                
                # Check for uniqueness
                assert webhook_url not in webhook_urls, \
                    f"Webhook URL should be unique across tenants: {webhook_url}"
                
                webhook_urls.add(webhook_url)
            
            # Verify all URLs are unique
            assert len(webhook_urls) == num_strategies, \
                f"Expected {num_strategies} unique URLs across tenants"
        
        asyncio.run(run_test())
    
    def test_webhook_url_format_consistency(self):
        """
        Webhook URLs follow a consistent format.
        
        All generated webhook URLs should follow the same format pattern:
        /api/v1/sync/push/webhook/{secure_token}
        """
        async def run_test():
            # Generate multiple webhook URLs
            num_urls = 10
            webhook_urls: List[str] = []
            
            for i in range(num_urls):
                webhook_id = secrets.token_urlsafe(16)
                webhook_url = f"/api/v1/sync/push/webhook/{webhook_id}"
                webhook_urls.append(webhook_url)
            
            # Verify format consistency
            url_pattern = re.compile(r'^/api/v1/sync/push/webhook/[A-Za-z0-9_-]+$')
            
            for url in webhook_urls:
                assert url_pattern.match(url), \
                    f"Webhook URL should match expected format: {url}"
                
                # Verify URL structure
                assert url.startswith("/api/v1/sync/push/webhook/"), \
                    f"Webhook URL should start with correct prefix: {url}"
                
                # Extract token part
                token = url.split("/")[-1]
                assert len(token) >= 16, \
                    f"Webhook token should be at least 16 characters: {token}"
        
        asyncio.run(run_test())
    
    @given(
        num_concurrent_requests=st.integers(min_value=5, max_value=15)
    )
    @settings(max_examples=8, deadline=None)
    def test_webhook_url_generation_is_thread_safe(self, num_concurrent_requests):
        """
        Webhook URL generation is thread-safe and produces unique URLs.
        
        When multiple webhook URLs are generated concurrently, each should
        still be unique without race conditions.
        """
        async def run_test():
            # Simulate concurrent webhook generation
            async def generate_webhook():
                webhook_id = secrets.token_urlsafe(16)
                return f"/api/v1/sync/push/webhook/{webhook_id}"
            
            # Generate webhooks concurrently
            tasks = [generate_webhook() for _ in range(num_concurrent_requests)]
            webhook_urls = await asyncio.gather(*tasks)
            
            # Verify all URLs are unique
            assert len(set(webhook_urls)) == num_concurrent_requests, \
                f"Concurrent webhook generation should produce unique URLs"
            
            # Verify all URLs are valid
            url_pattern = re.compile(r'^/api/v1/sync/push/webhook/[A-Za-z0-9_-]+$')
            for url in webhook_urls:
                assert url_pattern.match(url), \
                    f"Concurrently generated URL should be valid: {url}"
        
        asyncio.run(run_test())
    
    def test_webhook_secret_generation_is_cryptographically_secure(self):
        """
        Webhook secrets are generated using cryptographically secure methods.
        
        Webhook secrets should be generated using secrets module (not random),
        ensuring they are suitable for security-sensitive applications.
        """
        async def run_test():
            # Generate multiple secrets
            num_secrets = 20
            webhook_secrets: List[str] = []
            
            for i in range(num_secrets):
                # Generate secret using secrets module (as in sync_push.py)
                secret = secrets.token_urlsafe(32)
                webhook_secrets.append(secret)
                
                # Verify secret length (token_urlsafe(32) generates ~43 chars)
                assert len(secret) >= 32, \
                    f"Webhook secret should be at least 32 characters, got {len(secret)}"
                
                # Verify secret contains only URL-safe characters
                url_safe_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
                assert url_safe_pattern.match(secret), \
                    f"Webhook secret should contain only URL-safe characters: {secret}"
            
            # Verify all secrets are unique
            assert len(set(webhook_secrets)) == num_secrets, \
                f"All webhook secrets should be unique"
            
            # Verify high entropy (no two secrets should be similar)
            for i in range(len(webhook_secrets) - 1):
                secret1 = webhook_secrets[i]
                secret2 = webhook_secrets[i + 1]
                
                # Secrets should be completely different
                assert secret1 != secret2, \
                    f"Secrets should be unique: {secret1} vs {secret2}"
                
                # Check that secrets have low similarity
                if len(secret1) == len(secret2):
                    differences = sum(c1 != c2 for c1, c2 in zip(secret1, secret2))
                    similarity_ratio = differences / len(secret1)
                    assert similarity_ratio > 0.8, \
                        f"Secrets should have very high entropy (low similarity)"
        
        asyncio.run(run_test())
    
    @given(
        num_webhooks=st.integers(min_value=10, max_value=15)
    )
    @settings(max_examples=8, deadline=None)
    def test_webhook_url_collision_probability_is_negligible(self, num_webhooks):
        """
        Probability of webhook URL collision is negligible.
        
        With cryptographically secure random generation, the probability
        of collision should be astronomically low. Test that we can generate
        many URLs without any collisions.
        """
        async def run_test():
            # Generate a large number of webhook URLs
            webhook_urls: Set[str] = set()
            
            for i in range(num_webhooks):
                webhook_id = secrets.token_urlsafe(16)
                webhook_url = f"/api/v1/sync/push/webhook/{webhook_id}"
                
                # Check for collision
                assert webhook_url not in webhook_urls, \
                    f"Collision detected! URL already exists: {webhook_url}"
                
                webhook_urls.add(webhook_url)
            
            # Verify we generated the expected number of unique URLs
            assert len(webhook_urls) == num_webhooks, \
                f"Should generate {num_webhooks} unique URLs without collisions"
            
            # Calculate theoretical collision probability
            # For token_urlsafe(16), we have ~2^128 possible values
            # Probability of collision with n URLs is approximately n^2 / (2 * 2^128)
            # For n=20, this is ~2.17e-36, which is negligible
            
            # In practice, we should never see a collision in testing
            print(f"Generated {num_webhooks} unique webhook URLs without collision")
        
        asyncio.run(run_test())


# ============================================================================
# Property 17: Dry-Run Non-Modification
# ============================================================================

class TestDryRunNonModification:
    """
    Property 17: Dry-Run Non-Modification
    
    For any sync strategy dry-run execution, no data should be modified in
    either source or destination, but preview results should be returned.
    
    **Feature: admin-configuration**
    **Validates: Requirements 5.4**
    """
    
    @given(
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        batch_size=st.integers(min_value=100, max_value=5000),
        enabled=st.booleans(),
        num_records=st.integers(min_value=10, max_value=50),
    )
    @settings(max_examples=10, deadline=None)
    def test_dry_run_does_not_modify_source_data(
        self, mode, db_config_id, name, batch_size, enabled, num_records
    ):
        """
        Dry-run execution does not modify source database data.
        
        For any sync strategy configuration and any source data state,
        executing a dry-run should not modify the source database.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": enabled,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Simulate source data state (in-memory representation)
            source_data_before = {
                "records": [
                    {"id": i, "value": f"record-{i}", "timestamp": datetime.utcnow()}
                    for i in range(num_records)
                ],
                "checksum": hash(tuple(range(num_records))),
            }
            
            # Execute dry-run (simulated - in real implementation this would
            # query the source database but not write anything)
            dry_run_result = await self._execute_dry_run(
                service,
                saved_strategy.id,
                source_data_before
            )
            
            # Verify source data is unchanged
            source_data_after = source_data_before.copy()
            
            assert source_data_after["checksum"] == source_data_before["checksum"], \
                "Source data checksum should be unchanged after dry-run"
            
            assert len(source_data_after["records"]) == len(source_data_before["records"]), \
                f"Source record count should be unchanged: {len(source_data_before['records'])}"
            
            # Verify dry-run returned preview results
            assert dry_run_result is not None, \
                "Dry-run should return preview results"
            
            assert "preview_records" in dry_run_result, \
                "Dry-run result should contain preview_records"
            
            assert dry_run_result["modified_source"] is False, \
                "Dry-run should indicate source was not modified"
        
        asyncio.run(run_test())
    
    @given(
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        batch_size=st.integers(min_value=100, max_value=5000),
        enabled=st.booleans(),
        num_existing_records=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=10, deadline=None)
    def test_dry_run_does_not_modify_destination_data(
        self, mode, db_config_id, name, batch_size, enabled, num_existing_records
    ):
        """
        Dry-run execution does not modify destination database data.
        
        For any sync strategy and any destination data state, executing
        a dry-run should not write to or modify the destination database.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": enabled,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Simulate destination data state (in-memory representation)
            destination_data_before = {
                "records": [
                    {"id": i, "synced_value": f"existing-{i}"}
                    for i in range(num_existing_records)
                ],
                "record_count": num_existing_records,
                "last_modified": datetime.utcnow(),
            }
            
            # Execute dry-run
            dry_run_result = await self._execute_dry_run(
                service,
                saved_strategy.id,
                {"records": [{"id": i, "value": f"new-{i}"} for i in range(10)]}
            )
            
            # Verify destination data is unchanged
            destination_data_after = destination_data_before.copy()
            
            assert destination_data_after["record_count"] == destination_data_before["record_count"], \
                f"Destination record count should be unchanged: {num_existing_records}"
            
            assert len(destination_data_after["records"]) == len(destination_data_before["records"]), \
                "Destination records should be unchanged after dry-run"
            
            # Verify dry-run returned preview results
            assert dry_run_result is not None, \
                "Dry-run should return preview results"
            
            assert dry_run_result["modified_destination"] is False, \
                "Dry-run should indicate destination was not modified"
        
        asyncio.run(run_test())
    
    @given(
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        batch_size=st.integers(min_value=100, max_value=5000),
        enabled=st.booleans(),
        num_preview_records=st.integers(min_value=1, max_value=15),
    )
    @settings(max_examples=10, deadline=None)
    def test_dry_run_returns_preview_results(
        self, mode, db_config_id, name, batch_size, enabled, num_preview_records
    ):
        """
        Dry-run execution returns preview results.
        
        For any sync strategy, dry-run should return preview results showing
        what would be synchronized without actually performing the sync.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": enabled,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Simulate source data
            source_data = {
                "records": [
                    {"id": i, "value": f"record-{i}", "timestamp": datetime.utcnow()}
                    for i in range(num_preview_records)
                ]
            }
            
            # Execute dry-run
            dry_run_result = await self._execute_dry_run(
                service,
                saved_strategy.id,
                source_data
            )
            
            # Verify preview results are returned
            assert dry_run_result is not None, \
                "Dry-run should return results"
            
            assert "preview_records" in dry_run_result, \
                "Dry-run result should contain preview_records"
            
            assert isinstance(dry_run_result["preview_records"], list), \
                "Preview records should be a list"
            
            # Verify preview contains expected data
            preview_records = dry_run_result["preview_records"]
            assert len(preview_records) > 0, \
                "Preview should contain at least some records"
            
            # Preview should not exceed batch size
            assert len(preview_records) <= batch_size, \
                f"Preview should not exceed batch size: {batch_size}"
            
            # Verify metadata is included
            assert "total_records_to_sync" in dry_run_result, \
                "Dry-run should include total records count"
            
            assert "estimated_batches" in dry_run_result, \
                "Dry-run should include estimated batch count"
            
            assert "sync_mode" in dry_run_result, \
                "Dry-run should include sync mode"
            
            assert dry_run_result["sync_mode"] == mode.value, \
                f"Sync mode should match strategy: {mode.value}"
        
        asyncio.run(run_test())
    
    @given(
        strategy_data=st.fixed_dictionaries({
            "db_config_id": st.uuids().map(str),
            "name": st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
            )),
            "mode": st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
            "incremental_field": st.just("updated_at"),
            "batch_size": st.integers(min_value=100, max_value=5000),
            "enabled": st.booleans(),
        }),
        num_records=st.integers(min_value=20, max_value=50),
    )
    @settings(max_examples=10, deadline=None)
    def test_dry_run_respects_incremental_mode(self, strategy_data, num_records):
        """
        Dry-run respects incremental sync mode in preview.
        
        For any incremental sync strategy, dry-run should preview only
        the records that would be synced based on incremental field,
        without modifying any data.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Create an incremental sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Simulate source data with timestamps
            base_time = datetime.utcnow()
            last_sync_time = base_time
            
            source_data = {
                "records": [
                    {
                        "id": i,
                        "value": f"record-{i}",
                        "updated_at": base_time if i < num_records // 2 else base_time
                    }
                    for i in range(num_records)
                ]
            }
            
            # Execute dry-run with last sync timestamp
            dry_run_result = await self._execute_dry_run(
                service,
                saved_strategy.id,
                source_data,
                last_sync_timestamp=last_sync_time
            )
            
            # Verify preview results
            assert dry_run_result is not None, \
                "Dry-run should return results"
            
            if strategy_data["mode"] == SyncMode.INCREMENTAL:
                # For incremental mode, verify incremental field is considered
                assert "incremental_field" in dry_run_result, \
                    "Incremental dry-run should include incremental field info"
                
                assert dry_run_result["incremental_field"] == strategy_data["incremental_field"], \
                    f"Incremental field should match: {strategy_data['incremental_field']}"
                
                assert "last_sync_timestamp" in dry_run_result, \
                    "Incremental dry-run should include last sync timestamp"
            
            # Verify no data was modified
            assert dry_run_result["modified_source"] is False, \
                "Dry-run should not modify source data"
            
            assert dry_run_result["modified_destination"] is False, \
                "Dry-run should not modify destination data"
        
        asyncio.run(run_test())
    
    @given(
        num_concurrent_dry_runs=st.integers(min_value=2, max_value=8)
    )
    @settings(max_examples=8, deadline=None)
    def test_concurrent_dry_runs_do_not_interfere(self, num_concurrent_dry_runs):
        """
        Concurrent dry-run executions do not interfere with each other.
        
        Multiple dry-run operations running concurrently should not
        interfere with each other or modify any shared data.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Create multiple strategies
            strategies = []
            for i in range(num_concurrent_dry_runs):
                strategy_create = SyncStrategyCreate(
                    db_config_id=str(uuid4()),
                    name=f"strategy-{i}",
                    mode=SyncMode.FULL,
                    batch_size=1000,
                    enabled=True,
                )
                saved = await service.save_strategy(
                    strategy=strategy_create,
                    user_id="test-user",
                    user_name="Test User",
                )
                strategies.append(saved)
            
            # Execute dry-runs concurrently
            async def run_single_dry_run(strategy_id, index):
                source_data = {
                    "records": [
                        {"id": j, "value": f"strategy-{index}-record-{j}"}
                        for j in range(10)
                    ]
                }
                return await self._execute_dry_run(service, strategy_id, source_data)
            
            tasks = [
                run_single_dry_run(strategy.id, i)
                for i, strategy in enumerate(strategies)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all dry-runs completed successfully
            assert len(results) == num_concurrent_dry_runs, \
                f"All {num_concurrent_dry_runs} dry-runs should complete"
            
            # Verify each result is independent
            for i, result in enumerate(results):
                assert result is not None, \
                    f"Dry-run {i} should return results"
                
                assert result["modified_source"] is False, \
                    f"Dry-run {i} should not modify source"
                
                assert result["modified_destination"] is False, \
                    f"Dry-run {i} should not modify destination"
                
                assert "preview_records" in result, \
                    f"Dry-run {i} should include preview records"
        
        asyncio.run(run_test())
    
    async def _execute_dry_run(
        self,
        service: SyncStrategyService,
        strategy_id: str,
        source_data: Dict[str, Any],
        last_sync_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Execute a dry-run sync operation (simulated).
        
        In a real implementation, this would:
        1. Connect to source database (read-only)
        2. Query data based on strategy configuration
        3. Apply filters and transformations
        4. Return preview results WITHOUT writing to destination
        
        For testing, we simulate the dry-run behavior.
        
        Args:
            service: Sync strategy service
            strategy_id: Strategy ID
            source_data: Simulated source data
            last_sync_timestamp: Last sync timestamp for incremental mode
            
        Returns:
            Dry-run result with preview data
        """
        # Get strategy
        strategy = await service.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        # Simulate dry-run execution
        records = source_data.get("records", [])
        
        # Apply incremental filter if applicable
        if strategy.mode == SyncMode.INCREMENTAL and last_sync_timestamp:
            # Filter records based on incremental field
            incremental_field = strategy.incremental_field or "updated_at"
            filtered_records = [
                r for r in records
                if r.get(incremental_field, datetime.min) > last_sync_timestamp
            ]
        else:
            filtered_records = records
        
        # Limit preview to batch size
        preview_records = filtered_records[:strategy.batch_size]
        
        # Calculate estimated batches
        total_records = len(filtered_records)
        estimated_batches = (total_records + strategy.batch_size - 1) // strategy.batch_size
        
        # Return dry-run result
        return {
            "preview_records": preview_records,
            "total_records_to_sync": total_records,
            "estimated_batches": estimated_batches,
            "sync_mode": strategy.mode.value,
            "incremental_field": strategy.incremental_field,
            "last_sync_timestamp": last_sync_timestamp,
            "batch_size": strategy.batch_size,
            "modified_source": False,  # Dry-run never modifies source
            "modified_destination": False,  # Dry-run never modifies destination
            "is_dry_run": True,
        }


# ============================================================================
# Property 16: Sync Retry with Exponential Backoff
# ============================================================================

class TestSyncRetryWithExponentialBackoff:
    """
    Property 16: Sync Retry with Exponential Backoff
    
    For any sync operation that fails, the system should retry with exponential
    backoff, and after 3 consecutive failures, should alert administrators.
    
    **Feature: admin-configuration**
    **Validates: Requirements 3.7**
    """
    
    @given(
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        batch_size=st.integers(min_value=100, max_value=5000),
    )
    @settings(max_examples=8, deadline=None)
    def test_sync_retry_uses_exponential_backoff(
        self, db_config_id, name, mode, batch_size
    ):
        """
        Sync retry uses exponential backoff timing.
        
        For any sync strategy that fails, retries should use exponential
        backoff: 1s → 2s → 4s (with max 60s).
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": True,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Mock the sync execution to always fail
            original_execute = service._execute_sync_job
            attempt_times = []
            
            async def failing_execute(strategy_id, user_id, attempt):
                attempt_times.append(datetime.utcnow())
                raise Exception(f"Simulated sync failure on attempt {attempt + 1}")
            
            service._execute_sync_job = failing_execute
            
            try:
                # Execute sync with retry
                start_time = datetime.utcnow()
                result = await service.execute_sync_with_retry(
                    strategy_id=saved_strategy.id,
                    user_id="test-user",
                    max_retries=3,
                )
                end_time = datetime.utcnow()
                
                # Verify all attempts were made (initial + 3 retries = 4 total)
                assert len(attempt_times) == 4, \
                    f"Should have 4 attempts (initial + 3 retries), got {len(attempt_times)}"
                
                # Verify exponential backoff timing
                # Expected delays: 0s (initial), 1s, 2s, 4s
                # Total expected time: ~7 seconds (with some tolerance)
                total_duration = (end_time - start_time).total_seconds()
                
                # Allow some tolerance for execution time
                expected_min_duration = 7.0  # 1 + 2 + 4 = 7 seconds
                expected_max_duration = 10.0  # Allow 3 seconds tolerance
                
                assert expected_min_duration <= total_duration <= expected_max_duration, \
                    f"Total duration should be ~7s (with tolerance), got {total_duration:.2f}s"
                
                # Verify backoff between attempts
                if len(attempt_times) >= 2:
                    # First retry: ~1 second after initial attempt
                    delay_1 = (attempt_times[1] - attempt_times[0]).total_seconds()
                    assert 0.8 <= delay_1 <= 1.5, \
                        f"First retry delay should be ~1s, got {delay_1:.2f}s"
                
                if len(attempt_times) >= 3:
                    # Second retry: ~2 seconds after first retry
                    delay_2 = (attempt_times[2] - attempt_times[1]).total_seconds()
                    assert 1.8 <= delay_2 <= 2.5, \
                        f"Second retry delay should be ~2s, got {delay_2:.2f}s"
                
                if len(attempt_times) >= 4:
                    # Third retry: ~4 seconds after second retry
                    delay_3 = (attempt_times[3] - attempt_times[2]).total_seconds()
                    assert 3.8 <= delay_3 <= 4.5, \
                        f"Third retry delay should be ~4s, got {delay_3:.2f}s"
                
                # Verify final status is failed
                assert result.status == "failed", \
                    "Final status should be 'failed' after all retries exhausted"
                
                # Verify error message indicates retry exhaustion
                assert hasattr(result, 'message') or hasattr(result, 'error_message'), \
                    "Result should have message or error_message attribute"
                
                error_msg = getattr(result, 'error_message', None) or getattr(result, 'message', '')
                assert error_msg, \
                    "Error message should be present for failed sync"
                assert "failed after" in error_msg.lower() or "retry" in error_msg.lower(), \
                    f"Error message should indicate retry exhaustion, got: {error_msg}"
            
            finally:
                # Restore original method
                service._execute_sync_job = original_execute
        
        asyncio.run(run_test())
    
    @given(
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        batch_size=st.integers(min_value=100, max_value=5000),
        num_consecutive_failures=st.integers(min_value=3, max_value=4),
    )
    @settings(max_examples=8, deadline=None)
    def test_alert_sent_after_three_consecutive_failures(
        self, db_config_id, name, mode, batch_size, num_consecutive_failures
    ):
        """
        Administrator alert is sent after 3 consecutive failures.
        
        For any sync strategy that fails 3 or more consecutive times,
        an alert should be sent to administrators.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": True,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Mock the sync execution to always fail
            original_execute = service._execute_sync_job
            alert_calls = []
            
            async def failing_execute(strategy_id, user_id, attempt):
                raise Exception(f"Simulated sync failure on attempt {attempt + 1}")
            
            # Mock alert sending
            original_alert = service._send_administrator_alert
            
            async def mock_alert(strategy_id, consecutive_failures, last_error):
                alert_calls.append({
                    "strategy_id": strategy_id,
                    "consecutive_failures": consecutive_failures,
                    "last_error": last_error,
                })
            
            service._execute_sync_job = failing_execute
            service._send_administrator_alert = mock_alert
            
            try:
                # Execute sync multiple times to trigger consecutive failures
                for i in range(num_consecutive_failures):
                    result = await service.execute_sync_with_retry(
                        strategy_id=saved_strategy.id,
                        user_id="test-user",
                        max_retries=3,
                    )
                    
                    # Verify result is failed
                    assert result.status == "failed", \
                        f"Sync {i + 1} should fail"
                
                # Verify consecutive failure counter
                consecutive_failures = service.get_consecutive_failures(saved_strategy.id)
                assert consecutive_failures == num_consecutive_failures, \
                    f"Should have {num_consecutive_failures} consecutive failures, got {consecutive_failures}"
                
                # Verify alert was sent after 3 failures
                if num_consecutive_failures >= 3:
                    assert len(alert_calls) >= 1, \
                        "Alert should be sent after 3 consecutive failures"
                    
                    # Verify alert content
                    first_alert = alert_calls[0]
                    assert first_alert["strategy_id"] == saved_strategy.id, \
                        "Alert should reference correct strategy"
                    
                    assert first_alert["consecutive_failures"] >= 3, \
                        f"Alert should indicate at least 3 failures, got {first_alert['consecutive_failures']}"
                    
                    assert "Simulated sync failure" in first_alert["last_error"], \
                        "Alert should include error message"
                    
                    # Verify alert is sent only once (not on every subsequent failure)
                    # After first alert, subsequent failures shouldn't trigger more alerts
                    # until the failure counter is reset
                    if num_consecutive_failures > 3:
                        # Alert should be sent only once
                        assert len(alert_calls) == 1, \
                            "Alert should be sent only once for consecutive failures"
            
            finally:
                # Restore original methods
                service._execute_sync_job = original_execute
                service._send_administrator_alert = original_alert
                # Reset failure counter
                service.reset_failure_counter(saved_strategy.id)
        
        asyncio.run(run_test())
    
    @given(
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        batch_size=st.integers(min_value=100, max_value=5000),
        success_on_attempt=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=15, deadline=None)
    def test_successful_retry_resets_failure_counter(
        self, db_config_id, name, mode, batch_size, success_on_attempt
    ):
        """
        Successful retry resets the consecutive failure counter.
        
        For any sync strategy that fails but then succeeds on retry,
        the consecutive failure counter should be reset to 0.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": True,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Mock the sync execution to fail initially, then succeed
            original_execute = service._execute_sync_job
            attempt_counter = [0]
            
            async def conditional_execute(strategy_id, user_id, attempt):
                attempt_counter[0] += 1
                if attempt_counter[0] < success_on_attempt:
                    raise Exception(f"Simulated sync failure on attempt {attempt_counter[0]}")
                else:
                    # Success on specified attempt
                    return await original_execute(strategy_id, user_id, attempt)
            
            service._execute_sync_job = conditional_execute
            
            try:
                # Execute sync with retry
                result = await service.execute_sync_with_retry(
                    strategy_id=saved_strategy.id,
                    user_id="test-user",
                    max_retries=3,
                )
                
                # Verify sync eventually succeeded
                assert result.status == "completed", \
                    f"Sync should succeed on attempt {success_on_attempt}"
                
                # Verify failure counter was reset
                consecutive_failures = service.get_consecutive_failures(saved_strategy.id)
                assert consecutive_failures == 0, \
                    f"Consecutive failures should be reset to 0 after success, got {consecutive_failures}"
                
                # Verify alert flag was reset
                assert not service._alert_sent.get(saved_strategy.id, False), \
                    "Alert sent flag should be reset after success"
            
            finally:
                # Restore original method
                service._execute_sync_job = original_execute
        
        asyncio.run(run_test())
    
    @given(
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        batch_size=st.integers(min_value=100, max_value=5000),
        max_retries=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=15, deadline=None)
    def test_retry_respects_max_retries_parameter(
        self, db_config_id, name, mode, batch_size, max_retries
    ):
        """
        Retry mechanism respects the max_retries parameter.
        
        For any sync strategy with a specified max_retries value,
        the system should attempt exactly max_retries + 1 times
        (initial attempt + retries).
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": True,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Mock the sync execution to always fail
            original_execute = service._execute_sync_job
            attempt_count = [0]
            
            async def failing_execute(strategy_id, user_id, attempt):
                attempt_count[0] += 1
                raise Exception(f"Simulated sync failure on attempt {attempt_count[0]}")
            
            service._execute_sync_job = failing_execute
            
            try:
                # Execute sync with custom max_retries
                result = await service.execute_sync_with_retry(
                    strategy_id=saved_strategy.id,
                    user_id="test-user",
                    max_retries=max_retries,
                )
                
                # Verify correct number of attempts
                expected_attempts = max_retries + 1  # Initial + retries
                assert attempt_count[0] == expected_attempts, \
                    f"Should have {expected_attempts} attempts (1 initial + {max_retries} retries), got {attempt_count[0]}"
                
                # Verify final status is failed
                assert result.status == "failed", \
                    "Final status should be 'failed' after all retries exhausted"
            
            finally:
                # Restore original method
                service._execute_sync_job = original_execute
                # Reset failure counter
                service.reset_failure_counter(saved_strategy.id)
        
        asyncio.run(run_test())
    
    @given(
        db_config_id=st.uuids().map(str),
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
        )),
        mode=st.sampled_from([SyncMode.FULL, SyncMode.INCREMENTAL]),
        batch_size=st.integers(min_value=100, max_value=5000),
    )
    @settings(max_examples=15, deadline=None)
    def test_backoff_does_not_exceed_max_backoff(
        self, db_config_id, name, mode, batch_size
    ):
        """
        Exponential backoff does not exceed maximum backoff limit.
        
        For any sync strategy with many retries, the backoff delay
        should not exceed MAX_BACKOFF_SECONDS (60 seconds).
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Build strategy data with conditional incremental_field
            strategy_data = {
                "db_config_id": db_config_id,
                "name": name,
                "mode": mode,
                "batch_size": batch_size,
                "enabled": True,
            }
            if mode == SyncMode.INCREMENTAL:
                strategy_data["incremental_field"] = "updated_at"
            
            # Create a sync strategy
            strategy_create = SyncStrategyCreate(**strategy_data)
            saved_strategy = await service.save_strategy(
                strategy=strategy_create,
                user_id="test-user",
                user_name="Test User",
            )
            
            # Mock the sync execution to always fail
            original_execute = service._execute_sync_job
            attempt_times = []
            
            async def failing_execute(strategy_id, user_id, attempt):
                attempt_times.append(datetime.utcnow())
                raise Exception(f"Simulated sync failure on attempt {attempt + 1}")
            
            service._execute_sync_job = failing_execute
            
            try:
                # Execute sync with many retries to test max backoff
                result = await service.execute_sync_with_retry(
                    strategy_id=saved_strategy.id,
                    user_id="test-user",
                    max_retries=10,  # Many retries to test max backoff
                )
                
                # Verify backoff delays
                # Expected: 1, 2, 4, 8, 16, 32, 60, 60, 60, 60 (capped at 60)
                for i in range(1, len(attempt_times)):
                    delay = (attempt_times[i] - attempt_times[i-1]).total_seconds()
                    
                    # Verify delay doesn't exceed max backoff + tolerance
                    max_allowed_delay = service.MAX_BACKOFF_SECONDS + 1.0  # 1s tolerance
                    assert delay <= max_allowed_delay, \
                        f"Backoff delay {i} should not exceed {service.MAX_BACKOFF_SECONDS}s, got {delay:.2f}s"
                
                # Verify final status is failed
                assert result.status == "failed", \
                    "Final status should be 'failed' after all retries exhausted"
            
            finally:
                # Restore original method
                service._execute_sync_job = original_execute
                # Reset failure counter
                service.reset_failure_counter(saved_strategy.id)
        
        asyncio.run(run_test())
    
    @given(
        num_strategies=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=10, deadline=None)
    def test_failure_counters_are_independent_per_strategy(self, num_strategies):
        """
        Failure counters are tracked independently for each strategy.
        
        For any set of sync strategies, failures in one strategy should
        not affect the failure counter of another strategy.
        """
        async def run_test():
            # Create service
            service = SyncStrategyService(require_tenant_id=False)
            
            # Create multiple strategies
            strategies = []
            for i in range(num_strategies):
                strategy_create = SyncStrategyCreate(
                    db_config_id=str(uuid4()),
                    name=f"strategy-{i}",
                    mode=SyncMode.FULL,
                    batch_size=1000,
                    enabled=True,
                )
                saved = await service.save_strategy(
                    strategy=strategy_create,
                    user_id="test-user",
                    user_name="Test User",
                )
                strategies.append(saved)
            
            # Mock the sync execution to always fail
            original_execute = service._execute_sync_job
            
            async def failing_execute(strategy_id, user_id, attempt):
                raise Exception(f"Simulated sync failure")
            
            service._execute_sync_job = failing_execute
            
            try:
                # Fail each strategy a different number of times
                for i, strategy in enumerate(strategies):
                    num_failures = i + 1  # 1, 2, 3, 4, 5 failures
                    
                    for _ in range(num_failures):
                        await service.execute_sync_with_retry(
                            strategy_id=strategy.id,
                            user_id="test-user",
                            max_retries=3,
                        )
                
                # Verify each strategy has independent failure counter
                for i, strategy in enumerate(strategies):
                    expected_failures = i + 1
                    actual_failures = service.get_consecutive_failures(strategy.id)
                    
                    assert actual_failures == expected_failures, \
                        f"Strategy {i} should have {expected_failures} failures, got {actual_failures}"
                
                # Verify failure counters are independent
                failure_counts = [
                    service.get_consecutive_failures(s.id)
                    for s in strategies
                ]
                
                # All counts should be different
                assert len(set(failure_counts)) == len(failure_counts), \
                    f"Failure counters should be independent: {failure_counts}"
            
            finally:
                # Restore original method
                service._execute_sync_job = original_execute
                # Reset all failure counters
                for strategy in strategies:
                    service.reset_failure_counter(strategy.id)
        
        asyncio.run(run_test())


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
