"""Best Practice Library Service for ontology modeling best practices.

This module provides a library of curated best practices:
- Best practice storage and retrieval
- Industry and use case categorization
- Usage tracking and promotion
- Step-by-step application guidance
- Peer review and contribution workflow

Requirements:
- 11.1: Best practice library
- 11.2: Best practice display completeness
- 11.3: Application guidance
- 11.4: Contribution and review
- 11.5: Usage-based promotion
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
import statistics


class BestPracticeCategory(str, Enum):
    """Category of best practice."""
    DATA_MODELING = "data_modeling"
    ENTITY_DESIGN = "entity_design"
    RELATION_DESIGN = "relation_design"
    ATTRIBUTE_DESIGN = "attribute_design"
    NAMING_CONVENTION = "naming_convention"
    VALIDATION_RULES = "validation_rules"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class Industry(str, Enum):
    """Industry type."""
    FINANCE = "金融"
    HEALTHCARE = "医疗"
    MANUFACTURING = "制造"
    RETAIL = "零售"
    TECHNOLOGY = "科技"
    GOVERNMENT = "政府"
    EDUCATION = "教育"
    GENERAL = "通用"


class BestPracticeStatus(str, Enum):
    """Status of best practice."""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class ConfigurationStep:
    """Step in best practice application."""
    step_number: int = 0
    title: str = ""
    description: str = ""
    instructions: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    example: Optional[str] = None


@dataclass
class BestPractice:
    """Best practice for ontology modeling."""
    practice_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    category: BestPracticeCategory = BestPracticeCategory.DATA_MODELING
    industry: Industry = Industry.GENERAL
    use_case: str = ""

    # Content
    problem_statement: str = ""
    solution: str = ""
    benefits: List[str] = field(default_factory=list)
    configuration_steps: List[ConfigurationStep] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    author_id: UUID = field(default_factory=uuid4)
    status: BestPracticeStatus = BestPracticeStatus.DRAFT
    usage_count: int = 0
    rating_sum: float = 0.0
    rating_count: int = 0
    is_promoted: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Tags
    tags: List[str] = field(default_factory=list)


@dataclass
class BestPracticeReview:
    """Review of a best practice submission."""
    review_id: UUID = field(default_factory=uuid4)
    practice_id: UUID = field(default_factory=uuid4)
    reviewer_id: UUID = field(default_factory=uuid4)
    decision: str = ""  # "approve", "reject", "request_changes"
    comments: str = ""
    rating: float = 0.0  # 1.0-5.0
    reviewed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApplicationSession:
    """Session for applying a best practice."""
    session_id: UUID = field(default_factory=uuid4)
    practice_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)

    # Progress tracking
    current_step: int = 0
    completed_steps: Set[int] = field(default_factory=set)
    step_results: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # Session state
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    is_completed: bool = False


class BestPracticeService:
    """Service for managing best practice library."""

    def __init__(self):
        """Initialize best practice service."""
        self._practices: Dict[UUID, BestPractice] = {}
        self._reviews: Dict[UUID, List[BestPracticeReview]] = {}
        self._sessions: Dict[UUID, ApplicationSession] = {}
        self._lock = asyncio.Lock()

        # Configuration
        self._promotion_percentile = 75  # 75th percentile for promotion

    async def create_best_practice(
        self,
        author_id: UUID,
        title: str,
        description: str,
        category: BestPracticeCategory,
        industry: Industry,
        use_case: str,
        problem_statement: str,
        solution: str,
        benefits: List[str],
        configuration_steps: List[ConfigurationStep],
        examples: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None
    ) -> BestPractice:
        """Create a new best practice.

        Args:
            author_id: Author's expert ID
            title: Practice title
            description: Short description
            category: Practice category
            industry: Target industry
            use_case: Specific use case
            problem_statement: Problem being solved
            solution: Solution approach
            benefits: List of benefits
            configuration_steps: Steps to apply practice
            examples: Usage examples
            tags: Search tags

        Returns:
            Created best practice
        """
        async with self._lock:
            practice = BestPractice(
                title=title,
                description=description,
                category=category,
                industry=industry,
                use_case=use_case,
                problem_statement=problem_statement,
                solution=solution,
                benefits=benefits,
                configuration_steps=configuration_steps,
                examples=examples or [],
                author_id=author_id,
                tags=tags or []
            )

            self._practices[practice.practice_id] = practice
            return practice

    async def submit_best_practice(
        self,
        practice_id: UUID,
        reviewer_ids: List[UUID]
    ) -> BestPractice:
        """Submit a best practice for review.

        Args:
            practice_id: Practice ID
            reviewer_ids: List of reviewer IDs

        Returns:
            Updated practice

        Raises:
            ValueError: If practice not found or already submitted
        """
        async with self._lock:
            if practice_id not in self._practices:
                raise ValueError(f"Practice {practice_id} not found")

            practice = self._practices[practice_id]

            if practice.status != BestPracticeStatus.DRAFT:
                raise ValueError(f"Practice is not in draft status: {practice.status}")

            practice.status = BestPracticeStatus.UNDER_REVIEW
            practice.updated_at = datetime.utcnow()

            # Initialize review tracking
            if practice_id not in self._reviews:
                self._reviews[practice_id] = []

            return practice

    async def review_best_practice(
        self,
        practice_id: UUID,
        reviewer_id: UUID,
        decision: str,
        comments: str,
        rating: float = 0.0
    ) -> BestPracticeReview:
        """Review a best practice submission.

        Args:
            practice_id: Practice ID
            reviewer_id: Reviewer ID
            decision: "approve", "reject", or "request_changes"
            comments: Review comments
            rating: Quality rating (1.0-5.0)

        Returns:
            Review record

        Raises:
            ValueError: If practice not found or not under review
        """
        async with self._lock:
            if practice_id not in self._practices:
                raise ValueError(f"Practice {practice_id} not found")

            practice = self._practices[practice_id]

            if practice.status != BestPracticeStatus.UNDER_REVIEW:
                raise ValueError(f"Practice is not under review: {practice.status}")

            # Create review
            review = BestPracticeReview(
                practice_id=practice_id,
                reviewer_id=reviewer_id,
                decision=decision,
                comments=comments,
                rating=rating
            )

            if practice_id not in self._reviews:
                self._reviews[practice_id] = []
            self._reviews[practice_id].append(review)

            # Update practice status based on decision
            if decision == "approve":
                # Check if all reviewers approved (simplified: approve on first approval)
                practice.status = BestPracticeStatus.APPROVED
                practice.published_at = datetime.utcnow()
                practice.rating_sum += rating
                practice.rating_count += 1
            elif decision == "reject":
                practice.status = BestPracticeStatus.REJECTED
            elif decision == "request_changes":
                practice.status = BestPracticeStatus.DRAFT

            practice.updated_at = datetime.utcnow()

            return review

    async def get_best_practice(
        self,
        practice_id: UUID
    ) -> Optional[BestPractice]:
        """Get a best practice by ID.

        Args:
            practice_id: Practice ID

        Returns:
            Best practice or None
        """
        async with self._lock:
            return self._practices.get(practice_id)

    async def search_best_practices(
        self,
        category: Optional[BestPracticeCategory] = None,
        industry: Optional[Industry] = None,
        use_case: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_drafts: bool = False
    ) -> List[BestPractice]:
        """Search for best practices.

        Args:
            category: Filter by category
            industry: Filter by industry
            use_case: Filter by use case (substring match)
            tags: Filter by tags
            include_drafts: Include draft practices

        Returns:
            List of matching practices
        """
        async with self._lock:
            results = []

            for practice in self._practices.values():
                # Status filter
                if not include_drafts and practice.status != BestPracticeStatus.APPROVED:
                    continue

                # Category filter
                if category and practice.category != category:
                    continue

                # Industry filter (match specific or GENERAL)
                if industry and practice.industry != industry and practice.industry != Industry.GENERAL:
                    continue

                # Use case filter
                if use_case and use_case.lower() not in practice.use_case.lower():
                    continue

                # Tags filter
                if tags and not any(tag in practice.tags for tag in tags):
                    continue

                results.append(practice)

            # Sort by promotion status and usage count
            results.sort(key=lambda p: (p.is_promoted, p.usage_count), reverse=True)

            return results

    async def apply_best_practice(
        self,
        practice_id: UUID,
        user_id: UUID,
        ontology_id: UUID
    ) -> ApplicationSession:
        """Start applying a best practice.

        Args:
            practice_id: Practice ID
            user_id: User ID
            ontology_id: Target ontology ID

        Returns:
            Application session

        Raises:
            ValueError: If practice not found or not approved
        """
        async with self._lock:
            if practice_id not in self._practices:
                raise ValueError(f"Practice {practice_id} not found")

            practice = self._practices[practice_id]

            if practice.status != BestPracticeStatus.APPROVED:
                raise ValueError(f"Practice is not approved: {practice.status}")

            # Create application session
            session = ApplicationSession(
                practice_id=practice_id,
                user_id=user_id,
                ontology_id=ontology_id
            )

            self._sessions[session.session_id] = session

            # Increment usage count
            practice.usage_count += 1
            practice.updated_at = datetime.utcnow()

            # Check for promotion eligibility
            await self._update_promotion_status()

            return session

    async def complete_step(
        self,
        session_id: UUID,
        step_number: int,
        result: Dict[str, Any]
    ) -> ApplicationSession:
        """Complete a step in the application process.

        Args:
            session_id: Session ID
            step_number: Step number
            result: Step result data

        Returns:
            Updated session

        Raises:
            ValueError: If session not found
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self._sessions[session_id]

            # Mark step as completed
            session.completed_steps.add(step_number)
            session.step_results[step_number] = result
            session.current_step = step_number + 1

            # Check if all steps completed
            practice = self._practices.get(session.practice_id)
            if practice and len(session.completed_steps) == len(practice.configuration_steps):
                session.is_completed = True
                session.completed_at = datetime.utcnow()

            return session

    async def get_application_session(
        self,
        session_id: UUID
    ) -> Optional[ApplicationSession]:
        """Get an application session.

        Args:
            session_id: Session ID

        Returns:
            Application session or None
        """
        async with self._lock:
            return self._sessions.get(session_id)

    async def get_next_step(
        self,
        session_id: UUID
    ) -> Optional[ConfigurationStep]:
        """Get the next step for an application session.

        Args:
            session_id: Session ID

        Returns:
            Next configuration step or None if completed
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            practice = self._practices.get(session.practice_id)
            if not practice:
                return None

            # Return current step
            if session.current_step < len(practice.configuration_steps):
                return practice.configuration_steps[session.current_step]

            return None

    async def _update_promotion_status(self) -> None:
        """Update promotion status for practices based on usage."""
        # Get all approved practices
        approved_practices = [
            p for p in self._practices.values()
            if p.status == BestPracticeStatus.APPROVED
        ]

        if len(approved_practices) < 4:
            # Need at least 4 practices to calculate 75th percentile
            return

        # Calculate 75th percentile of usage counts
        usage_counts = [p.usage_count for p in approved_practices]
        threshold = statistics.quantiles(usage_counts, n=4)[2]  # 75th percentile

        # Update promotion status
        for practice in approved_practices:
            practice.is_promoted = practice.usage_count >= threshold

    async def get_popular_practices(
        self,
        limit: int = 10,
        category: Optional[BestPracticeCategory] = None,
        industry: Optional[Industry] = None
    ) -> List[BestPractice]:
        """Get popular (promoted) best practices.

        Args:
            limit: Maximum number to return
            category: Filter by category
            industry: Filter by industry

        Returns:
            List of popular practices
        """
        async with self._lock:
            practices = [
                p for p in self._practices.values()
                if p.status == BestPracticeStatus.APPROVED and p.is_promoted
            ]

            # Apply filters
            if category:
                practices = [p for p in practices if p.category == category]

            if industry:
                practices = [p for p in practices if p.industry == industry or p.industry == Industry.GENERAL]

            # Sort by usage count
            practices.sort(key=lambda p: p.usage_count, reverse=True)

            return practices[:limit]

    async def get_reviews(
        self,
        practice_id: UUID
    ) -> List[BestPracticeReview]:
        """Get reviews for a best practice.

        Args:
            practice_id: Practice ID

        Returns:
            List of reviews
        """
        async with self._lock:
            return self._reviews.get(practice_id, [])

    async def get_average_rating(
        self,
        practice_id: UUID
    ) -> float:
        """Get average rating for a best practice.

        Args:
            practice_id: Practice ID

        Returns:
            Average rating or 0.0 if no ratings
        """
        async with self._lock:
            practice = self._practices.get(practice_id)
            if not practice or practice.rating_count == 0:
                return 0.0

            return practice.rating_sum / practice.rating_count

    async def list_all_practices(
        self,
        status: Optional[BestPracticeStatus] = None
    ) -> List[BestPractice]:
        """List all best practices.

        Args:
            status: Filter by status

        Returns:
            List of practices
        """
        async with self._lock:
            practices = list(self._practices.values())

            if status:
                practices = [p for p in practices if p.status == status]

            return practices

    async def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for the best practice library.

        Returns:
            Dictionary of statistics
        """
        async with self._lock:
            approved_practices = [
                p for p in self._practices.values()
                if p.status == BestPracticeStatus.APPROVED
            ]

            total_usage = sum(p.usage_count for p in approved_practices)
            promoted_count = sum(1 for p in approved_practices if p.is_promoted)

            stats = {
                "total_practices": len(self._practices),
                "approved_practices": len(approved_practices),
                "promoted_practices": promoted_count,
                "total_usage_count": total_usage,
                "active_sessions": sum(1 for s in self._sessions.values() if not s.is_completed),
                "completed_sessions": sum(1 for s in self._sessions.values() if s.is_completed)
            }

            # Calculate average usage for approved practices
            if approved_practices:
                stats["average_usage"] = total_usage / len(approved_practices)

            return stats
