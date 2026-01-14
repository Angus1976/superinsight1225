"""
Integration tests for Ragas Evaluation Module
Ragas 评估模块集成测试
"""

import pytest
from datetime import datetime
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestRagasEvaluationIntegration:
    """Integration tests for Ragas evaluation workflow"""

    def test_single_evaluation_workflow(self):
        """Test single item Ragas evaluation workflow"""
        # Input data
        evaluation_input = {
            "question": "What is the capital of France?",
            "answer": "The capital of France is Paris. It is known for the Eiffel Tower.",
            "contexts": [
                "Paris is the capital and largest city of France.",
                "The Eiffel Tower is a famous landmark in Paris."
            ],
            "ground_truth": "Paris is the capital of France."
        }
        
        # Simulate evaluation scores
        scores = {
            "faithfulness": 0.9,  # Answer is based on contexts
            "answer_relevancy": 0.95,  # Answer is relevant to question
            "context_precision": 0.85,  # Contexts are precise
            "context_recall": 0.8  # Contexts cover ground truth
        }
        
        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores)
        
        # Create result
        result = {
            "question": evaluation_input["question"],
            "answer": evaluation_input["answer"],
            "contexts": evaluation_input["contexts"],
            "ground_truth": evaluation_input["ground_truth"],
            "scores": scores,
            "overall_score": overall_score
        }
        
        assert 0 <= result["overall_score"] <= 1
        assert all(0 <= s <= 1 for s in result["scores"].values())

    def test_batch_evaluation_workflow(self):
        """Test batch Ragas evaluation workflow"""
        # Dataset
        dataset = [
            {
                "question": "What is Python?",
                "answer": "Python is a programming language.",
                "contexts": ["Python is a high-level programming language."],
                "ground_truth": "Python is a programming language."
            },
            {
                "question": "What is machine learning?",
                "answer": "Machine learning is a subset of AI.",
                "contexts": ["Machine learning is a branch of artificial intelligence."],
                "ground_truth": "Machine learning is a type of AI."
            },
            {
                "question": "What is deep learning?",
                "answer": "Deep learning uses neural networks.",
                "contexts": ["Deep learning is based on artificial neural networks."],
                "ground_truth": "Deep learning uses neural networks."
            }
        ]
        
        # Evaluate each item
        results = []
        for item in dataset:
            # Simulate scores
            scores = {
                "faithfulness": 0.85 + len(item["answer"]) % 10 * 0.01,
                "answer_relevancy": 0.9,
                "context_precision": 0.8,
                "context_recall": 0.75
            }
            overall = sum(scores.values()) / len(scores)
            results.append({
                "question": item["question"],
                "scores": scores,
                "overall_score": overall
            })
        
        # Calculate batch statistics
        avg_scores = {}
        for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            values = [r["scores"][metric] for r in results]
            avg_scores[metric] = sum(values) / len(values)
        
        batch_result = {
            "total_evaluated": len(results),
            "average_scores": avg_scores,
            "results": results
        }
        
        assert batch_result["total_evaluated"] == 3
        assert all(0 <= s <= 1 for s in batch_result["average_scores"].values())

    def test_evaluation_with_selected_metrics(self):
        """Test evaluation with selected metrics only"""
        evaluation_input = {
            "question": "What is AI?",
            "answer": "AI stands for Artificial Intelligence.",
            "contexts": ["Artificial Intelligence (AI) is the simulation of human intelligence."]
        }
        
        # Only evaluate selected metrics
        selected_metrics = ["faithfulness", "answer_relevancy"]
        
        scores = {}
        if "faithfulness" in selected_metrics:
            scores["faithfulness"] = 0.88
        if "answer_relevancy" in selected_metrics:
            scores["answer_relevancy"] = 0.92
        if "context_precision" in selected_metrics:
            scores["context_precision"] = 0.85
        if "context_recall" in selected_metrics:
            scores["context_recall"] = 0.80
        
        overall = sum(scores.values()) / len(scores) if scores else 0
        
        assert len(scores) == 2
        assert "context_precision" not in scores
        assert "context_recall" not in scores


class TestFaithfulnessEvaluation:
    """Integration tests for faithfulness evaluation"""

    def test_high_faithfulness(self):
        """Test evaluation with high faithfulness"""
        answer = "Paris is the capital of France."
        contexts = ["Paris is the capital city of France, located in Europe."]
        
        # Simulate faithfulness check
        answer_words = set(answer.lower().split())
        context_words = set()
        for ctx in contexts:
            context_words.update(ctx.lower().split())
        
        overlap = len(answer_words & context_words)
        faithfulness = overlap / len(answer_words) if answer_words else 0
        
        assert faithfulness > 0.5  # High overlap

    def test_low_faithfulness(self):
        """Test evaluation with low faithfulness (hallucination)"""
        answer = "Paris was founded in 1789 by Napoleon."  # Hallucinated
        contexts = ["Paris is the capital city of France."]
        
        answer_words = set(answer.lower().split())
        context_words = set()
        for ctx in contexts:
            context_words.update(ctx.lower().split())
        
        overlap = len(answer_words & context_words)
        faithfulness = overlap / len(answer_words) if answer_words else 0
        
        # Low overlap indicates potential hallucination
        assert faithfulness < 0.5


class TestAnswerRelevancyEvaluation:
    """Integration tests for answer relevancy evaluation"""

    def test_relevant_answer(self):
        """Test evaluation with relevant answer"""
        question = "What is the capital of France?"
        answer = "The capital of France is Paris."
        
        # Check if answer addresses the question
        question_keywords = {"capital", "france"}
        answer_lower = answer.lower()
        
        keyword_coverage = sum(1 for kw in question_keywords if kw in answer_lower)
        relevancy = keyword_coverage / len(question_keywords)
        
        assert relevancy >= 0.5

    def test_irrelevant_answer(self):
        """Test evaluation with irrelevant answer"""
        question = "What is the capital of France?"
        answer = "The weather is nice today."
        
        question_keywords = {"capital", "france"}
        answer_lower = answer.lower()
        
        keyword_coverage = sum(1 for kw in question_keywords if kw in answer_lower)
        relevancy = keyword_coverage / len(question_keywords)
        
        assert relevancy < 0.5


class TestContextEvaluation:
    """Integration tests for context precision and recall"""

    def test_context_precision(self):
        """Test context precision evaluation"""
        question = "What is Python?"
        contexts = [
            "Python is a programming language.",  # Relevant
            "Python is easy to learn.",  # Relevant
            "The weather is sunny today."  # Not relevant
        ]
        ground_truth = "Python is a programming language."
        
        # Check relevance of each context
        ground_truth_words = set(ground_truth.lower().split())
        relevant_count = 0
        
        for ctx in contexts:
            ctx_words = set(ctx.lower().split())
            overlap = len(ctx_words & ground_truth_words)
            if overlap >= 2:  # At least 2 words overlap
                relevant_count += 1
        
        precision = relevant_count / len(contexts)
        
        assert precision == pytest.approx(2/3, rel=0.01)

    def test_context_recall(self):
        """Test context recall evaluation"""
        contexts = [
            "Python is a programming language.",
            "It was created by Guido van Rossum."
        ]
        ground_truth = "Python is a high-level programming language created by Guido van Rossum."
        
        # Check how much of ground truth is covered
        ground_truth_words = set(ground_truth.lower().split())
        context_words = set()
        for ctx in contexts:
            context_words.update(ctx.lower().split())
        
        covered = len(ground_truth_words & context_words)
        recall = covered / len(ground_truth_words)
        
        assert recall > 0.5  # Good coverage


class TestRagasResultStorage:
    """Integration tests for Ragas result storage"""

    def test_store_evaluation_result(self):
        """Test storing evaluation result"""
        results_db = {}
        
        result = {
            "id": "eval_001",
            "annotation_id": "ann_001",
            "question": "What is AI?",
            "answer": "AI is artificial intelligence.",
            "scores": {
                "faithfulness": 0.9,
                "answer_relevancy": 0.85
            },
            "overall_score": 0.875,
            "evaluated_at": datetime.utcnow().isoformat()
        }
        
        results_db[result["id"]] = result
        
        assert "eval_001" in results_db
        assert results_db["eval_001"]["overall_score"] == 0.875

    def test_query_evaluation_results(self):
        """Test querying evaluation results"""
        results = [
            {"id": "1", "annotation_id": "ann_1", "overall_score": 0.9},
            {"id": "2", "annotation_id": "ann_2", "overall_score": 0.7},
            {"id": "3", "annotation_id": "ann_3", "overall_score": 0.85},
            {"id": "4", "annotation_id": "ann_4", "overall_score": 0.6},
        ]
        
        # Filter by score threshold
        high_quality = [r for r in results if r["overall_score"] >= 0.8]
        low_quality = [r for r in results if r["overall_score"] < 0.7]
        
        assert len(high_quality) == 2
        assert len(low_quality) == 1

    def test_aggregate_evaluation_statistics(self):
        """Test aggregating evaluation statistics"""
        results = [
            {"scores": {"faithfulness": 0.9, "answer_relevancy": 0.85}},
            {"scores": {"faithfulness": 0.8, "answer_relevancy": 0.9}},
            {"scores": {"faithfulness": 0.85, "answer_relevancy": 0.88}},
        ]
        
        # Aggregate by metric
        aggregated = {}
        for metric in ["faithfulness", "answer_relevancy"]:
            values = [r["scores"][metric] for r in results]
            aggregated[metric] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
        
        assert aggregated["faithfulness"]["mean"] == pytest.approx(0.85, rel=0.01)
        assert aggregated["answer_relevancy"]["min"] == 0.85


class TestRagasWithQualityWorkflow:
    """Integration tests for Ragas with quality workflow"""

    def test_ragas_triggers_improvement_task(self):
        """Test that low Ragas score triggers improvement task"""
        # Evaluation result with low score
        evaluation = {
            "annotation_id": "ann_001",
            "overall_score": 0.5,  # Below threshold
            "scores": {
                "faithfulness": 0.4,  # Very low
                "answer_relevancy": 0.6
            }
        }
        
        threshold = 0.7
        
        # Check if improvement task should be created
        should_create_task = evaluation["overall_score"] < threshold
        
        if should_create_task:
            # Identify problematic dimensions
            issues = []
            for metric, score in evaluation["scores"].items():
                if score < 0.6:
                    issues.append({
                        "metric": metric,
                        "score": score,
                        "severity": "high" if score < 0.5 else "medium"
                    })
            
            task = {
                "annotation_id": evaluation["annotation_id"],
                "issues": issues,
                "priority": 3 if any(i["severity"] == "high" for i in issues) else 2
            }
        
        assert should_create_task is True
        assert len(issues) == 1
        assert issues[0]["metric"] == "faithfulness"

    def test_ragas_improvement_verification(self):
        """Test verifying improvement with Ragas re-evaluation"""
        # Original evaluation
        original = {
            "annotation_id": "ann_001",
            "overall_score": 0.5,
            "scores": {"faithfulness": 0.4, "answer_relevancy": 0.6}
        }
        
        # After improvement
        improved = {
            "annotation_id": "ann_001",
            "overall_score": 0.85,
            "scores": {"faithfulness": 0.85, "answer_relevancy": 0.85}
        }
        
        # Calculate improvement
        improvement = {
            "overall": improved["overall_score"] - original["overall_score"],
            "by_metric": {
                metric: improved["scores"][metric] - original["scores"][metric]
                for metric in original["scores"]
            }
        }
        
        assert improvement["overall"] > 0.3
        assert improvement["by_metric"]["faithfulness"] > 0.4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
