"""
Security Vulnerability Reporting and Severity Categorization.

Generates security scan reports with severity categorization (critical, high, medium, low).

Validates: Requirements 6.6, Property 18
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


# =============================================================================
# Severity and Category Enums
# =============================================================================

class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VulnerabilityCategory(Enum):
    """Categories of security vulnerabilities."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    AUTH_BYPASS = "auth_bypass"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    DEPENDENCY_VULNERABILITY = "dependency_vulnerability"
    CSRF = "csrf"
    IDOR = "idor"
    BROKEN_AUTH = "broken_auth"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"
    ACCESS_CONTROL = "access_control"
    CRYPTOGRAPHY = "cryptography"
    INFORMATION_DISCLOSURE = "information_disclosure"


# =============================================================================
# Vulnerability Data Model
# =============================================================================

@dataclass
class Vulnerability:
    """Represents a security vulnerability."""
    vulnerability_id: str
    title: str
    description: str
    severity: Severity
    category: VulnerabilityCategory
    affected_component: str
    remediation: str
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "open"
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vulnerability to dictionary."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "affected_component": self.affected_component,
            "remediation": self.remediation,
            "cve_id": self.cve_id,
            "cvss_score": self.cvss_score,
            "discovered_at": self.discovered_at.isoformat(),
            "status": self.status,
            "references": self.references
        }


# =============================================================================
# Security Report Generator
# =============================================================================

class SecurityReportGenerator:
    """
    Generates security vulnerability reports with severity categorization.
    
    Validates: Property 18 - Security Vulnerability Severity Categorization
    """
    
    def __init__(self):
        self.vulnerabilities: List[Vulnerability] = []
        self.scan_metadata: Dict[str, Any] = {}
    
    def add_vulnerability(self, vulnerability: Vulnerability):
        """Add a vulnerability to the report."""
        self.vulnerabilities.append(vulnerability)
    
    def set_scan_metadata(
        self,
        scan_type: str,
        target: str,
        start_time: datetime,
        end_time: datetime,
        tools_used: List[str]
    ):
        """Set scan metadata."""
        self.scan_metadata = {
            "scan_type": scan_type,
            "target": target,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "tools_used": tools_used
        }
    
    def categorize_by_severity(self) -> Dict[str, List[Vulnerability]]:
        """
        Categorize vulnerabilities by severity.
        
        Property 18: All detected vulnerabilities SHALL be assigned a severity
        category from the set {critical, high, medium, low}.
        """
        categorized = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": []
        }
        
        for vuln in self.vulnerabilities:
            categorized[vuln.severity.value].append(vuln)
        
        return categorized
    
    def categorize_by_category(self) -> Dict[str, List[Vulnerability]]:
        """Categorize vulnerabilities by category."""
        categorized = {}
        
        for vuln in self.vulnerabilities:
            cat = vuln.category.value
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(vuln)
        
        return categorized
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate scan summary."""
        by_severity = self.categorize_by_severity()
        
        return {
            "total_vulnerabilities": len(self.vulnerabilities),
            "by_severity": {
                "critical": len(by_severity["critical"]),
                "high": len(by_severity["high"]),
                "medium": len(by_severity["medium"]),
                "low": len(by_severity["low"]),
                "info": len(by_severity["info"])
            },
            "by_category": {
                cat: len(vulns) 
                for cat, vulns in self.categorize_by_category().items()
            },
            "scan_metadata": self.scan_metadata
        }
    
    def generate_json_report(self) -> str:
        """Generate JSON format report."""
        report = {
            "report_generated_at": datetime.utcnow().isoformat(),
            "scan_metadata": self.scan_metadata,
            "summary": self.get_summary(),
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "categorized_by_severity": {
                severity: [v.to_dict() for v in vulns]
                for severity, vulns in self.categorize_by_severity().items()
            }
        }
        
        return json.dumps(report, indent=2)
    
    def generate_html_report(self) -> str:
        """Generate HTML format report."""
        by_severity = self.categorize_by_severity()
        summary = self.get_summary()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Vulnerability Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .severity-card {{ padding: 20px; border-radius: 5px; text-align: center; }}
        .critical {{ background: #dc3545; color: white; }}
        .high {{ background: #fd7e14; color: white; }}
        .medium {{ background: #ffc107; color: black; }}
        .low {{ background: #28a745; color: white; }}
        .vulnerability {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .vulnerability.critical {{ border-left: 5px solid #dc3545; }}
        .vulnerability.high {{ border-left: 5px solid #fd7e14; }}
        .vulnerability.medium {{ border-left: 5px solid #ffc107; }}
        .vulnerability.low {{ border-left: 5px solid #28a745; }}
        .badge {{ padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
        .badge-critical {{ background: #dc3545; color: white; }}
        .badge-high {{ background: #fd7e14; color: white; }}
        .badge-medium {{ background: #ffc107; color: black; }}
        .badge-low {{ background: #28a745; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Vulnerability Report</h1>
        <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Target: {self.scan_metadata.get('target', 'N/A')}</p>
        <p>Scan Type: {self.scan_metadata.get('scan_type', 'N/A')}</p>
    </div>
    
    <div class="summary">
        <div class="severity-card critical">
            <h2>{summary['by_severity']['critical']}</h2>
            <p>Critical</p>
        </div>
        <div class="severity-card high">
            <h2>{summary['by_severity']['high']}</h2>
            <p>High</p>
        </div>
        <div class="severity-card medium">
            <h2>{summary['by_severity']['medium']}</h2>
            <p>Medium</p>
        </div>
        <div class="severity-card low">
            <h2>{summary['by_severity']['low']}</h2>
            <p>Low</p>
        </div>
    </div>
    
    <h2>Vulnerabilities by Severity</h2>
"""
        
        for severity in ["critical", "high", "medium", "low"]:
            vulns = by_severity[severity]
            if vulns:
                html += f"<h3>{severity.upper()} ({len(vulns)})</h3>\n"
                for vuln in vulns:
                    html += f"""
    <div class="vulnerability {severity}">
        <h3>{vuln.title}</h3>
        <p><span class="badge badge-{severity}">{vuln.severity.value.upper()}</span></p>
        <p><strong>ID:</strong> {vuln.vulnerability_id}</p>
        <p><strong>Category:</strong> {vuln.category.value.replace('_', ' ').title()}</p>
        <p><strong>Affected Component:</strong> {vuln.affected_component}</p>
        <p><strong>Description:</strong> {vuln.description}</p>
        <p><strong>Remediation:</strong> {vuln.remediation}</p>
        {"<p><strong>CVE:</strong> " + vuln.cve_id + "</p>" if vuln.cve_id else ""}
    </div>
"""
        
        html += """
</body>
</html>
"""
        return html
    
    def generate_text_report(self) -> str:
        """Generate plain text format report."""
        by_severity = self.categorize_by_severity()
        summary = self.get_summary()
        
        lines = [
            "=" * 60,
            "SECURITY VULNERABILITY REPORT",
            "=" * 60,
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Target: {self.scan_metadata.get('target', 'N/A')}",
            f"Scan Type: {self.scan_metadata.get('scan_type', 'N/A')}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Vulnerabilities: {summary['total_vulnerabilities']}",
            f"  Critical: {summary['by_severity']['critical']}",
            f"  High: {summary['by_severity']['high']}",
            f"  Medium: {summary['by_severity']['medium']}",
            f"  Low: {summary['by_severity']['low']}",
            "",
            "VULNERABILITIES",
            "-" * 40,
        ]
        
        for severity in ["critical", "high", "medium", "low"]:
            vulns = by_severity[severity]
            if vulns:
                lines.append(f"\n{severity.upper()} SEVERITY ({len(vulns)})")
                lines.append("-" * 40)
                for vuln in vulns:
                    lines.extend([
                        f"  ID: {vuln.vulnerability_id}",
                        f"  Title: {vuln.title}",
                        f"  Category: {vuln.category.value}",
                        f"  Component: {vuln.affected_component}",
                        f"  Description: {vuln.description[:100]}...",
                        f"  Remediation: {vuln.remediation[:100]}...",
                        f"  CVE: {vuln.cve_id or 'N/A'}",
                        "",
                    ])
        
        lines.extend([
            "=" * 60,
            "END OF REPORT",
            "=" * 60,
        ])
        
        return "\n".join(lines)


# =============================================================================
# Security Scanner Integration
# =============================================================================

class SecurityScanner:
    """
    Integrated security scanner that runs multiple security tests
    and generates comprehensive reports.
    """
    
    def __init__(self):
        self.report_generator = SecurityReportGenerator()
        self.scanners = {}
    
    def register_scanner(self, name: str, scanner: Any):
        """Register a security scanner."""
        self.scanners[name] = scanner
    
    def run_scan(
        self,
        scan_type: str,
        target: str,
        tools_used: List[str]
    ) -> SecurityReportGenerator:
        """Run security scan and generate report."""
        from datetime import datetime
        
        start_time = datetime.utcnow()
        
        # Run all registered scanners
        for name, scanner in self.scanners.items():
            if hasattr(scanner, 'get_vulnerabilities'):
                vulns = scanner.get_vulnerabilities()
                for vuln in vulns:
                    # Convert scanner vulnerability to report vulnerability
                    self.report_generator.add_vulnerability(
                        self._convert_to_vulnerability(vuln, name)
                    )
        
        end_time = datetime.utcnow()
        
        self.report_generator.set_scan_metadata(
            scan_type=scan_type,
            target=target,
            start_time=start_time,
            end_time=end_time,
            tools_used=tools_used
        )
        
        return self.report_generator
    
    def _convert_to_vulnerability(
        self,
        scanner_vuln: Dict[str, Any],
        scanner_name: str
    ) -> Vulnerability:
        """Convert scanner-specific vulnerability to standard format."""
        # Map scanner severity to enum
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        
        severity = severity_map.get(
            scanner_vuln.get("severity", "medium"),
            Severity.MEDIUM
        )
        
        # Map scanner name to category
        category_map = {
            "sql_injection": VulnerabilityCategory.SQL_INJECTION,
            "xss": VulnerabilityCategory.XSS,
            "auth_bypass": VulnerabilityCategory.AUTH_BYPASS,
            "sensitive_data": VulnerabilityCategory.SENSITIVE_DATA_EXPOSURE,
            "dependency": VulnerabilityCategory.DEPENDENCY_VULNERABILITY,
        }
        
        category = category_map.get(scanner_name, VulnerabilityCategory.INFORMATION_DISCLOSURE)
        
        return Vulnerability(
            vulnerability_id=f"SEC-{len(self.report_generator.vulnerabilities) + 1:04d}",
            title=scanner_vuln.get("title", "Unknown Vulnerability"),
            description=scanner_vuln.get("details", scanner_vuln.get("description", "")),
            severity=severity,
            category=category,
            affected_component=scanner_vuln.get("endpoint", scanner_vuln.get("field_name", "Unknown")),
            remediation="Update to latest version or apply security patch",
            cve_id=scanner_vuln.get("cve_id"),
            cvss_score=scanner_vuln.get("cvss_score"),
            references=[scanner_vuln.get("advisory", "")]
        )


# =============================================================================
# Test Cases
# =============================================================================

class TestSecurityVulnerabilityCategorization:
    """Tests for security vulnerability severity categorization."""
    
    def test_severity_enum_values(self):
        """Test that severity enum has correct values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
    
    def test_vulnerability_to_dict(self):
        """Test vulnerability to dictionary conversion."""
        vuln = Vulnerability(
            vulnerability_id="SEC-0001",
            title="SQL Injection Vulnerability",
            description="SQL injection in user input",
            severity=Severity.HIGH,
            category=VulnerabilityCategory.SQL_INJECTION,
            affected_component="/api/v1/users",
            remediation="Use parameterized queries",
            cve_id="CVE-2024-1234"
        )
        
        result = vuln.to_dict()
        
        assert result["vulnerability_id"] == "SEC-0001"
        assert result["severity"] == "high"
        assert result["category"] == "sql_injection"
        assert result["cve_id"] == "CVE-2024-1234"
    
    def test_categorize_by_severity(self):
        """Test vulnerability categorization by severity."""
        generator = SecurityReportGenerator()
        
        # Add vulnerabilities with different severities
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0001",
            title="Critical Vuln",
            description="Critical",
            severity=Severity.CRITICAL,
            category=VulnerabilityCategory.SQL_INJECTION,
            affected_component="test",
            remediation="fix"
        ))
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0002",
            title="High Vuln",
            description="High",
            severity=Severity.HIGH,
            category=VulnerabilityCategory.XSS,
            affected_component="test",
            remediation="fix"
        ))
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0003",
            title="Medium Vuln",
            description="Medium",
            severity=Severity.MEDIUM,
            category=VulnerabilityCategory.AUTH_BYPASS,
            affected_component="test",
            remediation="fix"
        ))
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0004",
            title="Low Vuln",
            description="Low",
            severity=Severity.LOW,
            category=VulnerabilityCategory.SENSITIVE_DATA_EXPOSURE,
            affected_component="test",
            remediation="fix"
        ))
        
        categorized = generator.categorize_by_severity()
        
        assert len(categorized["critical"]) == 1
        assert len(categorized["high"]) == 1
        assert len(categorized["medium"]) == 1
        assert len(categorized["low"]) == 1
        assert len(categorized["info"]) == 0
    
    def test_get_summary(self):
        """Test summary generation."""
        generator = SecurityReportGenerator()
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0001",
            title="Test",
            description="Test",
            severity=Severity.CRITICAL,
            category=VulnerabilityCategory.SQL_INJECTION,
            affected_component="test",
            remediation="fix"
        ))
        
        summary = generator.get_summary()
        
        assert summary["total_vulnerabilities"] == 1
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 0
    
    def test_json_report_generation(self):
        """Test JSON report generation."""
        generator = SecurityReportGenerator()
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0001",
            title="SQL Injection",
            description="SQL injection vulnerability",
            severity=Severity.HIGH,
            category=VulnerabilityCategory.SQL_INJECTION,
            affected_component="/api/users",
            remediation="Use parameterized queries"
        ))
        
        report = generator.generate_json_report()
        
        assert "SEC-0001" in report
        assert "sql_injection" in report
        assert "high" in report
    
    def test_html_report_generation(self):
        """Test HTML report generation."""
        generator = SecurityReportGenerator()
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0001",
            title="XSS Vulnerability",
            description="Cross-site scripting",
            severity=Severity.MEDIUM,
            category=VulnerabilityCategory.XSS,
            affected_component="/api/search",
            remediation="Escape output"
        ))
        
        report = generator.generate_html_report()
        
        assert "<!DOCTYPE html>" in report or "<html" in report
        assert "XSS Vulnerability" in report
        assert "medium" in report
    
    def test_text_report_generation(self):
        """Test text report generation."""
        generator = SecurityReportGenerator()
        
        generator.add_vulnerability(Vulnerability(
            vulnerability_id="SEC-0001",
            title="Auth Bypass",
            description="Authentication bypass",
            severity=Severity.CRITICAL,
            category=VulnerabilityCategory.AUTH_BYPASS,
            affected_component="/api/auth",
            remediation="Fix authentication logic"
        ))
        
        report = generator.generate_text_report()
        
        assert "SECURITY VULNERABILITY REPORT" in report
        assert "SEC-0001" in report
        assert "CRITICAL" in report


class TestProperty18SeverityCategorization:
    """
    Property 18: Security Vulnerability Severity Categorization
    
    For any detected security vulnerability, the vulnerability SHALL be
    assigned a severity category from the set {critical, high, medium, low}.
    """
    
    def test_all_vulnerabilities_have_severity(self):
        """Test that all vulnerabilities have severity assigned."""
        generator = SecurityReportGenerator()
        
        for severity in Severity:
            generator.add_vulnerability(Vulnerability(
                vulnerability_id=f"SEC-{severity.name}",
                title=f"Test {severity.name}",
                description="Test",
                severity=severity,
                category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                affected_component="test",
                remediation="fix"
            ))
        
        categorized = generator.categorize_by_severity()
        
        # All severities should be represented
        for sev in ["critical", "high", "medium", "low"]:
            assert len(categorized[sev]) == 1, f"Missing {sev} severity category"
    
    def test_severity_categories_are_complete(self):
        """Test that severity categories cover all possible values."""
        expected_categories = {"critical", "high", "medium", "low"}
        actual_categories = {s.value for s in Severity}
        
        assert actual_categories == expected_categories, \
            "Severity categories must be exactly {critical, high, medium, low}"
    
    def test_vulnerability_severity_is_valid(self):
        """Test that vulnerability severity is always valid."""
        expected_categories = {"critical", "high", "medium", "low"}
        for severity in Severity:
            vuln = Vulnerability(
                vulnerability_id="SEC-TEST",
                title="Test",
                description="Test",
                severity=severity,
                category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                affected_component="test",
                remediation="fix"
            )
            
            assert vuln.severity in Severity, "Severity must be a valid Severity enum"
            assert vuln.severity.value in expected_categories, \
                "Severity value must be in {critical, high, medium, low}"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])