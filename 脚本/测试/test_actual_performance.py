#!/usr/bin/env python3
"""
Real performance test to measure actual permission check times.
This test uses real database connections and measures actual performance.
"""

import asyncio
import time
import statistics
import sys
import os
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.security.rbac_controller_optimized import OptimizedRBACController
from src.security.permission_performance_optimizer import OptimizationConfig
from src.security.models import UserModel, UserRole
from src.security.rbac_models import RoleModel, PermissionModel, UserRoleModel, RolePermissionModel


def setup_test_data(db_session):
    """Set up test data for performance testing."""
    # Create test user
    user = UserModel(
        id=uuid4(),
        username="test_user",
        email="test@example.com",
        tenant_id="test_tenant",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add(user)
    
    # Create test role
    role = RoleModel(
        name="test_role",
        description="Test role for performance testing",
        tenant_id="test_tenant",
        created_by=user.id
    )
    db_session.add(role)
    db_session.flush()
    
    # Create test permissions
    permissions = []
    for i in range(10):
        perm = PermissionModel(
            name=f"test_permission_{i}",
            description=f"Test permission {i}",
            scope="GLOBAL",
            created_by=user.id
        )
        permissions.append(perm)
        db_session.add(perm)
    
    db_session.flush()
    
    # Assign role to user
    user_role = UserRoleModel(
        user_id=user.id,
        role_id=role.id,
        assigned_by=user.id
    )
    db_session.add(user_role)
    
    # Assign permissions to role
    for perm in permissions:
        role_perm = RolePermissionModel(
            role_id=role.id,
            permission_id=perm.id
        )
        db_session.add(role_perm)
    
    db_session.commit()
    return user, role, permissions


async def test_real_performance():
    """Test real permission check performance."""
    print("Setting up test environment...")
    
    # Use SQLite for testing
    engine = create_engine("sqlite:///test_performance.db", echo=False)
    
    # Create tables (simplified for testing)
    from sqlalchemy import MetaData, Table, Column, String, Boolean, DateTime, ForeignKey, Text
    from datetime import datetime
    
    metadata = MetaData()
    
    # Simplified tables for testing
    users_table = Table('users', metadata,
        Column('id', String(36), primary_key=True),
        Column('username', String(50)),
        Column('email', String(100)),
        Column('tenant_id', String(50)),
        Column('role', String(20)),
        Column('is_active', Boolean, default=True),
        Column('created_at', DateTime, default=datetime.utcnow)
    )
    
    roles_table = Table('roles', metadata,
        Column('id', String(36), primary_key=True),
        Column('name', String(50)),
        Column('description', String(200)),
        Column('tenant_id', String(50)),
        Column('created_by', String(36)),
        Column('is_active', Boolean, default=True),
        Column('created_at', DateTime, default=datetime.utcnow)
    )
    
    permissions_table = Table('permissions', metadata,
        Column('id', String(36), primary_key=True),
        Column('name', String(50)),
        Column('description', String(200)),
        Column('scope', String(20)),
        Column('created_by', String(36)),
        Column('created_at', DateTime, default=datetime.utcnow)
    )
    
    user_roles_table = Table('user_roles', metadata,
        Column('user_id', String(36), ForeignKey('users.id')),
        Column('role_id', String(36), ForeignKey('roles.id')),
        Column('assigned_by', String(36)),
        Column('assigned_at', DateTime, default=datetime.utcnow)
    )
    
    role_permissions_table = Table('role_permissions', metadata,
        Column('role_id', String(36), ForeignKey('roles.id')),
        Column('permission_id', String(36), ForeignKey('permissions.id')),
        Column('assigned_at', DateTime, default=datetime.utcnow)
    )
    
    metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Set up optimized controller
        config = OptimizationConfig(
            target_response_time_ms=10.0,
            cache_preload_enabled=True,
            query_optimization_enabled=True,
            batch_processing_enabled=True,
            memory_cache_size=1000
        )
        
        controller = OptimizedRBACController(optimization_config=config)
        
        print("Creating test data...")
        # Insert test data directly
        user_id = uuid4()
        role_id = uuid4()
        permission_ids = [uuid4() for _ in range(10)]
        
        # Insert user
        session.execute(users_table.insert().values(
            id=str(user_id),
            username="test_user",
            email="test@example.com",
            tenant_id="test_tenant",
            role="VIEWER",
            is_active=True
        ))
        
        # Insert role
        session.execute(roles_table.insert().values(
            id=str(role_id),
            name="test_role",
            description="Test role",
            tenant_id="test_tenant",
            created_by=str(user_id),
            is_active=True
        ))
        
        # Insert permissions
        for i, perm_id in enumerate(permission_ids):
            session.execute(permissions_table.insert().values(
                id=str(perm_id),
                name=f"test_permission_{i}",
                description=f"Test permission {i}",
                scope="GLOBAL",
                created_by=str(user_id)
            ))
        
        # Assign role to user
        session.execute(user_roles_table.insert().values(
            user_id=str(user_id),
            role_id=str(role_id),
            assigned_by=str(user_id)
        ))
        
        # Assign permissions to role
        for perm_id in permission_ids:
            session.execute(role_permissions_table.insert().values(
                role_id=str(role_id),
                permission_id=str(perm_id)
            ))
        
        session.commit()
        
        print("Running performance tests...")
        
        # Test 1: Cold cache performance (first check)
        print("\n1. Testing cold cache performance...")
        cold_times = []
        for i in range(5):
            # Clear cache to ensure cold start
            controller.clear_all_permission_cache()
            
            start_time = time.perf_counter()
            # Use sync method since we don't have async DB setup
            result = controller.check_user_permission(
                user_id=user_id,
                permission_name="test_permission_0",
                db=session
            )
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            cold_times.append(response_time_ms)
            print(f"  Cold check {i+1}: {response_time_ms:.2f}ms")
        
        avg_cold_time = statistics.mean(cold_times)
        print(f"  Average cold time: {avg_cold_time:.2f}ms")
        
        # Test 2: Warm cache performance (subsequent checks)
        print("\n2. Testing warm cache performance...")
        warm_times = []
        for i in range(100):
            start_time = time.perf_counter()
            result = controller.check_user_permission(
                user_id=user_id,
                permission_name=f"test_permission_{i % 10}",
                db=session
            )
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            warm_times.append(response_time_ms)
        
        avg_warm_time = statistics.mean(warm_times)
        p95_warm_time = statistics.quantiles(warm_times, n=20)[18] if len(warm_times) > 1 else warm_times[0]
        max_warm_time = max(warm_times)
        under_10ms = sum(1 for t in warm_times if t < 10.0)
        compliance_rate = (under_10ms / len(warm_times)) * 100
        
        print(f"  Average warm time: {avg_warm_time:.2f}ms")
        print(f"  P95 warm time: {p95_warm_time:.2f}ms")
        print(f"  Max warm time: {max_warm_time:.2f}ms")
        print(f"  Compliance rate (<10ms): {compliance_rate:.1f}%")
        
        # Test 3: Batch performance
        print("\n3. Testing batch performance...")
        permissions_to_check = [f"test_permission_{i}" for i in range(5)]
        batch_times = []
        
        for i in range(20):
            start_time = time.perf_counter()
            results = controller.batch_check_permissions(
                user_id=user_id,
                permissions=permissions_to_check,
                db=session
            )
            end_time = time.perf_counter()
            
            total_time_ms = (end_time - start_time) * 1000
            avg_time_per_perm = total_time_ms / len(permissions_to_check)
            batch_times.append(avg_time_per_perm)
        
        avg_batch_time = statistics.mean(batch_times)
        print(f"  Average time per permission in batch: {avg_batch_time:.2f}ms")
        
        # Performance summary
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Cold cache average: {avg_cold_time:.2f}ms")
        print(f"Warm cache average: {avg_warm_time:.2f}ms")
        print(f"Warm cache P95: {p95_warm_time:.2f}ms")
        print(f"Batch average per permission: {avg_batch_time:.2f}ms")
        print(f"Target compliance rate: {compliance_rate:.1f}%")
        
        # Check if we meet the <10ms requirement
        target_met = avg_warm_time < 10.0 and p95_warm_time < 15.0 and compliance_rate >= 90.0
        
        if target_met:
            print("\n✅ PERFORMANCE TARGET MET!")
            print("   - Average warm cache time < 10ms")
            print("   - P95 time reasonable")
            print("   - >90% compliance rate")
        else:
            print("\n❌ PERFORMANCE TARGET NOT MET")
            if avg_warm_time >= 10.0:
                print(f"   - Average time {avg_warm_time:.2f}ms >= 10ms target")
            if p95_warm_time >= 15.0:
                print(f"   - P95 time {p95_warm_time:.2f}ms >= 15ms threshold")
            if compliance_rate < 90.0:
                print(f"   - Compliance rate {compliance_rate:.1f}% < 90% target")
        
        # Get cache statistics
        cache_stats = controller.get_cache_statistics()
        print(f"\nCache Statistics:")
        print(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
        print(f"  Memory cache size: {cache_stats.get('memory_cache_size', 0)}")
        
        return target_met
        
    finally:
        session.close()
        # Clean up test database
        os.remove("test_performance.db")


if __name__ == "__main__":
    result = asyncio.run(test_real_performance())
    sys.exit(0 if result else 1)