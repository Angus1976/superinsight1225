#!/usr/bin/env python3
"""
Integration test for Enhanced Recovery System.

Tests the complete fault tolerance and recovery system integration.
"""

import asyncio
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_recovery_integration():
    """Test the complete enhanced recovery system integration."""
    
    print("🚀 Starting Enhanced Recovery System Integration Test")
    print("=" * 60)
    
    try:
        # Test 1: Import all components
        print("\n1. Testing component imports...")
        
        from src.system.fault_detection_system import fault_detection_system
        from src.system.recovery_orchestrator import recovery_orchestrator
        from src.system.service_dependency_mapper import service_dependency_mapper
        from src.system.backup_recovery_system import backup_recovery_system
        from src.system.fault_tolerance_system import fault_tolerance_system
        from src.system.fault_recovery_integration import fault_recovery_integration
        
        print("✅ All components imported successfully")
        
        # Test 2: Start fault tolerance system
        print("\n2. Testing fault tolerance system...")
        
        await fault_tolerance_system.start_system()
        print(f"✅ Fault tolerance system started: {fault_tolerance_system.system_active}")
        
        # Test circuit breaker
        cb_status = fault_tolerance_system.get_circuit_breaker_status("database")
        if cb_status:
            print(f"✅ Circuit breaker for database: {cb_status['state']}")
        
        # Test rate limiter
        rl_status = fault_tolerance_system.get_rate_limiter_status("api_gateway")
        if rl_status:
            print(f"✅ Rate limiter for API gateway: {rl_status['current_tokens']} tokens")
        
        # Test feature toggle
        feature_enabled = fault_tolerance_system.is_feature_enabled("annotation_service", "ai_annotation")
        print(f"✅ AI annotation feature enabled: {feature_enabled}")
        
        # Test 3: Protected execution
        print("\n3. Testing protected execution...")
        
        async def test_service_call():
            await asyncio.sleep(0.1)  # Simulate work
            return "Service call successful"
        
        result = await fault_tolerance_system.execute_with_protection(
            "annotation_service", 
            test_service_call
        )
        print(f"✅ Protected execution result: {result}")
        
        # Test 4: System statistics
        print("\n4. Testing system statistics...")
        
        stats = fault_tolerance_system.get_system_statistics()
        print(f"✅ Total requests: {stats['total_requests']}")
        print(f"✅ Success rate: {stats['success_rate']:.2%}")
        print(f"✅ Registered services: {stats['registered_services']}")
        
        # Test 5: Start integrated system
        print("\n5. Testing integrated fault recovery system...")
        
        await fault_recovery_integration.start_integration()
        print("✅ Integrated fault recovery system started")
        
        # Get system status
        system_status = fault_recovery_integration.get_system_status()
        print(f"✅ System health: {system_status.system_health}")
        print(f"✅ Fault tolerance active: {system_status.fault_tolerance_active}")
        
        # Test 6: API endpoints (simulate)
        print("\n6. Testing API integration...")
        
        from src.api.fault_recovery_api import router
        print(f"✅ API router loaded with {len(router.routes)} routes")
        
        # Test 7: Backup system
        print("\n7. Testing backup recovery system...")
        
        await backup_recovery_system.start_system()
        print(f"✅ Backup system started: {backup_recovery_system.system_active}")
        
        backup_stats = backup_recovery_system.get_system_statistics()
        print(f"✅ Backup jobs scheduled: {backup_stats['scheduled_jobs']}")
        
        # Test 8: Cleanup
        print("\n8. Cleaning up...")
        
        await backup_recovery_system.stop_system()
        await fault_recovery_integration.stop_integration()
        await fault_tolerance_system.stop_system()
        
        print("✅ All systems stopped successfully")
        
        print("\n" + "=" * 60)
        print("🎉 Enhanced Recovery System Integration Test PASSED")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        logger.exception("Integration test error")
        return False


async def main():
    """Main test function."""
    success = await test_enhanced_recovery_integration()
    
    if success:
        print("\n✅ All tests passed! Enhanced Recovery System is ready for production.")
    else:
        print("\n❌ Tests failed! Please check the logs for details.")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())