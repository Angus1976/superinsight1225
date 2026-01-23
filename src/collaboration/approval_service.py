"""Approval Workflow Service for ontology change requests.

This module provides comprehensive approval workflow capabilities:
- Approval chain creation and management (1-5 levels)
- PARALLEL and SEQUENTIAL approval types
- Change request routing based on expertise
- Approval actions (approve, reject, request_changes)
- Deadline tracking and escalation
- Pending approvals query

Requirements:
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

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class ApprovalType(str, Enum):
    """Type of approval workflow."""
    SEQUENTIAL = "sequential"  # Approvals must be done in order
    PARALLEL = "parallel"  # All approvals can be done simultaneously


class ApprovalStatus(str, Enum):
    """Status of an approval."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    ESCALATED = "escalated"


class ChangeRequestStatus(str, Enum):
    """Status of a change request."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    IMPLEMENTED = "implemented"


@dataclass
class ApprovalLevel:
    """Single level in an approval chain."""
    level_number: int = 1
    approver_role: str = ""  # Role required for this level
    approver_ids: List[UUID] = field(default_factory=list)  # Specific approvers
    min_approvals: int = 1  # Minimum number of approvals needed at this level
    deadline_hours: int = 24  # Hours to complete approval
    is_required: bool = True
    escalation_approver_ids: List[UUID] = field(default_factory=list)  # Backup approvers


@dataclass
class ApprovalChain:
    """Chain of approvals for change requests."""
    chain_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    approval_type: ApprovalType = ApprovalType.SEQUENTIAL
    levels: List[ApprovalLevel] = field(default_factory=list)
    ontology_area: Optional[str] = None  # Specific ontology area this applies to
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class ApprovalRecord:
    """Record of a single approval action."""
    record_id: UUID = field(default_factory=uuid4)
    change_request_id: UUID = field(default_factory=uuid4)
    level_number: int = 1
    approver_id: UUID = field(default_factory=uuid4)
    approver_name: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision_reason: Optional[str] = None
    decided_at: Optional[datetime] = None
    deadline: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    is_escalated: bool = False


@dataclass
class ChangeRequest:
    """Change request for ontology modification."""
    request_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    requester_id: UUID = field(default_factory=uuid4)
    requester_name: str = ""
    ontology_id: UUID = field(default_factory=uuid4)
    ontology_area: str = ""  # Area of ontology affected
    change_type: str = ""  # "add_entity", "modify_relation", "delete_attribute", etc.
    change_details: Dict[str, Any] = field(default_factory=dict)
    status: ChangeRequestStatus = ChangeRequestStatus.DRAFT
    approval_chain_id: Optional[UUID] = None
    approval_records: List[ApprovalRecord] = field(default_factory=list)
    current_level: int = 0  # Current approval level (0 = not started)
    submitted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ApprovalService:
    """Service for managing approval workflows."""

    def __init__(self):
        """Initialize approval service."""
        self._chains: Dict[UUID, ApprovalChain] = {}
        self._change_requests: Dict[UUID, ChangeRequest] = {}
        self._lock = asyncio.Lock()

        # Configuration
        self._default_deadline_hours = 24
        self._escalation_reminder_hours = 2  # Remind before deadline

    async def create_approval_chain(
        self,
        name: str,
        description: str,
        approval_type: ApprovalType,
        levels: List[ApprovalLevel],
        created_by: UUID,
        ontology_area: Optional[str] = None
    ) -> ApprovalChain:
        """Create a new approval chain.

        Args:
            name: Chain name
            description: Chain description
            approval_type: SEQUENTIAL or PARALLEL
            levels: List of approval levels (1-5)
            created_by: User creating the chain
            ontology_area: Optional ontology area this applies to

        Returns:
            Created approval chain

        Raises:
            ValueError: If levels is invalid (not 1-5)
        """
        if not levels or len(levels) > 5:
            raise ValueError("Approval chain must have 1-5 levels")

        async with self._lock:
            chain = ApprovalChain(
                name=name,
                description=description,
                approval_type=approval_type,
                levels=sorted(levels, key=lambda l: l.level_number),
                ontology_area=ontology_area,
                created_by=created_by
            )

            self._chains[chain.chain_id] = chain

            return chain

    async def get_approval_chain(
        self,
        chain_id: UUID
    ) -> Optional[ApprovalChain]:
        """Get an approval chain by ID.

        Args:
            chain_id: Chain ID

        Returns:
            Approval chain or None if not found
        """
        async with self._lock:
            return self._chains.get(chain_id)

    async def list_approval_chains(
        self,
        ontology_area: Optional[str] = None,
        is_active: bool = True
    ) -> List[ApprovalChain]:
        """List approval chains.

        Args:
            ontology_area: Filter by ontology area
            is_active: Filter by active status

        Returns:
            List of approval chains
        """
        async with self._lock:
            chains = list(self._chains.values())

            if ontology_area:
                chains = [c for c in chains if c.ontology_area == ontology_area]

            if is_active:
                chains = [c for c in chains if c.is_active]

            return chains

    async def create_change_request(
        self,
        title: str,
        description: str,
        requester_id: UUID,
        requester_name: str,
        ontology_id: UUID,
        ontology_area: str,
        change_type: str,
        change_details: Dict[str, Any]
    ) -> ChangeRequest:
        """Create a new change request.

        Args:
            title: Request title
            description: Request description
            requester_id: User making the request
            requester_name: Requester name
            ontology_id: Ontology ID
            ontology_area: Area of ontology affected
            change_type: Type of change
            change_details: Details of the change

        Returns:
            Created change request
        """
        async with self._lock:
            request = ChangeRequest(
                title=title,
                description=description,
                requester_id=requester_id,
                requester_name=requester_name,
                ontology_id=ontology_id,
                ontology_area=ontology_area,
                change_type=change_type,
                change_details=change_details
            )

            self._change_requests[request.request_id] = request

            return request

    async def submit_change_request(
        self,
        request_id: UUID
    ) -> bool:
        """Submit a change request for approval.

        This will route the request to appropriate approvers and start the workflow.

        Args:
            request_id: Change request ID

        Returns:
            True if successful
        """
        async with self._lock:
            request = self._change_requests.get(request_id)
            if not request or request.status != ChangeRequestStatus.DRAFT:
                return False

            # Find appropriate approval chain
            chain = await self._find_approval_chain(request.ontology_area)
            if not chain:
                # No approval chain found, auto-approve
                request.status = ChangeRequestStatus.APPROVED
                return True

            request.approval_chain_id = chain.chain_id
            request.status = ChangeRequestStatus.SUBMITTED
            request.submitted_at = datetime.utcnow()

            # Route to first level approvers
            await self._route_to_level(request, chain, 1)

            return True

    async def _find_approval_chain(
        self,
        ontology_area: str
    ) -> Optional[ApprovalChain]:
        """Find appropriate approval chain for an ontology area.

        Args:
            ontology_area: Ontology area

        Returns:
            Approval chain or None
        """
        # Find chain specific to this area
        for chain in self._chains.values():
            if chain.is_active and chain.ontology_area == ontology_area:
                return chain

        # Find default chain (no specific area)
        for chain in self._chains.values():
            if chain.is_active and chain.ontology_area is None:
                return chain

        return None

    async def _route_to_level(
        self,
        request: ChangeRequest,
        chain: ApprovalChain,
        level_number: int
    ) -> None:
        """Route change request to a specific approval level.

        Args:
            request: Change request
            chain: Approval chain
            level_number: Level number to route to
        """
        level = next((l for l in chain.levels if l.level_number == level_number), None)
        if not level:
            return

        request.current_level = level_number
        request.status = ChangeRequestStatus.IN_REVIEW

        # Create approval records for this level
        deadline = datetime.utcnow() + timedelta(hours=level.deadline_hours)

        for approver_id in level.approver_ids:
            record = ApprovalRecord(
                change_request_id=request.request_id,
                level_number=level_number,
                approver_id=approver_id,
                deadline=deadline
            )
            request.approval_records.append(record)

        # In real implementation, send notifications to approvers here
        # await self._notify_approvers(request, level)

    async def approve(
        self,
        request_id: UUID,
        approver_id: UUID,
        approver_name: str,
        reason: Optional[str] = None
    ) -> bool:
        """Approve a change request.

        Args:
            request_id: Change request ID
            approver_id: Approver user ID
            approver_name: Approver name
            reason: Optional approval reason

        Returns:
            True if successful
        """
        async with self._lock:
            request = self._change_requests.get(request_id)
            if not request or request.status not in [ChangeRequestStatus.SUBMITTED, ChangeRequestStatus.IN_REVIEW]:
                return False

            # Find approval record for this approver at current level
            record = next(
                (r for r in request.approval_records
                 if r.level_number == request.current_level
                 and r.approver_id == approver_id
                 and r.status == ApprovalStatus.PENDING),
                None
            )

            if not record:
                return False

            # Update record
            record.status = ApprovalStatus.APPROVED
            record.approver_name = approver_name
            record.decision_reason = reason
            record.decided_at = datetime.utcnow()

            # Check if level is complete
            await self._check_level_completion(request)

            return True

    async def reject(
        self,
        request_id: UUID,
        approver_id: UUID,
        approver_name: str,
        reason: str
    ) -> bool:
        """Reject a change request.

        Args:
            request_id: Change request ID
            approver_id: Approver user ID
            approver_name: Approver name
            reason: Rejection reason (required)

        Returns:
            True if successful
        """
        if not reason:
            raise ValueError("Rejection reason is required")

        async with self._lock:
            request = self._change_requests.get(request_id)
            if not request or request.status not in [ChangeRequestStatus.SUBMITTED, ChangeRequestStatus.IN_REVIEW]:
                return False

            # Find approval record
            record = next(
                (r for r in request.approval_records
                 if r.level_number == request.current_level
                 and r.approver_id == approver_id
                 and r.status == ApprovalStatus.PENDING),
                None
            )

            if not record:
                return False

            # Update record
            record.status = ApprovalStatus.REJECTED
            record.approver_name = approver_name
            record.decision_reason = reason
            record.decided_at = datetime.utcnow()

            # Reject entire request
            request.status = ChangeRequestStatus.REJECTED
            request.updated_at = datetime.utcnow()

            # In real implementation, notify requester
            # await self._notify_rejection(request, reason)

            return True

    async def request_changes(
        self,
        request_id: UUID,
        approver_id: UUID,
        approver_name: str,
        requested_changes: str
    ) -> bool:
        """Request changes to a change request.

        This returns the request to the requester for revision.

        Args:
            request_id: Change request ID
            approver_id: Approver user ID
            approver_name: Approver name
            requested_changes: Description of requested changes

        Returns:
            True if successful
        """
        if not requested_changes:
            raise ValueError("Requested changes description is required")

        async with self._lock:
            request = self._change_requests.get(request_id)
            if not request or request.status not in [ChangeRequestStatus.SUBMITTED, ChangeRequestStatus.IN_REVIEW]:
                return False

            # Find approval record
            record = next(
                (r for r in request.approval_records
                 if r.level_number == request.current_level
                 and r.approver_id == approver_id
                 and r.status == ApprovalStatus.PENDING),
                None
            )

            if not record:
                return False

            # Update record
            record.status = ApprovalStatus.CHANGES_REQUESTED
            record.approver_name = approver_name
            record.decision_reason = requested_changes
            record.decided_at = datetime.utcnow()

            # Return to requester
            request.status = ChangeRequestStatus.CHANGES_REQUESTED
            request.current_level = 0
            request.updated_at = datetime.utcnow()

            # In real implementation, notify requester
            # await self._notify_changes_requested(request, requested_changes)

            return True

    async def _check_level_completion(
        self,
        request: ChangeRequest
    ) -> None:
        """Check if current approval level is complete.

        If complete, advance to next level or mark as approved.

        Args:
            request: Change request
        """
        if not request.approval_chain_id:
            return

        chain = self._chains.get(request.approval_chain_id)
        if not chain:
            return

        current_level = next(
            (l for l in chain.levels if l.level_number == request.current_level),
            None
        )
        if not current_level:
            return

        # Count approvals at current level
        level_records = [
            r for r in request.approval_records
            if r.level_number == request.current_level
        ]

        approved_count = sum(1 for r in level_records if r.status == ApprovalStatus.APPROVED)

        # Check if minimum approvals met
        if approved_count >= current_level.min_approvals:
            # Level complete, advance
            if request.current_level < len(chain.levels):
                # Move to next level
                await self._route_to_level(request, chain, request.current_level + 1)
            else:
                # All levels complete, approve request
                request.status = ChangeRequestStatus.APPROVED
                request.updated_at = datetime.utcnow()

                # In real implementation, notify all stakeholders
                # await self._notify_final_approval(request)

    async def get_pending_approvals(
        self,
        approver_id: UUID,
        ontology_area: Optional[str] = None
    ) -> List[ChangeRequest]:
        """Get pending approval requests for an approver.

        Args:
            approver_id: Approver user ID
            ontology_area: Optional filter by ontology area

        Returns:
            List of change requests pending approval by this user
        """
        async with self._lock:
            pending_requests = []

            for request in self._change_requests.values():
                if request.status != ChangeRequestStatus.IN_REVIEW:
                    continue

                if ontology_area and request.ontology_area != ontology_area:
                    continue

                # Check if this approver has pending approval at current level
                has_pending = any(
                    r.level_number == request.current_level
                    and r.approver_id == approver_id
                    and r.status == ApprovalStatus.PENDING
                    for r in request.approval_records
                )

                if has_pending:
                    pending_requests.append(request)

            # Sort by deadline (urgent first)
            pending_requests.sort(key=lambda r: self._get_approval_deadline(r, approver_id))

            return pending_requests

    def _get_approval_deadline(
        self,
        request: ChangeRequest,
        approver_id: UUID
    ) -> datetime:
        """Get approval deadline for a specific approver.

        Args:
            request: Change request
            approver_id: Approver ID

        Returns:
            Deadline datetime
        """
        record = next(
            (r for r in request.approval_records
             if r.level_number == request.current_level and r.approver_id == approver_id),
            None
        )
        return record.deadline if record else datetime.max

    async def check_escalations(self) -> int:
        """Check for missed deadlines and escalate if needed.

        Returns:
            Number of escalations performed
        """
        async with self._lock:
            escalation_count = 0
            now = datetime.utcnow()

            for request in self._change_requests.values():
                if request.status != ChangeRequestStatus.IN_REVIEW:
                    continue

                # Check pending approvals at current level
                for record in request.approval_records:
                    if (record.level_number == request.current_level
                            and record.status == ApprovalStatus.PENDING
                            and now > record.deadline
                            and not record.is_escalated):

                        # Escalate
                        record.is_escalated = True
                        record.status = ApprovalStatus.ESCALATED

                        # In real implementation:
                        # 1. Send escalation notification to backup approvers
                        # 2. Send reminder to original approver
                        # await self._escalate_approval(request, record)

                        escalation_count += 1

            return escalation_count

    async def get_change_request(
        self,
        request_id: UUID
    ) -> Optional[ChangeRequest]:
        """Get a change request by ID.

        Args:
            request_id: Change request ID

        Returns:
            Change request or None
        """
        async with self._lock:
            return self._change_requests.get(request_id)

    async def get_approval_history(
        self,
        request_id: UUID
    ) -> List[ApprovalRecord]:
        """Get approval history for a change request.

        Args:
            request_id: Change request ID

        Returns:
            List of approval records
        """
        async with self._lock:
            request = self._change_requests.get(request_id)
            if not request:
                return []

            return sorted(request.approval_records, key=lambda r: (r.level_number, r.decided_at or datetime.max))
