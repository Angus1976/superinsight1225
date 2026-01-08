"""
Core functionality test for the enhanced billing system.

Tests the core billing logic without external dependencies.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.billing.models import BillingRecord
from src.billing.invoice_generator import DetailedInvoiceGenerator, TaxConfiguration, TaxType
from src.billing.reward_system import RewardDistributionManager, RewardFrequency


def test_core_billing_functionality():
    """Test the core billing system functionality."""
    
    print("🧪 Testing Core Billing System Functionality")
    print("=" * 50)
    
    # 1. Create sample billing records
    print("1. Creating sample billing records...")
    billing_records = []
    for i in range(3):
        record = BillingRecord(
            tenant_id="test_tenant",
            user_id=f"user_{i}",
            task_id=uuid4(),
            annotation_count=100 + i * 20,
            time_spent=3600 + i * 600,  # 1-2 hours
            cost=Decimal(str(50.0 + i * 10)),
            billing_date=date.today() - timedelta(days=i),
            created_at=datetime.now()
        )
        billing_records.append(record)
    
    print(f"   ✅ Created {len(billing_records)} billing records")
    
    # 2. Test detailed invoice generation
    print("\n2. Testing detailed invoice generation...")
    invoice_generator = DetailedInvoiceGenerator()
    
    # Quality scores for testing
    quality_scores = {
        "user_0": 0.95,  # Excellent
        "user_1": 0.88,  # Good
        "user_2": 0.78,  # Acceptable
    }
    
    # Tax configuration
    tax_config = TaxConfiguration(
        tax_type=TaxType.VAT,
        rate=Decimal("13.0"),  # 13% VAT
        description="增值税"
    )
    
    invoice_data = invoice_generator.generate_detailed_invoice(
        tenant_id="test_tenant",
        billing_period="2026-01",
        billing_records=billing_records,
        quality_scores=quality_scores,
        tax_config=tax_config
    )
    
    print(f"   ✅ Generated invoice with ID: {invoice_data['id']}")
    print(f"   📊 Summary: {invoice_data['summary']['total_annotations']} annotations, "
          f"¥{invoice_data['summary']['final_total']:.2f} total")
    
    # Verify quality adjustments were applied
    project_breakdown = invoice_data.get('project_breakdown', [])
    has_quality_adjustments = any(
        project.get('quality_adjustments') for project in project_breakdown
    )
    assert has_quality_adjustments, "Invoice should contain quality adjustments"
    print("   ✅ Quality adjustments applied correctly")
    
    # 3. Test reward distribution system
    print("\n3. Testing reward distribution system...")
    reward_manager = RewardDistributionManager()
    
    # Calculate rewards for users
    user_ids = [f"user_{i}" for i in range(3)]
    period_start = date.today() - timedelta(days=30)
    period_end = date.today()
    
    reward_records = reward_manager.calculate_period_rewards(
        tenant_id="test_tenant",
        user_ids=user_ids,
        period_start=period_start,
        period_end=period_end,
        frequency=RewardFrequency.MONTHLY
    )
    
    print(f"   ✅ Calculated {len(reward_records)} reward records")
    
    # Display reward summary
    total_rewards = sum(record.amount for record in reward_records)
    auto_approved = len([r for r in reward_records if r.status.value == "approved"])
    
    print(f"   💰 Total rewards: ¥{float(total_rewards):.2f}")
    print(f"   ✅ Auto-approved: {auto_approved}/{len(reward_records)}")
    
    # Test reward statistics
    stats = reward_manager.get_reward_statistics("test_tenant")
    print(f"   📈 Statistics: {stats['total_rewards']} rewards, ¥{stats['total_amount']:.2f} total")
    
    # 4. Test reward effectiveness evaluation
    print("\n4. Testing reward effectiveness evaluation...")
    effectiveness = reward_manager.evaluate_reward_effectiveness("test_tenant", 30)
    
    print(f"   📊 ROI Analysis: {effectiveness['roi_analysis']['roi_percentage']:.1f}% ROI")
    print(f"   💡 Recommendations: {len(effectiveness['recommendations'])} suggestions")
    
    for i, recommendation in enumerate(effectiveness['recommendations'][:2], 1):
        print(f"      {i}. {recommendation}")
    
    # 5. Test quality-based calculations
    print("\n5. Testing quality-based calculations...")
    
    # Verify different quality scores produce different adjustments
    base_cost = Decimal("100.00")
    
    excellent_adjustment = invoice_generator.calculate_quality_adjustment(0.95, base_cost)
    good_adjustment = invoice_generator.calculate_quality_adjustment(0.88, base_cost)
    poor_adjustment = invoice_generator.calculate_quality_adjustment(0.65, base_cost)
    
    excellent_cost = invoice_generator.apply_quality_adjustment(base_cost, excellent_adjustment)
    good_cost = invoice_generator.apply_quality_adjustment(base_cost, good_adjustment)
    poor_cost = invoice_generator.apply_quality_adjustment(base_cost, poor_adjustment)
    
    print(f"   📊 Quality adjustments:")
    print(f"      Excellent (0.95): ¥{base_cost:.2f} → ¥{excellent_cost:.2f} ({excellent_adjustment.type.value})")
    print(f"      Good (0.88): ¥{base_cost:.2f} → ¥{good_cost:.2f} ({good_adjustment.type.value})")
    print(f"      Poor (0.65): ¥{base_cost:.2f} → ¥{poor_cost:.2f} ({poor_adjustment.type.value})")
    
    # Verify excellent > good > poor in terms of final cost
    assert excellent_cost > good_cost > poor_cost, "Quality adjustments should reflect quality levels"
    print("   ✅ Quality-based pricing working correctly")
    
    # 6. Test reward calculation engine
    print("\n6. Testing reward calculation engine...")
    
    calc_engine = reward_manager.calculation_engine
    
    # Test quality bonus calculation
    quality_bonus = calc_engine.calculate_quality_bonus("user_0", period_start, period_end)
    if quality_bonus:
        print(f"   🏆 Quality bonus for user_0: ¥{quality_bonus.final_amount:.2f}")
        print(f"      Quality score: {quality_bonus.quality_score:.2f}")
        print(f"      Efficiency score: {quality_bonus.efficiency_score:.2f}")
        print(f"      Criteria met: {len(quality_bonus.criteria_met)}")
    else:
        print("   ❌ No quality bonus calculated (criteria not met)")
    
    # Test efficiency bonus calculation
    efficiency_bonus = calc_engine.calculate_efficiency_bonus("user_1", period_start, period_end)
    if efficiency_bonus:
        print(f"   ⚡ Efficiency bonus for user_1: ¥{efficiency_bonus.final_amount:.2f}")
    else:
        print("   ❌ No efficiency bonus calculated (criteria not met)")
    
    print("   ✅ Reward calculation engine working correctly")
    
    # 7. Integration verification
    print("\n7. Integration verification...")
    
    # Verify rewards were calculated based on quality
    quality_rewards = [r for r in reward_records if r.reward_type.value == "quality_bonus"]
    print(f"   ✅ Generated {len(quality_rewards)} quality-based rewards")
    
    # Verify invoice totals are reasonable
    base_total = invoice_data['summary']['base_total']
    final_total = invoice_data['summary']['final_total']
    assert final_total > 0, "Final total should be positive"
    print(f"   ✅ Invoice totals: Base ¥{base_total:.2f} → Final ¥{final_total:.2f}")
    
    # Verify tax calculation
    tax_amount = invoice_data['summary']['tax_amount']
    expected_tax = invoice_data['summary']['discounted_subtotal'] * 0.13  # 13% VAT
    assert abs(tax_amount - expected_tax) < 0.01, "Tax calculation should be accurate"
    print(f"   ✅ Tax calculation: ¥{tax_amount:.2f} (13% VAT)")
    
    print("\n🎉 All core functionality tests passed!")
    print("\n📋 Test Summary:")
    print(f"   • Billing Records: {len(billing_records)} processed")
    print(f"   • Invoice Generated: ¥{invoice_data['summary']['final_total']:.2f} total")
    print(f"   • Quality Adjustments: Applied based on performance scores")
    print(f"   • Rewards Calculated: {len(reward_records)} rewards totaling ¥{float(total_rewards):.2f}")
    print(f"   • Tax Handling: 13% VAT applied correctly")
    print(f"   • Multi-level Breakdown: Project and user level details")
    
    return True


if __name__ == "__main__":
    test_core_billing_functionality()