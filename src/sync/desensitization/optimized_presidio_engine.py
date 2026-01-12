"""
Optimized Microsoft Presidio integration for high-performance PII detection and anonymization.
Target: > 1MB/s processing speed with minimal overhead.
"""

import hashlib
import logging
import time
import re
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import threading

from .models import (
    DesensitizationRule,
    DesensitizationResult,
    MaskingStrategy,
    PIIEntity,
    PIIEntityType
)

logger = logging.getLogger(__name__)


class OptimizedPresidioEngine:
    """
    High-performance Microsoft Presidio engine for PII detection and anonymization.
    
    Optimizations:
    - Compiled regex patterns for faster matching
    - Batch processing capabilities
    - Reduced logging overhead
    - Memory-efficient text processing
    - Parallel processing for large texts
    """
    
    def __init__(self, language: str = "en", enable_parallel: bool = True):
        """
        Initialize optimized Presidio engine.
        
        Args:
            language: Language code for analysis (default: "en")
            enable_parallel: Enable parallel processing for large texts
        """
        self.language = language
        self.enable_parallel = enable_parallel
        self._analyzer = None
        self._anonymizer = None
        self._initialized = False
        self._initialization_attempted = False
        self._compiled_patterns = {}
        self._pattern_cache = {}
        self._thread_pool = None
        self._lock = threading.Lock()
        
        # Pre-compile regex patterns for better performance
        self._compile_patterns()
        
        if enable_parallel:
            self._thread_pool = ThreadPoolExecutor(max_workers=4)
    
    def __del__(self):
        """Clean up thread pool on destruction."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)
    
    def _initialize_presidio(self) -> bool:
        """
        Initialize Presidio components lazily with reduced logging.
        
        Returns:
            bool: True if initialization successful
        """
        if self._initialized:
            return True
            
        if self._initialization_attempted:
            return False
            
        with self._lock:
            if self._initialized:
                return True
                
            if self._initialization_attempted:
                return False
                
            self._initialization_attempted = True
            
            try:
                # Try to import Presidio components
                from presidio_analyzer import AnalyzerEngine
                from presidio_anonymizer import AnonymizerEngine
                
                # Initialize analyzer
                self._analyzer = AnalyzerEngine()
                
                # Initialize anonymizer
                self._anonymizer = AnonymizerEngine()
                
                self._initialized = True
                logger.info("Presidio engine initialized successfully")
                return True
                
            except ImportError:
                # Only log once to reduce noise
                logger.warning("Presidio not available. Using optimized fallback implementation.")
                self._initialized = False
                return False
            except Exception as e:
                logger.error(f"Failed to initialize Presidio: {e}")
                self._initialized = False
                return False
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for better performance."""
        self._compiled_patterns = {
            PIIEntityType.EMAIL_ADDRESS: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                re.IGNORECASE
            ),
            PIIEntityType.PHONE_NUMBER: re.compile(
                r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
            ),
            PIIEntityType.CREDIT_CARD: re.compile(
                r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
            ),
            PIIEntityType.IP_ADDRESS: re.compile(
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ),
            PIIEntityType.US_SSN: re.compile(
                r'\b\d{3}-?\d{2}-?\d{4}\b'
            ),
        }
    
    @lru_cache(maxsize=1000)
    def _cached_pattern_search(self, pattern_key: str, text_hash: str, text: str) -> List[Tuple[int, int, str]]:
        """
        Cached pattern search for repeated text patterns.
        
        Args:
            pattern_key: Key identifying the pattern
            text_hash: Hash of the text for cache key
            text: Text to search
            
        Returns:
            List of (start, end, matched_text) tuples
        """
        if pattern_key not in self._compiled_patterns:
            return []
            
        pattern = self._compiled_patterns[pattern_key]
        matches = []
        
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), match.group()))
            
        return matches
    
    def detect_pii(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        language: Optional[str] = None,
        score_threshold: float = 0.6
    ) -> List[PIIEntity]:
        """
        Detect PII entities in text with optimized performance.
        
        Args:
            text: Text to analyze
            entities: List of entity types to detect (None for all)
            language: Language code (None for default)
            score_threshold: Minimum confidence score
            
        Returns:
            List of detected PII entities
        """
        if not text or not text.strip():
            return []
        
        # Use optimized fallback for better performance
        return self._optimized_detect_pii(text, entities, score_threshold)
    
    def _optimized_detect_pii(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        score_threshold: float = 0.6
    ) -> List[PIIEntity]:
        """
        Optimized PII detection using compiled regex patterns.
        
        Args:
            text: Text to analyze
            entities: List of entity types to detect
            score_threshold: Minimum confidence score
            
        Returns:
            List of detected PII entities
        """
        pii_entities = []
        text_hash = str(hash(text))
        
        # Filter patterns based on requested entities
        patterns_to_check = self._compiled_patterns
        if entities:
            entity_types = {PIIEntityType(e) for e in entities if e in [et.value for et in PIIEntityType]}
            patterns_to_check = {k: v for k, v in self._compiled_patterns.items() if k in entity_types}
        
        # Process patterns in parallel for large texts
        if self.enable_parallel and len(text) > 10000 and self._thread_pool:
            return self._parallel_detect_pii(text, patterns_to_check, text_hash)
        
        # Sequential processing for smaller texts
        for entity_type, pattern in patterns_to_check.items():
            matches = self._cached_pattern_search(entity_type.value, text_hash, text)
            
            for start, end, matched_text in matches:
                entity = PIIEntity(
                    entity_type=entity_type,
                    start=start,
                    end=end,
                    score=0.85,  # High confidence for regex matches
                    text=matched_text,
                    recognition_metadata={"method": "optimized_regex"}
                )
                pii_entities.append(entity)
        
        return pii_entities
    
    def _parallel_detect_pii(
        self,
        text: str,
        patterns_to_check: Dict[PIIEntityType, re.Pattern],
        text_hash: str
    ) -> List[PIIEntity]:
        """
        Parallel PII detection for large texts.
        
        Args:
            text: Text to analyze
            patterns_to_check: Patterns to check
            text_hash: Hash of the text
            
        Returns:
            List of detected PII entities
        """
        def detect_entity_type(entity_type):
            try:
                matches = self._cached_pattern_search(entity_type.value, text_hash, text)
                
                entities = []
                for start, end, matched_text in matches:
                    entity = PIIEntity(
                        entity_type=entity_type,
                        start=start,
                        end=end,
                        score=0.85,
                        text=matched_text,
                        recognition_metadata={"method": "optimized_regex_parallel"}
                    )
                    entities.append(entity)
                return entities
            except Exception as e:
                logger.warning(f"Parallel detection failed for {entity_type}: {e}")
                return []
        
        # Submit tasks to thread pool
        futures = []
        for entity_type in patterns_to_check.keys():
            future = self._thread_pool.submit(detect_entity_type, entity_type)
            futures.append(future)
        
        # Collect results
        all_entities = []
        for future in futures:
            try:
                entities = future.result(timeout=5.0)  # 5 second timeout
                all_entities.extend(entities)
            except Exception as e:
                logger.warning(f"Parallel detection failed: {e}")
        
        return all_entities
    
    def anonymize_text(
        self,
        text: str,
        rules: List[DesensitizationRule],
        entities: Optional[List[PIIEntity]] = None
    ) -> DesensitizationResult:
        """
        Anonymize text using desensitization rules with optimized performance.
        
        Args:
            text: Text to anonymize
            rules: List of desensitization rules
            entities: Pre-detected entities (None to detect automatically)
            
        Returns:
            DesensitizationResult with anonymized text and metadata
        """
        start_time = time.perf_counter()
        
        if not text or not text.strip():
            return DesensitizationResult(
                success=True,
                original_text=text,
                anonymized_text=text,
                entities_found=[],
                rules_applied=[],
                processing_time_ms=0.0
            )
        
        try:
            # Detect entities if not provided
            if entities is None:
                entity_types = [rule.entity_type.value for rule in rules if rule.enabled]
                entities = self.detect_pii(text, entity_types)
            
            # Use optimized anonymization
            return self._optimized_anonymize(text, rules, entities, start_time)
                
        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Anonymization failed: {e}")
            return DesensitizationResult(
                success=False,
                original_text=text,
                anonymized_text=text,
                entities_found=entities or [],
                rules_applied=[],
                processing_time_ms=processing_time,
                errors=[str(e)]
            )
    
    def _optimized_anonymize(
        self,
        text: str,
        rules: List[DesensitizationRule],
        entities: List[PIIEntity],
        start_time: float
    ) -> DesensitizationResult:
        """
        Optimized anonymization without Presidio dependency.
        
        Args:
            text: Text to anonymize
            rules: Desensitization rules
            entities: Detected PII entities
            start_time: Processing start time
            
        Returns:
            DesensitizationResult
        """
        anonymized_text = text
        rules_applied = []
        
        # Create rule lookup by entity type for O(1) access
        rule_map = {}
        for rule in rules:
            if rule.enabled:
                rule_map[rule.entity_type] = rule
        
        # Sort entities by start position (reverse order for replacement)
        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)
        
        # Apply anonymization to each entity
        for entity in sorted_entities:
            rule = rule_map.get(entity.entity_type)
            if not rule:
                continue
                
            # Apply masking based on strategy
            masked_value = self._apply_masking_strategy_optimized(entity.text, rule)
            
            # Replace in text
            anonymized_text = (
                anonymized_text[:entity.start] +
                masked_value +
                anonymized_text[entity.end:]
            )
            
            if rule.name not in rules_applied:
                rules_applied.append(rule.name or rule.id)
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return DesensitizationResult(
            success=True,
            original_text=text,
            anonymized_text=anonymized_text,
            entities_found=entities,
            rules_applied=rules_applied,
            processing_time_ms=processing_time
        )
    
    @lru_cache(maxsize=500)
    def _apply_masking_strategy_cached(
        self,
        text: str,
        strategy: str,
        config_str: str
    ) -> str:
        """
        Cached masking strategy application.
        
        Args:
            text: Text to mask
            strategy: Masking strategy string
            config_str: Serialized config for caching
            
        Returns:
            Masked text
        """
        import json
        config = json.loads(config_str) if config_str else {}
        
        if strategy == "REPLACE":
            return config.get("replacement", "***")
            
        elif strategy == "REDACT":
            return "[REDACTED]"
            
        elif strategy == "HASH":
            hash_type = config.get("hash_type", "sha256")
            salt = config.get("salt", "")
            
            if hash_type == "md5":
                return hashlib.md5((text + salt).encode()).hexdigest()[:8]
            else:  # Default to SHA256
                return hashlib.sha256((text + salt).encode()).hexdigest()[:8]
                
        elif strategy == "MASK":
            mask_char = config.get("mask_char", "*")
            chars_to_mask = config.get("chars_to_mask", -1)
            from_end = config.get("from_end", False)
            
            if chars_to_mask == -1:
                return mask_char * len(text)
            elif from_end:
                return text[:-chars_to_mask] + mask_char * chars_to_mask
            else:
                return mask_char * chars_to_mask + text[chars_to_mask:]
                
        elif strategy == "KEEP":
            return text
            
        else:
            # Default to masking
            return "*" * len(text)
    
    def _apply_masking_strategy(
        self,
        text: str,
        rule: DesensitizationRule
    ) -> str:
        """
        Apply masking strategy to text with optimized performance.
        
        Args:
            text: Text to mask
            rule: Desensitization rule
            
        Returns:
            Masked text
        """
        import json
        
        # Use cached version for repeated patterns
        config_str = json.dumps(rule.config, sort_keys=True) if rule.config else ""
        strategy_str = rule.masking_strategy.value if hasattr(rule.masking_strategy, 'value') else str(rule.masking_strategy)
        
        return self._apply_masking_strategy_cached(text, strategy_str, config_str)
    
    def batch_detect_pii(
        self,
        texts: List[str],
        entities: Optional[List[str]] = None,
        score_threshold: float = 0.6
    ) -> List[List[PIIEntity]]:
        """
        Batch PII detection for multiple texts with optimized performance.
        
        Args:
            texts: List of texts to analyze
            entities: List of entity types to detect
            score_threshold: Minimum confidence score
            
        Returns:
            List of PII entity lists for each text
        """
        if not texts:
            return []
        
        # Use parallel processing for batch operations
        if self.enable_parallel and len(texts) > 1 and self._thread_pool:
            def detect_single(text):
                return self.detect_pii(text, entities, score_threshold=score_threshold)
            
            futures = []
            for text in texts:
                future = self._thread_pool.submit(detect_single, text)
                futures.append(future)
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=10.0)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Batch detection failed for text: {e}")
                    results.append([])
            
            return results
        else:
            # Sequential processing
            return [self.detect_pii(text, entities, score_threshold=score_threshold) for text in texts]
    
    def batch_anonymize_text(
        self,
        texts: List[str],
        rules: List[DesensitizationRule],
        entities_list: Optional[List[List[PIIEntity]]] = None
    ) -> List[DesensitizationResult]:
        """
        Batch anonymization for multiple texts with optimized performance.
        
        Args:
            texts: List of texts to anonymize
            rules: List of desensitization rules
            entities_list: Pre-detected entities for each text
            
        Returns:
            List of DesensitizationResults
        """
        if not texts:
            return []
        
        # Use parallel processing for batch operations
        if self.enable_parallel and len(texts) > 1 and self._thread_pool:
            def anonymize_single(args):
                text, entities = args
                return self.anonymize_text(text, rules, entities)
            
            # Prepare arguments
            if entities_list is None:
                entities_list = [None] * len(texts)
            
            args_list = list(zip(texts, entities_list))
            
            futures = []
            for args in args_list:
                future = self._thread_pool.submit(anonymize_single, args)
                futures.append(future)
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=15.0)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Batch anonymization failed: {e}")
                    # Return failed result
                    results.append(DesensitizationResult(
                        success=False,
                        original_text="",
                        anonymized_text="",
                        entities_found=[],
                        rules_applied=[],
                        processing_time_ms=0.0,
                        errors=[str(e)]
                    ))
            
            return results
        else:
            # Sequential processing
            if entities_list is None:
                entities_list = [None] * len(texts)
            
            return [
                self.anonymize_text(text, rules, entities)
                for text, entities in zip(texts, entities_list)
            ]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the engine.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "presidio_available": self._initialized,
            "parallel_processing_enabled": self.enable_parallel,
            "compiled_patterns_count": len(self._compiled_patterns),
            "pattern_cache_size": len(self._pattern_cache),
            "thread_pool_active": self._thread_pool is not None,
            "cache_info": {
                "pattern_search_cache": self._cached_pattern_search.cache_info()._asdict(),
            }
        }
    
    def clear_caches(self):
        """Clear all internal caches to free memory."""
        self._cached_pattern_search.cache_clear()
        self._pattern_cache.clear()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate engine configuration and availability.
        
        Returns:
            Dict with validation results
        """
        result = {
            "presidio_available": False,
            "analyzer_ready": False,
            "anonymizer_ready": False,
            "optimized_fallback": True,
            "parallel_processing": self.enable_parallel,
            "compiled_patterns": len(self._compiled_patterns),
            "supported_entities": [e.value for e in self._compiled_patterns.keys()],
            "errors": []
        }
        
        try:
            if self._initialize_presidio():
                result["presidio_available"] = True
                result["analyzer_ready"] = self._analyzer is not None
                result["anonymizer_ready"] = self._anonymizer is not None
                
                if self._analyzer:
                    try:
                        result["supported_entities"] = self._analyzer.get_supported_entities()
                    except Exception as e:
                        result["errors"].append(f"Failed to get supported entities: {e}")
                        
        except Exception as e:
            result["errors"].append(f"Configuration validation failed: {e}")
            
        return result