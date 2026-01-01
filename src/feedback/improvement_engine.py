"""
Feedback-driven improvement engine for SuperInsight Platform.

Provides:
- Feedback-based quality improvement mechanisms
- Feedback impact assessment with sentiment analysis
- Preventive improvement measures with pattern recognition
- Customer relationship management integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import re

from .collector import (
    Feedback, FeedbackSource, FeedbackCategory,
    SentimentType, FeedbackStatus, FeedbackCollector
)
from .processor import (
    FeedbackProcessor, ProcessingTask, ProcessingStatus,
    ProcessingPriority
)

logger = logging.getLogger(__name__)


class ImprovementType(str, Enum):
    """Types of improvements."""
    PROCESS = "process"           # Process improvement
    GUIDELINE = "guideline"       # Guideline update
    TRAINING = "training"         # Training enhancement
    TOOL = "tool"                 # Tool improvement
    COMMUNICATION = "communication"  # Communication improvement
    QUALITY = "quality"           # Quality enhancement
    PREVENTIVE = "preventive"     # Preventive measure


class ImprovementStatus(str, Enum):
    """Improvement initiative status."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ImpactLevel(str, Enum):
    """Impact assessment levels."""
    CRITICAL = "critical"   # Requires immediate action
    HIGH = "high"           # Significant impact
    MEDIUM = "medium"       # Moderate impact
    LOW = "low"             # Minor impact


@dataclass
class Pattern:
    """Feedback pattern for common issue recognition."""
    id: UUID
    category: FeedbackCategory
    keywords: List[str]
    description: str
    occurrence_count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    feedback_ids: List[UUID] = field(default_factory=list)
    is_active: bool = True
    threshold_for_action: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "category": self.category.value,
            "keywords": self.keywords,
            "description": self.description,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "feedback_ids": [str(fid) for fid in self.feedback_ids],
            "is_active": self.is_active,
            "threshold_for_action": self.threshold_for_action,
            "needs_action": self.occurrence_count >= self.threshold_for_action
        }


@dataclass
class ImpactAssessment:
    """Impact assessment for feedback."""
    id: UUID
    feedback_ids: List[UUID]
    sentiment_distribution: Dict[str, int]
    avg_sentiment_score: float
    impact_level: ImpactLevel
    affected_areas: List[str]
    risk_score: float  # 0-1
    urgency_score: float  # 0-1
    customer_impact_count: int
    revenue_impact_estimate: Optional[float] = None
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "feedback_ids": [str(fid) for fid in self.feedback_ids],
            "sentiment_distribution": self.sentiment_distribution,
            "avg_sentiment_score": self.avg_sentiment_score,
            "impact_level": self.impact_level.value,
            "affected_areas": self.affected_areas,
            "risk_score": self.risk_score,
            "urgency_score": self.urgency_score,
            "customer_impact_count": self.customer_impact_count,
            "revenue_impact_estimate": self.revenue_impact_estimate,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ImprovementInitiative:
    """Improvement initiative based on feedback."""
    id: UUID
    title: str
    description: str
    improvement_type: ImprovementType
    status: ImprovementStatus = ImprovementStatus.PROPOSED
    priority: ImpactLevel = ImpactLevel.MEDIUM
    source_feedback_ids: List[UUID] = field(default_factory=list)
    pattern_id: Optional[UUID] = None
    assessment_id: Optional[UUID] = None
    owner: Optional[str] = None
    expected_outcomes: List[str] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    success_metrics: List[Dict[str, Any]] = field(default_factory=list)
    actual_outcomes: List[str] = field(default_factory=list)
    effectiveness_score: Optional[float] = None  # 0-1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    target_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "improvement_type": self.improvement_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "source_feedback_ids": [str(fid) for fid in self.source_feedback_ids],
            "pattern_id": str(self.pattern_id) if self.pattern_id else None,
            "assessment_id": str(self.assessment_id) if self.assessment_id else None,
            "owner": self.owner,
            "expected_outcomes": self.expected_outcomes,
            "action_items": self.action_items,
            "success_metrics": self.success_metrics,
            "actual_outcomes": self.actual_outcomes,
            "effectiveness_score": self.effectiveness_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "target_completion": self.target_completion.isoformat() if self.target_completion else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class CustomerRelationship:
    """Customer relationship tracking."""
    customer_id: str
    tenant_id: Optional[str] = None
    total_feedback_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    neutral_feedback_count: int = 0
    avg_sentiment_score: float = 0.0
    satisfaction_trend: str = "stable"  # improving, stable, declining
    last_feedback_at: Optional[datetime] = None
    engagement_score: float = 0.5  # 0-1
    risk_level: str = "low"  # low, medium, high
    notes: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "tenant_id": self.tenant_id,
            "total_feedback_count": self.total_feedback_count,
            "positive_feedback_count": self.positive_feedback_count,
            "negative_feedback_count": self.negative_feedback_count,
            "neutral_feedback_count": self.neutral_feedback_count,
            "avg_sentiment_score": self.avg_sentiment_score,
            "satisfaction_trend": self.satisfaction_trend,
            "last_feedback_at": self.last_feedback_at.isoformat() if self.last_feedback_at else None,
            "engagement_score": self.engagement_score,
            "risk_level": self.risk_level,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ImprovementEngine:
    """
    Feedback-driven improvement engine.

    Analyzes feedback to identify improvement opportunities,
    assess impact, and drive quality improvements.
    """

    # Category to improvement type mapping
    CATEGORY_IMPROVEMENT_MAP = {
        FeedbackCategory.QUALITY: ImprovementType.QUALITY,
        FeedbackCategory.EFFICIENCY: ImprovementType.PROCESS,
        FeedbackCategory.TOOL: ImprovementType.TOOL,
        FeedbackCategory.GUIDELINE: ImprovementType.GUIDELINE,
        FeedbackCategory.COMMUNICATION: ImprovementType.COMMUNICATION,
        FeedbackCategory.SUGGESTION: ImprovementType.PROCESS,
        FeedbackCategory.COMPLAINT: ImprovementType.QUALITY,
    }

    # Impact level thresholds
    IMPACT_THRESHOLDS = {
        "negative_ratio": {
            ImpactLevel.CRITICAL: 0.7,
            ImpactLevel.HIGH: 0.5,
            ImpactLevel.MEDIUM: 0.3,
        },
        "volume": {
            ImpactLevel.CRITICAL: 50,
            ImpactLevel.HIGH: 20,
            ImpactLevel.MEDIUM: 10,
        }
    }

    def __init__(
        self,
        feedback_collector: Optional[FeedbackCollector] = None,
        feedback_processor: Optional[FeedbackProcessor] = None
    ):
        """Initialize the improvement engine."""
        self._collector = feedback_collector or FeedbackCollector()
        self._processor = feedback_processor or FeedbackProcessor(self._collector)
        self._patterns: Dict[UUID, Pattern] = {}
        self._assessments: Dict[UUID, ImpactAssessment] = {}
        self._initiatives: Dict[UUID, ImprovementInitiative] = {}
        self._customer_relationships: Dict[str, CustomerRelationship] = {}

    async def analyze_feedback_pattern(
        self,
        feedback: Feedback
    ) -> Optional[Pattern]:
        """
        Analyze feedback to identify or update patterns.

        Args:
            feedback: Feedback to analyze

        Returns:
            Matched or created pattern
        """
        # Extract keywords from feedback
        keywords = self._extract_pattern_keywords(feedback.content)

        # Try to match existing pattern
        matched_pattern = None
        best_match_score = 0.0

        for pattern in self._patterns.values():
            if pattern.category != feedback.category:
                continue

            # Calculate keyword overlap
            overlap = len(set(pattern.keywords) & set(keywords))
            total = len(set(pattern.keywords) | set(keywords))
            score = overlap / total if total > 0 else 0

            if score > 0.5 and score > best_match_score:
                best_match_score = score
                matched_pattern = pattern

        if matched_pattern:
            # Update existing pattern
            matched_pattern.occurrence_count += 1
            matched_pattern.last_seen = datetime.now()
            matched_pattern.feedback_ids.append(feedback.id)

            # Update keywords
            for kw in keywords:
                if kw not in matched_pattern.keywords:
                    matched_pattern.keywords.append(kw)

            logger.info(
                f"Pattern {matched_pattern.id} updated - "
                f"occurrences: {matched_pattern.occurrence_count}"
            )

            # Check if pattern needs action
            if matched_pattern.occurrence_count >= matched_pattern.threshold_for_action:
                await self._trigger_preventive_action(matched_pattern)

            return matched_pattern

        # Create new pattern if negative feedback
        if feedback.sentiment == SentimentType.NEGATIVE:
            pattern = Pattern(
                id=uuid4(),
                category=feedback.category,
                keywords=keywords,
                description=f"Pattern identified from {feedback.category.value} feedback",
                occurrence_count=1,
                feedback_ids=[feedback.id]
            )
            self._patterns[pattern.id] = pattern

            logger.info(f"New pattern created: {pattern.id}")
            return pattern

        return None

    def _extract_pattern_keywords(self, text: str) -> List[str]:
        """Extract keywords for pattern matching."""
        keywords = []
        text_lower = text.lower()

        # Common issue keywords
        issue_patterns = [
            r'\b(?:error|错误|bug|问题|issue)\b',
            r'\b(?:slow|慢|延迟|delay)\b',
            r'\b(?:wrong|incorrect|不正确)\b',
            r'\b(?:missing|缺失|遗漏)\b',
            r'\b(?:unclear|不清楚|模糊)\b',
            r'\b(?:crash|崩溃|失败)\b',
            r'\b(?:quality|质量)\b',
            r'\b(?:accuracy|准确)\b',
            r'\b(?:consistency|一致性)\b',
        ]

        for pattern in issue_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            keywords.extend(matches)

        # Extract noun phrases (simplified)
        words = text_lower.split()
        for i, word in enumerate(words):
            if len(word) > 3 and word.isalpha():
                keywords.append(word)

        return list(set(keywords))[:10]  # Limit to 10 keywords

    async def _trigger_preventive_action(self, pattern: Pattern) -> None:
        """Trigger preventive action when pattern exceeds threshold."""
        # Create improvement initiative
        initiative = await self.create_improvement_initiative(
            title=f"Preventive Action for {pattern.category.value} Issues",
            description=f"Automated initiative created for recurring pattern with {pattern.occurrence_count} occurrences. Keywords: {', '.join(pattern.keywords[:5])}",
            improvement_type=ImprovementType.PREVENTIVE,
            source_feedback_ids=pattern.feedback_ids[-10:],  # Last 10 feedbacks
            pattern_id=pattern.id,
            priority=ImpactLevel.HIGH if pattern.occurrence_count >= 10 else ImpactLevel.MEDIUM
        )

        logger.warning(
            f"Preventive action triggered for pattern {pattern.id} - "
            f"initiative: {initiative.id}"
        )

    async def assess_feedback_impact(
        self,
        feedback_ids: List[UUID],
        feedbacks: List[Feedback]
    ) -> ImpactAssessment:
        """
        Assess the collective impact of feedback.

        Args:
            feedback_ids: List of feedback IDs
            feedbacks: List of feedback objects

        Returns:
            Impact assessment
        """
        if not feedbacks:
            return ImpactAssessment(
                id=uuid4(),
                feedback_ids=[],
                sentiment_distribution={},
                avg_sentiment_score=0.0,
                impact_level=ImpactLevel.LOW,
                affected_areas=[],
                risk_score=0.0,
                urgency_score=0.0,
                customer_impact_count=0
            )

        # Calculate sentiment distribution
        sentiment_counts = Counter(f.sentiment.value for f in feedbacks)
        sentiment_distribution = dict(sentiment_counts)

        # Calculate average sentiment score
        avg_sentiment = sum(f.sentiment_score for f in feedbacks) / len(feedbacks)

        # Identify affected areas
        affected_areas = list(set(f.category.value for f in feedbacks))

        # Calculate negative ratio
        negative_count = sentiment_counts.get("negative", 0)
        negative_ratio = negative_count / len(feedbacks)

        # Determine impact level
        impact_level = self._determine_impact_level(negative_ratio, len(feedbacks))

        # Calculate risk score
        risk_score = self._calculate_risk_score(feedbacks)

        # Calculate urgency score
        urgency_score = self._calculate_urgency_score(feedbacks)

        # Count unique customers affected
        customer_ids = set(f.submitter_id for f in feedbacks if f.submitter_id)
        customer_impact_count = len(customer_ids)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            feedbacks, impact_level, affected_areas
        )

        assessment = ImpactAssessment(
            id=uuid4(),
            feedback_ids=feedback_ids,
            sentiment_distribution=sentiment_distribution,
            avg_sentiment_score=round(avg_sentiment, 4),
            impact_level=impact_level,
            affected_areas=affected_areas,
            risk_score=round(risk_score, 4),
            urgency_score=round(urgency_score, 4),
            customer_impact_count=customer_impact_count,
            recommendations=recommendations
        )

        self._assessments[assessment.id] = assessment

        logger.info(
            f"Impact assessment created: {assessment.id} - "
            f"level: {impact_level.value}, risk: {risk_score:.2f}"
        )

        return assessment

    def _determine_impact_level(
        self,
        negative_ratio: float,
        volume: int
    ) -> ImpactLevel:
        """Determine impact level based on metrics."""
        # Check negative ratio thresholds
        if negative_ratio >= self.IMPACT_THRESHOLDS["negative_ratio"][ImpactLevel.CRITICAL]:
            return ImpactLevel.CRITICAL
        if negative_ratio >= self.IMPACT_THRESHOLDS["negative_ratio"][ImpactLevel.HIGH]:
            return ImpactLevel.HIGH
        if negative_ratio >= self.IMPACT_THRESHOLDS["negative_ratio"][ImpactLevel.MEDIUM]:
            return ImpactLevel.MEDIUM

        # Check volume thresholds
        if volume >= self.IMPACT_THRESHOLDS["volume"][ImpactLevel.CRITICAL]:
            return ImpactLevel.CRITICAL
        if volume >= self.IMPACT_THRESHOLDS["volume"][ImpactLevel.HIGH]:
            return ImpactLevel.HIGH
        if volume >= self.IMPACT_THRESHOLDS["volume"][ImpactLevel.MEDIUM]:
            return ImpactLevel.MEDIUM

        return ImpactLevel.LOW

    def _calculate_risk_score(self, feedbacks: List[Feedback]) -> float:
        """Calculate risk score from feedback."""
        if not feedbacks:
            return 0.0

        score = 0.0

        # Negative sentiment contribution
        negative_count = sum(1 for f in feedbacks if f.sentiment == SentimentType.NEGATIVE)
        score += (negative_count / len(feedbacks)) * 0.4

        # Complaint category contribution
        complaint_count = sum(1 for f in feedbacks if f.category == FeedbackCategory.COMPLAINT)
        score += (complaint_count / len(feedbacks)) * 0.3

        # Urgent tags contribution
        urgent_count = sum(1 for f in feedbacks if "urgent" in f.tags)
        score += (urgent_count / len(feedbacks)) * 0.2

        # Volume contribution
        score += min(len(feedbacks) / 100, 0.1)  # Cap at 0.1

        return min(score, 1.0)

    def _calculate_urgency_score(self, feedbacks: List[Feedback]) -> float:
        """Calculate urgency score from feedback."""
        if not feedbacks:
            return 0.0

        score = 0.0

        # Recent feedback is more urgent
        now = datetime.now()
        recent_count = sum(
            1 for f in feedbacks
            if (now - f.created_at).days <= 7
        )
        score += (recent_count / len(feedbacks)) * 0.3

        # Negative sentiment urgency
        negative_scores = [
            abs(f.sentiment_score) for f in feedbacks
            if f.sentiment == SentimentType.NEGATIVE
        ]
        if negative_scores:
            score += (sum(negative_scores) / len(negative_scores)) * 0.4

        # Complaint urgency
        complaint_ratio = sum(
            1 for f in feedbacks if f.category == FeedbackCategory.COMPLAINT
        ) / len(feedbacks)
        score += complaint_ratio * 0.3

        return min(score, 1.0)

    def _generate_recommendations(
        self,
        feedbacks: List[Feedback],
        impact_level: ImpactLevel,
        affected_areas: List[str]
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Impact-based recommendations
        if impact_level == ImpactLevel.CRITICAL:
            recommendations.append("Immediate escalation to management required")
            recommendations.append("Consider emergency response team activation")

        if impact_level in [ImpactLevel.CRITICAL, ImpactLevel.HIGH]:
            recommendations.append("Schedule stakeholder communication")
            recommendations.append("Implement immediate mitigation measures")

        # Area-based recommendations
        if "quality" in affected_areas:
            recommendations.append("Review and update quality guidelines")
            recommendations.append("Consider additional quality training")

        if "tool" in affected_areas:
            recommendations.append("Prioritize reported tool issues in backlog")
            recommendations.append("Review system stability and performance")

        if "guideline" in affected_areas:
            recommendations.append("Clarify ambiguous guidelines")
            recommendations.append("Update documentation and examples")

        if "efficiency" in affected_areas:
            recommendations.append("Analyze workflow bottlenecks")
            recommendations.append("Consider process optimization")

        # Sentiment-based recommendations
        negative_count = sum(1 for f in feedbacks if f.sentiment == SentimentType.NEGATIVE)
        if negative_count > len(feedbacks) * 0.5:
            recommendations.append("Implement customer satisfaction recovery program")

        return recommendations[:8]  # Limit to 8 recommendations

    async def create_improvement_initiative(
        self,
        title: str,
        description: str,
        improvement_type: ImprovementType,
        source_feedback_ids: Optional[List[UUID]] = None,
        pattern_id: Optional[UUID] = None,
        assessment_id: Optional[UUID] = None,
        priority: ImpactLevel = ImpactLevel.MEDIUM,
        owner: Optional[str] = None,
        target_days: int = 30
    ) -> ImprovementInitiative:
        """
        Create an improvement initiative.

        Args:
            title: Initiative title
            description: Initiative description
            improvement_type: Type of improvement
            source_feedback_ids: Related feedback IDs
            pattern_id: Related pattern ID
            assessment_id: Related assessment ID
            priority: Priority level
            owner: Initiative owner
            target_days: Target completion days

        Returns:
            Created initiative
        """
        initiative = ImprovementInitiative(
            id=uuid4(),
            title=title,
            description=description,
            improvement_type=improvement_type,
            priority=priority,
            source_feedback_ids=source_feedback_ids or [],
            pattern_id=pattern_id,
            assessment_id=assessment_id,
            owner=owner,
            target_completion=datetime.now() + timedelta(days=target_days)
        )

        # Generate default action items based on type
        initiative.action_items = self._generate_action_items(improvement_type)

        # Generate success metrics
        initiative.success_metrics = self._generate_success_metrics(improvement_type)

        self._initiatives[initiative.id] = initiative

        logger.info(f"Improvement initiative created: {initiative.id} - {title}")
        return initiative

    def _generate_action_items(self, improvement_type: ImprovementType) -> List[Dict[str, Any]]:
        """Generate default action items for improvement type."""
        action_templates = {
            ImprovementType.QUALITY: [
                {"action": "Review affected data samples", "status": "pending"},
                {"action": "Update quality checkpoints", "status": "pending"},
                {"action": "Retrain affected annotators", "status": "pending"},
                {"action": "Verify improvement in quality metrics", "status": "pending"}
            ],
            ImprovementType.PROCESS: [
                {"action": "Map current process workflow", "status": "pending"},
                {"action": "Identify improvement opportunities", "status": "pending"},
                {"action": "Design improved workflow", "status": "pending"},
                {"action": "Implement and test changes", "status": "pending"},
                {"action": "Document new process", "status": "pending"}
            ],
            ImprovementType.GUIDELINE: [
                {"action": "Review current guidelines", "status": "pending"},
                {"action": "Identify unclear sections", "status": "pending"},
                {"action": "Draft guideline updates", "status": "pending"},
                {"action": "Review with stakeholders", "status": "pending"},
                {"action": "Publish updated guidelines", "status": "pending"}
            ],
            ImprovementType.TRAINING: [
                {"action": "Identify training gaps", "status": "pending"},
                {"action": "Develop training materials", "status": "pending"},
                {"action": "Schedule training sessions", "status": "pending"},
                {"action": "Conduct training", "status": "pending"},
                {"action": "Evaluate training effectiveness", "status": "pending"}
            ],
            ImprovementType.TOOL: [
                {"action": "Reproduce reported issue", "status": "pending"},
                {"action": "Analyze root cause", "status": "pending"},
                {"action": "Develop fix or enhancement", "status": "pending"},
                {"action": "Test solution", "status": "pending"},
                {"action": "Deploy and verify", "status": "pending"}
            ],
            ImprovementType.COMMUNICATION: [
                {"action": "Review communication channels", "status": "pending"},
                {"action": "Identify communication gaps", "status": "pending"},
                {"action": "Establish improvement measures", "status": "pending"},
                {"action": "Implement changes", "status": "pending"},
                {"action": "Monitor communication effectiveness", "status": "pending"}
            ],
            ImprovementType.PREVENTIVE: [
                {"action": "Analyze pattern root cause", "status": "pending"},
                {"action": "Design preventive measures", "status": "pending"},
                {"action": "Implement controls", "status": "pending"},
                {"action": "Monitor for recurrence", "status": "pending"}
            ]
        }

        return action_templates.get(improvement_type, [
            {"action": "Analyze issue", "status": "pending"},
            {"action": "Design solution", "status": "pending"},
            {"action": "Implement and verify", "status": "pending"}
        ])

    def _generate_success_metrics(self, improvement_type: ImprovementType) -> List[Dict[str, Any]]:
        """Generate success metrics for improvement type."""
        metric_templates = {
            ImprovementType.QUALITY: [
                {"metric": "Quality score improvement", "target": "10% increase"},
                {"metric": "Error rate reduction", "target": "20% decrease"},
                {"metric": "Customer satisfaction", "target": ">4.0 rating"}
            ],
            ImprovementType.PROCESS: [
                {"metric": "Process cycle time", "target": "15% reduction"},
                {"metric": "Throughput increase", "target": "10% improvement"},
                {"metric": "Process compliance", "target": ">95%"}
            ],
            ImprovementType.GUIDELINE: [
                {"metric": "Guideline compliance", "target": ">90%"},
                {"metric": "Confusion-related feedback", "target": "50% reduction"},
                {"metric": "Consistency score", "target": ">0.85"}
            ],
            ImprovementType.TRAINING: [
                {"metric": "Training completion rate", "target": "100%"},
                {"metric": "Post-training assessment score", "target": ">80%"},
                {"metric": "Performance improvement", "target": "15% increase"}
            ],
            ImprovementType.TOOL: [
                {"metric": "Tool-related issues", "target": "80% reduction"},
                {"metric": "System uptime", "target": ">99.5%"},
                {"metric": "User satisfaction", "target": ">4.0 rating"}
            ],
            ImprovementType.COMMUNICATION: [
                {"metric": "Response time", "target": "<4 hours"},
                {"metric": "Communication satisfaction", "target": ">4.0 rating"},
                {"metric": "Information accuracy", "target": ">95%"}
            ],
            ImprovementType.PREVENTIVE: [
                {"metric": "Issue recurrence rate", "target": "<5%"},
                {"metric": "Proactive detection rate", "target": ">80%"},
                {"metric": "Prevention effectiveness", "target": ">90%"}
            ]
        }

        return metric_templates.get(improvement_type, [
            {"metric": "Issue resolution", "target": "100%"},
            {"metric": "Customer satisfaction", "target": ">4.0"}
        ])

    async def update_initiative_status(
        self,
        initiative_id: UUID,
        status: ImprovementStatus,
        notes: Optional[str] = None,
        actual_outcomes: Optional[List[str]] = None
    ) -> bool:
        """
        Update initiative status.

        Args:
            initiative_id: Initiative UUID
            status: New status
            notes: Optional notes
            actual_outcomes: Actual outcomes achieved

        Returns:
            True if updated
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return False

        old_status = initiative.status
        initiative.status = status
        initiative.updated_at = datetime.now()

        if actual_outcomes:
            initiative.actual_outcomes.extend(actual_outcomes)

        if status == ImprovementStatus.IMPLEMENTED:
            initiative.completed_at = datetime.now()

        logger.info(
            f"Initiative {initiative_id} status updated: "
            f"{old_status.value} -> {status.value}"
        )
        return True

    async def evaluate_initiative_effectiveness(
        self,
        initiative_id: UUID,
        post_implementation_feedbacks: List[Feedback]
    ) -> float:
        """
        Evaluate initiative effectiveness.

        Args:
            initiative_id: Initiative UUID
            post_implementation_feedbacks: Feedbacks after implementation

        Returns:
            Effectiveness score (0-1)
        """
        initiative = self._initiatives.get(initiative_id)
        if not initiative:
            return 0.0

        if not post_implementation_feedbacks:
            return 0.5  # Neutral if no feedback

        # Calculate improvement in sentiment
        positive_ratio = sum(
            1 for f in post_implementation_feedbacks
            if f.sentiment == SentimentType.POSITIVE
        ) / len(post_implementation_feedbacks)

        negative_ratio = sum(
            1 for f in post_implementation_feedbacks
            if f.sentiment == SentimentType.NEGATIVE
        ) / len(post_implementation_feedbacks)

        # Effectiveness based on positive/negative ratio
        effectiveness = positive_ratio - (negative_ratio * 0.5)
        effectiveness = max(0.0, min(1.0, effectiveness + 0.5))  # Normalize to 0-1

        initiative.effectiveness_score = round(effectiveness, 4)
        initiative.status = ImprovementStatus.VERIFIED
        initiative.updated_at = datetime.now()

        logger.info(
            f"Initiative {initiative_id} effectiveness evaluated: {effectiveness:.2f}"
        )

        return effectiveness

    async def update_customer_relationship(
        self,
        feedback: Feedback
    ) -> CustomerRelationship:
        """
        Update customer relationship based on feedback.

        Args:
            feedback: New feedback

        Returns:
            Updated customer relationship
        """
        customer_id = feedback.submitter_id or "anonymous"

        if customer_id not in self._customer_relationships:
            self._customer_relationships[customer_id] = CustomerRelationship(
                customer_id=customer_id,
                tenant_id=feedback.tenant_id
            )

        relationship = self._customer_relationships[customer_id]

        # Update counts
        relationship.total_feedback_count += 1
        if feedback.sentiment == SentimentType.POSITIVE:
            relationship.positive_feedback_count += 1
        elif feedback.sentiment == SentimentType.NEGATIVE:
            relationship.negative_feedback_count += 1
        else:
            relationship.neutral_feedback_count += 1

        # Update average sentiment
        total = relationship.total_feedback_count
        old_avg = relationship.avg_sentiment_score
        relationship.avg_sentiment_score = (
            (old_avg * (total - 1) + feedback.sentiment_score) / total
        )

        # Update last feedback time
        relationship.last_feedback_at = feedback.created_at
        relationship.updated_at = datetime.now()

        # Update trend
        relationship.satisfaction_trend = self._calculate_trend(relationship)

        # Update risk level
        relationship.risk_level = self._calculate_risk_level(relationship)

        # Update engagement score
        relationship.engagement_score = self._calculate_engagement_score(relationship)

        logger.debug(
            f"Customer relationship updated: {customer_id} - "
            f"trend: {relationship.satisfaction_trend}, risk: {relationship.risk_level}"
        )

        return relationship

    def _calculate_trend(self, relationship: CustomerRelationship) -> str:
        """Calculate satisfaction trend."""
        if relationship.total_feedback_count < 3:
            return "stable"

        positive_ratio = relationship.positive_feedback_count / relationship.total_feedback_count
        negative_ratio = relationship.negative_feedback_count / relationship.total_feedback_count

        if positive_ratio > 0.6:
            return "improving"
        elif negative_ratio > 0.4:
            return "declining"
        return "stable"

    def _calculate_risk_level(self, relationship: CustomerRelationship) -> str:
        """Calculate customer risk level."""
        if relationship.total_feedback_count == 0:
            return "low"

        negative_ratio = relationship.negative_feedback_count / relationship.total_feedback_count

        if negative_ratio > 0.5 or relationship.avg_sentiment_score < -0.3:
            return "high"
        elif negative_ratio > 0.3 or relationship.avg_sentiment_score < 0:
            return "medium"
        return "low"

    def _calculate_engagement_score(self, relationship: CustomerRelationship) -> float:
        """Calculate customer engagement score."""
        # Base on feedback frequency and recency
        score = 0.5

        # Volume contribution
        score += min(relationship.total_feedback_count * 0.02, 0.2)

        # Positive feedback contribution
        if relationship.total_feedback_count > 0:
            positive_ratio = relationship.positive_feedback_count / relationship.total_feedback_count
            score += positive_ratio * 0.2

        # Recency contribution
        if relationship.last_feedback_at:
            days_since = (datetime.now() - relationship.last_feedback_at).days
            if days_since < 7:
                score += 0.1
            elif days_since < 30:
                score += 0.05

        return min(score, 1.0)

    async def get_pattern(self, pattern_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a pattern by ID."""
        pattern = self._patterns.get(pattern_id)
        return pattern.to_dict() if pattern else None

    async def list_patterns(
        self,
        category: Optional[FeedbackCategory] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List patterns with filters."""
        patterns = list(self._patterns.values())

        if category:
            patterns = [p for p in patterns if p.category == category]
        if active_only:
            patterns = [p for p in patterns if p.is_active]

        # Sort by occurrence count descending
        patterns.sort(key=lambda x: x.occurrence_count, reverse=True)

        return [p.to_dict() for p in patterns[:limit]]

    async def get_initiative(self, initiative_id: UUID) -> Optional[Dict[str, Any]]:
        """Get an initiative by ID."""
        initiative = self._initiatives.get(initiative_id)
        return initiative.to_dict() if initiative else None

    async def list_initiatives(
        self,
        status: Optional[ImprovementStatus] = None,
        improvement_type: Optional[ImprovementType] = None,
        priority: Optional[ImpactLevel] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List initiatives with filters."""
        initiatives = list(self._initiatives.values())

        if status:
            initiatives = [i for i in initiatives if i.status == status]
        if improvement_type:
            initiatives = [i for i in initiatives if i.improvement_type == improvement_type]
        if priority:
            initiatives = [i for i in initiatives if i.priority == priority]

        # Sort by priority and creation date
        priority_order = {
            ImpactLevel.CRITICAL: 0,
            ImpactLevel.HIGH: 1,
            ImpactLevel.MEDIUM: 2,
            ImpactLevel.LOW: 3
        }
        initiatives.sort(key=lambda x: (priority_order.get(x.priority, 4), x.created_at))

        return [i.to_dict() for i in initiatives[:limit]]

    async def get_customer_relationship(
        self,
        customer_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get customer relationship."""
        relationship = self._customer_relationships.get(customer_id)
        return relationship.to_dict() if relationship else None

    async def list_at_risk_customers(
        self,
        risk_level: str = "high",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List at-risk customers."""
        customers = [
            c for c in self._customer_relationships.values()
            if c.risk_level == risk_level
        ]

        # Sort by negative feedback count descending
        customers.sort(key=lambda x: x.negative_feedback_count, reverse=True)

        return [c.to_dict() for c in customers[:limit]]

    async def get_improvement_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get improvement statistics.

        Args:
            days: Analysis period

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now() - timedelta(days=days)

        # Patterns
        patterns = [p for p in self._patterns.values() if p.last_seen >= cutoff]
        active_patterns = len([p for p in patterns if p.is_active])
        patterns_needing_action = len([
            p for p in patterns
            if p.occurrence_count >= p.threshold_for_action
        ])

        # Initiatives
        initiatives = [i for i in self._initiatives.values() if i.created_at >= cutoff]
        by_status = Counter(i.status.value for i in initiatives)
        by_type = Counter(i.improvement_type.value for i in initiatives)

        # Effectiveness
        verified = [i for i in initiatives if i.status == ImprovementStatus.VERIFIED]
        avg_effectiveness = (
            sum(i.effectiveness_score or 0 for i in verified) / len(verified)
            if verified else 0
        )

        # Customer relationships
        high_risk = len([c for c in self._customer_relationships.values() if c.risk_level == "high"])
        declining = len([c for c in self._customer_relationships.values() if c.satisfaction_trend == "declining"])

        return {
            "period_days": days,
            "patterns": {
                "total": len(patterns),
                "active": active_patterns,
                "needing_action": patterns_needing_action
            },
            "initiatives": {
                "total": len(initiatives),
                "by_status": dict(by_status),
                "by_type": dict(by_type),
                "avg_effectiveness": round(avg_effectiveness, 4)
            },
            "customer_risk": {
                "high_risk_count": high_risk,
                "declining_trend_count": declining,
                "total_tracked": len(self._customer_relationships)
            },
            "generated_at": datetime.now().isoformat()
        }
