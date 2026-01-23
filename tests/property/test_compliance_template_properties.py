"""Property tests for Compliance Template Service.

This module tests universal correctness properties:
- Property 24: Compliance Template Classification (validates 8.2)
- Property 25: PIPL Requirement Enforcement (validates 8.3)
"""

import pytest
import asyncio
from uuid import UUID, uuid4
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any

from src.collaboration.compliance_template_service import (
    ComplianceTemplateService,
    ComplianceRegulation,
    DataClassification,
    PILType,
    ConsentType
)


# Hypothesis strategies
uuid_strategy = st.builds(uuid4)
regulation_strategy = st.sampled_from(list(ComplianceRegulation))
data_classification_strategy = st.sampled_from(list(DataClassification))
pil_type_strategy = st.sampled_from(list(PILType))
consent_type_strategy = st.sampled_from(list(ConsentType))

# Text strategies
short_text_strategy = st.text(min_size=1, max_size=50)
medium_text_strategy = st.text(min_size=1, max_size=200)


class TestComplianceTemplateClassification:
    """Property 24: Compliance Template Classification.

    Validates Requirement 8.2:
    - Entities are automatically classified based on content
    - Classification rules are applied correctly
    - Core data is identified correctly
    - Important data is identified correctly
    - General data is the default classification
    """

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        entity_name=short_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_general_data_default_classification(
        self,
        entity_id: UUID,
        entity_name: str
    ):
        """Entities without specific keywords are classified as general data."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with no special keywords
        result = await service.classify_entity(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_description="Some generic description",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        # Property: Default classification is GENERAL
        assert result.classification == DataClassification.GENERAL
        assert result.entity_id == entity_id

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        core_keyword=st.sampled_from(["国家安全", "经济命脉", "民生", "公共利益", "关键信息基础设施"])
    )
    @settings(max_examples=50, deadline=None)
    async def test_core_data_classification(
        self,
        entity_id: UUID,
        core_keyword: str
    ):
        """Entities with core data keywords are classified as core data."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with core data keyword
        result = await service.classify_entity(
            entity_id=entity_id,
            entity_name=f"Entity related to {core_keyword}",
            entity_description=f"This contains {core_keyword} information",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        # Property: Classified as CORE
        assert result.classification == DataClassification.CORE
        assert len(result.matched_rules) > 0
        assert any("核心数据" in rec or "core" in rec.lower() for rec in result.recommendations)

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        important_keyword=st.sampled_from(["行业数据", "地区数据", "业务数据", "统计数据"])
    )
    @settings(max_examples=50, deadline=None)
    async def test_important_data_classification(
        self,
        entity_id: UUID,
        important_keyword: str
    ):
        """Entities with important data keywords are classified as important data."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with important data keyword
        result = await service.classify_entity(
            entity_id=entity_id,
            entity_name=f"Entity with {important_keyword}",
            entity_description=f"Contains {important_keyword}",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        # Property: Classified as IMPORTANT
        assert result.classification == DataClassification.IMPORTANT
        assert len(result.matched_rules) > 0

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        entity_name=short_text_strategy,
        entity_description=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_classification_is_deterministic(
        self,
        entity_id: UUID,
        entity_name: str,
        entity_description: str
    ):
        """Same entity always gets same classification."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify twice
        result1 = await service.classify_entity(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_description=entity_description,
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        result2 = await service.classify_entity(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_description=entity_description,
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        # Property: Deterministic classification
        assert result1.classification == result2.classification

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_classification_precedence(
        self,
        entity_id: UUID
    ):
        """Core data takes precedence over important data."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Entity with both core and important keywords
        result = await service.classify_entity(
            entity_id=entity_id,
            entity_name="国家安全 and 行业数据",
            entity_description="Contains both core and important keywords",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        # Property: Core takes precedence
        assert result.classification == DataClassification.CORE


class TestPIPLRequirementEnforcement:
    """Property 25: PIPL Requirement Enforcement.

    Validates Requirement 8.3:
    - Consent requirements are enforced
    - Sensitive information requires separate consent
    - Purpose limitation is checked
    - Data minimization is checked
    - Cross-border transfer restrictions are enforced
    """

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        sensitive_keyword=st.sampled_from([
            "生物识别", "指纹", "人脸", "宗教", "医疗", "健康", "金融账户", "位置", "行踪"
        ])
    )
    @settings(max_examples=50, deadline=None)
    async def test_sensitive_pil_detection(
        self,
        entity_id: UUID,
        sensitive_keyword: str
    ):
        """Sensitive personal information is correctly identified."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with sensitive PI
        result = await service.classify_entity(
            entity_id=entity_id,
            entity_name=f"Entity with {sensitive_keyword}",
            entity_description=f"Contains {sensitive_keyword} data",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Property: Identified as sensitive
        assert result.pil_type == PILType.SENSITIVE
        assert result.required_consent in [ConsentType.SEPARATE, ConsentType.WRITTEN]
        assert result.cross_border_allowed is False

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        basic_pil_keyword=st.sampled_from(["姓名", "手机", "email", "地址"])
    )
    @settings(max_examples=50, deadline=None)
    async def test_basic_pil_detection(
        self,
        entity_id: UUID,
        basic_pil_keyword: str
    ):
        """Basic personal information is correctly identified."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with basic PI (avoiding sensitive keywords)
        result = await service.classify_entity(
            entity_id=entity_id,
            entity_name=f"User {basic_pil_keyword}",
            entity_description=f"Stores user {basic_pil_keyword}",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Property: Identified as basic or sensitive (depending on keyword)
        assert result.pil_type in [PILType.BASIC, PILType.SENSITIVE]
        if result.pil_type == PILType.BASIC:
            assert result.required_consent == ConsentType.EXPLICIT

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_missing_consent_violation(
        self,
        entity_id: UUID
    ):
        """Missing consent is detected as violation."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with personal info
        await service.classify_entity(
            entity_id=entity_id,
            entity_name="User phone number",
            entity_description="Stores phone",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Validate without consent
        violations = await service.validate_pipl_compliance(
            entity_id=entity_id,
            has_consent=False,
            consent_type=None,
            has_purpose_specification=True,
            is_data_minimized=True,
            cross_border_transfer=False
        )

        # Property: Violation detected
        assert len(violations) > 0
        assert any(v.violation_type == "missing_consent" for v in violations)
        assert any(v.severity == "high" for v in violations)

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        consent_type=st.sampled_from([ConsentType.IMPLIED, ConsentType.EXPLICIT])
    )
    @settings(max_examples=50, deadline=None)
    async def test_insufficient_consent_for_sensitive(
        self,
        entity_id: UUID,
        consent_type: ConsentType
    ):
        """Insufficient consent for sensitive PI is detected."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify as sensitive PI
        await service.classify_entity(
            entity_id=entity_id,
            entity_name="User biometric fingerprint",
            entity_description="Biometric authentication",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Validate with insufficient consent
        violations = await service.validate_pipl_compliance(
            entity_id=entity_id,
            has_consent=True,
            consent_type=consent_type,  # Not SEPARATE or WRITTEN
            has_purpose_specification=True,
            is_data_minimized=True,
            cross_border_transfer=False
        )

        # Property: Violation detected for sensitive PI
        assert any(v.violation_type == "insufficient_consent" for v in violations)
        assert any(v.severity == "critical" for v in violations)

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_purpose_limitation_enforcement(
        self,
        entity_id: UUID
    ):
        """Missing purpose specification is detected."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with personal info
        await service.classify_entity(
            entity_id=entity_id,
            entity_name="User name",
            entity_description="Stores name",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Validate without purpose
        violations = await service.validate_pipl_compliance(
            entity_id=entity_id,
            has_consent=True,
            consent_type=ConsentType.EXPLICIT,
            has_purpose_specification=False,  # Missing purpose
            is_data_minimized=True,
            cross_border_transfer=False
        )

        # Property: Violation detected
        assert any(v.violation_type == "missing_purpose" for v in violations)

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_data_minimization_enforcement(
        self,
        entity_id: UUID
    ):
        """Data not minimized is detected."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with personal info
        await service.classify_entity(
            entity_id=entity_id,
            entity_name="User address",
            entity_description="Stores address",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Validate without minimization
        violations = await service.validate_pipl_compliance(
            entity_id=entity_id,
            has_consent=True,
            consent_type=ConsentType.EXPLICIT,
            has_purpose_specification=True,
            is_data_minimized=False,  # Not minimized
            cross_border_transfer=False
        )

        # Property: Violation detected
        assert any(v.violation_type == "data_not_minimized" for v in violations)

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_cross_border_transfer_restriction(
        self,
        entity_id: UUID
    ):
        """Illegal cross-border transfer is detected."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with personal info
        await service.classify_entity(
            entity_id=entity_id,
            entity_name="User email",
            entity_description="Stores email",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Validate with cross-border transfer
        violations = await service.validate_pipl_compliance(
            entity_id=entity_id,
            has_consent=True,
            consent_type=ConsentType.EXPLICIT,
            has_purpose_specification=True,
            is_data_minimized=True,
            cross_border_transfer=True  # Cross-border transfer
        )

        # Property: Violation detected
        assert any(v.violation_type == "illegal_cross_border_transfer" for v in violations)
        assert any(v.severity == "critical" for v in violations)

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_compliant_entity_no_violations(
        self,
        entity_id: UUID
    ):
        """Compliant entities have no violations."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify entity with personal info
        await service.classify_entity(
            entity_id=entity_id,
            entity_name="User name",
            entity_description="Stores name",
            entity_attributes=[],
            regulation=ComplianceRegulation.PIPL
        )

        # Validate with all requirements met
        violations = await service.validate_pipl_compliance(
            entity_id=entity_id,
            has_consent=True,
            consent_type=ConsentType.EXPLICIT,
            has_purpose_specification=True,
            is_data_minimized=True,
            cross_border_transfer=False
        )

        # Property: No violations for basic PI with proper consent
        basic_violations = [v for v in violations if v.severity in ["high", "critical"]]
        assert len(basic_violations) == 0


class TestComplianceReportGeneration:
    """Test compliance report generation."""

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        entity_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_compliance_report_structure(
        self,
        ontology_id: UUID,
        entity_count: int
    ):
        """Compliance reports have correct structure."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Classify multiple entities
        classifications = []
        for i in range(entity_count):
            result = await service.classify_entity(
                entity_id=uuid4(),
                entity_name=f"Entity_{i}",
                entity_description=f"Description {i}",
                entity_attributes=[],
                regulation=ComplianceRegulation.DSL
            )
            classifications.append(result)

        # Generate report
        report = await service.generate_compliance_report(
            ontology_id=ontology_id,
            entity_classifications=classifications,
            regulation=ComplianceRegulation.DSL
        )

        # Property: Report has all required fields
        assert report.ontology_id == ontology_id
        assert report.regulation == ComplianceRegulation.DSL
        assert len(report.entity_classifications) == entity_count
        assert report.compliant_count + report.non_compliant_count == entity_count
        assert 0 <= report.compliance_score <= 100
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_compliance_score_calculation(
        self,
        ontology_id: UUID
    ):
        """Compliance score is calculated correctly."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow template initialization

        # Mix of entities: some needing attention, some not
        classifications = []

        # Entity without special keywords (compliant)
        result1 = await service.classify_entity(
            entity_id=uuid4(),
            entity_name="Simple Entity",
            entity_description="Generic",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )
        classifications.append(result1)

        # Entity with core data (needs attention)
        result2 = await service.classify_entity(
            entity_id=uuid4(),
            entity_name="国家安全 Entity",
            entity_description="Contains core data",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )
        classifications.append(result2)

        # Generate report
        report = await service.generate_compliance_report(
            ontology_id=ontology_id,
            entity_classifications=classifications,
            regulation=ComplianceRegulation.DSL
        )

        # Property: Score reflects classification mix
        assert report.compliance_score >= 0
        assert report.compliance_score <= 100
        # At least one entity needs attention
        assert report.non_compliant_count >= 1


class TestTemplateManagement:
    """Test template management functionality."""

    @pytest.mark.asyncio
    async def test_builtin_templates_initialized(self):
        """Built-in templates are initialized on service creation."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow initialization

        # Get templates
        templates = await service.list_templates()

        # Property: DSL and PIPL templates exist
        assert len(templates) >= 2
        regulations = [t.regulation for t in templates]
        assert ComplianceRegulation.DSL in regulations
        assert ComplianceRegulation.PIPL in regulations

    @pytest.mark.asyncio
    @given(
        regulation=regulation_strategy,
        name=short_text_strategy,
        description=medium_text_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_template_creation(
        self,
        regulation: ComplianceRegulation,
        name: str,
        description: str
    ):
        """Templates can be created."""
        service = ComplianceTemplateService()

        # Create template
        template = await service.create_template(
            regulation=regulation,
            name=name,
            description=description,
            version="1.0"
        )

        # Property: Template is created with correct data
        assert template.regulation == regulation
        assert template.name == name
        assert template.description == description
        assert template.version == "1.0"

    @pytest.mark.asyncio
    @given(
        regulation=regulation_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_get_template_by_regulation(
        self,
        regulation: ComplianceRegulation
    ):
        """Templates can be retrieved by regulation."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow initialization

        # Get template
        template = await service.get_template(regulation)

        # Property: Template exists or is None
        if template:
            assert template.regulation == regulation


class TestEntityClassificationRetrieval:
    """Test entity classification retrieval."""

    @pytest.mark.asyncio
    @given(
        entity_id=uuid_strategy,
        entity_name=short_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_classification_retrieval(
        self,
        entity_id: UUID,
        entity_name: str
    ):
        """Classifications can be retrieved after creation."""
        service = ComplianceTemplateService()
        await asyncio.sleep(0.1)  # Allow initialization

        # Classify entity
        await service.classify_entity(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_description="Description",
            entity_attributes=[],
            regulation=ComplianceRegulation.DSL
        )

        # Retrieve classification
        classification = await service.get_entity_classification(entity_id)

        # Property: Classification is retrievable
        assert classification is not None
        assert classification.entity_id == entity_id
        assert classification.entity_name == entity_name
