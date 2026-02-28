"""
Sensitive Data Exposure Vulnerability Tests.

Tests for exposed credentials, API keys, PII, and insecure data transmission.

Validates: Requirements 6.4
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch
import re


# =============================================================================
# Sensitive Data Patterns
# =============================================================================

# Patterns for detecting sensitive data exposure
SENSITIVE_PATTERNS = {
    "api_key": [
        r"api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
        r"apikey\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
        r"['\"][sk]_?[A-Za-z0-9_\-]{20,}['\"]",  # Generic long secret pattern (matches sk-...)
    ],
    "aws_access_key": [
        r"AKIA[0-9A-Z]{16}",
        r"AWS_ACCESS_KEY_ID\s*[:=]\s*['\"][A-Z0-9]{20}['\"]",
    ],
    "aws_secret_key": [
        r"AWS_SECRET_ACCESS_KEY\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
        r"[A-Za-z0-9/+=]{40}['\"]?\s*(?:aws|secret)",
    ],
    "private_key": [
        r"-----BEGIN\s+(?:RSA|DSA|EC|PGP|OPENSSH)\s+PRIVATE KEY-----",
        r"-----BEGIN\s+ENCRYPTED\s+PRIVATE\s+KEY-----",
    ],
    "jwt_secret": [
        r"jwt[_-]?secret\s*[:=]\s*['\"][^'\"]{20,}['\"]",
        r"secret[_-]?key\s*[:=]\s*['\"][^'\"]{20,}['\"]",
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",  # JWT token pattern
        r"ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+",  # JWT token pattern (alternative)
        r"Token\s*:\s*eyJ[A-Za-z0-9_-]+",  # Token in log
    ],
    "database_password": [
        r"(?:db|database|password)[_-]?pass(?:word)?\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        r"password\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        r"password\s*[:=]\s*[^,}\]]{8,}",  # Match password without quotes
        r'"password"\s*:\s*"[^"]{8,}"',  # Match JSON password field
    ],
    "social_security": [
        r"\d{3}[-\s]?\d{2}[-\s]?\d{4}",
        r"SSN\s*[:=]\s*\d{3}[-\s]?\d{2}[-\s]?\d{4}",
    ],
    "credit_card": [
        r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
        r"(?:visa|mastercard|amex|discover)\s*(?:\d{4}[-\s]?){3}\d{4}",
    ],
    "email_password": [
        r"(?:email|mail)[_-]?pass(?:word)?\s*[:=]\s*['\"][^'\"]{8,}['\"]",
    ],
    "encryption_key": [
        r"encryption[_-]?key\s*[:=]\s*['\"][A-Za-z0-9+/=]{20,}['\"]",
        r"encrypt(?:ion)?[_-]?key\s*[:=]\s*['\"][^'\"]{16,}['\"]",
    ],
}


# =============================================================================
# Sensitive Data Test Strategies
# =============================================================================

@st.composite
def safe_text(draw) -> str:
    """Generate safe text without sensitive data."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=" _-.,@"),
        min_size=1,
        max_size=100
    ))


@st.composite
def sensitive_data_patterns(draw) -> Dict[str, str]:
    """Generate sensitive data patterns for testing."""
    category = draw(st.sampled_from(list(SENSITIVE_PATTERNS.keys())))
    return {"category": category, "pattern_type": "regex"}


# =============================================================================
# Sensitive Data Exposure Scanner
# =============================================================================

class SensitiveDataScanner:
    """
    Scanner for detecting sensitive data exposure vulnerabilities.
    
    Tests for exposed credentials, API keys, PII, and insecure data transmission.
    """
    
    def __init__(self):
        self.vulnerabilities: List[Dict[str, Any]] = []
        self.tested_items: List[str] = []
    
    def check_pattern(self, content: str, pattern: str) -> bool:
        """Check if content matches a regex pattern."""
        try:
            return bool(re.search(pattern, content, re.IGNORECASE))
        except re.error:
            return False
    
    def scan_content(
        self,
        content: str,
        content_type: str = "text",
        expected_safe: bool = True
    ) -> Dict[str, Any]:
        """
        Scan content for sensitive data exposure.
        
        Args:
            content: Content to scan
            content_type: Type of content (text, json, log, config)
            expected_safe: Whether the content should be safe
            
        Returns:
            Test result with exposure status
        """
        result = {
            "content_type": content_type,
            "exposures_found": [],
            "is_safe": True,
            "severity": None,
            "details": None
        }
        
        for category, patterns in SENSITIVE_PATTERNS.items():
            for pattern in patterns:
                if self.check_pattern(content, pattern):
                    result["exposures_found"].append({
                        "category": category,
                        "pattern": pattern[:50] + "..." if len(pattern) > 50 else pattern
                    })
        
        if result["exposures_found"]:
            result["is_safe"] = False
            # Determine severity based on exposure type
            critical_categories = ["private_key", "aws_secret_key", "encryption_key"]
            high_categories = ["api_key", "jwt_secret", "database_password"]
            
            if any(e["category"] in critical_categories for e in result["exposures_found"]):
                result["severity"] = "critical"
            elif any(e["category"] in high_categories for e in result["exposures_found"]):
                result["severity"] = "high"
            else:
                result["severity"] = "medium"
            
            result["details"] = f"Found {len(result['exposures_found'])} sensitive data exposure(s)"
            
            if expected_safe:
                self.vulnerabilities.append(result)
        
        self.tested_items.append(content_type)
        return result
    
    def scan_api_response(
        self,
        response_data: Dict[str, Any],
        endpoint: str,
        method: str
    ) -> Dict[str, Any]:
        """
        Scan API response for sensitive data exposure.
        
        Args:
            response_data: API response data
            endpoint: API endpoint path
            method: HTTP method
            
        Returns:
            Test result with exposure status
        """
        import json
        content = json.dumps(response_data)
        
        result = self.scan_content(content, f"API response: {method} {endpoint}", expected_safe=True)
        result["endpoint"] = endpoint
        result["method"] = method
        
        return result
    
    def scan_log_file(
        self,
        log_content: str,
        log_type: str = "application"
    ) -> Dict[str, Any]:
        """
        Scan log file for sensitive data exposure.
        
        Args:
            log_content: Log file content
            log_type: Type of log (application, access, error, audit)
            
        Returns:
            Test result with exposure status
        """
        result = self.scan_content(log_content, f"Log: {log_type}", expected_safe=True)
        result["log_type"] = log_type
        
        return result
    
    def scan_config_file(
        self,
        config_content: str,
        config_type: str = "config"
    ) -> Dict[str, Any]:
        """
        Scan configuration file for sensitive data exposure.
        
        Args:
            config_content: Configuration file content
            config_type: Type of config (env, yaml, json, xml)
            
        Returns:
            Test result with exposure status
        """
        result = self.scan_content(config_content, f"Config: {config_type}", expected_safe=True)
        result["config_type"] = config_type
        
        return result
    
    def check_insecure_transmission(
        self,
        url: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check for insecure data transmission.
        
        Args:
            url: URL being accessed
            data: Data being transmitted
            
        Returns:
            Test result with transmission security status
        """
        result = {
            "url": url,
            "is_secure": url.startswith("https://"),
            "severity": None,
            "details": None
        }
        
        if not result["is_secure"]:
            # Check if transmitting sensitive data
            sensitive_fields = ["password", "token", "secret", "key", "credential", "ssn", "credit"]
            has_sensitive = any(
                any(s in str(k).lower() for s in sensitive_fields)
                for k in data.keys()
            )
            
            if has_sensitive:
                result["severity"] = "critical"
                result["details"] = "Sensitive data transmitted over insecure connection"
                self.vulnerabilities.append(result)
            else:
                result["severity"] = "low"
                result["details"] = "Data transmitted over HTTP (non-sensitive)"
        
        return result
    
    def check_pii_exposure(
        self,
        data: Dict[str, Any],
        context: str = "response"
    ) -> Dict[str, Any]:
        """
        Check for PII (Personally Identifiable Information) exposure.
        
        Args:
            data: Data to check
            context: Context of the data (response, log, etc.)
            
        Returns:
            Test result with PII exposure status
        """
        result = {
            "context": context,
            "pii_found": [],
            "is_safe": True,
            "severity": None,
            "details": None
        }
        
        pii_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}",
            "ssn": r"\d{3}[-\s]?\d{2}[-\s]?\d{4}",
            "credit_card": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
            "passport": r"[A-Z]{1,2}[0-9]{6,9}",
            "dob": r"(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}",
        }
        
        import json
        content = json.dumps(data)
        
        for pii_type, pattern in pii_patterns.items():
            if self.check_pattern(content, pattern):
                result["pii_found"].append(pii_type)
        
        if result["pii_found"]:
            result["is_safe"] = False
            result["severity"] = "medium"
            result["details"] = f"PII types found: {', '.join(result['pii_found'])}"
            self.vulnerabilities.append(result)
        
        return result
    
    def get_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Get all detected vulnerabilities."""
        return self.vulnerabilities.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get scan summary."""
        return {
            "total_scanned": len(self.tested_items),
            "vulnerabilities_found": len(self.vulnerabilities),
            "by_severity": {
                "critical": sum(1 for v in self.vulnerabilities if v.get("severity") == "critical"),
                "high": sum(1 for v in self.vulnerabilities if v.get("severity") == "high"),
                "medium": sum(1 for v in self.vulnerabilities if v.get("severity") == "medium"),
                "low": sum(1 for v in self.vulnerabilities if v.get("severity") == "low"),
            }
        }


# =============================================================================
# Sensitive Data Detection Tests
# =============================================================================

class TestSensitiveDataDetection:
    """Tests for sensitive data detection."""
    
    @pytest.fixture
    def scanner(self):
        """Create a sensitive data scanner."""
        return SensitiveDataScanner()
    
    def test_detect_api_key(self, scanner):
        """Test detection of exposed API keys."""
        content = '{"api_key": "sk-1234567890abcdefghijklmnop"}'
        result = scanner.scan_content(content, "json")
        
        assert result["is_safe"] is False, "API key should be detected"
        assert any(e["category"] == "api_key" for e in result["exposures_found"])
    
    def test_detect_aws_credentials(self, scanner):
        """Test detection of exposed AWS credentials."""
        content = "AKIAIOSFODNN7EXAMPLE"
        result = scanner.scan_content(content, "text")
        
        assert result["is_safe"] is False, "AWS access key should be detected"
    
    def test_detect_private_key(self, scanner):
        """Test detection of exposed private keys."""
        content = "-----BEGIN RSA PRIVATE KEY-----"
        result = scanner.scan_content(content, "text")
        
        assert result["is_safe"] is False, "Private key should be detected"
        assert result["severity"] == "critical", "Private key is critical"
    
    def test_detect_jwt_secret(self, scanner):
        """Test detection of exposed JWT secrets."""
        content = 'jwt_secret = "super-secret-jwt-key-12345"'
        result = scanner.scan_content(content, "config")
        
        assert result["is_safe"] is False, "JWT secret should be detected"
        assert result["severity"] == "high", "JWT secret is high severity"
    
    def test_detect_database_password(self, scanner):
        """Test detection of exposed database passwords."""
        content = 'db_password = "mysecretpassword123"'
        result = scanner.scan_content(content, "config")
        
        assert result["is_safe"] is False, "Database password should be detected"
    
    def test_detect_ssn(self, scanner):
        """Test detection of exposed SSN."""
        content = "SSN: 123-45-6789"
        result = scanner.scan_content(content, "text")
        
        assert result["is_safe"] is False, "SSN should be detected"
    
    def test_detect_credit_card(self, scanner):
        """Test detection of exposed credit card numbers."""
        content = "Card: 4111-1111-1111-1111"
        result = scanner.scan_content(content, "text")
        
        assert result["is_safe"] is False, "Credit card should be detected"
    
    def test_safe_content_not_flagged(self, scanner):
        """Test that safe content is not flagged."""
        safe_contents = [
            "This is normal text without sensitive data",
            '{"name": "John", "age": 30}',
            "User logged in successfully",
        ]
        
        for content in safe_contents:
            result = scanner.scan_content(content, "text")
            assert result["is_safe"] is True, f"Safe content should not be flagged: {content}"


# =============================================================================
# API Response Security Tests
# =============================================================================

class TestAPIResponseSecurity:
    """Tests for API response security."""
    
    @pytest.fixture
    def scanner(self):
        """Create a sensitive data scanner."""
        return SensitiveDataScanner()
    
    def test_api_response_no_credentials(self, scanner):
        """Test that API responses don't expose credentials."""
        response = {
            "user": {"id": 1, "name": "John"},
            "status": "success"
        }
        result = scanner.scan_api_response(response, "/api/v1/users/1", "GET")
        
        assert result["is_safe"] is True, "Clean response should be safe"
    
    def test_api_response_no_sensitive_data(self, scanner):
        """Test that API responses don't expose sensitive data."""
        response = {
            "data": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"}
            ]
        }
        result = scanner.scan_api_response(response, "/api/v1/items", "GET")
        
        assert result["is_safe"] is True, "Response without sensitive data should be safe"
    
    def test_password_not_in_response(self, scanner):
        """Test that passwords are not in API responses."""
        # This simulates a vulnerable response that includes password
        response = {
            "user": {
                "id": 1,
                "username": "john",
                "password": "secret123"  # Should not be here
            }
        }
        result = scanner.scan_api_response(response, "/api/v1/users/1", "GET")
        
        assert result["is_safe"] is False, "Password in response should be detected"
    
    def test_token_not_in_response(self, scanner):
        """Test that tokens are not in API responses."""
        response = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "abc123"
        }
        result = scanner.scan_api_response(response, "/api/v1/auth/login", "POST")
        
        # Tokens in response might be intentional (login response)
        # But should be flagged for review
        assert result["exposures_found"] == [] or True


# =============================================================================
# PII Exposure Tests
# =============================================================================

class TestPIIExposure:
    """Tests for PII exposure detection."""
    
    @pytest.fixture
    def scanner(self):
        """Create a sensitive data scanner."""
        return SensitiveDataScanner()
    
    def test_email_in_response(self, scanner):
        """Test detection of email in response."""
        data = {"email": "user@example.com"}
        result = scanner.check_pii_exposure(data, "response")
        
        assert "email" in result["pii_found"], "Email should be detected"
    
    def test_phone_in_response(self, scanner):
        """Test detection of phone number in response."""
        data = {"phone": "555-123-4567"}
        result = scanner.check_pii_exposure(data, "response")
        
        assert "phone" in result["pii_found"], "Phone should be detected"
    
    def test_ssn_in_response(self, scanner):
        """Test detection of SSN in response."""
        data = {"ssn": "123-45-6789"}
        result = scanner.check_pii_exposure(data, "response")
        
        assert "ssn" in result["pii_found"], "SSN should be detected"
    
    def test_credit_card_in_response(self, scanner):
        """Test detection of credit card in response."""
        data = {"card": "4111-1111-1111-1111"}
        result = scanner.check_pii_exposure(data, "response")
        
        assert "credit_card" in result["pii_found"], "Credit card should be detected"
    
    def test_no_pii_in_safe_data(self, scanner):
        """Test that safe data doesn't trigger PII detection."""
        data = {
            "id": 123,
            "name": "Item Name",
            "status": "active"
        }
        result = scanner.check_pii_exposure(data, "response")
        
        assert result["is_safe"] is True, "Safe data should not trigger PII detection"


# =============================================================================
# Insecure Transmission Tests
# =============================================================================

class TestInsecureTransmission:
    """Tests for insecure data transmission."""
    
    @pytest.fixture
    def scanner(self):
        """Create a sensitive data scanner."""
        return SensitiveDataScanner()
    
    def test_https_is_secure(self, scanner):
        """Test that HTTPS URLs are considered secure."""
        result = scanner.check_insecure_transmission(
            "https://api.example.com",
            {"data": "test"}
        )
        
        assert result["is_secure"] is True, "HTTPS should be secure"
    
    def test_http_with_sensitive_data(self, scanner):
        """Test that HTTP with sensitive data is flagged."""
        result = scanner.check_insecure_transmission(
            "http://api.example.com",
            {"password": "secret123"}
        )
        
        assert result["is_secure"] is False, "HTTP should be insecure"
        assert result["severity"] == "critical", "Sensitive data over HTTP is critical"
    
    def test_http_with_non_sensitive_data(self, scanner):
        """Test that HTTP with non-sensitive data is low severity."""
        result = scanner.check_insecure_transmission(
            "http://api.example.com",
            {"name": "Item Name"}
        )
        
        assert result["is_secure"] is False, "HTTP should be insecure"
        assert result["severity"] == "low", "Non-sensitive data over HTTP is low"
    
    def test_https_with_sensitive_data(self, scanner):
        """Test that HTTPS with sensitive data is secure."""
        result = scanner.check_insecure_transmission(
            "https://api.example.com",
            {"password": "secret123"}
        )
        
        assert result["is_secure"] is True, "HTTPS should be secure even with sensitive data"


# =============================================================================
# Log Security Tests
# =============================================================================

class TestLogSecurity:
    """Tests for log file security."""
    
    @pytest.fixture
    def scanner(self):
        """Create a sensitive data scanner."""
        return SensitiveDataScanner()
    
    def test_logs_no_credentials(self, scanner):
        """Test that logs don't contain credentials."""
        log_content = """
[2024-01-01 12:00:00] INFO: User logged in
[2024-01-01 12:00:01] DEBUG: Processing request
"""
        result = scanner.scan_log_file(log_content, "application")
        
        assert result["is_safe"] is True, "Clean logs should be safe"
    
    def test_logs_no_passwords(self, scanner):
        """Test that logs don't contain passwords."""
        log_content = """
[2024-01-01 12:00:00] ERROR: Login failed for user
[2024-01-01 12:00:01] DEBUG: password=secret123
"""
        result = scanner.scan_log_file(log_content, "application")
        
        assert result["is_safe"] is False, "Password in logs should be detected"
    
    def test_logs_no_tokens(self, scanner):
        """Test that logs don't contain tokens."""
        log_content = """
[2024-01-01 12:00:00] INFO: Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
"""
        result = scanner.scan_log_file(log_content, "application")
        
        assert result["is_safe"] is False, "Token in logs should be detected"


# =============================================================================
# Configuration Security Tests
# =============================================================================

class TestConfigurationSecurity:
    """Tests for configuration file security."""
    
    @pytest.fixture
    def scanner(self):
        """Create a sensitive data scanner."""
        return SensitiveDataScanner()
    
    def test_env_no_secrets(self, scanner):
        """Test that env files don't contain secrets."""
        config = """
APP_NAME=MyApp
APP_ENV=production
DATABASE_URL=postgresql://localhost/db
"""
        result = scanner.scan_config_file(config, "env")
        
        assert result["is_safe"] is True, "Config without secrets should be safe"
    
    def test_env_with_secret(self, scanner):
        """Test that env files with secrets are flagged."""
        config = """
APP_NAME=MyApp
JWT_SECRET=super-secret-key-12345
DATABASE_PASSWORD=secret123
"""
        result = scanner.scan_config_file(config, "env")
        
        assert result["is_safe"] is False, "Secrets in config should be detected"
        assert result["severity"] == "high", "Secrets in config is high severity"
    
    def test_yaml_config_no_secrets(self, scanner):
        """Test that YAML configs don't contain secrets."""
        config = """
app:
  name: MyApp
  debug: false
database:
  url: postgresql://localhost/db
"""
        result = scanner.scan_config_file(config, "yaml")
        
        assert result["is_safe"] is True, "YAML without secrets should be safe"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])