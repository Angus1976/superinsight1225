"""
Disaster Recovery Planner for High Availability System.

Provides disaster recovery planning, execution, and business
continuity management for the high availability infrastructure.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class DisasterType(Enum):
    """Types of disasters."""
    DATA_CENTER_FAILURE = "data_center_failure"
    NETWORK_OUTAGE = "network_outage"
    DATABASE_CORRUPTION = "database_corruption"
    SECURITY_BREACH = "security_breach"
    NATURAL_DISASTER = "natural_disaster"
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_FAILURE = "software_failure"


class RecoveryPhase(Enum):
    """Phases of disaster recovery."""
    DETECTION = "detection"
    ASSESSMENT = "assessment"
    DECLARATION = "declaration"
    ACTIVATION = "activation"
    RECOVERY = "recovery"
    RESTORATION = "restoration"
    VALIDATION = "validation"
    RETURN_TO_NORMAL = "return_to_normal"


class RecoveryStatus(Enum):
    """Status of recovery operation."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class RecoveryObjective:
    """Recovery objectives (RTO/RPO)."""
    service_name: str
    rto_minutes: int  # Recovery Time Objective
    rpo_minutes: int  # Recovery Point Objective
    priority: int  # 1 = highest
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RecoveryStep:
    """A step in the recovery plan."""
    step_id: str
    name: str
    description: str
    responsible_team: str
    estimated_duration_minutes: int
    dependencies: List[str] = field(default_factory=list)
    status: RecoveryStatus = RecoveryStatus.NOT_STARTED
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    notes: str = ""


@dataclass
class DisasterRecoveryPlan:
    """A complete disaster recovery plan."""
    plan_id: str
    name: str
    disaster_type: DisasterType
    description: str
    steps: List[RecoveryStep]
    recovery_objectives: List[RecoveryObjective]
    created_at: float = field(default_factory=time.time)
    last_tested: Optional[float] = None
    version: str = "1.0"


@dataclass
class RecoveryExecution:
    """Execution of a disaster recovery plan."""
    execution_id: str
    plan: DisasterRecoveryPlan
    disaster_type: DisasterType
    current_phase: RecoveryPhase
    status: RecoveryStatus
    started_at: float
    completed_at: Optional[float] = None
    actual_rto_minutes: Optional[float] = None
    actual_rpo_minutes: Optional[float] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class DisasterRecoveryConfig:
    """Configuration for disaster recovery planner."""
    default_rto_minutes: int = 60
    default_rpo_minutes: int = 15
    test_interval_days: int = 90
    notification_enabled: bool = True
    auto_failover_enabled: bool = True


class DisasterRecoveryPlanner:
    """
    Disaster recovery planning and execution system.
    
    Features:
    - Recovery plan management
    - RTO/RPO tracking
    - Recovery execution coordination
    - Business continuity management
    - Recovery testing and validation
    """
    
    def __init__(self, config: Optional[DisasterRecoveryConfig] = None):
        self.config = config or DisasterRecoveryConfig()
        self.plans: Dict[str, DisasterRecoveryPlan] = {}
        self.executions: Dict[str, RecoveryExecution] = {}
        self.execution_history: deque = deque(maxlen=100)
        self.recovery_objectives: Dict[str, RecoveryObjective] = {}
        
        # Setup default plans
        self._setup_default_plans()
        
        logger.info("DisasterRecoveryPlanner initialized")
    
    def _setup_default_plans(self):
        """Setup default disaster recovery plans."""
        # Database failure plan
        db_plan = DisasterRecoveryPlan(
            plan_id="dr_database",
            name="Database Disaster Recovery",
            disaster_type=DisasterType.DATABASE_CORRUPTION,
            description="Recovery plan for database failures and corruption",
            steps=[
                RecoveryStep(
                    step_id="db_1",
                    name="Assess Database Status",
                    description="Evaluate the extent of database damage",
                    responsible_team="DBA Team",
                    estimated_duration_minutes=15
                ),
                RecoveryStep(
                    step_id="db_2",
                    name="Activate Standby Database",
                    description="Promote standby database to primary",
                    responsible_team="DBA Team",
                    estimated_duration_minutes=10,
                    dependencies=["db_1"]
                ),
                RecoveryStep(
                    step_id="db_3",
                    name="Verify Data Integrity",
                    description="Run integrity checks on recovered database",
                    responsible_team="DBA Team",
                    estimated_duration_minutes=30,
                    dependencies=["db_2"]
                ),
                RecoveryStep(
                    step_id="db_4",
                    name="Restore Application Connections",
                    description="Update application connection strings",
                    responsible_team="DevOps Team",
                    estimated_duration_minutes=10,
                    dependencies=["db_3"]
                ),
                RecoveryStep(
                    step_id="db_5",
                    name="Validate Application Functionality",
                    description="Test critical application functions",
                    responsible_team="QA Team",
                    estimated_duration_minutes=20,
                    dependencies=["db_4"]
                ),
            ],
            recovery_objectives=[
                RecoveryObjective(
                    service_name="database",
                    rto_minutes=60,
                    rpo_minutes=5,
                    priority=1
                )
            ]
        )
        self.plans[db_plan.plan_id] = db_plan
        
        # Full system failure plan
        system_plan = DisasterRecoveryPlan(
            plan_id="dr_full_system",
            name="Full System Disaster Recovery",
            disaster_type=DisasterType.DATA_CENTER_FAILURE,
            description="Recovery plan for complete system failure",
            steps=[
                RecoveryStep(
                    step_id="sys_1",
                    name="Activate DR Site",
                    description="Bring up disaster recovery site",
                    responsible_team="Infrastructure Team",
                    estimated_duration_minutes=30
                ),
                RecoveryStep(
                    step_id="sys_2",
                    name="Restore Database",
                    description="Restore database from latest backup",
                    responsible_team="DBA Team",
                    estimated_duration_minutes=45,
                    dependencies=["sys_1"]
                ),
                RecoveryStep(
                    step_id="sys_3",
                    name="Deploy Applications",
                    description="Deploy application services to DR site",
                    responsible_team="DevOps Team",
                    estimated_duration_minutes=30,
                    dependencies=["sys_2"]
                ),
                RecoveryStep(
                    step_id="sys_4",
                    name="Update DNS",
                    description="Update DNS to point to DR site",
                    responsible_team="Network Team",
                    estimated_duration_minutes=15,
                    dependencies=["sys_3"]
                ),
                RecoveryStep(
                    step_id="sys_5",
                    name="Validate Services",
                    description="Validate all services are operational",
                    responsible_team="QA Team",
                    estimated_duration_minutes=30,
                    dependencies=["sys_4"]
                ),
            ],
            recovery_objectives=[
                RecoveryObjective(
                    service_name="api_server",
                    rto_minutes=120,
                    rpo_minutes=15,
                    priority=1
                ),
                RecoveryObjective(
                    service_name="database",
                    rto_minutes=90,
                    rpo_minutes=5,
                    priority=1
                ),
                RecoveryObjective(
                    service_name="label_studio",
                    rto_minutes=180,
                    rpo_minutes=30,
                    priority=2
                ),
            ]
        )
        self.plans[system_plan.plan_id] = system_plan
        
        # Security breach plan
        security_plan = DisasterRecoveryPlan(
            plan_id="dr_security",
            name="Security Breach Recovery",
            disaster_type=DisasterType.SECURITY_BREACH,
            description="Recovery plan for security incidents",
            steps=[
                RecoveryStep(
                    step_id="sec_1",
                    name="Isolate Affected Systems",
                    description="Disconnect compromised systems from network",
                    responsible_team="Security Team",
                    estimated_duration_minutes=15
                ),
                RecoveryStep(
                    step_id="sec_2",
                    name="Assess Breach Scope",
                    description="Determine extent of security breach",
                    responsible_team="Security Team",
                    estimated_duration_minutes=60,
                    dependencies=["sec_1"]
                ),
                RecoveryStep(
                    step_id="sec_3",
                    name="Rotate Credentials",
                    description="Reset all passwords and API keys",
                    responsible_team="Security Team",
                    estimated_duration_minutes=30,
                    dependencies=["sec_2"]
                ),
                RecoveryStep(
                    step_id="sec_4",
                    name="Restore Clean Systems",
                    description="Deploy clean system images",
                    responsible_team="DevOps Team",
                    estimated_duration_minutes=60,
                    dependencies=["sec_3"]
                ),
                RecoveryStep(
                    step_id="sec_5",
                    name="Security Validation",
                    description="Perform security audit of restored systems",
                    responsible_team="Security Team",
                    estimated_duration_minutes=120,
                    dependencies=["sec_4"]
                ),
            ],
            recovery_objectives=[
                RecoveryObjective(
                    service_name="security",
                    rto_minutes=240,
                    rpo_minutes=0,
                    priority=1
                )
            ]
        )
        self.plans[security_plan.plan_id] = security_plan
    
    def create_plan(
        self,
        name: str,
        disaster_type: DisasterType,
        description: str,
        steps: List[RecoveryStep],
        recovery_objectives: List[RecoveryObjective]
    ) -> DisasterRecoveryPlan:
        """Create a new disaster recovery plan."""
        plan_id = f"dr_{str(uuid.uuid4())[:8]}"
        
        plan = DisasterRecoveryPlan(
            plan_id=plan_id,
            name=name,
            disaster_type=disaster_type,
            description=description,
            steps=steps,
            recovery_objectives=recovery_objectives
        )
        
        self.plans[plan_id] = plan
        logger.info(f"Created disaster recovery plan: {name}")
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[DisasterRecoveryPlan]:
        """Get a disaster recovery plan by ID."""
        return self.plans.get(plan_id)
    
    def get_plan_for_disaster(self, disaster_type: DisasterType) -> Optional[DisasterRecoveryPlan]:
        """Get the appropriate plan for a disaster type."""
        for plan in self.plans.values():
            if plan.disaster_type == disaster_type:
                return plan
        return None
    
    async def execute_plan(
        self,
        plan_id: str,
        disaster_type: Optional[DisasterType] = None
    ) -> RecoveryExecution:
        """Execute a disaster recovery plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        execution_id = str(uuid.uuid4())[:8]
        
        execution = RecoveryExecution(
            execution_id=execution_id,
            plan=plan,
            disaster_type=disaster_type or plan.disaster_type,
            current_phase=RecoveryPhase.DETECTION,
            status=RecoveryStatus.IN_PROGRESS,
            started_at=time.time()
        )
        
        self.executions[execution_id] = execution
        
        logger.info(f"Starting disaster recovery execution: {execution_id}")
        
        try:
            # Execute recovery phases
            for phase in RecoveryPhase:
                execution.current_phase = phase
                await self._execute_phase(execution, phase)
                
                if execution.status == RecoveryStatus.FAILED:
                    break
            
            if execution.status != RecoveryStatus.FAILED:
                execution.status = RecoveryStatus.COMPLETED
                execution.completed_at = time.time()
                
                # Calculate actual RTO
                execution.actual_rto_minutes = (
                    execution.completed_at - execution.started_at
                ) / 60
            
            logger.info(f"Disaster recovery execution {execution_id} completed")
            
        except Exception as e:
            execution.status = RecoveryStatus.FAILED
            execution.notes.append(f"Execution failed: {str(e)}")
            logger.error(f"Disaster recovery execution {execution_id} failed: {e}")
        
        finally:
            # Move to history
            self.execution_history.append(execution)
        
        return execution
    
    async def _execute_phase(self, execution: RecoveryExecution, phase: RecoveryPhase):
        """Execute a recovery phase."""
        logger.info(f"Executing phase: {phase.value}")
        
        if phase == RecoveryPhase.DETECTION:
            execution.notes.append("Disaster detected and confirmed")
            await asyncio.sleep(0.1)
            
        elif phase == RecoveryPhase.ASSESSMENT:
            execution.notes.append("Impact assessment completed")
            await asyncio.sleep(0.1)
            
        elif phase == RecoveryPhase.DECLARATION:
            execution.notes.append("Disaster officially declared")
            await asyncio.sleep(0.1)
            
        elif phase == RecoveryPhase.ACTIVATION:
            execution.notes.append("Recovery plan activated")
            await asyncio.sleep(0.1)
            
        elif phase == RecoveryPhase.RECOVERY:
            # Execute recovery steps
            for step in execution.plan.steps:
                await self._execute_step(execution, step)
                
                if step.status == RecoveryStatus.FAILED:
                    execution.status = RecoveryStatus.FAILED
                    return
            
        elif phase == RecoveryPhase.RESTORATION:
            execution.notes.append("Services restored")
            await asyncio.sleep(0.1)
            
        elif phase == RecoveryPhase.VALIDATION:
            execution.notes.append("Recovery validated")
            await asyncio.sleep(0.1)
            
        elif phase == RecoveryPhase.RETURN_TO_NORMAL:
            execution.notes.append("Normal operations resumed")
            await asyncio.sleep(0.1)
    
    async def _execute_step(self, execution: RecoveryExecution, step: RecoveryStep):
        """Execute a recovery step."""
        logger.info(f"Executing step: {step.name}")
        
        step.status = RecoveryStatus.IN_PROGRESS
        step.started_at = time.time()
        
        try:
            # Simulate step execution
            await asyncio.sleep(0.1)
            
            step.status = RecoveryStatus.COMPLETED
            step.completed_at = time.time()
            
            execution.notes.append(f"Step completed: {step.name}")
            
        except Exception as e:
            step.status = RecoveryStatus.FAILED
            step.notes = str(e)
            execution.notes.append(f"Step failed: {step.name} - {str(e)}")
    
    async def test_plan(self, plan_id: str) -> Dict[str, Any]:
        """Test a disaster recovery plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}
        
        logger.info(f"Testing disaster recovery plan: {plan.name}")
        
        test_results = {
            "plan_id": plan_id,
            "plan_name": plan.name,
            "test_time": time.time(),
            "steps_tested": [],
            "issues_found": [],
            "estimated_rto": 0,
        }
        
        total_duration = 0
        
        for step in plan.steps:
            step_result = {
                "step_id": step.step_id,
                "name": step.name,
                "estimated_duration": step.estimated_duration_minutes,
                "status": "passed"
            }
            
            # Simulate step test
            await asyncio.sleep(0.05)
            
            total_duration += step.estimated_duration_minutes
            test_results["steps_tested"].append(step_result)
        
        test_results["estimated_rto"] = total_duration
        test_results["success"] = len(test_results["issues_found"]) == 0
        
        # Update plan last tested
        plan.last_tested = time.time()
        
        logger.info(f"Plan test completed: {plan.name}")
        return test_results
    
    def set_recovery_objective(
        self,
        service_name: str,
        rto_minutes: int,
        rpo_minutes: int,
        priority: int = 1
    ):
        """Set recovery objectives for a service."""
        objective = RecoveryObjective(
            service_name=service_name,
            rto_minutes=rto_minutes,
            rpo_minutes=rpo_minutes,
            priority=priority
        )
        
        self.recovery_objectives[service_name] = objective
        logger.info(f"Set recovery objectives for {service_name}: RTO={rto_minutes}m, RPO={rpo_minutes}m")
    
    def get_recovery_objectives(self) -> List[RecoveryObjective]:
        """Get all recovery objectives."""
        return list(self.recovery_objectives.values())
    
    def list_plans(self) -> List[DisasterRecoveryPlan]:
        """List all disaster recovery plans."""
        return list(self.plans.values())
    
    def get_execution_history(self, limit: int = 20) -> List[RecoveryExecution]:
        """Get execution history."""
        return list(self.execution_history)[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get disaster recovery statistics."""
        history = list(self.execution_history)
        successful = [e for e in history if e.status == RecoveryStatus.COMPLETED]
        
        return {
            "total_plans": len(self.plans),
            "total_executions": len(history),
            "successful_executions": len(successful),
            "failed_executions": len(history) - len(successful),
            "success_rate": len(successful) / len(history) if history else 0,
            "avg_rto_minutes": (
                sum(e.actual_rto_minutes for e in successful if e.actual_rto_minutes)
                / len(successful) if successful else 0
            ),
            "recovery_objectives": len(self.recovery_objectives),
            "plans_by_type": {
                dt.value: len([p for p in self.plans.values() if p.disaster_type == dt])
                for dt in DisasterType
            }
        }


# Global disaster recovery planner instance
disaster_recovery_planner: Optional[DisasterRecoveryPlanner] = None


def initialize_disaster_recovery_planner(
    config: Optional[DisasterRecoveryConfig] = None
) -> DisasterRecoveryPlanner:
    """Initialize the global disaster recovery planner."""
    global disaster_recovery_planner
    disaster_recovery_planner = DisasterRecoveryPlanner(config)
    return disaster_recovery_planner


def get_disaster_recovery_planner() -> Optional[DisasterRecoveryPlanner]:
    """Get the global disaster recovery planner instance."""
    return disaster_recovery_planner
