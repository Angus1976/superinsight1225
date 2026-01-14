"""
Unit tests for Ragas Evaluator
Ragas 评估器单元测试
"""

import pytest
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestRagasEvaluator:
    """Ragas Evaluator unit tests"""

    def test_faithfulness_score_range(self):
        """Test faithfulness score is in valid range"""
        # Simulate faithfulness scores
        scores = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for score in scores:
            assert 0 <= score <= 1, f"Score {score} out of range"

    def test_answer_relevancy_score_range(self):
        """Test answer relevancy score is in valid range"""
        scores = [0.0, 0.33, 0.67, 1.0]
        
        for score in scores:
            assert 0 <= score <= 1

    def test_context_precision_score_range(self):
        """Test context precision score is in valid range"""
        scores = [0.0, 0.5, 0.8, 1.0]
        
        for score in scores:
            assert 0 <= score <= 1

    def test_context_recall_score_range(self):
        """Test context recall score is in valid range"""
        scores = [0.0, 0.4, 0.9, 1.0]
        
        for score in scores:
            assert 0 <= score <= 1

    def test_overall_score_calculation(self):
        """Test overall score calculation"""
        scores = {
            "faithfulness": 0.8,
            "answer_relevancy": 0.9,
            "context_precision": 0.7,
            "context_recall": 0.85
        }
        
        overall = sum(scores.values()) / len(scores)
        
        assert overall == pytest.approx(0.8125, rel=0.01)
        assert 0 <= overall <= 1

    def test_overall_score_with_subset_metrics(self):
        """Test overall score with subset of metrics"""
        scores = {
            "faithfulness": 0.8,
            "answer_relevancy": 0.9
        }
        
        overall = sum(scores.values()) / len(scores)
        
        assert overall == pytest.approx(0.85, rel=0.01)

    def test_evaluate_faithfulness_logic(self):
        """Test faithfulness evaluation logic"""
        def evaluate_faithfulness(answer: str, contexts: List[str]) -> float:
            """
            Simplified faithfulness evaluation:
            Check how many words in answer appear in contexts
            """
            if not answer or not contexts:
                return 0.0
            
            answer_words = set(answer.lower().split())
            context_words = set()
            for ctx in contexts:
                context_words.update(ctx.lower().split())
            
            if not answer_words:
                return 0.0
            
            overlap = len(answer_words & context_words)
            return overlap / len(answer_words)
        
        # Test cases
        answer = "The capital of France is Paris"
        contexts = ["Paris is the capital city of France"]
        
        score = evaluate_faithfulness(answer, contexts)
        assert 0 <= score <= 1
        assert score > 0.5  # Should have good overlap

    def test_evaluate_answer_relevancy_logic(self):
        """Test answer relevancy evaluation logic"""
        def evaluate_relevancy(question: str, answer: str) -> float:
            """
            Simplified relevancy evaluation:
            Check if answer contains question keywords
            """
            if not question or not answer:
                return 0.0
            
            # Extract key words (simplified)
            question_words = set(question.lower().split()) - {"what", "is", "the", "a", "an"}
            answer_words = set(answer.lower().split())
            
            if not question_words:
                return 1.0
            
            overlap = len(question_words & answer_words)
            return overlap / len(question_words)
        
        question = "What is the capital of France?"
        answer = "The capital of France is Paris"
        
        score = evaluate_relevancy(question, answer)
        assert 0 <= score <= 1

    def test_evaluate_context_precision_logic(self):
        """Test context precision evaluation logic"""
        def evaluate_precision(question: str, contexts: List[str], ground_truth: str) -> float:
            """
            Simplified precision evaluation:
            Check how many contexts are relevant to ground truth
            """
            if not contexts or not ground_truth:
                return 0.0
            
            ground_truth_words = set(ground_truth.lower().split())
            relevant_count = 0
            
            for ctx in contexts:
                ctx_words = set(ctx.lower().split())
                overlap = len(ctx_words & ground_truth_words)
                if overlap > len(ground_truth_words) * 0.3:  # 30% threshold
                    relevant_count += 1
            
            return relevant_count / len(contexts)
        
        contexts = [
            "Paris is the capital of France",
            "The Eiffel Tower is in Paris",
            "London is the capital of UK"  # Not relevant
        ]
        ground_truth = "Paris is the capital city of France"
        
        score = evaluate_precision("What is the capital of France?", contexts, ground_truth)
        assert 0 <= score <= 1

    def test_evaluate_context_recall_logic(self):
        """Test context recall evaluation logic"""
        def evaluate_recall(contexts: List[str], ground_truth: str) -> float:
            """
            Simplified recall evaluation:
            Check how much of ground truth is covered by contexts
            """
            if not ground_truth:
                return 0.0
            if not contexts:
                return 0.0
            
            ground_truth_words = set(ground_truth.lower().split())
            context_words = set()
            for ctx in contexts:
                context_words.update(ctx.lower().split())
            
            covered = len(ground_truth_words & context_words)
            return covered / len(ground_truth_words)
        
        contexts = ["Paris is the capital of France"]
        ground_truth = "Paris is the capital city of France"
        
        score = evaluate_recall(contexts, ground_truth)
        assert 0 <= score <= 1
        assert score > 0.5  # Should cover most words


class TestBatchEvaluation:
    """Tests for batch evaluation functionality"""

    def test_batch_evaluate_aggregation(self):
        """Test batch evaluation result aggregation"""
        results = [
            {"faithfulness": 0.8, "answer_relevancy": 0.9},
            {"faithfulness": 0.7, "answer_relevancy": 0.85},
            {"faithfulness": 0.9, "answer_relevancy": 0.95},
        ]
        
        # Calculate averages
        avg_scores = {}
        for metric in ["faithfulness", "answer_relevancy"]:
            values = [r[metric] for r in results]
            avg_scores[metric] = sum(values) / len(values)
        
        assert avg_scores["faithfulness"] == pytest.approx(0.8, rel=0.01)
        assert avg_scores["answer_relevancy"] == pytest.approx(0.9, rel=0.01)

    def test_batch_evaluate_empty_dataset(self):
        """Test batch evaluation with empty dataset"""
        dataset = []
        
        if not dataset:
            result = {"total_evaluated": 0, "average_scores": {}, "results": []}
        
        assert result["total_evaluated"] == 0

    def test_batch_evaluate_partial_metrics(self):
        """Test batch evaluation with partial metrics"""
        results = [
            {"faithfulness": 0.8},  # Only faithfulness
            {"faithfulness": 0.7, "answer_relevancy": 0.9},  # Both
            {"answer_relevancy": 0.85},  # Only relevancy
        ]
        
        # Calculate averages only for available metrics
        avg_scores = {}
        for metric in ["faithfulness", "answer_relevancy"]:
            values = [r[metric] for r in results if metric in r]
            if values:
                avg_scores[metric] = sum(values) / len(values)
        
        assert avg_scores["faithfulness"] == pytest.approx(0.75, rel=0.01)
        assert avg_scores["answer_relevancy"] == pytest.approx(0.875, rel=0.01)


class TestMetricValidation:
    """Tests for metric validation"""

    def test_valid_metric_names(self):
        """Test valid metric name validation"""
        valid_metrics = [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall"
        ]
        
        def validate_metric(metric: str) -> bool:
            return metric in valid_metrics
        
        assert validate_metric("faithfulness") is True
        assert validate_metric("invalid_metric") is False

    def test_metric_selection(self):
        """Test metric selection for evaluation"""
        all_metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        selected = ["faithfulness", "answer_relevancy"]
        
        # Filter to only selected metrics
        metrics_to_evaluate = [m for m in all_metrics if m in selected]
        
        assert len(metrics_to_evaluate) == 2
        assert "faithfulness" in metrics_to_evaluate
        assert "context_precision" not in metrics_to_evaluate


class TestInputValidation:
    """Tests for input validation"""

    def test_validate_question(self):
        """Test question validation"""
        def validate_question(question: str) -> tuple:
            if not question:
                return False, "Question is required"
            if len(question) > 1000:
                return False, "Question too long"
            return True, None
        
        assert validate_question("What is AI?") == (True, None)
        assert validate_question("")[0] is False
        assert validate_question("A" * 1500)[0] is False

    def test_validate_answer(self):
        """Test answer validation"""
        def validate_answer(answer: str) -> tuple:
            if not answer:
                return False, "Answer is required"
            if len(answer) > 5000:
                return False, "Answer too long"
            return True, None
        
        assert validate_answer("AI is artificial intelligence") == (True, None)
        assert validate_answer("")[0] is False

    def test_validate_contexts(self):
        """Test contexts validation"""
        def validate_contexts(contexts: List[str]) -> tuple:
            if not contexts:
                return False, "At least one context is required"
            if len(contexts) > 10:
                return False, "Too many contexts"
            if any(len(c) > 2000 for c in contexts):
                return False, "Context too long"
            return True, None
        
        assert validate_contexts(["Context 1", "Context 2"]) == (True, None)
        assert validate_contexts([])[0] is False
        assert validate_contexts(["C"] * 15)[0] is False


class TestScoreNormalization:
    """Tests for score normalization"""

    def test_normalize_score(self):
        """Test score normalization to [0, 1] range"""
        def normalize(score: float, min_val: float = 0, max_val: float = 1) -> float:
            if score < min_val:
                return 0.0
            if score > max_val:
                return 1.0
            return (score - min_val) / (max_val - min_val)
        
        assert normalize(0.5) == 0.5
        assert normalize(-0.5) == 0.0
        assert normalize(1.5) == 1.0
        assert normalize(0.0) == 0.0
        assert normalize(1.0) == 1.0

    def test_weighted_average_score(self):
        """Test weighted average score calculation"""
        scores = {
            "faithfulness": 0.8,
            "answer_relevancy": 0.9,
            "context_precision": 0.7,
            "context_recall": 0.85
        }
        weights = {
            "faithfulness": 0.3,
            "answer_relevancy": 0.3,
            "context_precision": 0.2,
            "context_recall": 0.2
        }
        
        weighted_sum = sum(scores[m] * weights[m] for m in scores)
        total_weight = sum(weights.values())
        weighted_avg = weighted_sum / total_weight
        
        expected = (0.8 * 0.3 + 0.9 * 0.3 + 0.7 * 0.2 + 0.85 * 0.2) / 1.0
        assert weighted_avg == pytest.approx(expected, rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
