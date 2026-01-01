"""
Reasoning Chain Unit Tests.

Tests for multi-step reasoning logic, hypothesis verification,
confidence evaluation, and backtracking mechanisms.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.agent.reasoning_chain import (
    ReasoningStepType,
    ReasoningStatus,
    ReasoningStep,
    Hypothesis,
    ReasoningChain,
    ReasoningChainBuilder,
    ReasoningEngine,
    get_reasoning_engine,
    create_analysis_reasoning_chain,
)


# =============================================================================
# ReasoningStep Tests
# =============================================================================

class TestReasoningStep:
    """Tests for ReasoningStep dataclass."""

    def test_step_creation_defaults(self):
        """Test creating a step with default values."""
        step = ReasoningStep()

        assert step.id is not None
        assert step.step_type == ReasoningStepType.OBSERVATION
        assert step.description == ""
        assert step.confidence == 0.0
        assert step.status == ReasoningStatus.PENDING
        assert step.input_data == {}
        assert step.output_data == {}
        assert step.evidence == []
        assert step.dependencies == []

    def test_step_creation_custom(self):
        """Test creating a step with custom values."""
        step = ReasoningStep(
            step_type=ReasoningStepType.INFERENCE,
            description="Derive conclusion from data",
            confidence=0.85,
            reasoning="Based on pattern analysis",
            evidence=["evidence1", "evidence2"]
        )

        assert step.step_type == ReasoningStepType.INFERENCE
        assert step.description == "Derive conclusion from data"
        assert step.confidence == 0.85
        assert len(step.evidence) == 2

    def test_step_to_dict(self):
        """Test converting step to dictionary."""
        step = ReasoningStep(
            step_type=ReasoningStepType.HYPOTHESIS,
            description="Test hypothesis",
            confidence=0.7,
            input_data={"key": "value"},
            output_data={"result": True}
        )

        result = step.to_dict()

        assert result["step_type"] == "hypothesis"
        assert result["description"] == "Test hypothesis"
        assert result["confidence"] == 0.7
        assert result["input_data"] == {"key": "value"}
        assert result["output_data"] == {"result": True}
        assert "timestamp" in result

    def test_step_with_error(self):
        """Test step with error message."""
        step = ReasoningStep(
            status=ReasoningStatus.FAILED,
            error_message="Execution failed"
        )

        assert step.status == ReasoningStatus.FAILED
        assert step.error_message == "Execution failed"


# =============================================================================
# Hypothesis Tests
# =============================================================================

class TestHypothesis:
    """Tests for Hypothesis class."""

    def test_hypothesis_creation(self):
        """Test creating a hypothesis."""
        hypothesis = Hypothesis(
            statement="Data shows increasing trend"
        )

        assert hypothesis.id is not None
        assert hypothesis.statement == "Data shows increasing trend"
        assert hypothesis.confidence == 0.0
        assert hypothesis.verified is False
        assert hypothesis.verification_result is None

    def test_calculate_confidence_no_evidence(self):
        """Test confidence calculation with no evidence."""
        hypothesis = Hypothesis(statement="Test")

        confidence = hypothesis.calculate_confidence()

        assert confidence == 0.5  # Neutral confidence

    def test_calculate_confidence_only_supporting(self):
        """Test confidence with only supporting evidence."""
        hypothesis = Hypothesis(
            statement="Test",
            supporting_evidence=["ev1", "ev2", "ev3"]
        )

        confidence = hypothesis.calculate_confidence()

        assert confidence > 0.5
        assert confidence <= 1.0

    def test_calculate_confidence_only_contradicting(self):
        """Test confidence with only contradicting evidence."""
        hypothesis = Hypothesis(
            statement="Test",
            contradicting_evidence=["ev1", "ev2"]
        )

        confidence = hypothesis.calculate_confidence()

        assert confidence < 0.5
        assert confidence >= 0.0

    def test_calculate_confidence_mixed_evidence(self):
        """Test confidence with mixed evidence."""
        hypothesis = Hypothesis(
            statement="Test",
            supporting_evidence=["ev1", "ev2", "ev3"],
            contradicting_evidence=["ev4"]
        )

        confidence = hypothesis.calculate_confidence()

        # More supporting than contradicting, should be > 0.5
        assert confidence > 0.5

    def test_calculate_confidence_more_evidence_higher_weight(self):
        """Test that more evidence increases confidence weight."""
        # Fewer pieces of evidence
        h1 = Hypothesis(
            statement="Test",
            supporting_evidence=["ev1"]
        )

        # More pieces of evidence
        h2 = Hypothesis(
            statement="Test",
            supporting_evidence=["ev1", "ev2", "ev3", "ev4", "ev5"]
        )

        c1 = h1.calculate_confidence()
        c2 = h2.calculate_confidence()

        # More evidence should give higher confidence
        assert c2 >= c1


# =============================================================================
# ReasoningChain Tests
# =============================================================================

class TestReasoningChain:
    """Tests for ReasoningChain class."""

    def test_chain_creation(self):
        """Test creating a reasoning chain."""
        chain = ReasoningChain(
            name="Test Chain",
            goal="Analyze data",
            description="Test description"
        )

        assert chain.id is not None
        assert chain.name == "Test Chain"
        assert chain.goal == "Analyze data"
        assert chain.status == ReasoningStatus.PENDING
        assert chain.steps == []
        assert chain.hypotheses == []
        assert chain.current_step_index == 0

    def test_add_step(self):
        """Test adding steps to chain."""
        chain = ReasoningChain(name="Test")
        step1 = ReasoningStep(description="Step 1")
        step2 = ReasoningStep(description="Step 2")

        chain.add_step(step1)
        chain.add_step(step2)

        assert len(chain.steps) == 2
        assert chain.steps[0].description == "Step 1"
        assert chain.steps[1].description == "Step 2"

    def test_get_current_step(self):
        """Test getting current step."""
        chain = ReasoningChain(name="Test")
        step1 = ReasoningStep(description="Step 1")
        step2 = ReasoningStep(description="Step 2")
        chain.add_step(step1)
        chain.add_step(step2)

        current = chain.get_current_step()

        assert current == step1

    def test_get_current_step_empty_chain(self):
        """Test getting current step from empty chain."""
        chain = ReasoningChain(name="Test")

        current = chain.get_current_step()

        assert current is None

    def test_advance(self):
        """Test advancing to next step."""
        chain = ReasoningChain(name="Test")
        chain.add_step(ReasoningStep(description="Step 1"))
        chain.add_step(ReasoningStep(description="Step 2"))

        result = chain.advance()

        assert result is True
        assert chain.current_step_index == 1
        assert chain.get_current_step().description == "Step 2"

    def test_advance_at_end(self):
        """Test advancing when at end of chain."""
        chain = ReasoningChain(name="Test")
        chain.add_step(ReasoningStep(description="Step 1"))
        chain.current_step_index = 0

        result = chain.advance()

        assert result is False
        assert chain.current_step_index == 0

    def test_backtrack(self):
        """Test backtracking to previous step."""
        chain = ReasoningChain(name="Test")
        step1 = ReasoningStep(description="Step 1")
        step2 = ReasoningStep(description="Step 2", status=ReasoningStatus.IN_PROGRESS)
        chain.add_step(step1)
        chain.add_step(step2)
        chain.current_step_index = 1

        result = chain.backtrack("Low confidence")

        assert result is True
        assert chain.current_step_index == 0
        assert len(chain.backtrack_history) == 1
        assert chain.backtrack_history[0] == (1, "Low confidence")
        assert step2.status == ReasoningStatus.BACKTRACKED

    def test_backtrack_at_start(self):
        """Test backtracking when at start of chain."""
        chain = ReasoningChain(name="Test")
        chain.add_step(ReasoningStep(description="Step 1"))

        result = chain.backtrack("No reason")

        assert result is False
        assert chain.current_step_index == 0
        assert len(chain.backtrack_history) == 0

    def test_calculate_overall_confidence_empty(self):
        """Test overall confidence for empty chain."""
        chain = ReasoningChain(name="Test")

        confidence = chain.calculate_overall_confidence()

        assert confidence == 0.0

    def test_calculate_overall_confidence_no_completed(self):
        """Test overall confidence with no completed steps."""
        chain = ReasoningChain(name="Test")
        chain.add_step(ReasoningStep(description="Step 1", status=ReasoningStatus.PENDING))

        confidence = chain.calculate_overall_confidence()

        assert confidence == 0.0

    def test_calculate_overall_confidence_completed_steps(self):
        """Test overall confidence with completed steps."""
        chain = ReasoningChain(name="Test")
        chain.add_step(ReasoningStep(
            description="Step 1",
            status=ReasoningStatus.COMPLETED,
            confidence=0.8
        ))
        chain.add_step(ReasoningStep(
            description="Step 2",
            status=ReasoningStatus.COMPLETED,
            confidence=0.9
        ))

        confidence = chain.calculate_overall_confidence()

        assert confidence > 0.0
        assert confidence <= 1.0
        # Later steps weighted more heavily
        assert chain.overall_confidence == confidence

    def test_to_dict(self):
        """Test converting chain to dictionary."""
        chain = ReasoningChain(
            name="Test Chain",
            goal="Test Goal",
            description="Test Description"
        )
        chain.add_step(ReasoningStep(description="Step 1"))
        chain.hypotheses.append(Hypothesis(statement="Test hypothesis"))

        result = chain.to_dict()

        assert result["name"] == "Test Chain"
        assert result["goal"] == "Test Goal"
        assert len(result["steps"]) == 1
        assert len(result["hypotheses"]) == 1
        assert "created_at" in result


# =============================================================================
# ReasoningChainBuilder Tests
# =============================================================================

class TestReasoningChainBuilder:
    """Tests for ReasoningChainBuilder class."""

    def test_create_chain(self):
        """Test creating a chain with builder."""
        builder = ReasoningChainBuilder()

        chain = builder.create_chain(
            name="Test Chain",
            goal="Analyze data",
            description="Test description"
        )

        assert chain.name == "Test Chain"
        assert chain.goal == "Analyze data"
        assert builder.chain == chain

    def test_add_observation_step(self):
        """Test adding observation step."""
        builder = ReasoningChainBuilder()
        builder.create_chain("Test", "Goal")

        step = builder.add_observation_step(
            description="Observe input",
            input_data={"key": "value"}
        )

        assert step.step_type == ReasoningStepType.OBSERVATION
        assert step.description == "Observe input"
        assert step.input_data == {"key": "value"}
        assert len(builder.chain.steps) == 1

    def test_add_hypothesis_step(self):
        """Test adding hypothesis step."""
        builder = ReasoningChainBuilder()
        builder.create_chain("Test", "Goal")

        step = builder.add_hypothesis_step(
            statement="Data shows trend",
            based_on=["step_1"]
        )

        assert step.step_type == ReasoningStepType.HYPOTHESIS
        assert "hypothesis_id" in step.metadata
        assert len(builder.chain.hypotheses) == 1
        assert builder.chain.hypotheses[0].statement == "Data shows trend"

    def test_add_inference_step(self):
        """Test adding inference step."""
        builder = ReasoningChainBuilder()
        builder.create_chain("Test", "Goal")

        step = builder.add_inference_step(
            description="Derive insights",
            inference_logic="Apply pattern matching",
            dependencies=["step_1"]
        )

        assert step.step_type == ReasoningStepType.INFERENCE
        assert step.reasoning == "Apply pattern matching"
        assert step.dependencies == ["step_1"]

    def test_add_verification_step(self):
        """Test adding verification step."""
        builder = ReasoningChainBuilder()
        builder.create_chain("Test", "Goal")

        step = builder.add_verification_step(
            hypothesis_id="hyp_001",
            verification_method="evidence_based"
        )

        assert step.step_type == ReasoningStepType.VERIFICATION
        assert step.input_data["hypothesis_id"] == "hyp_001"
        assert step.input_data["method"] == "evidence_based"

    def test_add_conclusion_step(self):
        """Test adding conclusion step."""
        builder = ReasoningChainBuilder()
        builder.create_chain("Test", "Goal")

        step = builder.add_conclusion_step(
            description="Final conclusion",
            dependencies=["step_1", "step_2"]
        )

        assert step.step_type == ReasoningStepType.CONCLUSION
        assert step.description == "Final conclusion"
        assert step.dependencies == ["step_1", "step_2"]

    def test_register_step_executor(self):
        """Test registering custom step executor."""
        builder = ReasoningChainBuilder()

        def custom_executor(step):
            return {"custom": True}

        builder.register_step_executor(
            ReasoningStepType.OBSERVATION,
            custom_executor
        )

        assert ReasoningStepType.OBSERVATION in builder.step_executors

    def test_register_hypothesis_verifier(self):
        """Test registering hypothesis verifier."""
        builder = ReasoningChainBuilder()

        def custom_verifier(hypothesis, context):
            return True, 0.9, "Verified"

        builder.register_hypothesis_verifier(custom_verifier)

        assert len(builder.hypothesis_verifiers) == 1


# =============================================================================
# ReasoningEngine Tests
# =============================================================================

class TestReasoningEngine:
    """Tests for ReasoningEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a reasoning engine for testing."""
        return ReasoningEngine()

    @pytest.fixture
    def simple_chain(self):
        """Create a simple reasoning chain for testing."""
        builder = ReasoningChainBuilder()
        chain = builder.create_chain(
            name="Test Chain",
            goal="Test analysis"
        )
        builder.add_observation_step(
            description="Observe data",
            input_data={"value": 42}
        )
        builder.add_conclusion_step(
            description="Draw conclusion"
        )
        return chain

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.active_chains == {}
        assert engine.completed_chains == []
        assert len(engine.step_executors) == 5  # Default executors

    def test_execute_observation_step(self, engine):
        """Test executing observation step."""
        step = ReasoningStep(
            step_type=ReasoningStepType.OBSERVATION,
            input_data={"field1": 100, "field2": "text"}
        )
        context = {"chain": None}

        result = engine._execute_observation(step, context)

        assert "data_type" in result
        assert "key_fields" in result
        assert "field1" in result["key_fields"]
        assert "field2" in result["key_fields"]
        assert step.confidence == 0.9  # High confidence for observations

    def test_execute_hypothesis_step(self, engine):
        """Test executing hypothesis step."""
        step = ReasoningStep(
            step_type=ReasoningStepType.HYPOTHESIS,
            input_data={"statement": "Data is valid"}
        )
        completed_step = ReasoningStep(
            status=ReasoningStatus.COMPLETED,
            description="Prior observation"
        )
        context = {"completed_steps": [completed_step]}

        result = engine._execute_hypothesis(step, context)

        assert result["hypothesis"] == "Data is valid"
        assert "supporting_evidence" in result
        assert step.confidence >= 0.5

    def test_execute_inference_step(self, engine):
        """Test executing inference step."""
        obs_step = ReasoningStep(
            id="obs_1",
            status=ReasoningStatus.COMPLETED,
            output_data={"observed_patterns": ["numeric_value"]}
        )
        step = ReasoningStep(
            step_type=ReasoningStepType.INFERENCE,
            input_data={"logic": "Pattern analysis"},
            dependencies=["obs_1"]
        )
        context = {"completed_steps": [obs_step]}

        result = engine._execute_inference(step, context)

        assert result["inference_logic"] == "Pattern analysis"
        assert "derived_conclusions" in result

    def test_execute_verification_step(self, engine):
        """Test executing verification step."""
        hypothesis = Hypothesis(
            id="hyp_1",
            statement="Test hypothesis",
            supporting_evidence=["ev1", "ev2", "ev3"]
        )
        chain = ReasoningChain(name="Test")
        chain.hypotheses.append(hypothesis)

        step = ReasoningStep(
            step_type=ReasoningStepType.VERIFICATION,
            input_data={"hypothesis_id": "hyp_1", "method": "evidence_based"}
        )
        context = {"chain": chain}

        result = engine._execute_verification(step, context)

        assert result["hypothesis_id"] == "hyp_1"
        assert "verified" in result
        assert "confidence" in result
        assert hypothesis.verified is True

    def test_execute_conclusion_step(self, engine):
        """Test executing conclusion step."""
        hypothesis = Hypothesis(
            id="hyp_1",
            statement="Test hypothesis",
            verified=True,
            verification_result=True
        )
        chain = ReasoningChain(name="Test")
        chain.hypotheses.append(hypothesis)
        chain.add_step(ReasoningStep(
            step_type=ReasoningStepType.INFERENCE,
            status=ReasoningStatus.COMPLETED,
            output_data={"derived_conclusions": ["Insight 1"]}
        ))

        step = ReasoningStep(
            step_type=ReasoningStepType.CONCLUSION,
            description="Final conclusion"
        )
        context = {"chain": chain}

        result = engine._execute_conclusion(step, context)

        assert result["summary"] == "Final conclusion"
        assert "Test hypothesis" in result["verified_hypotheses"]
        assert len(result["key_insights"]) > 0

    def test_execute_chain_success(self, engine, simple_chain):
        """Test successful chain execution."""
        result = engine.execute_chain(simple_chain)

        assert result.status == ReasoningStatus.COMPLETED
        assert result.completed_at is not None
        assert result.total_execution_time > 0
        assert result in engine.completed_chains

    def test_execute_chain_with_backtracking(self, engine):
        """Test chain execution with backtracking."""
        builder = ReasoningChainBuilder()
        chain = builder.create_chain("Test", "Goal")

        # Add step that will have low confidence
        step = builder.add_observation_step(
            description="Low confidence observation",
            input_data={}
        )
        builder.add_conclusion_step(description="Conclusion")

        # Force low confidence
        engine.backtrack_threshold = 0.95  # Higher threshold to trigger backtrack

        result = engine.execute_chain(chain)

        # Chain should still complete
        assert result.status == ReasoningStatus.COMPLETED

    def test_get_chain_summary(self, engine, simple_chain):
        """Test getting chain summary."""
        executed_chain = engine.execute_chain(simple_chain)

        summary = engine.get_chain_summary(executed_chain)

        assert summary["chain_id"] == executed_chain.id
        assert summary["name"] == "Test Chain"
        assert summary["status"] == "completed"
        assert "step_summary" in summary
        assert "execution_time" in summary


# =============================================================================
# Global Function Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_reasoning_engine(self):
        """Test getting global reasoning engine."""
        engine1 = get_reasoning_engine()
        engine2 = get_reasoning_engine()

        assert engine1 is engine2
        assert isinstance(engine1, ReasoningEngine)

    def test_create_analysis_reasoning_chain(self):
        """Test creating analysis reasoning chain."""
        chain = create_analysis_reasoning_chain(
            query="What is the trend in sales data?",
            data={"sales": [100, 150, 200]},
            analysis_type="trend"
        )

        assert chain.name.startswith("Analysis:")
        assert len(chain.steps) == 5  # observation, hypothesis, inference, verification, conclusion
        assert len(chain.hypotheses) == 1

        # Check step types
        step_types = [s.step_type for s in chain.steps]
        assert ReasoningStepType.OBSERVATION in step_types
        assert ReasoningStepType.HYPOTHESIS in step_types
        assert ReasoningStepType.INFERENCE in step_types
        assert ReasoningStepType.VERIFICATION in step_types
        assert ReasoningStepType.CONCLUSION in step_types


# =============================================================================
# Property-Based Tests (Conceptual)
# =============================================================================

class TestReasoningChainProperties:
    """Property-based tests for reasoning chain behavior."""

    def test_confidence_monotonicity_with_supporting_evidence(self):
        """Property: Confidence should increase with more supporting evidence."""
        h1 = Hypothesis(statement="Test", supporting_evidence=["e1"])
        h2 = Hypothesis(statement="Test", supporting_evidence=["e1", "e2"])
        h3 = Hypothesis(statement="Test", supporting_evidence=["e1", "e2", "e3"])

        c1 = h1.calculate_confidence()
        c2 = h2.calculate_confidence()
        c3 = h3.calculate_confidence()

        # More evidence should give higher or equal confidence
        assert c2 >= c1
        assert c3 >= c2

    def test_hypothesis_verification_consistency(self):
        """Property: Same hypothesis with same evidence should give same result."""
        def create_hypothesis():
            return Hypothesis(
                statement="Data is valid",
                supporting_evidence=["ev1", "ev2"],
                contradicting_evidence=["ev3"]
            )

        h1 = create_hypothesis()
        h2 = create_hypothesis()

        c1 = h1.calculate_confidence()
        c2 = h2.calculate_confidence()

        assert c1 == c2

    def test_chain_convergence(self):
        """Property: Chain should eventually reach a conclusion."""
        engine = ReasoningEngine()
        builder = ReasoningChainBuilder()

        chain = builder.create_chain("Test", "Goal")
        builder.add_observation_step("Observe", {"data": 1})
        builder.add_inference_step("Infer", "logic")
        builder.add_conclusion_step("Conclude")

        result = engine.execute_chain(chain)

        # Chain should reach conclusion (completed or failed, not stuck)
        assert result.status in [ReasoningStatus.COMPLETED, ReasoningStatus.FAILED]
        assert result.current_step_index >= 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestReasoningChainIntegration:
    """Integration tests for reasoning chain."""

    def test_full_reasoning_flow(self):
        """Test complete reasoning flow from start to finish."""
        engine = ReasoningEngine()
        builder = ReasoningChainBuilder()

        # Create chain
        chain = builder.create_chain(
            name="Data Analysis",
            goal="Determine if sales are increasing"
        )

        # Add steps
        obs = builder.add_observation_step(
            description="Observe sales data",
            input_data={"sales": [100, 120, 150, 180]}
        )

        hyp = builder.add_hypothesis_step(
            statement="Sales are increasing over time",
            based_on=[obs.id]
        )

        inf = builder.add_inference_step(
            description="Analyze trend",
            inference_logic="Compare consecutive values",
            dependencies=[obs.id]
        )

        ver = builder.add_verification_step(
            hypothesis_id=chain.hypotheses[0].id,
            verification_method="trend_analysis",
            dependencies=[inf.id]
        )

        builder.add_conclusion_step(
            description="Determine sales trend",
            dependencies=[ver.id]
        )

        # Add supporting evidence to hypothesis
        chain.hypotheses[0].supporting_evidence = [
            "Each value is higher than previous",
            "Growth rate is positive"
        ]

        # Execute
        result = engine.execute_chain(chain)

        # Verify
        assert result.status == ReasoningStatus.COMPLETED
        assert result.conclusion is not None
        assert result.overall_confidence > 0

        # Check summary
        summary = engine.get_chain_summary(result)
        assert summary["completed_steps"] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
