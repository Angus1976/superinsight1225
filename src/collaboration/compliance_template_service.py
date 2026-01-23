"""Compliance Template Service for Chinese regulatory compliance.

This module provides compliance templates and validation for Chinese regulations:
- Data Security Law (数据安全法, DSL)
- Personal Information Protection Law (个人信息保护法, PIPL)
- Cybersecurity Law (网络安全法, CSL)

Requirements:
- 8.1: Compliance template definition
- 8.2: Automatic entity classification
- 8.3: PIPL requirement enforcement
- 8.4: Cross-border transfer validation
- 8.5: Compliance report generation
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class DataClassification(str, Enum):
    """Data classification levels under Data Security Law."""
    GENERAL = "general"  # 一般数据
    IMPORTANT = "important"  # 重要数据
    CORE = "core"  # 核心数据


class PILType(str, Enum):
    """Personal Information types under PIPL."""
    BASIC = "basic"  # 一般个人信息
    SENSITIVE = "sensitive"  # 敏感个人信息
    NON_PIL = "non_pil"  # 非个人信息


class ConsentType(str, Enum):
    """Consent types under PIPL."""
    IMPLIED = "implied"  # 默示同意
    EXPLICIT = "explicit"  # 明示同意
    SEPARATE = "separate"  # 单独同意
    WRITTEN = "written"  # 书面同意


class ComplianceRegulation(str, Enum):
    """Supported regulations."""
    DSL = "dsl"  # Data Security Law
    PIPL = "pipl"  # Personal Information Protection Law
    CSL = "csl"  # Cybersecurity Law


@dataclass
class ClassificationRule:
    """Rule for classifying data."""
    rule_id: UUID = field(default_factory=uuid4)
    regulation: ComplianceRegulation = ComplianceRegulation.DSL
    classification: DataClassification = DataClassification.GENERAL
    keywords: List[str] = field(default_factory=list)  # Keywords to match
    conditions: List[str] = field(default_factory=list)  # Conditions to evaluate
    description: str = ""
    article_reference: str = ""  # Law article reference


@dataclass
class PILValidationRule:
    """Personal Information validation rule under PIPL."""
    rule_id: UUID = field(default_factory=uuid4)
    pil_type: PILType = PILType.BASIC
    required_consent: ConsentType = ConsentType.IMPLIED
    purpose_limitation: bool = True
    data_minimization: bool = True
    retention_period_days: Optional[int] = None
    cross_border_allowed: bool = False
    description: str = ""
    article_reference: str = ""


@dataclass
class ComplianceTemplate:
    """Compliance template for a regulation."""
    template_id: UUID = field(default_factory=uuid4)
    regulation: ComplianceRegulation = ComplianceRegulation.DSL
    name: str = ""
    description: str = ""
    version: str = "1.0"
    classification_rules: List[ClassificationRule] = field(default_factory=list)
    pil_rules: List[PILValidationRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EntityClassificationResult:
    """Result of entity classification."""
    entity_id: UUID = field(default_factory=uuid4)
    entity_name: str = ""
    classification: DataClassification = DataClassification.GENERAL
    pil_type: PILType = PILType.NON_PIL
    matched_rules: List[UUID] = field(default_factory=list)
    required_consent: Optional[ConsentType] = None
    cross_border_allowed: bool = True
    recommendations: List[str] = field(default_factory=list)
    classified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceViolation:
    """Compliance violation."""
    violation_id: UUID = field(default_factory=uuid4)
    entity_id: UUID = field(default_factory=uuid4)
    regulation: ComplianceRegulation = ComplianceRegulation.PIPL
    violation_type: str = ""
    description: str = ""
    severity: str = ""  # "low", "medium", "high", "critical"
    article_reference: str = ""
    remediation: str = ""


@dataclass
class ComplianceReport:
    """Compliance report for an ontology."""
    report_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)
    regulation: ComplianceRegulation = ComplianceRegulation.DSL
    entity_classifications: List[EntityClassificationResult] = field(default_factory=list)
    violations: List[ComplianceViolation] = field(default_factory=list)
    compliant_count: int = 0
    non_compliant_count: int = 0
    compliance_score: float = 0.0  # 0-100
    generated_at: datetime = field(default_factory=datetime.utcnow)
    recommendations: List[str] = field(default_factory=list)


class ComplianceTemplateService:
    """Service for managing compliance templates and validation."""

    def __init__(self):
        """Initialize compliance template service."""
        self._templates: Dict[UUID, ComplianceTemplate] = {}
        self._entity_classifications: Dict[UUID, EntityClassificationResult] = {}
        self._lock = asyncio.Lock()

        # Initialize built-in templates
        asyncio.create_task(self._initialize_builtin_templates())

    async def _initialize_builtin_templates(self):
        """Initialize built-in compliance templates."""
        # Data Security Law template
        dsl_template = await self.create_template(
            regulation=ComplianceRegulation.DSL,
            name="Data Security Law Compliance",
            description="数据安全法合规模板",
            version="1.0"
        )

        # Classification rules for DSL
        await self._add_dsl_classification_rules(dsl_template.template_id)

        # PIPL template
        pipl_template = await self.create_template(
            regulation=ComplianceRegulation.PIPL,
            name="Personal Information Protection Law Compliance",
            description="个人信息保护法合规模板",
            version="1.0"
        )

        # PIPL validation rules
        await self._add_pipl_validation_rules(pipl_template.template_id)

    async def _add_dsl_classification_rules(self, template_id: UUID):
        """Add Data Security Law classification rules."""
        async with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return

            # Core data (核心数据) - Article 21
            template.classification_rules.append(ClassificationRule(
                regulation=ComplianceRegulation.DSL,
                classification=DataClassification.CORE,
                keywords=["国家安全", "经济命脉", "民生", "公共利益", "关键信息基础设施"],
                description="关系国家安全、国民经济命脉、重要民生、重大公共利益等数据",
                article_reference="数据安全法 第21条"
            ))

            # Important data (重要数据) - Article 21
            template.classification_rules.append(ClassificationRule(
                regulation=ComplianceRegulation.DSL,
                classification=DataClassification.IMPORTANT,
                keywords=["行业数据", "地区数据", "业务数据", "统计数据"],
                description="一旦泄露可能直接影响政治安全、经济安全、社会稳定的数据",
                article_reference="数据安全法 第21条"
            ))

            # General data (一般数据)
            template.classification_rules.append(ClassificationRule(
                regulation=ComplianceRegulation.DSL,
                classification=DataClassification.GENERAL,
                keywords=[],
                description="不属于重要数据和核心数据的其他数据",
                article_reference="数据安全法 第21条"
            ))

    async def _add_pipl_validation_rules(self, template_id: UUID):
        """Add PIPL validation rules."""
        async with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return

            # Sensitive personal information - Article 28
            template.pil_rules.append(PILValidationRule(
                pil_type=PILType.SENSITIVE,
                required_consent=ConsentType.SEPARATE,
                purpose_limitation=True,
                data_minimization=True,
                retention_period_days=None,  # Must be specified
                cross_border_allowed=False,  # Requires separate approval
                description="敏感个人信息包括生物识别、宗教信仰、特定身份、医疗健康、金融账户、行踪轨迹等",
                article_reference="个人信息保护法 第28条"
            ))

            # Basic personal information - Article 13
            template.pil_rules.append(PILValidationRule(
                pil_type=PILType.BASIC,
                required_consent=ConsentType.EXPLICIT,
                purpose_limitation=True,
                data_minimization=True,
                retention_period_days=365,  # Default 1 year
                cross_border_allowed=False,  # Requires assessment
                description="一般个人信息包括姓名、联系方式、地址等",
                article_reference="个人信息保护法 第13条"
            ))

    async def create_template(
        self,
        regulation: ComplianceRegulation,
        name: str,
        description: str,
        version: str = "1.0"
    ) -> ComplianceTemplate:
        """Create a compliance template.

        Args:
            regulation: Regulation type
            name: Template name
            description: Template description
            version: Template version

        Returns:
            Created template
        """
        async with self._lock:
            template = ComplianceTemplate(
                regulation=regulation,
                name=name,
                description=description,
                version=version
            )
            self._templates[template.template_id] = template
            return template

    async def get_template(
        self,
        regulation: ComplianceRegulation
    ) -> Optional[ComplianceTemplate]:
        """Get template for a regulation.

        Args:
            regulation: Regulation type

        Returns:
            Template or None
        """
        async with self._lock:
            for template in self._templates.values():
                if template.regulation == regulation:
                    return template
            return None

    async def classify_entity(
        self,
        entity_id: UUID,
        entity_name: str,
        entity_description: str,
        entity_attributes: List[Dict[str, Any]],
        regulation: ComplianceRegulation = ComplianceRegulation.DSL
    ) -> EntityClassificationResult:
        """Classify an entity according to a regulation.

        Args:
            entity_id: Entity ID
            entity_name: Entity name
            entity_description: Entity description
            entity_attributes: Entity attributes
            regulation: Regulation to apply

        Returns:
            Classification result
        """
        async with self._lock:
            template = await self.get_template(regulation)
            if not template:
                raise ValueError(f"Template for {regulation} not found")

            result = EntityClassificationResult(
                entity_id=entity_id,
                entity_name=entity_name
            )

            # Combine text for keyword matching
            text_to_check = f"{entity_name} {entity_description}".lower()
            for attr in entity_attributes:
                text_to_check += f" {attr.get('name', '')} {attr.get('description', '')}".lower()

            # Apply classification rules
            if regulation == ComplianceRegulation.DSL:
                result.classification = await self._apply_dsl_classification(
                    text_to_check,
                    template.classification_rules,
                    result
                )

            # Apply PIPL rules if entity contains personal information
            if regulation == ComplianceRegulation.PIPL or self._contains_personal_info(text_to_check):
                await self._apply_pipl_rules(
                    text_to_check,
                    template.pil_rules if template else [],
                    result
                )

            # Store classification
            self._entity_classifications[entity_id] = result

            return result

    async def _apply_dsl_classification(
        self,
        text: str,
        rules: List[ClassificationRule],
        result: EntityClassificationResult
    ) -> DataClassification:
        """Apply DSL classification rules.

        Args:
            text: Text to check
            rules: Classification rules
            result: Result to update

        Returns:
            Classification level
        """
        # Check from highest to lowest classification
        for rule in sorted(rules, key=lambda r: ["core", "important", "general"].index(r.classification.value)):
            if rule.classification == DataClassification.GENERAL:
                continue  # Default classification

            # Check if any keywords match
            if any(keyword in text for keyword in rule.keywords):
                result.matched_rules.append(rule.rule_id)
                result.recommendations.append(
                    f"分类为{rule.classification.value}数据: {rule.description}"
                )
                return rule.classification

        # Default to general data
        return DataClassification.GENERAL

    def _contains_personal_info(self, text: str) -> bool:
        """Check if text contains personal information indicators.

        Args:
            text: Text to check

        Returns:
            True if personal information detected
        """
        pil_keywords = [
            "姓名", "name", "身份证", "id card", "手机", "phone", "email", "邮箱",
            "地址", "address", "生物识别", "biometric", "位置", "location",
            "健康", "health", "医疗", "medical", "财务", "financial"
        ]
        return any(keyword in text for keyword in pil_keywords)

    async def _apply_pipl_rules(
        self,
        text: str,
        rules: List[PILValidationRule],
        result: EntityClassificationResult
    ) -> None:
        """Apply PIPL validation rules.

        Args:
            text: Text to check
            rules: PIPL rules
            result: Result to update
        """
        # Sensitive personal information keywords
        sensitive_keywords = [
            "生物识别", "biometric", "指纹", "fingerprint", "人脸", "face",
            "宗教", "religion", "医疗", "medical", "健康", "health",
            "金融账户", "financial account", "位置", "location", "行踪", "trace"
        ]

        # Check if sensitive
        is_sensitive = any(keyword in text for keyword in sensitive_keywords)

        if is_sensitive:
            result.pil_type = PILType.SENSITIVE
            # Find matching rule
            for rule in rules:
                if rule.pil_type == PILType.SENSITIVE:
                    result.required_consent = rule.required_consent
                    result.cross_border_allowed = rule.cross_border_allowed
                    result.matched_rules.append(rule.rule_id)
                    result.recommendations.append(
                        f"敏感个人信息需要{rule.required_consent.value}同意"
                    )
                    result.recommendations.append(
                        f"目的限制: {'是' if rule.purpose_limitation else '否'}"
                    )
                    result.recommendations.append(
                        f"最小化原则: {'是' if rule.data_minimization else '否'}"
                    )
                    break
        elif self._contains_personal_info(text):
            result.pil_type = PILType.BASIC
            # Find matching rule
            for rule in rules:
                if rule.pil_type == PILType.BASIC:
                    result.required_consent = rule.required_consent
                    result.cross_border_allowed = rule.cross_border_allowed
                    result.matched_rules.append(rule.rule_id)
                    result.recommendations.append(
                        f"一般个人信息需要{rule.required_consent.value}同意"
                    )
                    if rule.retention_period_days:
                        result.recommendations.append(
                            f"建议保存期限: {rule.retention_period_days}天"
                        )
                    break

    async def validate_pipl_compliance(
        self,
        entity_id: UUID,
        has_consent: bool,
        consent_type: Optional[ConsentType],
        has_purpose_specification: bool,
        is_data_minimized: bool,
        cross_border_transfer: bool
    ) -> List[ComplianceViolation]:
        """Validate PIPL compliance for an entity.

        Args:
            entity_id: Entity ID
            has_consent: Whether consent was obtained
            consent_type: Type of consent obtained
            has_purpose_specification: Whether purpose is specified
            is_data_minimized: Whether data minimization applied
            cross_border_transfer: Whether cross-border transfer occurs

        Returns:
            List of violations
        """
        async with self._lock:
            violations = []
            classification = self._entity_classifications.get(entity_id)

            if not classification or classification.pil_type == PILType.NON_PIL:
                return violations

            # Check consent requirement - Article 13
            if not has_consent:
                violations.append(ComplianceViolation(
                    entity_id=entity_id,
                    regulation=ComplianceRegulation.PIPL,
                    violation_type="missing_consent",
                    description="未获得个人信息主体同意",
                    severity="high",
                    article_reference="个人信息保护法 第13条",
                    remediation="必须获得个人明确同意后方可处理个人信息"
                ))

            # Check consent type for sensitive information - Article 28
            if classification.pil_type == PILType.SENSITIVE:
                if consent_type != ConsentType.SEPARATE and consent_type != ConsentType.WRITTEN:
                    violations.append(ComplianceViolation(
                        entity_id=entity_id,
                        regulation=ComplianceRegulation.PIPL,
                        violation_type="insufficient_consent",
                        description="敏感个人信息需要单独同意",
                        severity="critical",
                        article_reference="个人信息保护法 第28条",
                        remediation="处理敏感个人信息需要取得个人的单独同意"
                    ))

            # Check purpose limitation - Article 6
            if not has_purpose_specification:
                violations.append(ComplianceViolation(
                    entity_id=entity_id,
                    regulation=ComplianceRegulation.PIPL,
                    violation_type="missing_purpose",
                    description="未明确处理目的",
                    severity="medium",
                    article_reference="个人信息保护法 第6条",
                    remediation="应当具有明确、合理的目的"
                ))

            # Check data minimization - Article 6
            if not is_data_minimized:
                violations.append(ComplianceViolation(
                    entity_id=entity_id,
                    regulation=ComplianceRegulation.PIPL,
                    violation_type="data_not_minimized",
                    description="未遵循最小必要原则",
                    severity="medium",
                    article_reference="个人信息保护法 第6条",
                    remediation="应当限于实现处理目的的最小范围"
                ))

            # Check cross-border transfer - Article 38
            if cross_border_transfer and not classification.cross_border_allowed:
                violations.append(ComplianceViolation(
                    entity_id=entity_id,
                    regulation=ComplianceRegulation.PIPL,
                    violation_type="illegal_cross_border_transfer",
                    description="未经批准的跨境传输",
                    severity="critical",
                    article_reference="个人信息保护法 第38条",
                    remediation="向境外提供个人信息需要通过国家网信部门组织的安全评估"
                ))

            return violations

    async def generate_compliance_report(
        self,
        ontology_id: UUID,
        entity_classifications: List[EntityClassificationResult],
        regulation: ComplianceRegulation = ComplianceRegulation.DSL
    ) -> ComplianceReport:
        """Generate compliance report for an ontology.

        Args:
            ontology_id: Ontology ID
            entity_classifications: Entity classifications
            regulation: Regulation to report on

        Returns:
            Compliance report
        """
        async with self._lock:
            report = ComplianceReport(
                ontology_id=ontology_id,
                regulation=regulation,
                entity_classifications=entity_classifications
            )

            # Count classifications
            for classification in entity_classifications:
                if classification.classification in [DataClassification.CORE, DataClassification.IMPORTANT]:
                    report.recommendations.append(
                        f"实体 '{classification.entity_name}' 分类为 {classification.classification.value}，"
                        f"需要加强保护措施"
                    )

            # Calculate compliance score
            total_entities = len(entity_classifications)
            if total_entities > 0:
                # Simple scoring: entities with recommendations need attention
                entities_needing_attention = sum(
                    1 for c in entity_classifications if c.recommendations
                )
                report.compliant_count = total_entities - entities_needing_attention
                report.non_compliant_count = entities_needing_attention
                report.compliance_score = (report.compliant_count / total_entities) * 100

            # Add general recommendations
            if regulation == ComplianceRegulation.DSL:
                report.recommendations.extend([
                    "建立数据分类分级管理制度 (数据安全法 第21条)",
                    "对重要数据和核心数据实施重点保护 (数据安全法 第21条)",
                    "定期开展数据安全风险评估 (数据安全法 第29条)"
                ])
            elif regulation == ComplianceRegulation.PIPL:
                report.recommendations.extend([
                    "制定个人信息保护合规制度 (个人信息保护法 第51条)",
                    "设立个人信息保护负责人 (个人信息保护法 第52条)",
                    "定期进行个人信息保护影响评估 (个人信息保护法 第55条)"
                ])

            return report

    async def get_entity_classification(
        self,
        entity_id: UUID
    ) -> Optional[EntityClassificationResult]:
        """Get classification result for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Classification result or None
        """
        async with self._lock:
            return self._entity_classifications.get(entity_id)

    async def list_templates(self) -> List[ComplianceTemplate]:
        """List all compliance templates.

        Returns:
            List of templates
        """
        async with self._lock:
            return list(self._templates.values())
