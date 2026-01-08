"""
Intelligent ticket dispatch engine for SuperInsight platform.

Implements smart ticket assignment based on:
- Skill matching
- Workload balancing
- Historical performance
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.ticket.models import (
    TicketModel,
    AnnotatorSkillModel,
    TicketHistoryModel,
    Ticket,
    AnnotatorSkill,
    TicketStatus,
    TicketPriority,
    TicketType,
    SLAConfig,
)
from src.ticket.dispatch_optimizer import DispatchOptimizer

logger = logging.getLogger(__name__)


class TicketDispatcher:
    """
    Intelligent ticket dispatch engine.

    Assigns tickets to annotators based on:
    - Skill matching (40% weight)
    - Available capacity (30% weight)
    - Historical performance (30% weight)
    """

    # Scoring weights
    SKILL_WEIGHT = 0.4
    CAPACITY_WEIGHT = 0.3
    PERFORMANCE_WEIGHT = 0.3

    # Minimum thresholds
    MIN_SKILL_LEVEL = 0.3  # Minimum skill level required
    MIN_CAPACITY = 1  # At least 1 available slot

    def __init__(self):
        """Initialize the ticket dispatcher."""
        self._assignment_cache: Dict[str, List[str]] = {}
        self._optimizer = DispatchOptimizer()

    async def dispatch_ticket(
        self,
        ticket_id: UUID,
        auto_assign: bool = True,
        preferred_user: Optional[str] = None
    ) -> Optional[str]:
        """
        Dispatch a ticket to the best available annotator.

        Args:
            ticket_id: UUID of the ticket to dispatch
            auto_assign: Whether to automatically assign the ticket
            preferred_user: Optional preferred user to assign to

        Returns:
            User ID of the assigned annotator, or None if no suitable annotator found
        """
        try:
            with db_manager.get_session() as session:
                # Get ticket
                ticket = session.execute(
                    select(TicketModel).where(TicketModel.id == ticket_id)
                ).scalar_one_or_none()

                if not ticket:
                    logger.error(f"Ticket not found: {ticket_id}")
                    return None

                if ticket.status not in [TicketStatus.OPEN, TicketStatus.ESCALATED]:
                    logger.warning(f"Ticket {ticket_id} is not in dispatchable state: {ticket.status}")
                    return None

                # If preferred user is specified, try to assign to them first
                if preferred_user:
                    if await self._can_assign_to_user(session, preferred_user, ticket):
                        if auto_assign:
                            await self._assign_ticket(session, ticket, preferred_user, "manual_preferred")
                        return preferred_user

                # Get available annotators
                candidates = await self.get_available_annotators(
                    session,
                    ticket.skill_requirements,
                    ticket.tenant_id
                )

                if not candidates:
                    logger.warning(f"No available annotators for ticket {ticket_id}")
                    return None

                # Score and rank candidates
                scored_candidates = await self._score_candidates(session, candidates, ticket)

                if not scored_candidates:
                    return None

                # Get best candidate
                best_candidate = scored_candidates[0]
                best_user_id = best_candidate["user_id"]

                if auto_assign:
                    await self._assign_ticket(session, ticket, best_user_id, "auto_dispatch")
                    logger.info(f"Auto-assigned ticket {ticket_id} to {best_user_id} (score: {best_candidate['score']:.3f})")

                return best_user_id

        except Exception as e:
            logger.error(f"Error dispatching ticket {ticket_id}: {e}")
            raise

    async def get_available_annotators(
        self,
        session: Session,
        skill_requirements: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> List[AnnotatorSkillModel]:
        """
        Get annotators that meet skill requirements and have available capacity.

        Args:
            session: Database session
            skill_requirements: Required skills and levels
            tenant_id: Optional tenant filter

        Returns:
            List of available annotators matching requirements
        """
        try:
            # Build base query
            query = select(AnnotatorSkillModel).where(
                and_(
                    AnnotatorSkillModel.is_available == True,
                    AnnotatorSkillModel.current_workload < AnnotatorSkillModel.max_workload
                )
            )

            # Apply tenant filter if specified
            if tenant_id:
                query = query.where(AnnotatorSkillModel.tenant_id == tenant_id)

            # Execute query
            result = session.execute(query)
            all_annotators = result.scalars().all()

            # Filter by skill requirements
            if not skill_requirements:
                return list(all_annotators)

            qualified_annotators = []
            required_skills = skill_requirements.get("skills", [])
            min_level = skill_requirements.get("min_level", self.MIN_SKILL_LEVEL)

            for annotator in all_annotators:
                # Check if annotator has required skill type
                if required_skills and annotator.skill_type not in required_skills:
                    continue

                # Check skill level
                if annotator.skill_level < min_level:
                    continue

                qualified_annotators.append(annotator)

            return qualified_annotators

        except Exception as e:
            logger.error(f"Error getting available annotators: {e}")
            return []

    def calculate_assignment_score(
        self,
        annotator: AnnotatorSkillModel,
        ticket: TicketModel
    ) -> float:
        """
        Calculate assignment score for an annotator-ticket pair.

        Score = skill_match * 0.4 + capacity_score * 0.3 + performance_score * 0.3

        Args:
            annotator: Annotator skill record
            ticket: Ticket to assign

        Returns:
            Assignment score (0-1)
        """
        # Skill matching score
        skill_score = self._calculate_skill_score(annotator, ticket)

        # Capacity score (inverse of utilization)
        capacity_score = self._calculate_capacity_score(annotator)

        # Performance score
        performance_score = self._calculate_performance_score(annotator)

        # Calculate weighted score
        total_score = (
            skill_score * self.SKILL_WEIGHT +
            capacity_score * self.CAPACITY_WEIGHT +
            performance_score * self.PERFORMANCE_WEIGHT
        )

        return min(1.0, max(0.0, total_score))

    def _calculate_skill_score(
        self,
        annotator: AnnotatorSkillModel,
        ticket: TicketModel
    ) -> float:
        """Calculate skill matching score."""
        base_score = annotator.skill_level

        # Bonus for exact skill match
        skill_requirements = ticket.skill_requirements or {}
        required_skills = skill_requirements.get("skills", [])

        if required_skills and annotator.skill_type in required_skills:
            base_score = min(1.0, base_score * 1.2)

        # Priority boost for high priority tickets
        if ticket.priority in [TicketPriority.CRITICAL, TicketPriority.HIGH]:
            # Prefer higher skilled annotators for critical tickets
            base_score = min(1.0, base_score * 1.1)

        return base_score

    def _calculate_capacity_score(self, annotator: AnnotatorSkillModel) -> float:
        """Calculate capacity score (higher is better)."""
        if annotator.max_workload == 0:
            return 0.0

        utilization = annotator.current_workload / annotator.max_workload
        # Inverse utilization: lower workload = higher score
        return 1.0 - utilization

    def _calculate_performance_score(self, annotator: AnnotatorSkillModel) -> float:
        """Calculate historical performance score."""
        # Weight success rate and quality score equally
        success_score = annotator.success_rate
        quality_score = annotator.avg_quality_score

        # Consider resolution time (lower is better)
        # Normalize to 0-1 (assume 1 hour = 3600s is baseline)
        time_score = 1.0
        if annotator.avg_resolution_time > 0:
            time_score = min(1.0, 3600 / annotator.avg_resolution_time)

        return (success_score * 0.4 + quality_score * 0.4 + time_score * 0.2)

    async def _score_candidates(
        self,
        session: Session,
        candidates: List[AnnotatorSkillModel],
        ticket: TicketModel
    ) -> List[Dict[str, Any]]:
        """Score and rank candidate annotators."""
        scored = []

        for annotator in candidates:
            score = self.calculate_assignment_score(annotator, ticket)
            scored.append({
                "user_id": annotator.user_id,
                "score": score,
                "skill_level": annotator.skill_level,
                "current_workload": annotator.current_workload,
                "success_rate": annotator.success_rate,
            })

        # Sort by score (descending)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    async def _can_assign_to_user(
        self,
        session: Session,
        user_id: str,
        ticket: TicketModel
    ) -> bool:
        """Check if ticket can be assigned to specific user."""
        annotator = session.execute(
            select(AnnotatorSkillModel).where(
                and_(
                    AnnotatorSkillModel.user_id == user_id,
                    AnnotatorSkillModel.is_available == True,
                    AnnotatorSkillModel.current_workload < AnnotatorSkillModel.max_workload
                )
            )
        ).scalar_one_or_none()

        return annotator is not None

    async def _assign_ticket(
        self,
        session: Session,
        ticket: TicketModel,
        user_id: str,
        assignment_type: str
    ) -> None:
        """Assign ticket to user and update related records."""
        now = datetime.now()

        # Update ticket
        old_status = ticket.status
        old_assignee = ticket.assigned_to

        ticket.assigned_to = user_id
        ticket.assigned_at = now
        ticket.status = TicketStatus.ASSIGNED
        ticket.updated_at = now

        # Set SLA deadline if not set
        if not ticket.sla_deadline:
            ticket.sla_deadline = SLAConfig.get_sla_deadline(ticket.priority, now)

        # Update annotator workload
        annotator = session.execute(
            select(AnnotatorSkillModel).where(AnnotatorSkillModel.user_id == user_id)
        ).scalar_one_or_none()

        if annotator:
            annotator.current_workload += 1
            annotator.total_tasks += 1
            annotator.last_active_at = now

        # Record history
        history = TicketHistoryModel(
            ticket_id=ticket.id,
            action="assigned",
            old_value=old_assignee,
            new_value=user_id,
            performed_by="system",
            notes=f"Auto-assigned via {assignment_type}"
        )
        session.add(history)

        # Record status change
        if old_status != TicketStatus.ASSIGNED:
            status_history = TicketHistoryModel(
                ticket_id=ticket.id,
                action="status_changed",
                old_value=old_status.value,
                new_value=TicketStatus.ASSIGNED.value,
                performed_by="system",
                notes="Status changed due to assignment"
            )
            session.add(status_history)

        session.commit()
        logger.info(f"Ticket {ticket.id} assigned to {user_id}")

    async def rebalance_workload(
        self,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Rebalance workload across annotators.

        Reassigns tickets from overloaded annotators to underutilized ones.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            List of rebalancing actions taken
        """
        actions = []

        try:
            with db_manager.get_session() as session:
                # Find overloaded annotators (> 80% utilization)
                overloaded_query = select(AnnotatorSkillModel).where(
                    and_(
                        AnnotatorSkillModel.is_available == True,
                        AnnotatorSkillModel.current_workload > AnnotatorSkillModel.max_workload * 0.8
                    )
                )
                if tenant_id:
                    overloaded_query = overloaded_query.where(
                        AnnotatorSkillModel.tenant_id == tenant_id
                    )

                overloaded = session.execute(overloaded_query).scalars().all()

                for annotator in overloaded:
                    # Find tickets that can be reassigned
                    tickets = session.execute(
                        select(TicketModel).where(
                            and_(
                                TicketModel.assigned_to == annotator.user_id,
                                TicketModel.status == TicketStatus.ASSIGNED,
                                TicketModel.sla_breached == False
                            )
                        ).order_by(TicketModel.priority.desc())
                    ).scalars().all()

                    # Try to reassign lowest priority tickets
                    for ticket in reversed(tickets):
                        if annotator.current_workload <= annotator.max_workload * 0.6:
                            break  # Balanced enough

                        new_assignee = await self.dispatch_ticket(
                            ticket.id,
                            auto_assign=False
                        )

                        if new_assignee and new_assignee != annotator.user_id:
                            await self._reassign_ticket(session, ticket, new_assignee)
                            actions.append({
                                "ticket_id": str(ticket.id),
                                "from_user": annotator.user_id,
                                "to_user": new_assignee,
                                "reason": "workload_rebalancing"
                            })

                session.commit()

        except Exception as e:
            logger.error(f"Error rebalancing workload: {e}")

        return actions

    async def _reassign_ticket(
        self,
        session: Session,
        ticket: TicketModel,
        new_user_id: str
    ) -> None:
        """Reassign ticket from one user to another."""
        old_user_id = ticket.assigned_to

        # Update old annotator workload
        if old_user_id:
            old_annotator = session.execute(
                select(AnnotatorSkillModel).where(
                    AnnotatorSkillModel.user_id == old_user_id
                )
            ).scalar_one_or_none()

            if old_annotator:
                old_annotator.current_workload = max(0, old_annotator.current_workload - 1)

        # Assign to new user
        await self._assign_ticket(session, ticket, new_user_id, "workload_rebalancing")

    async def get_workload_distribution(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current workload distribution statistics.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            Workload distribution summary
        """
        try:
            with db_manager.get_session() as session:
                query = select(AnnotatorSkillModel)
                if tenant_id:
                    query = query.where(AnnotatorSkillModel.tenant_id == tenant_id)

                annotators = session.execute(query).scalars().all()

                total_capacity = 0
                total_workload = 0
                by_user = []

                for a in annotators:
                    total_capacity += a.max_workload
                    total_workload += a.current_workload
                    by_user.append({
                        "user_id": a.user_id,
                        "current_workload": a.current_workload,
                        "max_workload": a.max_workload,
                        "utilization": a.current_workload / a.max_workload if a.max_workload > 0 else 0,
                        "is_available": a.is_available,
                    })

                return {
                    "total_capacity": total_capacity,
                    "total_workload": total_workload,
                    "overall_utilization": total_workload / total_capacity if total_capacity > 0 else 0,
                    "annotator_count": len(annotators),
                    "available_count": sum(1 for a in annotators if a.is_available),
                    "by_user": by_user,
                }

        except Exception as e:
            logger.error(f"Error getting workload distribution: {e}")
            return {}

    async def dispatch_ticket_optimized(
        self,
        ticket_id: UUID,
        policy_name: str = "default",
        auto_assign: bool = True,
        preferred_user: Optional[str] = None
    ) -> Optional[str]:
        """
        Dispatch a ticket using advanced optimization.

        Args:
            ticket_id: UUID of the ticket to dispatch
            policy_name: Dispatch policy to use
            auto_assign: Whether to automatically assign the ticket
            preferred_user: Optional preferred user to assign to

        Returns:
            User ID of the assigned annotator, or None if no suitable annotator found
        """
        try:
            with db_manager.get_session() as session:
                # Get ticket
                ticket = session.execute(
                    select(TicketModel).where(TicketModel.id == ticket_id)
                ).scalar_one_or_none()

                if not ticket:
                    logger.error(f"Ticket not found: {ticket_id}")
                    return None

                if ticket.status not in [TicketStatus.OPEN, TicketStatus.ESCALATED]:
                    logger.warning(f"Ticket {ticket_id} is not in dispatchable state: {ticket.status}")
                    return None

                # If preferred user is specified, try to assign to them first
                if preferred_user:
                    if await self._can_assign_to_user(session, preferred_user, ticket):
                        if auto_assign:
                            await self._assign_ticket(session, ticket, preferred_user, "manual_preferred")
                        return preferred_user

                # Get available annotators
                candidates = await self.get_available_annotators(
                    session,
                    ticket.skill_requirements,
                    ticket.tenant_id
                )

                if not candidates:
                    logger.warning(f"No available annotators for ticket {ticket_id}")
                    return None

                # Use optimizer for advanced dispatch
                best_candidate = await self._optimizer.optimize_dispatch(
                    ticket=ticket,
                    candidates=candidates,
                    policy_name=policy_name,
                    tenant_id=ticket.tenant_id
                )

                if not best_candidate:
                    logger.warning(f"Optimizer found no suitable candidate for ticket {ticket_id}")
                    return None

                if auto_assign:
                    await self._assign_ticket(session, ticket, best_candidate, f"optimized_dispatch:{policy_name}")
                    logger.info(f"Optimized dispatch assigned ticket {ticket_id} to {best_candidate}")

                return best_candidate

        except Exception as e:
            logger.error(f"Error in optimized dispatch for ticket {ticket_id}: {e}")
            raise

    async def get_dispatch_recommendations_advanced(
        self,
        ticket_id: UUID,
        policy_name: str = "default",
        include_scores: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get advanced dispatch recommendations with detailed scoring.

        Args:
            ticket_id: UUID of the ticket
            policy_name: Dispatch policy to use
            include_scores: Whether to include detailed scores

        Returns:
            List of recommended annotators with detailed information
        """
        try:
            with db_manager.get_session() as session:
                ticket = session.execute(
                    select(TicketModel).where(TicketModel.id == ticket_id)
                ).scalar_one_or_none()

                if not ticket:
                    return []

                candidates = await self.get_available_annotators(
                    session,
                    ticket.skill_requirements,
                    ticket.tenant_id
                )

                if not candidates:
                    return []

                # Get policy
                policies = await self._optimizer.get_dispatch_policies()
                policy = policies.get(policy_name, policies["default"])

                recommendations = []
                for candidate in candidates:
                    # Calculate detailed scores
                    skill_score = self.calculate_assignment_score(candidate, ticket)
                    
                    recommendation = {
                        "user_id": candidate.user_id,
                        "skill_level": candidate.skill_level,
                        "skill_type": candidate.skill_type,
                        "current_workload": candidate.current_workload,
                        "max_workload": candidate.max_workload,
                        "utilization_rate": candidate.current_workload / candidate.max_workload if candidate.max_workload > 0 else 0,
                        "success_rate": candidate.success_rate,
                        "avg_quality_score": candidate.avg_quality_score,
                        "avg_resolution_time": candidate.avg_resolution_time,
                        "is_available": candidate.is_available,
                        "last_active_at": candidate.last_active_at.isoformat() if candidate.last_active_at else None,
                    }

                    if include_scores:
                        recommendation.update({
                            "overall_score": skill_score,
                            "skill_match_score": self._calculate_skill_score(candidate, ticket),
                            "capacity_score": self._calculate_capacity_score(candidate),
                            "performance_score": self._calculate_performance_score(candidate),
                            "recommendation_reason": self._get_recommendation_reason(candidate, ticket, policy)
                        })

                    recommendations.append(recommendation)

                # Sort by overall score
                recommendations.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
                
                return recommendations[:10]  # Return top 10 recommendations

        except Exception as e:
            logger.error(f"Error getting advanced recommendations: {e}")
            return []

    def _get_recommendation_reason(
        self,
        candidate: AnnotatorSkillModel,
        ticket: TicketModel,
        policy: Dict[str, Any]
    ) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        # Skill matching
        if ticket.skill_requirements:
            required_skills = ticket.skill_requirements.get("skills", [])
            if candidate.skill_type in required_skills:
                reasons.append(f"匹配技能: {candidate.skill_type}")
        
        # Workload status
        utilization = candidate.current_workload / candidate.max_workload if candidate.max_workload > 0 else 0
        if utilization < 0.5:
            reasons.append("工作负载较轻")
        elif utilization < 0.8:
            reasons.append("工作负载适中")
        else:
            reasons.append("工作负载较重")
        
        # Performance
        if candidate.success_rate > 0.9:
            reasons.append("成功率高")
        if candidate.avg_quality_score > 0.8:
            reasons.append("质量评分高")
        
        # Priority considerations
        if ticket.priority in [TicketPriority.CRITICAL, TicketPriority.HIGH]:
            if candidate.success_rate > 0.85:
                reasons.append("适合高优先级任务")
        
        return "; ".join(reasons) if reasons else "基础匹配"

    async def evaluate_dispatch_effectiveness(
        self,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Evaluate dispatch effectiveness and provide optimization suggestions.

        Args:
            tenant_id: Optional tenant filter
            days: Analysis period in days

        Returns:
            Effectiveness evaluation and suggestions
        """
        try:
            # Get performance metrics from optimizer
            performance = await self._optimizer.evaluate_dispatch_performance(tenant_id, days)
            
            # Get workload distribution
            workload_dist = await self.get_workload_distribution(tenant_id)
            
            # Calculate effectiveness scores
            effectiveness_scores = {
                "dispatch_success_rate": performance.get("success_rate", 0),
                "sla_compliance_rate": performance.get("sla_compliance_rate", 0),
                "load_balance_score": self._calculate_load_balance_effectiveness(workload_dist),
                "reassignment_rate": performance.get("reassignment_rate", 0),
                "avg_assignment_time": performance.get("avg_assignment_time_seconds", 0)
            }
            
            # Generate optimization suggestions
            suggestions = self._generate_optimization_suggestions(effectiveness_scores, performance)
            
            return {
                "evaluation_period": f"{days} days",
                "effectiveness_scores": effectiveness_scores,
                "performance_metrics": performance,
                "workload_distribution": workload_dist,
                "optimization_suggestions": suggestions,
                "overall_effectiveness": self._calculate_overall_effectiveness(effectiveness_scores)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating dispatch effectiveness: {e}")
            return {}

    def _calculate_load_balance_effectiveness(self, workload_dist: Dict[str, Any]) -> float:
        """Calculate load balance effectiveness score."""
        if not workload_dist or not workload_dist.get("by_user"):
            return 0.0
        
        users = workload_dist["by_user"]
        if len(users) < 2:
            return 1.0  # Perfect balance with single user
        
        utilizations = [user["utilization"] for user in users if user["is_available"]]
        if not utilizations:
            return 0.0
        
        # Calculate coefficient of variation (lower is better)
        mean_util = sum(utilizations) / len(utilizations)
        if mean_util == 0:
            return 1.0
        
        variance = sum((u - mean_util) ** 2 for u in utilizations) / len(utilizations)
        cv = (variance ** 0.5) / mean_util
        
        # Convert to score (0-1, higher is better)
        return max(0.0, 1.0 - cv)

    def _generate_optimization_suggestions(
        self,
        effectiveness_scores: Dict[str, float],
        performance: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization suggestions based on performance."""
        suggestions = []
        
        # Dispatch success rate
        if effectiveness_scores["dispatch_success_rate"] < 0.8:
            suggestions.append("考虑调整技能匹配阈值或增加可用标注员")
        
        # SLA compliance
        if effectiveness_scores["sla_compliance_rate"] < 0.9:
            suggestions.append("优化工单优先级处理或调整SLA时间设置")
        
        # Load balance
        if effectiveness_scores["load_balance_score"] < 0.7:
            suggestions.append("启用负载均衡策略或重新分配工作负载")
        
        # Reassignment rate
        if effectiveness_scores["reassignment_rate"] > 0.2:
            suggestions.append("改进初始派发准确性或加强技能培训")
        
        # Assignment time
        if effectiveness_scores["avg_assignment_time"] > 3600:  # 1 hour
            suggestions.append("优化派发算法或增加自动化程度")
        
        # General suggestions
        total_dispatches = performance.get("total_dispatches", 0)
        if total_dispatches < 10:
            suggestions.append("数据量较少，建议收集更多派发数据以获得准确评估")
        
        return suggestions

    def _calculate_overall_effectiveness(self, scores: Dict[str, float]) -> float:
        """Calculate overall effectiveness score."""
        weights = {
            "dispatch_success_rate": 0.3,
            "sla_compliance_rate": 0.3,
            "load_balance_score": 0.2,
            "reassignment_rate": -0.2  # Negative weight (lower is better)
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in scores:
                if metric == "reassignment_rate":
                    # Invert reassignment rate (lower is better)
                    weighted_score += (1.0 - min(1.0, scores[metric])) * abs(weight)
                else:
                    weighted_score += scores[metric] * weight
                total_weight += abs(weight)
        
        return weighted_score / total_weight if total_weight > 0 else 0.0

    async def get_dispatch_policies(self) -> Dict[str, Any]:
        """Get available dispatch policies."""
        return await self._optimizer.get_dispatch_policies()

    async def update_dispatch_policy(
        self,
        policy_name: str,
        **updates
    ) -> bool:
        """Update a dispatch policy."""
        return await self._optimizer.update_dispatch_policy(policy_name, **updates)

    async def get_dispatch_rules(self) -> List[Dict[str, Any]]:
        """Get dispatch rules configuration."""
        return await self._optimizer.get_dispatch_rules()
