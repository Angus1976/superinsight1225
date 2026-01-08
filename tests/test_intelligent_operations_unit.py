"""
Unit tests for Intelligent Operations System.

Tests the AI-driven operations capabilities including:
- Machine learning-based anomaly detection and prediction
- Automated operations management
- Operations knowledge base functionality
- Decision support system
"""

import pytest
import asyncio
import time
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.system.intelligent_operations import (
    IntelligentOperationsSystem, MLPredictor, CapacityPlanner,
    IntelligentRecommendationEngine, PredictionType, RecommendationType
)
from src.system.automated_operations import (
    AutomatedOperationsSystem, AutoScaler, AutomatedRecoverySystem,
    AutomatedBackupSystem, AutomationLevel, OperationType
)
from src.system.operations_knowledge_base import (
    OperationsKnowledgeSystem, CaseLibrary, KnowledgeBase,
    DecisionSupportSystem, OperationalCase, CaseType, CaseSeverity, CaseStatus
)


class TestMLPredictor:
    """Test ML predictor functionality."""
    
    @pytest.fixture
    def ml_predictor(self):
        return MLPredictor()
    
    def test_add_training_data(self, ml_predictor):
        """Test adding training data."""
        features = {"cpu_usage": 75.0, "memory_usage": 60.0}
        target = 80.0
        
        ml_predictor.add_training_data("cpu_metric", features, target)
        
        assert len(ml_predictor.training_data["cpu_metric"]) == 1
        data_point = ml_predictor.training_data["cpu_metric"][0]
        assert data_point["features"] == features
        assert data_point["target"] == target
    
    @pytest.mark.asyncio
    async def test_train_model_insufficient_data(self, ml_predictor):
        """Test training with insufficient data."""
        # Add only a few data points
        for i in range(10):
            ml_predictor.add_training_data("test_metric", {"feature1": i}, i * 2)
        
        success = await ml_predictor.train_model("test_metric")
        assert not success  # Should fail due to insufficient data
    
    @pytest.mark.asyncio
    async def test_train_model_success(self, ml_predictor):
        """Test successful model training."""
        # Add sufficient training data with variation
        for i in range(150):
            features = {
                "cpu_usage": 50 + i % 40,
                "memory_usage": 60 + (i * 2) % 30,
                "hour_of_day": i % 24
            }
            target = 70 + (i % 50) + np.random.normal(0, 5)
            ml_predictor.add_training_data("test_metric", features, target)
        
        success = await ml_predictor.train_model("test_metric")
        assert success
        assert "test_metric" in ml_predictor.models
        assert "test_metric" in ml_predictor.scalers
        assert ml_predictor.model_accuracy["test_metric"] >= 0
    
    @pytest.mark.asyncio
    async def test_predict_no_model(self, ml_predictor):
        """Test prediction without trained model."""
        features = {"cpu_usage": 75.0}
        result = await ml_predictor.predict("nonexistent_metric", features)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_predict_with_model(self, ml_predictor):
        """Test prediction with trained model."""
        # Train a simple model first
        for i in range(150):
            features = {"feature1": i, "feature2": i * 2}
            target = i * 1.5 + 10
            ml_predictor.add_training_data("linear_metric", features, target)
        
        await ml_predictor.train_model("linear_metric")
        
        # Make prediction
        test_features = {"feature1": 100, "feature2": 200}
        result = await ml_predictor.predict("linear_metric", test_features)
        
        assert result is not None
        predicted_value, confidence = result
        assert isinstance(predicted_value, (int, float))
        assert 0 <= confidence <= 1
    
    def test_needs_retraining(self, ml_predictor):
        """Test retraining logic."""
        # New metric should need training
        assert ml_predictor.needs_retraining("new_metric")
        
        # Recently trained metric should not need retraining
        ml_predictor.last_training["recent_metric"] = datetime.utcnow()
        assert not ml_predictor.needs_retraining("recent_metric")
        
        # Old metric should need retraining
        ml_predictor.last_training["old_metric"] = datetime.utcnow() - timedelta(hours=25)
        assert ml_predictor.needs_retraining("old_metric")


class TestCapacityPlanner:
    """Test capacity planning functionality."""
    
    @pytest.fixture
    def capacity_planner(self):
        ml_predictor = MLPredictor()
        return CapacityPlanner(ml_predictor)
    
    @pytest.mark.asyncio
    async def test_generate_capacity_forecast(self, capacity_planner):
        """Test capacity forecast generation."""
        current_metrics = {
            "cpu_usage_percent": 75.0,
            "memory_usage_percent": 60.0,
            "hour_of_day": 14,
            "day_of_week": 2
        }
        
        forecast = await capacity_planner.generate_capacity_forecast(
            "cpu_usage_percent", current_metrics
        )
        
        assert forecast.resource_type == "cpu_usage_percent"
        assert forecast.current_usage == 75.0
        assert len(forecast.predicted_usage) == 24
        assert forecast.capacity_limit == 80.0  # Default for CPU
        assert isinstance(forecast.recommended_action, str)
        assert 0 <= forecast.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_capacity_forecast_exhaustion_warning(self, capacity_planner):
        """Test capacity forecast with exhaustion warning."""
        # High current usage that will exceed capacity
        current_metrics = {
            "cpu_usage_percent": 95.0,  # Very high usage
            "memory_usage_percent": 60.0
        }
        
        forecast = await capacity_planner.generate_capacity_forecast(
            "cpu_usage_percent", current_metrics
        )
        
        # Should predict exhaustion soon
        assert forecast.time_to_exhaustion is not None
        assert "URGENT" in forecast.recommended_action or "Scale up" in forecast.recommended_action
    
    def test_update_growth_rate(self, capacity_planner):
        """Test growth rate calculation."""
        # Historical data showing growth
        historical_data = [
            (time.time() - 3600, 50.0),  # 1 hour ago
            (time.time() - 1800, 55.0),  # 30 minutes ago
            (time.time(), 60.0)          # Now
        ]
        
        capacity_planner.update_growth_rate("test_resource", historical_data)
        
        assert "test_resource" in capacity_planner.growth_rates
        growth_rate = capacity_planner.growth_rates["test_resource"]
        assert isinstance(growth_rate, float)
        assert -0.1 <= growth_rate <= 0.1  # Should be clamped


class TestIntelligentRecommendationEngine:
    """Test intelligent recommendation engine."""
    
    @pytest.fixture
    def recommendation_engine(self):
        ml_predictor = MLPredictor()
        capacity_planner = CapacityPlanner(ml_predictor)
        return IntelligentRecommendationEngine(ml_predictor, capacity_planner)
    
    @pytest.mark.asyncio
    async def test_generate_performance_recommendations(self, recommendation_engine):
        """Test performance recommendation generation."""
        # High CPU usage scenario
        system_metrics = {
            "system.cpu.usage_percent": 85.0,
            "system.memory.usage_percent": 70.0,
            "requests.duration": 1.5
        }
        
        recommendations = await recommendation_engine._generate_performance_recommendations(system_metrics)
        
        assert len(recommendations) > 0
        cpu_rec = next((r for r in recommendations if "CPU" in r.title), None)
        assert cpu_rec is not None
        assert cpu_rec.recommendation_type == RecommendationType.OPTIMIZE_PERFORMANCE
        assert cpu_rec.priority in ["medium", "high"]
    
    @pytest.mark.asyncio
    async def test_generate_capacity_recommendations(self, recommendation_engine):
        """Test capacity recommendation generation."""
        from src.system.intelligent_operations import CapacityForecast
        
        # Create forecast with exhaustion warning
        forecast = CapacityForecast(
            resource_type="cpu_usage_percent",
            current_usage=85.0,
            predicted_usage=[90.0] * 24,
            capacity_limit=80.0,
            time_to_exhaustion=4,  # 4 hours
            recommended_action="Scale up immediately",
            confidence=0.8,
            created_at=datetime.utcnow()
        )
        
        recommendations = await recommendation_engine._generate_capacity_recommendations([forecast])
        
        assert len(recommendations) > 0
        scale_rec = recommendations[0]
        assert scale_rec.recommendation_type == RecommendationType.SCALE_UP
        assert scale_rec.priority in ["high", "critical"]
    
    def test_calculate_recommendation_score(self, recommendation_engine):
        """Test recommendation scoring."""
        from src.system.intelligent_operations import OperationalRecommendation
        
        high_priority_rec = OperationalRecommendation(
            recommendation_id="test1",
            recommendation_type=RecommendationType.OPTIMIZE_PERFORMANCE,
            title="High Priority Test",
            description="Test recommendation",
            priority="critical",
            estimated_impact={"performance": 0.8, "cost": -0.2},
            implementation_effort="low",
            timeline="immediate",
            prerequisites=[],
            risks=[],
            created_at=datetime.utcnow()
        )
        
        low_priority_rec = OperationalRecommendation(
            recommendation_id="test2",
            recommendation_type=RecommendationType.OPTIMIZE_PERFORMANCE,
            title="Low Priority Test",
            description="Test recommendation",
            priority="low",
            estimated_impact={"performance": 0.2},
            implementation_effort="high",
            timeline="long_term",
            prerequisites=[],
            risks=[],
            created_at=datetime.utcnow()
        )
        
        high_score = recommendation_engine._calculate_recommendation_score(high_priority_rec)
        low_score = recommendation_engine._calculate_recommendation_score(low_priority_rec)
        
        assert high_score > low_score


class TestAutoScaler:
    """Test auto-scaling functionality."""
    
    @pytest.fixture
    def auto_scaler(self):
        metrics_collector = Mock()
        return AutoScaler(metrics_collector)
    
    @pytest.mark.asyncio
    async def test_evaluate_scaling_decision_scale_up(self, auto_scaler):
        """Test scale up decision."""
        current_metrics = {
            "system.cpu.usage_percent": 85.0,  # Above threshold
            "system.memory.usage_percent": 70.0,
            "requests.duration": 1.5,
            "error_rate_percent": 2.0
        }
        
        decision = await auto_scaler.evaluate_scaling_decision("test_service", current_metrics)
        
        assert decision is not None
        assert decision["action"] == "scale_up"
        assert decision["service"] == "test_service"
        assert len(decision["reasons"]) > 0
        assert "CPU usage" in decision["reasons"][0]
    
    @pytest.mark.asyncio
    async def test_evaluate_scaling_decision_scale_down(self, auto_scaler):
        """Test scale down decision."""
        current_metrics = {
            "system.cpu.usage_percent": 20.0,  # Low usage
            "system.memory.usage_percent": 25.0,  # Low usage
            "requests.duration": 0.5,
            "error_rate_percent": 0.1
        }
        
        # Mock current instances > min
        auto_scaler._get_current_instances = Mock(return_value=3)
        
        decision = await auto_scaler.evaluate_scaling_decision("test_service", current_metrics)
        
        assert decision is not None
        assert decision["action"] == "scale_down"
        assert decision["service"] == "test_service"
    
    @pytest.mark.asyncio
    async def test_evaluate_scaling_decision_no_action(self, auto_scaler):
        """Test no scaling action needed."""
        current_metrics = {
            "system.cpu.usage_percent": 50.0,  # Normal usage
            "system.memory.usage_percent": 60.0,  # Normal usage
            "requests.duration": 1.0,
            "error_rate_percent": 1.0
        }
        
        decision = await auto_scaler.evaluate_scaling_decision("test_service", current_metrics)
        
        assert decision is None  # No action needed
    
    @pytest.mark.asyncio
    async def test_execute_scaling_action(self, auto_scaler):
        """Test scaling action execution."""
        scaling_decision = {
            "action": "scale_up",
            "service": "test_service",
            "recommended_instances": 3,
            "reasons": ["High CPU usage"],
            "cooldown": 300
        }
        
        # Mock successful scaling
        auto_scaler._simulate_scaling = AsyncMock(return_value=True)
        
        success = await auto_scaler.execute_scaling_action(scaling_decision)
        
        assert success
        assert len(auto_scaler.scaling_history) > 0
        assert "test_service" in auto_scaler.cooldown_periods


class TestCaseLibrary:
    """Test case library functionality."""
    
    @pytest.fixture
    def case_library(self, tmp_path):
        db_path = tmp_path / "test_cases.db"
        return CaseLibrary(str(db_path))
    
    @pytest.fixture
    def sample_case(self):
        return OperationalCase(
            case_id="test_case_001",
            case_type=CaseType.FAULT_RESOLUTION,
            severity=CaseSeverity.HIGH,
            status=CaseStatus.RESOLVED,
            title="High CPU Usage Resolution",
            description="System experienced high CPU usage",
            symptoms=["CPU usage > 90%", "Slow response times"],
            root_cause="Inefficient database queries",
            resolution_steps=["Added database indexes", "Optimized queries"],
            resolution_time_minutes=30,
            tags={"cpu", "performance", "database"},
            related_metrics={"cpu_usage_percent": 95.0},
            effectiveness_score=0.9
        )
    
    def test_add_case(self, case_library, sample_case):
        """Test adding a case to the library."""
        success = case_library.add_case(sample_case)
        
        assert success
        assert sample_case.case_id in case_library.cases
        assert case_library.cases[sample_case.case_id] == sample_case
    
    def test_search_cases_by_type(self, case_library, sample_case):
        """Test searching cases by type."""
        case_library.add_case(sample_case)
        
        results = case_library.search_cases(
            query=None,
            case_type=CaseType.FAULT_RESOLUTION
        )
        
        assert len(results) == 1
        assert results[0].case_id == sample_case.case_id
    
    def test_search_cases_by_query(self, case_library, sample_case):
        """Test searching cases by text query."""
        case_library.add_case(sample_case)
        
        results = case_library.search_cases(query="CPU usage")
        
        assert len(results) == 1
        assert results[0].case_id == sample_case.case_id
    
    def test_find_similar_cases(self, case_library, sample_case):
        """Test finding similar cases."""
        case_library.add_case(sample_case)
        
        similar_cases = case_library.find_similar_cases(
            symptoms=["High CPU usage", "Performance issues"],
            metrics={"cpu_usage_percent": 88.0}
        )
        
        assert len(similar_cases) == 1
        case, similarity = similar_cases[0]
        assert case.case_id == sample_case.case_id
        assert 0 < similarity <= 1
    
    def test_calculate_similarity(self, case_library, sample_case):
        """Test similarity calculation."""
        symptoms1 = ["CPU usage high", "slow response"]
        metrics1 = {"cpu_usage_percent": 90.0}
        
        similarity = case_library._calculate_similarity(symptoms1, metrics1, sample_case)
        
        assert 0 <= similarity <= 1
        assert similarity > 0  # Should have some similarity
    
    def test_get_case_statistics(self, case_library, sample_case):
        """Test case statistics generation."""
        case_library.add_case(sample_case)
        
        stats = case_library.get_case_statistics()
        
        assert stats["total_cases"] == 1
        assert stats["by_type"]["fault_resolution"] == 1
        assert stats["by_severity"]["high"] == 1
        assert stats["avg_effectiveness"] == 0.9


class TestDecisionSupportSystem:
    """Test decision support system."""
    
    @pytest.fixture
    def decision_support(self, tmp_path):
        case_db = tmp_path / "test_cases.db"
        kb_db = tmp_path / "test_kb.db"
        case_library = CaseLibrary(str(case_db))
        knowledge_base = KnowledgeBase(str(kb_db))
        return DecisionSupportSystem(case_library, knowledge_base)
    
    @pytest.mark.asyncio
    async def test_get_rule_based_recommendations(self, decision_support):
        """Test rule-based recommendations."""
        from src.system.operations_knowledge_base import DecisionContext
        
        context = DecisionContext(
            situation_id="test_situation",
            description="High CPU usage",
            current_metrics={"cpu_usage_percent": 85.0},
            symptoms=["High CPU usage"],
            constraints={},
            objectives=["Improve performance"],
            time_pressure="high",
            risk_tolerance="medium"
        )
        
        recommendations = await decision_support._get_rule_based_recommendations(context)
        
        assert len(recommendations) > 0
        cpu_rec = next((r for r in recommendations if "CPU" in r.recommended_action), None)
        assert cpu_rec is not None
    
    def test_matches_rule_conditions(self, decision_support):
        """Test rule condition matching."""
        metrics = {"cpu_usage_percent": 85.0, "memory_usage_percent": 70.0}
        
        # Should match
        conditions1 = {"cpu_usage_percent": {"min": 80}}
        assert decision_support._matches_rule_conditions(metrics, conditions1)
        
        # Should not match
        conditions2 = {"cpu_usage_percent": {"min": 90}}
        assert not decision_support._matches_rule_conditions(metrics, conditions2)
    
    def test_record_decision_outcome(self, decision_support):
        """Test recording decision outcomes."""
        # Add a decision to history first
        from src.system.operations_knowledge_base import DecisionRecommendation
        
        rec = DecisionRecommendation(
            recommendation_id="test_rec_001",
            context_id="test_context",
            recommended_action="Scale up CPU",
            rationale="High CPU usage",
            confidence=0.8,
            expected_outcome="Improved performance",
            risks=[],
            prerequisites=[],
            estimated_effort="low",
            similar_cases=[],
            success_probability=0.7
        )
        
        decision_support.decision_history.append({
            "context": Mock(),
            "recommendations": [rec],
            "timestamp": datetime.utcnow()
        })
        
        # Record outcome
        success = decision_support.record_decision_outcome(
            "test_rec_001", True, "Performance improved", "Scaling was effective"
        )
        
        assert success


class TestIntelligentOperationsSystem:
    """Test main intelligent operations system."""
    
    @pytest.fixture
    def intelligent_ops(self):
        metrics_collector = Mock()
        anomaly_detector = Mock()
        fault_detector = Mock()
        
        return IntelligentOperationsSystem(
            metrics_collector, anomaly_detector, fault_detector
        )
    
    def test_initialization(self, intelligent_ops):
        """Test system initialization."""
        assert intelligent_ops.ml_predictor is not None
        assert intelligent_ops.capacity_planner is not None
        assert intelligent_ops.recommendation_engine is not None
        assert not intelligent_ops.is_running
    
    @pytest.mark.asyncio
    async def test_start_stop(self, intelligent_ops):
        """Test starting and stopping the system."""
        # Mock the analysis loop to prevent infinite running
        intelligent_ops._analysis_loop = AsyncMock()
        
        await intelligent_ops.start()
        assert intelligent_ops.is_running
        
        await intelligent_ops.stop()
        assert not intelligent_ops.is_running
    
    def test_flatten_metrics(self, intelligent_ops):
        """Test metrics flattening."""
        metrics_summary = {
            "cpu_usage": {"latest": 75.0, "avg": 70.0},
            "memory_usage": {"latest": 60.0, "avg": 55.0},
            "invalid_metric": {"no_latest": True}
        }
        
        flat_metrics = intelligent_ops._flatten_metrics(metrics_summary)
        
        assert flat_metrics["cpu_usage"] == 75.0
        assert flat_metrics["memory_usage"] == 60.0
        assert "invalid_metric" not in flat_metrics
    
    def test_get_system_insights(self, intelligent_ops):
        """Test system insights generation."""
        # Add some mock data
        from src.system.intelligent_operations import Prediction, CapacityForecast
        
        prediction = Prediction(
            prediction_id="test_pred",
            prediction_type=PredictionType.PERFORMANCE_DEGRADATION,
            target_metric="cpu_usage",
            predicted_value=80.0,
            confidence=0.8,
            prediction_horizon=1,
            created_at=datetime.utcnow(),
            features_used=["cpu", "memory"],
            model_accuracy=0.75
        )
        
        intelligent_ops.predictions["cpu_usage"] = prediction
        
        insights = intelligent_ops.get_system_insights()
        
        assert "predictions" in insights
        assert "capacity_forecasts" in insights
        assert "recommendations" in insights
        assert "model_status" in insights
        assert insights["predictions"]["cpu_usage"]["predicted_value"] == 80.0


if __name__ == "__main__":
    pytest.main([__file__])