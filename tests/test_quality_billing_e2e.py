"""
End-to-End System Integration Tests for Quality-Billing Loop

Tests the complete workflow from quality detection to billing settlement,
verifying data consistency across all modules.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import asyncio
import uuid


# ============================================================================
# Domain Models for E2E Testing
# ============================================================================

class WorkflowStage(Enum):
    """Quality-billing workflow stages"""
    TICKET_CREATED = "ticket_created"
    AGENT_ASSIGNED = "agent_assigned"
    RESPONSE_GENERATED = "response_generated"
    QUALITY_EVALUATED = "quality_evaluated"
    BILLING_CALCULATED = "billing_calculated"
    INVOICE_GENERATED = "invoice_generated"
    PAYMENT_PROCESSED = "payment_processed"
    SETTLEMENT_COMPLETE = "settlement_complete"


@dataclass
class WorkflowEvent:
    """Event in the quality-billing workflow"""
    event_id: str
    stage: WorkflowStage
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class E2ETestContext:
    """Context for end-to-end test execution"""
    test_id: str
    tenant_id: str
    events: List[WorkflowEvent] = field(default_factory=list)
    checkpoints: Dict[str, Any] = field(default_factory=dict)

    def add_event(self, stage: WorkflowStage, data: Dict[str, Any]) -> WorkflowEvent:
        event = WorkflowEvent(
            event_id=str(uuid.uuid4()),
            stage=stage,
            timestamp=datetime.now(),
            data=data
        )
        self.events.append(event)
        return event

    def set_checkpoint(self, name: str, value: Any) -> None:
        self.checkpoints[name] = {
            "value": value,
            "timestamp": datetime.now()
        }

    def get_checkpoint(self, name: str) -> Optional[Any]:
        checkpoint = self.checkpoints.get(name)
        return checkpoint["value"] if checkpoint else None


# ============================================================================
# Mock Services for E2E Testing
# ============================================================================

class MockTicketService:
    """Mock ticket service for E2E testing"""

    def __init__(self):
        self.tickets: Dict[str, Dict] = {}

    def create_ticket(
        self,
        tenant_id: str,
        customer_query: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        ticket = {
            "ticket_id": ticket_id,
            "tenant_id": tenant_id,
            "customer_query": customer_query,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "assigned_agent": None,
            "response": None
        }
        self.tickets[ticket_id] = ticket
        return ticket

    def assign_agent(self, ticket_id: str, agent_id: str) -> Dict[str, Any]:
        if ticket_id not in self.tickets:
            raise ValueError(f"Ticket {ticket_id} not found")
        self.tickets[ticket_id]["assigned_agent"] = agent_id
        self.tickets[ticket_id]["status"] = "assigned"
        return self.tickets[ticket_id]

    def add_response(self, ticket_id: str, response: str) -> Dict[str, Any]:
        if ticket_id not in self.tickets:
            raise ValueError(f"Ticket {ticket_id} not found")
        self.tickets[ticket_id]["response"] = response
        self.tickets[ticket_id]["status"] = "resolved"
        self.tickets[ticket_id]["resolved_at"] = datetime.now().isoformat()
        return self.tickets[ticket_id]


class MockQualityService:
    """Mock quality evaluation service for E2E testing"""

    def __init__(self):
        self.evaluations: Dict[str, Dict] = {}

    def evaluate_response(
        self,
        ticket_id: str,
        query: str,
        response: str,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        # Simulate Ragas-style evaluation
        faithfulness = self._calculate_faithfulness(response, context or [])
        relevancy = self._calculate_relevancy(query, response)
        context_precision = self._calculate_context_precision(response, context or [])
        context_recall = self._calculate_context_recall(query, context or [])

        overall_score = (
            faithfulness * 0.3 +
            relevancy * 0.3 +
            context_precision * 0.2 +
            context_recall * 0.2
        )

        evaluation = {
            "evaluation_id": f"EVAL-{uuid.uuid4().hex[:8].upper()}",
            "ticket_id": ticket_id,
            "scores": {
                "faithfulness": faithfulness,
                "answer_relevancy": relevancy,
                "context_precision": context_precision,
                "context_recall": context_recall
            },
            "overall_score": overall_score,
            "quality_tier": self._determine_tier(overall_score),
            "evaluated_at": datetime.now().isoformat()
        }
        self.evaluations[ticket_id] = evaluation
        return evaluation

    def _calculate_faithfulness(self, response: str, context: List[str]) -> float:
        if not context:
            return 0.7
        context_text = " ".join(context).lower()
        response_words = set(response.lower().split())
        context_words = set(context_text.split())
        overlap = len(response_words & context_words)
        return min(1.0, overlap / max(len(response_words), 1) + 0.5)

    def _calculate_relevancy(self, query: str, response: str) -> float:
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        overlap = len(query_words & response_words)
        return min(1.0, overlap / max(len(query_words), 1) + 0.4)

    def _calculate_context_precision(self, response: str, context: List[str]) -> float:
        if not context:
            return 0.6
        return min(1.0, len(response) / 100 * 0.3 + 0.5)

    def _calculate_context_recall(self, query: str, context: List[str]) -> float:
        if not context:
            return 0.5
        return min(1.0, len(context) * 0.2 + 0.4)

    def _determine_tier(self, score: float) -> str:
        if score >= 0.9:
            return "platinum"
        elif score >= 0.75:
            return "gold"
        elif score >= 0.6:
            return "silver"
        else:
            return "bronze"


class MockBillingService:
    """Mock billing service for E2E testing"""

    TIER_RATES = {
        "platinum": Decimal("0.15"),
        "gold": Decimal("0.12"),
        "silver": Decimal("0.08"),
        "bronze": Decimal("0.05")
    }

    def __init__(self):
        self.billing_records: Dict[str, Dict] = {}
        self.invoices: Dict[str, Dict] = {}
        self.payments: Dict[str, Dict] = {}

    def calculate_billing(
        self,
        ticket_id: str,
        quality_tier: str,
        token_count: int = 1000
    ) -> Dict[str, Any]:
        rate = self.TIER_RATES.get(quality_tier, Decimal("0.05"))
        amount = rate * Decimal(token_count) / Decimal(1000)

        billing_record = {
            "billing_id": f"BILL-{uuid.uuid4().hex[:8].upper()}",
            "ticket_id": ticket_id,
            "quality_tier": quality_tier,
            "token_count": token_count,
            "rate": float(rate),
            "amount": float(amount),
            "created_at": datetime.now().isoformat()
        }
        self.billing_records[ticket_id] = billing_record
        return billing_record

    def generate_invoice(
        self,
        tenant_id: str,
        billing_ids: List[str],
        billing_period: str
    ) -> Dict[str, Any]:
        total_amount = Decimal("0")
        line_items = []

        for billing_id in billing_ids:
            for ticket_id, record in self.billing_records.items():
                if record["billing_id"] == billing_id:
                    total_amount += Decimal(str(record["amount"]))
                    line_items.append({
                        "billing_id": billing_id,
                        "ticket_id": ticket_id,
                        "amount": record["amount"],
                        "quality_tier": record["quality_tier"]
                    })

        invoice = {
            "invoice_id": f"INV-{uuid.uuid4().hex[:8].upper()}",
            "tenant_id": tenant_id,
            "billing_period": billing_period,
            "line_items": line_items,
            "total_amount": float(total_amount),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        self.invoices[invoice["invoice_id"]] = invoice
        return invoice

    def process_payment(
        self,
        invoice_id: str,
        payment_method: str = "credit_card"
    ) -> Dict[str, Any]:
        if invoice_id not in self.invoices:
            raise ValueError(f"Invoice {invoice_id} not found")

        invoice = self.invoices[invoice_id]

        payment = {
            "payment_id": f"PAY-{uuid.uuid4().hex[:8].upper()}",
            "invoice_id": invoice_id,
            "amount": invoice["total_amount"],
            "payment_method": payment_method,
            "status": "completed",
            "processed_at": datetime.now().isoformat()
        }

        self.invoices[invoice_id]["status"] = "paid"
        self.invoices[invoice_id]["paid_at"] = payment["processed_at"]
        self.payments[payment["payment_id"]] = payment

        return payment


class MockDataConsistencyChecker:
    """Checks data consistency across services"""

    def __init__(
        self,
        ticket_service: MockTicketService,
        quality_service: MockQualityService,
        billing_service: MockBillingService
    ):
        self.ticket_service = ticket_service
        self.quality_service = quality_service
        self.billing_service = billing_service

    def check_ticket_quality_consistency(self, ticket_id: str) -> Dict[str, Any]:
        """Check consistency between ticket and quality evaluation"""
        ticket = self.ticket_service.tickets.get(ticket_id)
        evaluation = self.quality_service.evaluations.get(ticket_id)

        issues = []

        if ticket and not evaluation:
            if ticket["status"] == "resolved":
                issues.append("Resolved ticket missing quality evaluation")

        if evaluation and not ticket:
            issues.append("Quality evaluation for non-existent ticket")

        if ticket and evaluation:
            if ticket["status"] != "resolved":
                issues.append("Quality evaluation for unresolved ticket")

        return {
            "ticket_id": ticket_id,
            "consistent": len(issues) == 0,
            "issues": issues
        }

    def check_quality_billing_consistency(self, ticket_id: str) -> Dict[str, Any]:
        """Check consistency between quality evaluation and billing"""
        evaluation = self.quality_service.evaluations.get(ticket_id)
        billing = self.billing_service.billing_records.get(ticket_id)

        issues = []

        if evaluation and not billing:
            issues.append("Quality evaluation missing billing record")

        if billing and not evaluation:
            issues.append("Billing record for non-evaluated ticket")

        if evaluation and billing:
            if evaluation["quality_tier"] != billing["quality_tier"]:
                issues.append(
                    f"Quality tier mismatch: evaluation={evaluation['quality_tier']}, "
                    f"billing={billing['quality_tier']}"
                )

        return {
            "ticket_id": ticket_id,
            "consistent": len(issues) == 0,
            "issues": issues
        }

    def check_full_workflow_consistency(self, ticket_id: str) -> Dict[str, Any]:
        """Check consistency across the entire workflow"""
        ticket_quality = self.check_ticket_quality_consistency(ticket_id)
        quality_billing = self.check_quality_billing_consistency(ticket_id)

        all_issues = ticket_quality["issues"] + quality_billing["issues"]

        return {
            "ticket_id": ticket_id,
            "consistent": len(all_issues) == 0,
            "ticket_quality_check": ticket_quality,
            "quality_billing_check": quality_billing,
            "total_issues": len(all_issues)
        }


# ============================================================================
# E2E Workflow Orchestrator
# ============================================================================

class QualityBillingWorkflow:
    """Orchestrates the complete quality-billing workflow"""

    def __init__(self):
        self.ticket_service = MockTicketService()
        self.quality_service = MockQualityService()
        self.billing_service = MockBillingService()
        self.consistency_checker = MockDataConsistencyChecker(
            self.ticket_service,
            self.quality_service,
            self.billing_service
        )

    async def execute_full_workflow(
        self,
        tenant_id: str,
        customer_query: str,
        agent_response: str,
        context: Optional[List[str]] = None
    ) -> E2ETestContext:
        """Execute the complete quality-billing workflow"""
        ctx = E2ETestContext(
            test_id=str(uuid.uuid4()),
            tenant_id=tenant_id
        )

        # Stage 1: Create ticket
        ticket = self.ticket_service.create_ticket(
            tenant_id=tenant_id,
            customer_query=customer_query
        )
        ctx.add_event(WorkflowStage.TICKET_CREATED, {"ticket": ticket})
        ctx.set_checkpoint("ticket_id", ticket["ticket_id"])

        # Stage 2: Assign agent
        agent_id = f"AGENT-{uuid.uuid4().hex[:6].upper()}"
        ticket = self.ticket_service.assign_agent(ticket["ticket_id"], agent_id)
        ctx.add_event(WorkflowStage.AGENT_ASSIGNED, {
            "ticket_id": ticket["ticket_id"],
            "agent_id": agent_id
        })

        # Stage 3: Generate response
        ticket = self.ticket_service.add_response(ticket["ticket_id"], agent_response)
        ctx.add_event(WorkflowStage.RESPONSE_GENERATED, {
            "ticket_id": ticket["ticket_id"],
            "response": agent_response
        })

        # Stage 4: Quality evaluation
        evaluation = self.quality_service.evaluate_response(
            ticket_id=ticket["ticket_id"],
            query=customer_query,
            response=agent_response,
            context=context
        )
        ctx.add_event(WorkflowStage.QUALITY_EVALUATED, {"evaluation": evaluation})
        ctx.set_checkpoint("quality_tier", evaluation["quality_tier"])
        ctx.set_checkpoint("overall_score", evaluation["overall_score"])

        # Stage 5: Calculate billing
        token_count = len(agent_response.split()) * 4  # Approximate token count
        billing = self.billing_service.calculate_billing(
            ticket_id=ticket["ticket_id"],
            quality_tier=evaluation["quality_tier"],
            token_count=token_count
        )
        ctx.add_event(WorkflowStage.BILLING_CALCULATED, {"billing": billing})
        ctx.set_checkpoint("billing_amount", billing["amount"])

        return ctx

    async def execute_batch_workflow(
        self,
        tenant_id: str,
        queries: List[Dict[str, Any]]
    ) -> List[E2ETestContext]:
        """Execute workflow for multiple queries"""
        contexts = []

        for query_data in queries:
            ctx = await self.execute_full_workflow(
                tenant_id=tenant_id,
                customer_query=query_data["query"],
                agent_response=query_data["response"],
                context=query_data.get("context")
            )
            contexts.append(ctx)

        return contexts

    async def generate_and_process_invoice(
        self,
        tenant_id: str,
        contexts: List[E2ETestContext],
        billing_period: str
    ) -> Dict[str, Any]:
        """Generate invoice and process payment for batch"""
        billing_ids = []

        for ctx in contexts:
            ticket_id = ctx.get_checkpoint("ticket_id")
            if ticket_id and ticket_id in self.billing_service.billing_records:
                billing_record = self.billing_service.billing_records[ticket_id]
                billing_ids.append(billing_record["billing_id"])

        # Generate invoice
        invoice = self.billing_service.generate_invoice(
            tenant_id=tenant_id,
            billing_ids=billing_ids,
            billing_period=billing_period
        )

        # Process payment
        payment = self.billing_service.process_payment(invoice["invoice_id"])

        return {
            "invoice": invoice,
            "payment": payment,
            "total_tickets": len(contexts),
            "total_amount": invoice["total_amount"]
        }


# ============================================================================
# Test Classes
# ============================================================================

class TestE2ECompleteWorkflow:
    """Test complete end-to-end workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_single_ticket_complete_workflow(self, workflow):
        """Test complete workflow for a single ticket"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-001",
            customer_query="How do I reset my password?",
            agent_response="To reset your password, go to Settings > Security > Reset Password. Click the reset button and follow the email instructions.",
            context=["Password reset is available in Settings", "Security section contains password options"]
        )

        # Verify all stages completed
        stages = [event.stage for event in ctx.events]
        assert WorkflowStage.TICKET_CREATED in stages
        assert WorkflowStage.AGENT_ASSIGNED in stages
        assert WorkflowStage.RESPONSE_GENERATED in stages
        assert WorkflowStage.QUALITY_EVALUATED in stages
        assert WorkflowStage.BILLING_CALCULATED in stages

        # Verify checkpoints
        assert ctx.get_checkpoint("ticket_id") is not None
        assert ctx.get_checkpoint("quality_tier") is not None
        assert ctx.get_checkpoint("billing_amount") is not None

        # Verify data consistency
        ticket_id = ctx.get_checkpoint("ticket_id")
        consistency = workflow.consistency_checker.check_full_workflow_consistency(ticket_id)
        assert consistency["consistent"] is True
        assert consistency["total_issues"] == 0

    @pytest.mark.asyncio
    async def test_batch_workflow_with_invoice(self, workflow):
        """Test batch workflow with invoice generation"""
        queries = [
            {
                "query": "How do I upgrade my plan?",
                "response": "To upgrade your plan, visit Billing > Plans and select your desired tier.",
                "context": ["Billing section has plan management", "Plans can be upgraded anytime"]
            },
            {
                "query": "What payment methods do you accept?",
                "response": "We accept credit cards, PayPal, and bank transfers.",
                "context": ["Payment options include cards and digital wallets"]
            },
            {
                "query": "How do I cancel my subscription?",
                "response": "Go to Account Settings > Subscription > Cancel. Note that cancellation takes effect at the end of your billing period.",
                "context": ["Subscription management in Account Settings", "Cancellation is processed at period end"]
            }
        ]

        contexts = await workflow.execute_batch_workflow(
            tenant_id="tenant-002",
            queries=queries
        )

        assert len(contexts) == 3

        # Generate and process invoice
        result = await workflow.generate_and_process_invoice(
            tenant_id="tenant-002",
            contexts=contexts,
            billing_period="2025-12"
        )

        assert result["invoice"]["status"] == "paid"
        assert result["payment"]["status"] == "completed"
        assert result["total_tickets"] == 3
        assert result["total_amount"] > 0

        # Verify all tickets are consistent
        for ctx in contexts:
            ticket_id = ctx.get_checkpoint("ticket_id")
            consistency = workflow.consistency_checker.check_full_workflow_consistency(ticket_id)
            assert consistency["consistent"] is True

    @pytest.mark.asyncio
    async def test_quality_tier_affects_billing(self, workflow):
        """Test that quality tier properly affects billing amount"""
        # High quality response
        high_quality_ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-003",
            customer_query="What are your business hours?",
            agent_response="Our business hours are Monday through Friday, 9 AM to 6 PM EST. We also offer 24/7 online support through our help center and AI assistant. During weekends, emergency support is available for premium customers.",
            context=[
                "Business hours: Mon-Fri 9 AM - 6 PM EST",
                "24/7 online support available",
                "Premium customers get weekend emergency support"
            ]
        )

        # Low quality response
        low_quality_ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-003",
            customer_query="What are your refund policies?",
            agent_response="Contact support.",
            context=["Refund policy details", "30-day money back guarantee"]
        )

        high_tier = high_quality_ctx.get_checkpoint("quality_tier")
        low_tier = low_quality_ctx.get_checkpoint("quality_tier")

        tier_order = ["bronze", "silver", "gold", "platinum"]
        high_tier_rank = tier_order.index(high_tier) if high_tier in tier_order else -1
        low_tier_rank = tier_order.index(low_tier) if low_tier in tier_order else -1

        # High quality should have equal or better tier
        assert high_tier_rank >= low_tier_rank

    @pytest.mark.asyncio
    async def test_workflow_event_ordering(self, workflow):
        """Test that workflow events are in correct chronological order"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-004",
            customer_query="How do I contact support?",
            agent_response="You can contact support via email at support@example.com or through our live chat feature.",
            context=["Support email: support@example.com", "Live chat available"]
        )

        expected_order = [
            WorkflowStage.TICKET_CREATED,
            WorkflowStage.AGENT_ASSIGNED,
            WorkflowStage.RESPONSE_GENERATED,
            WorkflowStage.QUALITY_EVALUATED,
            WorkflowStage.BILLING_CALCULATED
        ]

        actual_stages = [event.stage for event in ctx.events]

        for i, expected_stage in enumerate(expected_order):
            assert actual_stages[i] == expected_stage, f"Stage {i} should be {expected_stage}"

        # Verify timestamps are in order
        for i in range(1, len(ctx.events)):
            assert ctx.events[i].timestamp >= ctx.events[i-1].timestamp


class TestE2EDataConsistency:
    """Test data consistency across the workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_ticket_quality_data_linkage(self, workflow):
        """Test that ticket and quality data are properly linked"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-005",
            customer_query="How do I export my data?",
            agent_response="Go to Settings > Data > Export and select your preferred format (CSV, JSON, or XML).",
            context=["Data export in Settings", "Supports CSV, JSON, XML formats"]
        )

        ticket_id = ctx.get_checkpoint("ticket_id")

        # Verify ticket exists
        ticket = workflow.ticket_service.tickets.get(ticket_id)
        assert ticket is not None
        assert ticket["status"] == "resolved"

        # Verify evaluation exists and links to ticket
        evaluation = workflow.quality_service.evaluations.get(ticket_id)
        assert evaluation is not None
        assert evaluation["ticket_id"] == ticket_id

    @pytest.mark.asyncio
    async def test_quality_billing_data_linkage(self, workflow):
        """Test that quality and billing data are properly linked"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-006",
            customer_query="What security features do you offer?",
            agent_response="We offer two-factor authentication, encryption at rest and in transit, and regular security audits.",
            context=["2FA available", "End-to-end encryption", "SOC 2 certified"]
        )

        ticket_id = ctx.get_checkpoint("ticket_id")

        # Verify evaluation and billing have matching tiers
        evaluation = workflow.quality_service.evaluations.get(ticket_id)
        billing = workflow.billing_service.billing_records.get(ticket_id)

        assert evaluation is not None
        assert billing is not None
        assert evaluation["quality_tier"] == billing["quality_tier"]

    @pytest.mark.asyncio
    async def test_invoice_billing_records_consistency(self, workflow):
        """Test that invoice correctly aggregates billing records"""
        queries = [
            {"query": "Question 1", "response": "Answer 1 with detailed information."},
            {"query": "Question 2", "response": "Answer 2 with comprehensive details."},
        ]

        contexts = await workflow.execute_batch_workflow(
            tenant_id="tenant-007",
            queries=queries
        )

        result = await workflow.generate_and_process_invoice(
            tenant_id="tenant-007",
            contexts=contexts,
            billing_period="2025-12"
        )

        invoice = result["invoice"]

        # Sum of line items should equal total
        line_item_sum = sum(item["amount"] for item in invoice["line_items"])
        assert abs(line_item_sum - invoice["total_amount"]) < 0.001

        # Each line item should reference valid billing record
        for item in invoice["line_items"]:
            billing_id = item["billing_id"]
            found = False
            for record in workflow.billing_service.billing_records.values():
                if record["billing_id"] == billing_id:
                    found = True
                    break
            assert found, f"Billing record {billing_id} not found"


class TestE2EMultiTenant:
    """Test multi-tenant isolation in E2E workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self, workflow):
        """Test that tenant data is properly isolated"""
        # Create tickets for two different tenants
        ctx1 = await workflow.execute_full_workflow(
            tenant_id="tenant-A",
            customer_query="Tenant A question",
            agent_response="Tenant A response with specific information."
        )

        ctx2 = await workflow.execute_full_workflow(
            tenant_id="tenant-B",
            customer_query="Tenant B question",
            agent_response="Tenant B response with different information."
        )

        ticket_id_1 = ctx1.get_checkpoint("ticket_id")
        ticket_id_2 = ctx2.get_checkpoint("ticket_id")

        # Verify tickets belong to correct tenants
        ticket_1 = workflow.ticket_service.tickets[ticket_id_1]
        ticket_2 = workflow.ticket_service.tickets[ticket_id_2]

        assert ticket_1["tenant_id"] == "tenant-A"
        assert ticket_2["tenant_id"] == "tenant-B"
        assert ticket_id_1 != ticket_id_2

    @pytest.mark.asyncio
    async def test_tenant_invoice_isolation(self, workflow):
        """Test that invoices are properly isolated per tenant"""
        # Create queries for tenant A
        queries_a = [
            {"query": "Q1", "response": "Response 1 for tenant A."},
            {"query": "Q2", "response": "Response 2 for tenant A."},
        ]
        contexts_a = await workflow.execute_batch_workflow(
            tenant_id="tenant-A",
            queries=queries_a
        )

        # Create queries for tenant B
        queries_b = [
            {"query": "Q1", "response": "Response 1 for tenant B."},
        ]
        contexts_b = await workflow.execute_batch_workflow(
            tenant_id="tenant-B",
            queries=queries_b
        )

        # Generate invoices for each tenant
        result_a = await workflow.generate_and_process_invoice(
            tenant_id="tenant-A",
            contexts=contexts_a,
            billing_period="2025-12"
        )

        result_b = await workflow.generate_and_process_invoice(
            tenant_id="tenant-B",
            contexts=contexts_b,
            billing_period="2025-12"
        )

        # Verify invoice isolation
        assert result_a["invoice"]["tenant_id"] == "tenant-A"
        assert result_b["invoice"]["tenant_id"] == "tenant-B"
        assert len(result_a["invoice"]["line_items"]) == 2
        assert len(result_b["invoice"]["line_items"]) == 1


class TestE2EErrorHandling:
    """Test error handling in E2E workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_workflow_with_empty_response(self, workflow):
        """Test workflow handles empty response gracefully"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-008",
            customer_query="Important question",
            agent_response=""
        )

        # Workflow should complete even with empty response
        assert ctx.get_checkpoint("ticket_id") is not None
        assert ctx.get_checkpoint("quality_tier") is not None
        # Empty response should result in lower tier
        assert ctx.get_checkpoint("quality_tier") in ["bronze", "silver"]

    @pytest.mark.asyncio
    async def test_workflow_with_no_context(self, workflow):
        """Test workflow handles missing context gracefully"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-009",
            customer_query="Question without context",
            agent_response="Response to the question with general information.",
            context=None
        )

        # Workflow should complete without context
        assert ctx.get_checkpoint("ticket_id") is not None
        assert ctx.get_checkpoint("quality_tier") is not None
        assert ctx.get_checkpoint("billing_amount") is not None

    def test_invalid_invoice_id(self, workflow):
        """Test that invalid invoice ID raises appropriate error"""
        with pytest.raises(ValueError, match="Invoice .* not found"):
            workflow.billing_service.process_payment("INVALID-ID")

    def test_invalid_ticket_id_for_assignment(self, workflow):
        """Test that invalid ticket ID raises appropriate error"""
        with pytest.raises(ValueError, match="Ticket .* not found"):
            workflow.ticket_service.assign_agent("INVALID-TKT", "AGENT-001")


class TestE2EPerformance:
    """Test performance aspects of E2E workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_batch_processing_completes(self, workflow):
        """Test that batch processing completes for multiple tickets"""
        queries = [
            {"query": f"Question {i}", "response": f"Detailed answer {i} with information."}
            for i in range(10)
        ]

        contexts = await workflow.execute_batch_workflow(
            tenant_id="tenant-perf",
            queries=queries
        )

        assert len(contexts) == 10

        # All tickets should be consistent
        for ctx in contexts:
            ticket_id = ctx.get_checkpoint("ticket_id")
            consistency = workflow.consistency_checker.check_full_workflow_consistency(ticket_id)
            assert consistency["consistent"] is True

    @pytest.mark.asyncio
    async def test_workflow_event_count(self, workflow):
        """Test that workflow generates expected number of events"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-count",
            customer_query="Test query",
            agent_response="Test response with enough content."
        )

        # Should have exactly 5 events for complete workflow
        assert len(ctx.events) == 5


class TestE2EQualityMetrics:
    """Test quality metrics in E2E workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_quality_scores_in_valid_range(self, workflow):
        """Test that all quality scores are in valid range [0, 1]"""
        ctx = await workflow.execute_full_workflow(
            tenant_id="tenant-metrics",
            customer_query="How do I use the API?",
            agent_response="To use the API, first obtain an API key from your dashboard. Then make HTTP requests to our endpoints with the key in the Authorization header.",
            context=["API keys in dashboard", "REST API documentation available"]
        )

        ticket_id = ctx.get_checkpoint("ticket_id")
        evaluation = workflow.quality_service.evaluations[ticket_id]

        for metric, score in evaluation["scores"].items():
            assert 0.0 <= score <= 1.0, f"{metric} score {score} out of range"

        assert 0.0 <= evaluation["overall_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_quality_tier_assignment(self, workflow):
        """Test that quality tiers are correctly assigned based on score"""
        responses = [
            # Very detailed, high-quality response
            "Our comprehensive security suite includes multi-factor authentication with support for TOTP, SMS, and hardware keys. We implement AES-256 encryption for all data at rest and TLS 1.3 for data in transit. Our systems undergo quarterly penetration testing and annual SOC 2 Type II audits. We also offer role-based access control, audit logging, and real-time threat detection.",
            # Brief response
            "Yes, we have security features.",
        ]

        contexts = []
        for i, response in enumerate(responses):
            ctx = await workflow.execute_full_workflow(
                tenant_id=f"tenant-tier-{i}",
                customer_query="What security features do you have?",
                agent_response=response,
                context=["Security features documentation", "Compliance certifications"]
            )
            contexts.append(ctx)

        # First response should have higher or equal tier than second
        tier_order = {"bronze": 0, "silver": 1, "gold": 2, "platinum": 3}
        tier_0 = contexts[0].get_checkpoint("quality_tier")
        tier_1 = contexts[1].get_checkpoint("quality_tier")

        assert tier_order[tier_0] >= tier_order[tier_1]


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestE2EPropertyBased:
    """Property-based tests for E2E workflow"""

    @pytest.fixture
    def workflow(self) -> QualityBillingWorkflow:
        return QualityBillingWorkflow()

    @pytest.mark.asyncio
    async def test_billing_amount_non_negative(self, workflow):
        """Test that billing amounts are never negative"""
        test_cases = [
            {"query": "Q1", "response": "R1"},
            {"query": "", "response": ""},
            {"query": "Long query " * 100, "response": "Long response " * 100},
        ]

        for case in test_cases:
            ctx = await workflow.execute_full_workflow(
                tenant_id="tenant-prop",
                customer_query=case["query"],
                agent_response=case["response"]
            )

            billing_amount = ctx.get_checkpoint("billing_amount")
            assert billing_amount >= 0

    @pytest.mark.asyncio
    async def test_invoice_total_equals_sum(self, workflow):
        """Test that invoice total always equals sum of line items"""
        queries = [
            {"query": f"Q{i}", "response": f"Response {i} with content."}
            for i in range(5)
        ]

        contexts = await workflow.execute_batch_workflow(
            tenant_id="tenant-sum",
            queries=queries
        )

        result = await workflow.generate_and_process_invoice(
            tenant_id="tenant-sum",
            contexts=contexts,
            billing_period="2025-12"
        )

        invoice = result["invoice"]
        calculated_total = sum(item["amount"] for item in invoice["line_items"])

        assert abs(invoice["total_amount"] - calculated_total) < 0.001

    @pytest.mark.asyncio
    async def test_workflow_idempotency_property(self, workflow):
        """Test that same input produces consistent structure"""
        query = "Test query for idempotency"
        response = "Test response for idempotency check."

        ctx1 = await workflow.execute_full_workflow(
            tenant_id="tenant-idem-1",
            customer_query=query,
            agent_response=response
        )

        # Create new workflow instance for isolation
        workflow2 = QualityBillingWorkflow()
        ctx2 = await workflow2.execute_full_workflow(
            tenant_id="tenant-idem-2",
            customer_query=query,
            agent_response=response
        )

        # Same number of events
        assert len(ctx1.events) == len(ctx2.events)

        # Same stages in same order
        stages1 = [e.stage for e in ctx1.events]
        stages2 = [e.stage for e in ctx2.events]
        assert stages1 == stages2

        # Same quality tier for same input
        assert ctx1.get_checkpoint("quality_tier") == ctx2.get_checkpoint("quality_tier")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
