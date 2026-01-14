"""
Ragas Evaluator - Ragas 语义质量评估器
使用 Ragas 框架评估语义质量
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RagasEvaluationResult(BaseModel):
    """Ragas 评估结果"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    answer: str
    contexts: List[str] = Field(default_factory=list)
    ground_truth: Optional[str] = None
    scores: Dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0
    metrics_used: List[str] = Field(default_factory=list)
    evaluation_model: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class BatchRagasResult(BaseModel):
    """批量 Ragas 评估结果"""
    total_evaluated: int
    average_scores: Dict[str, float] = Field(default_factory=dict)
    results: List[RagasEvaluationResult] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class RagasEvaluator:
    """Ragas 语义质量评估器"""
    
    # 支持的评估指标
    SUPPORTED_METRICS = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall"
    ]
    
    def __init__(self, llm_client: Optional[Any] = None, model_name: str = "gpt-3.5-turbo"):
        """
        初始化 Ragas 评估器
        
        Args:
            llm_client: LLM客户端 (可选)
            model_name: 模型名称
        """
        self.llm_client = llm_client
        self.model_name = model_name
        
        # 内存存储
        self._evaluations: Dict[str, RagasEvaluationResult] = {}
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: Optional[List[str]] = None,
        ground_truth: Optional[str] = None,
        metrics: Optional[List[str]] = None
    ) -> RagasEvaluationResult:
        """
        评估单条数据
        
        Args:
            question: 问题
            answer: 答案
            contexts: 上下文列表 (可选)
            ground_truth: 标准答案 (可选)
            metrics: 要评估的指标列表 (可选)
            
        Returns:
            评估结果
        """
        contexts = contexts or []
        metrics = metrics or self.SUPPORTED_METRICS
        
        # 过滤有效指标
        valid_metrics = [m for m in metrics if m in self.SUPPORTED_METRICS]
        
        results: Dict[str, float] = {}
        
        for metric_name in valid_metrics:
            if metric_name == "faithfulness":
                score = await self._evaluate_faithfulness(answer, contexts)
            elif metric_name == "answer_relevancy":
                score = await self._evaluate_answer_relevancy(question, answer)
            elif metric_name == "context_precision":
                score = await self._evaluate_context_precision(question, contexts, ground_truth)
            elif metric_name == "context_recall":
                score = await self._evaluate_context_recall(contexts, ground_truth)
            else:
                continue
            
            results[metric_name] = score
        
        # 计算综合分数
        overall_score = sum(results.values()) / len(results) if results else 0.0
        
        evaluation = RagasEvaluationResult(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth,
            scores=results,
            overall_score=overall_score,
            metrics_used=valid_metrics,
            evaluation_model=self.model_name
        )
        
        # 存储评估结果
        self._evaluations[evaluation.id] = evaluation
        
        return evaluation
    
    async def _evaluate_faithfulness(
        self,
        answer: str,
        contexts: List[str]
    ) -> float:
        """
        评估忠实度 - 答案是否基于上下文
        
        Args:
            answer: 答案
            contexts: 上下文列表
            
        Returns:
            忠实度分数 (0-1)
        """
        if not answer or not contexts:
            return 0.0
        
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self._llm_evaluate_faithfulness(answer, contexts)
        
        # 简化评估：检查答案中的关键词是否出现在上下文中
        answer_words = set(answer.lower().split())
        context_text = " ".join(contexts).lower()
        context_words = set(context_text.split())
        
        if not answer_words:
            return 0.0
        
        # 计算答案词汇在上下文中出现的比例
        overlap = answer_words & context_words
        faithfulness = len(overlap) / len(answer_words)
        
        return min(1.0, max(0.0, faithfulness))
    
    async def _llm_evaluate_faithfulness(
        self,
        answer: str,
        contexts: List[str]
    ) -> float:
        """使用LLM评估忠实度"""
        prompt = f"""
        Given the following contexts and answer, evaluate if the answer is faithful to the contexts.
        Rate from 0 to 1, where 1 means completely faithful (all claims in the answer can be derived from the contexts).
        
        Contexts: {contexts}
        Answer: {answer}
        
        Return only a number between 0 and 1.
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            return self._parse_score(response)
        except Exception:
            return 0.5
    
    async def _evaluate_answer_relevancy(
        self,
        question: str,
        answer: str
    ) -> float:
        """
        评估答案相关性 - 答案是否回答了问题
        
        Args:
            question: 问题
            answer: 答案
            
        Returns:
            相关性分数 (0-1)
        """
        if not question or not answer:
            return 0.0
        
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self._llm_evaluate_relevancy(question, answer)
        
        # 简化评估：检查问题关键词是否在答案中被提及
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        # 移除常见停用词
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        question_words = question_words - stop_words
        
        if not question_words:
            return 1.0
        
        # 计算问题词汇在答案中出现的比例
        overlap = question_words & answer_words
        relevancy = len(overlap) / len(question_words)
        
        # 答案长度因子 (太短的答案可能不够相关)
        length_factor = min(1.0, len(answer) / 50)
        
        return min(1.0, max(0.0, relevancy * 0.7 + length_factor * 0.3))
    
    async def _llm_evaluate_relevancy(
        self,
        question: str,
        answer: str
    ) -> float:
        """使用LLM评估相关性"""
        prompt = f"""
        Given the following question and answer, evaluate if the answer is relevant to the question.
        Rate from 0 to 1, where 1 means the answer directly and completely addresses the question.
        
        Question: {question}
        Answer: {answer}
        
        Return only a number between 0 and 1.
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            return self._parse_score(response)
        except Exception:
            return 0.5
    
    async def _evaluate_context_precision(
        self,
        question: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> float:
        """
        评估上下文精确度 - 检索的上下文是否精确
        
        Args:
            question: 问题
            contexts: 上下文列表
            ground_truth: 标准答案 (可选)
            
        Returns:
            精确度分数 (0-1)
        """
        if not contexts:
            return 0.0
        
        if not question and not ground_truth:
            return 0.5
        
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self._llm_evaluate_context_precision(question, contexts, ground_truth)
        
        # 简化评估：检查上下文与问题/答案的相关性
        reference_text = (question + " " + (ground_truth or "")).lower()
        reference_words = set(reference_text.split())
        
        # 移除停用词
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        reference_words = reference_words - stop_words
        
        if not reference_words:
            return 0.5
        
        # 计算每个上下文的相关性
        relevance_scores = []
        for context in contexts:
            context_words = set(context.lower().split())
            overlap = reference_words & context_words
            score = len(overlap) / len(reference_words) if reference_words else 0
            relevance_scores.append(score)
        
        # 精确度 = 相关上下文的比例
        threshold = 0.1
        relevant_count = sum(1 for s in relevance_scores if s > threshold)
        precision = relevant_count / len(contexts)
        
        return min(1.0, max(0.0, precision))
    
    async def _llm_evaluate_context_precision(
        self,
        question: str,
        contexts: List[str],
        ground_truth: Optional[str]
    ) -> float:
        """使用LLM评估上下文精确度"""
        prompt = f"""
        Given the question and contexts, evaluate the precision of the contexts.
        Precision measures how many of the retrieved contexts are actually relevant to answering the question.
        Rate from 0 to 1, where 1 means all contexts are highly relevant.
        
        Question: {question}
        Contexts: {contexts}
        {"Ground Truth: " + ground_truth if ground_truth else ""}
        
        Return only a number between 0 and 1.
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            return self._parse_score(response)
        except Exception:
            return 0.5
    
    async def _evaluate_context_recall(
        self,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> float:
        """
        评估上下文召回率 - 是否检索到所有相关上下文
        
        Args:
            contexts: 上下文列表
            ground_truth: 标准答案 (可选)
            
        Returns:
            召回率分数 (0-1)
        """
        if not ground_truth:
            return 0.5 if contexts else 0.0
        
        if not contexts:
            return 0.0
        
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self._llm_evaluate_context_recall(contexts, ground_truth)
        
        # 简化评估：检查标准答案中的信息是否被上下文覆盖
        ground_truth_words = set(ground_truth.lower().split())
        
        # 移除停用词
        stop_words = {"the", "a", "an", "is", "are", "was", "were"}
        ground_truth_words = ground_truth_words - stop_words
        
        if not ground_truth_words:
            return 1.0
        
        # 合并所有上下文
        all_context_text = " ".join(contexts).lower()
        context_words = set(all_context_text.split())
        
        # 计算标准答案词汇被上下文覆盖的比例
        overlap = ground_truth_words & context_words
        recall = len(overlap) / len(ground_truth_words)
        
        return min(1.0, max(0.0, recall))
    
    async def _llm_evaluate_context_recall(
        self,
        contexts: List[str],
        ground_truth: str
    ) -> float:
        """使用LLM评估上下文召回率"""
        prompt = f"""
        Given the contexts and ground truth answer, evaluate the recall of the contexts.
        Recall measures whether the contexts contain all the information needed to derive the ground truth answer.
        Rate from 0 to 1, where 1 means the contexts contain all necessary information.
        
        Contexts: {contexts}
        Ground Truth: {ground_truth}
        
        Return only a number between 0 and 1.
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            return self._parse_score(response)
        except Exception:
            return 0.5
    
    def _parse_score(self, response: str) -> float:
        """
        解析LLM返回的分数
        
        Args:
            response: LLM响应
            
        Returns:
            分数 (0-1)
        """
        try:
            # 尝试提取数字
            import re
            numbers = re.findall(r"[\d.]+", response)
            if numbers:
                score = float(numbers[0])
                return min(1.0, max(0.0, score))
        except Exception:
            pass
        
        return 0.5
    
    async def batch_evaluate(
        self,
        dataset: List[Dict[str, Any]],
        metrics: Optional[List[str]] = None
    ) -> BatchRagasResult:
        """
        批量评估
        
        Args:
            dataset: 数据集列表，每项包含 question, answer, contexts, ground_truth
            metrics: 要评估的指标列表 (可选)
            
        Returns:
            批量评估结果
        """
        results: List[RagasEvaluationResult] = []
        
        for item in dataset:
            result = await self.evaluate(
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                contexts=item.get("contexts", []),
                ground_truth=item.get("ground_truth"),
                metrics=metrics
            )
            results.append(result)
        
        # 计算平均分
        avg_scores: Dict[str, float] = {}
        all_metrics = metrics or self.SUPPORTED_METRICS
        
        for metric in all_metrics:
            scores = [r.scores.get(metric, 0) for r in results if metric in r.scores]
            if scores:
                avg_scores[metric] = sum(scores) / len(scores)
        
        return BatchRagasResult(
            total_evaluated=len(results),
            average_scores=avg_scores,
            results=results
        )
    
    async def get_evaluation(self, evaluation_id: str) -> Optional[RagasEvaluationResult]:
        """获取评估结果"""
        return self._evaluations.get(evaluation_id)
    
    async def get_evaluations_by_project(
        self,
        project_id: str
    ) -> List[RagasEvaluationResult]:
        """获取项目的所有评估结果"""
        # 在实际实现中，这里会从数据库查询
        return list(self._evaluations.values())


# 独立函数 (用于属性测试)
def ragas_evaluate(
    question: str,
    answer: str,
    contexts: List[str],
    ground_truth: Optional[str] = None
) -> RagasEvaluationResult:
    """
    Ragas 评估 (同步版本，用于属性测试)
    
    Args:
        question: 问题
        answer: 答案
        contexts: 上下文列表
        ground_truth: 标准答案 (可选)
        
    Returns:
        评估结果
    """
    scores: Dict[str, float] = {}
    
    # 忠实度评估
    if answer and contexts:
        answer_words = set(answer.lower().split())
        context_text = " ".join(contexts).lower()
        context_words = set(context_text.split())
        
        if answer_words:
            overlap = answer_words & context_words
            scores["faithfulness"] = min(1.0, max(0.0, len(overlap) / len(answer_words)))
        else:
            scores["faithfulness"] = 0.0
    else:
        scores["faithfulness"] = 0.0
    
    # 答案相关性评估
    if question and answer:
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        question_words = question_words - stop_words
        
        if question_words:
            overlap = question_words & answer_words
            relevancy = len(overlap) / len(question_words)
            length_factor = min(1.0, len(answer) / 50)
            scores["answer_relevancy"] = min(1.0, max(0.0, relevancy * 0.7 + length_factor * 0.3))
        else:
            scores["answer_relevancy"] = 1.0
    else:
        scores["answer_relevancy"] = 0.0
    
    # 上下文精确度评估
    if contexts and (question or ground_truth):
        reference_text = (question + " " + (ground_truth or "")).lower()
        reference_words = set(reference_text.split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        reference_words = reference_words - stop_words
        
        if reference_words:
            relevance_scores = []
            for context in contexts:
                context_words = set(context.lower().split())
                overlap = reference_words & context_words
                score = len(overlap) / len(reference_words)
                relevance_scores.append(score)
            
            threshold = 0.1
            relevant_count = sum(1 for s in relevance_scores if s > threshold)
            scores["context_precision"] = min(1.0, max(0.0, relevant_count / len(contexts)))
        else:
            scores["context_precision"] = 0.5
    else:
        scores["context_precision"] = 0.0 if not contexts else 0.5
    
    # 上下文召回率评估
    if ground_truth and contexts:
        ground_truth_words = set(ground_truth.lower().split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were"}
        ground_truth_words = ground_truth_words - stop_words
        
        if ground_truth_words:
            all_context_text = " ".join(contexts).lower()
            context_words = set(all_context_text.split())
            overlap = ground_truth_words & context_words
            scores["context_recall"] = min(1.0, max(0.0, len(overlap) / len(ground_truth_words)))
        else:
            scores["context_recall"] = 1.0
    else:
        scores["context_recall"] = 0.5 if contexts else 0.0
    
    # 计算综合分数
    overall_score = sum(scores.values()) / len(scores) if scores else 0.0
    
    return RagasEvaluationResult(
        question=question,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
        scores=scores,
        overall_score=overall_score,
        metrics_used=list(scores.keys())
    )
