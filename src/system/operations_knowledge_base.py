"""
Operations Knowledge Base and Decision Support System for SuperInsight Platform.

Provides intelligent operations knowledge management including:
- Operations knowledge base with case library
- Fault handling case repository
- Decision support system for operations
- Experience learning and accumulation
- Best practices recommendation engine
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import sqlite3
import pickle
from pathlib import Path

from src.system.fault_detection_system import FaultEvent, FaultType, FaultSeverity
from src.system.automated_operations import AutomationExecution, OperationType
from src.system.intelligent_operations import OperationalRecommendation, RecommendationType

logger = logging.getLogger(__name__)


class CaseType(Enum):
    """Types of operational cases."""
    FAULT_RESOLUTION = "fault_resolution"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    CAPACITY_PLANNING = "capacity_planning"
    SECURITY_INCIDENT = "security_incident"
    MAINTENANCE_PROCEDURE = "maintenance_procedure"
    CONFIGURATION_CHANGE = "configuration_change"


class CaseSeverity(Enum):
    """Severity levels for operational cases."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(Enum):
    """Status of operational cases."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class OperationalCase:
    """Operational case record."""
    case_id: str
    case_type: CaseType
    severity: CaseSeverity
    status: CaseStatus
    title: str
    description: str
    symptoms: List[str]
    root_cause: Optional[str] = None
    resolution_steps: List[str] = field(default_factory=list)
    resolution_time_minutes: Optional[int] = None
    tags: Set[str] = field(default_factory=set)
    related_metrics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    created_by: str = "system"
    assigned_to: Optional[str] = None
    effectiveness_score: float = 0.0  # 0-1 scale
    reoccurrence_count: int = 0


@dataclass
class KnowledgeArticle:
    """Knowledge base article."""
    article_id: str
    title: str
    content: str
    category: str
    tags: Set[str]
    author: str
    created_at: datetime
    updated_at: datetime
    view_count: int = 0
    rating: float = 0.0
    related_cases: List[str] = field(default_factory=list)


@dataclass
class DecisionContext:
    """Context for decision support."""
    situation_id: str
    description: str
    current_metrics: Dict[str, float]
    symptoms: List[str]
    constraints: Dict[str, Any]
    objectives: List[str]
    time_pressure: str  # low, medium, high, critical
    risk_tolerance: str  # low, medium, high


@dataclass
class DecisionRecommendation:
    """Decision support recommendation."""
    recommendation_id: str
    context_id: str
    recommended_action: str
    rationale: str
    confidence: float
    expected_outcome: str
    risks: List[str]
    prerequisites: List[str]
    estimated_effort: str
    similar_cases: List[str]
    success_probability: float


class CaseLibrary:
    """
    Case library for storing and retrieving operational cases.
    
    Provides case-based reasoning for operational decisions.
    """
    
    def __init__(self, db_path: str = "operations_cases.db"):
        self.db_path = db_path
        self.cases: Dict[str, OperationalCase] = {}
        self.case_index: Dict[str, Set[str]] = defaultdict(set)  # Tag -> case_ids
        self.similarity_cache: Dict[str, List[Tuple[str, float]]] = {}
        
        # Initialize database
        self._init_database()
        self._load_cases()
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operational_cases (
                    case_id TEXT PRIMARY KEY,
                    case_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    symptoms TEXT,  -- JSON array
                    root_cause TEXT,
                    resolution_steps TEXT,  -- JSON array
                    resolution_time_minutes INTEGER,
                    tags TEXT,  -- JSON array
                    related_metrics TEXT,  -- JSON object
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT,
                    created_by TEXT,
                    assigned_to TEXT,
                    effectiveness_score REAL DEFAULT 0.0,
                    reoccurrence_count INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Case library database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing case library database: {e}")
    
    def _load_cases(self):
        """Load cases from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM operational_cases")
            rows = cursor.fetchall()
            
            for row in rows:
                case = self._row_to_case(row)
                self.cases[case.case_id] = case
                self._update_index(case)
            
            conn.close()
            
            logger.info(f"Loaded {len(self.cases)} cases from database")
            
        except Exception as e:
            logger.error(f"Error loading cases from database: {e}")
    
    def _row_to_case(self, row: tuple) -> OperationalCase:
        """Convert database row to OperationalCase."""
        return OperationalCase(
            case_id=row[0],
            case_type=CaseType(row[1]),
            severity=CaseSeverity(row[2]),
            status=CaseStatus(row[3]),
            title=row[4],
            description=row[5],
            symptoms=json.loads(row[6]) if row[6] else [],
            root_cause=row[7],
            resolution_steps=json.loads(row[8]) if row[8] else [],
            resolution_time_minutes=row[9],
            tags=set(json.loads(row[10])) if row[10] else set(),
            related_metrics=json.loads(row[11]) if row[11] else {},
            created_at=datetime.fromisoformat(row[12]),
            updated_at=datetime.fromisoformat(row[13]),
            resolved_at=datetime.fromisoformat(row[14]) if row[14] else None,
            created_by=row[15] or "system",
            assigned_to=row[16],
            effectiveness_score=row[17] or 0.0,
            reoccurrence_count=row[18] or 0
        )
    
    def _case_to_row(self, case: OperationalCase) -> tuple:
        """Convert OperationalCase to database row."""
        return (
            case.case_id,
            case.case_type.value,
            case.severity.value,
            case.status.value,
            case.title,
            case.description,
            json.dumps(case.symptoms),
            case.root_cause,
            json.dumps(case.resolution_steps),
            case.resolution_time_minutes,
            json.dumps(list(case.tags)),
            json.dumps(case.related_metrics),
            case.created_at.isoformat(),
            case.updated_at.isoformat(),
            case.resolved_at.isoformat() if case.resolved_at else None,
            case.created_by,
            case.assigned_to,
            case.effectiveness_score,
            case.reoccurrence_count
        )
    
    def add_case(self, case: OperationalCase) -> bool:
        """Add a new case to the library."""
        try:
            # Store in memory
            self.cases[case.case_id] = case
            self._update_index(case)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO operational_cases VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', self._case_to_row(case))
            
            conn.commit()
            conn.close()
            
            # Clear similarity cache
            self.similarity_cache.clear()
            
            logger.info(f"Added case to library: {case.case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding case to library: {e}")
            return False
    
    def update_case(self, case: OperationalCase) -> bool:
        """Update an existing case."""
        try:
            case.updated_at = datetime.utcnow()
            
            # Update in memory
            self.cases[case.case_id] = case
            self._update_index(case)
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE operational_cases SET
                    case_type=?, severity=?, status=?, title=?, description=?,
                    symptoms=?, root_cause=?, resolution_steps=?, resolution_time_minutes=?,
                    tags=?, related_metrics=?, updated_at=?, resolved_at=?,
                    assigned_to=?, effectiveness_score=?, reoccurrence_count=?
                WHERE case_id=?
            ''', self._case_to_row(case)[1:] + (case.case_id,))
            
            conn.commit()
            conn.close()
            
            # Clear similarity cache
            self.similarity_cache.clear()
            
            logger.info(f"Updated case: {case.case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating case: {e}")
            return False
    
    def _update_index(self, case: OperationalCase):
        """Update search index for a case."""
        # Remove from old index entries
        for tag_set in self.case_index.values():
            tag_set.discard(case.case_id)
        
        # Add to new index entries
        for tag in case.tags:
            self.case_index[tag.lower()].add(case.case_id)
        
        # Add case type and severity to index
        self.case_index[case.case_type.value].add(case.case_id)
        self.case_index[case.severity.value].add(case.case_id)
    
    def search_cases(self, query: str, case_type: Optional[CaseType] = None,
                    severity: Optional[CaseSeverity] = None,
                    status: Optional[CaseStatus] = None,
                    tags: Optional[List[str]] = None,
                    limit: int = 10) -> List[OperationalCase]:
        """Search cases by various criteria."""
        try:
            matching_cases = set(self.cases.keys())
            
            # Filter by case type
            if case_type:
                type_cases = self.case_index.get(case_type.value, set())
                matching_cases = matching_cases.intersection(type_cases)
            
            # Filter by severity
            if severity:
                severity_cases = self.case_index.get(severity.value, set())
                matching_cases = matching_cases.intersection(severity_cases)
            
            # Filter by status
            if status:
                matching_cases = {cid for cid in matching_cases 
                                if self.cases[cid].status == status}
            
            # Filter by tags
            if tags:
                for tag in tags:
                    tag_cases = self.case_index.get(tag.lower(), set())
                    matching_cases = matching_cases.intersection(tag_cases)
            
            # Filter by text query
            if query:
                query_lower = query.lower()
                text_matches = set()
                
                for case_id in matching_cases:
                    case = self.cases[case_id]
                    if (query_lower in case.title.lower() or
                        query_lower in case.description.lower() or
                        any(query_lower in symptom.lower() for symptom in case.symptoms)):
                        text_matches.add(case_id)
                
                matching_cases = text_matches
            
            # Convert to case objects and sort by relevance
            results = [self.cases[cid] for cid in matching_cases]
            results.sort(key=lambda c: (c.effectiveness_score, c.updated_at), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching cases: {e}")
            return []
    
    def find_similar_cases(self, symptoms: List[str], metrics: Dict[str, float],
                          case_type: Optional[CaseType] = None,
                          limit: int = 5) -> List[Tuple[OperationalCase, float]]:
        """Find cases similar to given symptoms and metrics."""
        try:
            # Create cache key
            cache_key = hashlib.md5(
                (str(sorted(symptoms)) + str(sorted(metrics.items()))).encode()
            ).hexdigest()
            
            if cache_key in self.similarity_cache:
                cached_results = self.similarity_cache[cache_key]
                return [(self.cases[cid], score) for cid, score in cached_results[:limit]]
            
            similarities = []
            
            for case in self.cases.values():
                if case_type and case.case_type != case_type:
                    continue
                
                similarity = self._calculate_similarity(symptoms, metrics, case)
                if similarity > 0.1:  # Minimum similarity threshold
                    similarities.append((case, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Cache results
            self.similarity_cache[cache_key] = [(case.case_id, score) for case, score in similarities]
            
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar cases: {e}")
            return []
    
    def _calculate_similarity(self, symptoms: List[str], metrics: Dict[str, float],
                            case: OperationalCase) -> float:
        """Calculate similarity between input and a case."""
        try:
            similarity_score = 0.0
            
            # Symptom similarity (40% weight)
            symptom_similarity = self._calculate_text_similarity(symptoms, case.symptoms)
            similarity_score += symptom_similarity * 0.4
            
            # Metric similarity (30% weight)
            metric_similarity = self._calculate_metric_similarity(metrics, case.related_metrics)
            similarity_score += metric_similarity * 0.3
            
            # Case effectiveness (20% weight)
            effectiveness_bonus = case.effectiveness_score * 0.2
            similarity_score += effectiveness_bonus
            
            # Recency bonus (10% weight)
            days_old = (datetime.utcnow() - case.updated_at).days
            recency_bonus = max(0, 1 - days_old / 365) * 0.1  # Decay over a year
            similarity_score += recency_bonus
            
            return min(1.0, similarity_score)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _calculate_text_similarity(self, text1_list: List[str], text2_list: List[str]) -> float:
        """Calculate text similarity between two lists of strings."""
        try:
            if not text1_list or not text2_list:
                return 0.0
            
            # Simple word-based similarity
            words1 = set()
            for text in text1_list:
                words1.update(text.lower().split())
            
            words2 = set()
            for text in text2_list:
                words2.update(text.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating text similarity: {e}")
            return 0.0
    
    def _calculate_metric_similarity(self, metrics1: Dict[str, float], 
                                   metrics2: Dict[str, float]) -> float:
        """Calculate similarity between two metric dictionaries."""
        try:
            if not metrics1 or not metrics2:
                return 0.0
            
            common_metrics = set(metrics1.keys()).intersection(set(metrics2.keys()))
            
            if not common_metrics:
                return 0.0
            
            similarities = []
            
            for metric in common_metrics:
                val1, val2 = metrics1[metric], metrics2[metric]
                
                # Avoid division by zero
                if val1 == 0 and val2 == 0:
                    similarities.append(1.0)
                elif val1 == 0 or val2 == 0:
                    similarities.append(0.0)
                else:
                    # Calculate relative similarity
                    ratio = min(val1, val2) / max(val1, val2)
                    similarities.append(ratio)
            
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating metric similarity: {e}")
            return 0.0
    
    def get_case_statistics(self) -> Dict[str, Any]:
        """Get statistics about the case library."""
        try:
            stats = {
                "total_cases": len(self.cases),
                "by_type": defaultdict(int),
                "by_severity": defaultdict(int),
                "by_status": defaultdict(int),
                "resolution_times": [],
                "effectiveness_scores": [],
                "most_common_tags": defaultdict(int)
            }
            
            for case in self.cases.values():
                stats["by_type"][case.case_type.value] += 1
                stats["by_severity"][case.severity.value] += 1
                stats["by_status"][case.status.value] += 1
                
                if case.resolution_time_minutes:
                    stats["resolution_times"].append(case.resolution_time_minutes)
                
                stats["effectiveness_scores"].append(case.effectiveness_score)
                
                for tag in case.tags:
                    stats["most_common_tags"][tag] += 1
            
            # Calculate averages
            if stats["resolution_times"]:
                stats["avg_resolution_time"] = sum(stats["resolution_times"]) / len(stats["resolution_times"])
            else:
                stats["avg_resolution_time"] = 0
            
            if stats["effectiveness_scores"]:
                stats["avg_effectiveness"] = sum(stats["effectiveness_scores"]) / len(stats["effectiveness_scores"])
            else:
                stats["avg_effectiveness"] = 0
            
            # Convert defaultdicts to regular dicts
            stats["by_type"] = dict(stats["by_type"])
            stats["by_severity"] = dict(stats["by_severity"])
            stats["by_status"] = dict(stats["by_status"])
            stats["most_common_tags"] = dict(sorted(stats["most_common_tags"].items(), 
                                                   key=lambda x: x[1], reverse=True)[:10])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting case statistics: {e}")
            return {}


class KnowledgeBase:
    """
    Operations knowledge base for storing and retrieving operational knowledge.
    
    Provides structured knowledge management for operations teams.
    """
    
    def __init__(self, kb_path: str = "operations_kb.db"):
        self.kb_path = kb_path
        self.articles: Dict[str, KnowledgeArticle] = {}
        self.article_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Initialize database
        self._init_database()
        self._load_articles()
    
    def _init_database(self):
        """Initialize knowledge base database."""
        try:
            conn = sqlite3.connect(self.kb_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_articles (
                    article_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    author TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    view_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    related_cases TEXT  -- JSON array
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Knowledge base database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing knowledge base database: {e}")
    
    def _load_articles(self):
        """Load articles from database."""
        try:
            conn = sqlite3.connect(self.kb_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM knowledge_articles")
            rows = cursor.fetchall()
            
            for row in rows:
                article = KnowledgeArticle(
                    article_id=row[0],
                    title=row[1],
                    content=row[2],
                    category=row[3],
                    tags=set(json.loads(row[4])) if row[4] else set(),
                    author=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                    view_count=row[8] or 0,
                    rating=row[9] or 0.0,
                    related_cases=json.loads(row[10]) if row[10] else []
                )
                
                self.articles[article.article_id] = article
                self._update_article_index(article)
            
            conn.close()
            
            logger.info(f"Loaded {len(self.articles)} articles from knowledge base")
            
        except Exception as e:
            logger.error(f"Error loading articles from knowledge base: {e}")
    
    def add_article(self, article: KnowledgeArticle) -> bool:
        """Add a new article to the knowledge base."""
        try:
            # Store in memory
            self.articles[article.article_id] = article
            self._update_article_index(article)
            
            # Store in database
            conn = sqlite3.connect(self.kb_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_articles VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.article_id,
                article.title,
                article.content,
                article.category,
                json.dumps(list(article.tags)),
                article.author,
                article.created_at.isoformat(),
                article.updated_at.isoformat(),
                article.view_count,
                article.rating,
                json.dumps(article.related_cases)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added article to knowledge base: {article.article_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding article to knowledge base: {e}")
            return False
    
    def _update_article_index(self, article: KnowledgeArticle):
        """Update search index for an article."""
        # Remove from old index entries
        for tag_set in self.article_index.values():
            tag_set.discard(article.article_id)
        
        # Add to new index entries
        for tag in article.tags:
            self.article_index[tag.lower()].add(article.article_id)
        
        # Add category to index
        self.article_index[article.category.lower()].add(article.article_id)
    
    def search_articles(self, query: str, category: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       limit: int = 10) -> List[KnowledgeArticle]:
        """Search articles by query, category, and tags."""
        try:
            matching_articles = set(self.articles.keys())
            
            # Filter by category
            if category:
                category_articles = self.article_index.get(category.lower(), set())
                matching_articles = matching_articles.intersection(category_articles)
            
            # Filter by tags
            if tags:
                for tag in tags:
                    tag_articles = self.article_index.get(tag.lower(), set())
                    matching_articles = matching_articles.intersection(tag_articles)
            
            # Filter by text query
            if query:
                query_lower = query.lower()
                text_matches = set()
                
                for article_id in matching_articles:
                    article = self.articles[article_id]
                    if (query_lower in article.title.lower() or
                        query_lower in article.content.lower()):
                        text_matches.add(article_id)
                
                matching_articles = text_matches
            
            # Convert to article objects and sort by relevance
            results = [self.articles[aid] for aid in matching_articles]
            results.sort(key=lambda a: (a.rating, a.view_count), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return []


class DecisionSupportSystem:
    """
    Decision support system for operational decisions.
    
    Provides intelligent recommendations based on context and historical data.
    """
    
    def __init__(self, case_library: CaseLibrary, knowledge_base: KnowledgeBase):
        self.case_library = case_library
        self.knowledge_base = knowledge_base
        self.decision_history: deque = deque(maxlen=1000)
        self.decision_rules: Dict[str, Dict[str, Any]] = {}
        
        # Setup default decision rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default decision rules."""
        self.decision_rules = {
            "high_cpu_usage": {
                "conditions": {"cpu_usage_percent": {"min": 80}},
                "recommendations": [
                    "Scale up CPU resources",
                    "Optimize CPU-intensive processes",
                    "Implement load balancing"
                ],
                "confidence": 0.8
            },
            "high_memory_usage": {
                "conditions": {"memory_usage_percent": {"min": 85}},
                "recommendations": [
                    "Scale up memory resources",
                    "Investigate memory leaks",
                    "Optimize data structures"
                ],
                "confidence": 0.8
            },
            "slow_response_time": {
                "conditions": {"response_time_ms": {"min": 2000}},
                "recommendations": [
                    "Optimize database queries",
                    "Implement caching",
                    "Scale application servers"
                ],
                "confidence": 0.7
            }
        }
    
    async def get_decision_recommendations(self, context: DecisionContext) -> List[DecisionRecommendation]:
        """Get decision recommendations for a given context."""
        try:
            recommendations = []
            
            # Rule-based recommendations
            rule_recommendations = await self._get_rule_based_recommendations(context)
            recommendations.extend(rule_recommendations)
            
            # Case-based recommendations
            case_recommendations = await self._get_case_based_recommendations(context)
            recommendations.extend(case_recommendations)
            
            # Knowledge-based recommendations
            kb_recommendations = await self._get_knowledge_based_recommendations(context)
            recommendations.extend(kb_recommendations)
            
            # Sort by confidence and success probability
            recommendations.sort(key=lambda r: (r.confidence, r.success_probability), reverse=True)
            
            # Store decision context
            self.decision_history.append({
                "context": context,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow()
            })
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error getting decision recommendations: {e}")
            return []
    
    async def _get_rule_based_recommendations(self, context: DecisionContext) -> List[DecisionRecommendation]:
        """Get recommendations based on predefined rules."""
        try:
            recommendations = []
            
            for rule_name, rule in self.decision_rules.items():
                if self._matches_rule_conditions(context.current_metrics, rule["conditions"]):
                    for i, recommendation_text in enumerate(rule["recommendations"]):
                        recommendation = DecisionRecommendation(
                            recommendation_id=f"rule_{rule_name}_{i}_{int(time.time())}",
                            context_id=context.situation_id,
                            recommended_action=recommendation_text,
                            rationale=f"Based on rule: {rule_name}",
                            confidence=rule["confidence"],
                            expected_outcome="Improved system performance",
                            risks=["Temporary service disruption", "Resource costs"],
                            prerequisites=["System access", "Change approval"],
                            estimated_effort="medium",
                            similar_cases=[],
                            success_probability=0.7
                        )
                        recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting rule-based recommendations: {e}")
            return []
    
    def _matches_rule_conditions(self, metrics: Dict[str, float], conditions: Dict[str, Dict[str, float]]) -> bool:
        """Check if metrics match rule conditions."""
        try:
            for metric_name, condition in conditions.items():
                if metric_name not in metrics:
                    continue
                
                metric_value = metrics[metric_name]
                
                if "min" in condition and metric_value < condition["min"]:
                    return False
                
                if "max" in condition and metric_value > condition["max"]:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error matching rule conditions: {e}")
            return False
    
    async def _get_case_based_recommendations(self, context: DecisionContext) -> List[DecisionRecommendation]:
        """Get recommendations based on similar historical cases."""
        try:
            recommendations = []
            
            # Find similar cases
            similar_cases = self.case_library.find_similar_cases(
                symptoms=context.symptoms,
                metrics=context.current_metrics,
                limit=3
            )
            
            for case, similarity in similar_cases:
                if case.status == CaseStatus.RESOLVED and case.resolution_steps:
                    for i, step in enumerate(case.resolution_steps):
                        recommendation = DecisionRecommendation(
                            recommendation_id=f"case_{case.case_id}_{i}_{int(time.time())}",
                            context_id=context.situation_id,
                            recommended_action=step,
                            rationale=f"Based on similar case: {case.title} (similarity: {similarity:.2f})",
                            confidence=similarity * case.effectiveness_score,
                            expected_outcome=f"Resolution similar to case {case.case_id}",
                            risks=["May not apply to current situation"],
                            prerequisites=["Verify applicability"],
                            estimated_effort="medium",
                            similar_cases=[case.case_id],
                            success_probability=case.effectiveness_score
                        )
                        recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting case-based recommendations: {e}")
            return []
    
    async def _get_knowledge_based_recommendations(self, context: DecisionContext) -> List[DecisionRecommendation]:
        """Get recommendations based on knowledge base articles."""
        try:
            recommendations = []
            
            # Search for relevant articles
            query = " ".join(context.symptoms + context.objectives)
            articles = self.knowledge_base.search_articles(query, limit=3)
            
            for article in articles:
                # Extract actionable recommendations from article content
                # This is a simplified implementation - in practice, you'd use NLP
                if "recommendation" in article.content.lower() or "solution" in article.content.lower():
                    recommendation = DecisionRecommendation(
                        recommendation_id=f"kb_{article.article_id}_{int(time.time())}",
                        context_id=context.situation_id,
                        recommended_action=f"Follow guidance in: {article.title}",
                        rationale=f"Based on knowledge base article: {article.title}",
                        confidence=min(0.8, article.rating / 5.0),  # Normalize rating to 0-1
                        expected_outcome="Resolution based on documented best practices",
                        risks=["May require adaptation to current context"],
                        prerequisites=["Review full article", "Verify applicability"],
                        estimated_effort="medium",
                        similar_cases=[],
                        success_probability=0.6
                    )
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting knowledge-based recommendations: {e}")
            return []
    
    def record_decision_outcome(self, recommendation_id: str, success: bool, 
                              actual_outcome: str, lessons_learned: str):
        """Record the outcome of a decision for learning."""
        try:
            # Find the recommendation in history
            for decision_record in reversed(self.decision_history):
                for rec in decision_record["recommendations"]:
                    if rec.recommendation_id == recommendation_id:
                        # Update recommendation with outcome
                        outcome_record = {
                            "recommendation_id": recommendation_id,
                            "success": success,
                            "actual_outcome": actual_outcome,
                            "lessons_learned": lessons_learned,
                            "recorded_at": datetime.utcnow()
                        }
                        
                        # Store outcome (in practice, this would update a database)
                        logger.info(f"Recorded decision outcome for {recommendation_id}: {'success' if success else 'failure'}")
                        return True
            
            logger.warning(f"Recommendation {recommendation_id} not found in history")
            return False
            
        except Exception as e:
            logger.error(f"Error recording decision outcome: {e}")
            return False


class OperationsKnowledgeSystem:
    """
    Main operations knowledge system integrating all knowledge management components.
    
    Provides unified interface for case management, knowledge base, and decision support.
    """
    
    def __init__(self, data_dir: str = "operations_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.case_library = CaseLibrary(str(self.data_dir / "cases.db"))
        self.knowledge_base = KnowledgeBase(str(self.data_dir / "knowledge.db"))
        self.decision_support = DecisionSupportSystem(self.case_library, self.knowledge_base)
        
        # Learning system
        self.learning_enabled = True
        self.auto_case_creation = True
        
        # Initialize with default knowledge
        self._initialize_default_knowledge()
    
    def _initialize_default_knowledge(self):
        """Initialize system with default operational knowledge."""
        try:
            # Add default knowledge articles
            default_articles = [
                {
                    "title": "High CPU Usage Troubleshooting",
                    "content": """
                    When CPU usage is consistently high (>80%):
                    1. Identify top CPU-consuming processes using top/htop
                    2. Check for runaway processes or infinite loops
                    3. Optimize or restart problematic services
                    4. Consider scaling up CPU resources
                    5. Implement load balancing if applicable
                    """,
                    "category": "performance",
                    "tags": {"cpu", "performance", "troubleshooting"}
                },
                {
                    "title": "Memory Leak Investigation",
                    "content": """
                    To investigate memory leaks:
                    1. Monitor memory usage over time
                    2. Use memory profiling tools (valgrind, heapdump)
                    3. Check for unclosed resources (files, connections)
                    4. Review recent code changes
                    5. Restart affected services as temporary fix
                    6. Implement proper resource cleanup
                    """,
                    "category": "performance",
                    "tags": {"memory", "leak", "debugging"}
                },
                {
                    "title": "Database Performance Optimization",
                    "content": """
                    Database performance optimization steps:
                    1. Identify slow queries using query logs
                    2. Add appropriate indexes
                    3. Optimize query structure
                    4. Update table statistics
                    5. Consider query caching
                    6. Monitor connection pool usage
                    """,
                    "category": "database",
                    "tags": {"database", "performance", "optimization"}
                }
            ]
            
            for i, article_data in enumerate(default_articles):
                article = KnowledgeArticle(
                    article_id=f"default_{i}",
                    title=article_data["title"],
                    content=article_data["content"],
                    category=article_data["category"],
                    tags=article_data["tags"],
                    author="system",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                if article.article_id not in self.knowledge_base.articles:
                    self.knowledge_base.add_article(article)
            
            logger.info("Default knowledge articles initialized")
            
        except Exception as e:
            logger.error(f"Error initializing default knowledge: {e}")
    
    async def create_case_from_fault(self, fault_event: FaultEvent) -> Optional[OperationalCase]:
        """Create a case from a fault event."""
        try:
            if not self.auto_case_creation:
                return None
            
            case = OperationalCase(
                case_id=f"fault_{fault_event.fault_id}",
                case_type=self._fault_type_to_case_type(fault_event.fault_type),
                severity=self._fault_severity_to_case_severity(fault_event.severity),
                status=CaseStatus.OPEN,
                title=f"Fault: {fault_event.description}",
                description=fault_event.description,
                symptoms=[fault_event.description],
                root_cause=fault_event.root_cause,
                tags={fault_event.fault_type.value, fault_event.service_name},
                related_metrics=fault_event.metrics,
                created_by="system"
            )
            
            if self.case_library.add_case(case):
                logger.info(f"Created case from fault: {case.case_id}")
                return case
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating case from fault: {e}")
            return None
    
    async def update_case_from_automation(self, case_id: str, automation_execution: AutomationExecution):
        """Update a case with automation execution results."""
        try:
            if case_id not in self.case_library.cases:
                return False
            
            case = self.case_library.cases[case_id]
            
            # Add automation steps to resolution
            if automation_execution.success:
                case.resolution_steps.append(automation_execution.action_taken)
                case.status = CaseStatus.RESOLVED
                case.resolved_at = automation_execution.completed_at
                
                if automation_execution.started_at and automation_execution.completed_at:
                    resolution_time = (automation_execution.completed_at - automation_execution.started_at).total_seconds() / 60
                    case.resolution_time_minutes = int(resolution_time)
                
                # Calculate effectiveness based on success
                case.effectiveness_score = 0.8  # Automated resolution gets good score
            else:
                case.resolution_steps.append(f"Failed: {automation_execution.action_taken}")
                if automation_execution.error_message:
                    case.resolution_steps.append(f"Error: {automation_execution.error_message}")
            
            return self.case_library.update_case(case)
            
        except Exception as e:
            logger.error(f"Error updating case from automation: {e}")
            return False
    
    def _fault_type_to_case_type(self, fault_type: FaultType) -> CaseType:
        """Convert fault type to case type."""
        mapping = {
            FaultType.SERVICE_UNAVAILABLE: CaseType.FAULT_RESOLUTION,
            FaultType.PERFORMANCE_DEGRADATION: CaseType.PERFORMANCE_OPTIMIZATION,
            FaultType.RESOURCE_EXHAUSTION: CaseType.CAPACITY_PLANNING,
            FaultType.CASCADE_FAILURE: CaseType.FAULT_RESOLUTION,
            FaultType.SECURITY_BREACH: CaseType.SECURITY_INCIDENT,
            FaultType.CONFIGURATION_ERROR: CaseType.CONFIGURATION_CHANGE
        }
        return mapping.get(fault_type, CaseType.FAULT_RESOLUTION)
    
    def _fault_severity_to_case_severity(self, fault_severity: FaultSeverity) -> CaseSeverity:
        """Convert fault severity to case severity."""
        mapping = {
            FaultSeverity.LOW: CaseSeverity.LOW,
            FaultSeverity.MEDIUM: CaseSeverity.MEDIUM,
            FaultSeverity.HIGH: CaseSeverity.HIGH,
            FaultSeverity.CRITICAL: CaseSeverity.CRITICAL
        }
        return mapping.get(fault_severity, CaseSeverity.MEDIUM)
    
    async def learn_from_recommendation(self, recommendation: OperationalRecommendation, 
                                      success: bool, outcome: str):
        """Learn from recommendation outcomes to improve future suggestions."""
        try:
            if not self.learning_enabled:
                return
            
            # Create or update knowledge based on recommendation outcome
            if success:
                # Create knowledge article from successful recommendation
                article = KnowledgeArticle(
                    article_id=f"learned_{recommendation.recommendation_id}",
                    title=f"Successful Resolution: {recommendation.title}",
                    content=f"""
                    Recommendation: {recommendation.description}
                    Outcome: {outcome}
                    Success: Yes
                    
                    This approach was successful and can be applied to similar situations.
                    """,
                    category="learned_solutions",
                    tags={"learned", "successful", recommendation.recommendation_type.value},
                    author="learning_system",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    rating=4.0  # High rating for successful outcomes
                )
                
                self.knowledge_base.add_article(article)
                logger.info(f"Created knowledge article from successful recommendation: {recommendation.recommendation_id}")
            
        except Exception as e:
            logger.error(f"Error learning from recommendation: {e}")
    
    def get_system_insights(self) -> Dict[str, Any]:
        """Get comprehensive insights about the knowledge system."""
        try:
            case_stats = self.case_library.get_case_statistics()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "case_library": {
                    "total_cases": case_stats.get("total_cases", 0),
                    "by_type": case_stats.get("by_type", {}),
                    "by_severity": case_stats.get("by_severity", {}),
                    "by_status": case_stats.get("by_status", {}),
                    "avg_resolution_time": case_stats.get("avg_resolution_time", 0),
                    "avg_effectiveness": case_stats.get("avg_effectiveness", 0)
                },
                "knowledge_base": {
                    "total_articles": len(self.knowledge_base.articles),
                    "categories": list(set(a.category for a in self.knowledge_base.articles.values())),
                    "most_viewed": sorted(
                        self.knowledge_base.articles.values(),
                        key=lambda a: a.view_count,
                        reverse=True
                    )[:5]
                },
                "decision_support": {
                    "total_decisions": len(self.decision_support.decision_history),
                    "recent_decisions": len([d for d in self.decision_support.decision_history 
                                           if (datetime.utcnow() - d["timestamp"]).days <= 7])
                },
                "learning_status": {
                    "learning_enabled": self.learning_enabled,
                    "auto_case_creation": self.auto_case_creation
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system insights: {e}")
            return {"error": str(e)}


# Global instance
operations_knowledge = None

def get_operations_knowledge() -> OperationsKnowledgeSystem:
    """Get the global operations knowledge system instance."""
    global operations_knowledge
    if operations_knowledge is None:
        operations_knowledge = OperationsKnowledgeSystem()
    
    return operations_knowledge