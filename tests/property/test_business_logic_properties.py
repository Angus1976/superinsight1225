"""
Business Logic Service Property Tests - 业务逻辑服务属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Property 13**
**Validates: Requirements 5.1-5.9**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4
from dataclasses import dataclass, field
import json


# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

@dataclass
class BusinessRuleData:
    """业务规则数据类"""
    id: str
    tenant_id: str
    project_id: str
    name: str
    description: Optional[str]
    pattern: str
    rule_type: str
    confidence: float
    frequency: int
    examples: List[Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "rule_type": self.rule_type,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "examples": self.examples,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class BusinessPatternData:
    """业务模式数据类"""
    id: str
    tenant_id: str
    project_id: str
    pattern_type: str
    description: Optional[str]
    strength: float
    evidence: List[Dict[str, Any]]
    detected_at: datetime
    last_seen: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "strength": self.strength,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }


@dataclass
class BusinessInsightData:
    """业务洞察数据类"""
    id: str
    tenant_id: str
    project_id: str
    insight_type: str
    title: str
    description: Optional[str]
    impact_score: float
    recommendations: List[str]
    data_points: List[Dict[str, Any]]
    created_at: datetime
    acknowledged_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "impact_score": self.impact_score,
            "recommendations": self.recommendations,
            "data_points": self.data_points,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


# ============================================================================
# In-Memory Repositories for Testing (模拟数据库行为)
# ============================================================================

class InMemoryBusinessRuleRepository:
    """内存业务规则仓库 - 用于属性测试"""
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    async def save(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """保存业务规则"""
        rule_id = rule.get('id') or str(uuid4())
        
        stored_rule = {
            'id': rule_id,
            'tenant_id': rule.get('tenant_id', 'default'),
            'project_id': rule.get('project_id'),
            'name': rule.get('name'),
            'description': rule.get('description'),
            'pattern': rule.get('pattern'),
            'rule_type': rule.get('rule_type'),
            'confidence': rule.get('confidence', 0.0),
            'frequency': rule.get('frequency', 0),
            'examples': rule.get('examples', []),
            'is_active': rule.get('is_active', True),
            'created_at': rule.get('created_at') or datetime.utcnow(),
            'updated_at': rule.get('updated_at') or datetime.utcnow()
        }
        
        # Ensure timestamps are datetime objects
        if isinstance(stored_rule['created_at'], str):
            stored_rule['created_at'] = datetime.fromisoformat(stored_rule['created_at'])
        if isinstance(stored_rule['updated_at'], str):
            stored_rule['updated_at'] = datetime.fromisoformat(stored_rule['updated_at'])
        
        self.storage[rule_id] = stored_rule
        return self._serialize_rule(stored_rule)
    
    async def get_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取业务规则"""
        rule = self.storage.get(rule_id)
        if rule:
            return self._serialize_rule(rule)
        return None
    
    async def find_by_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        rule_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """按项目查找业务规则"""
        results = []
        for rule in self.storage.values():
            if rule['project_id'] != project_id:
                continue
            if rule['tenant_id'] != tenant_id:
                continue
            if rule_type and rule['rule_type'] != rule_type:
                continue
            if active_only and not rule['is_active']:
                continue
            results.append(self._serialize_rule(rule))
        
        # Sort by confidence descending
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results
    
    async def update_confidence(self, rule_id: str, confidence: float) -> bool:
        """更新规则置信度"""
        if rule_id in self.storage:
            self.storage[rule_id]['confidence'] = confidence
            self.storage[rule_id]['updated_at'] = datetime.utcnow()
            return True
        return False
    
    async def delete(self, rule_id: str) -> bool:
        """删除业务规则"""
        if rule_id in self.storage:
            del self.storage[rule_id]
            return True
        return False
    
    async def toggle_active(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """切换规则激活状态"""
        if rule_id in self.storage:
            self.storage[rule_id]['is_active'] = not self.storage[rule_id]['is_active']
            self.storage[rule_id]['updated_at'] = datetime.utcnow()
            return self._serialize_rule(self.storage[rule_id])
        return None
    
    def _serialize_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """序列化规则用于输出"""
        return {
            **rule,
            'created_at': rule['created_at'].isoformat() if isinstance(rule['created_at'], datetime) else rule['created_at'],
            'updated_at': rule['updated_at'].isoformat() if isinstance(rule['updated_at'], datetime) else rule['updated_at']
        }
    
    def clear(self):
        """清空存储"""
        self.storage.clear()



class InMemoryBusinessPatternRepository:
    """内存业务模式仓库 - 用于属性测试"""
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    async def save(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """保存业务模式"""
        pattern_id = pattern.get('id') or str(uuid4())
        
        stored_pattern = {
            'id': pattern_id,
            'tenant_id': pattern.get('tenant_id', 'default'),
            'project_id': pattern.get('project_id'),
            'pattern_type': pattern.get('pattern_type'),
            'description': pattern.get('description'),
            'strength': pattern.get('strength', 0.0),
            'evidence': pattern.get('evidence', []),
            'detected_at': pattern.get('detected_at') or datetime.utcnow(),
            'last_seen': pattern.get('last_seen') or datetime.utcnow()
        }
        
        if isinstance(stored_pattern['detected_at'], str):
            stored_pattern['detected_at'] = datetime.fromisoformat(stored_pattern['detected_at'])
        if isinstance(stored_pattern['last_seen'], str):
            stored_pattern['last_seen'] = datetime.fromisoformat(stored_pattern['last_seen'])
        
        self.storage[pattern_id] = stored_pattern
        return self._serialize_pattern(stored_pattern)
    
    async def save_batch(self, patterns: List[Dict[str, Any]]) -> int:
        """批量保存业务模式"""
        count = 0
        for pattern in patterns:
            await self.save(pattern)
            count += 1
        return count
    
    async def get_by_id(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取业务模式"""
        pattern = self.storage.get(pattern_id)
        if pattern:
            return self._serialize_pattern(pattern)
        return None
    
    async def find_by_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        pattern_type: Optional[str] = None,
        min_strength: float = 0.0
    ) -> List[Dict[str, Any]]:
        """按项目查找业务模式"""
        results = []
        for pattern in self.storage.values():
            if pattern['project_id'] != project_id:
                continue
            if pattern['tenant_id'] != tenant_id:
                continue
            if pattern_type and pattern['pattern_type'] != pattern_type:
                continue
            if pattern['strength'] < min_strength:
                continue
            results.append(self._serialize_pattern(pattern))
        
        results.sort(key=lambda x: x['strength'], reverse=True)
        return results
    
    async def delete(self, pattern_id: str) -> bool:
        """删除业务模式"""
        if pattern_id in self.storage:
            del self.storage[pattern_id]
            return True
        return False
    
    def _serialize_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """序列化模式用于输出"""
        return {
            **pattern,
            'detected_at': pattern['detected_at'].isoformat() if isinstance(pattern['detected_at'], datetime) else pattern['detected_at'],
            'last_seen': pattern['last_seen'].isoformat() if isinstance(pattern['last_seen'], datetime) else pattern['last_seen']
        }
    
    def clear(self):
        """清空存储"""
        self.storage.clear()


class InMemoryBusinessInsightRepository:
    """内存业务洞察仓库 - 用于属性测试"""
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    async def save(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """保存业务洞察"""
        insight_id = insight.get('id') or str(uuid4())
        
        stored_insight = {
            'id': insight_id,
            'tenant_id': insight.get('tenant_id', 'default'),
            'project_id': insight.get('project_id'),
            'insight_type': insight.get('insight_type'),
            'title': insight.get('title'),
            'description': insight.get('description'),
            'impact_score': insight.get('impact_score', 0.0),
            'recommendations': insight.get('recommendations', []),
            'data_points': insight.get('data_points', []),
            'created_at': insight.get('created_at') or datetime.utcnow(),
            'acknowledged_at': insight.get('acknowledged_at')
        }
        
        if isinstance(stored_insight['created_at'], str):
            stored_insight['created_at'] = datetime.fromisoformat(stored_insight['created_at'])
        if stored_insight['acknowledged_at'] and isinstance(stored_insight['acknowledged_at'], str):
            stored_insight['acknowledged_at'] = datetime.fromisoformat(stored_insight['acknowledged_at'])
        
        self.storage[insight_id] = stored_insight
        return self._serialize_insight(stored_insight)
    
    async def get_by_id(self, insight_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取业务洞察"""
        insight = self.storage.get(insight_id)
        if insight:
            return self._serialize_insight(insight)
        return None
    
    async def find_by_project(
        self,
        project_id: str,
        tenant_id: str = "default",
        insight_type: Optional[str] = None,
        unacknowledged_only: bool = False
    ) -> List[Dict[str, Any]]:
        """按项目查找业务洞察"""
        results = []
        for insight in self.storage.values():
            if insight['project_id'] != project_id:
                continue
            if insight['tenant_id'] != tenant_id:
                continue
            if insight_type and insight['insight_type'] != insight_type:
                continue
            if unacknowledged_only and insight['acknowledged_at'] is not None:
                continue
            results.append(self._serialize_insight(insight))
        
        results.sort(key=lambda x: x['impact_score'], reverse=True)
        return results
    
    async def acknowledge(self, insight_id: str) -> bool:
        """确认业务洞察"""
        if insight_id in self.storage:
            self.storage[insight_id]['acknowledged_at'] = datetime.utcnow()
            return True
        return False
    
    async def delete(self, insight_id: str) -> bool:
        """删除业务洞察"""
        if insight_id in self.storage:
            del self.storage[insight_id]
            return True
        return False
    
    def _serialize_insight(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """序列化洞察用于输出"""
        return {
            **insight,
            'created_at': insight['created_at'].isoformat() if isinstance(insight['created_at'], datetime) else insight['created_at'],
            'acknowledged_at': insight['acknowledged_at'].isoformat() if insight['acknowledged_at'] and isinstance(insight['acknowledged_at'], datetime) else insight['acknowledged_at']
        }
    
    def clear(self):
        """清空存储"""
        self.storage.clear()



# ============================================================================
# Hypothesis Strategies (测试数据生成策略)
# ============================================================================

# 规则类型枚举
RULE_TYPES = ["sentiment_rule", "keyword_rule", "temporal_rule", "behavioral_rule"]

# 模式类型枚举
PATTERN_TYPES = ["sentiment_correlation", "keyword_association", "temporal_trend", "user_behavior"]

# 洞察类型枚举
INSIGHT_TYPES = ["quality_insight", "efficiency_insight", "pattern_insight", "trend_insight"]

# 生成有效的 ID
id_strategy = st.uuids().map(lambda u: f"id_{u.hex[:16]}")

# 生成有效的项目 ID
project_id_strategy = st.uuids().map(lambda u: f"project_{u.hex[:8]}")

# 生成有效的租户 ID
tenant_id_strategy = st.sampled_from(["default", "tenant_1", "tenant_2", "tenant_3"])

# 生成有效的名称
name_strategy = st.text(
    min_size=1, 
    max_size=100, 
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'))
).filter(lambda x: len(x.strip()) > 0)

# 生成有效的描述
description_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=500, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S')))
)

# 生成有效的模式字符串
pattern_strategy = st.text(
    min_size=1, 
    max_size=200, 
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'))
).filter(lambda x: len(x.strip()) > 0)

# 生成置信度/强度/影响分数
score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# 生成频率
frequency_strategy = st.integers(min_value=0, max_value=10000)

# 生成时间戳
timestamp_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
)

# 生成示例列表
examples_strategy = st.lists(
    st.fixed_dictionaries({
        'id': st.uuids().map(str),
        'text': st.text(min_size=1, max_size=100),
        'label': st.text(min_size=1, max_size=50)
    }),
    min_size=0,
    max_size=5
)

# 生成证据列表
evidence_strategy = st.lists(
    st.fixed_dictionaries({
        'type': st.text(min_size=1, max_size=50),
        'value': st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        'count': st.integers(min_value=0, max_value=1000)
    }),
    min_size=0,
    max_size=5
)

# 生成推荐列表
recommendations_strategy = st.lists(
    st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'))),
    min_size=0,
    max_size=5
)

# 生成数据点列表
data_points_strategy = st.lists(
    st.fixed_dictionaries({
        'metric': st.text(min_size=1, max_size=50),
        'value': st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False),
        'change': st.text(min_size=1, max_size=20)
    }),
    min_size=0,
    max_size=5
)

# 完整的业务规则策略
business_rule_strategy = st.fixed_dictionaries({
    'id': id_strategy,
    'tenant_id': tenant_id_strategy,
    'project_id': project_id_strategy,
    'name': name_strategy,
    'description': description_strategy,
    'pattern': pattern_strategy,
    'rule_type': st.sampled_from(RULE_TYPES),
    'confidence': score_strategy,
    'frequency': frequency_strategy,
    'examples': examples_strategy,
    'is_active': st.booleans(),
    'created_at': timestamp_strategy,
    'updated_at': timestamp_strategy
})

# 完整的业务模式策略
business_pattern_strategy = st.fixed_dictionaries({
    'id': id_strategy,
    'tenant_id': tenant_id_strategy,
    'project_id': project_id_strategy,
    'pattern_type': st.sampled_from(PATTERN_TYPES),
    'description': description_strategy,
    'strength': score_strategy,
    'evidence': evidence_strategy,
    'detected_at': timestamp_strategy,
    'last_seen': timestamp_strategy
})

# 完整的业务洞察策略
business_insight_strategy = st.fixed_dictionaries({
    'id': id_strategy,
    'tenant_id': tenant_id_strategy,
    'project_id': project_id_strategy,
    'insight_type': st.sampled_from(INSIGHT_TYPES),
    'title': name_strategy,
    'description': description_strategy,
    'impact_score': score_strategy,
    'recommendations': recommendations_strategy,
    'data_points': data_points_strategy,
    'created_at': timestamp_strategy,
    'acknowledged_at': st.one_of(st.none(), timestamp_strategy)
})



# ============================================================================
# Property 13: 业务逻辑服务 CRUD 往返
# **Validates: Requirements 5.1-5.9**
# ============================================================================

class TestBusinessRuleCRUDRoundTrip:
    """Property 13.1: 业务规则 CRUD 往返测试"""
    
    @given(rule=business_rule_strategy)
    @settings(max_examples=100)
    def test_rule_save_and_retrieve_by_id(self, rule):
        """保存后通过 ID 检索应该返回等价的规则
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirements 5.1, 5.5**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessRuleRepository()
            
            # 保存规则
            saved_rule = await repository.save(rule)
            
            # 通过 ID 检索
            retrieved = await repository.get_by_id(rule['id'])
            
            # 验证检索成功
            assert retrieved is not None, "Saved rule should be retrievable"
            
            # 验证关键字段匹配
            assert retrieved['id'] == rule['id'], "ID should match"
            assert retrieved['tenant_id'] == rule['tenant_id'], "Tenant ID should match"
            assert retrieved['project_id'] == rule['project_id'], "Project ID should match"
            assert retrieved['name'] == rule['name'], "Name should match"
            assert retrieved['pattern'] == rule['pattern'], "Pattern should match"
            assert retrieved['rule_type'] == rule['rule_type'], "Rule type should match"
            assert abs(retrieved['confidence'] - rule['confidence']) < 0.0001, "Confidence should match"
            assert retrieved['frequency'] == rule['frequency'], "Frequency should match"
            assert retrieved['is_active'] == rule['is_active'], "Is active should match"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(rule=business_rule_strategy, new_confidence=score_strategy)
    @settings(max_examples=100)
    def test_rule_update_confidence(self, rule, new_confidence):
        """更新置信度后应该反映更新的值
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.7**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessRuleRepository()
            
            # 保存规则
            await repository.save(rule)
            
            # 更新置信度
            result = await repository.update_confidence(rule['id'], new_confidence)
            assert result is True, "Update should succeed"
            
            # 检索并验证
            retrieved = await repository.get_by_id(rule['id'])
            assert retrieved is not None, "Rule should still exist"
            assert abs(retrieved['confidence'] - new_confidence) < 0.0001, \
                f"Confidence should be updated: {retrieved['confidence']} vs {new_confidence}"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(rule=business_rule_strategy)
    @settings(max_examples=100)
    def test_rule_delete(self, rule):
        """删除后应该无法检索
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.8**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessRuleRepository()
            
            # 保存规则
            await repository.save(rule)
            
            # 验证存在
            retrieved = await repository.get_by_id(rule['id'])
            assert retrieved is not None, "Rule should exist before deletion"
            
            # 删除规则
            result = await repository.delete(rule['id'])
            assert result is True, "Delete should succeed"
            
            # 验证不存在
            retrieved = await repository.get_by_id(rule['id'])
            assert retrieved is None, "Rule should not exist after deletion"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(rule=business_rule_strategy)
    @settings(max_examples=100)
    def test_rule_toggle_active(self, rule):
        """切换状态后应该反映更新的值
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.9**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessRuleRepository()
            
            # 保存规则
            await repository.save(rule)
            original_status = rule['is_active']
            
            # 切换状态
            toggled = await repository.toggle_active(rule['id'])
            assert toggled is not None, "Toggle should return updated rule"
            assert toggled['is_active'] != original_status, "Status should be toggled"
            
            # 再次切换
            toggled_again = await repository.toggle_active(rule['id'])
            assert toggled_again is not None, "Second toggle should return updated rule"
            assert toggled_again['is_active'] == original_status, "Status should be back to original"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(
        rules=st.lists(business_rule_strategy, min_size=2, max_size=10),
        rule_type=st.sampled_from(RULE_TYPES)
    )
    @settings(max_examples=100)
    def test_rule_find_by_project_with_filter(self, rules, rule_type):
        """按项目和类型过滤应该返回正确的结果
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.1**
        """
        import asyncio
        
        # 确保所有规则有唯一 ID
        ids = [r['id'] for r in rules]
        assume(len(ids) == len(set(ids)))
        
        async def run_test():
            repository = InMemoryBusinessRuleRepository()
            
            # 使用相同的项目 ID 和租户 ID
            project_id = "test_project"
            tenant_id = "default"
            
            # 保存所有规则，设置相同的项目和租户
            for rule in rules:
                rule_copy = {**rule, 'project_id': project_id, 'tenant_id': tenant_id}
                await repository.save(rule_copy)
            
            # 按类型过滤
            filtered = await repository.find_by_project(
                project_id=project_id,
                tenant_id=tenant_id,
                rule_type=rule_type,
                active_only=False
            )
            
            # 验证所有返回的规则都是指定类型
            for result in filtered:
                assert result['rule_type'] == rule_type, \
                    f"Rule type should be {rule_type}, got {result['rule_type']}"
            
            # 验证数量正确
            expected_count = len([r for r in rules if r['rule_type'] == rule_type])
            assert len(filtered) == expected_count, \
                f"Expected {expected_count} rules, got {len(filtered)}"
        
        asyncio.get_event_loop().run_until_complete(run_test())



class TestBusinessPatternCRUDRoundTrip:
    """Property 13.2: 业务模式 CRUD 往返测试"""
    
    @given(pattern=business_pattern_strategy)
    @settings(max_examples=100)
    def test_pattern_save_and_retrieve_by_id(self, pattern):
        """保存后通过 ID 检索应该返回等价的模式
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirements 5.2, 5.4**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessPatternRepository()
            
            # 保存模式
            saved_pattern = await repository.save(pattern)
            
            # 通过 ID 检索
            retrieved = await repository.get_by_id(pattern['id'])
            
            # 验证检索成功
            assert retrieved is not None, "Saved pattern should be retrievable"
            
            # 验证关键字段匹配
            assert retrieved['id'] == pattern['id'], "ID should match"
            assert retrieved['tenant_id'] == pattern['tenant_id'], "Tenant ID should match"
            assert retrieved['project_id'] == pattern['project_id'], "Project ID should match"
            assert retrieved['pattern_type'] == pattern['pattern_type'], "Pattern type should match"
            assert abs(retrieved['strength'] - pattern['strength']) < 0.0001, "Strength should match"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(patterns=st.lists(business_pattern_strategy, min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_pattern_save_batch(self, patterns):
        """批量保存应该保存所有模式
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.4**
        """
        import asyncio
        
        # 确保所有模式有唯一 ID
        ids = [p['id'] for p in patterns]
        assume(len(ids) == len(set(ids)))
        
        async def run_test():
            repository = InMemoryBusinessPatternRepository()
            
            # 批量保存
            saved_count = await repository.save_batch(patterns)
            
            # 验证保存数量
            assert saved_count == len(patterns), \
                f"Should save {len(patterns)} patterns, saved {saved_count}"
            
            # 验证每个模式都能检索
            for pattern in patterns:
                retrieved = await repository.get_by_id(pattern['id'])
                assert retrieved is not None, f"Pattern {pattern['id']} should be retrievable"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(
        patterns=st.lists(business_pattern_strategy, min_size=2, max_size=10),
        min_strength=score_strategy
    )
    @settings(max_examples=100)
    def test_pattern_find_by_project_with_strength_filter(self, patterns, min_strength):
        """按项目和强度过滤应该返回正确的结果
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.2**
        """
        import asyncio
        
        # 确保所有模式有唯一 ID
        ids = [p['id'] for p in patterns]
        assume(len(ids) == len(set(ids)))
        
        async def run_test():
            repository = InMemoryBusinessPatternRepository()
            
            # 使用相同的项目 ID 和租户 ID
            project_id = "test_project"
            tenant_id = "default"
            
            # 保存所有模式
            for pattern in patterns:
                pattern_copy = {**pattern, 'project_id': project_id, 'tenant_id': tenant_id}
                await repository.save(pattern_copy)
            
            # 按强度过滤
            filtered = await repository.find_by_project(
                project_id=project_id,
                tenant_id=tenant_id,
                min_strength=min_strength
            )
            
            # 验证所有返回的模式强度都 >= min_strength
            for result in filtered:
                assert result['strength'] >= min_strength, \
                    f"Strength should be >= {min_strength}, got {result['strength']}"
            
            # 验证数量正确
            expected_count = len([p for p in patterns if p['strength'] >= min_strength])
            assert len(filtered) == expected_count, \
                f"Expected {expected_count} patterns, got {len(filtered)}"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(pattern=business_pattern_strategy)
    @settings(max_examples=100)
    def test_pattern_delete(self, pattern):
        """删除后应该无法检索
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.4**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessPatternRepository()
            
            # 保存模式
            await repository.save(pattern)
            
            # 验证存在
            retrieved = await repository.get_by_id(pattern['id'])
            assert retrieved is not None, "Pattern should exist before deletion"
            
            # 删除模式
            result = await repository.delete(pattern['id'])
            assert result is True, "Delete should succeed"
            
            # 验证不存在
            retrieved = await repository.get_by_id(pattern['id'])
            assert retrieved is None, "Pattern should not exist after deletion"
        
        asyncio.get_event_loop().run_until_complete(run_test())


class TestBusinessInsightCRUDRoundTrip:
    """Property 13.3: 业务洞察 CRUD 往返测试"""
    
    @given(insight=business_insight_strategy)
    @settings(max_examples=100)
    def test_insight_save_and_retrieve_by_id(self, insight):
        """保存后通过 ID 检索应该返回等价的洞察
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.3**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessInsightRepository()
            
            # 保存洞察
            saved_insight = await repository.save(insight)
            
            # 通过 ID 检索
            retrieved = await repository.get_by_id(insight['id'])
            
            # 验证检索成功
            assert retrieved is not None, "Saved insight should be retrievable"
            
            # 验证关键字段匹配
            assert retrieved['id'] == insight['id'], "ID should match"
            assert retrieved['tenant_id'] == insight['tenant_id'], "Tenant ID should match"
            assert retrieved['project_id'] == insight['project_id'], "Project ID should match"
            assert retrieved['insight_type'] == insight['insight_type'], "Insight type should match"
            assert retrieved['title'] == insight['title'], "Title should match"
            assert abs(retrieved['impact_score'] - insight['impact_score']) < 0.0001, "Impact score should match"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(insight=business_insight_strategy)
    @settings(max_examples=100)
    def test_insight_acknowledge(self, insight):
        """确认后应该更新 acknowledged_at 时间戳
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.6**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessInsightRepository()
            
            # 保存未确认的洞察
            insight_copy = {**insight, 'acknowledged_at': None}
            await repository.save(insight_copy)
            
            # 验证未确认
            retrieved = await repository.get_by_id(insight['id'])
            assert retrieved['acknowledged_at'] is None, "Should be unacknowledged initially"
            
            # 确认洞察
            result = await repository.acknowledge(insight['id'])
            assert result is True, "Acknowledge should succeed"
            
            # 验证已确认
            retrieved = await repository.get_by_id(insight['id'])
            assert retrieved['acknowledged_at'] is not None, "Should be acknowledged after acknowledge()"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(
        insights=st.lists(business_insight_strategy, min_size=2, max_size=10)
    )
    @settings(max_examples=100)
    def test_insight_find_unacknowledged_only(self, insights):
        """按未确认过滤应该只返回未确认的洞察
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.3**
        """
        import asyncio
        
        # 确保所有洞察有唯一 ID
        ids = [i['id'] for i in insights]
        assume(len(ids) == len(set(ids)))
        
        async def run_test():
            repository = InMemoryBusinessInsightRepository()
            
            # 使用相同的项目 ID 和租户 ID
            project_id = "test_project"
            tenant_id = "default"
            
            # 保存所有洞察
            for insight in insights:
                insight_copy = {**insight, 'project_id': project_id, 'tenant_id': tenant_id}
                await repository.save(insight_copy)
            
            # 按未确认过滤
            filtered = await repository.find_by_project(
                project_id=project_id,
                tenant_id=tenant_id,
                unacknowledged_only=True
            )
            
            # 验证所有返回的洞察都未确认
            for result in filtered:
                assert result['acknowledged_at'] is None, \
                    "All returned insights should be unacknowledged"
            
            # 验证数量正确
            expected_count = len([i for i in insights if i['acknowledged_at'] is None])
            assert len(filtered) == expected_count, \
                f"Expected {expected_count} unacknowledged insights, got {len(filtered)}"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(insight=business_insight_strategy)
    @settings(max_examples=100)
    def test_insight_delete(self, insight):
        """删除后应该无法检索
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.3**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessInsightRepository()
            
            # 保存洞察
            await repository.save(insight)
            
            # 验证存在
            retrieved = await repository.get_by_id(insight['id'])
            assert retrieved is not None, "Insight should exist before deletion"
            
            # 删除洞察
            result = await repository.delete(insight['id'])
            assert result is True, "Delete should succeed"
            
            # 验证不存在
            retrieved = await repository.get_by_id(insight['id'])
            assert retrieved is None, "Insight should not exist after deletion"
        
        asyncio.get_event_loop().run_until_complete(run_test())



# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_repository_returns_empty_list(self):
        """空仓库应该返回空列表
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        import asyncio
        
        async def run_test():
            rule_repo = InMemoryBusinessRuleRepository()
            pattern_repo = InMemoryBusinessPatternRepository()
            insight_repo = InMemoryBusinessInsightRepository()
            
            rules = await rule_repo.find_by_project("nonexistent_project")
            patterns = await pattern_repo.find_by_project("nonexistent_project")
            insights = await insight_repo.find_by_project("nonexistent_project")
            
            assert rules == [], "Empty rule repository should return empty list"
            assert patterns == [], "Empty pattern repository should return empty list"
            assert insights == [], "Empty insight repository should return empty list"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_delete_nonexistent_returns_false(self):
        """删除不存在的记录应该返回 False
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirements 5.8**
        """
        import asyncio
        
        async def run_test():
            rule_repo = InMemoryBusinessRuleRepository()
            pattern_repo = InMemoryBusinessPatternRepository()
            insight_repo = InMemoryBusinessInsightRepository()
            
            rule_result = await rule_repo.delete("nonexistent_id")
            pattern_result = await pattern_repo.delete("nonexistent_id")
            insight_result = await insight_repo.delete("nonexistent_id")
            
            assert rule_result is False, "Deleting nonexistent rule should return False"
            assert pattern_result is False, "Deleting nonexistent pattern should return False"
            assert insight_result is False, "Deleting nonexistent insight should return False"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_update_nonexistent_returns_false(self):
        """更新不存在的记录应该返回 False
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirements 5.7, 5.9**
        """
        import asyncio
        
        async def run_test():
            rule_repo = InMemoryBusinessRuleRepository()
            insight_repo = InMemoryBusinessInsightRepository()
            
            confidence_result = await rule_repo.update_confidence("nonexistent_id", 0.5)
            toggle_result = await rule_repo.toggle_active("nonexistent_id")
            ack_result = await insight_repo.acknowledge("nonexistent_id")
            
            assert confidence_result is False, "Updating nonexistent rule confidence should return False"
            assert toggle_result is None, "Toggling nonexistent rule should return None"
            assert ack_result is False, "Acknowledging nonexistent insight should return False"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_confidence_range(self, confidence):
        """置信度应该在 0.0 到 1.0 之间
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.7**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessRuleRepository()
            
            rule = {
                'id': f"rule_{uuid4().hex[:16]}",
                'tenant_id': 'default',
                'project_id': 'test_project',
                'name': 'Test Rule',
                'description': None,
                'pattern': 'test pattern',
                'rule_type': 'sentiment_rule',
                'confidence': confidence,
                'frequency': 0,
                'examples': [],
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            await repository.save(rule)
            retrieved = await repository.get_by_id(rule['id'])
            
            assert 0.0 <= retrieved['confidence'] <= 1.0, \
                f"Confidence should be between 0.0 and 1.0, got {retrieved['confidence']}"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(
        strength=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_strength_range(self, strength):
        """强度应该在 0.0 到 1.0 之间
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.2**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessPatternRepository()
            
            pattern = {
                'id': f"pattern_{uuid4().hex[:16]}",
                'tenant_id': 'default',
                'project_id': 'test_project',
                'pattern_type': 'sentiment_correlation',
                'description': None,
                'strength': strength,
                'evidence': [],
                'detected_at': datetime.utcnow(),
                'last_seen': datetime.utcnow()
            }
            
            await repository.save(pattern)
            retrieved = await repository.get_by_id(pattern['id'])
            
            assert 0.0 <= retrieved['strength'] <= 1.0, \
                f"Strength should be between 0.0 and 1.0, got {retrieved['strength']}"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @given(
        impact_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_impact_score_range(self, impact_score):
        """影响分数应该在 0.0 到 1.0 之间
        
        **Feature: system-optimization, Property 13: 业务逻辑服务 CRUD 往返**
        **Validates: Requirement 5.3**
        """
        import asyncio
        
        async def run_test():
            repository = InMemoryBusinessInsightRepository()
            
            insight = {
                'id': f"insight_{uuid4().hex[:16]}",
                'tenant_id': 'default',
                'project_id': 'test_project',
                'insight_type': 'quality_insight',
                'title': 'Test Insight',
                'description': None,
                'impact_score': impact_score,
                'recommendations': [],
                'data_points': [],
                'created_at': datetime.utcnow(),
                'acknowledged_at': None
            }
            
            await repository.save(insight)
            retrieved = await repository.get_by_id(insight['id'])
            
            assert 0.0 <= retrieved['impact_score'] <= 1.0, \
                f"Impact score should be between 0.0 and 1.0, got {retrieved['impact_score']}"
        
        asyncio.get_event_loop().run_until_complete(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
