"""Annotation PII Detection and Desensitization Service.

This module provides comprehensive PII detection and desensitization for AI annotation:
- Automatic PII detection (email, phone, ID numbers, etc.)
- Chinese-specific PII detection (身份证, 手机号, 银行卡)
- Multiple desensitization strategies (mask, replace, hash, encrypt)
- Reversible desensitization for internal use
- Integration with audit logging
- Compliance with privacy regulations

Requirements:
- 7.3: Sensitive data desensitization
"""

import re
import hashlib
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
import base64


class PIIType(str, Enum):
    """Type of personally identifiable information."""
    # Contact information
    EMAIL = "email"
    PHONE = "phone"
    PHONE_CN = "phone_cn"  # Chinese mobile number

    # Identity documents
    ID_NUMBER_CN = "id_number_cn"  # Chinese ID card
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"

    # Financial
    CREDIT_CARD = "credit_card"
    BANK_CARD_CN = "bank_card_cn"  # Chinese bank card
    USCC = "uscc"  # Unified Social Credit Code

    # Personal data
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    IP_ADDRESS = "ip_address"

    # Sensitive content
    PASSWORD = "password"
    SECRET_KEY = "secret_key"
    API_KEY = "api_key"


class DesensitizationStrategy(str, Enum):
    """Strategy for desensitizing PII."""
    MASK = "mask"  # Replace with asterisks
    PARTIAL_MASK = "partial_mask"  # Show first/last chars
    REPLACE = "replace"  # Replace with placeholder
    HASH = "hash"  # One-way hash
    ENCRYPT = "encrypt"  # Reversible encryption
    REMOVE = "remove"  # Remove completely


@dataclass
class PIIPattern:
    """Pattern for detecting PII."""
    pii_type: PIIType
    pattern: str  # Regex pattern
    description: str
    examples: List[str] = field(default_factory=list)
    severity: str = "high"  # high, medium, low


@dataclass
class PIIDetection:
    """Detected PII instance."""
    detection_id: UUID = field(default_factory=uuid4)
    pii_type: PIIType = PIIType.EMAIL
    text: str = ""
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 1.0
    context: str = ""  # Surrounding text


@dataclass
class DesensitizationResult:
    """Result of desensitization operation."""
    original_text: str = ""
    desensitized_text: str = ""
    detections: List[PIIDetection] = field(default_factory=list)
    mapping: Dict[str, str] = field(default_factory=dict)  # original -> desensitized
    strategy: DesensitizationStrategy = DesensitizationStrategy.MASK
    is_reversible: bool = False
    processed_at: datetime = field(default_factory=datetime.utcnow)


class AnnotationPIIService:
    """Service for PII detection and desensitization in annotations."""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize PII service.

        Args:
            encryption_key: Optional key for reversible encryption
        """
        self._lock = asyncio.Lock()
        self._encryption_key = encryption_key or "default_pii_encryption_key"

        # Detection patterns
        self._patterns: Dict[PIIType, PIIPattern] = {
            # Email
            PIIType.EMAIL: PIIPattern(
                pii_type=PIIType.EMAIL,
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                description="Email address",
                examples=["user@example.com", "john.doe@company.co.uk"],
                severity="high"
            ),

            # Chinese mobile phone
            PIIType.PHONE_CN: PIIPattern(
                pii_type=PIIType.PHONE_CN,
                pattern=r'\b1[3-9]\d{9}\b',
                description="Chinese mobile phone number",
                examples=["13812345678", "18988776655"],
                severity="high"
            ),

            # International phone (basic)
            PIIType.PHONE: PIIPattern(
                pii_type=PIIType.PHONE,
                pattern=r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
                description="International phone number",
                examples=["+1-555-123-4567", "(555) 123-4567"],
                severity="high"
            ),

            # Chinese ID number (18 digits)
            PIIType.ID_NUMBER_CN: PIIPattern(
                pii_type=PIIType.ID_NUMBER_CN,
                pattern=r'\b[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b',
                description="Chinese ID card number (18 digits)",
                examples=["110101199001011234"],
                severity="high"
            ),

            # Credit card (basic Luhn check not included)
            PIIType.CREDIT_CARD: PIIPattern(
                pii_type=PIIType.CREDIT_CARD,
                pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                description="Credit card number",
                examples=["4532-1234-5678-9010", "5425 2334 3010 9903"],
                severity="high"
            ),

            # Chinese bank card (16-19 digits)
            PIIType.BANK_CARD_CN: PIIPattern(
                pii_type=PIIType.BANK_CARD_CN,
                pattern=r'\b\d{16,19}\b',
                description="Chinese bank card number",
                examples=["6222021234567890123"],
                severity="high"
            ),

            # Unified Social Credit Code (18 chars)
            PIIType.USCC: PIIPattern(
                pii_type=PIIType.USCC,
                pattern=r'\b[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}\b',
                description="Unified Social Credit Code",
                examples=["91110000600000000X"],
                severity="medium"
            ),

            # IP Address
            PIIType.IP_ADDRESS: PIIPattern(
                pii_type=PIIType.IP_ADDRESS,
                pattern=r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                description="IP address",
                examples=["192.168.1.1", "10.0.0.1"],
                severity="medium"
            ),

            # API Key (basic pattern)
            PIIType.API_KEY: PIIPattern(
                pii_type=PIIType.API_KEY,
                pattern=r'\b[A-Za-z0-9_-]{32,}\b',
                description="API key or secret token",
                examples=["sk-1234567890abcdefghijklmnopqrstuvwxyz"],
                severity="high"
            ),
        }

        # Desensitization cache for reversible operations
        self._desensitization_cache: Dict[str, str] = {}  # original -> desensitized
        self._reverse_cache: Dict[str, str] = {}  # desensitized -> original

    async def detect_pii(
        self,
        text: str,
        pii_types: Optional[List[PIIType]] = None
    ) -> List[PIIDetection]:
        """Detect PII in text.

        Args:
            text: Text to scan for PII
            pii_types: Optional list of PII types to detect (default: all)

        Returns:
            List of detected PII instances
        """
        async with self._lock:
            detections = []

            # Determine which patterns to use
            patterns_to_check = self._patterns
            if pii_types:
                patterns_to_check = {
                    pii_type: pattern
                    for pii_type, pattern in self._patterns.items()
                    if pii_type in pii_types
                }

            # Scan text with each pattern
            for pii_type, pattern_def in patterns_to_check.items():
                matches = re.finditer(pattern_def.pattern, text)

                for match in matches:
                    # Get context (20 chars before and after)
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end]

                    detection = PIIDetection(
                        pii_type=pii_type,
                        text=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=self._calculate_confidence(pii_type, match.group()),
                        context=context
                    )
                    detections.append(detection)

            # Sort by position
            detections.sort(key=lambda d: d.start_pos)

            return detections

    def _calculate_confidence(self, pii_type: PIIType, text: str) -> float:
        """Calculate confidence score for detected PII.

        Args:
            pii_type: Type of PII
            text: Detected text

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Basic confidence calculation
        # Could be enhanced with ML models

        # Email: check for common domains
        if pii_type == PIIType.EMAIL:
            common_domains = [".com", ".cn", ".org", ".net", ".edu"]
            if any(domain in text.lower() for domain in common_domains):
                return 0.95
            return 0.7

        # Chinese ID: validate checksum
        if pii_type == PIIType.ID_NUMBER_CN:
            if self._validate_chinese_id_checksum(text):
                return 0.98
            return 0.6

        # Default confidence
        return 0.85

    def _validate_chinese_id_checksum(self, id_number: str) -> bool:
        """Validate Chinese ID number checksum.

        Args:
            id_number: 18-digit ID number

        Returns:
            True if checksum is valid
        """
        if len(id_number) != 18:
            return False

        # Weight factors
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

        try:
            # Calculate sum
            total = sum(int(id_number[i]) * weights[i] for i in range(17))
            # Get check code
            check_index = total % 11
            expected_check = check_codes[check_index]

            return id_number[17].upper() == expected_check
        except (ValueError, IndexError):
            return False

    async def desensitize(
        self,
        text: str,
        strategy: DesensitizationStrategy = DesensitizationStrategy.PARTIAL_MASK,
        pii_types: Optional[List[PIIType]] = None,
        preserve_structure: bool = True
    ) -> DesensitizationResult:
        """Desensitize PII in text.

        Args:
            text: Text to desensitize
            strategy: Desensitization strategy
            pii_types: Optional list of PII types to desensitize
            preserve_structure: Preserve text structure (length, format)

        Returns:
            Desensitization result
        """
        # Detect PII
        detections = await self.detect_pii(text, pii_types)

        if not detections:
            return DesensitizationResult(
                original_text=text,
                desensitized_text=text,
                detections=[],
                mapping={},
                strategy=strategy
            )

        # Build desensitized text
        desensitized = text
        mapping = {}
        offset = 0  # Track position changes

        for detection in detections:
            original = detection.text
            desensitized_value = self._apply_strategy(
                original,
                detection.pii_type,
                strategy,
                preserve_structure
            )

            # Replace in text
            start = detection.start_pos + offset
            end = detection.end_pos + offset
            desensitized = desensitized[:start] + desensitized_value + desensitized[end:]

            # Update offset
            offset += len(desensitized_value) - len(original)

            # Store mapping
            mapping[original] = desensitized_value

        return DesensitizationResult(
            original_text=text,
            desensitized_text=desensitized,
            detections=detections,
            mapping=mapping,
            strategy=strategy,
            is_reversible=(strategy == DesensitizationStrategy.ENCRYPT)
        )

    def _apply_strategy(
        self,
        value: str,
        pii_type: PIIType,
        strategy: DesensitizationStrategy,
        preserve_structure: bool
    ) -> str:
        """Apply desensitization strategy to a value.

        Args:
            value: Original value
            pii_type: Type of PII
            strategy: Desensitization strategy
            preserve_structure: Preserve structure

        Returns:
            Desensitized value
        """
        if strategy == DesensitizationStrategy.MASK:
            return "*" * len(value)

        elif strategy == DesensitizationStrategy.PARTIAL_MASK:
            return self._partial_mask(value, pii_type)

        elif strategy == DesensitizationStrategy.REPLACE:
            return self._get_placeholder(pii_type)

        elif strategy == DesensitizationStrategy.HASH:
            return self._hash_value(value)

        elif strategy == DesensitizationStrategy.ENCRYPT:
            return self._encrypt_value(value)

        elif strategy == DesensitizationStrategy.REMOVE:
            return ""

        return value

    def _partial_mask(self, value: str, pii_type: PIIType) -> str:
        """Partially mask a value (show first/last chars).

        Args:
            value: Original value
            pii_type: Type of PII

        Returns:
            Partially masked value
        """
        if len(value) <= 4:
            return "*" * len(value)

        # Different masking rules for different PII types
        if pii_type == PIIType.EMAIL:
            # Show first 2 chars before @
            at_pos = value.find("@")
            if at_pos > 2:
                return value[:2] + "***" + value[at_pos:]
            return "***" + value[at_pos:]

        elif pii_type in [PIIType.PHONE, PIIType.PHONE_CN]:
            # Show first 3 and last 4
            return value[:3] + "*" * (len(value) - 7) + value[-4:]

        elif pii_type == PIIType.ID_NUMBER_CN:
            # Show first 6 and last 4
            return value[:6] + "*" * 8 + value[-4:]

        elif pii_type in [PIIType.CREDIT_CARD, PIIType.BANK_CARD_CN]:
            # Show last 4 digits
            return "*" * (len(value) - 4) + value[-4:]

        else:
            # Default: show first 2 and last 2
            return value[:2] + "*" * (len(value) - 4) + value[-2:]

    def _get_placeholder(self, pii_type: PIIType) -> str:
        """Get placeholder text for PII type.

        Args:
            pii_type: Type of PII

        Returns:
            Placeholder text
        """
        placeholders = {
            PIIType.EMAIL: "[EMAIL]",
            PIIType.PHONE: "[PHONE]",
            PIIType.PHONE_CN: "[手机号]",
            PIIType.ID_NUMBER_CN: "[身份证号]",
            PIIType.CREDIT_CARD: "[CARD]",
            PIIType.BANK_CARD_CN: "[银行卡号]",
            PIIType.USCC: "[社会信用代码]",
            PIIType.NAME: "[NAME]",
            PIIType.ADDRESS: "[ADDRESS]",
            PIIType.IP_ADDRESS: "[IP]",
            PIIType.API_KEY: "[API_KEY]",
        }
        return placeholders.get(pii_type, "[REDACTED]")

    def _hash_value(self, value: str) -> str:
        """Create one-way hash of value.

        Args:
            value: Original value

        Returns:
            Hashed value
        """
        hash_bytes = hashlib.sha256(value.encode()).digest()
        return base64.b64encode(hash_bytes[:8]).decode()  # Truncated hash

    def _encrypt_value(self, value: str) -> str:
        """Encrypt value (simple XOR for demo - use proper encryption in production).

        Args:
            value: Original value

        Returns:
            Encrypted value
        """
        # Simple XOR encryption (for demo purposes)
        # In production, use proper encryption (AES, Fernet, etc.)
        key_bytes = self._encryption_key.encode()
        value_bytes = value.encode()

        encrypted = bytearray()
        for i, byte in enumerate(value_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])

        return base64.b64encode(encrypted).decode()

    def _decrypt_value(self, encrypted: str) -> str:
        """Decrypt value (simple XOR for demo).

        Args:
            encrypted: Encrypted value

        Returns:
            Decrypted value
        """
        # XOR decryption (symmetric)
        encrypted_bytes = base64.b64decode(encrypted)
        key_bytes = self._encryption_key.encode()

        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])

        return decrypted.decode()

    async def desensitize_for_llm(
        self,
        text: str,
        tenant_id: UUID,
        user_id: UUID,
        audit_service: Optional[Any] = None
    ) -> DesensitizationResult:
        """Desensitize text before sending to external LLM.

        This method uses aggressive desensitization for external LLM calls.

        Args:
            text: Text to desensitize
            tenant_id: Tenant ID (for audit)
            user_id: User ID (for audit)
            audit_service: Optional audit service for logging

        Returns:
            Desensitization result
        """
        # Use partial masking to preserve some context
        result = await self.desensitize(
            text=text,
            strategy=DesensitizationStrategy.PARTIAL_MASK,
            preserve_structure=True
        )

        # Log desensitization to audit if service provided
        if audit_service and result.detections:
            try:
                from .annotation_audit_service import (
                    AnnotationOperationType,
                    AnnotationObjectType
                )
                await audit_service.log_operation(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation_type=AnnotationOperationType.UPDATE,
                    object_type=AnnotationObjectType.ANNOTATION,
                    object_id=uuid4(),
                    operation_description=f"PII desensitization: {len(result.detections)} instances detected and masked",
                    before_state={"text_length": len(text)},
                    after_state={
                        "detections": len(result.detections),
                        "pii_types": list(set(d.pii_type.value for d in result.detections))
                    }
                )
            except Exception as e:
                # Don't fail desensitization if audit logging fails
                pass

        return result

    async def get_statistics(
        self,
        text_samples: List[str]
    ) -> Dict[str, Any]:
        """Get PII detection statistics for text samples.

        Args:
            text_samples: List of text samples to analyze

        Returns:
            Dictionary of statistics
        """
        total_detections = 0
        pii_type_counts = {}
        total_chars = 0
        pii_chars = 0

        for text in text_samples:
            detections = await self.detect_pii(text)
            total_detections += len(detections)
            total_chars += len(text)

            for detection in detections:
                pii_type_counts[detection.pii_type.value] = \
                    pii_type_counts.get(detection.pii_type.value, 0) + 1
                pii_chars += len(detection.text)

        return {
            "total_samples": len(text_samples),
            "total_detections": total_detections,
            "avg_detections_per_sample": total_detections / len(text_samples) if text_samples else 0,
            "pii_type_distribution": pii_type_counts,
            "pii_char_ratio": (pii_chars / total_chars) if total_chars > 0 else 0,
            "most_common_pii_type": max(pii_type_counts.items(), key=lambda x: x[1])[0] if pii_type_counts else None
        }


# Global instance
_annotation_pii_service: Optional[AnnotationPIIService] = None
_pii_lock = asyncio.Lock()


async def get_annotation_pii_service(
    encryption_key: Optional[str] = None
) -> AnnotationPIIService:
    """Get or create the global annotation PII service.

    Args:
        encryption_key: Optional encryption key

    Returns:
        Annotation PII service instance
    """
    global _annotation_pii_service

    async with _pii_lock:
        if _annotation_pii_service is None:
            _annotation_pii_service = AnnotationPIIService(
                encryption_key=encryption_key
            )
        return _annotation_pii_service


async def reset_annotation_pii_service():
    """Reset the global annotation PII service (for testing)."""
    global _annotation_pii_service

    async with _pii_lock:
        _annotation_pii_service = None
