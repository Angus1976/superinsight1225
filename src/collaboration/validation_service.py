"""Validation Service for ontology elements with Chinese business identifier validators.

This module provides comprehensive validation capabilities for ontology elements,
including:
- Chinese business identifier validators (统一社会信用代码, 组织机构代码, 营业执照号)
- Chinese contract and seal validators
- Region-specific validation rules (CN, HK, TW, INTL)
- Industry-specific validation rules
- Localized error message generation

Requirements:
- 5.1: Chinese business identifier validation
- 5.2: Contract and seal usage validation
- 5.3: Seal authorization and recording
- 5.4: Regional validation configuration
- 5.5: Localized error messages
"""

import re
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class Region(str, Enum):
    """Geographic regions for validation rules."""
    CN = "CN"  # Mainland China
    HK = "HK"  # Hong Kong
    TW = "TW"  # Taiwan
    INTL = "INTL"  # International


class Industry(str, Enum):
    """Industry sectors for validation rules."""
    FINANCE = "金融"
    HEALTHCARE = "医疗"
    MANUFACTURING = "制造"
    RETAIL = "零售"
    EDUCATION = "教育"
    GOVERNMENT = "政府"
    LOGISTICS = "物流"
    REAL_ESTATE = "房地产"
    TECHNOLOGY = "科技"
    GENERAL = "通用"


class SealType(str, Enum):
    """Types of Chinese company seals."""
    COMPANY = "公章"  # Official company seal
    CONTRACT = "合同章"  # Contract seal
    FINANCIAL = "财务章"  # Financial seal
    LEGAL = "法人章"  # Legal representative seal
    INVOICE = "发票章"  # Invoice seal


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    ERROR = "ERROR"  # Blocking error
    WARNING = "WARNING"  # Non-blocking warning
    INFO = "INFO"  # Informational message


@dataclass
class ValidationRule:
    """Validation rule for ontology elements."""
    rule_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    region: Region = Region.CN
    industry: Industry = Industry.GENERAL
    validator_type: str = ""  # "regex", "function", "chinese_business_id", etc.
    validator_config: Dict[str, Any] = field(default_factory=dict)
    error_message_key: str = ""  # i18n key
    severity: ValidationSeverity = ValidationSeverity.ERROR
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class ValidationError:
    """Validation error for an ontology element."""
    error_id: UUID = field(default_factory=uuid4)
    element_id: Optional[UUID] = None
    element_type: str = ""  # "entity_type", "relation_type", "attribute", etc.
    rule_id: UUID = field(default_factory=uuid4)
    field_name: str = ""
    error_message: str = ""
    error_message_zh: str = ""
    error_message_en: str = ""
    severity: ValidationSeverity = ValidationSeverity.ERROR
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    info_messages: List[ValidationError] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContractEntity:
    """Contract entity for validation."""
    contract_id: str = ""
    contract_number: str = ""
    parties: List[str] = field(default_factory=list)
    seal_records: List[Dict[str, Any]] = field(default_factory=list)
    approval_status: str = ""  # "pending", "approved", "rejected"
    required_fields: Set[str] = field(default_factory=lambda: {
        "contract_number", "parties", "effective_date", "signing_date"
    })


class ChineseBusinessIdentifierValidator:
    """Validators for Chinese business identifiers.

    Supports:
    - 统一社会信用代码 (Unified Social Credit Code) - 18 characters
    - 组织机构代码 (Organization Code) - 9 characters
    - 营业执照号 (Business License Number)
    """

    # Character mapping for checksum calculation
    USCC_CHARS = "0123456789ABCDEFGHJKLMNPQRTUWXY"
    ORG_CODE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Weights for checksum calculation
    USCC_WEIGHTS = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
    ORG_CODE_WEIGHTS = [3, 7, 9, 10, 5, 8, 4, 2]

    @staticmethod
    def validate_uscc(code: str) -> tuple[bool, Optional[str]]:
        """Validate Unified Social Credit Code (统一社会信用代码).

        Format: 18 characters [0-9A-Z except I,O,S,V,Z]
        Structure:
        - Position 1: Registration authority (1-9, A-Y)
        - Position 2: Organization type (1-9, A-Y)
        - Position 3-8: Administrative division code (6 digits)
        - Position 9-17: Organization body code (9 chars)
        - Position 18: Check code

        Args:
            code: USCC to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not code:
            return False, "validation.uscc.empty"

        # Remove whitespace
        code = code.strip().upper()

        # Check length
        if len(code) != 18:
            return False, "validation.uscc.invalid_length"

        # Check characters
        if not all(c in ChineseBusinessIdentifierValidator.USCC_CHARS for c in code):
            return False, "validation.uscc.invalid_characters"

        # Calculate checksum
        try:
            checksum = 0
            for i in range(17):
                char_value = ChineseBusinessIdentifierValidator.USCC_CHARS.index(code[i])
                checksum += char_value * ChineseBusinessIdentifierValidator.USCC_WEIGHTS[i]

            remainder = checksum % 31
            check_code_index = (31 - remainder) % 31
            expected_check_code = ChineseBusinessIdentifierValidator.USCC_CHARS[check_code_index]

            if code[17] != expected_check_code:
                return False, "validation.uscc.invalid_checksum"

            return True, None

        except (ValueError, IndexError):
            return False, "validation.uscc.calculation_error"

    @staticmethod
    def validate_organization_code(code: str) -> tuple[bool, Optional[str]]:
        """Validate Organization Code (组织机构代码).

        Format: 9 characters [0-9A-Z]
        Structure:
        - Position 1-8: Organization code (8 chars)
        - Position 9: Check code

        Args:
            code: Organization code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not code:
            return False, "validation.org_code.empty"

        # Remove whitespace and hyphens
        code = code.strip().upper().replace("-", "")

        # Check length
        if len(code) != 9:
            return False, "validation.org_code.invalid_length"

        # Check characters
        if not all(c in ChineseBusinessIdentifierValidator.ORG_CODE_CHARS for c in code):
            return False, "validation.org_code.invalid_characters"

        # Calculate checksum
        try:
            checksum = 0
            for i in range(8):
                char_value = ChineseBusinessIdentifierValidator.ORG_CODE_CHARS.index(code[i])
                checksum += char_value * ChineseBusinessIdentifierValidator.ORG_CODE_WEIGHTS[i]

            remainder = 11 - (checksum % 11)

            # Determine expected check code
            if remainder == 10:
                expected_check_code = 'X'
            elif remainder == 11:
                expected_check_code = '0'
            else:
                expected_check_code = str(remainder)

            if code[8] != expected_check_code:
                return False, "validation.org_code.invalid_checksum"

            return True, None

        except (ValueError, IndexError):
            return False, "validation.org_code.calculation_error"

    @staticmethod
    def validate_business_license(license_number: str) -> tuple[bool, Optional[str]]:
        """Validate Business License Number (营业执照号).

        Business license numbers can be in various formats:
        - Old format: 15 digits
        - New format (USCC): 18 characters

        Args:
            license_number: Business license number to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not license_number:
            return False, "validation.business_license.empty"

        license_number = license_number.strip()

        # Check if it's new format (USCC)
        if len(license_number) == 18:
            return ChineseBusinessIdentifierValidator.validate_uscc(license_number)

        # Check old format (15 digits)
        elif len(license_number) == 15:
            if not license_number.isdigit():
                return False, "validation.business_license.old_format_invalid"
            return True, None

        else:
            return False, "validation.business_license.invalid_length"


class ValidationService:
    """Service for validating ontology elements with regional and industry-specific rules."""

    def __init__(self):
        """Initialize validation service."""
        self._rules: Dict[UUID, ValidationRule] = {}
        self._rules_by_region: Dict[Region, List[UUID]] = {region: [] for region in Region}
        self._rules_by_industry: Dict[Industry, List[UUID]] = {industry: [] for industry in Industry}
        self._lock = asyncio.Lock()

        # Cache for frequently accessed rules
        self._rule_cache: Dict[str, List[ValidationRule]] = {}
        self._cache_ttl = 1800  # 30 minutes

        # i18n error messages
        self._error_messages = {
            # USCC errors
            "validation.uscc.empty": {
                "zh-CN": "统一社会信用代码不能为空",
                "en-US": "Unified Social Credit Code cannot be empty"
            },
            "validation.uscc.invalid_length": {
                "zh-CN": "统一社会信用代码必须为18位",
                "en-US": "Unified Social Credit Code must be 18 characters"
            },
            "validation.uscc.invalid_characters": {
                "zh-CN": "统一社会信用代码包含非法字符(不允许I、O、S、V、Z)",
                "en-US": "Unified Social Credit Code contains invalid characters (I, O, S, V, Z not allowed)"
            },
            "validation.uscc.invalid_checksum": {
                "zh-CN": "统一社会信用代码校验位错误",
                "en-US": "Unified Social Credit Code checksum is invalid"
            },
            "validation.uscc.calculation_error": {
                "zh-CN": "统一社会信用代码校验计算错误",
                "en-US": "Unified Social Credit Code checksum calculation error"
            },

            # Organization code errors
            "validation.org_code.empty": {
                "zh-CN": "组织机构代码不能为空",
                "en-US": "Organization code cannot be empty"
            },
            "validation.org_code.invalid_length": {
                "zh-CN": "组织机构代码必须为9位",
                "en-US": "Organization code must be 9 characters"
            },
            "validation.org_code.invalid_characters": {
                "zh-CN": "组织机构代码包含非法字符",
                "en-US": "Organization code contains invalid characters"
            },
            "validation.org_code.invalid_checksum": {
                "zh-CN": "组织机构代码校验位错误",
                "en-US": "Organization code checksum is invalid"
            },
            "validation.org_code.calculation_error": {
                "zh-CN": "组织机构代码校验计算错误",
                "en-US": "Organization code checksum calculation error"
            },

            # Business license errors
            "validation.business_license.empty": {
                "zh-CN": "营业执照号不能为空",
                "en-US": "Business license number cannot be empty"
            },
            "validation.business_license.invalid_length": {
                "zh-CN": "营业执照号长度无效(应为15位或18位)",
                "en-US": "Business license number has invalid length (should be 15 or 18 characters)"
            },
            "validation.business_license.old_format_invalid": {
                "zh-CN": "旧版营业执照号必须为15位数字",
                "en-US": "Old format business license number must be 15 digits"
            },

            # Contract errors
            "validation.contract.missing_fields": {
                "zh-CN": "合同缺少必填字段: {fields}",
                "en-US": "Contract is missing required fields: {fields}"
            },
            "validation.contract.invalid_number_format": {
                "zh-CN": "合同编号格式无效",
                "en-US": "Contract number format is invalid"
            },
            "validation.contract.missing_approval": {
                "zh-CN": "合同未通过审批流程",
                "en-US": "Contract has not been approved"
            },

            # Seal errors
            "validation.seal.unauthorized": {
                "zh-CN": "印章使用未授权",
                "en-US": "Seal usage is not authorized"
            },
            "validation.seal.invalid_type": {
                "zh-CN": "印章类型无效: {seal_type}",
                "en-US": "Seal type is invalid: {seal_type}"
            },
            "validation.seal.missing_record": {
                "zh-CN": "印章使用缺少记录",
                "en-US": "Seal usage record is missing"
            },
        }

    async def create_rule(
        self,
        name: str,
        description: str,
        region: Region,
        industry: Industry,
        validator_type: str,
        validator_config: Dict[str, Any],
        error_message_key: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ) -> ValidationRule:
        """Create a new validation rule.

        Args:
            name: Rule name
            description: Rule description
            region: Geographic region
            industry: Industry sector
            validator_type: Type of validator (regex, function, chinese_business_id, etc.)
            validator_config: Configuration for the validator
            error_message_key: i18n key for error message
            severity: Severity level

        Returns:
            Created validation rule
        """
        async with self._lock:
            rule = ValidationRule(
                name=name,
                description=description,
                region=region,
                industry=industry,
                validator_type=validator_type,
                validator_config=validator_config,
                error_message_key=error_message_key,
                severity=severity
            )

            self._rules[rule.rule_id] = rule
            self._rules_by_region[region].append(rule.rule_id)
            self._rules_by_industry[industry].append(rule.rule_id)

            # Clear cache
            self._rule_cache.clear()

            return rule

    async def get_rules(
        self,
        region: Optional[Region] = None,
        industry: Optional[Industry] = None,
        is_active: bool = True
    ) -> List[ValidationRule]:
        """Get validation rules filtered by region and industry.

        Args:
            region: Filter by region (optional)
            industry: Filter by industry (optional)
            is_active: Filter by active status

        Returns:
            List of validation rules
        """
        async with self._lock:
            # Check cache
            cache_key = f"{region}:{industry}:{is_active}"
            if cache_key in self._rule_cache:
                return self._rule_cache[cache_key]

            rules = list(self._rules.values())

            # Filter by region
            if region is not None:
                rules = [r for r in rules if r.region == region or r.region == Region.INTL]

            # Filter by industry
            if industry is not None:
                rules = [r for r in rules if r.industry == industry or r.industry == Industry.GENERAL]

            # Filter by active status
            if is_active:
                rules = [r for r in rules if r.is_active]

            # Cache results
            self._rule_cache[cache_key] = rules

            return rules

    def get_error_message(self, error_key: str, language: str = "zh-CN", **kwargs) -> str:
        """Get localized error message.

        Args:
            error_key: Error message key
            language: Language code (zh-CN or en-US)
            **kwargs: Parameters for message formatting

        Returns:
            Localized error message
        """
        if error_key not in self._error_messages:
            return error_key  # Fallback to key

        message = self._error_messages[error_key].get(language, self._error_messages[error_key].get("en-US", error_key))

        # Format message with parameters
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message

    async def validate_chinese_business_id(
        self,
        identifier: str,
        identifier_type: str,
        element_id: Optional[UUID] = None
    ) -> ValidationResult:
        """Validate Chinese business identifier.

        Args:
            identifier: Business identifier to validate
            identifier_type: Type of identifier (uscc, org_code, business_license)
            element_id: Optional ontology element ID

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Validate based on type
        if identifier_type == "uscc":
            is_valid, error_key = ChineseBusinessIdentifierValidator.validate_uscc(identifier)
        elif identifier_type == "org_code":
            is_valid, error_key = ChineseBusinessIdentifierValidator.validate_organization_code(identifier)
        elif identifier_type == "business_license":
            is_valid, error_key = ChineseBusinessIdentifierValidator.validate_business_license(identifier)
        else:
            result.is_valid = False
            result.errors.append(ValidationError(
                element_id=element_id,
                element_type="business_identifier",
                field_name="identifier_type",
                error_message=f"Unknown identifier type: {identifier_type}",
                error_message_zh=f"未知的标识符类型: {identifier_type}",
                error_message_en=f"Unknown identifier type: {identifier_type}",
                severity=ValidationSeverity.ERROR
            ))
            return result

        if not is_valid and error_key:
            result.is_valid = False
            result.errors.append(ValidationError(
                element_id=element_id,
                element_type="business_identifier",
                field_name="identifier",
                error_message=self.get_error_message(error_key, "zh-CN"),
                error_message_zh=self.get_error_message(error_key, "zh-CN"),
                error_message_en=self.get_error_message(error_key, "en-US"),
                severity=ValidationSeverity.ERROR,
                suggestions=self._get_identifier_suggestions(identifier_type)
            ))

        return result

    async def validate_contract(
        self,
        contract: ContractEntity,
        element_id: Optional[UUID] = None
    ) -> ValidationResult:
        """Validate contract entity.

        Args:
            contract: Contract entity to validate
            element_id: Optional ontology element ID

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check required fields
        missing_fields = contract.required_fields - {
            k for k, v in contract.__dict__.items() if v
        }

        if missing_fields:
            result.is_valid = False
            fields_str = ", ".join(missing_fields)
            result.errors.append(ValidationError(
                element_id=element_id,
                element_type="contract",
                field_name="required_fields",
                error_message=self.get_error_message("validation.contract.missing_fields", "zh-CN", fields=fields_str),
                error_message_zh=self.get_error_message("validation.contract.missing_fields", "zh-CN", fields=fields_str),
                error_message_en=self.get_error_message("validation.contract.missing_fields", "en-US", fields=fields_str),
                severity=ValidationSeverity.ERROR
            ))

        # Validate contract number format (basic check)
        if contract.contract_number and not re.match(r'^[A-Z0-9\-]+$', contract.contract_number):
            result.warnings.append(ValidationError(
                element_id=element_id,
                element_type="contract",
                field_name="contract_number",
                error_message=self.get_error_message("validation.contract.invalid_number_format", "zh-CN"),
                error_message_zh=self.get_error_message("validation.contract.invalid_number_format", "zh-CN"),
                error_message_en=self.get_error_message("validation.contract.invalid_number_format", "en-US"),
                severity=ValidationSeverity.WARNING
            ))

        # Check approval status
        if contract.approval_status != "approved":
            result.warnings.append(ValidationError(
                element_id=element_id,
                element_type="contract",
                field_name="approval_status",
                error_message=self.get_error_message("validation.contract.missing_approval", "zh-CN"),
                error_message_zh=self.get_error_message("validation.contract.missing_approval", "zh-CN"),
                error_message_en=self.get_error_message("validation.contract.missing_approval", "en-US"),
                severity=ValidationSeverity.WARNING
            ))

        return result

    async def validate_seal_usage(
        self,
        seal_type: SealType,
        authorized: bool,
        has_record: bool,
        element_id: Optional[UUID] = None
    ) -> ValidationResult:
        """Validate seal usage.

        Args:
            seal_type: Type of seal
            authorized: Whether usage is authorized
            has_record: Whether usage is recorded
            element_id: Optional ontology element ID

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check authorization
        if not authorized:
            result.is_valid = False
            result.errors.append(ValidationError(
                element_id=element_id,
                element_type="seal_usage",
                field_name="authorization",
                error_message=self.get_error_message("validation.seal.unauthorized", "zh-CN"),
                error_message_zh=self.get_error_message("validation.seal.unauthorized", "zh-CN"),
                error_message_en=self.get_error_message("validation.seal.unauthorized", "en-US"),
                severity=ValidationSeverity.ERROR
            ))

        # Check usage record
        if not has_record:
            result.is_valid = False
            result.errors.append(ValidationError(
                element_id=element_id,
                element_type="seal_usage",
                field_name="usage_record",
                error_message=self.get_error_message("validation.seal.missing_record", "zh-CN"),
                error_message_zh=self.get_error_message("validation.seal.missing_record", "zh-CN"),
                error_message_en=self.get_error_message("validation.seal.missing_record", "en-US"),
                severity=ValidationSeverity.ERROR
            ))

        return result

    async def validate(
        self,
        element: Dict[str, Any],
        element_type: str,
        region: Optional[Region] = None,
        industry: Optional[Industry] = None
    ) -> ValidationResult:
        """Validate an ontology element against applicable rules.

        Args:
            element: Element data to validate
            element_type: Type of element
            region: Region for rule selection
            industry: Industry for rule selection

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Get applicable rules
        rules = await self.get_rules(region=region, industry=industry)

        # Apply each rule
        for rule in rules:
            rule_result = await self._apply_rule(element, element_type, rule)

            # Merge results
            result.errors.extend(rule_result.errors)
            result.warnings.extend(rule_result.warnings)
            result.info_messages.extend(rule_result.info_messages)

        # Overall validity
        result.is_valid = len(result.errors) == 0

        return result

    async def _apply_rule(
        self,
        element: Dict[str, Any],
        element_type: str,
        rule: ValidationRule
    ) -> ValidationResult:
        """Apply a single validation rule.

        Args:
            element: Element data
            element_type: Type of element
            rule: Validation rule to apply

        Returns:
            Validation result for this rule
        """
        result = ValidationResult()

        if rule.validator_type == "regex":
            # Regex validation
            field_name = rule.validator_config.get("field")
            pattern = rule.validator_config.get("pattern")

            if field_name in element:
                value = str(element[field_name])
                if not re.match(pattern, value):
                    error = ValidationError(
                        element_type=element_type,
                        field_name=field_name,
                        error_message=self.get_error_message(rule.error_message_key, "zh-CN"),
                        error_message_zh=self.get_error_message(rule.error_message_key, "zh-CN"),
                        error_message_en=self.get_error_message(rule.error_message_key, "en-US"),
                        severity=rule.severity
                    )

                    if rule.severity == ValidationSeverity.ERROR:
                        result.errors.append(error)
                    elif rule.severity == ValidationSeverity.WARNING:
                        result.warnings.append(error)
                    else:
                        result.info_messages.append(error)

        return result

    def _get_identifier_suggestions(self, identifier_type: str) -> List[str]:
        """Get suggestions for identifier validation errors.

        Args:
            identifier_type: Type of identifier

        Returns:
            List of suggestions
        """
        if identifier_type == "uscc":
            return [
                "确认统一社会信用代码为18位",
                "检查是否包含非法字符(I、O、S、V、Z)",
                "验证最后一位校验码是否正确"
            ]
        elif identifier_type == "org_code":
            return [
                "确认组织机构代码为9位",
                "检查最后一位校验码是否正确"
            ]
        elif identifier_type == "business_license":
            return [
                "新版营业执照号为18位统一社会信用代码",
                "旧版营业执照号为15位数字"
            ]

        return []
