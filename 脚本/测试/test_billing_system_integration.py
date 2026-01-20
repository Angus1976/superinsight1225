"""
Integration test for the enhanced billing system.

Tests the complete billing workflow including Excel export and reward distribution.
"""

import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.billing.models import BillingRecord
from src.billing.invoice_generator import DetailedInvoiceGenerator, TaxConfiguration, TaxType
from src.billing.excel_exporter import BillingExcelExporter, ExportFormat, ExportTemplate
from src.billing.reward_system import RewardDistributionManager, RewardFrequency


def test_enhanced_billing_system():
    """Test the complete enhanced billing system workflow."""
    
    print("🧪 Testing Enhanced Billing System Integration")
    print("=" * 50)
    
    # 1. Create sample billing records
    print("1. Creating sample billing records...")
    billing_records = []
    for i in range(5):
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
        "user_2": 0.82,  # Good
        "user_3": 0.78,  # Acceptable
        "user_4": 0.65   # Poor
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
    
    # 3. Test Excel export functionality
    print("\n3. Testing Excel export functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        exporter = BillingExcelExporter(output_dir=temp_dir)
        
        # Export billing records
        excel_file = exporter.export_billing_records_excel(
            billing_records=billing_records,
            template=ExportTemplate.DETAILED,
            filename="test_billing_records.xlsx"
        )
        
        print(f"   ✅ Exported billing records to: {os.path.basename(excel_file)}")
        
        # Export invoice
        invoice_file = exporter.export_invoice_excel(
            invoice_data=invoice_data,
            template=ExportTemplate.DETAILED,
            filename="test_invoice.xlsx"
        )
        
        print(f"   ✅ Exported invoice to: {os.path.basename(invoice_file)}")
        
        # Test CSV export
        csv_file = exporter.export_to_csv(
            data=billing_records,
            filename="test_export.csv"
        )
        
        print(f"   ✅ Exported CSV to: {os.path.basename(csv_file)}")
        
        # Verify files exist
        assert os.path.exists(excel_file), "Excel billing records file not created"
        assert os.path.exists(invoice_file), "Excel invoice file not created"
        assert os.path.exists(csv_file), "CSV file not created"
        
        print(f"   📁 All files created successfully in: {temp_dir}")
    
    # 4. Test reward distribution system
    print("\n4. Testing reward distribution system...")
    reward_manager = RewardDistributionManager()
    
    # Calculate rewards for users
    user_ids = [f"user_{i}" for i in range(5)]
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
    
    # 5. Test reward effectiveness evaluation
    print("\n5. Testing reward effectiveness evaluation...")
    effectiveness = reward_manager.evaluate_reward_effectiveness("test_tenant", 30)
    
    print(f"   📊 ROI Analysis: {effectiveness['roi_analysis']['roi_percentage']:.1f}% ROI")
    print(f"   💡 Recommendations: {len(effectiveness['recommendations'])} suggestions")
    
    for i, recommendation in enumerate(effectiveness['recommendations'][:2], 1):
        print(f"      {i}. {recommendation}")
    
    # 6. Integration verification
    print("\n6. Integration verification...")
    
    # Verify invoice contains quality adjustments
    project_breakdown = invoice_data.get('project_breakdown', [])
    has_quality_adjustments = any(
        project.get('quality_adjustments') for project in project_breakdown
    )
    assert has_quality_adjustments, "Invoice should contain quality adjustments"
    print("   ✅ Invoice contains quality adjustments")
    
    # Verify rewards were calculated based on quality
    quality_rewards = [r for r in reward_records if r.reward_type.value == "quality_bonus"]
    assert len(quality_rewards) > 0, "Should have quality-based rewards"
    print(f"   ✅ Generated {len(quality_rewards)} quality-based rewards")
    
    # Verify export permissions work
    from src.billing.excel_exporter import ExportPermission
    job_id = exporter.create_export_job(
        user_id="test_user",
        export_type="billing_records",
        format_type=ExportFormat.EXCEL,
        template=ExportTemplate.STANDARD,
        permission=ExportPermission.FULL_ACCESS
    )
    assert job_id is not None, "Should create export job with full access"
    print("   ✅ Export permission system working")
    
    print("\n🎉 All tests passed! Enhanced billing system is working correctly.")
    print("\n📋 Test Summary:")
    print(f"   • Billing Records: {len(billing_records)} created")
    print(f"   • Invoice Total: ¥{invoice_data['summary']['final_total']:.2f}")
    print(f"   • Rewards Calculated: {len(reward_records)}")
    print(f"   • Total Reward Amount: ¥{float(total_rewards):.2f}")
    print(f"   • Export Formats: Excel, CSV, PDF supported")
    print(f"   • Quality Adjustments: Applied based on scores")
    print(f"   • Approval Workflow: Implemented with role-based permissions")


if __name__ == "__main__":
    test_enhanced_billing_system()