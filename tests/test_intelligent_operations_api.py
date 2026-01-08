"""
Tests for Intelligent Operations API endpoints.

Tests the REST API functionality without requiring ML dependencies.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Mock the dependencies before importing the API
with patch('src.system.intelligent_operations.get_intelligent_operations'), \
     patch('src.system.automated_operations.get_automated_operations'), \
     patch('src.system.operations_knowledge_base.get_operations_knowledge'):
    
    from src.api.intelligent_operations_api import router


class TestIntelligentOperationsAPI:
    """Test intelligent operations API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return {"user_id": "test_user", "username": "testuser"}
    
    def test_api_router_creation(self):
        """Test that the API router is created successfully."""
        assert router is not None
        assert router.prefix == "/api/intelligent-operations"
        assert "Intelligent Operations" in router.tags
    
    @patch('src.api.intelligent_operations_api.get_current_user')
    @patch('src.api.intelligent_operations_api.get_intelligent_operations')
    @patch('src.api.intelligent_operations_api.get_automated_operations')
    @patch('src.api.intelligent_operations_api.get_operations_knowledge')
    def test_status_endpoint(self, mock_knowledge, mock_automated, mock_intelligent, mock_auth, client):
        """Test the status endpoint."""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock system components
        mock_intelligent_instance = Mock()
        mock_intelligent_instance.is_running = True
        mock_intelligent_instance.analysis_interval = 300
        mock_intelligent_instance.predictions = {}
        mock_intelligent_instance.recommendations = []
        mock_intelligent.return_value = mock_intelligent_instance
        
        mock_automated_instance = Mock()
        mock_automated_instance.get_automation_status.return_value = {
            "is_running": True,
            "active_operations": 0,
            "automation_rules": {}
        }
        mock_automated.return_value = mock_automated_instance
        
        mock_knowledge_instance = Mock()
        mock_knowledge_instance.get_system_insights.return_value = {
            "case_library": {"total_cases": 0},
            "knowledge_base": {"total_articles": 0}
        }
        mock_knowledge.return_value = mock_knowledge_instance
        
        # Test the endpoint
        response = client.get("/api/intelligent-operations/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "intelligent_operations" in data
        assert "automated_operations" in data
        assert "knowledge_system" in data
    
    @patch('src.api.intelligent_operations_api.get_current_user')
    @patch('src.api.intelligent_operations_api.get_intelligent_operations')
    def test_insights_endpoint(self, mock_intelligent, mock_auth, client):
        """Test the insights endpoint."""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock intelligent operations
        mock_instance = Mock()
        mock_instance.get_system_insights.return_value = {
            "predictions": {},
            "capacity_forecasts": {},
            "recommendations": [],
            "model_status": {}
        }
        mock_intelligent.return_value = mock_instance
        
        # Test the endpoint
        response = client.get("/api/intelligent-operations/insights")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "timestamp" in data
    
    @patch('src.api.intelligent_operations_api.get_current_user')
    @patch('src.api.intelligent_operations_api.get_intelligent_operations')
    def test_predictions_endpoint(self, mock_intelligent, mock_auth, client):
        """Test the predictions endpoint."""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock predictions
        mock_prediction = Mock()
        mock_prediction.prediction_id = "pred_001"
        mock_prediction.prediction_type.value = "performance_degradation"
        mock_prediction.target_metric = "cpu_usage"
        mock_prediction.predicted_value = 85.0
        mock_prediction.confidence = 0.8
        mock_prediction.prediction_horizon = 1
        mock_prediction.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_prediction.model_accuracy = 0.75
        
        mock_instance = Mock()
        mock_instance.predictions = {"cpu_usage": mock_prediction}
        mock_intelligent.return_value = mock_instance
        
        # Test the endpoint
        response = client.get("/api/intelligent-operations/predictions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["count"] == 1
    
    @patch('src.api.intelligent_operations_api.get_current_user')
    @patch('src.api.intelligent_operations_api.get_intelligent_operations')
    def test_recommendations_endpoint(self, mock_intelligent, mock_auth, client):
        """Test the recommendations endpoint."""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock recommendation
        mock_rec = Mock()
        mock_rec.recommendation_id = "rec_001"
        mock_rec.recommendation_type.value = "optimize_performance"
        mock_rec.title = "Optimize CPU Usage"
        mock_rec.description = "Reduce CPU usage"
        mock_rec.priority = "high"
        mock_rec.estimated_impact = {"performance": 0.3}
        mock_rec.implementation_effort = "medium"
        mock_rec.timeline = "short_term"
        mock_rec.prerequisites = []
        mock_rec.risks = []
        mock_rec.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_rec.expires_at = None
        
        mock_instance = Mock()
        mock_instance.recommendations = [mock_rec]
        mock_intelligent.return_value = mock_instance
        
        # Test the endpoint
        response = client.get("/api/intelligent-operations/recommendations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert len(data["data"]) == 1
    
    @patch('src.api.intelligent_operations_api.get_current_user')
    @patch('src.api.intelligent_operations_api.get_operations_knowledge')
    def test_search_cases_endpoint(self, mock_knowledge, mock_auth, client):
        """Test the search cases endpoint."""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock case
        mock_case = Mock()
        mock_case.case_id = "case_001"
        mock_case.case_type.value = "fault_resolution"
        mock_case.severity.value = "high"
        mock_case.status.value = "resolved"
        mock_case.title = "Database Issue"
        mock_case.description = "Database connection problem"
        mock_case.symptoms = ["slow queries"]
        mock_case.root_cause = "connection pool exhausted"
        mock_case.resolution_steps = ["increased pool size"]
        mock_case.resolution_time_minutes = 30
        mock_case.tags = {"database", "performance"}
        mock_case.effectiveness_score = 0.9
        mock_case.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_case.updated_at.isoformat.return_value = "2024-01-01T00:30:00"
        mock_case.resolved_at.isoformat.return_value = "2024-01-01T00:30:00"
        
        mock_case_library = Mock()
        mock_case_library.search_cases.return_value = [mock_case]
        
        mock_instance = Mock()
        mock_instance.case_library = mock_case_library
        mock_knowledge.return_value = mock_instance
        
        # Test the endpoint
        response = client.get("/api/intelligent-operations/knowledge/cases?query=database")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert len(data["data"]) == 1
    
    @patch('src.api.intelligent_operations_api.get_current_user')
    @patch('src.api.intelligent_operations_api.get_operations_knowledge')
    def test_search_articles_endpoint(self, mock_knowledge, mock_auth, client):
        """Test the search articles endpoint."""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock article
        mock_article = Mock()
        mock_article.article_id = "art_001"
        mock_article.title = "Performance Guide"
        mock_article.content = "This is a performance optimization guide..."
        mock_article.category = "performance"
        mock_article.tags = {"performance", "optimization"}
        mock_article.author = "expert"
        mock_article.view_count = 10
        mock_article.rating = 4.5
        mock_article.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_article.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        mock_kb = Mock()
        mock_kb.search_articles.return_value = [mock_article]
        
        mock_instance = Mock()
        mock_instance.knowledge_base = mock_kb
        mock_knowledge.return_value = mock_instance
        
        # Test the endpoint
        response = client.get("/api/intelligent-operations/knowledge/articles?query=performance")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert len(data["data"]) == 1
    
    def test_api_endpoint_paths(self):
        """Test that all expected API endpoints are defined."""
        # Get all routes from the router
        routes = [route.path for route in router.routes]
        
        expected_paths = [
            "/status",
            "/insights", 
            "/predictions",
            "/recommendations",
            "/capacity-forecasts",
            "/automation/status",
            "/automation/rules",
            "/automation/history",
            "/knowledge/cases",
            "/knowledge/cases/{case_id}",
            "/knowledge/articles",
            "/decision-support",
            "/knowledge/statistics",
            "/start",
            "/stop"
        ]
        
        for expected_path in expected_paths:
            full_path = f"/api/intelligent-operations{expected_path}"
            # Check if any route matches (considering path parameters)
            path_exists = any(
                expected_path.replace("{case_id}", "{path}") in route or
                expected_path in route
                for route in routes
            )
            assert path_exists, f"Expected path {expected_path} not found in routes"


class TestAPIModels:
    """Test API request/response models."""
    
    def test_prediction_request_model(self):
        """Test PredictionRequest model."""
        from src.api.intelligent_operations_api import PredictionRequest
        
        # Valid request
        request = PredictionRequest(
            metric_name="cpu_usage",
            prediction_horizon_hours=2,
            features={"memory_usage": 70.0}
        )
        
        assert request.metric_name == "cpu_usage"
        assert request.prediction_horizon_hours == 2
        assert request.features["memory_usage"] == 70.0
    
    def test_automation_rule_request_model(self):
        """Test AutomationRuleRequest model."""
        from src.api.intelligent_operations_api import AutomationRuleRequest
        
        # Valid request
        request = AutomationRuleRequest(
            rule_id="test_rule",
            operation_type="scaling",
            automation_level="automatic",
            trigger_conditions={"cpu_threshold": 80.0},
            action_parameters={"scale_factor": 1.5}
        )
        
        assert request.rule_id == "test_rule"
        assert request.operation_type == "scaling"
        assert request.automation_level == "automatic"
        assert request.trigger_conditions["cpu_threshold"] == 80.0
    
    def test_decision_request_model(self):
        """Test DecisionRequest model."""
        from src.api.intelligent_operations_api import DecisionRequest
        
        # Valid request
        request = DecisionRequest(
            situation_id="situation_001",
            description="High CPU usage",
            current_metrics={"cpu_usage": 85.0},
            symptoms=["High CPU", "Slow response"],
            objectives=["Reduce CPU usage"]
        )
        
        assert request.situation_id == "situation_001"
        assert request.description == "High CPU usage"
        assert len(request.current_metrics) == 1
        assert len(request.symptoms) == 2
        assert len(request.objectives) == 1
        assert request.time_pressure == "medium"  # Default value


if __name__ == "__main__":
    pytest.main([__file__])