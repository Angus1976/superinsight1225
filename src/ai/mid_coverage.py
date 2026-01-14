"""
Mid-Coverage Engine for SuperInsight platform.

Implements pattern analysis and auto-coverage based on human annotation samples,
with similarity matching and notification for review.
"""

import asyncio
import time
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from uuid import uuid4
from collections import defaultdict

from src.ai.annotation_schemas import (
    AnnotationType,
    AnnotationTask,
    AnnotatedSample,
    AnnotationPattern,
    SimilarTaskMatch,
    CoverageConfig,
    CoverageResult,
    CoverageBatchResult,
)

logger = logging.getLogger(__name__)


class MidCoverageEngine:
    """
    Mid-coverage engine for auto-annotation based on human samples.
    
    Features:
    - Pattern analysis from annotated samples
    - Similarity-based task matching
    - Auto-coverage with configurable threshold
    - Coverage record tracking for audit
    - Annotator notification for review
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        notification_service: Optional[Any] = None,
    ):
        """
        Initialize the mid-coverage engine.
        
        Args:
            similarity_threshold: Default similarity threshold
            notification_service: Optional notification service for alerts
        """
        self.default_similarity_threshold = similarity_threshold
        self.notification_service = notification_service
        self._pattern_cache: Dict[str, AnnotationPattern] = {}
    
    async def analyze_patterns(
        self,
        annotated_samples: List[AnnotatedSample],
    ) -> List[AnnotationPattern]:
        """
        Analyze annotation patterns from samples.
        
        Extracts common patterns and features from annotated samples
        that can be used to identify similar unannotated tasks.
        
        Args:
            annotated_samples: List of annotated samples
            
        Returns:
            List of extracted patterns
        """
        if not annotated_samples:
            return []
        
        patterns: List[AnnotationPattern] = []
        
        # Group samples by annotation type
        samples_by_type: Dict[AnnotationType, List[AnnotatedSample]] = defaultdict(list)
        for sample in annotated_samples:
            samples_by_type[sample.annotation_type].append(sample)
        
        # Extract patterns for each type
        for annotation_type, type_samples in samples_by_type.items():
            type_patterns = await self._extract_patterns_for_type(
                type_samples, annotation_type
            )
            patterns.extend(type_patterns)
        
        # Cache patterns
        for pattern in patterns:
            self._pattern_cache[pattern.pattern_id] = pattern
        
        logger.info(f"Extracted {len(patterns)} patterns from {len(annotated_samples)} samples")
        return patterns
    
    async def find_similar_tasks(
        self,
        patterns: List[AnnotationPattern],
        unannotated_tasks: List[AnnotationTask],
        similarity_threshold: float = None,
    ) -> List[SimilarTaskMatch]:
        """
        Find unannotated tasks similar to patterns.
        
        Args:
            patterns: Patterns to match against
            unannotated_tasks: Tasks to search
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of task matches with similarity scores
        """
        threshold = similarity_threshold or self.default_similarity_threshold
        matches: List[SimilarTaskMatch] = []
        
        for task in unannotated_tasks:
            best_match = await self._find_best_pattern_match(task, patterns, threshold)
            if best_match:
                matches.append(best_match)
        
        # Sort by similarity score descending
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        
        logger.info(f"Found {len(matches)} similar tasks above threshold {threshold}")
        return matches
    
    async def auto_cover(
        self,
        matches: List[SimilarTaskMatch],
        config: CoverageConfig = None,
    ) -> CoverageBatchResult:
        """
        Auto-cover tasks with annotations from matched patterns.
        
        Args:
            matches: List of task-pattern matches
            config: Coverage configuration
            
        Returns:
            CoverageBatchResult with coverage details
        """
        config = config or CoverageConfig()
        
        # Limit coverage count
        matches_to_cover = matches[:config.max_coverage]
        
        results: List[CoverageResult] = []
        total_similarity = 0.0
        
        for match in matches_to_cover:
            # Get pattern from cache
            pattern = self._pattern_cache.get(match.pattern_id)
            if not pattern:
                continue
            
            # Create coverage result
            result = CoverageResult(
                task_id=match.task_id,
                source_sample_id=pattern.source_annotations[0] if pattern.source_annotations else "",
                pattern_id=match.pattern_id,
                similarity_score=match.similarity_score,
                annotation=match.suggested_annotation,
                auto_covered=config.auto_apply,
                reviewed=False,
                created_at=datetime.utcnow(),
            )
            
            results.append(result)
            total_similarity += match.similarity_score
        
        avg_similarity = total_similarity / len(results) if results else 0.0
        
        batch_result = CoverageBatchResult(
            total_matched=len(matches),
            covered_count=len(results),
            average_similarity=avg_similarity,
            results=results,
            needs_review=config.notify_annotator,
        )
        
        logger.info(f"Auto-covered {len(results)} tasks with avg similarity {avg_similarity:.2f}")
        return batch_result
    
    async def notify_annotator(
        self,
        annotator_id: str,
        coverage_results: List[CoverageResult],
    ) -> None:
        """
        Notify annotator about auto-coverage for review.
        
        Args:
            annotator_id: ID of annotator to notify
            coverage_results: Coverage results to review
        """
        if not coverage_results:
            return
        
        notification_data = {
            "type": "auto_coverage_review",
            "annotator_id": annotator_id,
            "coverage_count": len(coverage_results),
            "task_ids": [r.task_id for r in coverage_results],
            "average_similarity": sum(r.similarity_score for r in coverage_results) / len(coverage_results),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if self.notification_service:
            try:
                await self.notification_service.send(
                    user_id=annotator_id,
                    notification_type="auto_coverage_review",
                    data=notification_data,
                )
                logger.info(f"Notified annotator {annotator_id} about {len(coverage_results)} coverage results")
            except Exception as e:
                logger.error(f"Failed to notify annotator {annotator_id}: {e}")
        else:
            logger.info(f"Would notify annotator {annotator_id}: {notification_data}")
    
    def get_coverage_record(self, result: CoverageResult) -> Dict[str, Any]:
        """
        Get coverage record for audit purposes.
        
        Args:
            result: Coverage result
            
        Returns:
            Dictionary with coverage record details
        """
        return {
            "task_id": result.task_id,
            "source_sample_id": result.source_sample_id,
            "pattern_id": result.pattern_id,
            "similarity_score": result.similarity_score,
            "annotation": result.annotation,
            "auto_covered": result.auto_covered,
            "reviewed": result.reviewed,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }
    
    # ========================================================================
    # Private methods
    # ========================================================================
    
    async def _extract_patterns_for_type(
        self,
        samples: List[AnnotatedSample],
        annotation_type: AnnotationType,
    ) -> List[AnnotationPattern]:
        """Extract patterns for a specific annotation type."""
        patterns = []
        
        # Group similar samples
        sample_groups = self._group_similar_samples(samples)
        
        for group_id, group_samples in sample_groups.items():
            if len(group_samples) < 1:
                continue
            
            # Extract common features
            features = self._extract_common_features(group_samples)
            
            # Create annotation template from most common annotation
            template = self._create_annotation_template(group_samples)
            
            pattern = AnnotationPattern(
                pattern_id=str(uuid4()),
                source_annotations=[s.id for s in group_samples],
                pattern_features=features,
                annotation_template=template,
                confidence=min(1.0, len(group_samples) * 0.2),  # More samples = higher confidence
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def _group_similar_samples(
        self,
        samples: List[AnnotatedSample],
    ) -> Dict[str, List[AnnotatedSample]]:
        """Group samples by similarity."""
        groups: Dict[str, List[AnnotatedSample]] = defaultdict(list)
        
        for sample in samples:
            # Create a simple hash based on annotation structure
            annotation_hash = self._hash_annotation_structure(sample.annotation)
            groups[annotation_hash].append(sample)
        
        return groups
    
    def _hash_annotation_structure(self, annotation: Dict[str, Any]) -> str:
        """Create a hash of annotation structure."""
        # Extract structure (keys and value types)
        structure = {}
        for key, value in annotation.items():
            if isinstance(value, list):
                structure[key] = f"list_{len(value)}"
            elif isinstance(value, dict):
                structure[key] = "dict"
            else:
                structure[key] = type(value).__name__
        
        structure_str = json.dumps(structure, sort_keys=True)
        return hashlib.md5(structure_str.encode()).hexdigest()[:8]
    
    def _extract_common_features(
        self,
        samples: List[AnnotatedSample],
    ) -> Dict[str, Any]:
        """Extract common features from samples."""
        if not samples:
            return {}
        
        features = {
            "sample_count": len(samples),
            "common_keys": set(),
            "text_patterns": [],
        }
        
        # Find common annotation keys
        all_keys = [set(s.annotation.keys()) for s in samples]
        if all_keys:
            features["common_keys"] = list(set.intersection(*all_keys))
        
        # Extract text patterns (simplified)
        for sample in samples[:5]:  # Limit to first 5
            text = sample.data.get("text", "")
            if text:
                # Extract first few words as pattern
                words = text.split()[:5]
                features["text_patterns"].append(" ".join(words))
        
        return features
    
    def _create_annotation_template(
        self,
        samples: List[AnnotatedSample],
    ) -> Dict[str, Any]:
        """Create annotation template from samples."""
        if not samples:
            return {}
        
        # Use the first sample's annotation as template
        # In production, this would be more sophisticated
        return samples[0].annotation.copy()
    
    async def _find_best_pattern_match(
        self,
        task: AnnotationTask,
        patterns: List[AnnotationPattern],
        threshold: float,
    ) -> Optional[SimilarTaskMatch]:
        """Find the best matching pattern for a task."""
        best_match = None
        best_score = 0.0
        
        for pattern in patterns:
            score = self._calculate_similarity(task, pattern)
            
            if score >= threshold and score > best_score:
                best_score = score
                best_match = SimilarTaskMatch(
                    task_id=task.id,
                    pattern_id=pattern.pattern_id,
                    similarity_score=score,
                    suggested_annotation=pattern.annotation_template,
                )
        
        return best_match
    
    def _calculate_similarity(
        self,
        task: AnnotationTask,
        pattern: AnnotationPattern,
    ) -> float:
        """
        Calculate similarity between task and pattern.
        
        Uses a combination of:
        - Text similarity (if available)
        - Metadata overlap
        - Structure similarity
        """
        score = 0.0
        weights = {"text": 0.6, "metadata": 0.2, "structure": 0.2}
        
        # Text similarity
        task_text = task.data.get("text", "")
        pattern_texts = pattern.pattern_features.get("text_patterns", [])
        
        if task_text and pattern_texts:
            text_scores = [
                self._text_similarity(task_text, pt)
                for pt in pattern_texts
            ]
            if text_scores:
                score += weights["text"] * max(text_scores)
        else:
            # If no text, redistribute weight
            score += weights["text"] * 0.5
        
        # Metadata overlap
        common_keys = pattern.pattern_features.get("common_keys", [])
        if common_keys:
            task_keys = set(task.metadata.keys())
            overlap = len(task_keys.intersection(set(common_keys)))
            score += weights["metadata"] * (overlap / max(len(common_keys), 1))
        else:
            score += weights["metadata"] * 0.5
        
        # Structure similarity (based on data keys)
        task_data_keys = set(task.data.keys())
        if task_data_keys:
            score += weights["structure"] * 0.8  # Assume similar structure
        
        return min(1.0, score)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using word overlap."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


# Singleton instance
_engine_instances: Dict[str, MidCoverageEngine] = {}


def get_mid_coverage_engine(
    tenant_id: Optional[str] = None,
    similarity_threshold: float = 0.85,
) -> MidCoverageEngine:
    """
    Get or create a mid-coverage engine instance.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        similarity_threshold: Default similarity threshold
        
    Returns:
        MidCoverageEngine instance
    """
    key = tenant_id or "global"
    
    if key not in _engine_instances:
        _engine_instances[key] = MidCoverageEngine(
            similarity_threshold=similarity_threshold
        )
    
    return _engine_instances[key]
