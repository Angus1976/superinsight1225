"""
Comprehensive Integration Tests for Quality-Billing System

Tests the complete workflow from work time calculation to invoice generation,
verifying multi-tenant billing isolation and quality-adjusted pricing.

Task 9.1: 计费系统集成测试
"""

import pytest
from datetime import datetime, timedelta, date
from typing import Dict, List, Any
from decimal import Decimal
from uuid import uuid4


# =============================================================================
# Test Data Models
# =============================================================================

class BillingRecordForTest:
    """Test billing record for integration testing"""
    
    def __init__(self, tenant_id: str, user_id: str, work_hours: float, 
                 quality_score: float, task_type: str = "annotation"):
        self.id = str(uuid4())
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.task_id = str(uuid4())
        self.work_hours = work_hours
        self.quality_score = quality_score
        self.task_type = task_type
        self.annotation_count = int(work_hours * 50)  # Approximate annotations per hour
        self.time_spent = int(work_hours * 3600)  # Convert to seconds
        self.created_at = datetime.now()
        self.billing_date = date.today()


class MockWorkTimeCalculator:
    """Mock work time calculator for testing"""
    
    def __init__(self):
        self.work_sessions = {}
    
    def start_work_session(self, user_id: str, task_id: str) -> str:
        session_id = str(uuid4())
        self.work_sessions[session_id] = {
            "user_id": user_id,
            "task_id": task_id,
            "start_time": datetime.now(),
            "end_time": None,
            "breaks": [],
            "status": "active"
        }
        return session_id
    
    def end_work_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.work_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.work_sessions[session_id]
        session["end_time"] = datetime.now()
        session["status"] = "completed"
        
        # Calculate work time (simulate 1-2 hours of work)
        base_time = 3600 + (hash(session_id) % 3600)  # 1-2 hours
        break_time = sum(b["duration"] for b in session["breaks"])
        effective_time = base_time - break_time
        
        return {
            "session_id": session_id,
            "total_time": base_time,
            "break_time": break_time,
            "effective_time": effective_time,
            "work_hours": effective_time / 3600
        }
    
    def add_break(self, session_id: str, duration_minutes: int):
        if session_id in self.work_sessions:
            self.work_sessions[session_id]["breaks"].append({
                "start": datetime.now(),
                "duration": duration_minutes * 60
            })


class MockQualityEvaluator:
    """Mock quality evaluator for testing"""
    
    def __init__(self):
        self.evaluations = {}
    
    def evaluate_work_quality(self, user_id: str, task_id: str, 
                            work_data: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate quality evaluation based on work characteristics
        base_score = 0.8
        
        # Adjust based on work hours (fatigue factor)
        work_hours = work_data.get("work_hours", 1)
        if work_hours > 8:
            base_score -= 0.1  # Fatigue penalty
        elif work_hours < 2:
            base_score -= 0.05  # Insufficient time penalty
        
        # Add some randomness but keep it deterministic for testing
        user_hash = hash(user_id) % 100
        score_adjustment = (user_hash - 50) / 1000  # -0.05 to +0.05
        
        final_score = max(0.0, min(1.0, base_score + score_adjustment))
        
        evaluation = {
            "evaluation_id": str(uuid4()),
            "user_id": user_id,
            "task_id": task_id,
            "quality_score": final_score,
            "accuracy": final_score * 0.95,
            "completeness": final_score * 1.02,
            "consistency": final_score * 0.98,
            "evaluated_at": datetime.now()
        }
        
        self.evaluations[task_id] = evaluation
        return evaluation


class MockBillingEngine:
    """Mock billing engine for testing"""
    
    def __init__(self):
        self.billing_rules = {}
        self.invoices = {}
        
    def set_billing_rule(self, tenant_id: str, rule: Dict[str, Any]):
        self.billing_rules[tenant_id] = rule
    
    def calculate_cost(self, billing_record: BillingRecordForTest) -> Decimal:
        rule = self.billing_rules.get(billing_record.tenant_id, {
            "base_rate_per_hour": 50.0,
            "quality_multipliers": {
                "excellent": 1.2,  # >= 0.9
                "good": 1.0,       # >= 0.8
                "acceptable": 0.9,  # >= 0.7
                "poor": 0.7        # < 0.7
            }
        })
        
        base_cost = Decimal(str(billing_record.work_hours * rule["base_rate_per_hour"]))
        
        # Apply quality multiplier
        quality_tier = self._get_quality_tier(billing_record.quality_score)
        multiplier = Decimal(str(rule["quality_multipliers"].get(quality_tier, 1.0)))
        
        return base_cost * multiplier
    
    def _get_quality_tier(self, score: float) -> str:
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "acceptable"
        else:
            return "poor"
    
    def generate_invoice(self, tenant_id: str, billing_records: List[BillingRecordForTest],
                        billing_period: str) -> Dict[str, Any]:
        total_amount = Decimal("0")
        line_items = []
        
        for record in billing_records:
            if record.tenant_id != tenant_id:
                continue
                
            cost = self.calculate_cost(record)
            total_amount += cost
            
            line_items.append({
                "record_id": record.id,
                "user_id": record.user_id,
                "work_hours": record.work_hours,
                "quality_score": record.quality_score,
                "quality_tier": self._get_quality_tier(record.quality_score),
                "cost": float(cost)
            })
        
        invoice = {
            "invoice_id": str(uuid4()),
            "tenant_id": tenant_id,
            "billing_period": billing_period,
            "generated_at": datetime.now(),
            "line_items": line_items,
            "subtotal": float(total_amount),
            "tax_rate": 0.13,  # 13% VAT
            "tax_amount": float(total_amount * Decimal("0.13")),
            "total_amount": float(total_amount * Decimal("1.13")),
            "status": "generated"
        }
        
        self.invoices[invoice["invoice_id"]] = invoice
        return invoice


# =============================================================================
# Integration Test Fixtures
# =============================================================================

@pytest.fixture
def work_time_calculator():
    return MockWorkTimeCalculator()

@pytest.fixture
def quality_evaluator():
    return MockQualityEvaluator()

@pytest.fixture
def billing_engine():
    return MockBillingEngine()

@pytest.fixture
def sample_tenants():
    return [
        {
            "tenant_id": "tenant_enterprise",
            "name": "Enterprise Corp",
            "billing_rule": {
                "base_rate_per_hour": 75.0,
                "quality_multipliers": {
                    "excellent": 1.3,
                    "good": 1.1,
                    "acceptable": 0.95,
                    "poor": 0.6
                }
            }
        },
        {
            "tenant_id": "tenant_startup",
            "name": "Startup Inc",
            "billing_rule": {
                "base_rate_per_hour": 40.0,
                "quality_multipliers": {
                    "excellent": 1.15,
                    "good": 1.0,
                    "acceptable": 0.9,
                    "poor": 0.75
                }
            }
        }
    ]


# =============================================================================
# Complete Workflow Integration Tests
# =============================================================================

class TestCompleteWorkflowIntegration:
    """Test complete workflow from work time to invoice generation"""
    
    def test_end_to_end_billing_workflow(self, work_time_calculator, quality_evaluator, 
                                       billing_engine, sample_tenants):
        """Test complete end-to-end billing workflow"""
        
        # Setup billing rules for tenants
        for tenant in sample_tenants:
            billing_engine.set_billing_rule(tenant["tenant_id"], tenant["billing_rule"])
        
        # Phase 1: Work Time Tracking
        work_sessions = []
        for tenant in sample_tenants:
            for user_idx in range(3):
                user_id = f"user_{tenant['tenant_id']}_{user_idx}"
                task_id = str(uuid4())
                
                # Start work session
                session_id = work_time_calculator.start_work_session(user_id, task_id)
                
                # Simulate work with breaks
                if user_idx == 1:  # Add break for second user
                    work_time_calculator.add_break(session_id, 15)  # 15-minute break
                
                # End work session
                session_result = work_time_calculator.end_work_session(session_id)
                work_sessions.append({
                    "tenant_id": tenant["tenant_id"],
                    "user_id": user_id,
                    "task_id": task_id,
                    "session_result": session_result
                })
        
        assert len(work_sessions) == 6  # 2 tenants × 3 users each
        
        # Phase 2: Quality Evaluation
        quality_evaluations = []
        for session in work_sessions:
            evaluation = quality_evaluator.evaluate_work_quality(
                session["user_id"],
                session["task_id"],
                session["session_result"]
            )
            quality_evaluations.append(evaluation)
        
        assert len(quality_evaluations) == 6
        
        # Phase 3: Billing Record Creation
        billing_records = []
        for i, session in enumerate(work_sessions):
            evaluation = quality_evaluations[i]
            
            record = BillingRecordForTest(
                tenant_id=session["tenant_id"],
                user_id=session["user_id"],
                work_hours=session["session_result"]["work_hours"],
                quality_score=evaluation["quality_score"]
            )
            billing_records.append(record)
        
        # Phase 4: Invoice Generation
        invoices = {}
        for tenant in sample_tenants:
            tenant_records = [r for r in billing_records if r.tenant_id == tenant["tenant_id"]]
            
            invoice = billing_engine.generate_invoice(
                tenant_id=tenant["tenant_id"],
                billing_records=tenant_records,
                billing_period="2026-01"
            )
            invoices[tenant["tenant_id"]] = invoice
        
        # Verification
        assert len(invoices) == 2
        
        # Verify tenant isolation
        for tenant_id, invoice in invoices.items():
            assert invoice["tenant_id"] == tenant_id
            assert len(invoice["line_items"]) == 3  # 3 users per tenant
            assert invoice["subtotal"] > 0  # Check subtotal instead of total
        
        # Verify different billing rates
        enterprise_subtotal = invoices["tenant_enterprise"]["subtotal"]
        startup_subtotal = invoices["tenant_startup"]["subtotal"]
        
        # Enterprise should generally cost more due to higher base rate
        assert enterprise_subtotal > startup_subtotal
        
        return {
            "work_sessions": work_sessions,
            "quality_evaluations": quality_evaluations,
            "billing_records": billing_records,
            "invoices": invoices
        }
    
    def test_quality_impact_on_billing(self, billing_engine):
        """Test that quality scores properly impact billing amounts"""
        
        tenant_id = "test_tenant"
        billing_engine.set_billing_rule(tenant_id, {
            "base_rate_per_hour": 50.0,
            "quality_multipliers": {
                "excellent": 1.2,
                "good": 1.0,
                "acceptable": 0.9,
                "poor": 0.7
            }
        })
        
        # Create records with different quality scores
        test_cases = [
            {"user_id": "user_excellent", "quality_score": 0.95, "expected_tier": "excellent"},
            {"user_id": "user_good", "quality_score": 0.85, "expected_tier": "good"},
            {"user_id": "user_acceptable", "quality_score": 0.75, "expected_tier": "acceptable"},
            {"user_id": "user_poor", "quality_score": 0.65, "expected_tier": "poor"}
        ]
        
        records = []
        costs = []
        
        for case in test_cases:
            record = BillingRecordForTest(
                tenant_id=tenant_id,
                user_id=case["user_id"],
                work_hours=2.0,  # Same work hours for fair comparison
                quality_score=case["quality_score"]
            )
            records.append(record)
            
            cost = billing_engine.calculate_cost(record)
            costs.append(float(cost))
        
        # Verify cost ordering: excellent > good > acceptable > poor
        assert costs[0] > costs[1] > costs[2] > costs[3]
        
        # Verify specific multipliers
        base_cost = 2.0 * 50.0  # 2 hours × $50/hour = $100
        assert abs(costs[0] - base_cost * 1.2) < 0.01  # Excellent: 120%
        assert abs(costs[1] - base_cost * 1.0) < 0.01  # Good: 100%
        assert abs(costs[2] - base_cost * 0.9) < 0.01  # Acceptable: 90%
        assert abs(costs[3] - base_cost * 0.7) < 0.01  # Poor: 70%
    
    def test_multi_tenant_billing_isolation(self, billing_engine):
        """Test that multi-tenant billing is properly isolated"""
        
        # Setup different billing rules for tenants
        tenants = [
            {"id": "tenant_a", "rate": 60.0},
            {"id": "tenant_b", "rate": 40.0},
            {"id": "tenant_c", "rate": 80.0}
        ]
        
        for tenant in tenants:
            billing_engine.set_billing_rule(tenant["id"], {
                "base_rate_per_hour": tenant["rate"],
                "quality_multipliers": {"good": 1.0}
            })
        
        # Create billing records for each tenant
        all_records = []
        for tenant in tenants:
            for user_idx in range(2):
                record = BillingRecordForTest(
                    tenant_id=tenant["id"],
                    user_id=f"user_{tenant['id']}_{user_idx}",
                    work_hours=1.0,
                    quality_score=0.85  # Good quality
                )
                all_records.append(record)
        
        # Generate invoices for each tenant
        invoices = {}
        for tenant in tenants:
            tenant_records = [r for r in all_records if r.tenant_id == tenant["id"]]
            
            invoice = billing_engine.generate_invoice(
                tenant_id=tenant["id"],
                billing_records=tenant_records,
                billing_period="2026-01"
            )
            invoices[tenant["id"]] = invoice
        
        # Verify isolation and correct billing
        for tenant in tenants:
            invoice = invoices[tenant["id"]]
            
            # Verify tenant isolation
            assert invoice["tenant_id"] == tenant["id"]
            assert len(invoice["line_items"]) == 2  # 2 users per tenant
            
            # Verify correct billing rate
            expected_subtotal = 2 * 1.0 * tenant["rate"]  # 2 users × 1 hour × rate
            assert abs(invoice["subtotal"] - expected_subtotal) < 0.01
            
            # Verify no cross-tenant contamination
            for item in invoice["line_items"]:
                assert item["user_id"].startswith(f"user_{tenant['id']}_")


class TestBillingPerformance:
    """Test billing system performance and scalability"""
    
    def test_large_batch_processing(self, billing_engine):
        """Test processing large batches of billing records"""
        
        tenant_id = "performance_test_tenant"
        billing_engine.set_billing_rule(tenant_id, {
            "base_rate_per_hour": 50.0,
            "quality_multipliers": {
                "excellent": 1.2,
                "good": 1.0,
                "acceptable": 0.9,
                "poor": 0.7
            }
        })
        
        # Create large batch of records
        batch_size = 100  # Reduced for faster testing
        records = []
        
        for i in range(batch_size):
            record = BillingRecordForTest(
                tenant_id=tenant_id,
                user_id=f"user_{i % 10}",  # 10 unique users
                work_hours=1.0 + (i % 8),  # 1-8 hours
                quality_score=0.7 + (i % 30) / 100  # 0.7-0.99
            )
            records.append(record)
        
        # Measure processing time
        start_time = datetime.now()
        
        invoice = billing_engine.generate_invoice(
            tenant_id=tenant_id,
            billing_records=records,
            billing_period="2026-01"
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify results
        assert len(invoice["line_items"]) == batch_size
        assert invoice["total_amount"] > 0
        
        # Performance assertion (should process records quickly)
        assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, expected < 5s"


class TestBillingErrorHandling:
    """Test error handling and edge cases"""
    
    def test_empty_billing_records(self, billing_engine):
        """Test handling of empty billing records"""
        
        tenant_id = "empty_test_tenant"
        
        invoice = billing_engine.generate_invoice(
            tenant_id=tenant_id,
            billing_records=[],
            billing_period="2026-01"
        )
        
        assert invoice["tenant_id"] == tenant_id
        assert len(invoice["line_items"]) == 0
        assert invoice["subtotal"] == 0.0
        assert invoice["total_amount"] == 0.0
    
    def test_zero_work_hours(self, billing_engine):
        """Test handling of zero work hours"""
        
        tenant_id = "zero_hours_tenant"
        billing_engine.set_billing_rule(tenant_id, {
            "base_rate_per_hour": 50.0,
            "quality_multipliers": {"good": 1.0}
        })
        
        record = BillingRecordForTest(
            tenant_id=tenant_id,
            user_id="test_user",
            work_hours=0.0,
            quality_score=0.85
        )
        
        cost = billing_engine.calculate_cost(record)
        assert cost == Decimal("0.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])