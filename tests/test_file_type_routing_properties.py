"""
Property-based test for file type routing correctness.

Validates that every supported FileType is routed to exactly one correct
extractor: PDF/DOCX/HTML/TXT/Markdown/JSON → FileExtractor (_TEXT_TYPES),
CSV/Excel → TabularParser (_TABULAR_TYPES), PPT → PPTExtractor (_PPT_TYPES),
Video/Audio → MediaTranscriber (_MEDIA_TYPES).

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from src.models.structuring import FileType
from src.services.vectorization_pipeline import (
    _TABULAR_TYPES,
    _TEXT_TYPES,
    _PPT_TYPES,
    _MEDIA_TYPES,
)

# ---------------------------------------------------------------------------
# Expected mappings
# ---------------------------------------------------------------------------

EXPECTED_TEXT = {"pdf", "docx", "html", "txt", "markdown", "json"}
EXPECTED_TABULAR = {"csv", "excel"}
EXPECTED_PPT = {"ppt"}
EXPECTED_MEDIA = {"video", "audio"}

ALL_ROUTING_SETS = [_TEXT_TYPES, _TABULAR_TYPES, _PPT_TYPES, _MEDIA_TYPES]
ALL_ROUTING_LABELS = ["_TEXT_TYPES", "_TABULAR_TYPES", "_PPT_TYPES", "_MEDIA_TYPES"]


# ---------------------------------------------------------------------------
# Property 10: 文件类型路由正确性
# ---------------------------------------------------------------------------


class TestFileTypeRoutingCorrectness:
    """Property 10: 文件类型路由正确性

    For any supported FileType, the Processing_System routes it to exactly
    one extractor via the routing sets defined in vectorization_pipeline.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    """

    # --- Mutual exclusivity ---

    def test_routing_sets_are_mutually_exclusive(self) -> None:
        """No file type value appears in more than one routing set."""
        for i, (set_a, label_a) in enumerate(zip(ALL_ROUTING_SETS, ALL_ROUTING_LABELS)):
            for set_b, label_b in zip(ALL_ROUTING_SETS[i + 1:], ALL_ROUTING_LABELS[i + 1:]):
                overlap = set_a & set_b
                assert not overlap, (
                    f"{label_a} and {label_b} overlap on {overlap}"
                )

    # --- Completeness ---

    def test_routing_sets_cover_all_file_types(self) -> None:
        """The union of all routing sets covers every FileType enum value."""
        all_routed = _TEXT_TYPES | _TABULAR_TYPES | _PPT_TYPES | _MEDIA_TYPES
        all_enum_values = {ft.value for ft in FileType}
        missing = all_enum_values - all_routed
        assert not missing, f"FileType values not routed: {missing}"

    def test_no_extra_values_in_routing_sets(self) -> None:
        """Routing sets contain no values outside the FileType enum."""
        all_routed = _TEXT_TYPES | _TABULAR_TYPES | _PPT_TYPES | _MEDIA_TYPES
        all_enum_values = {ft.value for ft in FileType}
        extra = all_routed - all_enum_values
        assert not extra, f"Routing sets contain unknown values: {extra}"

    # --- Specific mapping correctness ---

    def test_text_types_match_expected(self) -> None:
        """_TEXT_TYPES must be exactly {pdf, docx, html, txt, markdown, json}."""
        assert _TEXT_TYPES == EXPECTED_TEXT, (
            f"_TEXT_TYPES={_TEXT_TYPES}, expected={EXPECTED_TEXT}"
        )

    def test_tabular_types_match_expected(self) -> None:
        """_TABULAR_TYPES must be exactly {csv, excel}."""
        assert _TABULAR_TYPES == EXPECTED_TABULAR, (
            f"_TABULAR_TYPES={_TABULAR_TYPES}, expected={EXPECTED_TABULAR}"
        )

    def test_ppt_types_match_expected(self) -> None:
        """_PPT_TYPES must be exactly {ppt}."""
        assert _PPT_TYPES == EXPECTED_PPT, (
            f"_PPT_TYPES={_PPT_TYPES}, expected={EXPECTED_PPT}"
        )

    def test_media_types_match_expected(self) -> None:
        """_MEDIA_TYPES must be exactly {video, audio}."""
        assert _MEDIA_TYPES == EXPECTED_MEDIA, (
            f"_MEDIA_TYPES={_MEDIA_TYPES}, expected={EXPECTED_MEDIA}"
        )

    # --- Hypothesis: every sampled FileType lands in exactly one set ---

    @given(file_type=st.sampled_from(list(FileType)))
    @settings(max_examples=100)
    def test_every_file_type_routed_to_exactly_one_set(
        self, file_type: FileType
    ) -> None:
        """For any FileType, its value belongs to exactly one routing set."""
        val = file_type.value
        membership = [val in s for s in ALL_ROUTING_SETS]
        count = sum(membership)
        assert count == 1, (
            f"FileType {val!r} found in {count} routing sets "
            f"(expected exactly 1): "
            f"{[l for l, m in zip(ALL_ROUTING_LABELS, membership) if m]}"
        )

    @given(file_type=st.sampled_from(list(FileType)))
    @settings(max_examples=100)
    def test_file_type_maps_to_correct_extractor(
        self, file_type: FileType
    ) -> None:
        """For any FileType, it maps to the correct expected routing set."""
        val = file_type.value

        if val in EXPECTED_TEXT:
            assert val in _TEXT_TYPES, f"{val} should be in _TEXT_TYPES"
        elif val in EXPECTED_TABULAR:
            assert val in _TABULAR_TYPES, f"{val} should be in _TABULAR_TYPES"
        elif val in EXPECTED_PPT:
            assert val in _PPT_TYPES, f"{val} should be in _PPT_TYPES"
        elif val in EXPECTED_MEDIA:
            assert val in _MEDIA_TYPES, f"{val} should be in _MEDIA_TYPES"
        else:
            assert False, f"FileType {val!r} has no expected mapping"
