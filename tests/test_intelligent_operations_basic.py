"""
Basic tests for Intelligent Operations System (without sklearn dependencies).

Tests core functionality that doesn't require machine learning libraries.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Test basic components that don't require sklearn
from src.system.operations_knowledge_base import (
    OperationsKnowledgeSystem, CaseLibrary, KnowledgeBase,
    OperationalCase, CaseType, CaseSeverity, CaseStatus,
    KnowledgeArticle, DecisionContext
)


class TestOperationalCase:
    """Test operational case functionality."""
    
    def test_case_creation(self):
        """Test creating an operational case."""
        case = OperationalCase(
            case_id="test_001",
            case_type=CaseType.FAULT_RESOLUTION,
            severity=CaseSeverity.HIGH,
            status=CaseStatus.OPEN,
            title="Test Case",
            description="Test case description",
            symptoms=["symptom1", "symptom2"],
            tags={"test", "demo"}
        )
        
        assert case.case_id == "test_001"
        assert case.case_type == CaseType.FAULT_RESOLUTION
        assert case.severity == CaseSeverity.HIGH
        assert case.status == CaseStatus.OPEN
        assert len(case.symptoms) == 2
        assert "test" in case.tags
    
    def test_case_resolution(self):
        """Test case resolution."""
        case = OperationalCase(
            case_id="test_002",
            case_type=CaseType.PERFORMANCE_OPTIMIZATION,
            severity=CaseSeverity.MEDIUM,
            status=CaseStatus.IN_PROGRESS,
            title="Performance Issue",
            description="System performance degradation"
        )
        
        # Resolve the case
        case.status = CaseStatus.RESOLVED
        case.resolved_at = datetime.utcnow()
        case.resolution_steps = ["Step 1", "Step 2", "Step 3"]
        case.resolution_time_minutes = 45
        case.effectiveness_score = 0.8
        
        assert case.status == CaseStatus.RESOLVED
        assert case.resolved_at is not None
        assert len(case.resolution_steps) == 3
        assert case.effectiveness_score == 0.8


class TestKnowledgeArticle:
    """Test knowledge article functionality."""
    
    def test_article_creation(self):
        """Test creating a knowledge article."""
        article = KnowledgeArticle(
            article_id="kb_001",
            title="Troubleshooting Guide",
            content="This is a comprehensive troubleshooting guide...",
            category="troubleshooting",
            tags={"guide", "troubleshooting", "performance"},
            author="system_admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert article.article_id == "kb_001"
        assert article.title == "Troubleshooting Guide"
        assert article.category == "troubleshooting"
        assert "guide" in article.tags
        assert article.view_count == 0
        assert article.rating == 0.0
    
    def test_article_usage_tracking(self):
        """Test article usage tracking."""
        article = KnowledgeArticle(
            article_id="kb_002",
            title="Performance Optimization",
            content="Performance optimization techniques...",
            category="performance",
            tags={"performance", "optimization"},
            author="expert",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Simulate usage
        article.view_count += 1
        article.rating = 4.5
        
        assert article.view_count == 1
        assert article.rating == 4.5


class TestDecisionContext:
    """Test decision context functionality."""
    
    def test_decision_context_creation(self):
        """Test creating a decision context."""
        context = DecisionContext(
            situation_id="decision_001",
            description="High CPU usage requiring immediate action",
            current_metrics={
                "cpu_usage_percent": 85.0,
                "memory_usage_percent": 70.0,
                "response_time_ms": 2500
            },
            symptoms=["High CPU usage", "Slow response times", "Increased errors"],
            constraints={"budget": "limited", "downtime": "not_allowed"},
            objectives=["Reduce CPU usage", "Improve response time"],
            time_pressure="high",
            risk_tolerance="medium"
        )
        
        assert context.situation_id == "decision_001"
        assert len(context.current_metrics) == 3
        assert len(context.symptoms) == 3
        assert len(context.objectives) == 2
        assert context.time_pressure == "high"
        assert context.risk_tolerance == "medium"


class TestCaseLibraryBasic:
    """Test basic case library functionality without database."""
    
    @pytest.fixture
    def mock_case_library(self):
        """Create a mock case library for testing."""
        # Mock the database initialization
        with patch('sqlite3.connect'):
            case_library = CaseLibrary(":memory:")
            case_library.cases = {}  # Reset to empty for testing
            case_library.case_index = {}
            return case_library
    
    def test_case_indexing(self, mock_case_library):
        """Test case indexing functionality."""
        case = OperationalCase(
            case_id="idx_001",
            case_type=CaseType.FAULT_RESOLUTION,
            severity=CaseSeverity.HIGH,
            status=CaseStatus.RESOLVED,
            title="Database Connection Issue",
            description="Database connection pool exhausted",
            tags={"database", "connection", "performance"}
        )
        
        # Add case to memory (skip database)
        mock_case_library.cases[case.case_id] = case
        mock_case_library._update_index(case)
        
        # Check indexing
        assert case.case_id in mock_case_library.case_index["database"]
        assert case.case_id in mock_case_library.case_index["connection"]
        assert case.case_id in mock_case_library.case_index["fault_resolution"]
        assert case.case_id in mock_case_library.case_index["high"]
    
    def test_text_similarity_calculation(self, mock_case_library):
        """Test text similarity calculation."""
        text1 = ["high cpu usage", "performance degradation"]
        text2 = ["cpu usage high", "slow performance"]
        
        similarity = mock_case_library._calculate_text_similarity(text1, text2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0  # Should have some similarity due to common words
    
    def test_metric_similarity_calculation(self, mock_case_library):
        """Test metric similarity calculation."""
        metrics1 = {"cpu_usage": 85.0, "memory_usage": 70.0}
        metrics2 = {"cpu_usage": 80.0, "memory_usage": 75.0}
        
        similarity = mock_case_library._calculate_metric_similarity(metrics1, metrics2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0.8  # Should be high similarity for close values
    
    def test_empty_similarity_calculation(self, mock_case_library):
        """Test similarity calculation with empty inputs."""
        # Empty lists should return 0 similarity
        assert mock_case_library._calculate_text_similarity([], ["test"]) == 0.0
        assert mock_case_library._calculate_text_similarity(["test"], []) == 0.0
        
        # Empty metrics should return 0 similarity
        assert mock_case_library._calculate_metric_similarity({}, {"test": 1.0}) == 0.0
        assert mock_case_library._calculate_metric_similarity({"test": 1.0}, {}) == 0.0


class TestKnowledgeBaseBasic:
    """Test basic knowledge base functionality without database."""
    
    @pytest.fixture
    def mock_knowledge_base(self):
        """Create a mock knowledge base for testing."""
        with patch('sqlite3.connect'):
            kb = KnowledgeBase(":memory:")
            kb.articles = {}  # Reset to empty for testing
            kb.article_index = {}
            return kb
    
    def test_article_indexing(self, mock_knowledge_base):
        """Test article indexing functionality."""
        article = KnowledgeArticle(
            article_id="art_001",
            title="CPU Optimization Guide",
            content="Guide for optimizing CPU usage...",
            category="performance",
            tags={"cpu", "optimization", "performance"},
            author="expert",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add article to memory (skip database)
        mock_knowledge_base.articles[article.article_id] = article
        mock_knowledge_base._update_article_index(article)
        
        # Check indexing
        assert article.article_id in mock_knowledge_base.article_index["cpu"]
        assert article.article_id in mock_knowledge_base.article_index["optimization"]
        assert article.article_id in mock_knowledge_base.article_index["performance"]


class TestOperationsKnowledgeSystemBasic:
    """Test basic operations knowledge system functionality."""
    
    @pytest.fixture
    def mock_knowledge_system(self, tmp_path):
        """Create a mock knowledge system for testing."""
        with patch('sqlite3.connect'):
            # Use temporary directory for testing
            system = OperationsKnowledgeSystem(str(tmp_path))
            return system
    
    def test_system_initialization(self, mock_knowledge_system):
        """Test system initialization."""
        assert mock_knowledge_system.case_library is not None
        assert mock_knowledge_system.knowledge_base is not None
        assert mock_knowledge_system.decision_support is not None
        assert mock_knowledge_system.learning_enabled is True
        assert mock_knowledge_system.auto_case_creation is True
    
    def test_fault_type_conversion(self, mock_knowledge_system):
        """Test fault type to case type conversion."""
        from src.system.fault_detection_system import FaultType
        
        # Test various fault type conversions
        assert mock_knowledge_system._fault_type_to_case_type(
            FaultType.SERVICE_UNAVAILABLE
        ) == CaseType.FAULT_RESOLUTION
        
        assert mock_knowledge_system._fault_type_to_case_type(
            FaultType.PERFORMANCE_DEGRADATION
        ) == CaseType.PERFORMANCE_OPTIMIZATION
        
        assert mock_knowledge_system._fault_type_to_case_type(
            FaultType.SECURITY_BREACH
        ) == CaseType.SECURITY_INCIDENT
    
    def test_severity_conversion(self, mock_knowledge_system):
        """Test fault severity to case severity conversion."""
        from src.system.fault_detection_system import FaultSeverity
        
        # Test severity conversions
        assert mock_knowledge_system._fault_severity_to_case_severity(
            FaultSeverity.LOW
        ) == CaseSeverity.LOW
        
        assert mock_knowledge_system._fault_severity_to_case_severity(
            FaultSeverity.HIGH
        ) == CaseSeverity.HIGH
        
        assert mock_knowledge_system._fault_severity_to_case_severity(
            FaultSeverity.CRITICAL
        ) == CaseSeverity.CRITICAL
    
    def test_get_system_insights_structure(self, mock_knowledge_system):
        """Test system insights structure."""
        insights = mock_knowledge_system.get_system_insights()
        
        # Check required fields
        assert "timestamp" in insights
        assert "case_library" in insights
        assert "knowledge_base" in insights
        assert "decision_support" in insights
        assert "learning_status" in insights
        
        # Check learning status
        learning_status = insights["learning_status"]
        assert "learning_enabled" in learning_status
        assert "auto_case_creation" in learning_status
        assert learning_status["learning_enabled"] is True
        assert learning_status["auto_case_creation"] is True


class TestEnumValues:
    """Test enum values and conversions."""
    
    def test_case_type_values(self):
        """Test CaseType enum values."""
        assert CaseType.FAULT_RESOLUTION.value == "fault_resolution"
        assert CaseType.PERFORMANCE_OPTIMIZATION.value == "performance_optimization"
        assert CaseType.CAPACITY_PLANNING.value == "capacity_planning"
        assert CaseType.SECURITY_INCIDENT.value == "security_incident"
        assert CaseType.MAINTENANCE_PROCEDURE.value == "maintenance_procedure"
        assert CaseType.CONFIGURATION_CHANGE.value == "configuration_change"
    
    def test_case_severity_values(self):
        """Test CaseSeverity enum values."""
        assert CaseSeverity.LOW.value == "low"
        assert CaseSeverity.MEDIUM.value == "medium"
        assert CaseSeverity.HIGH.value == "high"
        assert CaseSeverity.CRITICAL.value == "critical"
    
    def test_case_status_values(self):
        """Test CaseStatus enum values."""
        assert CaseStatus.OPEN.value == "open"
        assert CaseStatus.IN_PROGRESS.value == "in_progress"
        assert CaseStatus.RESOLVED.value == "resolved"
        assert CaseStatus.CLOSED.value == "closed"


if __name__ == "__main__":
    pytest.main([__file__])