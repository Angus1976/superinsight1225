"""Property-based tests for Approval Workflow Service.

This module tests the universal correctness properties of the approval service:
- Property 15: Approval Workflow State Machine
- Property 43: Approval Chain Configuration Validation

Requirements validated:
- 4.1: Change request routing
- 4.3: Approve action
- 4.4: Reject action with reason
- 4.5: Request changes action
- 13.1: Approval chain configuration
- 13.2: Expert notification
- 13.3: Escalation on missed deadlines
- 13.4: Final approval notification
- 13.5: 1-5 approval levels
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from uuid import uuid4
from src.collaboration.approval_service import (
    ApprovalService,
    ApprovalType,
    ApprovalLevel,
    ApprovalStatus,
    ChangeRequestStatus
)


# ============================================================================
# Property 15: Approval Workflow State Machine
# ============================================================================

class TestApprovalWorkflowStateMachine:
    """Test approval workflow state machine.

    Property: Approval workflows must follow valid state transitions.
    The state machine must be deterministic and prevent invalid transitions.

    Requirements: 4.3, 4.4, 4.5, 13.2, 13.3, 13.4
    """

    @pytest.mark.asyncio
    async def test_change_request_lifecycle(self):
        """Test complete change request lifecycle from draft to approved."""
        service = ApprovalService()

        # Create approval chain with single level
        approver_id = uuid4()
        chain = await service.create_approval_chain(
            name="Simple Chain",
            description="Single level approval",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(
                    level_number=1,
                    approver_role="reviewer",
                    approver_ids=[approver_id],
                    min_approvals=1,
                    deadline_hours=24
                )
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        # Create change request
        request = await service.create_change_request(
            title="Add Entity",
            description="Add new entity type",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="add_entity",
            change_details={"entity_name": "TestEntity"}
        )

        # Verify initial state
        assert request.status == ChangeRequestStatus.DRAFT
        assert request.current_level == 0

        # Submit for approval
        success = await service.submit_change_request(request.request_id)
        assert success

        # Verify submitted state
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.status == ChangeRequestStatus.IN_REVIEW
            assert request.current_level == 1
            assert len(request.approval_records) == 1

        # Approve
        success = await service.approve(
            request_id=request.request_id,
            approver_id=approver_id,
            approver_name="approver1",
            reason="Looks good"
        )
        assert success

        # Verify approved state
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.status == ChangeRequestStatus.APPROVED

    @pytest.mark.asyncio
    async def test_multi_level_sequential_approval(self):
        """Test multi-level sequential approval workflow."""
        service = ApprovalService()

        # Create chain with 3 levels
        approver1_id = uuid4()
        approver2_id = uuid4()
        approver3_id = uuid4()

        chain = await service.create_approval_chain(
            name="Three Level Chain",
            description="Three sequential approval levels",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[approver1_id], min_approvals=1),
                ApprovalLevel(level_number=2, approver_ids=[approver2_id], min_approvals=1),
                ApprovalLevel(level_number=3, approver_ids=[approver3_id], min_approvals=1),
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        # Create and submit request
        request = await service.create_change_request(
            title="Test Request",
            description="Test multi-level approval",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="modify",
            change_details={}
        )

        await service.submit_change_request(request.request_id)

        # Verify level 1
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.current_level == 1

        # Approve level 1
        await service.approve(request.request_id, approver1_id, "approver1")

        # Should advance to level 2
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.current_level == 2

        # Approve level 2
        await service.approve(request.request_id, approver2_id, "approver2")

        # Should advance to level 3
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.current_level == 3

        # Approve level 3
        await service.approve(request.request_id, approver3_id, "approver3")

        # Should be fully approved
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.status == ChangeRequestStatus.APPROVED

    @pytest.mark.asyncio
    async def test_rejection_stops_workflow(self):
        """Test that rejection stops the approval workflow."""
        service = ApprovalService()

        approver_id = uuid4()
        chain = await service.create_approval_chain(
            name="Test Chain",
            description="Test rejection",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[approver_id], min_approvals=1)
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        request = await service.create_change_request(
            title="Test Request",
            description="Will be rejected",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="add",
            change_details={}
        )

        await service.submit_change_request(request.request_id)

        # Reject
        success = await service.reject(
            request_id=request.request_id,
            approver_id=approver_id,
            approver_name="approver",
            reason="Invalid change"
        )
        assert success

        # Verify rejected state
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.status == ChangeRequestStatus.REJECTED

            # Check approval record
            record = request.approval_records[0]
            assert record.status == ApprovalStatus.REJECTED
            assert record.decision_reason == "Invalid change"

    @pytest.mark.asyncio
    async def test_request_changes_returns_to_requester(self):
        """Test that requesting changes returns request to requester."""
        service = ApprovalService()

        approver_id = uuid4()
        chain = await service.create_approval_chain(
            name="Test Chain",
            description="Test changes requested",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[approver_id], min_approvals=1)
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        request = await service.create_change_request(
            title="Test Request",
            description="Needs changes",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="modify",
            change_details={}
        )

        await service.submit_change_request(request.request_id)

        # Request changes
        success = await service.request_changes(
            request_id=request.request_id,
            approver_id=approver_id,
            approver_name="approver",
            requested_changes="Please add more details"
        )
        assert success

        # Verify state
        async with service._lock:
            request = service._change_requests[request.request_id]
            assert request.status == ChangeRequestStatus.CHANGES_REQUESTED
            assert request.current_level == 0  # Returned to requester

            # Check approval record
            record = request.approval_records[0]
            assert record.status == ApprovalStatus.CHANGES_REQUESTED
            assert "more details" in record.decision_reason

    @pytest.mark.asyncio
    async def test_rejection_requires_reason(self):
        """Test that rejection requires a reason."""
        service = ApprovalService()

        approver_id = uuid4()
        chain = await service.create_approval_chain(
            name="Test Chain",
            description="Test rejection reason",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[approver_id], min_approvals=1)
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        request = await service.create_change_request(
            title="Test Request",
            description="Test",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="add",
            change_details={}
        )

        await service.submit_change_request(request.request_id)

        # Try to reject without reason (should raise error)
        with pytest.raises(ValueError, match="reason is required"):
            await service.reject(
                request_id=request.request_id,
                approver_id=approver_id,
                approver_name="approver",
                reason=""  # Empty reason
            )


# ============================================================================
# Property 43: Approval Chain Configuration Validation
# ============================================================================

class TestApprovalChainConfigurationValidation:
    """Test approval chain configuration validation.

    Property: Approval chains must be valid configurations with 1-5 levels.

    Requirements: 13.1, 13.5
    """

    @pytest.mark.asyncio
    async def test_create_valid_approval_chain(self):
        """Test creating valid approval chains with different configurations."""
        service = ApprovalService()

        # Single level chain
        chain1 = await service.create_approval_chain(
            name="Single Level",
            description="One approval level",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[uuid4()], min_approvals=1)
            ],
            created_by=uuid4()
        )
        assert len(chain1.levels) == 1

        # Five level chain (maximum)
        chain2 = await service.create_approval_chain(
            name="Five Level",
            description="Maximum levels",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=i, approver_ids=[uuid4()], min_approvals=1)
                for i in range(1, 6)
            ],
            created_by=uuid4()
        )
        assert len(chain2.levels) == 5

    @pytest.mark.asyncio
    async def test_reject_invalid_level_count(self):
        """Test that chains with invalid level counts are rejected."""
        service = ApprovalService()

        # Zero levels (should fail)
        with pytest.raises(ValueError, match="1-5 levels"):
            await service.create_approval_chain(
                name="Zero Levels",
                description="Invalid",
                approval_type=ApprovalType.SEQUENTIAL,
                levels=[],
                created_by=uuid4()
            )

        # Six levels (should fail)
        with pytest.raises(ValueError, match="1-5 levels"):
            await service.create_approval_chain(
                name="Six Levels",
                description="Invalid",
                approval_type=ApprovalType.SEQUENTIAL,
                levels=[
                    ApprovalLevel(level_number=i, approver_ids=[uuid4()], min_approvals=1)
                    for i in range(1, 7)  # 6 levels
                ],
                created_by=uuid4()
            )

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_approval(self):
        """Test parallel vs sequential approval types."""
        service = ApprovalService()

        # Sequential approval
        chain_seq = await service.create_approval_chain(
            name="Sequential",
            description="Sequential approval",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[uuid4()], min_approvals=1),
                ApprovalLevel(level_number=2, approver_ids=[uuid4()], min_approvals=1),
            ],
            created_by=uuid4()
        )
        assert chain_seq.approval_type == ApprovalType.SEQUENTIAL

        # Parallel approval
        chain_par = await service.create_approval_chain(
            name="Parallel",
            description="Parallel approval",
            approval_type=ApprovalType.PARALLEL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[uuid4(), uuid4()], min_approvals=2),
            ],
            created_by=uuid4()
        )
        assert chain_par.approval_type == ApprovalType.PARALLEL

    @pytest.mark.asyncio
    async def test_min_approvals_requirement(self):
        """Test that minimum approvals requirement is enforced."""
        service = ApprovalService()

        # Create chain requiring 2 approvals
        approver1_id = uuid4()
        approver2_id = uuid4()

        chain = await service.create_approval_chain(
            name="Two Approvals",
            description="Requires 2 approvals",
            approval_type=ApprovalType.PARALLEL,
            levels=[
                ApprovalLevel(
                    level_number=1,
                    approver_ids=[approver1_id, approver2_id],
                    min_approvals=2
                )
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        # Create and submit request
        request = await service.create_change_request(
            title="Test",
            description="Test min approvals",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="add",
            change_details={}
        )

        await service.submit_change_request(request.request_id)

        # First approval (should not complete)
        await service.approve(request.request_id, approver1_id, "approver1")

        async with service._lock:
            request_data = service._change_requests[request.request_id]
            assert request_data.status == ChangeRequestStatus.IN_REVIEW
            assert request_data.current_level == 1  # Still at level 1

        # Second approval (should complete)
        await service.approve(request.request_id, approver2_id, "approver2")

        async with service._lock:
            request_data = service._change_requests[request.request_id]
            assert request_data.status == ChangeRequestStatus.APPROVED


# ============================================================================
# Pending Approvals and Routing Tests
# ============================================================================

class TestPendingApprovalsAndRouting:
    """Test pending approvals query and routing.

    Requirements: 4.1, 13.2
    """

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self):
        """Test retrieving pending approvals for an approver."""
        service = ApprovalService()

        approver_id = uuid4()
        chain = await service.create_approval_chain(
            name="Test Chain",
            description="Test pending approvals",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(level_number=1, approver_ids=[approver_id], min_approvals=1)
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        # Create multiple requests
        request1 = await service.create_change_request(
            title="Request 1",
            description="First request",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="add",
            change_details={}
        )

        request2 = await service.create_change_request(
            title="Request 2",
            description="Second request",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="modify",
            change_details={}
        )

        await service.submit_change_request(request1.request_id)
        await service.submit_change_request(request2.request_id)

        # Get pending approvals
        pending = await service.get_pending_approvals(approver_id)

        assert len(pending) == 2
        assert all(r.status == ChangeRequestStatus.IN_REVIEW for r in pending)

    @pytest.mark.asyncio
    async def test_pending_approvals_sorted_by_deadline(self):
        """Test that pending approvals are sorted by deadline (urgent first)."""
        service = ApprovalService()

        approver_id = uuid4()

        # Create chain with short deadline
        chain = await service.create_approval_chain(
            name="Test Chain",
            description="Test deadline sorting",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(
                    level_number=1,
                    approver_ids=[approver_id],
                    min_approvals=1,
                    deadline_hours=1  # Short deadline
                )
            ],
            created_by=uuid4(),
            ontology_area="urgent"
        )

        # Create chain with long deadline
        chain2 = await service.create_approval_chain(
            name="Test Chain 2",
            description="Test deadline sorting",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(
                    level_number=1,
                    approver_ids=[approver_id],
                    min_approvals=1,
                    deadline_hours=48  # Long deadline
                )
            ],
            created_by=uuid4(),
            ontology_area="normal"
        )

        # Create requests
        request_normal = await service.create_change_request(
            title="Normal Request",
            description="Normal priority",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="normal",
            change_type="add",
            change_details={}
        )

        request_urgent = await service.create_change_request(
            title="Urgent Request",
            description="Urgent priority",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="urgent",
            change_type="add",
            change_details={}
        )

        await service.submit_change_request(request_normal.request_id)
        await service.submit_change_request(request_urgent.request_id)

        # Get pending approvals
        pending = await service.get_pending_approvals(approver_id)

        # Urgent request should come first
        assert len(pending) == 2
        assert pending[0].title == "Urgent Request"


# ============================================================================
# Escalation Tests
# ============================================================================

class TestEscalation:
    """Test deadline escalation.

    Requirements: 13.3
    """

    @pytest.mark.asyncio
    async def test_escalation_on_missed_deadline(self):
        """Test that missed deadlines trigger escalation."""
        service = ApprovalService()
        service._default_deadline_hours = 0  # Set to 0 for immediate expiration

        approver_id = uuid4()
        chain = await service.create_approval_chain(
            name="Test Chain",
            description="Test escalation",
            approval_type=ApprovalType.SEQUENTIAL,
            levels=[
                ApprovalLevel(
                    level_number=1,
                    approver_ids=[approver_id],
                    min_approvals=1,
                    deadline_hours=0  # Immediate deadline for testing
                )
            ],
            created_by=uuid4(),
            ontology_area="test_area"
        )

        request = await service.create_change_request(
            title="Test Request",
            description="Will miss deadline",
            requester_id=uuid4(),
            requester_name="requester",
            ontology_id=uuid4(),
            ontology_area="test_area",
            change_type="add",
            change_details={}
        )

        await service.submit_change_request(request.request_id)

        # Manually set deadline to past
        async with service._lock:
            request_data = service._change_requests[request.request_id]
            for record in request_data.approval_records:
                record.deadline = datetime.utcnow() - timedelta(hours=1)

        # Check escalations
        escalated = await service.check_escalations()

        assert escalated >= 1

        # Verify escalation status
        async with service._lock:
            request_data = service._change_requests[request.request_id]
            record = request_data.approval_records[0]
            assert record.is_escalated
            assert record.status == ApprovalStatus.ESCALATED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
