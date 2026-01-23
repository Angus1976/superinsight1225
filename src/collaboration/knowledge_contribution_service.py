"""Knowledge Contribution Tracking Service for ontology collaboration.

This module provides comprehensive tracking of expert contributions:
- Comment threading with parent-child relationships
- Entity and relation suggestions
- Document attachments (PDF, images, links)
- Contribution metrics and quality scoring
- Expert recognition and reputation

Requirements:
- 6.1: Expert comments and discussions
- 6.2: Entity suggestions
- 6.3: Relation suggestions
- 6.4: Document attachments
- 6.5: Contribution metrics
- 9.3: Expert recommendation updates
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class ContributionType(str, Enum):
    """Type of contribution."""
    COMMENT = "comment"
    ENTITY_SUGGESTION = "entity_suggestion"
    RELATION_SUGGESTION = "relation_suggestion"
    DOCUMENT_ATTACHMENT = "document_attachment"
    BEST_PRACTICE = "best_practice"


class ContributionStatus(str, Enum):
    """Status of a contribution."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"


class DocumentType(str, Enum):
    """Type of document attachment."""
    PDF = "pdf"
    IMAGE = "image"
    LINK = "link"
    WORD = "word"
    EXCEL = "excel"


@dataclass
class Comment:
    """Expert comment on an ontology element."""
    comment_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""  # "entity_type", "relation_type", "attribute"
    expert_id: UUID = field(default_factory=uuid4)
    content: str = ""
    parent_comment_id: Optional[UUID] = None  # For threaded discussions
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None


@dataclass
class EntitySuggestion:
    """Suggestion for a new or modified entity."""
    suggestion_id: UUID = field(default_factory=uuid4)
    expert_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)
    entity_type_id: Optional[UUID] = None  # None for new entity
    suggested_name: str = ""
    suggested_description: str = ""
    suggested_attributes: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    status: ContributionStatus = ContributionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: str = ""


@dataclass
class RelationSuggestion:
    """Suggestion for a new or modified relation."""
    suggestion_id: UUID = field(default_factory=uuid4)
    expert_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)
    relation_type_id: Optional[UUID] = None  # None for new relation
    suggested_name: str = ""
    suggested_description: str = ""
    source_entity_type: str = ""
    target_entity_type: str = ""
    cardinality: str = ""  # "1:1", "1:N", "N:M"
    rationale: str = ""
    status: ContributionStatus = ContributionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: str = ""


@dataclass
class DocumentAttachment:
    """Document attached to an ontology element."""
    attachment_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""
    expert_id: UUID = field(default_factory=uuid4)
    document_type: DocumentType = DocumentType.LINK
    title: str = ""
    description: str = ""
    url: Optional[str] = None  # For links and uploaded files
    file_path: Optional[str] = None  # Local storage path
    file_size_bytes: int = 0
    mime_type: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContributionMetrics:
    """Metrics for an expert's contributions."""
    expert_id: UUID = field(default_factory=uuid4)
    total_contributions: int = 0
    accepted_contributions: int = 0
    rejected_contributions: int = 0
    pending_contributions: int = 0
    comments_count: int = 0
    entity_suggestions_count: int = 0
    relation_suggestions_count: int = 0
    document_attachments_count: int = 0
    acceptance_rate: float = 0.0  # accepted / (accepted + rejected)
    average_quality_score: float = 0.0  # Peer review scores
    contribution_score: float = 0.0  # Overall reputation score
    last_contribution_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


class KnowledgeContributionService:
    """Service for tracking and managing expert contributions."""

    def __init__(self):
        """Initialize knowledge contribution service."""
        self._comments: Dict[UUID, Comment] = {}
        self._entity_suggestions: Dict[UUID, EntitySuggestion] = {}
        self._relation_suggestions: Dict[UUID, RelationSuggestion] = {}
        self._attachments: Dict[UUID, DocumentAttachment] = {}
        self._metrics: Dict[UUID, ContributionMetrics] = {}
        self._lock = asyncio.Lock()

        # Configuration
        self._quality_score_weight = 0.6
        self._acceptance_rate_weight = 0.4

    async def add_comment(
        self,
        element_id: UUID,
        element_type: str,
        expert_id: UUID,
        content: str,
        parent_comment_id: Optional[UUID] = None
    ) -> Comment:
        """Add a comment to an ontology element.

        Args:
            element_id: Element being commented on
            element_type: Type of element
            expert_id: Expert making comment
            content: Comment content
            parent_comment_id: Parent comment for threading

        Returns:
            Created comment
        """
        async with self._lock:
            # Validate parent comment exists if provided
            if parent_comment_id and parent_comment_id not in self._comments:
                raise ValueError(f"Parent comment {parent_comment_id} not found")

            comment = Comment(
                element_id=element_id,
                element_type=element_type,
                expert_id=expert_id,
                content=content,
                parent_comment_id=parent_comment_id
            )
            self._comments[comment.comment_id] = comment

            # Update metrics
            await self._update_contribution_count(expert_id, ContributionType.COMMENT)

            return comment

    async def suggest_entity(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        suggested_name: str,
        suggested_description: str,
        suggested_attributes: List[Dict[str, Any]],
        rationale: str,
        entity_type_id: Optional[UUID] = None
    ) -> EntitySuggestion:
        """Suggest a new or modified entity.

        Args:
            expert_id: Expert making suggestion
            ontology_id: Ontology ID
            suggested_name: Suggested entity name
            suggested_description: Suggested description
            suggested_attributes: List of suggested attributes
            rationale: Reason for suggestion
            entity_type_id: Existing entity ID if modifying

        Returns:
            Created entity suggestion
        """
        async with self._lock:
            suggestion = EntitySuggestion(
                expert_id=expert_id,
                ontology_id=ontology_id,
                entity_type_id=entity_type_id,
                suggested_name=suggested_name,
                suggested_description=suggested_description,
                suggested_attributes=suggested_attributes,
                rationale=rationale
            )
            self._entity_suggestions[suggestion.suggestion_id] = suggestion

            # Update metrics
            await self._update_contribution_count(expert_id, ContributionType.ENTITY_SUGGESTION)

            return suggestion

    async def suggest_relation(
        self,
        expert_id: UUID,
        ontology_id: UUID,
        suggested_name: str,
        suggested_description: str,
        source_entity_type: str,
        target_entity_type: str,
        cardinality: str,
        rationale: str,
        relation_type_id: Optional[UUID] = None
    ) -> RelationSuggestion:
        """Suggest a new or modified relation.

        Args:
            expert_id: Expert making suggestion
            ontology_id: Ontology ID
            suggested_name: Suggested relation name
            suggested_description: Suggested description
            source_entity_type: Source entity type
            target_entity_type: Target entity type
            cardinality: Relation cardinality
            rationale: Reason for suggestion
            relation_type_id: Existing relation ID if modifying

        Returns:
            Created relation suggestion
        """
        async with self._lock:
            suggestion = RelationSuggestion(
                expert_id=expert_id,
                ontology_id=ontology_id,
                relation_type_id=relation_type_id,
                suggested_name=suggested_name,
                suggested_description=suggested_description,
                source_entity_type=source_entity_type,
                target_entity_type=target_entity_type,
                cardinality=cardinality,
                rationale=rationale
            )
            self._relation_suggestions[suggestion.suggestion_id] = suggestion

            # Update metrics
            await self._update_contribution_count(expert_id, ContributionType.RELATION_SUGGESTION)

            return suggestion

    async def attach_document(
        self,
        element_id: UUID,
        element_type: str,
        expert_id: UUID,
        document_type: DocumentType,
        title: str,
        description: str,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size_bytes: int = 0,
        mime_type: str = ""
    ) -> DocumentAttachment:
        """Attach a document to an ontology element.

        Args:
            element_id: Element to attach to
            element_type: Type of element
            expert_id: Expert attaching document
            document_type: Type of document
            title: Document title
            description: Document description
            url: Document URL (for links or uploaded files)
            file_path: Local file path
            file_size_bytes: File size
            mime_type: MIME type

        Returns:
            Created document attachment
        """
        async with self._lock:
            # Validate document type requirements
            if document_type == DocumentType.LINK and not url:
                raise ValueError("URL required for link attachments")
            if document_type in [DocumentType.PDF, DocumentType.IMAGE, DocumentType.WORD, DocumentType.EXCEL]:
                if not file_path and not url:
                    raise ValueError("File path or URL required for file attachments")

            attachment = DocumentAttachment(
                element_id=element_id,
                element_type=element_type,
                expert_id=expert_id,
                document_type=document_type,
                title=title,
                description=description,
                url=url,
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                mime_type=mime_type
            )
            self._attachments[attachment.attachment_id] = attachment

            # Update metrics
            await self._update_contribution_count(expert_id, ContributionType.DOCUMENT_ATTACHMENT)

            return attachment

    async def accept_contribution(
        self,
        contribution_type: ContributionType,
        contribution_id: UUID,
        reviewer_id: UUID,
        review_notes: str = "",
        quality_score: float = 5.0
    ) -> None:
        """Accept a contribution.

        Args:
            contribution_type: Type of contribution
            contribution_id: Contribution ID
            reviewer_id: Reviewer ID
            review_notes: Review notes
            quality_score: Quality score (1.0-5.0)
        """
        async with self._lock:
            expert_id = None

            if contribution_type == ContributionType.ENTITY_SUGGESTION:
                if contribution_id not in self._entity_suggestions:
                    raise ValueError(f"Entity suggestion {contribution_id} not found")
                suggestion = self._entity_suggestions[contribution_id]
                suggestion.status = ContributionStatus.ACCEPTED
                suggestion.reviewed_by = reviewer_id
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.review_notes = review_notes
                expert_id = suggestion.expert_id

            elif contribution_type == ContributionType.RELATION_SUGGESTION:
                if contribution_id not in self._relation_suggestions:
                    raise ValueError(f"Relation suggestion {contribution_id} not found")
                suggestion = self._relation_suggestions[contribution_id]
                suggestion.status = ContributionStatus.ACCEPTED
                suggestion.reviewed_by = reviewer_id
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.review_notes = review_notes
                expert_id = suggestion.expert_id

            # Update expert metrics
            if expert_id:
                await self._update_metrics_on_acceptance(expert_id, quality_score)

    async def reject_contribution(
        self,
        contribution_type: ContributionType,
        contribution_id: UUID,
        reviewer_id: UUID,
        review_notes: str
    ) -> None:
        """Reject a contribution.

        Args:
            contribution_type: Type of contribution
            contribution_id: Contribution ID
            reviewer_id: Reviewer ID
            review_notes: Reason for rejection
        """
        async with self._lock:
            expert_id = None

            if contribution_type == ContributionType.ENTITY_SUGGESTION:
                if contribution_id not in self._entity_suggestions:
                    raise ValueError(f"Entity suggestion {contribution_id} not found")
                suggestion = self._entity_suggestions[contribution_id]
                suggestion.status = ContributionStatus.REJECTED
                suggestion.reviewed_by = reviewer_id
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.review_notes = review_notes
                expert_id = suggestion.expert_id

            elif contribution_type == ContributionType.RELATION_SUGGESTION:
                if contribution_id not in self._relation_suggestions:
                    raise ValueError(f"Relation suggestion {contribution_id} not found")
                suggestion = self._relation_suggestions[contribution_id]
                suggestion.status = ContributionStatus.REJECTED
                suggestion.reviewed_by = reviewer_id
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.review_notes = review_notes
                expert_id = suggestion.expert_id

            # Update expert metrics
            if expert_id:
                await self._update_metrics_on_rejection(expert_id)

    async def get_comments(
        self,
        element_id: UUID,
        include_resolved: bool = False
    ) -> List[Comment]:
        """Get comments for an element.

        Args:
            element_id: Element ID
            include_resolved: Include resolved comments

        Returns:
            List of comments
        """
        async with self._lock:
            comments = [
                c for c in self._comments.values()
                if c.element_id == element_id and (include_resolved or not c.is_resolved)
            ]
            return sorted(comments, key=lambda c: c.created_at)

    async def get_threaded_comments(
        self,
        element_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get comments organized by thread.

        Args:
            element_id: Element ID

        Returns:
            List of comment threads
        """
        async with self._lock:
            comments = await self.get_comments(element_id, include_resolved=True)

            # Build comment hierarchy
            comment_map = {c.comment_id: c for c in comments}
            threads = []

            for comment in comments:
                if comment.parent_comment_id is None:
                    # Root comment - build thread
                    thread = self._build_thread(comment, comment_map)
                    threads.append(thread)

            return threads

    def _build_thread(
        self,
        comment: Comment,
        comment_map: Dict[UUID, Comment]
    ) -> Dict[str, Any]:
        """Build a comment thread recursively.

        Args:
            comment: Root comment
            comment_map: Map of comment IDs to comments

        Returns:
            Thread dictionary
        """
        thread = {
            "comment_id": comment.comment_id,
            "content": comment.content,
            "expert_id": comment.expert_id,
            "created_at": comment.created_at,
            "is_resolved": comment.is_resolved,
            "replies": []
        }

        # Find replies
        for candidate in comment_map.values():
            if candidate.parent_comment_id == comment.comment_id:
                reply_thread = self._build_thread(candidate, comment_map)
                thread["replies"].append(reply_thread)

        return thread

    async def get_entity_suggestions(
        self,
        ontology_id: UUID,
        status: Optional[ContributionStatus] = None
    ) -> List[EntitySuggestion]:
        """Get entity suggestions for an ontology.

        Args:
            ontology_id: Ontology ID
            status: Filter by status

        Returns:
            List of entity suggestions
        """
        async with self._lock:
            suggestions = [
                s for s in self._entity_suggestions.values()
                if s.ontology_id == ontology_id and (status is None or s.status == status)
            ]
            return sorted(suggestions, key=lambda s: s.created_at, reverse=True)

    async def get_relation_suggestions(
        self,
        ontology_id: UUID,
        status: Optional[ContributionStatus] = None
    ) -> List[RelationSuggestion]:
        """Get relation suggestions for an ontology.

        Args:
            ontology_id: Ontology ID
            status: Filter by status

        Returns:
            List of relation suggestions
        """
        async with self._lock:
            suggestions = [
                s for s in self._relation_suggestions.values()
                if s.ontology_id == ontology_id and (status is None or s.status == status)
            ]
            return sorted(suggestions, key=lambda s: s.created_at, reverse=True)

    async def get_attachments(
        self,
        element_id: UUID
    ) -> List[DocumentAttachment]:
        """Get attachments for an element.

        Args:
            element_id: Element ID

        Returns:
            List of attachments
        """
        async with self._lock:
            attachments = [
                a for a in self._attachments.values()
                if a.element_id == element_id
            ]
            return sorted(attachments, key=lambda a: a.created_at, reverse=True)

    async def get_expert_metrics(
        self,
        expert_id: UUID
    ) -> ContributionMetrics:
        """Get contribution metrics for an expert.

        Args:
            expert_id: Expert ID

        Returns:
            Contribution metrics
        """
        async with self._lock:
            if expert_id not in self._metrics:
                self._metrics[expert_id] = ContributionMetrics(expert_id=expert_id)
            return self._metrics[expert_id]

    async def resolve_comment(
        self,
        comment_id: UUID,
        resolved_by: UUID
    ) -> None:
        """Mark a comment as resolved.

        Args:
            comment_id: Comment ID
            resolved_by: User resolving the comment
        """
        async with self._lock:
            if comment_id not in self._comments:
                raise ValueError(f"Comment {comment_id} not found")

            comment = self._comments[comment_id]
            comment.is_resolved = True
            comment.resolved_by = resolved_by
            comment.resolved_at = datetime.utcnow()

    async def _update_contribution_count(
        self,
        expert_id: UUID,
        contribution_type: ContributionType
    ) -> None:
        """Update contribution count for an expert.

        Args:
            expert_id: Expert ID
            contribution_type: Type of contribution
        """
        if expert_id not in self._metrics:
            self._metrics[expert_id] = ContributionMetrics(expert_id=expert_id)

        metrics = self._metrics[expert_id]
        metrics.total_contributions += 1
        metrics.last_contribution_at = datetime.utcnow()

        if contribution_type == ContributionType.COMMENT:
            metrics.comments_count += 1
        elif contribution_type == ContributionType.ENTITY_SUGGESTION:
            metrics.entity_suggestions_count += 1
            metrics.pending_contributions += 1
        elif contribution_type == ContributionType.RELATION_SUGGESTION:
            metrics.relation_suggestions_count += 1
            metrics.pending_contributions += 1
        elif contribution_type == ContributionType.DOCUMENT_ATTACHMENT:
            metrics.document_attachments_count += 1

        metrics.updated_at = datetime.utcnow()

    async def _update_metrics_on_acceptance(
        self,
        expert_id: UUID,
        quality_score: float
    ) -> None:
        """Update metrics when contribution is accepted.

        Args:
            expert_id: Expert ID
            quality_score: Quality score from review
        """
        if expert_id not in self._metrics:
            self._metrics[expert_id] = ContributionMetrics(expert_id=expert_id)

        metrics = self._metrics[expert_id]
        metrics.accepted_contributions += 1
        metrics.pending_contributions = max(0, metrics.pending_contributions - 1)

        # Update acceptance rate
        total_reviewed = metrics.accepted_contributions + metrics.rejected_contributions
        if total_reviewed > 0:
            metrics.acceptance_rate = metrics.accepted_contributions / total_reviewed

        # Update average quality score (EMA with alpha=0.3)
        if metrics.average_quality_score == 0:
            metrics.average_quality_score = quality_score
        else:
            alpha = 0.3
            metrics.average_quality_score = (
                alpha * quality_score + (1 - alpha) * metrics.average_quality_score
            )

        # Update overall contribution score
        metrics.contribution_score = (
            self._quality_score_weight * metrics.average_quality_score +
            self._acceptance_rate_weight * metrics.acceptance_rate * 5.0
        )

        metrics.updated_at = datetime.utcnow()

    async def _update_metrics_on_rejection(
        self,
        expert_id: UUID
    ) -> None:
        """Update metrics when contribution is rejected.

        Args:
            expert_id: Expert ID
        """
        if expert_id not in self._metrics:
            self._metrics[expert_id] = ContributionMetrics(expert_id=expert_id)

        metrics = self._metrics[expert_id]
        metrics.rejected_contributions += 1
        metrics.pending_contributions = max(0, metrics.pending_contributions - 1)

        # Update acceptance rate
        total_reviewed = metrics.accepted_contributions + metrics.rejected_contributions
        if total_reviewed > 0:
            metrics.acceptance_rate = metrics.accepted_contributions / total_reviewed

        # Update overall contribution score
        metrics.contribution_score = (
            self._quality_score_weight * metrics.average_quality_score +
            self._acceptance_rate_weight * metrics.acceptance_rate * 5.0
        )

        metrics.updated_at = datetime.utcnow()

    async def get_expert_contributions(
        self,
        expert_id: UUID,
        contribution_type: Optional[ContributionType] = None
    ) -> Dict[str, List[Any]]:
        """Get all contributions by an expert.

        Args:
            expert_id: Expert ID
            contribution_type: Filter by contribution type

        Returns:
            Dictionary of contributions by type
        """
        async with self._lock:
            contributions = {
                "comments": [],
                "entity_suggestions": [],
                "relation_suggestions": [],
                "attachments": []
            }

            if contribution_type is None or contribution_type == ContributionType.COMMENT:
                contributions["comments"] = [
                    c for c in self._comments.values()
                    if c.expert_id == expert_id
                ]

            if contribution_type is None or contribution_type == ContributionType.ENTITY_SUGGESTION:
                contributions["entity_suggestions"] = [
                    s for s in self._entity_suggestions.values()
                    if s.expert_id == expert_id
                ]

            if contribution_type is None or contribution_type == ContributionType.RELATION_SUGGESTION:
                contributions["relation_suggestions"] = [
                    s for s in self._relation_suggestions.values()
                    if s.expert_id == expert_id
                ]

            if contribution_type is None or contribution_type == ContributionType.DOCUMENT_ATTACHMENT:
                contributions["attachments"] = [
                    a for a in self._attachments.values()
                    if a.expert_id == expert_id
                ]

            return contributions
