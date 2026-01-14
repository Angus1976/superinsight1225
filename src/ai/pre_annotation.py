"""
Pre-Annotation Engine for SuperInsight platform.

Implements batch pre-annotation using LLM and sample learning,
with confidence scoring and review marking.
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
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
from src.ai.llm_switcher import LLMSwitcher, get_initialized_switcher
from src.ai.llm_schemas import GenerateOptions

logger = logging.getLogger(__name__)


# Prompt templates for different annotation types
ANNOTATION_PROMPTS = {
    AnnotationType.TEXT_CLASSIFICATION: """
You are an expert text classifier. Classify the following text into one of the given categories.

Categories: {categories}

Text: {text}

Respond with a JSON object containing:
- "label": the category label
- "confidence": a number between 0 and 1 indicating your confidence

Response:""",

    AnnotationType.NER: """
You are an expert named entity recognizer. Extract all named entities from the following text.

Entity types: {entity_types}

Text: {text}

Respond with a JSON object containing:
- "entities": a list of objects, each with "text", "label", "start", "end"
- "confidence": a number between 0 and 1 indicating your overall confidence

Response:""",

    AnnotationType.SENTIMENT: """
You are an expert sentiment analyzer. Analyze the sentiment of the following text.

Text: {text}

Respond with a JSON object containing:
- "sentiment": one of "positive", "negative", "neutral"
- "score": a number between -1 (very negative) and 1 (very positive)
- "confidence": a number between 0 and 1 indicating your confidence

Response:""",

    AnnotationType.RELATION_EXTRACTION: """
You are an expert at extracting relationships between entities. Extract all relationships from the following text.

Relation types: {relation_types}

Text: {text}

Respond with a JSON object containing:
- "relations": a list of objects, each with "subject", "predicate", "object"
- "confidence": a number between 0 and 1 indicating your overall confidence

Response:""",

    AnnotationType.SEQUENCE_LABELING: """
You are an expert at sequence labeling. Label each token in the following text.

Label types: {label_types}

Text: {text}

Respond with a JSON object containing:
- "labels": a list of objects, each with "token", "label"
- "confidence": a number between 0 and 1 indicating your overall confidence

Response:""",

    AnnotationType.QA: """
You are an expert at question answering. Answer the following question based on the given context.

Context: {context}

Question: {question}

Respond with a JSON object containing:
- "answer": the answer text
- "confidence": a number between 0 and 1 indicating your confidence

Response:""",

    AnnotationType.SUMMARIZATION: """
You are an expert at text summarization. Summarize the following text.

Text: {text}

Respond with a JSON object containing:
- "summary": the summary text
- "confidence": a number between 0 and 1 indicating your confidence

Response:""",
}


SAMPLE_LEARNING_PROMPT = """
You are an expert annotator. Learn from the following examples and annotate the new text in the same style.

Examples:
{examples}

Now annotate this text:
{text}

Respond with a JSON object in the same format as the examples.

Response:"""


class PreAnnotationEngine:
    """
    Pre-annotation engine using LLM for batch annotation.
    
    Features:
    - Batch pre-annotation with configurable batch size
    - Confidence scoring for each annotation
    - Sample learning for improved accuracy
    - Automatic review marking based on confidence threshold
    - Support for multiple annotation types
    """
    
    def __init__(
        self,
        llm_switcher: Optional[LLMSwitcher] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize the pre-annotation engine.
        
        Args:
            llm_switcher: LLM switcher instance
            tenant_id: Tenant ID for multi-tenant support
        """
        self._llm_switcher = llm_switcher
        self._tenant_id = tenant_id
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the engine."""
        if self._initialized:
            return
        
        if self._llm_switcher is None:
            self._llm_switcher = await get_initialized_switcher(self._tenant_id)
        
        self._initialized = True
        logger.info("Pre-annotation engine initialized")
    
    async def pre_annotate(
        self,
        tasks: List[AnnotationTask],
        config: PreAnnotationConfig,
    ) -> PreAnnotationBatchResult:
        """
        Perform batch pre-annotation.
        
        Args:
            tasks: List of tasks to annotate
            config: Pre-annotation configuration
            
        Returns:
            PreAnnotationBatchResult with all results
        """
        await self._ensure_initialized()
        
        # Enforce max items limit
        if len(tasks) > config.max_items:
            tasks = tasks[:config.max_items]
            logger.warning(f"Truncated tasks to max_items limit: {config.max_items}")
        
        start_time = time.time()
        results: List[PreAnnotationResult] = []
        successful = 0
        failed = 0
        needs_review = 0
        
        # Process in batches
        for i in range(0, len(tasks), config.batch_size):
            batch = tasks[i:i + config.batch_size]
            batch_results = await self._process_batch(batch, config)
            
            for result in batch_results:
                results.append(result)
                if result.error:
                    failed += 1
                else:
                    successful += 1
                    if result.needs_review:
                        needs_review += 1
        
        total_time = (time.time() - start_time) * 1000
        
        return PreAnnotationBatchResult(
            job_id=str(uuid4()),
            total_tasks=len(tasks),
            successful=successful,
            failed=failed,
            needs_review=needs_review,
            results=results,
            processing_time_ms=total_time,
            created_at=datetime.utcnow(),
        )
    
    async def pre_annotate_with_samples(
        self,
        tasks: List[AnnotationTask],
        samples: List[AnnotatedSample],
        config: PreAnnotationConfig,
    ) -> PreAnnotationBatchResult:
        """
        Perform pre-annotation using sample learning.
        
        Args:
            tasks: List of tasks to annotate
            samples: Annotated samples for learning
            config: Pre-annotation configuration
            
        Returns:
            PreAnnotationBatchResult with all results
        """
        await self._ensure_initialized()
        
        # Enforce max items limit
        if len(tasks) > config.max_items:
            tasks = tasks[:config.max_items]
        
        start_time = time.time()
        results: List[PreAnnotationResult] = []
        successful = 0
        failed = 0
        needs_review = 0
        
        # Process in batches with sample context
        for i in range(0, len(tasks), config.batch_size):
            batch = tasks[i:i + config.batch_size]
            batch_results = await self._process_batch_with_samples(batch, samples, config)
            
            for result in batch_results:
                results.append(result)
                if result.error:
                    failed += 1
                else:
                    successful += 1
                    if result.needs_review:
                        needs_review += 1
        
        total_time = (time.time() - start_time) * 1000
        
        return PreAnnotationBatchResult(
            job_id=str(uuid4()),
            total_tasks=len(tasks),
            successful=successful,
            failed=failed,
            needs_review=needs_review,
            results=results,
            processing_time_ms=total_time,
            created_at=datetime.utcnow(),
        )
    
    def calculate_confidence(self, prediction: Dict[str, Any]) -> float:
        """
        Calculate confidence score for a prediction.
        
        Args:
            prediction: The prediction dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        # If prediction contains explicit confidence, use it
        if "confidence" in prediction:
            conf = prediction["confidence"]
            if isinstance(conf, (int, float)):
                return max(0.0, min(1.0, float(conf)))
        
        # Calculate based on prediction completeness
        confidence = 0.5  # Base confidence
        
        # Boost confidence for complete predictions
        if prediction:
            non_empty_fields = sum(1 for v in prediction.values() if v)
            total_fields = len(prediction)
            if total_fields > 0:
                confidence += 0.3 * (non_empty_fields / total_fields)
        
        return min(1.0, confidence)
    
    def mark_for_review(
        self,
        results: List[PreAnnotationResult],
        threshold: float,
    ) -> List[PreAnnotationResult]:
        """
        Mark results that need human review based on confidence threshold.
        
        Args:
            results: List of pre-annotation results
            threshold: Confidence threshold
            
        Returns:
            Updated results with needs_review flags
        """
        for result in results:
            result.needs_review = result.confidence < threshold
        return results
    
    async def _ensure_initialized(self) -> None:
        """Ensure the engine is initialized."""
        if not self._initialized:
            await self.initialize()
    
    async def _process_batch(
        self,
        tasks: List[AnnotationTask],
        config: PreAnnotationConfig,
    ) -> List[PreAnnotationResult]:
        """Process a batch of tasks."""
        results = []
        
        # Process tasks concurrently
        async def process_task(task: AnnotationTask) -> PreAnnotationResult:
            return await self._annotate_single(task, config)
        
        # Use asyncio.gather for concurrent processing
        task_results = await asyncio.gather(
            *[process_task(task) for task in tasks],
            return_exceptions=True
        )
        
        for task, result in zip(tasks, task_results):
            if isinstance(result, Exception):
                results.append(PreAnnotationResult(
                    task_id=task.id,
                    annotation={},
                    confidence=0.0,
                    needs_review=True,
                    method_used=config.method.value if config.method else "custom_llm",
                    processing_time_ms=0,
                    error=str(result),
                ))
            else:
                results.append(result)
        
        return results
    
    async def _process_batch_with_samples(
        self,
        tasks: List[AnnotationTask],
        samples: List[AnnotatedSample],
        config: PreAnnotationConfig,
    ) -> List[PreAnnotationResult]:
        """Process a batch of tasks with sample learning."""
        results = []
        
        async def process_task(task: AnnotationTask) -> PreAnnotationResult:
            return await self._annotate_with_samples(task, samples, config)
        
        task_results = await asyncio.gather(
            *[process_task(task) for task in tasks],
            return_exceptions=True
        )
        
        for task, result in zip(tasks, task_results):
            if isinstance(result, Exception):
                results.append(PreAnnotationResult(
                    task_id=task.id,
                    annotation={},
                    confidence=0.0,
                    needs_review=True,
                    method_used=config.method.value if config.method else "custom_llm",
                    processing_time_ms=0,
                    error=str(result),
                ))
            else:
                results.append(result)
        
        return results
    
    async def _annotate_single(
        self,
        task: AnnotationTask,
        config: PreAnnotationConfig,
    ) -> PreAnnotationResult:
        """Annotate a single task."""
        start_time = time.time()
        
        try:
            # Build prompt
            prompt = self._build_prompt(task, config.annotation_type)
            
            # Generate annotation
            options = GenerateOptions(
                max_tokens=1000,
                temperature=0.3,  # Lower temperature for more consistent results
            )
            
            response = await self._llm_switcher.generate(
                prompt=prompt,
                options=options,
                model=config.model,
            )
            
            # Parse response
            annotation = self._parse_response(response.content)
            confidence = self.calculate_confidence(annotation)
            
            processing_time = (time.time() - start_time) * 1000
            
            return PreAnnotationResult(
                task_id=task.id,
                annotation=annotation,
                confidence=confidence,
                needs_review=confidence < config.confidence_threshold,
                method_used=config.method.value if config.method else "custom_llm",
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to annotate task {task.id}: {e}")
            
            return PreAnnotationResult(
                task_id=task.id,
                annotation={},
                confidence=0.0,
                needs_review=True,
                method_used=config.method.value if config.method else "custom_llm",
                processing_time_ms=processing_time,
                error=str(e),
            )
    
    async def _annotate_with_samples(
        self,
        task: AnnotationTask,
        samples: List[AnnotatedSample],
        config: PreAnnotationConfig,
    ) -> PreAnnotationResult:
        """Annotate a task using sample learning."""
        start_time = time.time()
        
        try:
            # Build prompt with samples
            prompt = self._build_sample_prompt(task, samples)
            
            options = GenerateOptions(
                max_tokens=1000,
                temperature=0.3,
            )
            
            response = await self._llm_switcher.generate(
                prompt=prompt,
                options=options,
                model=config.model,
            )
            
            annotation = self._parse_response(response.content)
            confidence = self.calculate_confidence(annotation)
            
            # Boost confidence slightly for sample-based annotation
            confidence = min(1.0, confidence + 0.1)
            
            processing_time = (time.time() - start_time) * 1000
            
            return PreAnnotationResult(
                task_id=task.id,
                annotation=annotation,
                confidence=confidence,
                needs_review=confidence < config.confidence_threshold,
                method_used="sample_learning",
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to annotate task {task.id} with samples: {e}")
            
            return PreAnnotationResult(
                task_id=task.id,
                annotation={},
                confidence=0.0,
                needs_review=True,
                method_used="sample_learning",
                processing_time_ms=processing_time,
                error=str(e),
            )
    
    def _build_prompt(
        self,
        task: AnnotationTask,
        annotation_type: AnnotationType,
    ) -> str:
        """Build prompt for annotation."""
        template = ANNOTATION_PROMPTS.get(annotation_type)
        if not template:
            template = ANNOTATION_PROMPTS[AnnotationType.TEXT_CLASSIFICATION]
        
        # Extract text from task data
        text = task.data.get("text", task.data.get("content", str(task.data)))
        
        # Get type-specific parameters from metadata
        params = {
            "text": text,
            "categories": task.metadata.get("categories", "positive, negative, neutral"),
            "entity_types": task.metadata.get("entity_types", "PERSON, ORG, LOC, DATE"),
            "relation_types": task.metadata.get("relation_types", "works_for, located_in, part_of"),
            "label_types": task.metadata.get("label_types", "B-PER, I-PER, B-ORG, I-ORG, O"),
            "context": task.data.get("context", ""),
            "question": task.data.get("question", ""),
        }
        
        return template.format(**params)
    
    def _build_sample_prompt(
        self,
        task: AnnotationTask,
        samples: List[AnnotatedSample],
    ) -> str:
        """Build prompt with sample examples."""
        # Format examples
        examples = []
        for sample in samples[:5]:  # Limit to 5 examples
            example_text = sample.data.get("text", str(sample.data))
            example_annotation = json.dumps(sample.annotation, ensure_ascii=False)
            examples.append(f"Text: {example_text}\nAnnotation: {example_annotation}")
        
        examples_str = "\n\n".join(examples)
        
        # Get task text
        text = task.data.get("text", task.data.get("content", str(task.data)))
        
        return SAMPLE_LEARNING_PROMPT.format(
            examples=examples_str,
            text=text,
        )
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract annotation."""
        # Try to extract JSON from response
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
            
            # Return raw response as annotation
            return {"raw_response": response, "confidence": 0.3}


# Singleton instance
_engine_instances: Dict[str, PreAnnotationEngine] = {}


def get_pre_annotation_engine(tenant_id: Optional[str] = None) -> PreAnnotationEngine:
    """
    Get or create a pre-annotation engine instance.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        
    Returns:
        PreAnnotationEngine instance
    """
    key = tenant_id or "global"
    
    if key not in _engine_instances:
        _engine_instances[key] = PreAnnotationEngine(tenant_id=tenant_id)
    
    return _engine_instances[key]


async def get_initialized_engine(tenant_id: Optional[str] = None) -> PreAnnotationEngine:
    """
    Get an initialized pre-annotation engine.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        
    Returns:
        Initialized PreAnnotationEngine instance
    """
    engine = get_pre_annotation_engine(tenant_id)
    await engine.initialize()
    return engine
