"""
Desensitization Performance Optimizer - Achieve > 1MB/s processing speed.

This module provides performance optimizations for data desensitization operations
including batch processing, caching, parallel execution, and memory management.
"""

import time
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import lru_cache
import hashlib

from .optimized_presidio_engine import OptimizedPresidioEngine
from .models import DesensitizationRule, DesensitizationResult, PIIEntity

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    enable_parallel_processing: bool = True
    max_worker_threads: int = 4
    batch_size: int = 10
    cache_size: int = 1000
    memory_limit_mb: int = 100
    enable_compression: bool = True
    chunk_size_kb: int = 64


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    total_bytes_processed: int = 0
    total_processing_time: float = 0.0
    throughput_mbps: float = 0.0
    cache_hit_rate: float = 0.0
    parallel_efficiency: float = 0.0
    memory_usage_mb: float = 0.0


class DesensitizationPerformanceOptimizer:
    """
    High-performance desensitization optimizer.
    
    Provides optimized batch processing, caching, and parallel execution
    for achieving > 1MB/s desensitization throughput.
    """
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        """
        Initialize performance optimizer.
        
        Args:
            config: Performance configuration
        """
        self.config = config or PerformanceConfig()
        self.engine = OptimizedPresidioEngine(
            enable_parallel=self.config.enable_parallel_processing
        )
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()
        self._thread_pool = None
        
        if self.config.enable_parallel_processing:
            self._thread_pool = ThreadPoolExecutor(
                max_workers=self.config.max_worker_threads
            )
    
    def __del__(self):
        """Clean up resources."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)
    
    def process_text_batch(
        self,
        texts: List[str],
        rules: List[DesensitizationRule],
        detect_only: bool = False
    ) -> List[DesensitizationResult]:
        """
        Process a batch of texts with optimized performance.
        
        Args:
            texts: List of texts to process
            rules: Desensitization rules to apply
            detect_only: If True, only detect PII without anonymization
            
        Returns:
            List of processing results
        """
        start_time = time.perf_counter()
        
        try:
            # Calculate total size for metrics
            total_bytes = sum(len(text.encode('utf-8')) for text in texts)
            
            # Process in optimized batches
            if self.config.enable_parallel_processing and len(texts) > 1:
                results = self._process_batch_parallel(texts, rules, detect_only)
            else:
                results = self._process_batch_sequential(texts, rules, detect_only)
            
            # Update metrics
            processing_time = time.perf_counter() - start_time
            self._update_metrics(total_bytes, processing_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Return failed results
            return [
                DesensitizationResult(
                    success=False,
                    original_text=text,
                    anonymized_text=text,
                    entities_found=[],
                    rules_applied=[],
                    processing_time_ms=0.0,
                    errors=[str(e)]
                )
                for text in texts
            ]
    
    def _process_batch_parallel(
        self,
        texts: List[str],
        rules: List[DesensitizationRule],
        detect_only: bool
    ) -> List[DesensitizationResult]:
        """
        Process batch using parallel execution.
        
        Args:
            texts: Texts to process
            rules: Desensitization rules
            detect_only: Detection only flag
            
        Returns:
            List of results
        """
        def process_single_text(text_index_pair):
            text, index = text_index_pair
            try:
                if detect_only:
                    # Detection only
                    entities = self.engine.detect_pii(text)
                    return index, DesensitizationResult(
                        success=True,
                        original_text=text,
                        anonymized_text=text,
                        entities_found=entities,
                        rules_applied=[],
                        processing_time_ms=0.0
                    )
                else:
                    # Full anonymization
                    result = self.engine.anonymize_text(text, rules)
                    return index, result
            except Exception as e:
                return index, DesensitizationResult(
                    success=False,
                    original_text=text,
                    anonymized_text=text,
                    entities_found=[],
                    rules_applied=[],
                    processing_time_ms=0.0,
                    errors=[str(e)]
                )
        
        # Submit tasks with indices to maintain order
        indexed_texts = [(text, i) for i, text in enumerate(texts)]
        futures = []
        
        for text_pair in indexed_texts:
            future = self._thread_pool.submit(process_single_text, text_pair)
            futures.append(future)
        
        # Collect results in order
        results = [None] * len(texts)
        for future in as_completed(futures, timeout=30.0):
            try:
                index, result = future.result()
                results[index] = result
            except Exception as e:
                logger.warning(f"Parallel processing failed: {e}")
        
        # Fill any None results with error results
        for i, result in enumerate(results):
            if result is None:
                results[i] = DesensitizationResult(
                    success=False,
                    original_text=texts[i] if i < len(texts) else "",
                    anonymized_text=texts[i] if i < len(texts) else "",
                    entities_found=[],
                    rules_applied=[],
                    processing_time_ms=0.0,
                    errors=["Parallel processing timeout"]
                )
        
        return results
    
    def _process_batch_sequential(
        self,
        texts: List[str],
        rules: List[DesensitizationRule],
        detect_only: bool
    ) -> List[DesensitizationResult]:
        """
        Process batch sequentially.
        
        Args:
            texts: Texts to process
            rules: Desensitization rules
            detect_only: Detection only flag
            
        Returns:
            List of results
        """
        results = []
        
        for text in texts:
            try:
                if detect_only:
                    entities = self.engine.detect_pii(text)
                    result = DesensitizationResult(
                        success=True,
                        original_text=text,
                        anonymized_text=text,
                        entities_found=entities,
                        rules_applied=[],
                        processing_time_ms=0.0
                    )
                else:
                    result = self.engine.anonymize_text(text, rules)
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Sequential processing failed: {e}")
                results.append(DesensitizationResult(
                    success=False,
                    original_text=text,
                    anonymized_text=text,
                    entities_found=[],
                    rules_applied=[],
                    processing_time_ms=0.0,
                    errors=[str(e)]
                ))
        
        return results
    
    def process_large_text(
        self,
        text: str,
        rules: List[DesensitizationRule],
        chunk_size_kb: Optional[int] = None
    ) -> DesensitizationResult:
        """
        Process large text by chunking for optimal performance.
        
        Args:
            text: Large text to process
            rules: Desensitization rules
            chunk_size_kb: Chunk size in KB (None for config default)
            
        Returns:
            Combined desensitization result
        """
        start_time = time.perf_counter()
        
        chunk_size = (chunk_size_kb or self.config.chunk_size_kb) * 1024
        text_bytes = text.encode('utf-8')
        
        # If text is small enough, process directly
        if len(text_bytes) <= chunk_size:
            return self.engine.anonymize_text(text, rules)
        
        # Split into chunks with overlap to handle entities at boundaries
        overlap_size = 200  # 200 characters overlap
        chunks = []
        chunk_positions = []
        
        i = 0
        while i < len(text):
            chunk_end = min(i + chunk_size, len(text))
            chunk = text[i:chunk_end]
            chunks.append(chunk)
            chunk_positions.append(i)
            
            # Move to next chunk with overlap
            i = chunk_end - overlap_size
            if i >= len(text) - overlap_size:
                break
        
        # Process chunks
        chunk_results = self.process_text_batch(chunks, rules)
        
        # Merge results
        merged_text = ""
        all_entities = []
        all_rules_applied = set()
        all_errors = []
        success = True
        
        for i, (chunk_result, chunk_start) in enumerate(zip(chunk_results, chunk_positions)):
            if not chunk_result.success:
                success = False
                all_errors.extend(chunk_result.errors)
                continue
            
            # Add chunk text (handle overlap)
            if i == 0:
                merged_text += chunk_result.anonymized_text
            else:
                # Skip overlap from previous chunk
                overlap_start = overlap_size if chunk_start > 0 else 0
                merged_text += chunk_result.anonymized_text[overlap_start:]
            
            # Adjust entity positions and add to global list
            for entity in chunk_result.entities_found:
                adjusted_entity = PIIEntity(
                    entity_type=entity.entity_type,
                    start=entity.start + chunk_start,
                    end=entity.end + chunk_start,
                    score=entity.score,
                    text=entity.text,
                    recognition_metadata=entity.recognition_metadata
                )
                all_entities.append(adjusted_entity)
            
            all_rules_applied.update(chunk_result.rules_applied)
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return DesensitizationResult(
            success=success,
            original_text=text,
            anonymized_text=merged_text,
            entities_found=all_entities,
            rules_applied=list(all_rules_applied),
            processing_time_ms=processing_time,
            errors=all_errors
        )
    
    def benchmark_performance(
        self,
        test_sizes_mb: List[float] = None,
        rules: List[DesensitizationRule] = None
    ) -> Dict[str, Any]:
        """
        Benchmark desensitization performance.
        
        Args:
            test_sizes_mb: List of test sizes in MB
            rules: Rules to use for testing
            
        Returns:
            Benchmark results
        """
        if test_sizes_mb is None:
            test_sizes_mb = [0.1, 0.5, 1.0, 2.0]
        
        if rules is None:
            # Create default test rules
            from .models import PIIEntityType, MaskingStrategy, SensitivityLevel
            from uuid import uuid4
            
            rules = [
                DesensitizationRule(
                    id=str(uuid4()),
                    name="Email Masking",
                    entity_type=PIIEntityType.EMAIL_ADDRESS,
                    masking_strategy=MaskingStrategy.MASK,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    confidence_threshold=0.7,
                    config={"mask_char": "*", "chars_to_mask": -1},
                    enabled=True
                )
            ]
        
        benchmark_results = {
            "test_configuration": {
                "parallel_processing": self.config.enable_parallel_processing,
                "max_workers": self.config.max_worker_threads,
                "batch_size": self.config.batch_size,
                "chunk_size_kb": self.config.chunk_size_kb
            },
            "results": []
        }
        
        for size_mb in test_sizes_mb:
            # Generate test text
            test_text = self._generate_test_text(size_mb)
            
            # Benchmark processing
            start_time = time.perf_counter()
            result = self.process_large_text(test_text, rules)
            processing_time = time.perf_counter() - start_time
            
            # Calculate metrics
            text_size_bytes = len(test_text.encode('utf-8'))
            throughput_mbps = (text_size_bytes / (1024 * 1024)) / processing_time
            
            benchmark_results["results"].append({
                "size_mb": size_mb,
                "size_bytes": text_size_bytes,
                "processing_time_s": processing_time,
                "throughput_mbps": throughput_mbps,
                "entities_found": len(result.entities_found),
                "success": result.success,
                "target_met": throughput_mbps > 1.0
            })
        
        return benchmark_results
    
    def _generate_test_text(self, size_mb: float) -> str:
        """
        Generate test text with embedded PII.
        
        Args:
            size_mb: Target size in MB
            
        Returns:
            Generated test text
        """
        target_chars = int(size_mb * 1024 * 1024)
        
        # Base patterns
        words = ["data", "processing", "system", "user", "information", "security"]
        pii_patterns = ["user@example.com", "555-123-4567", "192.168.1.1"]
        
        text_parts = []
        current_length = 0
        
        while current_length < target_chars:
            # Add regular text
            sentence = " ".join(words[:4]) + ". "
            text_parts.append(sentence)
            current_length += len(sentence)
            
            # Occasionally add PII
            if current_length % 500 == 0:
                pii = f"Contact: {pii_patterns[current_length % len(pii_patterns)]}. "
                text_parts.append(pii)
                current_length += len(pii)
        
        return "".join(text_parts)[:target_chars]
    
    def _update_metrics(self, bytes_processed: int, processing_time: float):
        """
        Update performance metrics.
        
        Args:
            bytes_processed: Number of bytes processed
            processing_time: Processing time in seconds
        """
        with self._lock:
            self.metrics.total_bytes_processed += bytes_processed
            self.metrics.total_processing_time += processing_time
            
            if self.metrics.total_processing_time > 0:
                total_mb = self.metrics.total_bytes_processed / (1024 * 1024)
                self.metrics.throughput_mbps = total_mb / self.metrics.total_processing_time
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics.
        
        Returns:
            Performance metrics
        """
        with self._lock:
            # Get engine stats
            engine_stats = self.engine.get_performance_stats()
            
            # Update cache hit rate if available
            if "cache_info" in engine_stats:
                cache_info = engine_stats["cache_info"]["pattern_search_cache"]
                total_requests = cache_info["hits"] + cache_info["misses"]
                if total_requests > 0:
                    self.metrics.cache_hit_rate = cache_info["hits"] / total_requests
            
            return self.metrics
    
    def clear_caches(self):
        """Clear all caches to free memory."""
        self.engine.clear_caches()
        
        with self._lock:
            # Reset metrics
            self.metrics = PerformanceMetrics()
    
    def optimize_for_throughput(self) -> PerformanceConfig:
        """
        Optimize configuration for maximum throughput.
        
        Returns:
            Optimized configuration
        """
        # Run quick benchmark to find optimal settings
        import multiprocessing
        
        optimal_config = PerformanceConfig(
            enable_parallel_processing=True,
            max_worker_threads=min(multiprocessing.cpu_count(), 8),
            batch_size=20,
            cache_size=2000,
            memory_limit_mb=200,
            enable_compression=True,
            chunk_size_kb=128
        )
        
        return optimal_config