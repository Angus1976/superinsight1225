"""
Microsoft Presidio integration for PII detection and anonymization.
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Union

from .models import (
    DesensitizationRule,
    DesensitizationResult,
    MaskingStrategy,
    PIIEntity,
    PIIEntityType
)

logger = logging.getLogger(__name__)


class PresidioEngine:
    """
    Microsoft Presidio engine for PII detection and anonymization.
    
    Provides enterprise-grade PII detection and data masking capabilities
    using Microsoft Presidio analyzer and anonymizer.
    """
    
    def __init__(self, language: str = "en"):
        """
        Initialize Presidio engine.
        
        Args:
            language: Language code for analysis (default: "en")
        """
        self.language = language
        self._analyzer = None
        self._anonymizer = None
        self._nlp_engine = None
        self._initialized = False
        
    def _initialize_presidio(self) -> bool:
        """
        Initialize Presidio components lazily.
        
        Returns:
            bool: True if initialization successful
        """
        if self._initialized:
            return True
            
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
            
        except ImportError as e:
            logger.warning(f"Presidio not available: {e}. Using fallback implementation.")
            self._initialized = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Presidio: {e}")
            self._initialized = False
            return False
    
    def detect_pii(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        language: Optional[str] = None,
        score_threshold: float = 0.6
    ) -> List[PIIEntity]:
        """
        Detect PII entities in text.
        
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
            
        # Use fallback if Presidio not available
        if not self._initialize_presidio():
            return self._fallback_detect_pii(text, entities, score_threshold)
            
        try:
            # Analyze text with Presidio
            results = self._analyzer.analyze(
                text=text,
                entities=entities,
                language=language or self.language,
                score_threshold=score_threshold
            )
            
            # Convert to our PIIEntity format
            pii_entities = []
            for result in results:
                entity = PIIEntity(
                    entity_type=PIIEntityType(result.entity_type),
                    start=result.start,
                    end=result.end,
                    score=result.score,
                    text=text[result.start:result.end],
                    recognition_metadata=result.recognition_metadata or {}
                )
                pii_entities.append(entity)
                
            return pii_entities
            
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            return self._fallback_detect_pii(text, entities, score_threshold)
    
    def _fallback_detect_pii(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        score_threshold: float = 0.6
    ) -> List[PIIEntity]:
        """
        Fallback PII detection using regex patterns.
        
        Args:
            text: Text to analyze
            entities: List of entity types to detect
            score_threshold: Minimum confidence score
            
        Returns:
            List of detected PII entities
        """
        import re
        
        pii_entities = []
        
        # Define regex patterns for common PII types
        patterns = {
            PIIEntityType.EMAIL_ADDRESS: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            PIIEntityType.PHONE_NUMBER: r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            PIIEntityType.CREDIT_CARD: r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            PIIEntityType.IP_ADDRESS: r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            PIIEntityType.US_SSN: r'\b\d{3}-?\d{2}-?\d{4}\b',
        }
        
        # Filter patterns based on requested entities
        if entities:
            patterns = {k: v for k, v in patterns.items() if k.value in entities}
        
        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = PIIEntity(
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    score=0.8,  # Fixed score for regex matches
                    text=match.group(),
                    recognition_metadata={"method": "regex_fallback"}
                )
                pii_entities.append(entity)
        
        return pii_entities
    
    def anonymize_text(
        self,
        text: str,
        rules: List[DesensitizationRule],
        entities: Optional[List[PIIEntity]] = None
    ) -> DesensitizationResult:
        """
        Anonymize text using desensitization rules.
        
        Args:
            text: Text to anonymize
            rules: List of desensitization rules
            entities: Pre-detected entities (None to detect automatically)
            
        Returns:
            DesensitizationResult with anonymized text and metadata
        """
        start_time = time.time()
        
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
            
            # Use Presidio anonymizer if available
            if self._initialize_presidio():
                return self._presidio_anonymize(text, rules, entities, start_time)
            else:
                return self._fallback_anonymize(text, rules, entities, start_time)
                
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
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
    
    def _presidio_anonymize(
        self,
        text: str,
        rules: List[DesensitizationRule],
        entities: List[PIIEntity],
        start_time: float
    ) -> DesensitizationResult:
        """
        Anonymize using Presidio anonymizer.
        
        Args:
            text: Text to anonymize
            rules: Desensitization rules
            entities: Detected PII entities
            start_time: Processing start time
            
        Returns:
            DesensitizationResult
        """
        from presidio_anonymizer.entities import OperatorConfig
        
        # Create anonymizer operators based on rules
        operators = {}
        rules_applied = []
        
        for rule in rules:
            if not rule.enabled:
                continue
                
            operator_config = self._create_operator_config(rule)
            if operator_config:
                operators[rule.entity_type.value] = operator_config
                rules_applied.append(rule.name or rule.id)
        
        # Convert our entities to Presidio format
        presidio_entities = []
        for entity in entities:
            if entity.entity_type.value in operators:
                presidio_entities.append({
                    "entity_type": entity.entity_type.value,
                    "start": entity.start,
                    "end": entity.end
                })
        
        # Anonymize text
        try:
            result = self._anonymizer.anonymize(
                text=text,
                analyzer_results=presidio_entities,
                operators=operators
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            return DesensitizationResult(
                success=True,
                original_text=text,
                anonymized_text=result.text,
                entities_found=entities,
                rules_applied=rules_applied,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Presidio anonymization failed: {e}")
            return self._fallback_anonymize(text, rules, entities, start_time)
    
    def _create_operator_config(self, rule: DesensitizationRule) -> Optional[Any]:
        """
        Create Presidio operator config from desensitization rule.
        
        Args:
            rule: Desensitization rule
            
        Returns:
            Presidio OperatorConfig or None
        """
        try:
            from presidio_anonymizer.entities import OperatorConfig
            
            if rule.masking_strategy == MaskingStrategy.REPLACE:
                return OperatorConfig(
                    "replace",
                    {"new_value": rule.config.get("replacement", "***")}
                )
            elif rule.masking_strategy == MaskingStrategy.REDACT:
                return OperatorConfig("redact", {})
            elif rule.masking_strategy == MaskingStrategy.HASH:
                return OperatorConfig(
                    "hash",
                    {"hash_type": rule.config.get("hash_type", "sha256")}
                )
            elif rule.masking_strategy == MaskingStrategy.MASK:
                return OperatorConfig(
                    "mask",
                    {
                        "masking_char": rule.config.get("mask_char", "*"),
                        "chars_to_mask": rule.config.get("chars_to_mask", -1),
                        "from_end": rule.config.get("from_end", False)
                    }
                )
            elif rule.masking_strategy == MaskingStrategy.KEEP:
                return OperatorConfig("keep", {})
            
            return None
            
        except ImportError:
            return None
    
    def _fallback_anonymize(
        self,
        text: str,
        rules: List[DesensitizationRule],
        entities: List[PIIEntity],
        start_time: float
    ) -> DesensitizationResult:
        """
        Fallback anonymization without Presidio.
        
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
        
        # Create rule lookup by entity type
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
            masked_value = self._apply_masking_strategy(entity.text, rule)
            
            # Replace in text
            anonymized_text = (
                anonymized_text[:entity.start] +
                masked_value +
                anonymized_text[entity.end:]
            )
            
            if rule.name not in rules_applied:
                rules_applied.append(rule.name or rule.id)
        
        processing_time = (time.time() - start_time) * 1000
        
        return DesensitizationResult(
            success=True,
            original_text=text,
            anonymized_text=anonymized_text,
            entities_found=entities,
            rules_applied=rules_applied,
            processing_time_ms=processing_time
        )
    
    def _apply_masking_strategy(
        self,
        text: str,
        rule: DesensitizationRule
    ) -> str:
        """
        Apply masking strategy to text.
        
        Args:
            text: Text to mask
            rule: Desensitization rule
            
        Returns:
            Masked text
        """
        if rule.masking_strategy == MaskingStrategy.REPLACE:
            return rule.config.get("replacement", "***")
            
        elif rule.masking_strategy == MaskingStrategy.REDACT:
            return "[REDACTED]"
            
        elif rule.masking_strategy == MaskingStrategy.HASH:
            hash_type = rule.config.get("hash_type", "sha256")
            salt = rule.config.get("salt", "")
            
            if hash_type == "md5":
                return hashlib.md5((text + salt).encode()).hexdigest()[:8]
            else:  # Default to SHA256
                return hashlib.sha256((text + salt).encode()).hexdigest()[:8]
                
        elif rule.masking_strategy == MaskingStrategy.MASK:
            mask_char = rule.config.get("mask_char", "*")
            chars_to_mask = rule.config.get("chars_to_mask", -1)
            from_end = rule.config.get("from_end", False)
            
            if chars_to_mask == -1:
                return mask_char * len(text)
            elif from_end:
                return text[:-chars_to_mask] + mask_char * chars_to_mask
            else:
                return mask_char * chars_to_mask + text[chars_to_mask:]
                
        elif rule.masking_strategy == MaskingStrategy.KEEP:
            return text
            
        else:
            # Default to masking
            return "*" * len(text)
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate Presidio configuration and availability.
        
        Returns:
            Dict with validation results
        """
        result = {
            "presidio_available": False,
            "analyzer_ready": False,
            "anonymizer_ready": False,
            "supported_entities": [],
            "supported_languages": [],
            "errors": []
        }
        
        try:
            if self._initialize_presidio():
                result["presidio_available"] = True
                result["analyzer_ready"] = self._analyzer is not None
                result["anonymizer_ready"] = self._anonymizer is not None
                
                if self._analyzer:
                    # Get supported entities
                    try:
                        result["supported_entities"] = self._analyzer.get_supported_entities()
                    except Exception as e:
                        result["errors"].append(f"Failed to get supported entities: {e}")
                        
                    # Get supported languages
                    try:
                        result["supported_languages"] = self._analyzer.get_supported_languages()
                    except Exception as e:
                        result["errors"].append(f"Failed to get supported languages: {e}")
                        
        except Exception as e:
            result["errors"].append(f"Configuration validation failed: {e}")
            
        return result