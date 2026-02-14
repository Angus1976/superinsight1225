"""
Quality Comparison Service for AI Application Integration.

Compares quality metrics between governed and raw data sources using Ragas framework.
Integrates with existing Ragas quality evaluation infrastructure.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.ragas_integration.evaluator import RagasEvaluator, RagasEvaluationResult
from src.ragas_integration.quality_monitor import QualityMonitor, MonitoringConfig
from src.ragas_integration.trend_analyzer import QualityTrendAnalyzer
from src.models.annotation import Annotation

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality metrics for a dataset."""
    
    completeness: float  # Percentage of non-null values
    accuracy: float  # Validation against ground truth
    consistency: float  # Cross-field validation
    timeliness: float  # Data freshness
    ai_confidence: float  # Model confidence scores
    semantic_quality: float  # Ragas-based semantic evaluation
    overall_score: float  # Weighted average
    
    # Ragas-specific metrics
    ragas_faithfulness: Optional[float] = None
    ragas_relevancy: Optional[float] = None
    ragas_precision: Optional[float] = None
    ragas_recall: Optional[float] = None
    
    # Lineage tracking for governed data
    lineage_info: Optional[Dict[str, Any]] = None
    governance_steps: Optional[List[str]] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonMetrics:
    """Comparison metrics between governed and raw data."""
    
    governed_metrics: QualityMetrics
    raw_metrics: QualityMetrics
    improvement_percentage: Dict[str, float]  # Per-metric improvement
    overall_improvement: float
    
    comparison_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComparisonReport:
    """Detailed comparison report with visualizations."""
    
    comparison_metrics: ComparisonMetrics
    summary: str
    recommendations: List[str]
    visualizations: Dict[str, Any]  # Chart data for frontend
    
    report_id: str = field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = field(default_factory=datetime.utcnow)


class QualityComparisonService:
    """Compares quality metrics between governed and raw data."""
    
    def __init__(self, enable_monitoring: bool = False):
        """
        Initialize quality comparison service.
        
        Args:
            enable_monitoring: Enable quality monitoring and trend analysis
        """
        self.ragas_evaluator = RagasEvaluator()
        
        # Optional quality monitoring
        self.quality_monitor: Optional[QualityMonitor] = None
        self.trend_analyzer: Optional[QualityTrendAnalyzer] = None
        
        if enable_monitoring:
            self.quality_monitor = QualityMonitor()
            self.trend_analyzer = QualityTrendAnalyzer()
        
        # Metric weights for overall score
        self.metric_weights = {
            'completeness': 0.20,
            'accuracy': 0.25,
            'consistency': 0.15,
            'timeliness': 0.10,
            'ai_confidence': 0.15,
            'semantic_quality': 0.15
        }
    
    async def evaluate_quality(
        self,
        data: Any,
        is_governed: bool,
        annotations: Optional[List[Any]] = None
    ) -> QualityMetrics:
        """
        Evaluate data quality using Ragas framework.
        
        Args:
            data: Dataset to evaluate
            is_governed: Whether data is governed
            annotations: Optional annotation data for Ragas evaluation
            
        Returns:
            Quality metrics for the dataset
        """
        logger.info(f"Evaluating quality for {'governed' if is_governed else 'raw'} data")
        
        # Calculate basic metrics
        completeness = self._calculate_completeness(data)
        accuracy = self._calculate_accuracy(data)
        consistency = self._calculate_consistency(data)
        timeliness = self._calculate_timeliness(data)
        ai_confidence = self._calculate_ai_confidence(data)
        
        # Calculate semantic quality using Ragas
        semantic_quality = await self._calculate_semantic_quality(data, annotations)
        
        # Get detailed Ragas metrics for comparison
        ragas_metrics = await self.get_detailed_ragas_metrics(data, annotations)
        
        # Extract lineage info for governed data
        lineage_info = None
        governance_steps = None
        if is_governed:
            lineage_info = self.extract_lineage_info(data)
            if lineage_info:
                governance_steps = lineage_info.get('governance_pipeline', [])
        
        # Calculate overall score
        overall_score = (
            completeness * self.metric_weights['completeness'] +
            accuracy * self.metric_weights['accuracy'] +
            consistency * self.metric_weights['consistency'] +
            timeliness * self.metric_weights['timeliness'] +
            ai_confidence * self.metric_weights['ai_confidence'] +
            semantic_quality * self.metric_weights['semantic_quality']
        )
        
        return QualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            ai_confidence=ai_confidence,
            semantic_quality=semantic_quality,
            overall_score=overall_score,
            ragas_faithfulness=ragas_metrics.get('ragas_faithfulness'),
            ragas_relevancy=ragas_metrics.get('ragas_relevancy'),
            ragas_precision=ragas_metrics.get('ragas_precision'),
            ragas_recall=ragas_metrics.get('ragas_recall'),
            lineage_info=lineage_info,
            governance_steps=governance_steps,
            metadata={
                'is_governed': is_governed,
                'record_count': len(data) if isinstance(data, list) else 1,
                'evaluation_timestamp': datetime.utcnow().isoformat(),
                'ragas_available': self.ragas_evaluator.is_available()
            }
        )
    
    async def compare_datasets(
        self,
        governed_data: Any,
        raw_data: Any,
        governed_annotations: Optional[List[Any]] = None,
        raw_annotations: Optional[List[Any]] = None
    ) -> ComparisonMetrics:
        """
        Compare quality metrics between governed and raw datasets.
        
        Args:
            governed_data: Governed dataset
            raw_data: Raw dataset
            governed_annotations: Annotations for governed data
            raw_annotations: Annotations for raw data
            
        Returns:
            Comparison metrics showing differences
        """
        logger.info("Comparing governed vs raw data quality")
        
        # Evaluate both datasets
        governed_metrics = await self.evaluate_quality(
            governed_data, 
            is_governed=True,
            annotations=governed_annotations
        )
        raw_metrics = await self.evaluate_quality(
            raw_data,
            is_governed=False,
            annotations=raw_annotations
        )
        
        # Calculate improvement percentages
        improvement = self._calculate_improvement(governed_metrics, raw_metrics)
        
        # Calculate overall improvement
        overall_improvement = (
            governed_metrics.overall_score - raw_metrics.overall_score
        ) / raw_metrics.overall_score * 100 if raw_metrics.overall_score > 0 else 0
        
        return ComparisonMetrics(
            governed_metrics=governed_metrics,
            raw_metrics=raw_metrics,
            improvement_percentage=improvement,
            overall_improvement=overall_improvement
        )
    
    def generate_comparison_report(
        self,
        comparison: ComparisonMetrics
    ) -> ComparisonReport:
        """
        Generate detailed comparison report with visualizations.
        
        Args:
            comparison: Comparison metrics
            
        Returns:
            Detailed report with visualizations
        """
        logger.info(f"Generating comparison report: {comparison.comparison_id}")
        
        # Generate summary
        summary = self._generate_summary(comparison)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(comparison)
        
        # Generate visualization data
        visualizations = self._generate_visualizations(comparison)
        
        return ComparisonReport(
            comparison_metrics=comparison,
            summary=summary,
            recommendations=recommendations,
            visualizations=visualizations
        )
    
    def _calculate_completeness(self, data: Any) -> float:
        """Calculate completeness metric (percentage of non-null values)."""
        if not data:
            return 0.0
        
        if isinstance(data, list):
            total_fields = 0
            non_null_fields = 0
            
            for record in data:
                if isinstance(record, dict):
                    for value in record.values():
                        total_fields += 1
                        if value is not None and value != '':
                            non_null_fields += 1
            
            return non_null_fields / total_fields if total_fields > 0 else 0.0
        
        return 1.0  # Single record assumed complete
    
    def _calculate_accuracy(self, data: Any) -> float:
        """Calculate accuracy metric (validation against ground truth)."""
        # Placeholder: In real implementation, compare against ground truth
        # For now, return a baseline score
        if not data:
            return 0.0
        
        # Governed data typically has higher accuracy due to validation
        return 0.85  # Baseline accuracy score
    
    def _calculate_consistency(self, data: Any) -> float:
        """Calculate consistency metric (cross-field validation)."""
        if not data:
            return 0.0
        
        if isinstance(data, list):
            # Check format consistency across records
            if not data:
                return 0.0
            
            # Get field names from first record
            if isinstance(data[0], dict):
                expected_fields = set(data[0].keys())
                consistent_records = sum(
                    1 for record in data
                    if isinstance(record, dict) and set(record.keys()) == expected_fields
                )
                return consistent_records / len(data)
        
        return 1.0
    
    def _calculate_timeliness(self, data: Any) -> float:
        """Calculate timeliness metric (data freshness)."""
        # Placeholder: Check timestamps if available
        # For now, return a baseline score
        return 0.90  # Baseline timeliness score
    
    def _calculate_ai_confidence(self, data: Any) -> float:
        """Calculate AI confidence metric (model confidence scores)."""
        if not data:
            return 0.0
        
        # Check if data has confidence scores
        if isinstance(data, list):
            confidence_scores = []
            for record in data:
                if isinstance(record, dict) and 'confidence' in record:
                    confidence_scores.append(record['confidence'])
            
            if confidence_scores:
                return sum(confidence_scores) / len(confidence_scores)
        
        return 0.75  # Baseline confidence score
    
    async def _calculate_semantic_quality(
        self,
        data: Any,
        annotations: Optional[List[Any]] = None
    ) -> float:
        """
        Calculate semantic quality using Ragas framework.
        
        Integrates with existing Ragas evaluation infrastructure.
        """
        if not self.ragas_evaluator.is_available():
            logger.warning("Ragas not available, using baseline semantic quality")
            return 0.70
        
        if not annotations:
            logger.info("No annotations provided, using baseline semantic quality")
            return 0.70
        
        try:
            # Convert to Annotation objects if needed
            annotation_objects = self._convert_to_annotations(annotations)
            
            # Evaluate using Ragas
            result: RagasEvaluationResult = await self.ragas_evaluator.evaluate_annotations(
                annotations=annotation_objects
            )
            
            # Add to monitoring if enabled
            if self.quality_monitor:
                self.quality_monitor.add_evaluation_result(result)
            
            if self.trend_analyzer:
                self.trend_analyzer.add_evaluation_result(result)
            
            # Return overall score from Ragas evaluation
            return result.overall_score
            
        except Exception as e:
            logger.error(f"Ragas evaluation failed: {e}")
            return 0.70  # Fallback score
    
    def _convert_to_annotations(self, annotations: List[Any]) -> List[Annotation]:
        """Convert annotation data to Annotation objects."""
        annotation_objects = []
        
        for ann in annotations:
            if isinstance(ann, Annotation):
                annotation_objects.append(ann)
            elif isinstance(ann, dict):
                # Create Annotation object from dict
                annotation_objects.append(
                    Annotation(
                        id=ann.get('id'),
                        annotation_data=ann.get('annotation_data', ann),
                        confidence=ann.get('confidence', 1.0)
                    )
                )
        
        return annotation_objects
    
    async def get_detailed_ragas_metrics(
        self,
        data: Any,
        annotations: Optional[List[Any]] = None
    ) -> Dict[str, float]:
        """
        Get detailed Ragas metrics for comparison-specific analysis.
        
        Returns individual Ragas metrics (faithfulness, relevancy, precision, recall).
        """
        if not self.ragas_evaluator.is_available() or not annotations:
            return {}
        
        try:
            annotation_objects = self._convert_to_annotations(annotations)
            
            # Evaluate with all available metrics
            result: RagasEvaluationResult = await self.ragas_evaluator.evaluate_annotations(
                annotations=annotation_objects,
                metrics=['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
            )
            
            # Extract individual metrics
            return {
                'ragas_faithfulness': result.metrics.get('faithfulness', 0.0),
                'ragas_relevancy': result.metrics.get('answer_relevancy', 0.0),
                'ragas_precision': result.metrics.get('context_precision', 0.0),
                'ragas_recall': result.metrics.get('context_recall', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get detailed Ragas metrics: {e}")
            return {}
    
    def extract_lineage_info(self, data: Any) -> Optional[Dict[str, Any]]:
        """
        Extract lineage information for governed data.
        
        Tracks governance steps applied to the data.
        """
        if not isinstance(data, (list, dict)):
            return None
        
        lineage = {
            'tracked': False,
            'governance_pipeline': [],
            'transformations': [],
            'quality_checks': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Extract lineage from data metadata
        if isinstance(data, dict):
            metadata = data.get('metadata', {})
            lineage['tracked'] = metadata.get('lineage_tracked', False)
            lineage['governance_pipeline'] = metadata.get('governance_steps', [])
            lineage['transformations'] = metadata.get('transformations', [])
            lineage['quality_checks'] = metadata.get('quality_checks', [])
        elif isinstance(data, list) and data:
            # Check first record for lineage info
            first_record = data[0]
            if isinstance(first_record, dict):
                metadata = first_record.get('metadata', {})
                lineage['tracked'] = metadata.get('lineage_tracked', False)
                lineage['governance_pipeline'] = metadata.get('governance_steps', [])
        
        return lineage if lineage['tracked'] else None
    
    def _calculate_improvement(
        self,
        governed: QualityMetrics,
        raw: QualityMetrics
    ) -> Dict[str, float]:
        """Calculate improvement percentage for each metric."""
        improvements = {}
        
        for metric in ['completeness', 'accuracy', 'consistency', 
                      'timeliness', 'ai_confidence', 'semantic_quality']:
            governed_value = getattr(governed, metric)
            raw_value = getattr(raw, metric)
            
            if raw_value > 0:
                improvement = (governed_value - raw_value) / raw_value * 100
            else:
                improvement = 0.0
            
            improvements[metric] = improvement
        
        return improvements
    
    def _generate_summary(self, comparison: ComparisonMetrics) -> str:
        """Generate summary text for comparison."""
        overall_improvement = comparison.overall_improvement
        
        if overall_improvement > 20:
            quality_level = "significant"
        elif overall_improvement > 10:
            quality_level = "moderate"
        elif overall_improvement > 0:
            quality_level = "slight"
        else:
            quality_level = "no"
        
        summary = (
            f"Quality comparison shows {quality_level} improvement "
            f"({overall_improvement:.1f}%) when using governed data. "
            f"Governed data overall score: {comparison.governed_metrics.overall_score:.2f}, "
            f"Raw data overall score: {comparison.raw_metrics.overall_score:.2f}."
        )
        
        return summary
    
    def _generate_recommendations(self, comparison: ComparisonMetrics) -> List[str]:
        """Generate recommendations based on comparison."""
        recommendations = []
        
        # Check each metric for significant differences
        for metric, improvement in comparison.improvement_percentage.items():
            if improvement < 5:  # Less than 5% improvement
                recommendations.append(
                    f"Consider improving {metric} in governance process "
                    f"(current improvement: {improvement:.1f}%)"
                )
        
        # Overall recommendation
        if comparison.overall_improvement > 20:
            recommendations.append(
                "Governed data shows excellent quality improvement. "
                "Continue using governance pipeline for production workloads."
            )
        elif comparison.overall_improvement < 10:
            recommendations.append(
                "Quality improvement is below target. "
                "Review governance rules and validation processes."
            )
        
        return recommendations
    
    def _generate_visualizations(self, comparison: ComparisonMetrics) -> Dict[str, Any]:
        """Generate visualization data for frontend."""
        # Radar chart data for quality metrics
        radar_data = {
            'labels': ['Completeness', 'Accuracy', 'Consistency', 
                      'Timeliness', 'AI Confidence', 'Semantic Quality'],
            'governed': [
                comparison.governed_metrics.completeness,
                comparison.governed_metrics.accuracy,
                comparison.governed_metrics.consistency,
                comparison.governed_metrics.timeliness,
                comparison.governed_metrics.ai_confidence,
                comparison.governed_metrics.semantic_quality
            ],
            'raw': [
                comparison.raw_metrics.completeness,
                comparison.raw_metrics.accuracy,
                comparison.raw_metrics.consistency,
                comparison.raw_metrics.timeliness,
                comparison.raw_metrics.ai_confidence,
                comparison.raw_metrics.semantic_quality
            ]
        }
        
        # Bar chart data for improvements
        bar_data = {
            'labels': list(comparison.improvement_percentage.keys()),
            'values': list(comparison.improvement_percentage.values())
        }
        
        # Overall score comparison
        score_comparison = {
            'governed': comparison.governed_metrics.overall_score,
            'raw': comparison.raw_metrics.overall_score,
            'improvement': comparison.overall_improvement
        }
        
        # Ragas-specific metrics comparison
        ragas_comparison = None
        if (comparison.governed_metrics.ragas_faithfulness is not None and
            comparison.raw_metrics.ragas_faithfulness is not None):
            ragas_comparison = {
                'labels': ['Faithfulness', 'Relevancy', 'Precision', 'Recall'],
                'governed': [
                    comparison.governed_metrics.ragas_faithfulness or 0,
                    comparison.governed_metrics.ragas_relevancy or 0,
                    comparison.governed_metrics.ragas_precision or 0,
                    comparison.governed_metrics.ragas_recall or 0
                ],
                'raw': [
                    comparison.raw_metrics.ragas_faithfulness or 0,
                    comparison.raw_metrics.ragas_relevancy or 0,
                    comparison.raw_metrics.ragas_precision or 0,
                    comparison.raw_metrics.ragas_recall or 0
                ]
            }
        
        # Lineage visualization for governed data
        lineage_viz = None
        if comparison.governed_metrics.lineage_info:
            lineage_viz = {
                'governance_steps': comparison.governed_metrics.governance_steps or [],
                'transformations': comparison.governed_metrics.lineage_info.get('transformations', []),
                'quality_checks': comparison.governed_metrics.lineage_info.get('quality_checks', [])
            }
        
        viz_data = {
            'radar_chart': radar_data,
            'bar_chart': bar_data,
            'score_comparison': score_comparison
        }
        
        if ragas_comparison:
            viz_data['ragas_comparison'] = ragas_comparison
        
        if lineage_viz:
            viz_data['lineage'] = lineage_viz
        
        return viz_data
    
    async def get_quality_trends(
        self,
        time_period_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        Get quality trends over time using trend analyzer.
        
        Args:
            time_period_days: Number of days to analyze
            
        Returns:
            Trend analysis data or None if monitoring not enabled
        """
        if not self.trend_analyzer:
            logger.warning("Trend analyzer not enabled")
            return None
        
        from datetime import timedelta
        
        trends = self.trend_analyzer.analyze_all_metrics(
            timedelta(days=time_period_days)
        )
        
        return {
            metric: trend.to_dict()
            for metric, trend in trends.items()
        }
    
    async def start_quality_monitoring(self) -> None:
        """Start quality monitoring if enabled."""
        if self.quality_monitor:
            await self.quality_monitor.start_monitoring()
            logger.info("Quality monitoring started")
        else:
            logger.warning("Quality monitoring not enabled")
    
    async def stop_quality_monitoring(self) -> None:
        """Stop quality monitoring if enabled."""
        if self.quality_monitor:
            await self.quality_monitor.stop_monitoring()
            logger.info("Quality monitoring stopped")
    
    def get_monitoring_status(self) -> Optional[Dict[str, Any]]:
        """Get current monitoring status."""
        if self.quality_monitor:
            return self.quality_monitor.get_monitoring_status()
        return None
