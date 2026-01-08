"""
Push Result Verifier.

Handles verification and confirmation of push results:
- Push result validation and verification
- Data integrity checks
- Confirmation mechanisms
- Rollback capabilities
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select

from src.database.connection import db_manager
from src.sync.models import SyncAuditLogModel, AuditAction
from .incremental_push import ChangeRecord, PushResult
from .target_manager import PushTargetConfig

logger = logging.getLogger(__name__)


class VerificationRule(BaseModel):
    """Verification rule configuration."""
    rule_id: str
    name: str
    description: Optional[str] = None
    rule_type: str  # checksum, count, content, schema, custom
    enabled: bool = True
    
    # Rule configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Thresholds and limits
    error_threshold: float = 0.0  # Percentage of errors allowed
    timeout_seconds: int = 300  # Verification timeout
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 5


class VerificationResult(BaseModel):
    """Result of a verification check."""
    verification_id: str
    rule_id: str
    target_id: str
    status: str  # success, failed, timeout, error
    
    # Verification details
    records_verified: int = 0
    records_failed: int = 0
    verification_time_ms: float = 0.0
    
    # Error information
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Verification data
    expected_checksum: Optional[str] = None
    actual_checksum: Optional[str] = None
    expected_count: Optional[int] = None
    actual_count: Optional[int] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConfirmationRequest(BaseModel):
    """Push confirmation request."""
    push_id: str
    target_id: str
    confirmation_type: str  # auto, manual, delayed
    
    # Confirmation criteria
    required_verifications: List[str] = Field(default_factory=list)
    confirmation_timeout: Optional[datetime] = None
    
    # Callback configuration
    callback_url: Optional[str] = None
    callback_headers: Dict[str, str] = Field(default_factory=dict)


class ConfirmationResult(BaseModel):
    """Result of push confirmation."""
    confirmation_id: str
    push_id: str
    target_id: str
    status: str  # confirmed, rejected, timeout, pending
    
    # Confirmation details
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None  # user_id or system
    rejection_reason: Optional[str] = None
    
    # Verification results
    verification_results: List[VerificationResult] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RollbackPlan(BaseModel):
    """Rollback plan for failed pushes."""
    rollback_id: str
    push_id: str
    target_id: str
    
    # Rollback strategy
    strategy: str  # compensating_transaction, restore_backup, manual
    
    # Rollback operations
    operations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Rollback status
    status: str = "planned"  # planned, executing, completed, failed
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PushResultVerifier:
    """
    Enterprise push result verifier.
    
    Provides comprehensive verification and confirmation of push operations
    including data integrity checks, result validation, and rollback capabilities.
    """
    
    def __init__(self):
        self._verification_rules: Dict[str, VerificationRule] = {}
        self._verification_results: Dict[str, VerificationResult] = {}
        self._confirmation_requests: Dict[str, ConfirmationRequest] = {}
        self._confirmation_results: Dict[str, ConfirmationResult] = {}
        self._rollback_plans: Dict[str, RollbackPlan] = {}
        
        # Initialize default verification rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default verification rules."""
        # Record count verification
        count_rule = VerificationRule(
            rule_id="record_count",
            name="Record Count Verification",
            description="Verify that the number of records pushed matches expected count",
            rule_type="count",
            config={
                "tolerance_percentage": 0.0  # Exact match required
            }
        )
        self._verification_rules[count_rule.rule_id] = count_rule
        
        # Data checksum verification
        checksum_rule = VerificationRule(
            rule_id="data_checksum",
            name="Data Checksum Verification", 
            description="Verify data integrity using checksums",
            rule_type="checksum",
            config={
                "algorithm": "sha256",
                "include_metadata": False
            }
        )
        self._verification_rules[checksum_rule.rule_id] = checksum_rule
        
        # Content verification
        content_rule = VerificationRule(
            rule_id="content_verification",
            name="Content Verification",
            description="Verify that pushed content matches source data",
            rule_type="content",
            config={
                "sample_percentage": 10.0,  # Verify 10% of records
                "key_fields": ["id", "timestamp"]
            }
        )
        self._verification_rules[content_rule.rule_id] = content_rule
    
    async def verify_push_result(
        self,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord],
        verification_rules: Optional[List[str]] = None
    ) -> List[VerificationResult]:
        """
        Verify push result against configured rules.
        
        Args:
            push_result: Result of the push operation
            target: Target configuration
            original_changes: Original change records that were pushed
            verification_rules: List of rule IDs to apply (None for all)
            
        Returns:
            List of verification results
        """
        try:
            # Determine which rules to apply
            rules_to_apply = verification_rules or list(self._verification_rules.keys())
            
            # Filter rules based on target configuration
            applicable_rules = []
            for rule_id in rules_to_apply:
                rule = self._verification_rules.get(rule_id)
                if rule and rule.enabled and self._is_rule_applicable(rule, target):
                    applicable_rules.append(rule)
            
            if not applicable_rules:
                logger.warning(f"No applicable verification rules for target {target.target_id}")
                return []
            
            # Execute verification rules
            verification_tasks = []
            for rule in applicable_rules:
                task = self._execute_verification_rule(
                    rule, push_result, target, original_changes
                )
                verification_tasks.append(task)
            
            # Wait for all verifications to complete
            results = await asyncio.gather(*verification_tasks, return_exceptions=True)
            
            # Process results
            verification_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Verification rule {applicable_rules[i].rule_id} failed: {result}")
                    # Create failed verification result
                    failed_result = VerificationResult(
                        verification_id=str(uuid4()),
                        rule_id=applicable_rules[i].rule_id,
                        target_id=target.target_id,
                        status="error",
                        error_message=str(result)
                    )
                    verification_results.append(failed_result)
                else:
                    verification_results.append(result)
            
            # Store verification results
            for result in verification_results:
                self._verification_results[result.verification_id] = result
            
            # Log verification summary
            successful_verifications = len([r for r in verification_results if r.status == "success"])
            logger.info(
                f"Verification completed for push {push_result.push_id}: "
                f"{successful_verifications}/{len(verification_results)} rules passed"
            )
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Error verifying push result: {e}")
            return []
    
    def _is_rule_applicable(self, rule: VerificationRule, target: PushTargetConfig) -> bool:
        """Check if a verification rule is applicable to the target."""
        # Check target type compatibility
        target_types = rule.config.get("applicable_target_types", [])
        if target_types and target.target_type not in target_types:
            return False
        
        # Check if target supports the verification type
        if rule.rule_type == "checksum" and not target.connection_config.get("supports_checksum", True):
            return False
        
        if rule.rule_type == "content" and not target.connection_config.get("supports_read_back", True):
            return False
        
        return True
    
    async def _execute_verification_rule(
        self,
        rule: VerificationRule,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> VerificationResult:
        """Execute a specific verification rule."""
        verification_id = str(uuid4())
        start_time = datetime.utcnow()
        
        try:
            if rule.rule_type == "count":
                result = await self._verify_record_count(
                    verification_id, rule, push_result, target, original_changes
                )
            elif rule.rule_type == "checksum":
                result = await self._verify_data_checksum(
                    verification_id, rule, push_result, target, original_changes
                )
            elif rule.rule_type == "content":
                result = await self._verify_content_integrity(
                    verification_id, rule, push_result, target, original_changes
                )
            elif rule.rule_type == "schema":
                result = await self._verify_schema_compliance(
                    verification_id, rule, push_result, target, original_changes
                )
            elif rule.rule_type == "custom":
                result = await self._verify_custom_rule(
                    verification_id, rule, push_result, target, original_changes
                )
            else:
                raise ValueError(f"Unknown verification rule type: {rule.rule_type}")
            
            # Calculate verification time
            verification_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.verification_time_ms = verification_time
            
            return result
            
        except Exception as e:
            verification_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return VerificationResult(
                verification_id=verification_id,
                rule_id=rule.rule_id,
                target_id=target.target_id,
                status="error",
                verification_time_ms=verification_time,
                error_message=str(e)
            )
    
    async def _verify_record_count(
        self,
        verification_id: str,
        rule: VerificationRule,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> VerificationResult:
        """Verify that record count matches expected value."""
        expected_count = len(original_changes)
        actual_count = push_result.records_pushed
        
        # Check tolerance
        tolerance_percentage = rule.config.get("tolerance_percentage", 0.0)
        tolerance = int(expected_count * tolerance_percentage / 100)
        
        count_diff = abs(expected_count - actual_count)
        status = "success" if count_diff <= tolerance else "failed"
        
        return VerificationResult(
            verification_id=verification_id,
            rule_id=rule.rule_id,
            target_id=target.target_id,
            status=status,
            records_verified=actual_count,
            records_failed=count_diff if status == "failed" else 0,
            expected_count=expected_count,
            actual_count=actual_count,
            error_message=f"Count mismatch: expected {expected_count}, got {actual_count}" if status == "failed" else None
        )
    
    async def _verify_data_checksum(
        self,
        verification_id: str,
        rule: VerificationRule,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> VerificationResult:
        """Verify data integrity using checksums."""
        algorithm = rule.config.get("algorithm", "sha256")
        include_metadata = rule.config.get("include_metadata", False)
        
        # Calculate expected checksum from original data
        expected_checksum = self._calculate_data_checksum(
            original_changes, algorithm, include_metadata
        )
        
        # Get actual checksum from target (simulated)
        actual_checksum = await self._get_target_checksum(
            target, push_result, algorithm
        )
        
        status = "success" if expected_checksum == actual_checksum else "failed"
        
        return VerificationResult(
            verification_id=verification_id,
            rule_id=rule.rule_id,
            target_id=target.target_id,
            status=status,
            records_verified=len(original_changes),
            records_failed=len(original_changes) if status == "failed" else 0,
            expected_checksum=expected_checksum,
            actual_checksum=actual_checksum,
            error_message=f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}" if status == "failed" else None
        )
    
    async def _verify_content_integrity(
        self,
        verification_id: str,
        rule: VerificationRule,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> VerificationResult:
        """Verify content integrity by sampling records."""
        sample_percentage = rule.config.get("sample_percentage", 10.0)
        key_fields = rule.config.get("key_fields", ["id"])
        
        # Select sample records
        sample_size = max(1, int(len(original_changes) * sample_percentage / 100))
        sample_changes = original_changes[:sample_size]  # Simple sampling
        
        # Verify sample records (simulated)
        verified_count = 0
        failed_count = 0
        
        for change in sample_changes:
            # Simulate content verification
            await asyncio.sleep(0.001)  # Simulate verification time
            
            # In production, this would read back the data from target and compare
            is_valid = await self._verify_record_content(change, target, key_fields)
            
            if is_valid:
                verified_count += 1
            else:
                failed_count += 1
        
        # Calculate overall status
        error_rate = failed_count / len(sample_changes) if sample_changes else 0
        error_threshold = rule.error_threshold / 100
        status = "success" if error_rate <= error_threshold else "failed"
        
        return VerificationResult(
            verification_id=verification_id,
            rule_id=rule.rule_id,
            target_id=target.target_id,
            status=status,
            records_verified=verified_count,
            records_failed=failed_count,
            error_message=f"Content verification failed for {failed_count}/{len(sample_changes)} sample records" if status == "failed" else None
        )
    
    async def _verify_schema_compliance(
        self,
        verification_id: str,
        rule: VerificationRule,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> VerificationResult:
        """Verify schema compliance of pushed data."""
        # Simulate schema verification
        await asyncio.sleep(0.05)  # Simulate schema check time
        
        # In production, this would validate the schema of pushed data
        schema_valid = True  # Assume valid for simulation
        
        return VerificationResult(
            verification_id=verification_id,
            rule_id=rule.rule_id,
            target_id=target.target_id,
            status="success" if schema_valid else "failed",
            records_verified=len(original_changes),
            records_failed=0 if schema_valid else len(original_changes),
            error_message=None if schema_valid else "Schema validation failed"
        )
    
    async def _verify_custom_rule(
        self,
        verification_id: str,
        rule: VerificationRule,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> VerificationResult:
        """Execute custom verification rule."""
        # Simulate custom rule execution
        await asyncio.sleep(0.02)
        
        # In production, this would execute custom verification logic
        custom_result = True  # Assume success for simulation
        
        return VerificationResult(
            verification_id=verification_id,
            rule_id=rule.rule_id,
            target_id=target.target_id,
            status="success" if custom_result else "failed",
            records_verified=len(original_changes),
            records_failed=0 if custom_result else len(original_changes),
            error_message=None if custom_result else "Custom verification failed"
        )
    
    def _calculate_data_checksum(
        self,
        changes: List[ChangeRecord],
        algorithm: str,
        include_metadata: bool
    ) -> str:
        """Calculate checksum for change records."""
        hasher = hashlib.new(algorithm)
        
        for change in changes:
            # Create deterministic string representation
            data_str = f"{change.record_id}:{change.operation}:{change.table_name}"
            
            if change.new_data:
                # Sort keys for deterministic ordering
                sorted_data = {k: change.new_data[k] for k in sorted(change.new_data.keys())}
                data_str += f":{str(sorted_data)}"
            
            if include_metadata and change.metadata:
                sorted_metadata = {k: change.metadata[k] for k in sorted(change.metadata.keys())}
                data_str += f":{str(sorted_metadata)}"
            
            hasher.update(data_str.encode('utf-8'))
        
        return hasher.hexdigest()
    
    async def _get_target_checksum(
        self,
        target: PushTargetConfig,
        push_result: PushResult,
        algorithm: str
    ) -> str:
        """Get checksum from target system."""
        # Simulate getting checksum from target
        await asyncio.sleep(0.01)
        
        # In production, this would query the target system for actual checksum
        # For simulation, return a consistent checksum based on push result
        hasher = hashlib.new(algorithm)
        hasher.update(f"{push_result.push_id}:{push_result.records_pushed}".encode('utf-8'))
        return hasher.hexdigest()
    
    async def _verify_record_content(
        self,
        change: ChangeRecord,
        target: PushTargetConfig,
        key_fields: List[str]
    ) -> bool:
        """Verify content of a specific record."""
        # Simulate record content verification
        await asyncio.sleep(0.001)
        
        # In production, this would read the record from target and compare
        return True  # Assume valid for simulation
    
    async def request_confirmation(
        self,
        push_result: PushResult,
        target: PushTargetConfig,
        confirmation_type: str = "auto",
        required_verifications: Optional[List[str]] = None,
        timeout_minutes: int = 30
    ) -> ConfirmationRequest:
        """
        Request confirmation for a push operation.
        
        Args:
            push_result: Push result to confirm
            target: Target configuration
            confirmation_type: Type of confirmation (auto, manual, delayed)
            required_verifications: List of verification rule IDs that must pass
            timeout_minutes: Confirmation timeout in minutes
            
        Returns:
            Confirmation request
        """
        try:
            confirmation_timeout = datetime.utcnow() + timedelta(minutes=timeout_minutes)
            
            request = ConfirmationRequest(
                push_id=push_result.push_id,
                target_id=target.target_id,
                confirmation_type=confirmation_type,
                required_verifications=required_verifications or [],
                confirmation_timeout=confirmation_timeout
            )
            
            self._confirmation_requests[push_result.push_id] = request
            
            logger.info(
                f"Confirmation requested for push {push_result.push_id} "
                f"(type: {confirmation_type}, timeout: {timeout_minutes}m)"
            )
            
            return request
            
        except Exception as e:
            logger.error(f"Error requesting confirmation: {e}")
            raise
    
    async def process_confirmation(
        self,
        push_id: str,
        verification_results: List[VerificationResult],
        confirmed_by: Optional[str] = None
    ) -> ConfirmationResult:
        """
        Process confirmation for a push operation.
        
        Args:
            push_id: Push operation ID
            verification_results: Results of verification checks
            confirmed_by: User ID who confirmed (None for automatic)
            
        Returns:
            Confirmation result
        """
        try:
            confirmation_id = str(uuid4())
            request = self._confirmation_requests.get(push_id)
            
            if not request:
                raise ValueError(f"No confirmation request found for push {push_id}")
            
            # Check if confirmation has timed out
            if request.confirmation_timeout and datetime.utcnow() > request.confirmation_timeout:
                result = ConfirmationResult(
                    confirmation_id=confirmation_id,
                    push_id=push_id,
                    target_id=request.target_id,
                    status="timeout",
                    verification_results=verification_results,
                    rejection_reason="Confirmation timeout exceeded"
                )
            else:
                # Check required verifications
                status = self._evaluate_confirmation_status(request, verification_results)
                
                result = ConfirmationResult(
                    confirmation_id=confirmation_id,
                    push_id=push_id,
                    target_id=request.target_id,
                    status=status,
                    confirmed_at=datetime.utcnow() if status == "confirmed" else None,
                    confirmed_by=confirmed_by or "system",
                    verification_results=verification_results,
                    rejection_reason=self._get_rejection_reason(request, verification_results) if status == "rejected" else None
                )
            
            self._confirmation_results[confirmation_id] = result
            
            # Log confirmation result
            await self._log_confirmation_audit(result)
            
            logger.info(f"Confirmation processed for push {push_id}: {result.status}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing confirmation: {e}")
            raise
    
    def _evaluate_confirmation_status(
        self,
        request: ConfirmationRequest,
        verification_results: List[VerificationResult]
    ) -> str:
        """Evaluate confirmation status based on verification results."""
        if not request.required_verifications:
            # No specific verifications required, check overall success
            failed_verifications = [r for r in verification_results if r.status != "success"]
            return "confirmed" if not failed_verifications else "rejected"
        
        # Check required verifications
        required_results = {
            r.rule_id: r for r in verification_results 
            if r.rule_id in request.required_verifications
        }
        
        # All required verifications must be present and successful
        for rule_id in request.required_verifications:
            if rule_id not in required_results:
                return "rejected"  # Missing required verification
            
            if required_results[rule_id].status != "success":
                return "rejected"  # Required verification failed
        
        return "confirmed"
    
    def _get_rejection_reason(
        self,
        request: ConfirmationRequest,
        verification_results: List[VerificationResult]
    ) -> str:
        """Get reason for confirmation rejection."""
        failed_verifications = [r for r in verification_results if r.status != "success"]
        
        if not failed_verifications:
            return "Unknown rejection reason"
        
        failed_rules = [r.rule_id for r in failed_verifications]
        return f"Failed verification rules: {', '.join(failed_rules)}"
    
    async def create_rollback_plan(
        self,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord],
        strategy: str = "compensating_transaction"
    ) -> RollbackPlan:
        """
        Create rollback plan for a failed or rejected push.
        
        Args:
            push_result: Push result to rollback
            target: Target configuration
            original_changes: Original change records
            strategy: Rollback strategy
            
        Returns:
            Rollback plan
        """
        try:
            rollback_id = str(uuid4())
            
            # Generate rollback operations based on strategy
            operations = await self._generate_rollback_operations(
                strategy, push_result, target, original_changes
            )
            
            plan = RollbackPlan(
                rollback_id=rollback_id,
                push_id=push_result.push_id,
                target_id=target.target_id,
                strategy=strategy,
                operations=operations
            )
            
            self._rollback_plans[rollback_id] = plan
            
            logger.info(
                f"Created rollback plan {rollback_id} for push {push_result.push_id} "
                f"using {strategy} strategy"
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Error creating rollback plan: {e}")
            raise
    
    async def _generate_rollback_operations(
        self,
        strategy: str,
        push_result: PushResult,
        target: PushTargetConfig,
        original_changes: List[ChangeRecord]
    ) -> List[Dict[str, Any]]:
        """Generate rollback operations based on strategy."""
        operations = []
        
        if strategy == "compensating_transaction":
            # Create compensating operations for each change
            for change in original_changes:
                if change.operation == "INSERT":
                    # Compensate INSERT with DELETE
                    operations.append({
                        "operation": "DELETE",
                        "table_name": change.table_name,
                        "record_id": change.record_id,
                        "where_clause": {"id": change.record_id}
                    })
                elif change.operation == "UPDATE":
                    # Compensate UPDATE with reverse UPDATE
                    operations.append({
                        "operation": "UPDATE",
                        "table_name": change.table_name,
                        "record_id": change.record_id,
                        "data": change.old_data,
                        "where_clause": {"id": change.record_id}
                    })
                elif change.operation == "DELETE":
                    # Compensate DELETE with INSERT
                    operations.append({
                        "operation": "INSERT",
                        "table_name": change.table_name,
                        "record_id": change.record_id,
                        "data": change.old_data
                    })
        
        elif strategy == "restore_backup":
            # Create backup restoration operation
            operations.append({
                "operation": "RESTORE_BACKUP",
                "backup_timestamp": push_result.timestamp,
                "tables": list(set(change.table_name for change in original_changes))
            })
        
        elif strategy == "manual":
            # Create manual intervention operations
            operations.append({
                "operation": "MANUAL_INTERVENTION",
                "description": f"Manual rollback required for push {push_result.push_id}",
                "affected_records": len(original_changes),
                "instructions": "Contact system administrator for manual rollback"
            })
        
        return operations
    
    async def execute_rollback(self, rollback_id: str) -> bool:
        """
        Execute a rollback plan.
        
        Args:
            rollback_id: Rollback plan ID
            
        Returns:
            True if rollback was successful
        """
        try:
            plan = self._rollback_plans.get(rollback_id)
            if not plan:
                raise ValueError(f"Rollback plan {rollback_id} not found")
            
            plan.status = "executing"
            plan.executed_at = datetime.utcnow()
            
            # Execute rollback operations
            for operation in plan.operations:
                await self._execute_rollback_operation(operation, plan)
            
            plan.status = "completed"
            plan.completed_at = datetime.utcnow()
            
            logger.info(f"Rollback {rollback_id} completed successfully")
            return True
            
        except Exception as e:
            if rollback_id in self._rollback_plans:
                self._rollback_plans[rollback_id].status = "failed"
            
            logger.error(f"Error executing rollback {rollback_id}: {e}")
            return False
    
    async def _execute_rollback_operation(
        self,
        operation: Dict[str, Any],
        plan: RollbackPlan
    ) -> None:
        """Execute a single rollback operation."""
        # Simulate rollback operation execution
        await asyncio.sleep(0.01)
        
        logger.info(
            f"Executing rollback operation: {operation['operation']} "
            f"for plan {plan.rollback_id}"
        )
        
        # In production, this would execute the actual rollback operation
        # based on the target type and operation details
    
    async def _log_confirmation_audit(self, result: ConfirmationResult) -> None:
        """Log confirmation result to audit trail."""
        try:
            with db_manager.get_session() as session:
                audit_log = SyncAuditLogModel(
                    tenant_id="system",  # Would get from context
                    action=AuditAction.DATA_PUSHED,
                    actor_type="system",
                    action_details={
                        "confirmation_id": result.confirmation_id,
                        "push_id": result.push_id,
                        "target_id": result.target_id,
                        "status": result.status,
                        "confirmed_by": result.confirmed_by,
                        "verification_count": len(result.verification_results)
                    },
                    success=result.status == "confirmed"
                )
                
                session.add(audit_log)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error logging confirmation audit: {e}")
    
    def get_verification_statistics(self, target_id: Optional[str] = None) -> Dict[str, Any]:
        """Get verification statistics."""
        results = list(self._verification_results.values())
        
        if target_id:
            results = [r for r in results if r.target_id == target_id]
        
        if not results:
            return {"total_verifications": 0}
        
        stats = {
            "total_verifications": len(results),
            "successful_verifications": len([r for r in results if r.status == "success"]),
            "failed_verifications": len([r for r in results if r.status == "failed"]),
            "error_verifications": len([r for r in results if r.status == "error"]),
            "average_verification_time_ms": sum(r.verification_time_ms for r in results) / len(results),
            "verification_by_rule": {},
            "verification_by_target": {}
        }
        
        # Group by rule
        for result in results:
            rule_id = result.rule_id
            if rule_id not in stats["verification_by_rule"]:
                stats["verification_by_rule"][rule_id] = {
                    "total": 0, "success": 0, "failed": 0, "error": 0
                }
            
            stats["verification_by_rule"][rule_id]["total"] += 1
            stats["verification_by_rule"][rule_id][result.status] += 1
        
        # Group by target
        for result in results:
            target_id = result.target_id
            if target_id not in stats["verification_by_target"]:
                stats["verification_by_target"][target_id] = {
                    "total": 0, "success": 0, "failed": 0, "error": 0
                }
            
            stats["verification_by_target"][target_id]["total"] += 1
            stats["verification_by_target"][target_id][result.status] += 1
        
        return stats
    
    def add_verification_rule(self, rule: VerificationRule) -> None:
        """Add a custom verification rule."""
        self._verification_rules[rule.rule_id] = rule
        logger.info(f"Added verification rule: {rule.rule_id}")
    
    def remove_verification_rule(self, rule_id: str) -> bool:
        """Remove a verification rule."""
        if rule_id in self._verification_rules:
            del self._verification_rules[rule_id]
            logger.info(f"Removed verification rule: {rule_id}")
            return True
        return False
    
    def list_verification_rules(self) -> List[VerificationRule]:
        """List all verification rules."""
        return list(self._verification_rules.values())