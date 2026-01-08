"""
Unit tests for Ragas Integration System.

Tests the core functionality of Ragas evaluation, trend analysis,
and quality monitoring components.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from src.ragas_integration import (
    RagasEvaluator,
    RagasEvaluationResult,
    QualityTrendAnalyzer,
    QualityMonitor,
    MonitoringConfig
)
from src.ragas_integration.trend_analyzer import TrendDirection, AlertSeverity
from src.models.annotation import Annotation


class TestRagasEvaluator:
    """Test Ragas evaluator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RagasEvaluator()
    
    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        assert self.evaluator is not None
        assert hasattr(self.evaluator, 'available_metrics')
        assert hasattr(self.evaluator, 'metric_weights')
    
    def test_metric_descriptions(self):
        """Test getting metric descriptions."""
        descriptions = self.evaluator.get_metric_descriptions()
        
        assert isinstance(descriptions, dict)
        assert len(descriptions) > 0
        
        # Check for expected metrics
        expected_metrics = [
            "faithfulness", "answer_relevancy", "context_precision", 
            "context_recall", "answer_correctness", "answer_similarity"
        ]
        
        for metric in expected_metrics:
            assert metric in descriptions
            assert isinstance(descriptions[metric], str)
            assert len(descriptions[metric]) > 0
    
    @pytest.mark.asyncio
    async def test_basic_evaluation(self):
        """Test basic evaluation functionality."""
        # Create test annotations
        annotations = [
            Annotation(
                id=uuid4(),
                task_id=uuid4(),
                annotator_id="test_user",
                annotation_data={
                    "question": "What is machine learning?",
                    "answer": "Machine learning is a subset of AI.",
                    "context": "AI and machine learning context"
                },
                confidence=0.9
            )
        ]
        
        result = await self.evaluator.evaluate_annotations(annotations)
        
        assert isinstance(result, RagasEvaluationResult)
        assert result.evaluation_id is not None
        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0
        assert isinstance(result.metrics, dict)
        assert result.evaluation_date is not None
    
    @pytest.mark.asyncio
    async def test_single_annotation_evaluation(self):
        """Test single annotation evaluation."""
        annotation = Annotation(
            id=uuid4(),
            task_id=uuid4(),
            annotator_id="test_user",
            annotation_data={
                "question": "Test question?",
                "answer": "Test answer",
                "context": "Test context"
            },
            confidence=0.8
        )
        
        scores = await self.evaluator.evaluate_single_annotation(annotation)
        
        assert isinstance(scores, dict)
        assert len(scores) > 0
        
        # Should at least have confidence score
        assert "confidence" in scores
        assert scores["confidence"] == 0.8
    
    def test_configure_metric_weights(self):
        """Test configuring metric weights."""
        new_weights = {
            "faithfulness": 0.4,
            "answer_relevancy": 0.3,
            "context_precision": 0.2,
            "context_recall": 0.1
        }
        
        self.evaluator.configure_metric_weights(new_weights)
        
        for metric, weight in new_weights.items():
            assert self.evaluator.metric_weights[metric] == weight


class TestQualityTrendAnalyzer:
    """Test quality trend analyzer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = QualityTrendAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        assert self.analyzer is not None
        assert len(self.analyzer.evaluation_history) == 0
        assert isinstance(self.analyzer.alert_thresholds, dict)
        assert len(self.analyzer.active_alerts) == 0
    
    def test_add_evaluation_result(self):
        """Test adding evaluation results."""
        result = RagasEvaluationResult(
            evaluation_id="test_eval_001",
            metrics={"faithfulness": 0.8, "answer_relevancy": 0.9},
            overall_score=0.85
        )
        
        initial_count = len(self.analyzer.evaluation_history)
        self.analyzer.add_evaluation_result(result)
        
        assert len(self.analyzer.evaluation_history) == initial_count + 1
        assert self.analyzer.evaluation_history[-1] == result
    
    def test_trend_analysis_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        trend = self.analyzer.analyze_metric_trend("overall_score")
        
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA
        assert trend.confidence == 0.0
        assert trend.data_points == 0
    
    def test_trend_analysis_with_data(self):
        """Test trend analysis with sufficient data."""
        # Add multiple evaluation results
        for i in range(5):
            result = RagasEvaluationResult(
                evaluation_id=f"test_eval_{i}",
                metrics={"faithfulness": 0.7 + i * 0.05},
                overall_score=0.7 + i * 0.05,
                evaluation_date=datetime.now() - timedelta(days=4-i)
            )
            self.analyzer.add_evaluation_result(result)
        
        trend = self.analyzer.analyze_metric_trend("overall_score")
        
        assert trend.direction != TrendDirection.INSUFFICIENT_DATA
        assert trend.data_points == 5
        assert trend.current_value > 0
    
    def test_analyze_all_metrics(self):
        """Test analyzing all available metrics."""
        # Add evaluation result with multiple metrics
        result = RagasEvaluationResult(
            evaluation_id="test_eval_multi",
            metrics={
                "faithfulness": 0.8,
                "answer_relevancy": 0.9,
                "context_precision": 0.7
            },
            overall_score=0.8
        )
        self.analyzer.add_evaluation_result(result)
        
        trends = self.analyzer.analyze_all_metrics()
        
        assert isinstance(trends, dict)
        assert "overall_score" in trends
        assert "faithfulness" in trends
        assert "answer_relevancy" in trends
        assert "context_precision" in trends
    
    def test_alert_management(self):
        """Test alert management functionality."""
        # Initially no alerts
        alerts = self.analyzer.get_active_alerts()
        assert len(alerts) == 0
        
        # Add evaluation that should trigger alerts (low quality)
        result = RagasEvaluationResult(
            evaluation_id="low_quality_eval",
            metrics={"faithfulness": 0.4},  # Below critical threshold
            overall_score=0.4
        )
        self.analyzer.add_evaluation_result(result)
        
        # Check for alerts
        alerts = self.analyzer.get_active_alerts()
        assert len(alerts) > 0
        
        # Test alert acknowledgment
        if alerts:
            alert_id = alerts[0].alert_id
            success = self.analyzer.acknowledge_alert(alert_id)
            assert success is True
            
            # Test clearing acknowledged alerts
            cleared_count = self.analyzer.clear_acknowledged_alerts()
            assert cleared_count > 0
    
    def test_quality_summary(self):
        """Test quality summary generation."""
        # Add some evaluation results
        for i in range(3):
            result = RagasEvaluationResult(
                evaluation_id=f"summary_test_{i}",
                metrics={"faithfulness": 0.8 + i * 0.05},
                overall_score=0.8 + i * 0.05
            )
            self.analyzer.add_evaluation_result(result)
        
        summary = self.analyzer.get_quality_summary()
        
        assert isinstance(summary, dict)
        assert "overall_health_score" in summary
        assert "trends" in summary
        assert "active_alerts" in summary
        assert "recommendations" in summary
        assert "generated_at" in summary
    
    def test_export_trend_data(self):
        """Test exporting trend data."""
        # Add evaluation result
        result = RagasEvaluationResult(
            evaluation_id="export_test",
            metrics={"faithfulness": 0.8},
            overall_score=0.8
        )
        self.analyzer.add_evaluation_result(result)
        
        export_data = self.analyzer.export_trend_data("overall_score")
        
        assert isinstance(export_data, dict)
        assert "metric_name" in export_data
        assert "data_points" in export_data
        assert "trend_analysis" in export_data
        assert "exported_at" in export_data
        
        assert export_data["metric_name"] == "overall_score"
        assert len(export_data["data_points"]) > 0


class TestQualityMonitor:
    """Test quality monitor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = QualityMonitor()
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        assert self.monitor is not None
        assert isinstance(self.monitor.config, MonitoringConfig)
        assert self.monitor.status.value == "stopped"
        assert len(self.monitor.monitoring_tasks) == 0
    
    def test_config_update(self):
        """Test updating monitoring configuration."""
        new_config = MonitoringConfig(
            evaluation_interval=120,
            min_overall_quality=0.9,
            enable_auto_retraining=False
        )
        
        self.monitor.update_config(new_config)
        
        assert self.monitor.config.evaluation_interval == 120
        assert self.monitor.config.min_overall_quality == 0.9
        assert self.monitor.config.enable_auto_retraining is False
    
    def test_monitoring_status(self):
        """Test getting monitoring status."""
        status = self.monitor.get_monitoring_status()
        
        assert isinstance(status, dict)
        assert "status" in status
        assert "config" in status
        assert "statistics" in status
        assert "last_updated" in status
        
        assert status["status"] == "stopped"
        assert isinstance(status["statistics"], dict)
    
    @pytest.mark.asyncio
    async def test_manual_retraining(self):
        """Test manual retraining trigger."""
        initial_count = len(self.monitor.retraining_history)
        
        await self.monitor.manual_retraining("Test retraining")
        
        assert len(self.monitor.retraining_history) == initial_count + 1
        
        latest_event = self.monitor.retraining_history[-1]
        assert latest_event.trigger.value == "manual"
        assert latest_event.trigger_reason == "Test retraining"
    
    def test_retraining_history(self):
        """Test getting retraining history."""
        history = self.monitor.get_retraining_history()
        
        assert isinstance(history, list)
        # History might be empty initially, which is fine
    
    def test_add_evaluation_result(self):
        """Test adding evaluation result to monitor."""
        result = RagasEvaluationResult(
            evaluation_id="monitor_test",
            metrics={"faithfulness": 0.8},
            overall_score=0.8
        )
        
        # Should not raise any exceptions
        self.monitor.add_evaluation_result(result)
        
        # Verify it was added to trend analyzer
        assert len(self.monitor.trend_analyzer.evaluation_history) > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_report(self):
        """Test generating monitoring report."""
        # Add some evaluation data first
        result = RagasEvaluationResult(
            evaluation_id="report_test",
            metrics={"faithfulness": 0.8},
            overall_score=0.8
        )
        self.monitor.add_evaluation_result(result)
        
        report = await self.monitor.generate_monitoring_report()
        
        assert isinstance(report, dict)
        assert "report_period" in report
        assert "generated_at" in report
        assert "monitoring_status" in report
        assert "quality_summary" in report
        assert "retraining_summary" in report
        assert "recommendations" in report


class TestMonitoringConfig:
    """Test monitoring configuration."""
    
    def test_config_initialization(self):
        """Test config initialization with defaults."""
        config = MonitoringConfig()
        
        assert config.evaluation_interval == 300
        assert config.min_overall_quality == 0.7
        assert config.enable_auto_retraining is True
        assert config.enable_notifications is True
    
    def test_config_custom_values(self):
        """Test config with custom values."""
        config = MonitoringConfig(
            evaluation_interval=600,
            min_overall_quality=0.9,
            enable_auto_retraining=False,
            notification_channels=["email", "slack"]
        )
        
        assert config.evaluation_interval == 600
        assert config.min_overall_quality == 0.9
        assert config.enable_auto_retraining is False
        assert "email" in config.notification_channels
        assert "slack" in config.notification_channels
    
    def test_config_to_dict(self):
        """Test config serialization to dictionary."""
        config = MonitoringConfig()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert "evaluation_interval" in config_dict
        assert "min_overall_quality" in config_dict
        assert "enable_auto_retraining" in config_dict
        assert "enable_notifications" in config_dict


class TestIntegrationWorkflow:
    """Test integration workflow between components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RagasEvaluator()
        self.analyzer = QualityTrendAnalyzer()
        self.monitor = QualityMonitor()
    
    @pytest.mark.asyncio
    async def test_evaluation_to_trend_workflow(self):
        """Test workflow from evaluation to trend analysis."""
        # Create test annotation
        annotation = Annotation(
            id=uuid4(),
            task_id=uuid4(),
            annotator_id="workflow_test_user",
            annotation_data={
                "question": "Integration test question?",
                "answer": "Integration test answer",
                "context": "Integration test context"
            },
            confidence=0.85
        )
        
        # Step 1: Evaluate
        result = await self.evaluator.evaluate_annotations([annotation])
        assert isinstance(result, RagasEvaluationResult)
        
        # Step 2: Add to trend analyzer
        self.analyzer.add_evaluation_result(result)
        assert len(self.analyzer.evaluation_history) > 0
        
        # Step 3: Analyze trends
        trends = self.analyzer.analyze_all_metrics()
        assert isinstance(trends, dict)
        assert len(trends) > 0
        
        # Step 4: Get quality summary
        summary = self.analyzer.get_quality_summary()
        assert isinstance(summary, dict)
        assert "overall_health_score" in summary
    
    @pytest.mark.asyncio
    async def test_evaluation_to_monitoring_workflow(self):
        """Test workflow from evaluation to monitoring."""
        # Create test annotation
        annotation = Annotation(
            id=uuid4(),
            task_id=uuid4(),
            annotator_id="monitoring_test_user",
            annotation_data={
                "question": "Monitoring test question?",
                "answer": "Monitoring test answer"
            },
            confidence=0.75
        )
        
        # Step 1: Evaluate
        result = await self.evaluator.evaluate_annotations([annotation])
        
        # Step 2: Add to monitor
        self.monitor.add_evaluation_result(result)
        
        # Step 3: Check monitoring status
        status = self.monitor.get_monitoring_status()
        assert status["statistics"]["total_evaluations"] > 0
        
        # Step 4: Generate report
        report = await self.monitor.generate_monitoring_report()
        assert isinstance(report, dict)
        assert "quality_summary" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])