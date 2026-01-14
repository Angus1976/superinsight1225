"""
Hybrid SQL Generation for Text-to-SQL Methods.

Combines template-based and LLM-based generation with
template-first priority and intelligent fallback.
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from .schemas import (
    SQLGenerationResult,
    MethodType,
)
from .schema_analyzer import DatabaseSchema
from .basic import TemplateFiller, get_template_filler
from .llm_based import LLMSQLGenerator, LLMFramework, get_llm_sql_generator

logger = logging.getLogger(__name__)


@dataclass
class SQLOptimizationRule:
    """SQL optimization rule."""
    name: str
    pattern: str
    replacement: str
    description: str
    enabled: bool = True


class SQLOptimizationRules:
    """
    SQL optimization rules for post-processing.
    
    Applies common optimizations to generated SQL.
    """
    
    def __init__(self):
        """Initialize optimization rules."""
        self.rules: List[SQLOptimizationRule] = self._load_default_rules()
    
    def _load_default_rules(self) -> List[SQLOptimizationRule]:
        """Load default optimization rules."""
        return [
            SQLOptimizationRule(
                name="remove_redundant_distinct",
                pattern=r"SELECT\s+DISTINCT\s+\*",
                replacement="SELECT *",
                description="Remove DISTINCT when selecting all columns",
            ),
            SQLOptimizationRule(
                name="optimize_count_star",
                pattern=r"COUNT\(1\)",
                replacement="COUNT(*)",
                description="Use COUNT(*) instead of COUNT(1)",
            ),
            SQLOptimizationRule(
                name="remove_order_in_subquery",
                pattern=r"\(\s*SELECT[^)]+ORDER\s+BY[^)]+\)",
                replacement="",  # Complex - skip for now
                description="Remove ORDER BY in subqueries",
                enabled=False,
            ),
        ]
    
    def optimize(self, sql: str) -> str:
        """
        Apply optimization rules to SQL.
        
        Args:
            sql: SQL query to optimize
            
        Returns:
            Optimized SQL query
        """
        import re
        
        optimized = sql
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.replacement:
                    optimized = re.sub(
                        rule.pattern,
                        rule.replacement,
                        optimized,
                        flags=re.IGNORECASE
                    )
            except Exception as e:
                logger.warning(f"Optimization rule {rule.name} failed: {e}")
        
        return optimized
    
    def add_rule(self, rule: SQLOptimizationRule) -> None:
        """Add an optimization rule."""
        self.rules.append(rule)
    
    def remove_rule(self, name: str) -> bool:
        """Remove an optimization rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                del self.rules[i]
                return True
        return False


@dataclass
class MethodUsageLog:
    """Log entry for method usage."""
    query: str
    method_used: str
    success: bool
    confidence: float
    execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    template_id: Optional[str] = None
    error: Optional[str] = None


class HybridGenerator:
    """
    Hybrid SQL Generator combining template and LLM methods.
    
    Features:
    - Template-first approach for high confidence
    - LLM fallback for complex queries
    - Rule-based post-processing optimization
    - Method usage logging and analytics
    """
    
    def __init__(
        self,
        template_filler: Optional[TemplateFiller] = None,
        llm_generator: Optional[LLMSQLGenerator] = None,
        template_confidence_threshold: float = 0.7
    ):
        """
        Initialize Hybrid Generator.
        
        Args:
            template_filler: Template filler instance
            llm_generator: LLM generator instance
            template_confidence_threshold: Minimum confidence for template match
        """
        self._template_filler = template_filler
        self._llm_generator = llm_generator
        self.template_confidence_threshold = template_confidence_threshold
        self.rules = SQLOptimizationRules()
        
        # Usage logging
        self._usage_logs: List[MethodUsageLog] = []
        self._max_logs = 1000
        
        # Statistics
        self._total_calls = 0
        self._template_calls = 0
        self._llm_calls = 0
        self._hybrid_calls = 0
    
    @property
    def template_filler(self) -> TemplateFiller:
        """Get template filler, initializing if needed."""
        if self._template_filler is None:
            self._template_filler = get_template_filler()
        return self._template_filler
    
    @property
    def llm_generator(self) -> LLMSQLGenerator:
        """Get LLM generator, initializing if needed."""
        if self._llm_generator is None:
            self._llm_generator = get_llm_sql_generator()
        return self._llm_generator
    
    async def generate(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None,
        db_type: str = "postgresql"
    ) -> SQLGenerationResult:
        """
        Generate SQL using hybrid approach.
        
        Strategy:
        1. Try template matching first
        2. If template confidence is high enough, use template result
        3. Otherwise, fall back to LLM generation
        4. Apply rule-based post-processing
        
        Args:
            query: Natural language query
            schema: Database schema for context
            db_type: Target database type
            
        Returns:
            SQLGenerationResult with generated SQL
        """
        start_time = time.time()
        self._total_calls += 1
        
        try:
            # Step 1: Try template matching
            template_result = self.template_filler.generate(query, schema)
            
            # Step 2: Check if template result is good enough
            if (template_result.sql and 
                template_result.confidence >= self.template_confidence_threshold):
                
                self._template_calls += 1
                
                # Apply optimization rules
                optimized_sql = self.rules.optimize(template_result.sql)
                
                execution_time = (time.time() - start_time) * 1000
                
                result = SQLGenerationResult(
                    sql=optimized_sql,
                    method_used="template",
                    confidence=template_result.confidence,
                    execution_time_ms=execution_time,
                    formatted_sql=template_result.formatted_sql,
                    template_id=template_result.template_id,
                    metadata={
                        **template_result.metadata,
                        "hybrid_strategy": "template_match",
                        "optimizations_applied": True,
                    },
                )
                
                self._log_usage(query, result)
                return result
            
            # Step 3: Fall back to LLM
            self._llm_calls += 1
            llm_result = await self.llm_generator.generate(query, schema, db_type=db_type)
            
            if llm_result.sql:
                # Apply optimization rules
                optimized_sql = self.rules.optimize(llm_result.sql)
                
                execution_time = (time.time() - start_time) * 1000
                
                # Determine method used
                method_used = "hybrid"
                if template_result.sql:
                    # Both methods produced results
                    self._hybrid_calls += 1
                    method_used = "hybrid"
                else:
                    method_used = "llm"
                
                result = SQLGenerationResult(
                    sql=optimized_sql,
                    method_used=method_used,
                    confidence=llm_result.confidence,
                    execution_time_ms=execution_time,
                    formatted_sql=llm_result.formatted_sql,
                    explanation=llm_result.explanation,
                    metadata={
                        **llm_result.metadata,
                        "hybrid_strategy": "llm_fallback",
                        "template_attempted": bool(template_result.sql),
                        "template_confidence": template_result.confidence,
                        "optimizations_applied": True,
                    },
                )
                
                self._log_usage(query, result)
                return result
            
            # Step 4: Both methods failed
            execution_time = (time.time() - start_time) * 1000
            
            result = SQLGenerationResult(
                sql="",
                method_used="hybrid",
                confidence=0.0,
                execution_time_ms=execution_time,
                metadata={
                    "error": "Both template and LLM methods failed",
                    "template_error": template_result.metadata.get("error"),
                    "llm_error": llm_result.metadata.get("error"),
                },
            )
            
            self._log_usage(query, result, error="Both methods failed")
            return result
            
        except Exception as e:
            logger.error(f"Hybrid generation failed: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            result = SQLGenerationResult(
                sql="",
                method_used="hybrid",
                confidence=0.0,
                execution_time_ms=execution_time,
                metadata={"error": str(e)},
            )
            
            self._log_usage(query, result, error=str(e))
            return result
    
    def _log_usage(
        self,
        query: str,
        result: SQLGenerationResult,
        error: Optional[str] = None
    ) -> None:
        """Log method usage for analytics."""
        log_entry = MethodUsageLog(
            query=query,
            method_used=result.method_used,
            success=bool(result.sql),
            confidence=result.confidence,
            execution_time_ms=result.execution_time_ms,
            template_id=result.template_id,
            error=error,
        )
        
        self._usage_logs.append(log_entry)
        
        # Trim logs if too many
        if len(self._usage_logs) > self._max_logs:
            self._usage_logs = self._usage_logs[-self._max_logs:]
    
    def log_method_usage(self, query: str, method: str) -> None:
        """
        Manually log method usage.
        
        Args:
            query: The query that was processed
            method: The method that was used
        """
        log_entry = MethodUsageLog(
            query=query,
            method_used=method,
            success=True,
            confidence=1.0,
            execution_time_ms=0.0,
        )
        self._usage_logs.append(log_entry)
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get method usage statistics."""
        if not self._usage_logs:
            return {
                "total_queries": 0,
                "method_distribution": {},
                "average_confidence": 0.0,
                "success_rate": 0.0,
            }
        
        total = len(self._usage_logs)
        successful = sum(1 for log in self._usage_logs if log.success)
        
        method_counts: Dict[str, int] = {}
        total_confidence = 0.0
        
        for log in self._usage_logs:
            method_counts[log.method_used] = method_counts.get(log.method_used, 0) + 1
            total_confidence += log.confidence
        
        return {
            "total_queries": total,
            "successful_queries": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "method_distribution": {
                method: count / total for method, count in method_counts.items()
            },
            "method_counts": method_counts,
            "average_confidence": total_confidence / total if total > 0 else 0.0,
            "average_execution_time_ms": sum(
                log.execution_time_ms for log in self._usage_logs
            ) / total if total > 0 else 0.0,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            "total_calls": self._total_calls,
            "template_calls": self._template_calls,
            "llm_calls": self._llm_calls,
            "hybrid_calls": self._hybrid_calls,
            "template_rate": self._template_calls / max(1, self._total_calls),
            "llm_rate": self._llm_calls / max(1, self._total_calls),
            "usage_statistics": self.get_usage_statistics(),
        }
    
    def calculate_confidence(self, result: SQLGenerationResult) -> float:
        """
        Calculate overall confidence for a result.
        
        Args:
            result: SQL generation result
            
        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = result.confidence
        
        # Adjust based on method
        if result.method_used == "template":
            # Template results are generally more reliable
            return min(1.0, base_confidence * 1.1)
        elif result.method_used == "llm":
            # LLM results may need slight reduction
            return base_confidence * 0.95
        else:
            # Hybrid - use as-is
            return base_confidence
    
    def clear_logs(self) -> None:
        """Clear usage logs."""
        self._usage_logs.clear()
    
    def set_template_threshold(self, threshold: float) -> None:
        """Set template confidence threshold."""
        self.template_confidence_threshold = max(0.0, min(1.0, threshold))


# Global instance
_hybrid_generator: Optional[HybridGenerator] = None


def get_hybrid_generator() -> HybridGenerator:
    """Get or create global HybridGenerator instance."""
    global _hybrid_generator
    if _hybrid_generator is None:
        _hybrid_generator = HybridGenerator()
    return _hybrid_generator
