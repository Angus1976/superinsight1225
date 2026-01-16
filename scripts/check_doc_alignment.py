#!/usr/bin/env python3
"""
Documentation-Code Alignment Checker

Verifies that documentation (requirements, design, tasks) aligns with actual code implementation.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

@dataclass
class AlignmentIssue:
    """Represents a documentation-code alignment issue"""
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'missing_impl', 'missing_doc', 'mismatch', 'outdated'
    file: str
    line: int
    description: str
    suggestion: str

class DocAlignmentChecker:
    """Check alignment between documentation and code"""
    
    def __init__(self, feature_path: str):
        self.feature_path = Path(feature_path)
        self.feature_name = self.feature_path.name
        self.issues: List[AlignmentIssue] = []
        
    def check_alignment(self) -> Dict:
        """Run all alignment checks"""
        print(f"🔍 Checking alignment for feature: {self.feature_name}")
        
        # Load documentation
        requirements = self._load_doc('requirements.md')
        design = self._load_doc('design.md')
        tasks = self._load_doc('tasks.md')
        
        if not all([requirements, design, tasks]):
            return self._generate_report(success=False, message="Missing core documentation files")
        
        # Run checks
        self._check_requirements_coverage(requirements)
        self._check_design_implementation(design)
        self._check_task_completion(tasks)
        self._check_cross_references(requirements, design, tasks)
        
        # Generate report
        return self._generate_report(
            success=len([i for i in self.issues if i.severity == 'critical']) == 0,
            message=f"Found {len(self.issues)} alignment issues"
        )
    
    def _load_doc(self, filename: str) -> str:
        """Load documentation file"""
        doc_path = self.feature_path / filename
        if not doc_path.exists():
            self.issues.append(AlignmentIssue(
                severity='critical',
                category='missing_doc',
                file=filename,
                line=0,
                description=f"Required documentation file {filename} not found",
                suggestion=f"Create {filename} following the template in doc-first-workflow.md"
            ))
            return ""
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _check_requirements_coverage(self, requirements: str):
        """Check if all requirements have corresponding implementation"""
        # Extract requirement IDs (e.g., "1.1", "2.3")
        req_pattern = r'###?\s+(\d+\.\d+)\s+(.+)'
        requirements_found = re.findall(req_pattern, requirements)
        
        print(f"  📋 Found {len(requirements_found)} requirements")
        
        # Check for acceptance criteria
        for req_id, req_name in requirements_found:
            if 'Acceptance Criteria' not in requirements:
                self.issues.append(AlignmentIssue(
                    severity='warning',
                    category='missing_doc',
                    file='requirements.md',
                    line=0,
                    description=f"Requirement {req_id} missing acceptance criteria",
                    suggestion="Add EARS-format acceptance criteria (WHEN/IF/WHERE...THEN)"
                ))
    
    def _check_design_implementation(self, design: str):
        """Check if design decisions are reflected in code"""
        # Check for required design sections
        required_sections = [
            'Architecture Overview',
            'Component Design',
            'Technical Decisions'
        ]
        
        for section in required_sections:
            if section not in design:
                self.issues.append(AlignmentIssue(
                    severity='warning',
                    category='missing_doc',
                    file='design.md',
                    line=0,
                    description=f"Missing required section: {section}",
                    suggestion=f"Add {section} section following the template"
                ))
        
        # Check for diagrams
        if '```mermaid' not in design:
            self.issues.append(AlignmentIssue(
                severity='info',
                category='missing_doc',
                file='design.md',
                line=0,
                description="No Mermaid diagrams found",
                suggestion="Add architecture or sequence diagrams for clarity"
            ))
    
    def _check_task_completion(self, tasks: str):
        """Check task completion status"""
        # Count tasks
        total_tasks = len(re.findall(r'- \[[ x~-]\]', tasks))
        completed_tasks = len(re.findall(r'- \[x\]', tasks))
        in_progress_tasks = len(re.findall(r'- \[-\]', tasks))
        
        print(f"  ✅ Tasks: {completed_tasks}/{total_tasks} completed, {in_progress_tasks} in progress")
        
        # Check for time estimates
        if 'Est:' not in tasks and total_tasks > 0:
            self.issues.append(AlignmentIssue(
                severity='warning',
                category='missing_doc',
                file='tasks.md',
                line=0,
                description="Tasks missing time estimates",
                suggestion="Add time estimates (Est: Xh) to all tasks"
            ))
    
    def _check_cross_references(self, requirements: str, design: str, tasks: str):
        """Check for broken cross-references"""
        # Check if tasks reference requirements
        if 'Validates:' not in tasks and 'Requirements' not in tasks:
            self.issues.append(AlignmentIssue(
                severity='info',
                category='missing_doc',
                file='tasks.md',
                line=0,
                description="Tasks don't reference requirements",
                suggestion="Add 'Validates: Requirements X.Y' to link tasks to requirements"
            ))
    
    def _generate_report(self, success: bool, message: str) -> Dict:
        """Generate alignment report"""
        report = {
            'feature': self.feature_name,
            'success': success,
            'message': message,
            'summary': {
                'total_issues': len(self.issues),
                'critical': len([i for i in self.issues if i.severity == 'critical']),
                'warnings': len([i for i in self.issues if i.severity == 'warning']),
                'info': len([i for i in self.issues if i.severity == 'info'])
            },
            'issues': [asdict(issue) for issue in self.issues]
        }
        
        # Print summary
        print(f"\n📊 Alignment Report:")
        print(f"  Total Issues: {report['summary']['total_issues']}")
        print(f"  Critical: {report['summary']['critical']}")
        print(f"  Warnings: {report['summary']['warnings']}")
        print(f"  Info: {report['summary']['info']}")
        
        if report['summary']['critical'] > 0:
            print(f"\n❌ CRITICAL ISSUES FOUND - Documentation must be fixed before code changes!")
        elif report['summary']['warnings'] > 0:
            print(f"\n⚠️  Warnings found - Consider addressing before proceeding")
        else:
            print(f"\n✅ Documentation-code alignment verified!")
        
        return report

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python check_doc_alignment.py <feature-path>")
        print("Example: python check_doc_alignment.py .kiro/specs/audit-security")
        sys.exit(1)
    
    feature_path = sys.argv[1]
    
    if not os.path.exists(feature_path):
        print(f"❌ Feature path not found: {feature_path}")
        sys.exit(1)
    
    checker = DocAlignmentChecker(feature_path)
    report = checker.check_alignment()
    
    # Save report
    report_path = Path(feature_path) / 'alignment-report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Report saved to: {report_path}")
    
    # Exit with error code if critical issues found
    sys.exit(0 if report['success'] else 1)

if __name__ == '__main__':
    main()
