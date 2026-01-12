#!/usr/bin/env python3

"""
Simple test to verify Zero Leakage Prevention System functionality
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_simple_detection():
    """Test simple credit card detection"""
    
    try:
        from src.security.zero_leakage_prevention import ZeroLeakagePreventionSystem
        
        # Create system
        system = ZeroLeakagePreventionSystem()
        print("✅ System created successfully")
        
        # Test credit card detection
        credit_card = "4532-1234-5678-9012"
        
        result = await system.scan_for_leakage(
            data=credit_card,
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        print(f"✅ Scan completed")
        print(f"   Has leakage: {result.has_leakage}")
        print(f"   Risk level: {result.risk_level}")
        print(f"   Detected entities: {len(result.detected_entities)}")
        print(f"   Confidence: {result.confidence_score}")
        
        if result.has_leakage and len(result.detected_entities) > 0:
            print("✅ Credit card detection working!")
            return True
        else:
            print("❌ Credit card detection not working")
            print(f"   Error: {result.metadata.get('error', 'No error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_detection())
    sys.exit(0 if success else 1)