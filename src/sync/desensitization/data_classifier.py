"""
Intelligent data classification and labeling system.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .models import (
    ClassificationResult,
    DatasetClassification,
    PIIEntity,
    PIIEntityType,
    SensitivityLevel,
    DesensitizationRule
)
from .presidio_engine import PresidioEngine

logger = logging.getLogger(__name__)


class DataClassifier:
    """
    Intelligent data classifier for automatic PII detection and sensitivity assessment.
    
    Provides automated data classification, sensitivity scoring, and compliance
    assessment capabilities for data governance and privacy protection.
    """
    
    def __init__(self, presidio_engine: Optional[PresidioEngine] = None):
        """
        Initialize data classifier.
        
        Args:
            presidio_engine: Optional Presidio engine instance
        """
        self.presidio_engine = presidio_engine or PresidioEngine()
        self._field_patterns = self._initialize_field_patterns()
        self._sensitivity_weights = self._initialize_sensitivity_weights()
    
    def classify_field(
        self,
        field_name: str,
        sample_values: List[Any],
        max_samples: int = 100
    ) -> ClassificationResult:
        """
        Classify a data field for PII content and sensitivity.
        
        Args:
            field_name: Name of the field
            sample_values: Sample values from the field
            max_samples: Maximum number of samples to analyze
            
        Returns:
            ClassificationResult with PII entities and sensitivity assessment
        """
        try:
            # Limit sample size for performance
            samples = sample_values[:max_samples]
            
            # Convert samples to strings and filter non-empty
            text_samples = []
            for value in samples:
                if value is not None:
                    text_str = str(value).strip()
                    if text_str:
                        text_samples.append(text_str)
            
            if not text_samples:
                return ClassificationResult(
                    field_name=field_name,
                    entities=[],
                    sensitivity_level=SensitivityLevel.LOW,
                    confidence_score=0.0,
                    requires_masking=False
                )
            
            # Analyze field name for patterns
            field_entities = self._analyze_field_name(field_name)
            
            # Analyze sample values for PII
            value_entities = self._analyze_sample_values(text_samples)
            
            # Combine and deduplicate entities
            all_entities = self._merge_entities(field_entities, value_entities)
            
            # Calculate sensitivity level and confidence
            sensitivity_level, confidence_score = self._calculate_sensitivity(
                field_name, all_entities, text_samples
            )
            
            # Determine if masking is required
            requires_masking = self._requires_masking(sensitivity_level, confidence_score)
            
            # Generate suggested rules
            suggested_rules = self._generate_suggested_rules(
                field_name, all_entities, sensitivity_level
            )
            
            return ClassificationResult(
                field_name=field_name,
                entities=all_entities,
                sensitivity_level=sensitivity_level,
                confidence_score=confidence_score,
                requires_masking=requires_masking,
                suggested_rules=suggested_rules
            )
            
        except Exception as e:
            logger.error(f"Field classification failed for {field_name}: {e}")
            return ClassificationResult(
                field_name=field_name,
                entities=[],
                sensitivity_level=SensitivityLevel.LOW,
                confidence_score=0.0,
                requires_masking=False
            )
    
    def classify_dataset(
        self,
        dataset_id: str,
        field_data: Dict[str, List[Any]],
        max_samples_per_field: int = 100
    ) -> DatasetClassification:
        """
        Classify an entire dataset for PII content and compliance.
        
        Args:
            dataset_id: Dataset identifier
            field_data: Dictionary mapping field names to sample values
            max_samples_per_field: Maximum samples to analyze per field
            
        Returns:
            DatasetClassification with overall assessment
        """
        try:
            field_classifications = []
            sensitive_field_count = 0
            total_confidence = 0.0
            
            # Classify each field
            for field_name, sample_values in field_data.items():
                classification = self.classify_field(
                    field_name, sample_values, max_samples_per_field
                )
                field_classifications.append(classification)
                
                if classification.requires_masking:
                    sensitive_field_count += 1
                
                total_confidence += classification.confidence_score
            
            # Calculate overall metrics
            total_fields = len(field_classifications)
            avg_confidence = total_confidence / total_fields if total_fields > 0 else 0.0
            
            # Determine overall sensitivity
            overall_sensitivity = self._calculate_overall_sensitivity(
                field_classifications, sensitive_field_count, total_fields
            )
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(
                field_classifications, sensitive_field_count, total_fields
            )
            
            # Generate recommendations
            recommendations = self._generate_dataset_recommendations(
                field_classifications, overall_sensitivity, compliance_score
            )
            
            return DatasetClassification(
                dataset_id=dataset_id,
                total_fields=total_fields,
                sensitive_fields=sensitive_field_count,
                field_classifications=field_classifications,
                overall_sensitivity=overall_sensitivity,
                compliance_score=compliance_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Dataset classification failed for {dataset_id}: {e}")
            return DatasetClassification(
                dataset_id=dataset_id,
                total_fields=0,
                sensitive_fields=0,
                field_classifications=[],
                overall_sensitivity=SensitivityLevel.LOW,
                compliance_score=0.0
            )
    
    def _analyze_field_name(self, field_name: str) -> List[PIIEntity]:
        """
        Analyze field name for PII indicators.
        
        Args:
            field_name: Field name to analyze
            
        Returns:
            List of potential PII entities based on field name
        """
        entities = []
        field_lower = field_name.lower()
        
        for entity_type, patterns in self._field_patterns.items():
            for pattern in patterns:
                if re.search(pattern, field_lower):
                    entity = PIIEntity(
                        entity_type=entity_type,
                        start=0,
                        end=len(field_name),
                        score=0.7,  # Field name matching gets moderate confidence
                        text=field_name,
                        recognition_metadata={"method": "field_name_pattern"}
                    )
                    entities.append(entity)
                    break  # Only match first pattern per entity type
        
        return entities
    
    def _analyze_sample_values(self, text_samples: List[str]) -> List[PIIEntity]:
        """
        Analyze sample values for PII content.
        
        Args:
            text_samples: List of text samples to analyze
            
        Returns:
            List of detected PII entities
        """
        all_entities = []
        
        # Analyze a subset of samples for performance
        analysis_samples = text_samples[:20]  # Limit to 20 samples
        
        for sample in analysis_samples:
            entities = self.presidio_engine.detect_pii(sample)
            all_entities.extend(entities)
        
        # Aggregate entities by type and calculate average confidence
        entity_stats = {}
        for entity in all_entities:
            entity_type = entity.entity_type
            if entity_type not in entity_stats:
                entity_stats[entity_type] = {
                    "count": 0,
                    "total_score": 0.0,
                    "examples": []
                }
            
            entity_stats[entity_type]["count"] += 1
            entity_stats[entity_type]["total_score"] += entity.score
            
            # Keep a few examples
            if len(entity_stats[entity_type]["examples"]) < 3:
                entity_stats[entity_type]["examples"].append(entity.text)
        
        # Create representative entities
        representative_entities = []
        for entity_type, stats in entity_stats.items():
            avg_score = stats["total_score"] / stats["count"]
            
            # Only include if found in multiple samples or high confidence
            if stats["count"] > 1 or avg_score > 0.8:
                entity = PIIEntity(
                    entity_type=entity_type,
                    start=0,
                    end=0,
                    score=avg_score,
                    text=f"Found in {stats['count']} samples",
                    recognition_metadata={
                        "method": "value_analysis",
                        "sample_count": stats["count"],
                        "examples": stats["examples"][:3]
                    }
                )
                representative_entities.append(entity)
        
        return representative_entities
    
    def _merge_entities(
        self,
        field_entities: List[PIIEntity],
        value_entities: List[PIIEntity]
    ) -> List[PIIEntity]:
        """
        Merge and deduplicate entities from field name and value analysis.
        
        Args:
            field_entities: Entities from field name analysis
            value_entities: Entities from value analysis
            
        Returns:
            Merged list of entities
        """
        merged_entities = []
        seen_types = set()
        
        # Prioritize value entities (higher confidence)
        for entity in value_entities:
            if entity.entity_type not in seen_types:
                merged_entities.append(entity)
                seen_types.add(entity.entity_type)
        
        # Add field entities for types not found in values
        for entity in field_entities:
            if entity.entity_type not in seen_types:
                merged_entities.append(entity)
                seen_types.add(entity.entity_type)
        
        return merged_entities
    
    def _calculate_sensitivity(
        self,
        field_name: str,
        entities: List[PIIEntity],
        samples: List[str]
    ) -> Tuple[SensitivityLevel, float]:
        """
        Calculate sensitivity level and confidence score.
        
        Args:
            field_name: Field name
            entities: Detected PII entities
            samples: Sample values
            
        Returns:
            Tuple of (sensitivity_level, confidence_score)
        """
        if not entities:
            return SensitivityLevel.LOW, 0.0
        
        # Calculate weighted sensitivity score
        total_weight = 0.0
        weighted_score = 0.0
        
        for entity in entities:
            entity_weight = self._sensitivity_weights.get(entity.entity_type, 1.0)
            weighted_score += entity.score * entity_weight
            total_weight += entity_weight
        
        if total_weight == 0:
            return SensitivityLevel.LOW, 0.0
        
        avg_weighted_score = weighted_score / total_weight
        
        # Determine sensitivity level based on entity types and scores
        max_entity_sensitivity = max(
            self._get_entity_sensitivity(entity.entity_type) for entity in entities
        )
        
        # Adjust based on confidence
        if avg_weighted_score >= 0.9:
            confidence_score = avg_weighted_score
        elif avg_weighted_score >= 0.7:
            confidence_score = avg_weighted_score * 0.9
        else:
            confidence_score = avg_weighted_score * 0.8
            # Lower sensitivity if confidence is low
            if max_entity_sensitivity == SensitivityLevel.CRITICAL:
                max_entity_sensitivity = SensitivityLevel.HIGH
            elif max_entity_sensitivity == SensitivityLevel.HIGH:
                max_entity_sensitivity = SensitivityLevel.MEDIUM
        
        return max_entity_sensitivity, confidence_score
    
    def _get_entity_sensitivity(self, entity_type: PIIEntityType) -> SensitivityLevel:
        """
        Get sensitivity level for an entity type.
        
        Args:
            entity_type: PII entity type
            
        Returns:
            Sensitivity level
        """
        critical_entities = {
            PIIEntityType.CREDIT_CARD,
            PIIEntityType.US_SSN,
            PIIEntityType.US_PASSPORT,
            PIIEntityType.MEDICAL_LICENSE
        }
        
        high_entities = {
            PIIEntityType.PERSON,
            PIIEntityType.PHONE_NUMBER,
            PIIEntityType.US_DRIVER_LICENSE,
            PIIEntityType.IBAN_CODE
        }
        
        medium_entities = {
            PIIEntityType.EMAIL_ADDRESS,
            PIIEntityType.LOCATION,
            PIIEntityType.DATE_TIME
        }
        
        if entity_type in critical_entities:
            return SensitivityLevel.CRITICAL
        elif entity_type in high_entities:
            return SensitivityLevel.HIGH
        elif entity_type in medium_entities:
            return SensitivityLevel.MEDIUM
        else:
            return SensitivityLevel.LOW
    
    def _requires_masking(
        self,
        sensitivity_level: SensitivityLevel,
        confidence_score: float
    ) -> bool:
        """
        Determine if field requires masking.
        
        Args:
            sensitivity_level: Sensitivity level
            confidence_score: Confidence score
            
        Returns:
            True if masking is required
        """
        if sensitivity_level == SensitivityLevel.CRITICAL:
            return confidence_score >= 0.6
        elif sensitivity_level == SensitivityLevel.HIGH:
            return confidence_score >= 0.7
        elif sensitivity_level == SensitivityLevel.MEDIUM:
            return confidence_score >= 0.8
        else:
            return False
    
    def _generate_suggested_rules(
        self,
        field_name: str,
        entities: List[PIIEntity],
        sensitivity_level: SensitivityLevel
    ) -> List[DesensitizationRule]:
        """
        Generate suggested desensitization rules.
        
        Args:
            field_name: Field name
            entities: Detected entities
            sensitivity_level: Sensitivity level
            
        Returns:
            List of suggested rules
        """
        suggested_rules = []
        
        for entity in entities:
            # Choose masking strategy based on entity type and sensitivity
            if entity.entity_type in {PIIEntityType.CREDIT_CARD, PIIEntityType.US_SSN}:
                strategy = "redact"
                config = {}
            elif entity.entity_type == PIIEntityType.PERSON:
                strategy = "replace"
                config = {"replacement": "[PERSON]"}
            elif entity.entity_type in {PIIEntityType.EMAIL_ADDRESS, PIIEntityType.PHONE_NUMBER}:
                strategy = "mask"
                config = {"mask_char": "*", "chars_to_mask": -1, "from_end": False}
            else:
                strategy = "mask"
                config = {"mask_char": "*", "chars_to_mask": 4, "from_end": True}
            
            rule = DesensitizationRule(
                name=f"Auto-generated rule for {field_name}",
                entity_type=entity.entity_type,
                masking_strategy=strategy,
                sensitivity_level=sensitivity_level,
                confidence_threshold=max(0.7, entity.score - 0.1),
                config=config
            )
            suggested_rules.append(rule)
        
        return suggested_rules
    
    def _calculate_overall_sensitivity(
        self,
        field_classifications: List[ClassificationResult],
        sensitive_fields: int,
        total_fields: int
    ) -> SensitivityLevel:
        """
        Calculate overall dataset sensitivity.
        
        Args:
            field_classifications: Field classification results
            sensitive_fields: Number of sensitive fields
            total_fields: Total number of fields
            
        Returns:
            Overall sensitivity level
        """
        if total_fields == 0:
            return SensitivityLevel.LOW
        
        # Count fields by sensitivity level
        sensitivity_counts = {
            SensitivityLevel.CRITICAL: 0,
            SensitivityLevel.HIGH: 0,
            SensitivityLevel.MEDIUM: 0,
            SensitivityLevel.LOW: 0
        }
        
        for classification in field_classifications:
            sensitivity_counts[classification.sensitivity_level] += 1
        
        # Determine overall sensitivity
        critical_ratio = sensitivity_counts[SensitivityLevel.CRITICAL] / total_fields
        high_ratio = sensitivity_counts[SensitivityLevel.HIGH] / total_fields
        medium_ratio = sensitivity_counts[SensitivityLevel.MEDIUM] / total_fields
        
        if critical_ratio > 0.1:  # More than 10% critical fields
            return SensitivityLevel.CRITICAL
        elif critical_ratio > 0 or high_ratio > 0.2:  # Any critical or >20% high
            return SensitivityLevel.HIGH
        elif high_ratio > 0 or medium_ratio > 0.3:  # Any high or >30% medium
            return SensitivityLevel.MEDIUM
        else:
            return SensitivityLevel.LOW
    
    def _calculate_compliance_score(
        self,
        field_classifications: List[ClassificationResult],
        sensitive_fields: int,
        total_fields: int
    ) -> float:
        """
        Calculate compliance score (0-100).
        
        Args:
            field_classifications: Field classification results
            sensitive_fields: Number of sensitive fields
            total_fields: Total number of fields
            
        Returns:
            Compliance score as percentage
        """
        if total_fields == 0:
            return 100.0
        
        # Base score starts at 100
        score = 100.0
        
        # Deduct points for unmasked sensitive fields
        for classification in field_classifications:
            if classification.requires_masking:
                # Deduct more points for higher sensitivity
                if classification.sensitivity_level == SensitivityLevel.CRITICAL:
                    score -= 20.0
                elif classification.sensitivity_level == SensitivityLevel.HIGH:
                    score -= 15.0
                elif classification.sensitivity_level == SensitivityLevel.MEDIUM:
                    score -= 10.0
        
        return max(0.0, score)
    
    def _generate_dataset_recommendations(
        self,
        field_classifications: List[ClassificationResult],
        overall_sensitivity: SensitivityLevel,
        compliance_score: float
    ) -> List[str]:
        """
        Generate recommendations for dataset compliance.
        
        Args:
            field_classifications: Field classification results
            overall_sensitivity: Overall sensitivity level
            compliance_score: Compliance score
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Count fields requiring masking
        fields_needing_masking = [
            c for c in field_classifications if c.requires_masking
        ]
        
        if fields_needing_masking:
            recommendations.append(
                f"Apply data masking to {len(fields_needing_masking)} sensitive fields"
            )
        
        # Sensitivity-specific recommendations
        if overall_sensitivity == SensitivityLevel.CRITICAL:
            recommendations.extend([
                "Implement strict access controls and audit logging",
                "Consider data encryption at rest and in transit",
                "Establish data retention and deletion policies"
            ])
        elif overall_sensitivity == SensitivityLevel.HIGH:
            recommendations.extend([
                "Implement role-based access controls",
                "Enable audit logging for data access",
                "Consider additional data protection measures"
            ])
        
        # Compliance-specific recommendations
        if compliance_score < 70:
            recommendations.append("Urgent: Address compliance gaps to meet regulatory requirements")
        elif compliance_score < 85:
            recommendations.append("Improve data protection measures to enhance compliance")
        
        # Field-specific recommendations
        critical_fields = [
            c.field_name for c in field_classifications
            if c.sensitivity_level == SensitivityLevel.CRITICAL
        ]
        if critical_fields:
            recommendations.append(
                f"Priority: Secure critical fields: {', '.join(critical_fields[:3])}"
            )
        
        return recommendations
    
    def _initialize_field_patterns(self) -> Dict[PIIEntityType, List[str]]:
        """
        Initialize field name patterns for PII detection.
        
        Returns:
            Dictionary mapping entity types to regex patterns
        """
        return {
            PIIEntityType.PERSON: [
                r'.*name.*', r'.*person.*', r'.*user.*', r'.*customer.*',
                r'.*client.*', r'.*contact.*', r'.*owner.*', r'.*author.*'
            ],
            PIIEntityType.EMAIL_ADDRESS: [
                r'.*email.*', r'.*mail.*', r'.*contact.*'
            ],
            PIIEntityType.PHONE_NUMBER: [
                r'.*phone.*', r'.*tel.*', r'.*mobile.*', r'.*cell.*',
                r'.*number.*', r'.*contact.*'
            ],
            PIIEntityType.CREDIT_CARD: [
                r'.*card.*', r'.*credit.*', r'.*payment.*', r'.*cc.*'
            ],
            PIIEntityType.US_SSN: [
                r'.*ssn.*', r'.*social.*', r'.*security.*'
            ],
            PIIEntityType.IP_ADDRESS: [
                r'.*ip.*', r'.*address.*', r'.*host.*'
            ],
            PIIEntityType.LOCATION: [
                r'.*address.*', r'.*location.*', r'.*city.*', r'.*state.*',
                r'.*country.*', r'.*zip.*', r'.*postal.*'
            ],
            PIIEntityType.DATE_TIME: [
                r'.*date.*', r'.*time.*', r'.*birth.*', r'.*dob.*',
                r'.*created.*', r'.*modified.*'
            ]
        }
    
    def _initialize_sensitivity_weights(self) -> Dict[PIIEntityType, float]:
        """
        Initialize sensitivity weights for entity types.
        
        Returns:
            Dictionary mapping entity types to weight values
        """
        return {
            PIIEntityType.CREDIT_CARD: 3.0,
            PIIEntityType.US_SSN: 3.0,
            PIIEntityType.US_PASSPORT: 2.5,
            PIIEntityType.MEDICAL_LICENSE: 2.5,
            PIIEntityType.PERSON: 2.0,
            PIIEntityType.PHONE_NUMBER: 2.0,
            PIIEntityType.US_DRIVER_LICENSE: 2.0,
            PIIEntityType.EMAIL_ADDRESS: 1.5,
            PIIEntityType.LOCATION: 1.5,
            PIIEntityType.DATE_TIME: 1.0,
            PIIEntityType.IP_ADDRESS: 1.0,
            PIIEntityType.URL: 0.5
        }