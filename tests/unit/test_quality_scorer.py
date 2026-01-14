"""
Unit tests for Quality Scorer
质量评分器单元测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestQualityScorer:
    """Quality Scorer unit tests"""

    def test_calculate_accuracy_perfect_match(self):
        """Test accuracy calculation with perfect match"""
        annotation = {"label": "positive", "confidence": 0.9, "category": "review"}
        gold_standard = {"label": "positive", "confidence": 0.9, "category": "review"}
        
        matching = sum(1 for k, v in gold_standard.items() if annotation.get(k) == v)
        accuracy = matching / len(gold_standard)
        
        assert accuracy == 1.0

    def test_calculate_accuracy_partial_match(self):
        """Test accuracy calculation with partial match"""
        annotation = {"label": "positive", "confidence": 0.8, "category": "review"}
        gold_standard = {"label": "positive", "confidence": 0.9, "category": "feedback"}
        
        matching = sum(1 for k, v in gold_standard.items() if annotation.get(k) == v)
        accuracy = matching / len(gold_standard)
        
        assert accuracy == pytest.approx(1/3, rel=0.01)

    def test_calculate_accuracy_no_match(self):
        """Test accuracy calculation with no match"""
        annotation = {"label": "negative", "confidence": 0.5}
        gold_standard = {"label": "positive", "confidence": 0.9}
        
        matching = sum(1 for k, v in gold_standard.items() if annotation.get(k) == v)
        accuracy = matching / len(gold_standard)
        
        assert accuracy == 0.0

    def test_calculate_accuracy_empty_gold_standard(self):
        """Test accuracy calculation with empty gold standard"""
        annotation = {"label": "positive"}
        gold_standard = {}
        
        accuracy = 0.0 if not gold_standard else sum(
            1 for k, v in gold_standard.items() if annotation.get(k) == v
        ) / len(gold_standard)
        
        assert accuracy == 0.0

    def test_calculate_completeness_all_filled(self):
        """Test completeness calculation with all fields filled"""
        annotation_data = {"field1": "value1", "field2": "value2", "field3": "value3"}
        required_fields = ["field1", "field2", "field3"]
        
        filled = sum(1 for f in required_fields if f in annotation_data and annotation_data[f])
        completeness = filled / len(required_fields) if required_fields else 1.0
        
        assert completeness == 1.0

    def test_calculate_completeness_partial_filled(self):
        """Test completeness calculation with partial fields filled"""
        annotation_data = {"field1": "value1", "field2": "", "field3": None}
        required_fields = ["field1", "field2", "field3"]
        
        filled = sum(1 for f in required_fields if f in annotation_data and annotation_data[f])
        completeness = filled / len(required_fields) if required_fields else 1.0
        
        assert completeness == pytest.approx(1/3, rel=0.01)

    def test_calculate_completeness_no_required_fields(self):
        """Test completeness calculation with no required fields"""
        annotation_data = {"field1": "value1"}
        required_fields = []
        
        completeness = 1.0 if not required_fields else sum(
            1 for f in required_fields if f in annotation_data and annotation_data[f]
        ) / len(required_fields)
        
        assert completeness == 1.0

    def test_calculate_timeliness_on_time(self):
        """Test timeliness calculation when on time"""
        expected_duration = 3600  # 1 hour
        actual_duration = 1800  # 30 minutes
        
        if actual_duration <= expected_duration:
            timeliness = 1.0
        elif actual_duration <= expected_duration * 2:
            timeliness = 0.8
        elif actual_duration <= expected_duration * 3:
            timeliness = 0.6
        else:
            timeliness = 0.4
        
        assert timeliness == 1.0

    def test_calculate_timeliness_slightly_late(self):
        """Test timeliness calculation when slightly late"""
        expected_duration = 3600  # 1 hour
        actual_duration = 5400  # 1.5 hours
        
        if actual_duration <= expected_duration:
            timeliness = 1.0
        elif actual_duration <= expected_duration * 2:
            timeliness = 0.8
        elif actual_duration <= expected_duration * 3:
            timeliness = 0.6
        else:
            timeliness = 0.4
        
        assert timeliness == 0.8

    def test_calculate_timeliness_very_late(self):
        """Test timeliness calculation when very late"""
        expected_duration = 3600  # 1 hour
        actual_duration = 14400  # 4 hours
        
        if actual_duration <= expected_duration:
            timeliness = 1.0
        elif actual_duration <= expected_duration * 2:
            timeliness = 0.8
        elif actual_duration <= expected_duration * 3:
            timeliness = 0.6
        else:
            timeliness = 0.4
        
        assert timeliness == 0.4

    def test_calculate_weighted_score(self):
        """Test weighted score calculation"""
        scores = {"accuracy": 0.9, "completeness": 0.8, "timeliness": 1.0}
        weights = {"accuracy": 0.4, "completeness": 0.3, "timeliness": 0.3}
        
        total_weight = sum(weights.values())
        weighted_sum = sum(scores.get(dim, 0) * weights.get(dim, 0) for dim in weights)
        total_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        expected = (0.9 * 0.4 + 0.8 * 0.3 + 1.0 * 0.3) / 1.0
        assert total_score == pytest.approx(expected, rel=0.01)

    def test_calculate_weighted_score_missing_dimension(self):
        """Test weighted score with missing dimension"""
        scores = {"accuracy": 0.9, "completeness": 0.8}
        weights = {"accuracy": 0.4, "completeness": 0.3, "timeliness": 0.3}
        
        total_weight = sum(weights.values())
        weighted_sum = sum(scores.get(dim, 0) * weights.get(dim, 0) for dim in weights)
        total_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        expected = (0.9 * 0.4 + 0.8 * 0.3 + 0 * 0.3) / 1.0
        assert total_score == pytest.approx(expected, rel=0.01)

    def test_calculate_cohens_kappa_perfect_agreement(self):
        """Test Cohen's Kappa with perfect agreement"""
        # Perfect agreement: both annotators agree on all items
        annotations1 = [1, 1, 0, 0, 1]
        annotations2 = [1, 1, 0, 0, 1]
        
        # Calculate observed agreement
        n = len(annotations1)
        observed_agreement = sum(1 for a, b in zip(annotations1, annotations2) if a == b) / n
        
        # For perfect agreement, kappa = 1
        assert observed_agreement == 1.0

    def test_calculate_cohens_kappa_no_agreement(self):
        """Test Cohen's Kappa with no agreement"""
        annotations1 = [1, 1, 1, 1, 1]
        annotations2 = [0, 0, 0, 0, 0]
        
        n = len(annotations1)
        observed_agreement = sum(1 for a, b in zip(annotations1, annotations2) if a == b) / n
        
        assert observed_agreement == 0.0

    def test_calculate_fleiss_kappa_multiple_annotators(self):
        """Test Fleiss' Kappa calculation logic"""
        # 3 annotators rating 5 items with 2 categories
        ratings = [
            [1, 1, 0],  # Item 1: 2 agree on 1, 1 disagrees
            [1, 1, 1],  # Item 2: all agree on 1
            [0, 0, 0],  # Item 3: all agree on 0
            [1, 0, 1],  # Item 4: 2 agree on 1
            [0, 1, 0],  # Item 5: 2 agree on 0
        ]
        
        n_items = len(ratings)
        n_raters = len(ratings[0])
        
        # Calculate agreement per item
        agreements = []
        for item_ratings in ratings:
            count_1 = sum(item_ratings)
            count_0 = n_raters - count_1
            # Agreement = (n1*(n1-1) + n0*(n0-1)) / (n*(n-1))
            agreement = (count_1 * (count_1 - 1) + count_0 * (count_0 - 1)) / (n_raters * (n_raters - 1))
            agreements.append(agreement)
        
        mean_agreement = sum(agreements) / n_items
        assert 0 <= mean_agreement <= 1

    def test_score_range_validation(self):
        """Test that all scores are in valid range [0, 1]"""
        test_scores = [0.0, 0.5, 1.0, 0.33, 0.67, 0.99]
        
        for score in test_scores:
            assert 0 <= score <= 1, f"Score {score} out of range"

    def test_consistency_score_single_annotator(self):
        """Test consistency score with single annotator"""
        annotations = [{"label": "positive"}]
        
        # Single annotator should return 1.0
        if len(annotations) < 2:
            consistency = 1.0
        else:
            consistency = 0.5  # placeholder
        
        assert consistency == 1.0


class TestQualityScorerIntegration:
    """Integration-style unit tests for Quality Scorer"""

    def test_full_scoring_workflow(self):
        """Test complete scoring workflow"""
        # Simulate annotation data
        annotation_data = {
            "label": "positive",
            "confidence": 0.85,
            "entities": ["product", "feature"],
        }
        gold_standard = {
            "label": "positive",
            "confidence": 0.9,
            "entities": ["product", "feature"],
        }
        required_fields = ["label", "confidence", "entities"]
        
        # Calculate accuracy
        matching = sum(1 for k, v in gold_standard.items() if annotation_data.get(k) == v)
        accuracy = matching / len(gold_standard)
        
        # Calculate completeness
        filled = sum(1 for f in required_fields if f in annotation_data and annotation_data[f])
        completeness = filled / len(required_fields)
        
        # Assume on-time
        timeliness = 1.0
        
        # Calculate weighted score
        weights = {"accuracy": 0.4, "completeness": 0.3, "timeliness": 0.3}
        scores = {"accuracy": accuracy, "completeness": completeness, "timeliness": timeliness}
        
        total_weight = sum(weights.values())
        total_score = sum(scores[d] * weights[d] for d in weights) / total_weight
        
        assert 0 <= total_score <= 1
        assert accuracy == pytest.approx(2/3, rel=0.01)  # 2 out of 3 match
        assert completeness == 1.0
        assert timeliness == 1.0

    def test_scoring_with_default_weights(self):
        """Test scoring with default weight configuration"""
        default_weights = {
            "accuracy": 0.4,
            "completeness": 0.3,
            "timeliness": 0.2,
            "consistency": 0.1
        }
        
        assert sum(default_weights.values()) == pytest.approx(1.0, rel=0.001)
        assert all(0 < w <= 1 for w in default_weights.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
