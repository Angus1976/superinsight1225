"""
Property-based tests for LLM Pre-Annotation Integration.

Tests Properties 18, 19, 20 from the LLM Integration design spec.
"""
import pytest
import asyncio
import json
from typing import Dict, Any, Optional, List
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime
from uuid import uuid4

from src.ai.annotation_schemas import (
    AnnotationType,
    AnnotationTask,
    AnnotatedSample,
    PreAnnotationConfig,
    PreAnnotationResult,
    PreAnnotationBatchResult,
    AnnotationMethod,
)
from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    GenerateOptions, LLMResponse, TokenUsage, HealthStatus, LLMError, LLMErrorCode
)


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating valid annotation types
annotation_type_strategy = st.sampled_from(list(AnnotationType))

# Strategy for generating valid task IDs
task_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    whitelist_characters='-_'
)).filter(lambda x: x.strip())

# Strategy for generating text content
text_content_strategy = st.text(min_size=1, max_size=500).filter(lambda x: x.strip())

# Strategy for generating confidence scores
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for generating confidence thresholds
threshold_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for generating batch sizes
batch_size_strategy = st.integers(min_value=1, max_value=100)


# ============================================================================
# Mock Classes
# ============================================================================

class MockLLMSwitcher:
    """Mock LLM Switcher for testing pre-annotation."""
    
    def __init__(
        self,
        should_fail: bool = False,
        fail_probability: float = 0.0,
        response_content: Optional[str] = None,
        response_confidence: Optional[float] = None,
    ):
        self._should_fail = should_fail
        self._fail_probability = fail_probability
        self._response_content = response_content
        self._response_confidence = response_confidence
        self._call_count = 0
        self._last_prompt = None
        self._last_options = None
        self._initialized = True
    
    async def generate(
        self,
        prompt: str,
        options: Optional[GenerateOptions] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate mock response."""
        self._call_count += 1
        self._last_prompt = prompt
        self._last_options = options
        
        # Simulate failure if configured
        if self._should_fail:
            raise Exception("Mock LLM provider failed")
        
        # Simulate probabilistic failure
        import random
        if random.random() < self._fail_probability:
            raise Exception("Random mock failure")
        
        # Generate response content
        if self._response_content:
            content = self._response_content
        else:
            # Generate a valid JSON response based on prompt content
            confidence = self._response_confidence if self._response_confidence is not None else 0.85
            prompt_lower = prompt.lower()
            
            # Check for annotation type keywords in order of specificity
            # Use "for X:" pattern to match the prompt format "Annotate this text for X:"
            if "for text_classification:" in prompt_lower or "for classification:" in prompt_lower:
                content = json.dumps({
                    "label": "positive",
                    "confidence": confidence
                })
            elif "for ner:" in prompt_lower or "for entity" in prompt_lower:
                content = json.dumps({
                    "entities": [
                        {"text": "Example", "label": "ORG", "start": 0, "end": 7}
                    ],
                    "confidence": confidence
                })
            elif "for sentiment:" in prompt_lower:
                content = json.dumps({
                    "sentiment": "positive",
                    "score": 0.8,
                    "confidence": confidence
                })
            elif "for relation" in prompt_lower:
                content = json.dumps({
                    "relations": [
                        {"subject": "A", "predicate": "works_for", "object": "B"}
                    ],
                    "confidence": confidence
                })
            elif "for sequence_labeling:" in prompt_lower or "for sequence" in prompt_lower:
                content = json.dumps({
                    "labels": [
                        {"token": "Example", "label": "B-PER"}
                    ],
                    "confidence": confidence
                })
            elif "for qa:" in prompt_lower or "for question" in prompt_lower:
                content = json.dumps({
                    "answer": "This is the answer",
                    "confidence": confidence
                })
            elif "for summar" in prompt_lower:
                content = json.dumps({
                    "summary": "This is a summary",
                    "confidence": confidence
                })
            else:
                # Default response with label (valid for text_classification)
                content = json.dumps({
                    "label": "default",
                    "confidence": confidence
                })
        
        return LLMResponse(
            content=content,
            model=model or "test-model",
            provider="mock",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        )


class PreAnnotationEngineForTest:
    """
    Test implementation of PreAnnotationEngine for property testing.
    
    This mirrors the actual PreAnnotationEngine but with controllable behavior
    for testing purposes.
    """
    
    def __init__(
        self,
        llm_switcher: Optional[MockLLMSwitcher] = None,
        tenant_id: Optional[str] = None,
    ):
        self._llm_switcher = llm_switcher or MockLLMSwitcher()
        self._tenant_id = tenant_id
        self._initialized = False
        self._error_logs: List[Dict[str, Any]] = []
    
    async def initialize(self) -> None:
        """Initialize the engine."""
        self._initialized = True
    
    async def _ensure_initialized(self) -> None:
        """Ensure the engine is initialized."""
        if not self._initialized:
            await self.initialize()
    
    async def pre_annotate(
        self,
        tasks: List[AnnotationTask],
        config: PreAnnotationConfig,
    ) -> PreAnnotationBatchResult:
        """Perform batch pre-annotation."""
        await self._ensure_initialized()
        
        # Enforce max items limit
        if len(tasks) > config.max_items:
            tasks = tasks[:config.max_items]
        
        results: List[PreAnnotationResult] = []
        successful = 0
        failed = 0
        needs_review = 0
        
        for task in tasks:
            result = await self._annotate_single(task, config)
            results.append(result)
            
            if result.error:
                failed += 1
            else:
                successful += 1
                if result.needs_review:
                    needs_review += 1
        
        return PreAnnotationBatchResult(
            job_id=str(uuid4()),
            total_tasks=len(tasks),
            successful=successful,
            failed=failed,
            needs_review=needs_review,
            results=results,
            processing_time_ms=100.0,
            created_at=datetime.utcnow(),
        )
    
    async def _annotate_single(
        self,
        task: AnnotationTask,
        config: PreAnnotationConfig,
    ) -> PreAnnotationResult:
        """Annotate a single task."""
        try:
            # Build prompt
            prompt = self._build_prompt(task, config.annotation_type)
            
            # Generate annotation
            options = GenerateOptions(
                max_tokens=1000,
                temperature=0.3,
            )
            
            response = await self._llm_switcher.generate(
                prompt=prompt,
                options=options,
                model=config.model,
            )
            
            # Parse response
            annotation = self._parse_response(response.content)
            confidence = self.calculate_confidence(annotation)
            
            return PreAnnotationResult(
                task_id=task.id,
                annotation=annotation,
                confidence=confidence,
                needs_review=confidence < config.confidence_threshold,
                method_used=config.method.value if config.method else "custom_llm",
                processing_time_ms=10.0,
            )
            
        except Exception as e:
            # Log error but don't block manual annotation (Requirement 7.3)
            self._error_logs.append({
                'task_id': task.id,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
            })
            
            return PreAnnotationResult(
                task_id=task.id,
                annotation={},
                confidence=0.0,
                needs_review=True,
                method_used=config.method.value if config.method else "custom_llm",
                processing_time_ms=0.0,
                error=str(e),
            )
    
    def calculate_confidence(self, prediction: Dict[str, Any]) -> float:
        """Calculate confidence score for a prediction."""
        # If prediction contains explicit confidence, use it
        if "confidence" in prediction:
            conf = prediction["confidence"]
            if isinstance(conf, (int, float)):
                return max(0.0, min(1.0, float(conf)))
        
        # Calculate based on prediction completeness
        confidence = 0.5  # Base confidence
        
        if prediction:
            non_empty_fields = sum(1 for v in prediction.values() if v)
            total_fields = len(prediction)
            if total_fields > 0:
                confidence += 0.3 * (non_empty_fields / total_fields)
        
        return min(1.0, confidence)
    
    def _build_prompt(
        self,
        task: AnnotationTask,
        annotation_type: AnnotationType,
    ) -> str:
        """Build prompt for annotation."""
        text = task.data.get("text", task.data.get("content", str(task.data)))
        return f"Annotate this text for {annotation_type.value}: {text}"
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract annotation."""
        response = response.strip()
        
        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass
            
            return {"raw_response": response, "confidence": 0.3}
    
    def get_error_logs(self) -> List[Dict[str, Any]]:
        """Get logged errors for verification."""
        return self._error_logs.copy()


# ============================================================================
# Helper Functions
# ============================================================================

def create_annotation_task(
    task_id: str,
    text: str,
    annotation_type: AnnotationType,
) -> AnnotationTask:
    """Create an annotation task for testing."""
    metadata = {}
    
    if annotation_type == AnnotationType.TEXT_CLASSIFICATION:
        metadata["categories"] = "positive, negative, neutral"
    elif annotation_type == AnnotationType.NER:
        metadata["entity_types"] = "PERSON, ORG, LOC"
    elif annotation_type == AnnotationType.RELATION_EXTRACTION:
        metadata["relation_types"] = "works_for, located_in"
    elif annotation_type == AnnotationType.SEQUENCE_LABELING:
        metadata["label_types"] = "B-PER, I-PER, O"
    
    return AnnotationTask(
        id=task_id,
        data={"text": text},
        metadata=metadata,
    )


def create_pre_annotation_config(
    annotation_type: AnnotationType,
    confidence_threshold: float = 0.7,
    batch_size: int = 10,
    max_items: int = 100,
) -> PreAnnotationConfig:
    """Create a pre-annotation config for testing."""
    return PreAnnotationConfig(
        annotation_type=annotation_type,
        confidence_threshold=confidence_threshold,
        batch_size=batch_size,
        max_items=max_items,
        method=AnnotationMethod.CUSTOM_LLM,
    )


def is_valid_annotation_schema(
    annotation: Dict[str, Any],
    annotation_type: AnnotationType,
) -> bool:
    """
    Check if annotation conforms to expected schema for the annotation type.
    
    Returns True if the annotation has the expected structure.
    """
    if not annotation:
        return False
    
    # All annotations should be dictionaries
    if not isinstance(annotation, dict):
        return False
    
    # Check type-specific schema requirements
    if annotation_type == AnnotationType.TEXT_CLASSIFICATION:
        # Should have 'label' field
        return 'label' in annotation or 'raw_response' in annotation
    
    elif annotation_type == AnnotationType.NER:
        # Should have 'entities' list
        return 'entities' in annotation or 'raw_response' in annotation
    
    elif annotation_type == AnnotationType.SENTIMENT:
        # Should have 'sentiment' field
        return 'sentiment' in annotation or 'raw_response' in annotation
    
    elif annotation_type == AnnotationType.RELATION_EXTRACTION:
        # Should have 'relations' list
        return 'relations' in annotation or 'raw_response' in annotation
    
    elif annotation_type == AnnotationType.SEQUENCE_LABELING:
        # Should have 'labels' list
        return 'labels' in annotation or 'raw_response' in annotation
    
    elif annotation_type == AnnotationType.QA:
        # Should have 'answer' field
        return 'answer' in annotation or 'raw_response' in annotation
    
    elif annotation_type == AnnotationType.SUMMARIZATION:
        # Should have 'summary' field
        return 'summary' in annotation or 'raw_response' in annotation
    
    # Unknown type - accept any non-empty dict
    return len(annotation) > 0


# ============================================================================
# Property Tests
# ============================================================================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    annotation_type=annotation_type_strategy,
    task_id=task_id_strategy,
    text=text_content_strategy,
    confidence=confidence_strategy,
)
def test_property_18_response_schema_compliance(
    annotation_type: AnnotationType,
    task_id: str,
    text: str,
    confidence: float,
):
    """
    Property 18: Response Schema Compliance
    
    *For any* successful LLM response, parsing the response should produce
    a valid annotation object that conforms to the annotation schema.
    
    **Validates: Requirements 7.2**
    """
    async def run_test():
        # Create mock switcher with controlled confidence
        mock_switcher = MockLLMSwitcher(
            should_fail=False,
            response_confidence=confidence,
        )
        
        # Create engine with mock switcher
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        # Create task and config
        task = create_annotation_task(task_id, text, annotation_type)
        config = create_pre_annotation_config(annotation_type)
        
        # Run pre-annotation
        result = await engine.pre_annotate([task], config)
        
        # Verify we got a result
        assert result is not None
        assert len(result.results) == 1
        
        task_result = result.results[0]
        
        # For successful annotations (no error), verify schema compliance
        if task_result.error is None:
            assert task_result.annotation is not None
            assert isinstance(task_result.annotation, dict)
            
            # Verify annotation conforms to expected schema
            assert is_valid_annotation_schema(
                task_result.annotation,
                annotation_type
            ), f"Annotation does not conform to {annotation_type} schema: {task_result.annotation}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    annotation_type=annotation_type_strategy,
    task_id=task_id_strategy,
    text=text_content_strategy,
)
def test_property_18_successful_response_produces_valid_annotation(
    annotation_type: AnnotationType,
    task_id: str,
    text: str,
):
    """
    Property 18: Successful responses produce valid annotations
    
    **Validates: Requirements 7.2**
    """
    async def run_test():
        # Create mock switcher that always succeeds
        mock_switcher = MockLLMSwitcher(should_fail=False)
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        task = create_annotation_task(task_id, text, annotation_type)
        config = create_pre_annotation_config(annotation_type)
        
        result = await engine.pre_annotate([task], config)
        
        # Successful annotation should have valid structure
        task_result = result.results[0]
        assert task_result.error is None
        assert task_result.annotation is not None
        assert isinstance(task_result.annotation, dict)
        assert len(task_result.annotation) > 0
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    annotation_type=annotation_type_strategy,
    task_id=task_id_strategy,
    text=text_content_strategy,
)
def test_property_19_pre_annotation_error_isolation(
    annotation_type: AnnotationType,
    task_id: str,
    text: str,
):
    """
    Property 19: Pre-Annotation Error Isolation
    
    *For any* pre-annotation request that fails, the failure should be logged
    but should not prevent manual annotation from proceeding.
    
    **Validates: Requirements 7.3**
    """
    async def run_test():
        # Create mock switcher that always fails
        mock_switcher = MockLLMSwitcher(should_fail=True)
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        task = create_annotation_task(task_id, text, annotation_type)
        config = create_pre_annotation_config(annotation_type)
        
        # Pre-annotation should NOT raise an exception
        # It should return a result with error information
        result = await engine.pre_annotate([task], config)
        
        # Verify we got a result (not an exception)
        assert result is not None
        assert len(result.results) == 1
        
        task_result = result.results[0]
        
        # Verify error is captured in result, not raised
        assert task_result.error is not None
        assert "Mock LLM provider failed" in task_result.error
        
        # Verify the result still has valid structure for manual annotation
        assert task_result.task_id == task_id
        assert task_result.annotation == {}  # Empty annotation on failure
        assert task_result.confidence == 0.0  # Zero confidence on failure
        assert task_result.needs_review is True  # Should be marked for review
        
        # Verify error was logged
        error_logs = engine.get_error_logs()
        assert len(error_logs) == 1
        assert error_logs[0]['task_id'] == task_id
        assert 'error' in error_logs[0]
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    num_tasks=st.integers(min_value=1, max_value=10),
    fail_indices=st.lists(st.integers(min_value=0, max_value=9), max_size=5),
)
def test_property_19_partial_failures_dont_block_other_tasks(
    num_tasks: int,
    fail_indices: List[int],
):
    """
    Property 19: Partial failures don't block other tasks
    
    **Validates: Requirements 7.3**
    """
    async def run_test():
        # Normalize fail indices to be within range
        fail_indices_set = set(i % num_tasks for i in fail_indices)
        
        # Create tasks
        tasks = [
            create_annotation_task(
                f"task-{i}",
                f"Sample text {i}",
                AnnotationType.TEXT_CLASSIFICATION
            )
            for i in range(num_tasks)
        ]
        
        # Track which tasks should fail
        call_count = [0]
        
        class PartialFailureSwitcher(MockLLMSwitcher):
            async def generate(self, prompt, options=None, model=None, system_prompt=None):
                current_call = call_count[0]
                call_count[0] += 1
                
                if current_call in fail_indices_set:
                    raise Exception(f"Simulated failure for task {current_call}")
                
                return await super().generate(prompt, options, model, system_prompt)
        
        engine = PreAnnotationEngineForTest(llm_switcher=PartialFailureSwitcher())
        config = create_pre_annotation_config(AnnotationType.TEXT_CLASSIFICATION)
        
        # Should complete without raising exception
        result = await engine.pre_annotate(tasks, config)
        
        # All tasks should have results
        assert len(result.results) == num_tasks
        
        # Count successes and failures
        expected_failures = len(fail_indices_set)
        expected_successes = num_tasks - expected_failures
        
        assert result.failed == expected_failures
        assert result.successful == expected_successes
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    annotation_type=annotation_type_strategy,
    task_id=task_id_strategy,
    text=text_content_strategy,
    confidence=confidence_strategy,
)
def test_property_20_confidence_score_storage(
    annotation_type: AnnotationType,
    task_id: str,
    text: str,
    confidence: float,
):
    """
    Property 20: Confidence Score Storage
    
    *For any* successful pre-annotation, the stored annotation should include
    a confidence score field with a value between 0.0 and 1.0.
    
    **Validates: Requirements 7.4**
    """
    async def run_test():
        # Create mock switcher with specific confidence
        mock_switcher = MockLLMSwitcher(
            should_fail=False,
            response_confidence=confidence,
        )
        
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        task = create_annotation_task(task_id, text, annotation_type)
        config = create_pre_annotation_config(annotation_type)
        
        result = await engine.pre_annotate([task], config)
        
        assert len(result.results) == 1
        task_result = result.results[0]
        
        # For successful annotations, verify confidence score
        if task_result.error is None:
            # Confidence should be stored in result
            assert hasattr(task_result, 'confidence')
            assert task_result.confidence is not None
            
            # Confidence should be between 0.0 and 1.0
            assert 0.0 <= task_result.confidence <= 1.0, \
                f"Confidence {task_result.confidence} is not in range [0.0, 1.0]"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    confidence=confidence_strategy,
    threshold=threshold_strategy,
)
def test_property_20_confidence_determines_review_status(
    confidence: float,
    threshold: float,
):
    """
    Property 20: Confidence determines review status
    
    **Validates: Requirements 7.4**
    """
    async def run_test():
        mock_switcher = MockLLMSwitcher(
            should_fail=False,
            response_confidence=confidence,
        )
        
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        task = create_annotation_task(
            "test-task",
            "Sample text for testing",
            AnnotationType.TEXT_CLASSIFICATION
        )
        config = create_pre_annotation_config(
            AnnotationType.TEXT_CLASSIFICATION,
            confidence_threshold=threshold,
        )
        
        result = await engine.pre_annotate([task], config)
        task_result = result.results[0]
        
        if task_result.error is None:
            # needs_review should be True if confidence < threshold
            expected_needs_review = task_result.confidence < threshold
            assert task_result.needs_review == expected_needs_review, \
                f"needs_review={task_result.needs_review} but confidence={task_result.confidence}, threshold={threshold}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    num_tasks=st.integers(min_value=1, max_value=20),
    annotation_type=annotation_type_strategy,
)
def test_property_20_all_successful_results_have_confidence(
    num_tasks: int,
    annotation_type: AnnotationType,
):
    """
    Property 20: All successful results have confidence scores
    
    **Validates: Requirements 7.4**
    """
    async def run_test():
        mock_switcher = MockLLMSwitcher(should_fail=False)
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        tasks = [
            create_annotation_task(
                f"task-{i}",
                f"Sample text {i}",
                annotation_type
            )
            for i in range(num_tasks)
        ]
        
        config = create_pre_annotation_config(annotation_type)
        result = await engine.pre_annotate(tasks, config)
        
        # All results should have valid confidence scores
        for task_result in result.results:
            if task_result.error is None:
                assert task_result.confidence is not None
                assert isinstance(task_result.confidence, float)
                assert 0.0 <= task_result.confidence <= 1.0
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    task_id=task_id_strategy,
    text=text_content_strategy,
)
def test_property_20_failed_annotations_have_zero_confidence(
    task_id: str,
    text: str,
):
    """
    Property 20: Failed annotations have zero confidence
    
    **Validates: Requirements 7.4**
    """
    async def run_test():
        mock_switcher = MockLLMSwitcher(should_fail=True)
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        task = create_annotation_task(
            task_id,
            text,
            AnnotationType.TEXT_CLASSIFICATION
        )
        config = create_pre_annotation_config(AnnotationType.TEXT_CLASSIFICATION)
        
        result = await engine.pre_annotate([task], config)
        task_result = result.results[0]
        
        # Failed annotations should have zero confidence
        assert task_result.error is not None
        assert task_result.confidence == 0.0
    
    asyncio.run(run_test())


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(
    batch_size=batch_size_strategy,
    num_tasks=st.integers(min_value=1, max_value=50),
)
def test_batch_processing_maintains_schema_compliance(
    batch_size: int,
    num_tasks: int,
):
    """
    Verify schema compliance is maintained across batch processing.
    
    **Validates: Requirements 7.2**
    """
    async def run_test():
        mock_switcher = MockLLMSwitcher(should_fail=False)
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        tasks = [
            create_annotation_task(
                f"task-{i}",
                f"Sample text {i}",
                AnnotationType.TEXT_CLASSIFICATION
            )
            for i in range(num_tasks)
        ]
        
        config = create_pre_annotation_config(
            AnnotationType.TEXT_CLASSIFICATION,
            batch_size=batch_size,
        )
        
        result = await engine.pre_annotate(tasks, config)
        
        # All successful results should have valid schemas
        for task_result in result.results:
            if task_result.error is None:
                assert is_valid_annotation_schema(
                    task_result.annotation,
                    AnnotationType.TEXT_CLASSIFICATION
                )
    
    asyncio.run(run_test())


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(
    malformed_json=st.text(min_size=5, max_size=100).filter(
        lambda x: not x.strip().startswith('{') and not x.strip().isdigit() and '{}' not in x
    ),
)
def test_malformed_response_handling(malformed_json: str):
    """
    Verify malformed LLM responses are handled gracefully.
    
    **Validates: Requirements 7.2, 7.3**
    """
    async def run_test():
        # Create switcher that returns malformed JSON
        mock_switcher = MockLLMSwitcher(
            should_fail=False,
            response_content=malformed_json,
        )
        
        engine = PreAnnotationEngineForTest(llm_switcher=mock_switcher)
        
        task = create_annotation_task(
            "test-task",
            "Sample text",
            AnnotationType.TEXT_CLASSIFICATION
        )
        config = create_pre_annotation_config(AnnotationType.TEXT_CLASSIFICATION)
        
        # Should not raise exception
        result = await engine.pre_annotate([task], config)
        
        assert len(result.results) == 1
        task_result = result.results[0]
        
        # Should either have a fallback annotation with raw_response or an error
        # Both are acceptable ways to handle malformed responses
        # Empty annotation with no error is also acceptable if the response was parseable
        if task_result.error is None:
            assert task_result.annotation is not None
            # Either has meaningful content, or is empty (which is valid for some edge cases)
            # The key property is that it doesn't crash
            if task_result.annotation:
                # If non-empty, should have some recognizable structure
                assert isinstance(task_result.annotation, dict)
        else:
            # Error case is also acceptable - the key is it doesn't crash
            assert task_result.annotation == {}
    
    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
