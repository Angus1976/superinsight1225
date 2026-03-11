"""
Unit tests for toolkit data models and interfaces.

Validates DataProfile, component models, enums, and ABC enforcement.
"""

import inspect
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.toolkit.models import (
    BasicInfo,
    ComputationalCharacteristics,
    CostEstimate,
    DataFingerprint,
    DataProfile,
    QualityMetrics,
    SemanticInfo,
    StructureInfo,
)
from src.toolkit.models.enums import (
    DataStructure,
    Domain,
    Encoding,
    FileType,
    Language,
    SemanticType,
)
from src.toolkit.interfaces import (
    DataProfiler,
    QualityAnalyzer,
    SemanticAnalyzer,
    TypeDetector,
)
from src.toolkit.interfaces.profiler import DataSource, ProfilingOptions


# --- Enum Tests ---

class TestEnums:
    def test_file_type_values(self):
        assert FileType.CSV == "csv"
        assert FileType.EXCEL == "excel"
        assert FileType.UNKNOWN == "unknown"

    def test_language_values(self):
        assert Language.CHINESE == "zh"
        assert Language.ENGLISH == "en"

    def test_semantic_type_values(self):
        assert SemanticType.EMAIL == "email"
        assert SemanticType.PHONE == "phone"


# --- BasicInfo Tests ---

class TestBasicInfo:
    def test_defaults(self):
        info = BasicInfo()
        assert info.file_type == FileType.UNKNOWN
        assert info.file_size == 0
        assert info.encoding == Encoding.UNKNOWN
        assert info.record_count == 0
        assert info.column_count == 0

    def test_custom_values(self):
        info = BasicInfo(
            file_type=FileType.CSV,
            file_size=2048,
            encoding=Encoding.UTF8,
            record_count=500,
            column_count=10,
        )
        assert info.file_type == FileType.CSV
        assert info.file_size == 2048

    def test_negative_file_size_rejected(self):
        with pytest.raises(ValidationError):
            BasicInfo(file_size=-1)

    def test_negative_record_count_rejected(self):
        with pytest.raises(ValidationError):
            BasicInfo(record_count=-1)


# --- QualityMetrics Tests ---

class TestQualityMetrics:
    def test_defaults(self):
        qm = QualityMetrics()
        assert qm.completeness_score == 0.0
        assert qm.anomaly_count == 0

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            QualityMetrics(completeness_score=1.5)
        with pytest.raises(ValidationError):
            QualityMetrics(completeness_score=-0.1)

    def test_valid_scores(self):
        qm = QualityMetrics(
            completeness_score=0.95,
            consistency_score=0.8,
            accuracy_score=1.0,
            anomaly_count=5,
            missing_value_ratio=0.05,
        )
        assert qm.completeness_score == 0.95
        assert qm.anomaly_count == 5


# --- StructureInfo Tests ---

class TestStructureInfo:
    def test_defaults(self):
        si = StructureInfo()
        assert si.column_schema == {}
        assert si.data_types == []
        assert si.hierarchy_depth == 0
        assert si.data_structure == DataStructure.UNSTRUCTURED

    def test_custom_schema(self):
        si = StructureInfo(
            column_schema={"name": "string", "age": "int"},
            data_structure=DataStructure.TABULAR,
        )
        assert si.column_schema["name"] == "string"
        assert si.data_structure == DataStructure.TABULAR


# --- SemanticInfo Tests ---

class TestSemanticInfo:
    def test_defaults(self):
        si = SemanticInfo()
        assert si.language is None
        assert si.domain is None
        assert si.entities == []
        assert si.sensitive_fields == []

    def test_with_values(self):
        si = SemanticInfo(
            language=Language.CHINESE,
            domain=Domain.FINANCE,
            entities=["Company A"],
            sensitive_fields=["email"],
        )
        assert si.language == Language.CHINESE
        assert si.domain == Domain.FINANCE
        assert len(si.entities) == 1


# --- DataProfile Tests ---

class TestDataProfile:
    def test_default_profile(self):
        profile = DataProfile()
        assert isinstance(profile.id, UUID)
        assert profile.fingerprint is None
        assert profile.is_partial is False
        assert profile.basic_info is not None
        assert profile.quality_metrics is not None
        assert profile.structure_info is not None
        assert profile.semantic_info is not None
        assert profile.computational_characteristics is not None

    def test_profile_with_fingerprint(self):
        fp = DataFingerprint(fingerprint_id="sha256:abc123")
        profile = DataProfile(fingerprint=fp)
        assert profile.fingerprint.fingerprint_id == "sha256:abc123"
        assert profile.fingerprint.algorithm == "sha256"

    def test_partial_profile(self):
        profile = DataProfile(is_partial=True)
        assert profile.is_partial is True


# --- CostEstimate Tests ---

class TestCostEstimate:
    def test_defaults(self):
        ce = CostEstimate()
        assert ce.time_seconds == 0.0
        assert ce.memory_bytes == 0
        assert ce.monetary_cost == 0.0

    def test_negative_rejected(self):
        with pytest.raises(ValidationError):
            CostEstimate(time_seconds=-1.0)


# --- ProfilingOptions & DataSource Tests ---

class TestProfilingOptions:
    def test_defaults(self):
        opts = ProfilingOptions()
        assert opts.quick_mode is False
        assert opts.sampling_mode is False
        assert opts.sample_size == 10000
        assert opts.timeout_seconds is None


class TestDataSource:
    def test_minimal(self):
        ds = DataSource()
        assert ds.path is None
        assert ds.content is None
        assert ds.name == "unknown"

    def test_with_content(self):
        ds = DataSource(path="/tmp/test.csv", content=b"a,b\n1,2", name="test")
        assert ds.path == "/tmp/test.csv"
        assert ds.name == "test"


# --- Interface ABC Enforcement ---

class TestInterfacesAreAbstract:
    def test_data_profiler_is_abstract(self):
        assert inspect.isabstract(DataProfiler)

    def test_type_detector_is_abstract(self):
        assert inspect.isabstract(TypeDetector)

    def test_quality_analyzer_is_abstract(self):
        assert inspect.isabstract(QualityAnalyzer)

    def test_semantic_analyzer_is_abstract(self):
        assert inspect.isabstract(SemanticAnalyzer)

    def test_cannot_instantiate_data_profiler(self):
        with pytest.raises(TypeError):
            DataProfiler()

    def test_cannot_instantiate_type_detector(self):
        with pytest.raises(TypeError):
            TypeDetector()

    def test_cannot_instantiate_quality_analyzer(self):
        with pytest.raises(TypeError):
            QualityAnalyzer()

    def test_cannot_instantiate_semantic_analyzer(self):
        with pytest.raises(TypeError):
            SemanticAnalyzer()
