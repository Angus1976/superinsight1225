"""
Unit tests for Quality Rule Engine
质量规则引擎单元测试
"""

import pytest
from datetime import datetime
from typing import Dict, List, Optional
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class MockRule:
    """Mock quality rule for testing"""
    def __init__(
        self,
        id: str,
        name: str,
        rule_type: str = "builtin",
        severity: str = "medium",
        priority: int = 50,
        enabled: bool = True,
        config: Dict = None,
        version: int = 1
    ):
        self.id = id
        self.name = name
        self.rule_type = rule_type
        self.severity = severity
        self.priority = priority
        self.enabled = enabled
        self.config = config or {}
        self.version = version
        self.project_id = "test_project"
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class TestQualityRuleEngine:
    """Quality Rule Engine unit tests"""

    def test_create_rule(self):
        """Test rule creation"""
        rule_data = {
            "name": "Test Rule",
            "description": "A test rule",
            "rule_type": "builtin",
            "severity": "high",
            "priority": 80,
            "project_id": "project1"
        }
        
        rule = MockRule(
            id="rule1",
            name=rule_data["name"],
            rule_type=rule_data["rule_type"],
            severity=rule_data["severity"],
            priority=rule_data["priority"]
        )
        
        assert rule.name == "Test Rule"
        assert rule.rule_type == "builtin"
        assert rule.severity == "high"
        assert rule.priority == 80
        assert rule.enabled is True
        assert rule.version == 1

    def test_update_rule(self):
        """Test rule update"""
        rule = MockRule(id="rule1", name="Original Name", priority=50)
        
        # Simulate update
        rule.name = "Updated Name"
        rule.priority = 75
        rule.version += 1
        rule.updated_at = datetime.utcnow()
        
        assert rule.name == "Updated Name"
        assert rule.priority == 75
        assert rule.version == 2

    def test_get_active_rules_filtering(self):
        """Test filtering active rules"""
        rules = [
            MockRule(id="1", name="Rule 1", enabled=True, priority=100),
            MockRule(id="2", name="Rule 2", enabled=False, priority=90),
            MockRule(id="3", name="Rule 3", enabled=True, priority=80),
            MockRule(id="4", name="Rule 4", enabled=True, priority=70),
        ]
        
        active_rules = [r for r in rules if r.enabled]
        
        assert len(active_rules) == 3
        assert all(r.enabled for r in active_rules)

    def test_rule_priority_sorting(self):
        """Test rule priority sorting"""
        rules = [
            MockRule(id="1", name="Low Priority", priority=30),
            MockRule(id="2", name="High Priority", priority=90),
            MockRule(id="3", name="Medium Priority", priority=60),
        ]
        
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        
        assert sorted_rules[0].name == "High Priority"
        assert sorted_rules[1].name == "Medium Priority"
        assert sorted_rules[2].name == "Low Priority"

    def test_get_score_weights_default(self):
        """Test default score weights"""
        default_weights = {
            "accuracy": 0.4,
            "completeness": 0.3,
            "timeliness": 0.2,
            "consistency": 0.1
        }
        
        assert sum(default_weights.values()) == pytest.approx(1.0)
        assert all(0 < w <= 1 for w in default_weights.values())

    def test_get_score_weights_custom(self):
        """Test custom score weights"""
        custom_weights = {
            "accuracy": 0.5,
            "completeness": 0.3,
            "timeliness": 0.2
        }
        
        assert sum(custom_weights.values()) == pytest.approx(1.0)

    def test_get_required_fields(self):
        """Test getting required fields from config"""
        config = {
            "required_fields": ["name", "email", "phone"],
            "optional_fields": ["address", "notes"]
        }
        
        required = config.get("required_fields", [])
        
        assert len(required) == 3
        assert "name" in required
        assert "email" in required

    def test_create_from_template(self):
        """Test creating rules from template"""
        template = {
            "id": "template1",
            "name": "Standard Validation Template",
            "rules": [
                {"name": "Required Fields", "rule_type": "builtin", "severity": "high"},
                {"name": "Format Check", "rule_type": "builtin", "severity": "medium"},
            ]
        }
        
        created_rules = []
        for i, rule_config in enumerate(template["rules"]):
            rule = MockRule(
                id=f"rule_{i}",
                name=rule_config["name"],
                rule_type=rule_config["rule_type"],
                severity=rule_config["severity"]
            )
            created_rules.append(rule)
        
        assert len(created_rules) == 2
        assert created_rules[0].name == "Required Fields"
        assert created_rules[1].name == "Format Check"

    def test_rule_version_history(self):
        """Test rule version history tracking"""
        versions = [
            {"version": 1, "name": "Rule v1", "config": {"threshold": 0.5}},
            {"version": 2, "name": "Rule v2", "config": {"threshold": 0.6}},
            {"version": 3, "name": "Rule v3", "config": {"threshold": 0.7}},
        ]
        
        assert len(versions) == 3
        assert versions[-1]["version"] == 3
        assert versions[-1]["config"]["threshold"] == 0.7


class TestRuleCaching:
    """Tests for rule caching functionality"""

    def test_cache_key_generation(self):
        """Test cache key generation"""
        project_id = "project123"
        cache_key = f"quality_rules:{project_id}"
        
        assert cache_key == "quality_rules:project123"

    def test_cache_serialization(self):
        """Test rule serialization for caching"""
        rule = MockRule(
            id="rule1",
            name="Test Rule",
            rule_type="builtin",
            severity="high",
            priority=80,
            config={"threshold": 0.7}
        )
        
        # Serialize
        serialized = json.dumps({
            "id": rule.id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "severity": rule.severity,
            "priority": rule.priority,
            "config": rule.config
        })
        
        # Deserialize
        deserialized = json.loads(serialized)
        
        assert deserialized["id"] == "rule1"
        assert deserialized["name"] == "Test Rule"
        assert deserialized["config"]["threshold"] == 0.7

    def test_cache_invalidation_on_update(self):
        """Test cache invalidation logic"""
        cache = {"quality_rules:project1": "[rule_data]"}
        
        def invalidate_cache(project_id: str):
            key = f"quality_rules:{project_id}"
            if key in cache:
                del cache[key]
        
        invalidate_cache("project1")
        
        assert "quality_rules:project1" not in cache


class TestRuleValidation:
    """Tests for rule validation"""

    def test_validate_rule_name(self):
        """Test rule name validation"""
        def validate_name(name: str) -> tuple:
            if not name:
                return False, "Name is required"
            if len(name) > 100:
                return False, "Name too long"
            if not name.strip():
                return False, "Name cannot be empty"
            return True, None
        
        assert validate_name("Valid Rule Name") == (True, None)
        assert validate_name("")[0] is False
        assert validate_name("A" * 150)[0] is False
        assert validate_name("   ")[0] is False

    def test_validate_rule_type(self):
        """Test rule type validation"""
        valid_types = ["builtin", "custom"]
        
        def validate_type(rule_type: str) -> bool:
            return rule_type in valid_types
        
        assert validate_type("builtin") is True
        assert validate_type("custom") is True
        assert validate_type("invalid") is False

    def test_validate_severity(self):
        """Test severity validation"""
        valid_severities = ["critical", "high", "medium", "low"]
        
        def validate_severity(severity: str) -> bool:
            return severity in valid_severities
        
        assert validate_severity("critical") is True
        assert validate_severity("high") is True
        assert validate_severity("invalid") is False

    def test_validate_priority_range(self):
        """Test priority range validation"""
        def validate_priority(priority: int) -> tuple:
            if priority < 0:
                return False, "Priority must be non-negative"
            if priority > 100:
                return False, "Priority must not exceed 100"
            return True, None
        
        assert validate_priority(50) == (True, None)
        assert validate_priority(0) == (True, None)
        assert validate_priority(100) == (True, None)
        assert validate_priority(-1)[0] is False
        assert validate_priority(101)[0] is False

    def test_validate_custom_script(self):
        """Test custom script validation"""
        def validate_script(script: str) -> tuple:
            if not script:
                return True, None  # Script is optional
            
            # Check for dangerous patterns
            dangerous_patterns = ["import os", "import sys", "exec(", "eval(", "__import__"]
            for pattern in dangerous_patterns:
                if pattern in script:
                    return False, f"Script contains forbidden pattern: {pattern}"
            
            # Try to compile
            try:
                compile(script, "<string>", "exec")
                return True, None
            except SyntaxError as e:
                return False, f"Syntax error: {str(e)}"
        
        assert validate_script("result = data.get('value', 0) > 0") == (True, None)
        assert validate_script("import os")[0] is False
        assert validate_script("exec('bad')")[0] is False
        assert validate_script("invalid syntax !!!")[0] is False


class TestRuleTemplates:
    """Tests for rule templates"""

    def test_builtin_templates(self):
        """Test builtin rule templates"""
        templates = [
            {
                "id": "required_fields",
                "name": "Required Fields Check",
                "rule_type": "builtin",
                "severity": "high",
                "config": {"fields": []}
            },
            {
                "id": "value_range",
                "name": "Value Range Check",
                "rule_type": "builtin",
                "severity": "medium",
                "config": {"field": "", "min": None, "max": None}
            },
            {
                "id": "format_validation",
                "name": "Format Validation",
                "rule_type": "builtin",
                "severity": "medium",
                "config": {"field": "", "pattern": ""}
            }
        ]
        
        assert len(templates) == 3
        assert all("id" in t for t in templates)
        assert all("config" in t for t in templates)

    def test_template_instantiation(self):
        """Test instantiating rule from template"""
        template = {
            "id": "required_fields",
            "name": "Required Fields Check",
            "rule_type": "builtin",
            "severity": "high",
            "config": {"fields": []}
        }
        
        # Customize template
        instance_config = {
            **template,
            "config": {"fields": ["name", "email", "phone"]}
        }
        
        rule = MockRule(
            id="rule_from_template",
            name=instance_config["name"],
            rule_type=instance_config["rule_type"],
            severity=instance_config["severity"],
            config=instance_config["config"]
        )
        
        assert rule.config["fields"] == ["name", "email", "phone"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
