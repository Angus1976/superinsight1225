"""
Unit tests for QualityComparisonService.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai_integration.quality_comparison import (
    QualityComparisonService,
    QualityMetrics,
    ComparisonMetrics,
    ComparisonReport
)
from src.ragas_integration.evaluator import RagasEvaluationResult


@pytest.fixture
def quality_service():
    """Create QualityComparisonService instance."""
    return QualityComparisonService()


@pytest.fixture
def sample_governed_data():
    """Sample governed data."""
    return [
        {
            'id': 1,
            'name': 'Record 1',
            'value': 100,
            'category': 'A',
            'confidence': 0.95
        },
        {
            'id': 2,
            'name': 'Record 2',
            'value': 200,
            'category': 'B',
            'confidence': 0.92
        }
    ]


@pytest.fixture
def sample_raw_data():
    """Sample raw data with missing values."""
    return [
        {
            'id': 1,
            'name': 'Record 1',
            'value': None,  # Missing value
            'category': 'A',
            'confidence': 0.75
        },
        {
            'id': 2,
            'name': '',  # Empty value
            'value': 200,
            'category': 'B'  # Missing confidence
        }
    ]


class TestQualityMetrics:
    """Test QualityMetrics dataclass."""
    
    def test_quality_metrics_creation(self):
        """Test creating QualityMetrics."""
        metrics = QualityMetrics(
            completeness=0.95,
            accuracy=0.90,
            consistency=0.88,
            timeliness=0.92,
            ai_confidence=0.85,
            semantic_quality=0.87,
            overall_score=0.89
        )
        
        assert metrics.completeness == 0.95
        assert metrics.accuracy == 0.90
        assert metrics.overall_score == 0.89
        assert isinstance(metrics.metadata, dict)


class TestQualityComparisonService:
    """Test QualityComparisonService."""
    
    @pytest.mark.asyncio
    async def test_evaluate_quality_governed_data(
        self,
        quality_service,
        sample_governed_data
    ):
        """Test evaluating quality for governed data."""
        metrics = await quality_service.evaluate_quality(
            data=sample_governed_data,
            is_governed=True
        )
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.completeness > 0
        assert metrics.overall_score > 0
        assert metrics.metadata['is_governed'] is True
        assert metrics.metadata['record_count'] == 2
    
    @pytest.mark.asyncio
    async def test_evaluate_quality_raw_data(
        self,
        quality_service,
        sample_raw_data
    ):
        """Test evaluating quality for raw data."""
        metrics = await quality_service.evaluate_quality(
            data=sample_raw_data,
            is_governed=False
        )
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.completeness < 1.0  # Has missing values
        assert metrics.metadata['is_governed'] is False
    
    def test_calculate_completeness_full_data(
        self,
        quality_service,
        sample_governed_data
    ):
        """Test completeness calculation with full data."""
        completeness = quality_service._calculate_completeness(
            sample_governed_data
        )
        
        assert completeness == 1.0  # All fields present
    
    def test_calculate_completeness_missing_data(
        self,
        quality_service,
        sample_raw_data
    ):
        """Test completeness calculation with missing data."""
        completeness = quality_service._calculate_completeness(
            sample_raw_data
        )
        
        # Should be less than 1.0 due to missing values
        assert 0 < completeness < 1.0
    
    def test_calculate_completeness_empty_data(self, quality_service):
        """Test completeness calculation with empty data."""
        completeness = quality_service._calculate_completeness([])
        assert completeness == 0.0
    
    def test_calculate_consistency_consistent_data(
        self,
        quality_service,
        sample_governed_data
    ):
        """Test consistency calculation with consistent data."""
        consistency = quality_service._calculate_consistency(
            sample_governed_data
        )
        
        assert consistency == 1.0  # All records have same fields
    
    def test_calculate_consistency_inconsistent_data(
        self,
        quality_service
    ):
        """Test consistency calculation with inconsistent data."""
        inconsistent_data = [
            {'id': 1, 'name': 'A', 'value': 100},
            {'id': 2, 'name': 'B'},  # Missing 'value' field
        ]
        
        consistency = quality_service._calculate_consistency(
            inconsistent_data
        )
        
        assert consistency < 1.0
    
    def test_calculate_ai_confidence_with_scores(
        self,
        quality_service,
        sample_governed_data
    ):
        """Test AI confidence calculation with confidence scores."""
        confidence = quality_service._calculate_ai_confidence(
            sample_governed_data
        )
        
        # Average of 0.95 and 0.92
        assert 0.93 <= confidence <= 0.94
    
    def test_calculate_ai_confidence_without_scores(
        self,
        quality_service
    ):
        """Test AI confidence calculation without confidence scores."""
        data_no_confidence = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'}
        ]
        
        confidence = quality_service._calculate_ai_confidence(
            data_no_confidence
        )
        
        # Should return baseline score
        assert confidence == 0.75
    
    @pytest.mark.asyncio
    async def test_calculate_semantic_quality_with_ragas(
        self,
        quality_service
    ):
        """Test semantic quality calculation with Ragas."""
        mock_annotations = [MagicMock()]
        mock_result = RagasEvaluationResult(
            evaluation_id='test_eval',
            overall_score=0.88,
            metrics={},
            task_id=None
        )
        
        with patch.object(
            quality_service.ragas_evaluator,
            'is_available',
            return_value=True
        ):
            with patch.object(
                quality_service.ragas_evaluator,
                'evaluate_annotations',
                new=AsyncMock(return_value=mock_result)
            ):
                semantic_quality = await quality_service._calculate_semantic_quality(
                    data=[],
                    annotations=mock_annotations
                )
                
                assert semantic_quality == 0.88
    
    @pytest.mark.asyncio
    async def test_calculate_semantic_quality_without_ragas(
        self,
        quality_service
    ):
        """Test semantic quality calculation without Ragas."""
        with patch.object(
            quality_service.ragas_evaluator,
            'is_available',
            return_value=False
        ):
            semantic_quality = await quality_service._calculate_semantic_quality(
                data=[],
                annotations=None
            )
            
            # Should return baseline score
            assert semantic_quality == 0.70
    
    @pytest.mark.asyncio
    async def test_compare_datasets(
        self,
        quality_service,
        sample_governed_data,
        sample_raw_data
    ):
        """Test comparing governed vs raw datasets."""
        comparison = await quality_service.compare_datasets(
            governed_data=sample_governed_data,
            raw_data=sample_raw_data
        )
        
        assert isinstance(comparison, ComparisonMetrics)
        assert isinstance(comparison.governed_metrics, QualityMetrics)
        assert isinstance(comparison.raw_metrics, QualityMetrics)
        assert isinstance(comparison.improvement_percentage, dict)
        assert 'completeness' in comparison.improvement_percentage
        assert comparison.comparison_id is not None
    
    @pytest.mark.asyncio
    async def test_compare_datasets_shows_improvement(
        self,
        quality_service,
        sample_governed_data,
        sample_raw_data
    ):
        """Test that governed data shows improvement over raw data."""
        comparison = await quality_service.compare_datasets(
            governed_data=sample_governed_data,
            raw_data=sample_raw_data
        )
        
        # Governed data should have better completeness
        assert (
            comparison.governed_metrics.completeness >
            comparison.raw_metrics.completeness
        )
        
        # Overall improvement should be positive
        assert comparison.overall_improvement > 0
    
    def test_calculate_improvement(self, quality_service):
        """Test improvement calculation."""
        governed = QualityMetrics(
            completeness=0.95,
            accuracy=0.90,
            consistency=0.88,
            timeliness=0.92,
            ai_confidence=0.85,
            semantic_quality=0.87,
            overall_score=0.89
        )
        
        raw = QualityMetrics(
            completeness=0.75,
            accuracy=0.80,
            consistency=0.70,
            timeliness=0.85,
            ai_confidence=0.70,
            semantic_quality=0.72,
            overall_score=0.75
        )
        
        improvements = quality_service._calculate_improvement(governed, raw)
        
        assert 'completeness' in improvements
        assert improvements['completeness'] > 0  # Positive improvement
        
        # Completeness improved from 0.75 to 0.95
        # (0.95 - 0.75) / 0.75 * 100 = 26.67%
        assert 26 <= improvements['completeness'] <= 27
    
    def test_generate_comparison_report(self, quality_service):
        """Test generating comparison report."""
        governed = QualityMetrics(
            completeness=0.95,
            accuracy=0.90,
            consistency=0.88,
            timeliness=0.92,
            ai_confidence=0.85,
            semantic_quality=0.87,
            overall_score=0.89
        )
        
        raw = QualityMetrics(
            completeness=0.75,
            accuracy=0.80,
            consistency=0.70,
            timeliness=0.85,
            ai_confidence=0.70,
            semantic_quality=0.72,
            overall_score=0.75
        )
        
        comparison = ComparisonMetrics(
            governed_metrics=governed,
            raw_metrics=raw,
            improvement_percentage={
                'completeness': 26.67,
                'accuracy': 12.5,
                'consistency': 25.71,
                'timeliness': 8.24,
                'ai_confidence': 21.43,
                'semantic_quality': 20.83
            },
            overall_improvement=18.67
        )
        
        report = quality_service.generate_comparison_report(comparison)
        
        assert isinstance(report, ComparisonReport)
        assert report.comparison_metrics == comparison
        assert isinstance(report.summary, str)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.visualizations, dict)
        assert report.report_id is not None
    
    def test_generate_summary_significant_improvement(
        self,
        quality_service
    ):
        """Test summary generation with significant improvement."""
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.95, accuracy=0.90, consistency=0.88,
                timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
                overall_score=0.89
            ),
            raw_metrics=QualityMetrics(
                completeness=0.70, accuracy=0.75, consistency=0.65,
                timeliness=0.80, ai_confidence=0.65, semantic_quality=0.68,
                overall_score=0.70
            ),
            improvement_percentage={},
            overall_improvement=27.14  # > 20%
        )
        
        summary = quality_service._generate_summary(comparison)
        
        assert 'significant' in summary
        assert '27.1%' in summary
    
    def test_generate_summary_moderate_improvement(
        self,
        quality_service
    ):
        """Test summary generation with moderate improvement."""
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.85, accuracy=0.82, consistency=0.80,
                timeliness=0.85, ai_confidence=0.78, semantic_quality=0.80,
                overall_score=0.82
            ),
            raw_metrics=QualityMetrics(
                completeness=0.75, accuracy=0.75, consistency=0.72,
                timeliness=0.78, ai_confidence=0.70, semantic_quality=0.73,
                overall_score=0.74
            ),
            improvement_percentage={},
            overall_improvement=10.81  # 10-20%
        )
        
        summary = quality_service._generate_summary(comparison)
        
        assert 'moderate' in summary
    
    def test_generate_recommendations(self, quality_service):
        """Test recommendations generation."""
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.95, accuracy=0.90, consistency=0.88,
                timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
                overall_score=0.89
            ),
            raw_metrics=QualityMetrics(
                completeness=0.93, accuracy=0.88, consistency=0.86,
                timeliness=0.90, ai_confidence=0.83, semantic_quality=0.85,
                overall_score=0.87
            ),
            improvement_percentage={
                'completeness': 2.15,  # < 5%
                'accuracy': 2.27,  # < 5%
                'consistency': 2.33,  # < 5%
                'timeliness': 2.22,  # < 5%
                'ai_confidence': 2.41,  # < 5%
                'semantic_quality': 2.35  # < 5%
            },
            overall_improvement=2.30
        )
        
        recommendations = quality_service._generate_recommendations(
            comparison
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should recommend improving metrics with low improvement
        assert any('completeness' in rec for rec in recommendations)
    
    def test_generate_visualizations(self, quality_service):
        """Test visualization data generation."""
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.95, accuracy=0.90, consistency=0.88,
                timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
                overall_score=0.89
            ),
            raw_metrics=QualityMetrics(
                completeness=0.75, accuracy=0.80, consistency=0.70,
                timeliness=0.85, ai_confidence=0.70, semantic_quality=0.72,
                overall_score=0.75
            ),
            improvement_percentage={
                'completeness': 26.67,
                'accuracy': 12.5,
                'consistency': 25.71,
                'timeliness': 8.24,
                'ai_confidence': 21.43,
                'semantic_quality': 20.83
            },
            overall_improvement=18.67
        )
        
        visualizations = quality_service._generate_visualizations(comparison)
        
        assert 'radar_chart' in visualizations
        assert 'bar_chart' in visualizations
        assert 'score_comparison' in visualizations
        
        # Check radar chart structure
        radar = visualizations['radar_chart']
        assert 'labels' in radar
        assert 'governed' in radar
        assert 'raw' in radar
        assert len(radar['labels']) == 6
        assert len(radar['governed']) == 6
        assert len(radar['raw']) == 6
        
        # Check bar chart structure
        bar = visualizations['bar_chart']
        assert 'labels' in bar
        assert 'values' in bar
        
        # Check score comparison
        score = visualizations['score_comparison']
        assert score['governed'] == 0.89
        assert score['raw'] == 0.75
        assert score['improvement'] == 18.67


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_evaluate_quality_empty_data(self, quality_service):
        """Test evaluating empty data."""
        metrics = await quality_service.evaluate_quality(
            data=[],
            is_governed=True
        )
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.completeness == 0.0
    
    @pytest.mark.asyncio
    async def test_evaluate_quality_single_record(self, quality_service):
        """Test evaluating single record."""
        single_record = {'id': 1, 'name': 'Test', 'value': 100}
        
        metrics = await quality_service.evaluate_quality(
            data=single_record,
            is_governed=True
        )
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.completeness == 1.0
    
    def test_calculate_improvement_zero_raw_value(self, quality_service):
        """Test improvement calculation when raw value is zero."""
        governed = QualityMetrics(
            completeness=0.95, accuracy=0.90, consistency=0.88,
            timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
            overall_score=0.89
        )
        
        raw = QualityMetrics(
            completeness=0.0,  # Zero value
            accuracy=0.80, consistency=0.70,
            timeliness=0.85, ai_confidence=0.70, semantic_quality=0.72,
            overall_score=0.75
        )
        
        improvements = quality_service._calculate_improvement(governed, raw)
        
        # Should handle zero gracefully
        assert improvements['completeness'] == 0.0


class TestComparisonWorkflow:
    """Test complete comparison workflow (Requirements 15.2, 15.3, 15.4)."""
    
    @pytest.mark.asyncio
    async def test_complete_comparison_workflow(
        self,
        quality_service,
        sample_governed_data,
        sample_raw_data
    ):
        """
        Test complete comparison workflow from data to report.
        Validates Requirements 15.2, 15.3, 15.4.
        """
        # Step 1: Compare datasets (Requirement 15.2)
        comparison = await quality_service.compare_datasets(
            governed_data=sample_governed_data,
            raw_data=sample_raw_data
        )
        
        assert isinstance(comparison, ComparisonMetrics)
        assert comparison.comparison_id is not None
        
        # Step 2: Verify quality metrics are calculated (Requirement 15.3)
        assert comparison.governed_metrics.completeness > 0
        assert comparison.governed_metrics.accuracy > 0
        assert comparison.governed_metrics.consistency > 0
        assert comparison.governed_metrics.ai_confidence > 0
        
        assert comparison.raw_metrics.completeness > 0
        assert comparison.raw_metrics.accuracy > 0
        
        # Step 3: Generate report with visualizations (Requirement 15.4)
        report = quality_service.generate_comparison_report(comparison)
        
        assert isinstance(report, ComparisonReport)
        assert report.report_id is not None
        assert len(report.summary) > 0
        assert len(report.recommendations) > 0
        
        # Verify visualizations for frontend display (Requirement 15.4)
        assert 'radar_chart' in report.visualizations
        assert 'bar_chart' in report.visualizations
        assert 'score_comparison' in report.visualizations
        
        # Verify visual indicators data structure
        radar = report.visualizations['radar_chart']
        assert len(radar['labels']) == 6
        assert len(radar['governed']) == 6
        assert len(radar['raw']) == 6
        
        # Verify improvement percentages are calculated
        assert 'completeness' in comparison.improvement_percentage
        assert 'accuracy' in comparison.improvement_percentage
        assert 'consistency' in comparison.improvement_percentage
    
    @pytest.mark.asyncio
    async def test_comparison_with_ragas_integration(
        self,
        quality_service
    ):
        """
        Test comparison using Ragas framework (Requirement 15.5).
        """
        governed_data = [
            {'id': 1, 'text': 'High quality data', 'confidence': 0.95}
        ]
        raw_data = [
            {'id': 1, 'text': 'Low quality data', 'confidence': 0.65}
        ]
        
        # Mock annotations for Ragas evaluation
        mock_annotations = [
            MagicMock(
                id=1,
                annotation_data={'text': 'Test annotation'},
                confidence=0.9
            )
        ]
        
        with patch.object(
            quality_service.ragas_evaluator,
            'is_available',
            return_value=True
        ):
            with patch.object(
                quality_service.ragas_evaluator,
                'evaluate_annotations',
                new=AsyncMock(return_value=RagasEvaluationResult(
                    evaluation_id='test_eval',
                    overall_score=0.88,
                    metrics={
                        'faithfulness': 0.90,
                        'answer_relevancy': 0.85,
                        'context_precision': 0.87,
                        'context_recall': 0.89
                    },
                    task_id=None
                ))
            ):
                comparison = await quality_service.compare_datasets(
                    governed_data=governed_data,
                    raw_data=raw_data,
                    governed_annotations=mock_annotations,
                    raw_annotations=mock_annotations
                )
                
                # Verify Ragas metrics are included
                assert comparison.governed_metrics.semantic_quality > 0
                assert comparison.raw_metrics.semantic_quality > 0
                
                # Verify detailed Ragas metrics
                assert comparison.governed_metrics.ragas_faithfulness is not None
                assert comparison.governed_metrics.ragas_relevancy is not None
    
    @pytest.mark.asyncio
    async def test_lineage_tracking_for_governed_data(
        self,
        quality_service
    ):
        """
        Test lineage information extraction (Requirement 15.6).
        """
        governed_data_with_lineage = [
            {
                'id': 1,
                'value': 100,
                'metadata': {
                    'lineage_tracked': True,
                    'governance_steps': [
                        'Data Validation',
                        'Quality Enhancement',
                        'Semantic Enrichment'
                    ],
                    'transformations': ['Normalization', 'Deduplication'],
                    'quality_checks': ['Completeness Check', 'Accuracy Check']
                }
            }
        ]
        
        metrics = await quality_service.evaluate_quality(
            data=governed_data_with_lineage,
            is_governed=True
        )
        
        # Verify lineage information is extracted
        assert metrics.lineage_info is not None
        assert metrics.lineage_info['tracked'] is True
        assert len(metrics.governance_steps) == 3
        assert 'Data Validation' in metrics.governance_steps
        assert 'Quality Enhancement' in metrics.governance_steps
        
        # Verify lineage is included in visualizations
        comparison = await quality_service.compare_datasets(
            governed_data=governed_data_with_lineage,
            raw_data=[{'id': 1, 'value': 100}]
        )
        
        report = quality_service.generate_comparison_report(comparison)
        
        if 'lineage' in report.visualizations:
            lineage_viz = report.visualizations['lineage']
            assert 'governance_steps' in lineage_viz
            assert len(lineage_viz['governance_steps']) == 3


class TestReportGeneration:
    """Test report generation functionality (Requirements 15.3, 15.4)."""
    
    def test_report_includes_all_required_metrics(self, quality_service):
        """
        Test that report includes all required quality metrics.
        Validates Requirement 15.3.
        """
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.95, accuracy=0.90, consistency=0.88,
                timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
                overall_score=0.89
            ),
            raw_metrics=QualityMetrics(
                completeness=0.75, accuracy=0.80, consistency=0.70,
                timeliness=0.85, ai_confidence=0.70, semantic_quality=0.72,
                overall_score=0.75
            ),
            improvement_percentage={
                'completeness': 26.67,
                'accuracy': 12.5,
                'consistency': 25.71,
                'timeliness': 8.24,
                'ai_confidence': 21.43,
                'semantic_quality': 20.83
            },
            overall_improvement=18.67
        )
        
        report = quality_service.generate_comparison_report(comparison)
        
        # Verify all required metrics are in visualizations
        radar = report.visualizations['radar_chart']
        expected_metrics = [
            'Completeness', 'Accuracy', 'Consistency',
            'Timeliness', 'AI Confidence', 'Semantic Quality'
        ]
        
        for metric in expected_metrics:
            assert metric in radar['labels']
        
        # Verify score comparison includes all components
        score_comp = report.visualizations['score_comparison']
        assert 'governed' in score_comp
        assert 'raw' in score_comp
        assert 'improvement' in score_comp
    
    def test_visual_indicators_for_differences(self, quality_service):
        """
        Test visual indicators for highlighting differences.
        Validates Requirement 15.4.
        """
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.95, accuracy=0.90, consistency=0.88,
                timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
                overall_score=0.89
            ),
            raw_metrics=QualityMetrics(
                completeness=0.60, accuracy=0.65, consistency=0.55,
                timeliness=0.70, ai_confidence=0.60, semantic_quality=0.62,
                overall_score=0.62
            ),
            improvement_percentage={
                'completeness': 58.33,
                'accuracy': 38.46,
                'consistency': 60.0,
                'timeliness': 31.43,
                'ai_confidence': 41.67,
                'semantic_quality': 40.32
            },
            overall_improvement=43.55
        )
        
        report = quality_service.generate_comparison_report(comparison)
        
        # Verify bar chart shows improvement percentages
        bar_chart = report.visualizations['bar_chart']
        assert 'labels' in bar_chart
        assert 'values' in bar_chart
        assert len(bar_chart['values']) == 6
        
        # All improvements should be positive
        for value in bar_chart['values']:
            assert value > 0
        
        # Verify recommendations highlight significant differences
        assert len(report.recommendations) > 0
        assert any('excellent' in rec.lower() or 'significant' in rec.lower() 
                  for rec in report.recommendations)
    
    def test_report_with_ragas_metrics(self, quality_service):
        """
        Test report generation with Ragas-specific metrics.
        Validates Requirement 15.5.
        """
        comparison = ComparisonMetrics(
            governed_metrics=QualityMetrics(
                completeness=0.95, accuracy=0.90, consistency=0.88,
                timeliness=0.92, ai_confidence=0.85, semantic_quality=0.87,
                overall_score=0.89,
                ragas_faithfulness=0.92,
                ragas_relevancy=0.88,
                ragas_precision=0.90,
                ragas_recall=0.86
            ),
            raw_metrics=QualityMetrics(
                completeness=0.75, accuracy=0.80, consistency=0.70,
                timeliness=0.85, ai_confidence=0.70, semantic_quality=0.72,
                overall_score=0.75,
                ragas_faithfulness=0.70,
                ragas_relevancy=0.68,
                ragas_precision=0.72,
                ragas_recall=0.69
            ),
            improvement_percentage={
                'completeness': 26.67,
                'accuracy': 12.5,
                'consistency': 25.71,
                'timeliness': 8.24,
                'ai_confidence': 21.43,
                'semantic_quality': 20.83
            },
            overall_improvement=18.67
        )
        
        report = quality_service.generate_comparison_report(comparison)
        
        # Verify Ragas comparison is included in visualizations
        assert 'ragas_comparison' in report.visualizations
        
        ragas_viz = report.visualizations['ragas_comparison']
        assert 'labels' in ragas_viz
        assert 'governed' in ragas_viz
        assert 'raw' in ragas_viz
        
        # Verify all Ragas metrics are present
        expected_ragas_metrics = ['Faithfulness', 'Relevancy', 'Precision', 'Recall']
        assert ragas_viz['labels'] == expected_ragas_metrics
        
        # Verify governed data has better Ragas scores
        for i in range(len(ragas_viz['governed'])):
            assert ragas_viz['governed'][i] >= ragas_viz['raw'][i]
