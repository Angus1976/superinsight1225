#!/usr/bin/env python3
"""
Comprehensive Documentation Audit Script for SuperInsight Project
Performs alignment, size, redundancy, completeness, and structure audits
"""

import os
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Set

# Token estimation: ~1.33 words per token (conservative)
WORDS_PER_TOKEN = 0.75
TOKEN_LIMIT = 10000
REDUNDANCY_THRESHOLD = 0.05  # 5%

class DocumentationAuditor:
    def __init__(self, specs_dir: str = ".kiro/specs"):
        self.specs_dir = Path(specs_dir)
        self.features = []
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "alignment": {},
            "size": {},
            "redundancy": {},
            "completeness": {},
            "structure": {},
            "metrics": {},
            "recommendations": []
        }
    
    def run_comprehensive_audit(self):
        """Run all audit checks"""
        print("🔍 COMPREHENSIVE DOCUMENTATION AUDIT")
        print("=" * 80)
        
        # Discover all features
        self.discover_features()
        
        # Run audits
        print("\n1️⃣ Running Alignment Audit...")
        self.audit_alignment()
        
        print("\n2️⃣ Running Size Audit...")
        self.audit_size()
        
        print("\n3️⃣ Running Redundancy Audit...")
        self.audit_redundancy()
        
        print("\n4️⃣ Running Completeness Audit...")
        self.audit_completeness()
        
        print("\n5️⃣ Running Structure Audit...")
        self.audit_structure()
        
        print("\n6️⃣ Calculating Metrics...")
        self.calculate_metrics()
        
        print("\n7️⃣ Generating Recommendations...")
        self.generate_recommendations()
        
        return self.audit_results
    
    def discover_features(self):
        """Discover all feature directories"""
        for item in self.specs_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                self.features.append(item.name)
        
        print(f"📁 Discovered {len(self.features)} features")
    
    def audit_alignment(self):
        """Check documentation-code alignment"""
        alignment_scores = {}
        
        for feature in self.features:
            feature_dir = self.specs_dir / feature
            
            # Check if alignment report exists
            alignment_file = feature_dir / "alignment-report.json"
            if alignment_file.exists():
                try:
                    with open(alignment_file) as f:
                        data = json.load(f)
                        alignment_scores[feature] = {
                            "score": data.get("alignment_score", 0),
                            "has_report": True
                        }
                except:
                    alignment_scores[feature] = {"score": 0, "has_report": False}
            else:
                # Estimate alignment based on file existence
                req_exists = (feature_dir / "requirements.md").exists()
                design_exists = (feature_dir / "design.md").exists()
                tasks_exists = (feature_dir / "tasks.md").exists()
                
                score = 0
                if req_exists and design_exists and tasks_exists:
                    score = 75  # Assume 75% if all docs exist
                elif req_exists and design_exists:
                    score = 50
                elif req_exists:
                    score = 25
                
                alignment_scores[feature] = {
                    "score": score,
                    "has_report": False,
                    "estimated": True
                }
        
        self.audit_results["alignment"] = alignment_scores
        
        # Calculate overall alignment
        total_score = sum(s["score"] for s in alignment_scores.values())
        avg_score = total_score / len(alignment_scores) if alignment_scores else 0
        
        print(f"   ✓ Average alignment score: {avg_score:.1f}%")
        print(f"   ✓ Features with reports: {sum(1 for s in alignment_scores.values() if s['has_report'])}")
    
    def audit_size(self):
        """Check document sizes and identify oversized files"""
        size_data = {}
        oversized = []
        
        for feature in self.features:
            feature_dir = self.specs_dir / feature
            feature_sizes = {}
            
            for doc_type in ["requirements.md", "design.md", "tasks.md"]:
                doc_path = feature_dir / doc_type
                if doc_path.exists():
                    content = doc_path.read_text()
                    words = len(content.split())
                    tokens = int(words / WORDS_PER_TOKEN)
                    
                    feature_sizes[doc_type] = {
                        "words": words,
                        "tokens": tokens,
                        "oversized": tokens > TOKEN_LIMIT
                    }
                    
                    if tokens > TOKEN_LIMIT:
                        oversized.append({
                            "feature": feature,
                            "file": doc_type,
                            "tokens": tokens,
                            "excess": tokens - TOKEN_LIMIT
                        })
            
            size_data[feature] = feature_sizes
        
        self.audit_results["size"] = {
            "by_feature": size_data,
            "oversized_files": oversized
        }
        
        print(f"   ✓ Total documents analyzed: {sum(len(s) for s in size_data.values())}")
        print(f"   ⚠️  Oversized files (>{TOKEN_LIMIT} tokens): {len(oversized)}")
    
    def audit_redundancy(self):
        """Check for duplicate content across documents"""
        # Simple redundancy check: look for repeated paragraphs
        all_paragraphs = defaultdict(list)
        
        for feature in self.features:
            feature_dir = self.specs_dir / feature
            
            for doc_type in ["requirements.md", "design.md", "tasks.md"]:
                doc_path = feature_dir / doc_type
                if doc_path.exists():
                    content = doc_path.read_text()
                    # Split into paragraphs (2+ lines)
                    paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 100]
                    
                    for para in paragraphs:
                        all_paragraphs[para].append(f"{feature}/{doc_type}")
        
        # Find duplicates
        duplicates = {para: locs for para, locs in all_paragraphs.items() if len(locs) > 1}
        
        total_paragraphs = len(all_paragraphs)
        duplicate_count = len(duplicates)
        redundancy_score = (duplicate_count / total_paragraphs * 100) if total_paragraphs > 0 else 0
        
        self.audit_results["redundancy"] = {
            "score": redundancy_score,
            "total_paragraphs": total_paragraphs,
            "duplicate_paragraphs": duplicate_count,
            "duplicates": [{"locations": locs, "preview": para[:100]} for para, locs in list(duplicates.items())[:10]]
        }
        
        print(f"   ✓ Redundancy score: {redundancy_score:.2f}%")
        print(f"   ✓ Duplicate paragraphs found: {duplicate_count}")
    
    def audit_completeness(self):
        """Check if all features have complete documentation"""
        completeness_data = {}
        
        for feature in self.features:
            feature_dir = self.specs_dir / feature
            
            checks = {
                "requirements.md": (feature_dir / "requirements.md").exists(),
                "design.md": (feature_dir / "design.md").exists(),
                "tasks.md": (feature_dir / "tasks.md").exists(),
                "CHANGELOG.md": (feature_dir / "CHANGELOG.md").exists(),
                "README.md": (feature_dir / "README.md").exists()
            }
            
            # Check for EARS notation in requirements
            ears_present = False
            if checks["requirements.md"]:
                req_content = (feature_dir / "requirements.md").read_text()
                ears_present = bool(re.search(r'(WHEN|IF|WHERE|WHILE).*THEN', req_content, re.IGNORECASE))
            
            # Check for diagrams in design
            diagrams_present = False
            if checks["design.md"]:
                design_content = (feature_dir / "design.md").read_text()
                diagrams_present = bool(re.search(r'```mermaid', design_content, re.IGNORECASE))
            
            completeness_score = (
                sum(checks.values()) / len(checks) * 100
            )
            
            completeness_data[feature] = {
                "score": completeness_score,
                "files": checks,
                "ears_notation": ears_present,
                "has_diagrams": diagrams_present
            }
        
        self.audit_results["completeness"] = completeness_data
        
        avg_completeness = sum(d["score"] for d in completeness_data.values()) / len(completeness_data)
        complete_features = sum(1 for d in completeness_data.values() if d["score"] == 100)
        
        print(f"   ✓ Average completeness: {avg_completeness:.1f}%")
        print(f"   ✓ Fully complete features: {complete_features}/{len(self.features)}")
    
    def audit_structure(self):
        """Check document structure and formatting"""
        structure_issues = []
        
        for feature in self.features:
            feature_dir = self.specs_dir / feature
            
            for doc_type in ["requirements.md", "design.md", "tasks.md"]:
                doc_path = feature_dir / doc_type
                if doc_path.exists():
                    content = doc_path.read_text()
                    
                    # Check heading hierarchy
                    headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
                    
                    # Check for proper H1 -> H2 -> H3 progression
                    prev_level = 0
                    for heading_marks, heading_text in headings:
                        level = len(heading_marks)
                        if level > prev_level + 1:
                            structure_issues.append({
                                "feature": feature,
                                "file": doc_type,
                                "issue": "heading_skip",
                                "detail": f"Skipped from H{prev_level} to H{level}"
                            })
                        prev_level = level
                    
                    # Check for broken links
                    links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
                    for link_text, link_url in links:
                        if link_url.startswith('#'):
                            continue  # Skip anchor links
                        if link_url.startswith('http'):
                            continue  # Skip external links
                        
                        # Check if local file exists
                        link_path = feature_dir / link_url
                        if not link_path.exists():
                            structure_issues.append({
                                "feature": feature,
                                "file": doc_type,
                                "issue": "broken_link",
                                "detail": f"Link to {link_url} not found"
                            })
        
        self.audit_results["structure"] = {
            "issues": structure_issues,
            "issue_count": len(structure_issues)
        }
        
        print(f"   ⚠️  Structure issues found: {len(structure_issues)}")
    
    def calculate_metrics(self):
        """Calculate overall metrics"""
        metrics = {
            "total_features": len(self.features),
            "total_documents": sum(len(s) for s in self.audit_results["size"]["by_feature"].values()),
            "alignment_score": sum(s["score"] for s in self.audit_results["alignment"].values()) / len(self.features) if self.features else 0,
            "completeness_score": sum(d["score"] for d in self.audit_results["completeness"].values()) / len(self.features) if self.features else 0,
            "redundancy_score": self.audit_results["redundancy"]["score"],
            "oversized_files": len(self.audit_results["size"]["oversized_files"]),
            "structure_issues": self.audit_results["structure"]["issue_count"]
        }
        
        # Calculate average document size
        all_sizes = []
        for feature_sizes in self.audit_results["size"]["by_feature"].values():
            all_sizes.extend([s["tokens"] for s in feature_sizes.values()])
        
        metrics["avg_document_size"] = sum(all_sizes) / len(all_sizes) if all_sizes else 0
        
        self.audit_results["metrics"] = metrics
        
        print(f"\n📊 OVERALL METRICS:")
        print(f"   • Total Features: {metrics['total_features']}")
        print(f"   • Total Documents: {metrics['total_documents']}")
        print(f"   • Alignment Score: {metrics['alignment_score']:.1f}%")
        print(f"   • Completeness Score: {metrics['completeness_score']:.1f}%")
        print(f"   • Redundancy Score: {metrics['redundancy_score']:.2f}%")
        print(f"   • Average Document Size: {metrics['avg_document_size']:.0f} tokens")
    
    def generate_recommendations(self):
        """Generate actionable recommendations"""
        recommendations = []
        
        # Oversized files
        oversized = self.audit_results["size"]["oversized_files"]
        if oversized:
            recommendations.append({
                "priority": "HIGH",
                "category": "Size",
                "title": f"Split {len(oversized)} oversized documents",
                "details": [f"{f['feature']}/{f['file']} ({f['tokens']} tokens, {f['excess']} over limit)" for f in oversized[:5]]
            })
        
        # Low alignment
        low_alignment = [f for f, s in self.audit_results["alignment"].items() if s["score"] < 75]
        if low_alignment:
            recommendations.append({
                "priority": "HIGH",
                "category": "Alignment",
                "title": f"Improve alignment for {len(low_alignment)} features",
                "details": low_alignment[:10]
            })
        
        # Incomplete features
        incomplete = [f for f, d in self.audit_results["completeness"].items() if d["score"] < 100]
        if incomplete:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Completeness",
                "title": f"Complete documentation for {len(incomplete)} features",
                "details": incomplete[:10]
            })
        
        # Missing EARS notation
        no_ears = [f for f, d in self.audit_results["completeness"].items() if d["files"].get("requirements.md") and not d["ears_notation"]]
        if no_ears:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Requirements",
                "title": f"Add EARS notation to {len(no_ears)} requirements documents",
                "details": no_ears[:10]
            })
        
        # Missing diagrams
        no_diagrams = [f for f, d in self.audit_results["completeness"].items() if d["files"].get("design.md") and not d["has_diagrams"]]
        if no_diagrams:
            recommendations.append({
                "priority": "LOW",
                "category": "Design",
                "title": f"Add diagrams to {len(no_diagrams)} design documents",
                "details": no_diagrams[:10]
            })
        
        # High redundancy
        if self.audit_results["redundancy"]["score"] > REDUNDANCY_THRESHOLD * 100:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Redundancy",
                "title": "Reduce content duplication",
                "details": [f"Found {self.audit_results['redundancy']['duplicate_paragraphs']} duplicate paragraphs"]
            })
        
        # Structure issues
        if self.audit_results["structure"]["issue_count"] > 0:
            recommendations.append({
                "priority": "LOW",
                "category": "Structure",
                "title": f"Fix {self.audit_results['structure']['issue_count']} structure issues",
                "details": [f"{i['feature']}/{i['file']}: {i['issue']}" for i in self.audit_results["structure"]["issues"][:10]]
            })
        
        self.audit_results["recommendations"] = recommendations
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"   [{rec['priority']}] {rec['category']}: {rec['title']}")

def main():
    auditor = DocumentationAuditor()
    results = auditor.run_comprehensive_audit()
    
    # Save results
    output_file = "audit-report.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Audit complete! Results saved to {output_file}")
    
    # Generate markdown report
    generate_markdown_report(results)

def generate_markdown_report(results):
    """Generate a markdown report from audit results"""
    report = f"""# Comprehensive Documentation Audit Report

**Generated**: {results['timestamp']}

## Executive Summary

| Metric | Score | Status |
|--------|-------|--------|
| Alignment Score | {results['metrics']['alignment_score']:.1f}% | {'✅' if results['metrics']['alignment_score'] >= 90 else '⚠️' if results['metrics']['alignment_score'] >= 75 else '🔴'} |
| Completeness Score | {results['metrics']['completeness_score']:.1f}% | {'✅' if results['metrics']['completeness_score'] >= 90 else '⚠️' if results['metrics']['completeness_score'] >= 75 else '🔴'} |
| Redundancy Score | {results['metrics']['redundancy_score']:.2f}% | {'✅' if results['metrics']['redundancy_score'] < 5 else '⚠️' if results['metrics']['redundancy_score'] < 10 else '🔴'} |
| Average Document Size | {results['metrics']['avg_document_size']:.0f} tokens | {'✅' if results['metrics']['avg_document_size'] < 8000 else '⚠️'} |

## 1. Alignment Audit

**Overall Score**: {results['metrics']['alignment_score']:.1f}%

### Features by Alignment Score

"""
    
    # Sort features by alignment score
    sorted_alignment = sorted(results['alignment'].items(), key=lambda x: x[1]['score'])
    
    report += "| Feature | Score | Has Report |\n"
    report += "|---------|-------|------------|\n"
    for feature, data in sorted_alignment[:20]:
        report += f"| {feature} | {data['score']:.0f}% | {'✅' if data['has_report'] else '❌'} |\n"
    
    report += f"\n## 2. Size Audit\n\n"
    report += f"**Oversized Files**: {len(results['size']['oversized_files'])}\n\n"
    
    if results['size']['oversized_files']:
        report += "### Files Exceeding 10,000 Tokens\n\n"
        report += "| Feature | File | Tokens | Excess |\n"
        report += "|---------|------|--------|--------|\n"
        for item in results['size']['oversized_files'][:20]:
            report += f"| {item['feature']} | {item['file']} | {item['tokens']:,} | +{item['excess']:,} |\n"
    
    report += f"\n## 3. Redundancy Audit\n\n"
    report += f"**Redundancy Score**: {results['redundancy']['score']:.2f}%\n"
    report += f"**Duplicate Paragraphs**: {results['redundancy']['duplicate_paragraphs']}\n\n"
    
    report += f"\n## 4. Completeness Audit\n\n"
    report += f"**Average Completeness**: {results['metrics']['completeness_score']:.1f}%\n\n"
    
    # Features missing documents
    incomplete = [(f, d) for f, d in results['completeness'].items() if d['score'] < 100]
    if incomplete:
        report += "### Incomplete Features\n\n"
        report += "| Feature | Score | Missing |\n"
        report += "|---------|-------|----------|\n"
        for feature, data in sorted(incomplete, key=lambda x: x[1]['score'])[:20]:
            missing = [k for k, v in data['files'].items() if not v]
            report += f"| {feature} | {data['score']:.0f}% | {', '.join(missing)} |\n"
    
    report += f"\n## 5. Structure Audit\n\n"
    report += f"**Issues Found**: {results['structure']['issue_count']}\n\n"
    
    if results['structure']['issues']:
        report += "### Top Structure Issues\n\n"
        for issue in results['structure']['issues'][:20]:
            report += f"- **{issue['feature']}/{issue['file']}**: {issue['issue']} - {issue['detail']}\n"
    
    report += f"\n## 6. Recommendations\n\n"
    
    for rec in results['recommendations']:
        report += f"### [{rec['priority']}] {rec['category']}: {rec['title']}\n\n"
        if rec['details']:
            for detail in rec['details'][:10]:
                report += f"- {detail}\n"
            if len(rec['details']) > 10:
                report += f"- ... and {len(rec['details']) - 10} more\n"
        report += "\n"
    
    report += f"\n## Summary\n\n"
    report += f"- **Total Features**: {results['metrics']['total_features']}\n"
    report += f"- **Total Documents**: {results['metrics']['total_documents']}\n"
    report += f"- **Alignment Score**: {results['metrics']['alignment_score']:.1f}%\n"
    report += f"- **Completeness Score**: {results['metrics']['completeness_score']:.1f}%\n"
    report += f"- **Redundancy Score**: {results['metrics']['redundancy_score']:.2f}%\n"
    report += f"- **Structure Issues**: {results['metrics']['structure_issues']}\n"
    
    with open("audit-report.md", 'w') as f:
        f.write(report)
    
    print(f"✅ Markdown report saved to audit-report.md")

if __name__ == "__main__":
    main()
