"""
Text-to-SQL Quality Assessment Module.

Provides quality assessment capabilities:
- Ragas framework integration for semantic quality
- User feedback collection
- Training data export for LLM fine-tuning

Implements Task 15 from text-to-sql-methods specification.
"""

import asyncio
import hashlib
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class FeedbackRating(str, Enum):
    """User feedback rating."""
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"


class QualityDimension(str, Enum):
    """Quality assessment dimension."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    EXECUTION = "execution"
    RELEVANCE = "relevance"
    FAITHFULNESS = "faithfulness"


class ExportFormat(str, Enum):
    """Training data export format."""
    JSONL = "jsonl"
    CSV = "csv"
    PARQUET = "parquet"


# Default quality thresholds
DEFAULT_SYNTAX_THRESHOLD = 0.95
DEFAULT_SEMANTIC_THRESHOLD = 0.85
DEFAULT_RELEVANCE_THRESHOLD = 0.80


# =============================================================================
# Data Models
# =============================================================================

class QualityScore(BaseModel):
    """Quality score for a single dimension."""
    dimension: QualityDimension
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


class QualityAssessment(BaseModel):
    """Complete quality assessment for generated SQL."""
    id: UUID = Field(default_factory=uuid4)
    query: str
    generated_sql: str
    expected_sql: Optional[str] = None
    database_type: str
    method_used: str

    # Quality scores
    scores: List[QualityScore] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)

    # Metadata
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def get_score(self, dimension: QualityDimension) -> Optional[float]:
        """Get score for a specific dimension."""
        for score in self.scores:
            if score.dimension == dimension:
                return score.score
        return None


class UserFeedback(BaseModel):
    """User feedback for generated SQL."""
    id: UUID = Field(default_factory=uuid4)
    query: str
    generated_sql: str
    corrected_sql: Optional[str] = None
    rating: FeedbackRating
    comment: Optional[str] = None
    database_type: str
    method_used: str

    # Metadata
    user_id: str
    tenant_id: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    # Tags for categorization
    tags: List[str] = Field(default_factory=list)


class TrainingExample(BaseModel):
    """Training example for LLM fine-tuning."""
    id: UUID = Field(default_factory=uuid4)
    query: str
    sql: str
    database_type: str
    method_used: str
    quality_score: float = Field(ge=0.0, le=1.0)

    # Source information
    source: str = "generated"  # generated, user_corrected, manual
    feedback_id: Optional[UUID] = None
    assessment_id: Optional[UUID] = None

    # Schema context
    schema_context: Optional[str] = None
    table_names: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QualityConfig(BaseModel):
    """Configuration for quality assessment service."""
    syntax_threshold: float = DEFAULT_SYNTAX_THRESHOLD
    semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD
    min_quality_for_training: float = 0.8
    max_feedback_logs: int = 10000
    max_assessment_logs: int = 10000


class FeedbackStatistics(BaseModel):
    """Statistics for user feedback."""
    total_feedback: int = 0
    correct_count: int = 0
    partially_correct_count: int = 0
    incorrect_count: int = 0
    feedback_rate: float = 0.0  # Percentage of queries with feedback
    average_correction_distance: float = 0.0  # Edit distance for corrections


# =============================================================================
# Ragas-style Quality Assessor
# =============================================================================

class RagasQualityAssessor:
    """
    Ragas-style quality assessor for Text-to-SQL.

    Evaluates generated SQL quality across multiple dimensions:
    - Syntax correctness
    - Semantic faithfulness (matches query intent)
    - Relevance (uses appropriate tables/columns)

    Note: This is a simplified implementation. For production,
    integrate with the actual Ragas framework.
    """

    def __init__(
        self,
        llm_evaluator: Optional[Callable] = None,
        syntax_validator: Optional[Callable] = None,
    ):
        """
        Initialize Ragas-style assessor.

        Args:
            llm_evaluator: Optional LLM function for semantic evaluation
            syntax_validator: Optional SQL syntax validator
        """
        self._llm_evaluator = llm_evaluator
        self._syntax_validator = syntax_validator

    async def assess(
        self,
        query: str,
        generated_sql: str,
        expected_sql: Optional[str] = None,
        schema_context: Optional[str] = None,
        database_type: str = "postgresql",
    ) -> QualityAssessment:
        """
        Assess quality of generated SQL.

        Args:
            query: Original natural language query
            generated_sql: Generated SQL statement
            expected_sql: Optional expected/ground truth SQL
            schema_context: Optional database schema context
            database_type: Target database type

        Returns:
            Quality assessment with scores
        """
        scores: List[QualityScore] = []

        # 1. Syntax assessment
        syntax_score = await self._assess_syntax(generated_sql, database_type)
        scores.append(syntax_score)

        # 2. Semantic faithfulness assessment
        faithfulness_score = await self._assess_faithfulness(
            query, generated_sql, expected_sql
        )
        scores.append(faithfulness_score)

        # 3. Relevance assessment
        relevance_score = await self._assess_relevance(
            query, generated_sql, schema_context
        )
        scores.append(relevance_score)

        # Calculate overall score (weighted average)
        overall = self._calculate_overall_score(scores)

        return QualityAssessment(
            query=query,
            generated_sql=generated_sql,
            expected_sql=expected_sql,
            database_type=database_type,
            method_used="unknown",
            scores=scores,
            overall_score=overall,
        )

    async def _assess_syntax(
        self,
        sql: str,
        database_type: str,
    ) -> QualityScore:
        """Assess SQL syntax correctness."""
        score = 1.0
        details: Dict[str, Any] = {"valid": True, "errors": []}

        if self._syntax_validator:
            try:
                result = await self._syntax_validator(sql, database_type)
                if not result.get("valid", True):
                    score = 0.0
                    details["valid"] = False
                    details["errors"] = result.get("errors", [])
            except Exception as e:
                logger.warning(f"Syntax validation error: {e}")
                score = 0.5
                details["error"] = str(e)
        else:
            # Basic syntax checks
            sql_upper = sql.upper().strip()

            # Check for common SQL keywords
            valid_starts = ["SELECT", "INSERT", "UPDATE", "DELETE", "WITH"]
            if not any(sql_upper.startswith(s) for s in valid_starts):
                score = 0.0
                details["valid"] = False
                details["errors"].append("Invalid SQL statement start")

            # Check for balanced parentheses
            if sql.count("(") != sql.count(")"):
                score = max(0.0, score - 0.5)
                details["errors"].append("Unbalanced parentheses")

            # Check for semicolon (optional but good)
            if not sql.strip().endswith(";"):
                score = max(0.0, score - 0.1)
                details["warnings"] = ["Missing trailing semicolon"]

        return QualityScore(
            dimension=QualityDimension.SYNTAX,
            score=score,
            confidence=0.9,
            details=details,
        )

    async def _assess_faithfulness(
        self,
        query: str,
        generated_sql: str,
        expected_sql: Optional[str],
    ) -> QualityScore:
        """Assess semantic faithfulness to the original query."""
        score = 0.5  # Default middle score
        details: Dict[str, Any] = {}

        if expected_sql:
            # Compare with expected SQL
            similarity = self._calculate_sql_similarity(generated_sql, expected_sql)
            score = similarity
            details["expected_similarity"] = similarity

        if self._llm_evaluator:
            try:
                # Use LLM to evaluate faithfulness
                eval_result = await self._llm_evaluator(
                    query=query,
                    sql=generated_sql,
                    dimension="faithfulness",
                )
                score = eval_result.get("score", score)
                details["llm_evaluation"] = eval_result
            except Exception as e:
                logger.warning(f"LLM evaluation error: {e}")
        else:
            # Heuristic faithfulness check
            query_lower = query.lower()
            sql_lower = generated_sql.lower()

            # Check if query keywords appear in SQL
            keywords = self._extract_keywords(query_lower)
            found_keywords = sum(1 for kw in keywords if kw in sql_lower)

            if keywords:
                keyword_score = found_keywords / len(keywords)
                score = (score + keyword_score) / 2
                details["keyword_match"] = keyword_score
                details["keywords_found"] = found_keywords
                details["keywords_total"] = len(keywords)

        return QualityScore(
            dimension=QualityDimension.FAITHFULNESS,
            score=score,
            confidence=0.7 if not self._llm_evaluator else 0.85,
            details=details,
        )

    async def _assess_relevance(
        self,
        query: str,
        generated_sql: str,
        schema_context: Optional[str],
    ) -> QualityScore:
        """Assess relevance of generated SQL to schema."""
        score = 0.7  # Default reasonable score
        details: Dict[str, Any] = {}

        # Extract table names from SQL
        tables = self._extract_tables(generated_sql)
        details["tables_used"] = tables

        if schema_context:
            # Check if tables exist in schema
            schema_lower = schema_context.lower()
            valid_tables = sum(1 for t in tables if t.lower() in schema_lower)

            if tables:
                table_score = valid_tables / len(tables)
                score = table_score
                details["valid_tables"] = valid_tables
                details["schema_match"] = table_score

        if self._llm_evaluator:
            try:
                eval_result = await self._llm_evaluator(
                    query=query,
                    sql=generated_sql,
                    dimension="relevance",
                    schema=schema_context,
                )
                score = eval_result.get("score", score)
                details["llm_evaluation"] = eval_result
            except Exception as e:
                logger.warning(f"LLM relevance evaluation error: {e}")

        return QualityScore(
            dimension=QualityDimension.RELEVANCE,
            score=score,
            confidence=0.75,
            details=details,
        )

    def _calculate_overall_score(self, scores: List[QualityScore]) -> float:
        """Calculate weighted overall score."""
        if not scores:
            return 0.0

        # Weights for each dimension
        weights = {
            QualityDimension.SYNTAX: 0.3,
            QualityDimension.FAITHFULNESS: 0.4,
            QualityDimension.RELEVANCE: 0.3,
            QualityDimension.SEMANTIC: 0.4,
            QualityDimension.EXECUTION: 0.3,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for score in scores:
            weight = weights.get(score.dimension, 0.25)
            weighted_sum += score.score * weight * score.confidence
            total_weight += weight * score.confidence

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _calculate_sql_similarity(self, sql1: str, sql2: str) -> float:
        """Calculate similarity between two SQL statements."""
        # Normalize SQL
        def normalize(sql: str) -> str:
            sql = sql.lower().strip()
            sql = " ".join(sql.split())  # Normalize whitespace
            return sql

        norm1 = normalize(sql1)
        norm2 = normalize(sql2)

        if norm1 == norm2:
            return 1.0

        # Token-based similarity
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query."""
        # Remove common words
        stop_words = {
            "show", "me", "all", "the", "a", "an", "of", "from", "in",
            "to", "for", "with", "and", "or", "that", "which", "where",
            "what", "how", "many", "much", "find", "get", "list", "give",
        }

        words = query.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        import re

        # Simple regex to extract table names after FROM and JOIN
        patterns = [
            r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]

        tables = []
        sql_upper = sql.upper()

        for pattern in patterns:
            matches = re.findall(pattern, sql_upper)
            tables.extend(matches)

        return list(set(tables))


# =============================================================================
# Quality Assessment Service
# =============================================================================

class QualityAssessmentService:
    """
    Quality Assessment Service for Text-to-SQL.

    Features:
    - Ragas-style quality assessment
    - User feedback collection and analysis
    - Training data export for LLM fine-tuning
    """

    def __init__(
        self,
        config: Optional[QualityConfig] = None,
        ragas_assessor: Optional[RagasQualityAssessor] = None,
    ):
        """
        Initialize quality assessment service.

        Args:
            config: Quality configuration
            ragas_assessor: Optional custom Ragas assessor
        """
        self._config = config or QualityConfig()
        self._assessor = ragas_assessor or RagasQualityAssessor()
        self._lock = asyncio.Lock()

        # Storage
        self._assessments: Deque[QualityAssessment] = deque(
            maxlen=self._config.max_assessment_logs
        )
        self._feedback: Deque[UserFeedback] = deque(
            maxlen=self._config.max_feedback_logs
        )
        self._training_data: Dict[UUID, TrainingExample] = {}

        logger.info("QualityAssessmentService initialized")

    # =========================================================================
    # Quality Assessment (Ragas Integration)
    # =========================================================================

    async def assess_quality(
        self,
        query: str,
        generated_sql: str,
        expected_sql: Optional[str] = None,
        schema_context: Optional[str] = None,
        database_type: str = "postgresql",
        method_used: str = "unknown",
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> QualityAssessment:
        """
        Assess quality of generated SQL using Ragas-style evaluation.

        Args:
            query: Original natural language query
            generated_sql: Generated SQL statement
            expected_sql: Optional expected/ground truth SQL
            schema_context: Optional database schema context
            database_type: Target database type
            method_used: Generation method used
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            correlation_id: Optional correlation ID

        Returns:
            Quality assessment with scores
        """
        assessment = await self._assessor.assess(
            query=query,
            generated_sql=generated_sql,
            expected_sql=expected_sql,
            schema_context=schema_context,
            database_type=database_type,
        )

        # Add metadata
        assessment.method_used = method_used
        assessment.user_id = user_id
        assessment.tenant_id = tenant_id
        assessment.correlation_id = correlation_id

        # Store assessment
        async with self._lock:
            self._assessments.append(assessment)

            # Auto-generate training data if quality is high enough
            if assessment.overall_score >= self._config.min_quality_for_training:
                await self._create_training_example_from_assessment(assessment)

        logger.debug(
            f"Quality assessment completed: {assessment.id} "
            f"(score={assessment.overall_score:.2f})"
        )

        return assessment

    async def get_assessment(self, assessment_id: UUID) -> Optional[QualityAssessment]:
        """Get assessment by ID."""
        for assessment in self._assessments:
            if assessment.id == assessment_id:
                return assessment
        return None

    async def get_assessments(
        self,
        limit: int = 100,
        min_score: Optional[float] = None,
        method: Optional[str] = None,
    ) -> List[QualityAssessment]:
        """
        Get assessments with optional filtering.

        Args:
            limit: Maximum number of assessments
            min_score: Filter by minimum overall score
            method: Filter by generation method

        Returns:
            List of assessments
        """
        assessments = list(self._assessments)

        if min_score is not None:
            assessments = [a for a in assessments if a.overall_score >= min_score]

        if method:
            assessments = [a for a in assessments if a.method_used == method]

        # Sort by timestamp (most recent first)
        assessments.sort(key=lambda x: x.assessed_at, reverse=True)

        return assessments[:limit]

    # =========================================================================
    # User Feedback Collection
    # =========================================================================

    async def submit_feedback(
        self,
        query: str,
        generated_sql: str,
        rating: FeedbackRating,
        user_id: str,
        corrected_sql: Optional[str] = None,
        comment: Optional[str] = None,
        database_type: str = "postgresql",
        method_used: str = "unknown",
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> UserFeedback:
        """
        Submit user feedback for generated SQL.

        Args:
            query: Original natural language query
            generated_sql: Generated SQL statement
            rating: User rating (correct, partially_correct, incorrect)
            user_id: User identifier
            corrected_sql: Optional user-corrected SQL
            comment: Optional user comment
            database_type: Target database type
            method_used: Generation method used
            tenant_id: Optional tenant identifier
            correlation_id: Optional correlation ID
            tags: Optional tags for categorization

        Returns:
            Created feedback record
        """
        feedback = UserFeedback(
            query=query,
            generated_sql=generated_sql,
            corrected_sql=corrected_sql,
            rating=rating,
            comment=comment,
            database_type=database_type,
            method_used=method_used,
            user_id=user_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            tags=tags or [],
        )

        async with self._lock:
            self._feedback.append(feedback)

            # Create training example from corrected SQL
            if corrected_sql and rating != FeedbackRating.INCORRECT:
                await self._create_training_example_from_feedback(feedback)

        logger.info(f"Feedback submitted: {feedback.id} (rating={rating.value})")

        return feedback

    async def get_feedback(
        self,
        limit: int = 100,
        rating: Optional[FeedbackRating] = None,
        user_id: Optional[str] = None,
    ) -> List[UserFeedback]:
        """
        Get feedback with optional filtering.

        Args:
            limit: Maximum number of feedback records
            rating: Filter by rating
            user_id: Filter by user

        Returns:
            List of feedback records
        """
        feedback_list = list(self._feedback)

        if rating:
            feedback_list = [f for f in feedback_list if f.rating == rating]

        if user_id:
            feedback_list = [f for f in feedback_list if f.user_id == user_id]

        # Sort by timestamp (most recent first)
        feedback_list.sort(key=lambda x: x.submitted_at, reverse=True)

        return feedback_list[:limit]

    async def get_feedback_statistics(self) -> FeedbackStatistics:
        """Get feedback statistics."""
        feedback_list = list(self._feedback)

        if not feedback_list:
            return FeedbackStatistics()

        correct_count = sum(1 for f in feedback_list if f.rating == FeedbackRating.CORRECT)
        partial_count = sum(1 for f in feedback_list if f.rating == FeedbackRating.PARTIALLY_CORRECT)
        incorrect_count = sum(1 for f in feedback_list if f.rating == FeedbackRating.INCORRECT)

        return FeedbackStatistics(
            total_feedback=len(feedback_list),
            correct_count=correct_count,
            partially_correct_count=partial_count,
            incorrect_count=incorrect_count,
            feedback_rate=0.0,  # Would need total requests to calculate
        )

    # =========================================================================
    # Training Data Export
    # =========================================================================

    async def _create_training_example_from_assessment(
        self,
        assessment: QualityAssessment,
    ) -> TrainingExample:
        """Create training example from high-quality assessment."""
        example = TrainingExample(
            query=assessment.query,
            sql=assessment.generated_sql,
            database_type=assessment.database_type,
            method_used=assessment.method_used,
            quality_score=assessment.overall_score,
            source="generated",
            assessment_id=assessment.id,
        )

        self._training_data[example.id] = example
        return example

    async def _create_training_example_from_feedback(
        self,
        feedback: UserFeedback,
    ) -> TrainingExample:
        """Create training example from user-corrected feedback."""
        sql = feedback.corrected_sql or feedback.generated_sql
        quality_score = 1.0 if feedback.rating == FeedbackRating.CORRECT else 0.8

        example = TrainingExample(
            query=feedback.query,
            sql=sql,
            database_type=feedback.database_type,
            method_used=feedback.method_used,
            quality_score=quality_score,
            source="user_corrected" if feedback.corrected_sql else "user_validated",
            feedback_id=feedback.id,
        )

        self._training_data[example.id] = example
        return example

    async def export_training_data(
        self,
        format: ExportFormat = ExportFormat.JSONL,
        min_quality_score: float = 0.8,
        database_type: Optional[str] = None,
        include_metadata: bool = True,
    ) -> str:
        """
        Export training data for LLM fine-tuning.

        Args:
            format: Export format (jsonl, csv, parquet)
            min_quality_score: Minimum quality score filter
            database_type: Filter by database type
            include_metadata: Include metadata in export

        Returns:
            Exported data as string (for JSONL/CSV)
        """
        # Filter training data
        examples = [
            ex for ex in self._training_data.values()
            if ex.quality_score >= min_quality_score
        ]

        if database_type:
            examples = [ex for ex in examples if ex.database_type == database_type]

        # Sort by quality score (highest first)
        examples.sort(key=lambda x: x.quality_score, reverse=True)

        if format == ExportFormat.JSONL:
            return self._export_jsonl(examples, include_metadata)
        elif format == ExportFormat.CSV:
            return self._export_csv(examples, include_metadata)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_jsonl(
        self,
        examples: List[TrainingExample],
        include_metadata: bool,
    ) -> str:
        """Export to JSONL format."""
        lines = []

        for ex in examples:
            record = {
                "query": ex.query,
                "sql": ex.sql,
                "database_type": ex.database_type,
            }

            if include_metadata:
                record.update({
                    "method_used": ex.method_used,
                    "quality_score": ex.quality_score,
                    "source": ex.source,
                    "created_at": ex.created_at.isoformat(),
                })

            lines.append(json.dumps(record, ensure_ascii=False))

        return "\n".join(lines)

    def _export_csv(
        self,
        examples: List[TrainingExample],
        include_metadata: bool,
    ) -> str:
        """Export to CSV format."""
        if include_metadata:
            header = "query,sql,database_type,method_used,quality_score,source"
        else:
            header = "query,sql,database_type"

        lines = [header]

        for ex in examples:
            # Escape CSV fields
            query = ex.query.replace('"', '""')
            sql = ex.sql.replace('"', '""')

            if include_metadata:
                line = f'"{query}","{sql}",{ex.database_type},{ex.method_used},{ex.quality_score},{ex.source}'
            else:
                line = f'"{query}","{sql}",{ex.database_type}'

            lines.append(line)

        return "\n".join(lines)

    async def get_training_data_statistics(self) -> Dict[str, Any]:
        """Get training data statistics."""
        examples = list(self._training_data.values())

        if not examples:
            return {
                "total_examples": 0,
                "by_source": {},
                "by_database_type": {},
                "average_quality_score": 0.0,
            }

        by_source: Dict[str, int] = {}
        by_db_type: Dict[str, int] = {}
        total_quality = 0.0

        for ex in examples:
            by_source[ex.source] = by_source.get(ex.source, 0) + 1
            by_db_type[ex.database_type] = by_db_type.get(ex.database_type, 0) + 1
            total_quality += ex.quality_score

        return {
            "total_examples": len(examples),
            "by_source": by_source,
            "by_database_type": by_db_type,
            "average_quality_score": total_quality / len(examples),
        }

    # =========================================================================
    # Reports
    # =========================================================================

    async def generate_quality_report(
        self,
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive quality report.

        Args:
            period_days: Number of days to include

        Returns:
            Quality report dictionary
        """
        cutoff = datetime.utcnow() - timedelta(days=period_days)

        # Filter recent assessments
        assessments = [
            a for a in self._assessments
            if a.assessed_at >= cutoff
        ]

        # Filter recent feedback
        feedback = [
            f for f in self._feedback
            if f.submitted_at >= cutoff
        ]

        # Calculate statistics
        if assessments:
            avg_overall = sum(a.overall_score for a in assessments) / len(assessments)
            avg_syntax = sum(
                a.get_score(QualityDimension.SYNTAX) or 0
                for a in assessments
            ) / len(assessments)
            avg_faithfulness = sum(
                a.get_score(QualityDimension.FAITHFULNESS) or 0
                for a in assessments
            ) / len(assessments)
            avg_relevance = sum(
                a.get_score(QualityDimension.RELEVANCE) or 0
                for a in assessments
            ) / len(assessments)
        else:
            avg_overall = avg_syntax = avg_faithfulness = avg_relevance = 0.0

        # Method breakdown
        method_stats: Dict[str, Dict[str, Any]] = {}
        for a in assessments:
            if a.method_used not in method_stats:
                method_stats[a.method_used] = {
                    "count": 0,
                    "total_score": 0.0,
                }
            method_stats[a.method_used]["count"] += 1
            method_stats[a.method_used]["total_score"] += a.overall_score

        for method, stats in method_stats.items():
            stats["average_score"] = stats["total_score"] / stats["count"]

        # Feedback breakdown
        feedback_stats = await self.get_feedback_statistics()

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period_days": period_days,
            "assessments": {
                "total": len(assessments),
                "average_overall_score": avg_overall,
                "average_syntax_score": avg_syntax,
                "average_faithfulness_score": avg_faithfulness,
                "average_relevance_score": avg_relevance,
                "by_method": method_stats,
            },
            "feedback": {
                "total": feedback_stats.total_feedback,
                "correct_count": feedback_stats.correct_count,
                "partially_correct_count": feedback_stats.partially_correct_count,
                "incorrect_count": feedback_stats.incorrect_count,
            },
            "training_data": await self.get_training_data_statistics(),
        }
