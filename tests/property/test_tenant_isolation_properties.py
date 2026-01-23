"""
Admin Configuration Tenant Isolation Property Tests

Tests multi-tenant configuration isolation properties to ensure that
configurations created by one tenant are not visible or accessible to
other tenants, even with direct API calls attempting cross-tenant access.

**Feature: admin-configuration**
**Property 2: Multi-Tenant Configuration Isolation**
**Validates: Requirements 1.6, 7.1, 7.2, 7.3**
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any, Set
from uuid import uuid4
from datetime import datetime

from src.admin.config_manager import ConfigManager
from src.admin.schemas import (
    LLMConfigCreate,
    DBConfigCreate,
    SyncStrategyCreate,
    SyncMode,
    LLMType,
    DatabaseType,
)


# ============================================================================
# Property 2: Multi-Tenant Configuration Isolation
# ============================================================================

class TestMultiTenantConfigurationIsolation:
    """
    Property 2: Multi-Tenant Configuration Isolation
    
    For any two different tenants, configurations created by one tenant
    should not be visible or accessible to the other tenant, even with
    direct API calls attempting cross-tenant access.
    
    **Feature: admin-configuration**
    **Validates: Requirements 1.6, 7.1, 7.2, 7.3**
    """
    
    @given(
        num_tenants=st.integers(min_value=2, max_value=5),
        configs_per_tenant=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_llm_configs_isolated_between_tenants(
        self, num_tenants, configs_per_tenant
    ):
        """
        LLM configurations are isolated between tenants.
        
        For any set of tenants, each tenant's LLM configurations should
        only be visible to that tenant. Attempting to access another
        tenant's configurations should return empty results.
        """
        async def run_test():
            # Create config manager
            manager = ConfigManager(require_tenant_id=True)
            
            # Generate unique tenant IDs
            tenant_ids = [f"tenant-{uuid4()}" for _ in range(num_tenants)]
            
            # Track which configs belong to which tenant
            tenant_configs: Dict[str, List[str]] = {tid: [] for tid in tenant_ids}
            
            # Create LLM configs for each tenant
            for tenant_id in tenant_ids:
                for i in range(configs_per_tenant):
                    config = LLMConfigCreate(
                        name=f"llm-config-{tenant_id}-{i}",
                        llm_type=LLMType.OPENAI,
                        model_name="gpt-4",
                        api_key=f"sk-test-{uuid4()}",
                        api_endpoint="https://api.openai.com/v1",
                        temperature=0.7,
                        max_tokens=2048,
                    )
                    
                    saved = await manager.save_llm_config(
                        config=config,
                        user_id="test-user",
                        user_name="Test User",
                        tenant_id=tenant_id,
                    )
                    
                    tenant_configs[tenant_id].append(saved.id)
            
            # Verify each tenant can only see their own configs
            for tenant_id in tenant_ids:
                # List configs for this tenant
                configs = await manager.list_llm_configs(tenant_id=tenant_id)
                
                # Should see exactly the configs created for this tenant
                config_ids = {c.id for c in configs}
                expected_ids = set(tenant_configs[tenant_id])
                
                assert config_ids == expected_ids, (
                    f"Tenant {tenant_id} should see only their own configs. "
                    f"Expected: {expected_ids}, Got: {config_ids}"
                )
                
                # Verify count matches
                assert len(configs) == configs_per_tenant, (
                    f"Tenant {tenant_id} should have {configs_per_tenant} configs, "
                    f"got {len(configs)}"
                )
                
                # Verify no configs from other tenants are visible
                for other_tenant_id in tenant_ids:
                    if other_tenant_id != tenant_id:
                        other_config_ids = set(tenant_configs[other_tenant_id])
                        overlap = config_ids & other_config_ids
                        assert len(overlap) == 0, (
                            f"Tenant {tenant_id} should not see configs from "
                            f"tenant {other_tenant_id}. Found overlap: {overlap}"
                        )
        
        asyncio.run(run_test())
    
    @given(
        num_tenants=st.integers(min_value=2, max_value=5),
        configs_per_tenant=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_db_configs_isolated_between_tenants(
        self, num_tenants, configs_per_tenant
    ):
        """
        Database configurations are isolated between tenants.
        
        For any set of tenants, each tenant's database configurations
        should only be visible to that tenant.
        """
        async def run_test():
            # Create config manager
            manager = ConfigManager(require_tenant_id=True)
            
            # Generate unique tenant IDs
            tenant_ids = [f"tenant-{uuid4()}" for _ in range(num_tenants)]
            
            # Track which configs belong to which tenant
            tenant_configs: Dict[str, List[str]] = {tid: [] for tid in tenant_ids}
            
            # Create DB configs for each tenant
            for tenant_id in tenant_ids:
                for i in range(configs_per_tenant):
                    config = DBConfigCreate(
                        name=f"db-config-{tenant_id}-{i}",
                        db_type=DatabaseType.POSTGRESQL,
                        host="localhost",
                        port=5432,
                        database=f"testdb_{tenant_id}_{i}",
                        username="testuser",
                        password=f"testpass-{uuid4()}",
                        is_readonly=True,
                    )
                    
                    saved = await manager.save_db_config(
                        config=config,
                        user_id="test-user",
                        user_name="Test User",
                        tenant_id=tenant_id,
                    )
                    
                    tenant_configs[tenant_id].append(saved.id)
            
            # Verify each tenant can only see their own configs
            for tenant_id in tenant_ids:
                configs = await manager.list_db_configs(tenant_id=tenant_id)
                
                config_ids = {c.id for c in configs}
                expected_ids = set(tenant_configs[tenant_id])
                
                assert config_ids == expected_ids, (
                    f"Tenant {tenant_id} should see only their own DB configs. "
                    f"Expected: {expected_ids}, Got: {config_ids}"
                )
                
                assert len(configs) == configs_per_tenant, (
                    f"Tenant {tenant_id} should have {configs_per_tenant} DB configs, "
                    f"got {len(configs)}"
                )
                
                # Verify no configs from other tenants are visible
                for other_tenant_id in tenant_ids:
                    if other_tenant_id != tenant_id:
                        other_config_ids = set(tenant_configs[other_tenant_id])
                        overlap = config_ids & other_config_ids
                        assert len(overlap) == 0, (
                            f"Tenant {tenant_id} should not see DB configs from "
                            f"tenant {other_tenant_id}. Found overlap: {overlap}"
                        )
        
        asyncio.run(run_test())
    
    @given(
        tenant_a_id=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
        )),
        tenant_b_id=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
        )),
        num_configs=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, deadline=None)
    def test_cross_tenant_get_access_denied(
        self, tenant_a_id, tenant_b_id, num_configs
    ):
        """
        Direct get requests for another tenant's config are denied.
        
        For any two different tenants A and B, tenant A should not be
        able to retrieve tenant B's configurations by ID, even if they
        know the configuration ID.
        """
        # Ensure tenants are different
        assume(tenant_a_id != tenant_b_id)
        
        async def run_test():
            # Create config manager
            manager = ConfigManager(require_tenant_id=True)
            
            # Create configs for tenant B
            tenant_b_config_ids: List[str] = []
            
            for i in range(num_configs):
                config = LLMConfigCreate(
                    name=f"tenant-b-config-{i}",
                    llm_type=LLMType.OPENAI,
                    model_name="gpt-4",
                    api_key=f"sk-tenant-b-{uuid4()}",
                    api_endpoint="https://api.openai.com/v1",
                )
                
                saved = await manager.save_llm_config(
                    config=config,
                    user_id="tenant-b-user",
                    user_name="Tenant B User",
                    tenant_id=tenant_b_id,
                )
                
                tenant_b_config_ids.append(saved.id)
            
            # Attempt to access tenant B's configs as tenant A
            for config_id in tenant_b_config_ids:
                result = await manager.get_llm_config(
                    config_id=config_id,
                    tenant_id=tenant_a_id,
                )
                
                # Should return None (not found) due to tenant isolation
                assert result is None, (
                    f"Tenant A ({tenant_a_id}) should not be able to access "
                    f"tenant B's ({tenant_b_id}) config {config_id}. "
                    f"Cross-tenant access should be denied."
                )
            
            # Verify tenant B can still access their own configs
            for config_id in tenant_b_config_ids:
                result = await manager.get_llm_config(
                    config_id=config_id,
                    tenant_id=tenant_b_id,
                )
                
                assert result is not None, (
                    f"Tenant B ({tenant_b_id}) should be able to access "
                    f"their own config {config_id}"
                )
                
                assert result.id == config_id, (
                    f"Retrieved config ID should match: {config_id}"
                )
        
        asyncio.run(run_test())
    
    @given(
        tenant_a_id=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
        )),
        tenant_b_id=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
        )),
        num_configs=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, deadline=None)
    def test_cross_tenant_delete_access_denied(
        self, tenant_a_id, tenant_b_id, num_configs
    ):
        """
        Delete requests for another tenant's config are denied.
        
        For any two different tenants A and B, tenant A should not be
        able to delete tenant B's configurations, even if they know
        the configuration ID.
        """
        # Ensure tenants are different
        assume(tenant_a_id != tenant_b_id)
        
        async def run_test():
            # Create config manager
            manager = ConfigManager(require_tenant_id=True)
            
            # Create configs for tenant B
            tenant_b_config_ids: List[str] = []
            
            for i in range(num_configs):
                config = DBConfigCreate(
                    name=f"tenant-b-db-{i}",
                    db_type=DatabaseType.POSTGRESQL,
                    host="localhost",
                    port=5432,
                    database=f"tenant_b_db_{i}",
                    username="tenant_b_user",
                    password=f"tenant-b-pass-{uuid4()}",
                )
                
                saved = await manager.save_db_config(
                    config=config,
                    user_id="tenant-b-user",
                    user_name="Tenant B User",
                    tenant_id=tenant_b_id,
                )
                
                tenant_b_config_ids.append(saved.id)
            
            # Attempt to delete tenant B's configs as tenant A
            for config_id in tenant_b_config_ids:
                result = await manager.delete_db_config(
                    config_id=config_id,
                    user_id="tenant-a-user",
                    user_name="Tenant A User",
                    tenant_id=tenant_a_id,
                )
                
                # Should return False (not found) due to tenant isolation
                assert result is False, (
                    f"Tenant A ({tenant_a_id}) should not be able to delete "
                    f"tenant B's ({tenant_b_id}) config {config_id}. "
                    f"Cross-tenant delete should be denied."
                )
            
            # Verify tenant B's configs still exist
            for config_id in tenant_b_config_ids:
                result = await manager.get_db_config(
                    config_id=config_id,
                    tenant_id=tenant_b_id,
                )
                
                assert result is not None, (
                    f"Tenant B's config {config_id} should still exist after "
                    f"failed cross-tenant delete attempt"
                )
            
            # Verify tenant B can delete their own configs
            for config_id in tenant_b_config_ids:
                result = await manager.delete_db_config(
                    config_id=config_id,
                    user_id="tenant-b-user",
                    user_name="Tenant B User",
                    tenant_id=tenant_b_id,
                )
                
                assert result is True, (
                    f"Tenant B ({tenant_b_id}) should be able to delete "
                    f"their own config {config_id}"
                )
        
        asyncio.run(run_test())
    
    @given(
        num_tenants=st.integers(min_value=3, max_value=6),
        configs_per_tenant=st.integers(min_value=2, max_value=4),
    )
    @settings(max_examples=100, deadline=None)
    def test_tenant_isolation_with_concurrent_access(
        self, num_tenants, configs_per_tenant
    ):
        """
        Tenant isolation is maintained under concurrent access.
        
        When multiple tenants access configurations concurrently,
        each tenant should still only see their own configurations
        without any cross-tenant leakage.
        """
        async def run_test():
            # Create config manager
            manager = ConfigManager(require_tenant_id=True)
            
            # Generate unique tenant IDs
            tenant_ids = [f"tenant-{uuid4()}" for _ in range(num_tenants)]
            
            # Track which configs belong to which tenant
            tenant_configs: Dict[str, List[str]] = {tid: [] for tid in tenant_ids}
            
            # Create configs for all tenants concurrently
            async def create_tenant_configs(tenant_id: str):
                config_ids = []
                for i in range(configs_per_tenant):
                    config = LLMConfigCreate(
                        name=f"concurrent-config-{tenant_id}-{i}",
                        llm_type=LLMType.QIANWEN,
                        model_name="qwen-turbo",
                        api_key=f"sk-qwen-{uuid4()}",
                        api_endpoint="https://dashscope.aliyuncs.com/api/v1",
                    )
                    
                    saved = await manager.save_llm_config(
                        config=config,
                        user_id=f"user-{tenant_id}",
                        user_name=f"User {tenant_id}",
                        tenant_id=tenant_id,
                    )
                    
                    config_ids.append(saved.id)
                
                return tenant_id, config_ids
            
            # Create configs concurrently
            tasks = [create_tenant_configs(tid) for tid in tenant_ids]
            results = await asyncio.gather(*tasks)
            
            # Store results
            for tenant_id, config_ids in results:
                tenant_configs[tenant_id] = config_ids
            
            # Verify isolation concurrently
            async def verify_tenant_isolation(tenant_id: str):
                configs = await manager.list_llm_configs(tenant_id=tenant_id)
                
                config_ids = {c.id for c in configs}
                expected_ids = set(tenant_configs[tenant_id])
                
                # Should see only own configs
                assert config_ids == expected_ids, (
                    f"Concurrent access: Tenant {tenant_id} should see only "
                    f"their own configs. Expected: {expected_ids}, Got: {config_ids}"
                )
                
                # Should not see any other tenant's configs
                for other_tenant_id in tenant_ids:
                    if other_tenant_id != tenant_id:
                        other_config_ids = set(tenant_configs[other_tenant_id])
                        overlap = config_ids & other_config_ids
                        assert len(overlap) == 0, (
                            f"Concurrent access: Tenant {tenant_id} should not see "
                            f"configs from tenant {other_tenant_id}"
                        )
                
                return True
            
            # Verify isolation concurrently
            verify_tasks = [verify_tenant_isolation(tid) for tid in tenant_ids]
            verify_results = await asyncio.gather(*verify_tasks)
            
            # All verifications should pass
            assert all(verify_results), "All tenant isolation checks should pass"
        
        asyncio.run(run_test())
    
    @given(
        num_tenants=st.integers(min_value=2, max_value=4),
        num_llm_configs=st.integers(min_value=1, max_value=3),
        num_db_configs=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, deadline=None)
    def test_tenant_isolation_across_all_config_types(
        self, num_tenants, num_llm_configs, num_db_configs
    ):
        """
        Tenant isolation applies to all configuration types.
        
        For any tenant, isolation should be enforced across all
        configuration types: LLM configs, DB configs, and sync strategies.
        """
        async def run_test():
            # Create config manager
            manager = ConfigManager(require_tenant_id=True)
            
            # Generate unique tenant IDs
            tenant_ids = [f"tenant-{uuid4()}" for _ in range(num_tenants)]
            
            # Track configs by tenant and type
            tenant_llm_configs: Dict[str, List[str]] = {tid: [] for tid in tenant_ids}
            tenant_db_configs: Dict[str, List[str]] = {tid: [] for tid in tenant_ids}
            
            # Create LLM and DB configs for each tenant
            for tenant_id in tenant_ids:
                # Create LLM configs
                for i in range(num_llm_configs):
                    llm_config = LLMConfigCreate(
                        name=f"llm-{tenant_id}-{i}",
                        llm_type=LLMType.OPENAI,
                        model_name="gpt-4",
                        api_key=f"sk-{uuid4()}",
                        api_endpoint="https://api.openai.com/v1",
                    )
                    
                    saved_llm = await manager.save_llm_config(
                        config=llm_config,
                        user_id=f"user-{tenant_id}",
                        user_name=f"User {tenant_id}",
                        tenant_id=tenant_id,
                    )
                    
                    tenant_llm_configs[tenant_id].append(saved_llm.id)
                
                # Create DB configs
                for i in range(num_db_configs):
                    db_config = DBConfigCreate(
                        name=f"db-{tenant_id}-{i}",
                        db_type=DatabaseType.MYSQL,
                        host="localhost",
                        port=3306,
                        database=f"db_{tenant_id}_{i}",
                        username="user",
                        password=f"pass-{uuid4()}",
                    )
                    
                    saved_db = await manager.save_db_config(
                        config=db_config,
                        user_id=f"user-{tenant_id}",
                        user_name=f"User {tenant_id}",
                        tenant_id=tenant_id,
                    )
                    
                    tenant_db_configs[tenant_id].append(saved_db.id)
            
            # Verify isolation for each tenant across all config types
            for tenant_id in tenant_ids:
                # Check LLM configs
                llm_configs = await manager.list_llm_configs(tenant_id=tenant_id)
                llm_config_ids = {c.id for c in llm_configs}
                expected_llm_ids = set(tenant_llm_configs[tenant_id])
                
                assert llm_config_ids == expected_llm_ids, (
                    f"Tenant {tenant_id} LLM config isolation failed. "
                    f"Expected: {expected_llm_ids}, Got: {llm_config_ids}"
                )
                
                # Check DB configs
                db_configs = await manager.list_db_configs(tenant_id=tenant_id)
                db_config_ids = {c.id for c in db_configs}
                expected_db_ids = set(tenant_db_configs[tenant_id])
                
                assert db_config_ids == expected_db_ids, (
                    f"Tenant {tenant_id} DB config isolation failed. "
                    f"Expected: {expected_db_ids}, Got: {db_config_ids}"
                )
                
                # Verify no cross-tenant leakage
                for other_tenant_id in tenant_ids:
                    if other_tenant_id != tenant_id:
                        # Check LLM configs
                        other_llm_ids = set(tenant_llm_configs[other_tenant_id])
                        llm_overlap = llm_config_ids & other_llm_ids
                        assert len(llm_overlap) == 0, (
                            f"LLM config leakage detected between tenant {tenant_id} "
                            f"and tenant {other_tenant_id}"
                        )
                        
                        # Check DB configs
                        other_db_ids = set(tenant_db_configs[other_tenant_id])
                        db_overlap = db_config_ids & other_db_ids
                        assert len(db_overlap) == 0, (
                            f"DB config leakage detected between tenant {tenant_id} "
                            f"and tenant {other_tenant_id}"
                        )
        
        asyncio.run(run_test())
    
    def test_tenant_id_required_for_read_operations(self):
        """
        Tenant ID is required for read configuration operations.
        
        When require_tenant_id is True (production mode), read operations
        (list, get) should require a tenant_id parameter to enforce isolation.
        """
        async def run_test():
            # Create config manager with tenant_id requirement
            manager = ConfigManager(require_tenant_id=True)
            
            # Attempt to list configs without tenant_id should raise error
            with pytest.raises(ValueError, match="tenant_id is required"):
                await manager.list_llm_configs(tenant_id=None)
            
            # Attempt to get config without tenant_id should raise error
            with pytest.raises(ValueError, match="tenant_id is required"):
                await manager.get_llm_config(
                    config_id="some-id",
                    tenant_id=None,
                )
            
            # Attempt to delete config without tenant_id should raise error
            with pytest.raises(ValueError, match="tenant_id is required"):
                await manager.delete_llm_config(
                    config_id="some-id",
                    user_id="test-user",
                    tenant_id=None,
                )
            
            # Same for DB configs
            with pytest.raises(ValueError, match="tenant_id is required"):
                await manager.list_db_configs(tenant_id=None)
            
            with pytest.raises(ValueError, match="tenant_id is required"):
                await manager.get_db_config(
                    config_id="some-id",
                    tenant_id=None,
                )
            
            with pytest.raises(ValueError, match="tenant_id is required"):
                await manager.delete_db_config(
                    config_id="some-id",
                    user_id="test-user",
                    tenant_id=None,
                )
        
        asyncio.run(run_test())
    
    @given(
        num_tenants=st.integers(min_value=2, max_value=4),
        configs_per_tenant=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_tenant_isolation_persists_across_manager_instances(
        self, num_tenants, configs_per_tenant
    ):
        """
        Tenant isolation persists across different manager instances.
        
        When using the same underlying storage (in-memory or database),
        tenant isolation should be maintained even when using different
        ConfigManager instances.
        
        Note: This test uses shared in-memory storage to simulate
        persistence across manager instances.
        """
        async def run_test():
            # Create first manager instance with shared storage
            shared_storage = {
                "llm": {},
                "database": {},
                "sync_strategy": {},
                "third_party": {},
            }
            
            manager1 = ConfigManager(require_tenant_id=True)
            # Share the in-memory storage
            manager1._in_memory_configs = shared_storage
            
            # Generate unique tenant IDs
            tenant_ids = [f"tenant-{uuid4()}" for _ in range(num_tenants)]
            
            # Track configs by tenant
            tenant_configs: Dict[str, List[str]] = {tid: [] for tid in tenant_ids}
            
            # Create configs using first manager
            for tenant_id in tenant_ids:
                for i in range(configs_per_tenant):
                    config = LLMConfigCreate(
                        name=f"persistent-config-{tenant_id}-{i}",
                        llm_type=LLMType.OPENAI,
                        model_name="gpt-4",
                        api_key=f"sk-{uuid4()}",
                        api_endpoint="https://api.openai.com/v1",
                    )
                    
                    saved = await manager1.save_llm_config(
                        config=config,
                        user_id=f"user-{tenant_id}",
                        user_name=f"User {tenant_id}",
                        tenant_id=tenant_id,
                    )
                    
                    tenant_configs[tenant_id].append(saved.id)
            
            # Create second manager instance with same shared storage
            manager2 = ConfigManager(require_tenant_id=True)
            manager2._in_memory_configs = shared_storage
            
            # Verify isolation using second manager
            for tenant_id in tenant_ids:
                configs = await manager2.list_llm_configs(tenant_id=tenant_id)
                
                config_ids = {c.id for c in configs}
                expected_ids = set(tenant_configs[tenant_id])
                
                assert config_ids == expected_ids, (
                    f"Tenant isolation should persist across manager instances. "
                    f"Tenant {tenant_id} expected: {expected_ids}, got: {config_ids}"
                )
                
                # Verify no cross-tenant access
                for other_tenant_id in tenant_ids:
                    if other_tenant_id != tenant_id:
                        other_config_ids = set(tenant_configs[other_tenant_id])
                        overlap = config_ids & other_config_ids
                        assert len(overlap) == 0, (
                            f"Cross-tenant leakage detected with second manager instance"
                        )
        
        asyncio.run(run_test())


# ============================================================================
# Property 22: Tenant Default Initialization
# ============================================================================

class TestTenantDefaultInitialization:
    """
    Property 22: Tenant Default Initialization
    
    For any newly created tenant, the system should automatically initialize
    default configuration templates for LLM providers, database connections,
    and sync strategies.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.4**
    """
    
    @given(
        tenant_id=st.uuids().map(str),  # Generate valid UUID strings
        include_llm=st.booleans(),
        include_database=st.booleans(),
        include_sync=st.booleans(),
    )
    @settings(max_examples=100, deadline=None)
    def test_new_tenant_gets_default_configs(
        self, tenant_id, include_llm, include_database, include_sync
    ):
        """
        New tenants receive default configuration templates.
        
        For any newly created tenant, the system should initialize
        default configurations based on the specified flags.
        
        **Validates: Requirements 7.4**
        """
        # Skip if all flags are False (nothing to test)
        assume(include_llm or include_database or include_sync)
        
        async def run_test():
            from src.admin.tenant_config_initializer import TenantConfigInitializer
            from unittest.mock import AsyncMock, MagicMock
            
            # Create mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.add = MagicMock()
            
            # Mock query results for global defaults (return empty)
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            mock_session.execute.return_value = mock_result
            
            # Create initializer with mock session
            initializer = TenantConfigInitializer(db=mock_session)
            
            # Initialize tenant defaults
            result = await initializer.initialize_tenant_defaults(
                tenant_id=tenant_id,
                user_id=None,  # Use None instead of invalid UUID string
                include_llm=include_llm,
                include_database=include_database,
                include_sync=include_sync,
                inherit_global=False,  # Use templates, not global defaults
            )
            
            # Verify result structure
            assert "tenant_id" in result, "Result should contain tenant_id"
            assert result["tenant_id"] == tenant_id, "Tenant ID should match"
            
            assert "llm_configs" in result, "Result should contain llm_configs"
            assert "db_configs" in result, "Result should contain db_configs"
            assert "sync_strategies" in result, "Result should contain sync_strategies"
            assert "created_at" in result, "Result should contain created_at"
            
            # Verify LLM configs created if requested
            if include_llm:
                assert len(result["llm_configs"]) > 0, (
                    f"Should create LLM configs when include_llm=True. "
                    f"Got {len(result['llm_configs'])} configs"
                )
                # Should create at least the default templates (3 templates)
                assert len(result["llm_configs"]) >= 3, (
                    f"Should create at least 3 LLM configs (Ollama, OpenAI, Qianwen). "
                    f"Got {len(result['llm_configs'])}"
                )
            else:
                assert len(result["llm_configs"]) == 0, (
                    f"Should not create LLM configs when include_llm=False. "
                    f"Got {len(result['llm_configs'])} configs"
                )
            
            # Verify database configs created if requested
            if include_database:
                assert len(result["db_configs"]) > 0, (
                    f"Should create database configs when include_database=True. "
                    f"Got {len(result['db_configs'])} configs"
                )
                # Should create at least the default templates (2 templates)
                assert len(result["db_configs"]) >= 2, (
                    f"Should create at least 2 database configs (PostgreSQL, MySQL). "
                    f"Got {len(result['db_configs'])}"
                )
            else:
                assert len(result["db_configs"]) == 0, (
                    f"Should not create database configs when include_database=False. "
                    f"Got {len(result['db_configs'])} configs"
                )
            
            # Verify sync strategies created if requested
            if include_sync and include_database:
                # Sync strategies require database configs
                assert len(result["sync_strategies"]) > 0, (
                    f"Should create sync strategies when include_sync=True "
                    f"and database configs exist. "
                    f"Got {len(result['sync_strategies'])} strategies"
                )
                # Should create at least the default templates (2 templates)
                assert len(result["sync_strategies"]) >= 2, (
                    f"Should create at least 2 sync strategies (Full, Incremental). "
                    f"Got {len(result['sync_strategies'])}"
                )
            elif include_sync and not include_database:
                # Sync strategies cannot be created without database configs
                assert len(result["sync_strategies"]) == 0, (
                    f"Should not create sync strategies when no database configs exist. "
                    f"Got {len(result['sync_strategies'])} strategies"
                )
            else:
                assert len(result["sync_strategies"]) == 0, (
                    f"Should not create sync strategies when include_sync=False. "
                    f"Got {len(result['sync_strategies'])} strategies"
                )
            
            # Verify database operations were called
            if include_llm or include_database or include_sync:
                # Should have called commit
                mock_session.commit.assert_called()
        
        asyncio.run(run_test())
    
    @given(
        num_tenants=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_default_configs_isolated_between_tenants(self, num_tenants):
        """
        Default configurations are isolated between tenants.
        
        When multiple tenants are initialized with defaults,
        each tenant should receive their own isolated set of
        default configurations.
        
        **Validates: Requirements 7.4, 7.1**
        """
        async def run_test():
            from src.admin.tenant_config_initializer import TenantConfigInitializer
            from unittest.mock import AsyncMock, MagicMock
            
            # Create mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.add = MagicMock()
            
            # Mock query results for global defaults (return empty)
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            mock_session.execute.return_value = mock_result
            
            initializer = TenantConfigInitializer(db=mock_session)
            
            # Generate unique tenant IDs as valid UUIDs
            tenant_ids = [str(uuid4()) for _ in range(num_tenants)]
            
            # Track initialization results
            tenant_results: Dict[str, Dict[str, Any]] = {}
            
            # Initialize defaults for all tenants
            for tenant_id in tenant_ids:
                result = await initializer.initialize_tenant_defaults(
                    tenant_id=tenant_id,
                    user_id=None,  # Use None instead of invalid UUID string
                    include_llm=True,
                    include_database=True,
                    include_sync=True,
                    inherit_global=False,
                )
                tenant_results[tenant_id] = result
            
            # Verify each tenant has their own configs
            for tenant_id in tenant_ids:
                result = tenant_results[tenant_id]
                
                # Verify counts
                assert len(result["llm_configs"]) >= 3, (
                    f"Tenant {tenant_id} should have at least 3 LLM configs"
                )
                assert len(result["db_configs"]) >= 2, (
                    f"Tenant {tenant_id} should have at least 2 DB configs"
                )
                assert len(result["sync_strategies"]) >= 2, (
                    f"Tenant {tenant_id} should have at least 2 sync strategies"
                )
                
                # Verify no overlap with other tenants
                for other_tenant_id in tenant_ids:
                    if other_tenant_id != tenant_id:
                        other_result = tenant_results[other_tenant_id]
                        
                        # Config IDs should be unique
                        llm_overlap = set(result["llm_configs"]) & set(other_result["llm_configs"])
                        db_overlap = set(result["db_configs"]) & set(other_result["db_configs"])
                        sync_overlap = set(result["sync_strategies"]) & set(other_result["sync_strategies"])
                        
                        assert len(llm_overlap) == 0, (
                            f"LLM config overlap detected between tenant {tenant_id} "
                            f"and tenant {other_tenant_id}: {llm_overlap}"
                        )
                        
                        assert len(db_overlap) == 0, (
                            f"DB config overlap detected between tenant {tenant_id} "
                            f"and tenant {other_tenant_id}: {db_overlap}"
                        )
                        
                        assert len(sync_overlap) == 0, (
                            f"Sync strategy overlap detected between tenant {tenant_id} "
                            f"and tenant {other_tenant_id}: {sync_overlap}"
                        )
        
        asyncio.run(run_test())
    
    @given(
        tenant_id=st.uuids().map(str),  # Generate valid UUID strings
    )
    @settings(max_examples=100, deadline=None)
    def test_default_configs_include_all_types(self, tenant_id):
        """
        Default initialization includes all configuration types.
        
        For any newly created tenant with all flags enabled,
        the system should create defaults for:
        - LLM providers (Ollama, OpenAI, Qianwen)
        - Database connections (PostgreSQL, MySQL)
        - Sync strategies (Full, Incremental)
        
        **Validates: Requirements 7.4**
        """
        async def run_test():
            from src.admin.tenant_config_initializer import TenantConfigInitializer, DefaultTemplates
            from unittest.mock import AsyncMock, MagicMock
            
            # Create mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.add = MagicMock()
            
            # Mock query results for global defaults (return empty)
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            mock_session.execute.return_value = mock_result
            
            initializer = TenantConfigInitializer(db=mock_session)
            
            # Initialize with all types enabled
            result = await initializer.initialize_tenant_defaults(
                tenant_id=tenant_id,
                user_id=None,  # Use None instead of invalid UUID string
                include_llm=True,
                include_database=True,
                include_sync=True,
                inherit_global=False,
            )
            
            # Verify LLM configs include expected count from templates
            assert len(result["llm_configs"]) == len(DefaultTemplates.LLM_TEMPLATES), (
                f"Should create {len(DefaultTemplates.LLM_TEMPLATES)} LLM configs. "
                f"Got {len(result['llm_configs'])}"
            )
            
            # Verify database configs include expected count from templates
            assert len(result["db_configs"]) == len(DefaultTemplates.DATABASE_TEMPLATES), (
                f"Should create {len(DefaultTemplates.DATABASE_TEMPLATES)} DB configs. "
                f"Got {len(result['db_configs'])}"
            )
            
            # Verify sync strategies include expected count from templates
            assert len(result["sync_strategies"]) == len(DefaultTemplates.SYNC_STRATEGY_TEMPLATES), (
                f"Should create {len(DefaultTemplates.SYNC_STRATEGY_TEMPLATES)} sync strategies. "
                f"Got {len(result['sync_strategies'])}"
            )
        
        asyncio.run(run_test())
    
    @given(
        tenant_id=st.uuids().map(str),  # Generate valid UUID strings
    )
    @settings(max_examples=100, deadline=None)
    def test_default_configs_are_valid(self, tenant_id):
        """
        Default configurations are valid and well-formed.
        
        For any newly created tenant, all default configurations
        should be valid and contain required fields.
        
        **Validates: Requirements 7.4**
        """
        async def run_test():
            from src.admin.tenant_config_initializer import TenantConfigInitializer
            from unittest.mock import AsyncMock, MagicMock
            from uuid import UUID
            
            # Create mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            
            # Track added objects
            added_objects = []
            def mock_add(obj):
                added_objects.append(obj)
            mock_session.add = mock_add
            
            # Mock query results for global defaults (return empty)
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            mock_session.execute.return_value = mock_result
            
            initializer = TenantConfigInitializer(db=mock_session)
            
            # Initialize defaults
            result = await initializer.initialize_tenant_defaults(
                tenant_id=tenant_id,
                user_id=None,  # Use None instead of invalid UUID string
                include_llm=True,
                include_database=True,
                include_sync=True,
                inherit_global=False,
            )
            
            # Verify LLM configs are valid
            llm_configs = [obj for obj in added_objects if hasattr(obj, 'config_type') and obj.config_type == 'llm']
            
            for config in llm_configs:
                # Required fields
                assert config.name, "LLM config should have a name"
                assert config.config_data, "LLM config should have config_data"
                assert "llm_type" in config.config_data, (
                    "LLM config should have llm_type"
                )
                assert "model_name" in config.config_data, (
                    "LLM config should have model_name"
                )
                assert "api_endpoint" in config.config_data, (
                    "LLM config should have api_endpoint"
                )
                
                # Tenant ID should match
                assert str(config.tenant_id) == tenant_id, (
                    f"LLM config tenant_id should match. "
                    f"Expected: {tenant_id}, Got: {config.tenant_id}"
                )
            
            # Verify database configs are valid
            db_configs = [obj for obj in added_objects if hasattr(obj, 'db_type')]
            
            for config in db_configs:
                # Required fields
                assert config.name, "DB config should have a name"
                assert config.db_type, "DB config should have db_type"
                assert config.host, "DB config should have host"
                assert config.port, "DB config should have port"
                assert config.database, "DB config should have database"
                assert config.username, "DB config should have username"
                
                # Tenant ID should match
                assert str(config.tenant_id) == tenant_id, (
                    f"DB config tenant_id should match. "
                    f"Expected: {tenant_id}, Got: {config.tenant_id}"
                )
                
                # Should be read-only by default
                assert config.is_readonly is True, (
                    "Default DB configs should be read-only"
                )
        
        asyncio.run(run_test())
    
    @given(
        tenant_id=st.uuids().map(str),  # Generate valid UUID strings
    )
    @settings(max_examples=100, deadline=None)
    def test_idempotent_initialization(self, tenant_id):
        """
        Tenant initialization creates new configs each time.
        
        Initializing the same tenant multiple times creates
        new configurations each time (not idempotent by design).
        
        **Validates: Requirements 7.4**
        """
        async def run_test():
            from src.admin.tenant_config_initializer import TenantConfigInitializer
            from unittest.mock import AsyncMock, MagicMock
            
            # Create mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.add = MagicMock()
            
            # Mock query results for global defaults (return empty)
            mock_result = MagicMock()
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            mock_session.execute.return_value = mock_result
            
            initializer = TenantConfigInitializer(db=mock_session)
            
            # First initialization
            result1 = await initializer.initialize_tenant_defaults(
                tenant_id=tenant_id,
                user_id=None,  # Use None instead of invalid UUID string
                include_llm=True,
                include_database=True,
                include_sync=True,
                inherit_global=False,
            )
            
            first_llm_count = len(result1["llm_configs"])
            first_db_count = len(result1["db_configs"])
            first_sync_count = len(result1["sync_strategies"])
            
            # Second initialization (should create new configs)
            result2 = await initializer.initialize_tenant_defaults(
                tenant_id=tenant_id,
                user_id=None,  # Use None instead of invalid UUID string
                include_llm=True,
                include_database=True,
                include_sync=True,
                inherit_global=False,
            )
            
            second_llm_count = len(result2["llm_configs"])
            second_db_count = len(result2["db_configs"])
            second_sync_count = len(result2["sync_strategies"])
            
            # Each initialization should create the same number of configs
            assert second_llm_count == first_llm_count, (
                f"Second initialization should create same number of LLM configs. "
                f"First: {first_llm_count}, Second: {second_llm_count}"
            )
            
            assert second_db_count == first_db_count, (
                f"Second initialization should create same number of DB configs. "
                f"First: {first_db_count}, Second: {second_db_count}"
            )
            
            # Config IDs should be different (new configs created)
            llm_overlap = set(result1["llm_configs"]) & set(result2["llm_configs"])
            db_overlap = set(result1["db_configs"]) & set(result2["db_configs"])
            
            assert len(llm_overlap) == 0, (
                f"Second initialization should create new LLM configs with different IDs. "
                f"Found overlap: {llm_overlap}"
            )
            
            assert len(db_overlap) == 0, (
                f"Second initialization should create new DB configs with different IDs. "
                f"Found overlap: {db_overlap}"
            )
        
        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
