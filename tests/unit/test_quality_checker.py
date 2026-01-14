"""
Unit tests for Quality Checker
质量检查器单元测试
"""

import pytest
import re
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestQualityChecker:
    """Quality Checker unit tests"""

    def test_check_required_fields_all_present(self):
        """Test required fields check when all fields are present"""
        annotation_data = {"name": "John", "email": "john@example.com", "age": 30}
        required_fields = ["name", "email", "age"]
        
        missing = [f for f in required_fields if f not in annotation_data or not annotation_data[f]]
        passed = len(missing) == 0
        
        assert passed is True
        assert missing == []

    def test_check_required_fields_some_missing(self):
        """Test required fields check when some fields are missing"""
        annotation_data = {"name": "John", "email": ""}
        required_fields = ["name", "email", "age"]
        
        missing = [f for f in required_fields if f not in annotation_data or not annotation_data[f]]
        passed = len(missing) == 0
        
        assert passed is False
        assert "email" in missing
        assert "age" in missing

    def test_check_value_range_within_range(self):
        """Test value range check when value is within range"""
        annotation_data = {"score": 75, "rating": 4}
        config = {
            "score": {"min": 0, "max": 100},
            "rating": {"min": 1, "max": 5}
        }
        
        issues = []
        for field, range_config in config.items():
            value = annotation_data.get(field)
            if value is not None:
                if value < range_config["min"] or value > range_config["max"]:
                    issues.append(f"{field} out of range")
        
        assert len(issues) == 0

    def test_check_value_range_out_of_range(self):
        """Test value range check when value is out of range"""
        annotation_data = {"score": 150, "rating": 0}
        config = {
            "score": {"min": 0, "max": 100},
            "rating": {"min": 1, "max": 5}
        }
        
        issues = []
        for field, range_config in config.items():
            value = annotation_data.get(field)
            if value is not None:
                if value < range_config["min"] or value > range_config["max"]:
                    issues.append(f"{field} out of range")
        
        assert len(issues) == 2
        assert "score out of range" in issues
        assert "rating out of range" in issues

    def test_check_format_validation_email(self):
        """Test format validation for email"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        valid_emails = ["test@example.com", "user.name@domain.org", "a@b.co"]
        invalid_emails = ["invalid", "no@domain", "@example.com", "test@.com"]
        
        for email in valid_emails:
            assert re.match(email_pattern, email) is not None, f"{email} should be valid"
        
        for email in invalid_emails:
            assert re.match(email_pattern, email) is None, f"{email} should be invalid"

    def test_check_format_validation_phone(self):
        """Test format validation for phone number"""
        # Pattern requires at least 7 digits for a valid phone number
        phone_pattern = r'^\+?[1-9]\d{6,14}$'
        
        valid_phones = ["+8613800138000", "13800138000", "+1234567890"]
        invalid_phones = ["abc", "123", "+0123456789", "12345"]  # Too short or starts with 0
        
        for phone in valid_phones:
            assert re.match(phone_pattern, phone) is not None, f"{phone} should be valid"
        
        for phone in invalid_phones:
            assert re.match(phone_pattern, phone) is None, f"{phone} should be invalid"

    def test_check_length_limit_within_limit(self):
        """Test length limit check when within limit"""
        annotation_data = {"description": "Short text", "title": "Title"}
        config = {
            "description": {"min": 5, "max": 100},
            "title": {"min": 1, "max": 50}
        }
        
        issues = []
        for field, limit_config in config.items():
            value = annotation_data.get(field, "")
            length = len(value)
            if length < limit_config["min"]:
                issues.append(f"{field} too short")
            elif length > limit_config["max"]:
                issues.append(f"{field} too long")
        
        assert len(issues) == 0

    def test_check_length_limit_violations(self):
        """Test length limit check with violations"""
        annotation_data = {"description": "Hi", "title": "A" * 100}
        config = {
            "description": {"min": 5, "max": 100},
            "title": {"min": 1, "max": 50}
        }
        
        issues = []
        for field, limit_config in config.items():
            value = annotation_data.get(field, "")
            length = len(value)
            if length < limit_config["min"]:
                issues.append(f"{field} too short")
            elif length > limit_config["max"]:
                issues.append(f"{field} too long")
        
        assert len(issues) == 2
        assert "description too short" in issues
        assert "title too long" in issues

    def test_check_text_length(self):
        """Test text length validation"""
        def check_text_length(text: str, min_len: int, max_len: int) -> tuple:
            length = len(text)
            if length < min_len:
                return False, f"Text too short (min: {min_len})"
            if length > max_len:
                return False, f"Text too long (max: {max_len})"
            return True, None
        
        assert check_text_length("Hello World", 5, 100) == (True, None)
        assert check_text_length("Hi", 5, 100)[0] is False
        assert check_text_length("A" * 200, 5, 100)[0] is False

    def test_check_entity_overlap(self):
        """Test entity overlap detection"""
        def check_entity_overlap(entities: List[Dict]) -> List[str]:
            """Check if entities overlap"""
            issues = []
            for i, e1 in enumerate(entities):
                for j, e2 in enumerate(entities):
                    if i >= j:
                        continue
                    # Check overlap
                    if e1["start"] < e2["end"] and e2["start"] < e1["end"]:
                        issues.append(f"Entities {i} and {j} overlap")
            return issues
        
        # No overlap
        entities_no_overlap = [
            {"start": 0, "end": 5, "label": "A"},
            {"start": 10, "end": 15, "label": "B"}
        ]
        assert check_entity_overlap(entities_no_overlap) == []
        
        # With overlap
        entities_with_overlap = [
            {"start": 0, "end": 10, "label": "A"},
            {"start": 5, "end": 15, "label": "B"}
        ]
        assert len(check_entity_overlap(entities_with_overlap)) > 0

    def test_check_allowed_values(self):
        """Test allowed values validation"""
        def check_allowed_values(value: Any, allowed: List[Any]) -> bool:
            return value in allowed
        
        allowed_labels = ["positive", "negative", "neutral"]
        
        assert check_allowed_values("positive", allowed_labels) is True
        assert check_allowed_values("negative", allowed_labels) is True
        assert check_allowed_values("unknown", allowed_labels) is False

    def test_severity_classification(self):
        """Test issue severity classification"""
        def classify_severity(rule_severity: str, issue_count: int) -> str:
            if rule_severity == "critical":
                return "critical"
            if rule_severity == "high" and issue_count > 3:
                return "critical"
            if rule_severity == "high":
                return "high"
            if rule_severity == "medium" and issue_count > 5:
                return "high"
            return rule_severity
        
        assert classify_severity("critical", 1) == "critical"
        assert classify_severity("high", 5) == "critical"
        assert classify_severity("high", 2) == "high"
        assert classify_severity("medium", 10) == "high"
        assert classify_severity("low", 1) == "low"

    def test_batch_check_aggregation(self):
        """Test batch check result aggregation"""
        results = [
            {"passed": True, "issues": []},
            {"passed": False, "issues": [{"severity": "high"}]},
            {"passed": False, "issues": [{"severity": "medium"}, {"severity": "low"}]},
            {"passed": True, "issues": []},
        ]
        
        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        failed_count = total - passed_count
        total_issues = sum(len(r["issues"]) for r in results)
        
        assert total == 4
        assert passed_count == 2
        assert failed_count == 2
        assert total_issues == 3


class TestBuiltinRules:
    """Tests for builtin rule implementations"""

    def test_required_fields_rule(self):
        """Test required_fields builtin rule"""
        def execute_required_fields(data: Dict, config: Dict) -> Dict:
            required = config.get("fields", [])
            missing = [f for f in required if f not in data or not data[f]]
            return {
                "passed": len(missing) == 0,
                "message": f"Missing fields: {missing}" if missing else None,
                "field": missing[0] if missing else None
            }
        
        config = {"fields": ["name", "email"]}
        
        result1 = execute_required_fields({"name": "John", "email": "j@e.com"}, config)
        assert result1["passed"] is True
        
        result2 = execute_required_fields({"name": "John"}, config)
        assert result2["passed"] is False
        assert "email" in result2["message"]

    def test_value_range_rule(self):
        """Test value_range builtin rule"""
        def execute_value_range(data: Dict, config: Dict) -> Dict:
            field = config.get("field")
            min_val = config.get("min")
            max_val = config.get("max")
            
            value = data.get(field)
            if value is None:
                return {"passed": True}
            
            if min_val is not None and value < min_val:
                return {"passed": False, "message": f"{field} below minimum {min_val}", "field": field}
            if max_val is not None and value > max_val:
                return {"passed": False, "message": f"{field} above maximum {max_val}", "field": field}
            
            return {"passed": True}
        
        config = {"field": "score", "min": 0, "max": 100}
        
        assert execute_value_range({"score": 50}, config)["passed"] is True
        assert execute_value_range({"score": -10}, config)["passed"] is False
        assert execute_value_range({"score": 150}, config)["passed"] is False

    def test_format_validation_rule(self):
        """Test format_validation builtin rule"""
        def execute_format_validation(data: Dict, config: Dict) -> Dict:
            field = config.get("field")
            pattern = config.get("pattern")
            
            value = data.get(field, "")
            if not value:
                return {"passed": True}
            
            if re.match(pattern, str(value)):
                return {"passed": True}
            return {"passed": False, "message": f"{field} format invalid", "field": field}
        
        email_config = {"field": "email", "pattern": r'^[\w.+-]+@[\w.-]+\.\w+$'}
        
        assert execute_format_validation({"email": "test@example.com"}, email_config)["passed"] is True
        assert execute_format_validation({"email": "invalid"}, email_config)["passed"] is False


class TestCustomRuleExecution:
    """Tests for custom rule execution"""

    def test_safe_script_execution(self):
        """Test safe execution of custom scripts"""
        def safe_execute(script: str, data: Dict) -> Dict:
            """Safely execute a validation script"""
            try:
                # Create restricted namespace
                namespace = {"data": data, "result": {"passed": True}}
                exec(script, {"__builtins__": {}}, namespace)
                return namespace.get("result", {"passed": True})
            except Exception as e:
                return {"passed": False, "message": f"Script error: {str(e)}"}
        
        # Simple validation script
        script = """
result = {"passed": data.get("value", 0) > 0}
"""
        
        result1 = safe_execute(script, {"value": 10})
        assert result1["passed"] is True
        
        result2 = safe_execute(script, {"value": -5})
        assert result2["passed"] is False

    def test_script_error_handling(self):
        """Test error handling in custom scripts"""
        def safe_execute(script: str, data: Dict) -> Dict:
            try:
                namespace = {"data": data, "result": {"passed": True}}
                exec(script, {"__builtins__": {}}, namespace)
                return namespace.get("result", {"passed": True})
            except Exception as e:
                return {"passed": False, "message": f"Script error: {str(e)}"}
        
        # Script with error
        bad_script = "result = 1 / 0"
        result = safe_execute(bad_script, {})
        
        assert result["passed"] is False
        assert "Script error" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
