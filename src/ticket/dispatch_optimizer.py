"""
Advanced ticket dispatch optimization system.

Provides:
- Enhanced skill matching algorithms
- Advanced load balancing strategies
- Dispatch rule engine and policy management
- Performance evaluation and optimization
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import UUID
from enum import Enum
import numpy as np
from dataclasses import dataclass

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.ticket.models import (
    TicketModel,
    AnnotatorSkillModel,
    TicketHistoryModel,
    TicketStatus,
    TicketPriority,
    TicketType,
)

logger = logging.getLogger(__name__)


class DispatchStrategy(str, Enum):
    """Dispatch strategy options."""
    SKILL_FIRST = "skill_first"          # Prioritize skill matching
    LOAD_BALANCE = "load_balance"        # Prioritize load balancing
    PERFORMANCE = "performance"          # Prioritize historical performance
    HYBRID = "hybrid"                    # Balanced approach
    ROUND_ROBIN = "round_robin"          # Simple round-robin
    LEAST_LOADED = "least_loaded"        # Assign to least loaded


class LoadBalanceStrategy(str, Enum):
    """Load balancing strategy options."""
    EQUAL_DISTRIBUTION = "equal_distribution"    # Equal workload distribution
    CAPACITY_BASED = "capacity_based"           # Based on individual capacity
    PERFORMANCE_WEIGHTED = "performance_weighted"  # Weight by performance
    SKILL_WEIGHTED = "skill_weighted"           # Weight by skill level


@dataclass
class DispatchRule:
    """Rule for dispatch decision making."""
    name: str
    condition: callable
    action: callable
    priority: int = 0
    enabled: bool = True
    description: str = ""


@dataclass
class DispatchPolicy:
    """Dispatch policy configuration."""
    name: str
    strategy: DispatchStrategy
    load_balance_strategy: LoadBalanceStrategy
    skill_weight: float = 0.4
    capacity_weight: float = 0.3
    performance_weight: float = 0.3
    min_skill_threshold: float = 0.3
    max_workload_ratio: float = 0.9
    enabled: bool = True


@dataclass
class DispatchMetrics:
    """Metrics for dispatch performance evaluation."""
    total_dispatches: int = 0
    successful_dispatches: int = 0
    avg_dispatch_time: float = 0.0
    skill_match_accuracy: float = 0.0
    load_balance_score: float = 0.0
    sla_compliance_rate: float = 0.0
    reassignment_rate: float = 0.0


class AdvancedSkillMatcher:
    """Advanced skill matching algorithms."""
    
    @staticmethod
    def calculate_skill_compatibility(
        annotator_skills: Dict[str, float],
        required_skills: Dict[str, Any]
    ) -> float:
        """
        Calculate skill compatibility score using advanced matching.
        
        Args:
            annotator_skills: Annotator's skill levels
            required_skills: Required skills and levels
            
        Returns:
            Compatibility score (0-1)
        """
        if not required_skills or not annotator_skills:
            return 0.5  # Neutral score
        
        required_skill_types = required_skills.get("skills", [])
        min_level = required_skills.get("min_level", 0.3)
        
        if not required_skill_types:
            return 0.8  # No specific requirements
        
        # Calculate compatibility for each required skill
        compatibility_scores = []
        
        for skill_type in required_skill_types:
            annotator_level = annotator_skills.get(skill_type, 0.0)
            
            if annotator_level >= min_level:
                # Bonus for exceeding minimum
                excess_bonus = min(0.2, (annotator_level - min_level) * 0.5)
                compatibility_scores.append(min(1.0, annotator_level + excess_bonus))
            else:
                # Penalty for not meeting minimum
                penalty = (min_level - annotator_level) * 0.8
                compatibility_scores.append(max(0.0, annotator_level - penalty))
        
        # Return weighted average
        return sum(compatibility_scores) / len(compatibility_scores)
    
    @staticmethod
    def calculate_skill_diversity_bonus(
        annotator_skills: Dict[str, float],
        team_skills: List[Dict[str, float]]
    ) -> float:
        """
        Calculate bonus for skill diversity in team.
        
        Args:
            annotator_skills: Candidate's skills
            team_skills: Current team members' skills
            
        Returns:
            Diversity bonus (0-0.2)
        """
        if not team_skills:
            return 0.1  # Small bonus for first assignment
        
        # Calculate skill coverage
        all_skills = set()
        for skills in team_skills:
            all_skills.update(skills.keys())
        
        candidate_skills = set(annotator_skills.keys())
        
        # Bonus for new skills
        new_skills = candidate_skills - all_skills
        diversity_bonus = len(new_skills) * 0.05
        
        return min(0.2, diversity_bonus)


class LoadBalanceOptimizer:
    """Advanced load balancing optimization."""
    
    @staticmethod
    def calculate_optimal_distribution(
        annotators: List[AnnotatorSkillModel],
        strategy: LoadBalanceStrategy
    ) -> Dict[str, float]:
        """
        Calculate optimal workload distribution.
        
        Args:
            annotators: List of available annotators
            strategy: Load balancing strategy
            
        Returns:
            Optimal workload targets for each annotator
        """
        if not annotators:
            return {}
        
        targets = {}
        
        if strategy == LoadBalanceStrategy.EQUAL_DISTRIBUTION:
            # Equal distribution regardless of capacity
            target_load = sum(a.current_workload for a in annotators) / len(annotators)
            for annotator in annotators:
                targets[annotator.user_id] = target_load
                
        elif strategy == LoadBalanceStrategy.CAPACITY_BASED:
            # Distribution based on individual capacity
            total_capacity = sum(a.max_workload for a in annotators)
            total_workload = sum(a.current_workload for a in annotators)
            
            for annotator in annotators:
                capacity_ratio = annotator.max_workload / total_capacity
                targets[annotator.user_id] = total_workload * capacity_ratio
                
        elif strategy == LoadBalanceStrategy.PERFORMANCE_WEIGHTED:
            # Weight by performance metrics
            total_performance = sum(a.success_rate * a.avg_quality_score for a in annotators)
            total_workload = sum(a.current_workload for a in annotators)
            
            for annotator in annotators:
                performance_score = annotator.success_rate * annotator.avg_quality_score
                performance_ratio = performance_score / total_performance if total_performance > 0 else 1/len(annotators)
                targets[annotator.user_id] = total_workload * performance_ratio
                
        elif strategy == LoadBalanceStrategy.SKILL_WEIGHTED:
            # Weight by average skill level
            total_skill = sum(a.skill_level for a in annotators)
            total_workload = sum(a.current_workload for a in annotators)
            
            for annotator in annotators:
                skill_ratio = annotator.skill_level / total_skill if total_skill > 0 else 1/len(annotators)
                targets[annotator.user_id] = total_workload * skill_ratio
        
        return targets
    
    @staticmethod
    def calculate_load_balance_score(
        annotators: List[AnnotatorSkillModel],
        targets: Dict[str, float]
    ) -> float:
        """
        Calculate load balance score (0-1, higher is better).
        
        Args:
            annotators: List of annotators
            targets: Target workload distribution
            
        Returns:
            Load balance score
        """
        if not annotators or not targets:
            return 1.0
        
        deviations = []
        for annotator in annotators:
            target = targets.get(annotator.user_id, annotator.current_workload)
            if target > 0:
                deviation = abs(annotator.current_workload - target) / target
                deviations.append(deviation)
        
        if not deviations:
            return 1.0
        
        # Convert average deviation to score (lower deviation = higher score)
        avg_deviation = sum(deviations) / len(deviations)
        return max(0.0, 1.0 - avg_deviation)


class DispatchOptimizer:
    """
    Advanced ticket dispatch optimization system.
    
    Provides intelligent dispatch with configurable strategies,
    rules, and performance optimization.
    """
    
    def __init__(self):
        """Initialize the dispatch optimizer."""
        self._policies = self._setup_default_policies()
        self._rules = self._setup_default_rules()
        self._metrics = DispatchMetrics()
        self._skill_matcher = AdvancedSkillMatcher()
        self._load_balancer = LoadBalanceOptimizer()
        
    def _setup_default_policies(self) -> Dict[str, DispatchPolicy]:
        """Setup default dispatch policies."""
        return {
            "default": DispatchPolicy(
                name="default",
                strategy=DispatchStrategy.HYBRID,
                load_balance_strategy=LoadBalanceStrategy.CAPACITY_BASED,
                skill_weight=0.4,
                capacity_weight=0.3,
                performance_weight=0.3
            ),
            "skill_focused": DispatchPolicy(
                name="skill_focused",
                strategy=DispatchStrategy.SKILL_FIRST,
                load_balance_strategy=LoadBalanceStrategy.SKILL_WEIGHTED,
                skill_weight=0.6,
                capacity_weight=0.2,
                performance_weight=0.2,
                min_skill_threshold=0.5
            ),
            "load_balanced": DispatchPolicy(
                name="load_balanced",
                strategy=DispatchStrategy.LOAD_BALANCE,
                load_balance_strategy=LoadBalanceStrategy.EQUAL_DISTRIBUTION,
                skill_weight=0.2,
                capacity_weight=0.5,
                performance_weight=0.3,
                max_workload_ratio=0.8
            ),
            "performance_optimized": DispatchPolicy(
                name="performance_optimized",
                strategy=DispatchStrategy.PERFORMANCE,
                load_balance_strategy=LoadBalanceStrategy.PERFORMANCE_WEIGHTED,
                skill_weight=0.3,
                capacity_weight=0.2,
                performance_weight=0.5
            )
        }
    
    def _setup_default_rules(self) -> List[DispatchRule]:
        """Setup default dispatch rules."""
        return [
            DispatchRule(
                name="critical_priority_override",
                condition=lambda ticket, **kwargs: ticket.priority == TicketPriority.CRITICAL,
                action=lambda candidates, **kwargs: self._prioritize_best_performers(candidates),
                priority=100,
                description="Assign critical tickets to best performers"
            ),
            
            DispatchRule(
                name="skill_requirement_filter",
                condition=lambda ticket, **kwargs: bool(ticket.skill_requirements),
                action=lambda candidates, ticket, **kwargs: self._filter_by_skills(candidates, ticket.skill_requirements),
                priority=90,
                description="Filter candidates by skill requirements"
            ),
            
            DispatchRule(
                name="workload_limit_filter",
                condition=lambda **kwargs: True,  # Always apply
                action=lambda candidates, policy, **kwargs: self._filter_by_workload(candidates, policy.max_workload_ratio),
                priority=80,
                description="Filter overloaded candidates"
            ),
            
            DispatchRule(
                name="customer_complaint_priority",
                condition=lambda ticket, **kwargs: ticket.ticket_type == TicketType.CUSTOMER_COMPLAINT,
                action=lambda candidates, **kwargs: self._prioritize_customer_service_skills(candidates),
                priority=70,
                description="Prioritize customer service skills for complaints"
            ),
            
            DispatchRule(
                name="avoid_recent_failures",
                condition=lambda **kwargs: True,
                action=lambda candidates, **kwargs: self._deprioritize_recent_failures(candidates),
                priority=60,
                description="Avoid annotators with recent failures"
            )
        ]
    
    async def optimize_dispatch(
        self,
        ticket: TicketModel,
        candidates: List[AnnotatorSkillModel],
        policy_name: str = "default",
        tenant_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Optimize ticket dispatch using advanced algorithms.
        
        Args:
            ticket: Ticket to dispatch
            candidates: Available candidates
            policy_name: Dispatch policy to use
            tenant_id: Optional tenant filter
            
        Returns:
            Selected annotator user ID or None
        """
        start_time = datetime.now()
        
        try:
            # Get dispatch policy
            policy = self._policies.get(policy_name, self._policies["default"])
            
            if not candidates:
                logger.warning(f"No candidates available for ticket {ticket.id}")
                return None
            
            # Apply dispatch rules
            filtered_candidates = await self._apply_dispatch_rules(
                ticket=ticket,
                candidates=candidates,
                policy=policy
            )
            
            if not filtered_candidates:
                logger.warning(f"No candidates passed dispatch rules for ticket {ticket.id}")
                return None
            
            # Calculate optimal assignment
            selected_annotator = await self._calculate_optimal_assignment(
                ticket=ticket,
                candidates=filtered_candidates,
                policy=policy,
                tenant_id=tenant_id
            )
            
            # Update metrics
            dispatch_time = (datetime.now() - start_time).total_seconds()
            await self._update_dispatch_metrics(
                success=selected_annotator is not None,
                dispatch_time=dispatch_time,
                ticket=ticket,
                selected_annotator=selected_annotator
            )
            
            return selected_annotator
            
        except Exception as e:
            logger.error(f"Error optimizing dispatch for ticket {ticket.id}: {e}")
            return None
    
    async def _apply_dispatch_rules(
        self,
        ticket: TicketModel,
        candidates: List[AnnotatorSkillModel],
        policy: DispatchPolicy
    ) -> List[AnnotatorSkillModel]:
        """Apply dispatch rules to filter and modify candidates."""
        current_candidates = candidates.copy()
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(
            [rule for rule in self._rules if rule.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            try:
                if rule.condition(ticket=ticket, policy=policy, candidates=current_candidates):
                    current_candidates = rule.action(
                        candidates=current_candidates,
                        ticket=ticket,
                        policy=policy
                    )
                    
                    if not current_candidates:
                        logger.warning(f"Rule '{rule.name}' filtered out all candidates")
                        break
                        
            except Exception as e:
                logger.warning(f"Error applying rule '{rule.name}': {e}")
        
        return current_candidates
    
    async def _calculate_optimal_assignment(
        self,
        ticket: TicketModel,
        candidates: List[AnnotatorSkillModel],
        policy: DispatchPolicy,
        tenant_id: Optional[str] = None
    ) -> Optional[str]:
        """Calculate optimal assignment based on policy."""
        if not candidates:
            return None
        
        # Calculate scores for each candidate
        candidate_scores = []
        
        for candidate in candidates:
            score = await self._calculate_candidate_score(
                candidate=candidate,
                ticket=ticket,
                policy=policy,
                all_candidates=candidates
            )
            
            candidate_scores.append({
                "user_id": candidate.user_id,
                "score": score,
                "candidate": candidate
            })
        
        # Sort by score (highest first)
        candidate_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Apply strategy-specific selection
        if policy.strategy == DispatchStrategy.ROUND_ROBIN:
            return await self._select_round_robin(candidates, tenant_id)
        elif policy.strategy == DispatchStrategy.LEAST_LOADED:
            return min(candidates, key=lambda c: c.current_workload).user_id
        else:
            # Return highest scoring candidate
            return candidate_scores[0]["user_id"] if candidate_scores else None
    
    async def _calculate_candidate_score(
        self,
        candidate: AnnotatorSkillModel,
        ticket: TicketModel,
        policy: DispatchPolicy,
        all_candidates: List[AnnotatorSkillModel]
    ) -> float:
        """Calculate comprehensive score for a candidate."""
        # Skill score
        annotator_skills = {candidate.skill_type: candidate.skill_level}
        skill_score = self._skill_matcher.calculate_skill_compatibility(
            annotator_skills, ticket.skill_requirements
        )
        
        # Capacity score (inverse of utilization)
        capacity_score = 1.0 - (candidate.current_workload / candidate.max_workload) if candidate.max_workload > 0 else 0.0
        
        # Performance score
        performance_score = (candidate.success_rate * 0.5 + candidate.avg_quality_score * 0.5)
        
        # Load balance score
        targets = self._load_balancer.calculate_optimal_distribution(
            all_candidates, policy.load_balance_strategy
        )
        target_load = targets.get(candidate.user_id, candidate.current_workload)
        load_balance_score = 1.0 - abs(candidate.current_workload - target_load) / max(1, target_load)
        
        # Weighted combination
        total_score = (
            skill_score * policy.skill_weight +
            capacity_score * policy.capacity_weight +
            performance_score * policy.performance_weight +
            load_balance_score * 0.1  # Small load balance factor
        )
        
        return min(1.0, max(0.0, total_score))
    
    # Rule action methods
    def _prioritize_best_performers(self, candidates: List[AnnotatorSkillModel]) -> List[AnnotatorSkillModel]:
        """Prioritize candidates with best performance."""
        return sorted(
            candidates,
            key=lambda c: c.success_rate * c.avg_quality_score,
            reverse=True
        )
    
    def _filter_by_skills(
        self,
        candidates: List[AnnotatorSkillModel],
        skill_requirements: Dict[str, Any]
    ) -> List[AnnotatorSkillModel]:
        """Filter candidates by skill requirements."""
        if not skill_requirements:
            return candidates
        
        required_skills = skill_requirements.get("skills", [])
        min_level = skill_requirements.get("min_level", 0.3)
        
        filtered = []
        for candidate in candidates:
            if not required_skills or candidate.skill_type in required_skills:
                if candidate.skill_level >= min_level:
                    filtered.append(candidate)
        
        return filtered
    
    def _filter_by_workload(
        self,
        candidates: List[AnnotatorSkillModel],
        max_workload_ratio: float
    ) -> List[AnnotatorSkillModel]:
        """Filter candidates by workload limits."""
        return [
            c for c in candidates
            if c.max_workload == 0 or c.current_workload / c.max_workload <= max_workload_ratio
        ]
    
    def _prioritize_customer_service_skills(self, candidates: List[AnnotatorSkillModel]) -> List[AnnotatorSkillModel]:
        """Prioritize candidates with customer service skills."""
        customer_service_candidates = [
            c for c in candidates
            if "customer_service" in c.skill_type or c.skill_type == "customer_service"
        ]
        
        other_candidates = [
            c for c in candidates
            if c not in customer_service_candidates
        ]
        
        return customer_service_candidates + other_candidates
    
    def _deprioritize_recent_failures(self, candidates: List[AnnotatorSkillModel]) -> List[AnnotatorSkillModel]:
        """Deprioritize candidates with recent failures."""
        # Sort by success rate (higher first)
        return sorted(candidates, key=lambda c: c.success_rate, reverse=True)
    
    async def _select_round_robin(
        self,
        candidates: List[AnnotatorSkillModel],
        tenant_id: Optional[str] = None
    ) -> Optional[str]:
        """Select candidate using round-robin strategy."""
        if not candidates:
            return None
        
        # Simple round-robin based on last assignment time
        return min(candidates, key=lambda c: c.last_active_at or datetime.min).user_id
    
    async def _update_dispatch_metrics(
        self,
        success: bool,
        dispatch_time: float,
        ticket: TicketModel,
        selected_annotator: Optional[str]
    ) -> None:
        """Update dispatch performance metrics."""
        self._metrics.total_dispatches += 1
        
        if success:
            self._metrics.successful_dispatches += 1
        
        # Update average dispatch time
        if self._metrics.total_dispatches == 1:
            self._metrics.avg_dispatch_time = dispatch_time
        else:
            self._metrics.avg_dispatch_time = (
                (self._metrics.avg_dispatch_time * (self._metrics.total_dispatches - 1) + dispatch_time)
                / self._metrics.total_dispatches
            )
    
    async def evaluate_dispatch_performance(
        self,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Evaluate dispatch performance over time.
        
        Args:
            tenant_id: Optional tenant filter
            days: Analysis period in days
            
        Returns:
            Performance evaluation results
        """
        try:
            with db_manager.get_session() as session:
                cutoff = datetime.now() - timedelta(days=days)
                
                # Query dispatch history
                query = select(TicketModel).where(
                    and_(
                        TicketModel.assigned_at >= cutoff,
                        TicketModel.assigned_to.isnot(None)
                    )
                )
                
                if tenant_id:
                    query = query.where(TicketModel.tenant_id == tenant_id)
                
                tickets = session.execute(query).scalars().all()
                
                if not tickets:
                    return {"message": "No dispatch data available"}
                
                # Calculate metrics
                total_dispatches = len(tickets)
                successful_dispatches = len([t for t in tickets if t.status != TicketStatus.OPEN])
                
                # Calculate average assignment time (from creation to assignment)
                assignment_times = []
                for ticket in tickets:
                    if ticket.assigned_at and ticket.created_at:
                        assignment_times.append(
                            (ticket.assigned_at - ticket.created_at).total_seconds()
                        )
                
                avg_assignment_time = sum(assignment_times) / len(assignment_times) if assignment_times else 0
                
                # Calculate reassignment rate
                reassignments = 0
                for ticket in tickets:
                    # Count history entries for reassignments
                    history_count = session.execute(
                        select(func.count(TicketHistoryModel.id)).where(
                            and_(
                                TicketHistoryModel.ticket_id == ticket.id,
                                TicketHistoryModel.action == "assigned"
                            )
                        )
                    ).scalar()
                    
                    if history_count > 1:
                        reassignments += 1
                
                reassignment_rate = reassignments / total_dispatches if total_dispatches > 0 else 0
                
                # Calculate SLA compliance
                sla_compliant = len([t for t in tickets if not t.sla_breached])
                sla_compliance_rate = sla_compliant / total_dispatches if total_dispatches > 0 else 0
                
                return {
                    "period_days": days,
                    "total_dispatches": total_dispatches,
                    "successful_dispatches": successful_dispatches,
                    "success_rate": successful_dispatches / total_dispatches if total_dispatches > 0 else 0,
                    "avg_assignment_time_seconds": avg_assignment_time,
                    "reassignment_rate": reassignment_rate,
                    "sla_compliance_rate": sla_compliance_rate,
                    "current_metrics": {
                        "total_dispatches": self._metrics.total_dispatches,
                        "successful_dispatches": self._metrics.successful_dispatches,
                        "avg_dispatch_time": self._metrics.avg_dispatch_time,
                    }
                }
                
        except Exception as e:
            logger.error(f"Error evaluating dispatch performance: {e}")
            return {}
    
    async def get_dispatch_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get available dispatch policies."""
        return {
            name: {
                "name": policy.name,
                "strategy": policy.strategy.value,
                "load_balance_strategy": policy.load_balance_strategy.value,
                "skill_weight": policy.skill_weight,
                "capacity_weight": policy.capacity_weight,
                "performance_weight": policy.performance_weight,
                "min_skill_threshold": policy.min_skill_threshold,
                "max_workload_ratio": policy.max_workload_ratio,
                "enabled": policy.enabled
            }
            for name, policy in self._policies.items()
        }
    
    async def update_dispatch_policy(
        self,
        policy_name: str,
        **updates
    ) -> bool:
        """Update a dispatch policy."""
        try:
            if policy_name not in self._policies:
                return False
            
            policy = self._policies[policy_name]
            
            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            logger.info(f"Updated dispatch policy: {policy_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating dispatch policy: {e}")
            return False
    
    async def get_dispatch_rules(self) -> List[Dict[str, Any]]:
        """Get dispatch rules configuration."""
        return [
            {
                "name": rule.name,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "description": rule.description
            }
            for rule in self._rules
        ]