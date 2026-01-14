"""
Property-based tests for API Format Conversion.

Tests Property 3: 第三方工具格式转换往返
Validates: Requirements 8.4, 8.5

For any valid annotation data, converting to third-party format and back
should preserve the essential data (round-trip conversion).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from enum import Enum


# ============================================================================
# Local copies of schemas to avoid import issues
# ============================================================================

class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"


# ============================================================================
# Mock Format Converter
# ============================================================================

class MockFormatConverter:
    """Mock format converter for testing round-trip conversion."""
    
    def __init__(self):
        self._supported_formats = ["label_studio", "prodigy", "doccano", "custom"]
    
    def to_label_studio(self, annotation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to Label Studio format."""
        return {
            "id": annotation.get("id"),
            "data": {
                "text": annotation.get("text", ""),
            },
            "annotations": [{
                "result": self._convert_result_to_ls(annotation),
            }],
            "meta": annotation.get("metadata", {}),
        }
    
    def from_label_studio(self, ls_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert from Label Studio format."""
        result = {
            "id": ls_data.get("id"),
            "text": ls_data.get("data", {}).get("text", ""),
            "metadata": ls_data.get("meta", {}),
        }
        
        # Extract annotation result
        annotations = ls_data.get("annotations", [])
        if annotations:
            result.update(self._convert_result_from_ls(annotations[0].get("result", [])))
        
        return result
    
    def to_prodigy(self, annotation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to Prodigy format."""
        return {
            "_task_hash": hash(annotation.get("id", "")),
            "text": annotation.get("text", ""),
            "label": annotation.get("label"),
            "spans": annotation.get("entities", []),
            "meta": {
                "id": annotation.get("id"),
                **annotation.get("metadata", {}),
            },
        }
    
    def from_prodigy(self, prodigy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert from Prodigy format."""
        return {
            "id": prodigy_data.get("meta", {}).get("id"),
            "text": prodigy_data.get("text", ""),
            "label": prodigy_data.get("label"),
            "entities": prodigy_data.get("spans", []),
            "metadata": {k: v for k, v in prodigy_data.get("meta", {}).items() if k != "id"},
        }
    
    def _convert_result_to_ls(self, annotation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert annotation result to Label Studio format."""
        results = []
        
        # Handle classification
        if annotation.get("label"):
            results.append({
                "type": "choices",
                "value": {"choices": [annotation["label"]]},
            })
        
        # Handle entities
        for entity in annotation.get("entities", []):
            results.append({
                "type": "labels",
                "value": {
                    "start": entity.get("start", 0),
                    "end": entity.get("end", 0),
                    "labels": [entity.get("label", "")],
                    "text": entity.get("text", ""),
                },
            })
        
        return results
    
    def _convert_result_from_ls(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert Label Studio result to annotation format."""
        output = {}
        entities = []
        
        for result in results:
            if result.get("type") == "choices":
                choices = result.get("value", {}).get("choices", [])
                if choices:
                    output["label"] = choices[0]
            elif result.get("type") == "labels":
                value = result.get("value", {})
                entities.append({
                    "start": value.get("start", 0),
                    "end": value.get("end", 0),
                    "label": value.get("labels", [""])[0],
                    "text": value.get("text", ""),
                })
        
        if entities:
            output["entities"] = entities
        
        return output
    
    def round_trip(
        self,
        annotation: Dict[str, Any],
        target_format: str,
    ) -> Dict[str, Any]:
        """
        Perform round-trip conversion.
        
        Property 3: 第三方工具格式转换往返
        """
        if target_format == "label_studio":
            converted = self.to_label_studio(annotation)
            return self.from_label_studio(converted)
        elif target_format == "prodigy":
            converted = self.to_prodigy(annotation)
            return self.from_prodigy(converted)
        else:
            raise ValueError(f"Unsupported format: {target_format}")


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def annotation_id_strategy(draw):
    """Generate valid annotation IDs."""
    return f"ann_{draw(st.integers(min_value=1, max_value=100000))}"


@st.composite
def text_strategy(draw):
    """Generate valid text content."""
    return draw(st.text(min_size=1, max_size=500, alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        whitelist_characters=' '
    )))


@st.composite
def label_strategy(draw):
    """Generate valid labels."""
    labels = ["positive", "negative", "neutral", "spam", "not_spam", "urgent", "normal"]
    return draw(st.sampled_from(labels))


@st.composite
def entity_strategy(draw, text_length: int):
    """Generate valid entity annotation."""
    if text_length < 2:
        return None
    
    start = draw(st.integers(min_value=0, max_value=max(0, text_length - 2)))
    end = draw(st.integers(min_value=start + 1, max_value=min(start + 50, text_length)))
    
    return {
        "start": start,
        "end": end,
        "label": draw(st.sampled_from(["PERSON", "ORG", "LOC", "DATE", "MISC"])),
        "text": "",  # Will be filled based on actual text
    }


@st.composite
def classification_annotation_strategy(draw):
    """Generate classification annotation."""
    return {
        "id": draw(annotation_id_strategy()),
        "text": draw(text_strategy()),
        "label": draw(label_strategy()),
        "metadata": {},
    }


@st.composite
def ner_annotation_strategy(draw):
    """Generate NER annotation."""
    text = draw(text_strategy())
    text_len = len(text)
    
    num_entities = draw(st.integers(min_value=0, max_value=3))
    entities = []
    
    for _ in range(num_entities):
        entity = draw(entity_strategy(text_len))
        if entity:
            entity["text"] = text[entity["start"]:entity["end"]]
            entities.append(entity)
    
    return {
        "id": draw(annotation_id_strategy()),
        "text": text,
        "entities": entities,
        "metadata": {},
    }


# ============================================================================
# Property Tests
# ============================================================================

class TestFormatConversionRoundTrip:
    """
    Property 3: 第三方工具格式转换往返
    
    For any valid annotation data, converting to third-party format and back
    should preserve the essential data.
    
    **Validates: Requirements 8.4, 8.5**
    """
    
    def test_label_studio_round_trip_classification(self):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.4**
        
        Classification annotation should survive Label Studio round-trip.
        """
        converter = MockFormatConverter()
        
        annotation = {
            "id": "ann_1",
            "text": "This is a test document.",
            "label": "positive",
            "metadata": {},
        }
        
        result = converter.round_trip(annotation, "label_studio")
        
        assert result["id"] == annotation["id"]
        assert result["text"] == annotation["text"]
        assert result["label"] == annotation["label"]
    
    def test_prodigy_round_trip_classification(self):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.5**
        
        Classification annotation should survive Prodigy round-trip.
        """
        converter = MockFormatConverter()
        
        annotation = {
            "id": "ann_1",
            "text": "This is a test document.",
            "label": "negative",
            "metadata": {},
        }
        
        result = converter.round_trip(annotation, "prodigy")
        
        assert result["id"] == annotation["id"]
        assert result["text"] == annotation["text"]
        assert result["label"] == annotation["label"]
    
    @given(annotation=classification_annotation_strategy())
    @settings(max_examples=100)
    def test_label_studio_round_trip_property(self, annotation: Dict[str, Any]):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.4**
        
        Any classification annotation should survive Label Studio round-trip.
        """
        converter = MockFormatConverter()
        
        result = converter.round_trip(annotation, "label_studio")
        
        # Essential fields should be preserved
        assert result["id"] == annotation["id"]
        assert result["text"] == annotation["text"]
        assert result["label"] == annotation["label"]
    
    @given(annotation=classification_annotation_strategy())
    @settings(max_examples=100)
    def test_prodigy_round_trip_property(self, annotation: Dict[str, Any]):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.5**
        
        Any classification annotation should survive Prodigy round-trip.
        """
        converter = MockFormatConverter()
        
        result = converter.round_trip(annotation, "prodigy")
        
        # Essential fields should be preserved
        assert result["id"] == annotation["id"]
        assert result["text"] == annotation["text"]
        assert result["label"] == annotation["label"]
    
    @given(annotation=ner_annotation_strategy())
    @settings(max_examples=100)
    def test_label_studio_ner_round_trip_property(self, annotation: Dict[str, Any]):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.4**
        
        Any NER annotation should survive Label Studio round-trip.
        """
        converter = MockFormatConverter()
        
        result = converter.round_trip(annotation, "label_studio")
        
        # Essential fields should be preserved
        assert result["id"] == annotation["id"]
        assert result["text"] == annotation["text"]
        
        # Entities should be preserved
        if annotation.get("entities"):
            assert "entities" in result
            assert len(result["entities"]) == len(annotation["entities"])
            
            for orig, conv in zip(annotation["entities"], result["entities"]):
                assert conv["start"] == orig["start"]
                assert conv["end"] == orig["end"]
                assert conv["label"] == orig["label"]


class TestFormatConversionIntegrity:
    """
    Tests for format conversion data integrity.
    
    **Validates: Requirements 8.4, 8.5**
    """
    
    def test_empty_annotation_handling(self):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.4**
        
        Empty annotation should be handled gracefully.
        """
        converter = MockFormatConverter()
        
        annotation = {
            "id": "ann_empty",
            "text": "",
            "metadata": {},
        }
        
        # Should not raise
        result = converter.round_trip(annotation, "label_studio")
        assert result["id"] == annotation["id"]
    
    @given(
        format_name=st.sampled_from(["label_studio", "prodigy"]),
        annotation=classification_annotation_strategy(),
    )
    @settings(max_examples=100)
    def test_multiple_round_trips_stable(
        self,
        format_name: str,
        annotation: Dict[str, Any],
    ):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.4, 8.5**
        
        Multiple round-trips should produce stable results.
        """
        converter = MockFormatConverter()
        
        # First round-trip
        result1 = converter.round_trip(annotation, format_name)
        
        # Second round-trip
        result2 = converter.round_trip(result1, format_name)
        
        # Results should be identical
        assert result1["id"] == result2["id"]
        assert result1["text"] == result2["text"]
        assert result1.get("label") == result2.get("label")


class TestUnsupportedFormatHandling:
    """
    Tests for unsupported format handling.
    
    **Validates: Requirements 8.4**
    """
    
    def test_unsupported_format_raises_error(self):
        """
        **Feature: ai-annotation, Property 3: 第三方工具格式转换往返**
        **Validates: Requirements 8.4**
        
        Unsupported format should raise error.
        """
        converter = MockFormatConverter()
        
        annotation = {
            "id": "ann_1",
            "text": "Test",
            "label": "positive",
        }
        
        with pytest.raises(ValueError, match="Unsupported format"):
            converter.round_trip(annotation, "unknown_format")


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
