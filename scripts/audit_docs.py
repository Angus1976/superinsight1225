#!/usr/bin/env python3
"""
Documentation Quality Audit Script

Checks documentation for:
- Clarity (readability score)
- Completeness (required sections present)
- Redundancy (duplicate content detection)
- Cross-references (broken links)
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

def calculate_readability_score(text: str) -> float:
    """Calculate simple readability score based on sentence and word length."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return 0.0
    
    total_words = 0
    total_chars = 0
    
    for sentence in sentences:
        words = sentence.split()
        total_words += len(words)
        total_chars += len(sentence)
    
    avg_sentence_length = total_words / len(sentences)
    avg_word_length = total_chars / total_words if total_words > 0 else 0
    
    # Simple readability score (lower is better)
    # Ideal: 15-20 words per sentence, 4-5 chars per word
    score = abs(avg_sentence_length - 17.5) + abs(avg_word_length - 4.5) * 2
    
    return max(0, 100 - score * 2)

def check_required_sections(content: str, doc_type: str) -> Tuple[List[str], List[str]]:
    """Check if required sections are present."""
    required_sections = {
        'requirements': [
            'Introduction',
            'Glossary',
            'Requirements',
            'Acceptance Criteria',
            'Non-Functional Requirements'
        ],
        'design': [
            'Architecture Overview',
            'Component Design',
            'Technical Decisions',
            'Correctness Properties'
        ],
        'tasks': [
            'Task Breakdown',
            'Progress Tracking',
            'Dependencies',
            'Success Criteria'
        ]
    }
    
    sections = required_sections.get(doc_type, [])
    found = []
    missing = []
    
    for section in sections:
        # Check for section headers (## or ###)
        pattern = rf'^##+ .*{re.escape(section)}'
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            found.append(section)
        else:
            missing.append(section)
    
    return found, missing

def find_duplicate_content(files: Dict[str, str], threshold: int = 50) -> List[Dict]:
    """Find duplicate content across files."""
    duplicates = []
    
    # Extract paragraphs from each file
    file_paragraphs = {}
    for filename, content in files.items():
        # Split by double newlines to get paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > threshold]
        file_paragraphs[filename] = paragraphs
    
    # Compare paragraphs across files
    checked = set()
    for file1, paras1 in file_paragraphs.items():
        for file2, paras2 in file_paragraphs.items():
            if file1 >= file2:  # Skip self and already checked pairs
                continue
            
            pair_key = f"{file1}:{file2}"
            if pair_key in checked:
                continue
            checked.add(pair_key)
            
            for i, para1 in enumerate(paras1):
                for j, para2 in enumerate(paras2):
                    # Simple similarity check
                    if len(para1) > threshold and len(para2) > threshold:
                        # Check if paragraphs are very similar
                        words1 = set(para1.lower().split())
                        words2 = set(para2.lower().split())
                        
                        if len(words1) > 10 and len(words2) > 10:
                            overlap = len(words1 & words2)
                            similarity = overlap / min(len(words1), len(words2))
                            
                            if similarity > 0.7:  # 70% similarity
                                duplicates.append({
                                    'file1': file1,
                                    'file2': file2,
                                    'similarity': similarity,
                                    'content_preview': para1[:100] + '...'
                                })
    
    return duplicates

def check_cross_references(content: str, base_path: Path) -> Tuple[List[str], List[str]]:
    """Check for broken cross-references."""
    valid_refs = []
    broken_refs = []
    
    # Find markdown links [text](path)
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    links = re.findall(link_pattern, content)
    
    for text, path in links:
        # Skip external URLs
        if path.startswith('http://') or path.startswith('https://'):
            continue
        
        # Skip anchors
        if path.startswith('#'):
            continue
        
        # Check if file exists
        full_path = base_path / path
        if full_path.exists():
            valid_refs.append(path)
        else:
            broken_refs.append(path)
    
    return valid_refs, broken_refs

def check_ears_notation(content: str) -> Dict:
    """Check for EARS notation in acceptance criteria."""
    ears_keywords = ['WHEN', 'THEN', 'IF', 'WHERE', 'WHILE', 'SHALL']
    
    # Find acceptance criteria sections
    criteria_pattern = r'(?:Acceptance Criteria|验收标准)(.*?)(?=\n##|\Z)'
    criteria_sections = re.findall(criteria_pattern, content, re.DOTALL | re.IGNORECASE)
    
    total_criteria = 0
    ears_compliant = 0
    
    for section in criteria_sections:
        # Count numbered items
        items = re.findall(r'^\d+\.', section, re.MULTILINE)
        total_criteria += len(items)
        
        # Check for EARS keywords
        for keyword in ears_keywords:
            if keyword in section:
                ears_compliant += 1
                break
    
    return {
        'total_criteria': total_criteria,
        'ears_compliant': ears_compliant,
        'compliance_rate': ears_compliant / total_criteria if total_criteria > 0 else 0
    }

def audit_feature(feature_path: str) -> Dict:
    """Audit a feature's documentation."""
    feature_path = Path(feature_path)
    
    if not feature_path.exists():
        return {'error': f'Feature path not found: {feature_path}'}
    
    results = {
        'feature': feature_path.name,
        'path': str(feature_path),
        'files': {},
        'overall': {
            'clarity_score': 0,
            'completeness_score': 0,
            'redundancy_score': 100,
            'cross_ref_score': 100
        },
        'issues': []
    }
    
    # Read all markdown files
    files_content = {}
    for doc_type in ['requirements', 'design', 'tasks']:
        doc_path = feature_path / f'{doc_type}.md'
        if doc_path.exists():
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                files_content[f'{doc_type}.md'] = content
    
    if not files_content:
        results['issues'].append({
            'severity': 'critical',
            'message': 'No documentation files found'
        })
        return results
    
    # Audit each file
    total_clarity = 0
    total_completeness = 0
    file_count = 0
    
    for filename, content in files_content.items():
        doc_type = filename.replace('.md', '')
        file_results = {
            'clarity_score': 0,
            'completeness': {},
            'cross_references': {}
        }
        
        # Clarity check
        clarity_score = calculate_readability_score(content)
        file_results['clarity_score'] = clarity_score
        total_clarity += clarity_score
        
        # Completeness check
        found, missing = check_required_sections(content, doc_type)
        file_results['completeness'] = {
            'found': found,
            'missing': missing,
            'score': len(found) / (len(found) + len(missing)) * 100 if (len(found) + len(missing)) > 0 else 100
        }
        total_completeness += file_results['completeness']['score']
        
        if missing:
            results['issues'].append({
                'severity': 'warning',
                'file': filename,
                'message': f'Missing sections: {", ".join(missing)}'
            })
        
        # Cross-reference check
        valid_refs, broken_refs = check_cross_references(content, feature_path)
        file_results['cross_references'] = {
            'valid': valid_refs,
            'broken': broken_refs,
            'score': len(valid_refs) / (len(valid_refs) + len(broken_refs)) * 100 if (len(valid_refs) + len(broken_refs)) > 0 else 100
        }
        
        if broken_refs:
            results['issues'].append({
                'severity': 'error',
                'file': filename,
                'message': f'Broken references: {", ".join(broken_refs)}'
            })
        
        # EARS notation check (for requirements)
        if doc_type == 'requirements':
            ears_check = check_ears_notation(content)
            file_results['ears_notation'] = ears_check
            
            if ears_check['compliance_rate'] < 0.8:
                results['issues'].append({
                    'severity': 'warning',
                    'file': filename,
                    'message': f'Low EARS notation compliance: {ears_check["compliance_rate"]*100:.1f}%'
                })
        
        results['files'][filename] = file_results
        file_count += 1
    
    # Redundancy check
    duplicates = find_duplicate_content(files_content)
    if duplicates:
        results['redundancy'] = {
            'duplicates_found': len(duplicates),
            'details': duplicates
        }
        results['overall']['redundancy_score'] = max(0, 100 - len(duplicates) * 10)
        
        for dup in duplicates:
            results['issues'].append({
                'severity': 'info',
                'message': f'Duplicate content between {dup["file1"]} and {dup["file2"]} ({dup["similarity"]*100:.1f}% similar)'
            })
    
    # Calculate overall scores
    results['overall']['clarity_score'] = total_clarity / file_count if file_count > 0 else 0
    results['overall']['completeness_score'] = total_completeness / file_count if file_count > 0 else 0
    
    # Calculate cross-reference score
    total_cross_ref_score = sum(
        f['cross_references']['score'] 
        for f in results['files'].values() 
        if 'cross_references' in f
    )
    cross_ref_count = sum(1 for f in results['files'].values() if 'cross_references' in f)
    results['overall']['cross_ref_score'] = total_cross_ref_score / cross_ref_count if cross_ref_count > 0 else 100
    
    return results

def print_audit_report(results: Dict):
    """Print formatted audit report."""
    print(f"\n📋 Documentation Quality Audit: {results['feature']}")
    print(f"   Path: {results['path']}")
    print()
    
    if 'error' in results:
        print(f"❌ {results['error']}")
        return
    
    # Overall scores
    print("📊 Overall Quality Scores:")
    overall = results['overall']
    print(f"   Clarity:       {overall['clarity_score']:.1f}/100")
    print(f"   Completeness:  {overall['completeness_score']:.1f}/100")
    print(f"   Redundancy:    {overall['redundancy_score']:.1f}/100")
    print(f"   Cross-refs:    {overall['cross_ref_score']:.1f}/100")
    print()
    
    # File-by-file details
    print("📄 File Details:")
    for filename, file_data in results['files'].items():
        print(f"\n   {filename}:")
        print(f"     Clarity Score: {file_data['clarity_score']:.1f}/100")
        
        comp = file_data['completeness']
        print(f"     Completeness: {comp['score']:.1f}/100")
        if comp['missing']:
            print(f"       Missing: {', '.join(comp['missing'])}")
        
        if 'cross_references' in file_data:
            xref = file_data['cross_references']
            print(f"     Cross-refs: {len(xref['valid'])} valid, {len(xref['broken'])} broken")
        
        if 'ears_notation' in file_data:
            ears = file_data['ears_notation']
            print(f"     EARS Compliance: {ears['compliance_rate']*100:.1f}% ({ears['ears_compliant']}/{ears['total_criteria']})")
    
    # Issues
    if results['issues']:
        print(f"\n⚠️  Issues Found: {len(results['issues'])}")
        
        critical = [i for i in results['issues'] if i['severity'] == 'critical']
        errors = [i for i in results['issues'] if i['severity'] == 'error']
        warnings = [i for i in results['issues'] if i['severity'] == 'warning']
        info = [i for i in results['issues'] if i['severity'] == 'info']
        
        if critical:
            print(f"\n   🔴 Critical ({len(critical)}):")
            for issue in critical:
                print(f"      - {issue['message']}")
        
        if errors:
            print(f"\n   ❌ Errors ({len(errors)}):")
            for issue in errors:
                file_info = f" [{issue['file']}]" if 'file' in issue else ""
                print(f"      - {issue['message']}{file_info}")
        
        if warnings:
            print(f"\n   ⚠️  Warnings ({len(warnings)}):")
            for issue in warnings:
                file_info = f" [{issue['file']}]" if 'file' in issue else ""
                print(f"      - {issue['message']}{file_info}")
        
        if info:
            print(f"\n   ℹ️  Info ({len(info)}):")
            for issue in info:
                print(f"      - {issue['message']}")
    else:
        print("\n✅ No issues found!")
    
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python audit_docs.py <feature_path>")
        print("Example: python audit_docs.py .kiro/specs/docker-infrastructure")
        sys.exit(1)
    
    feature_path = sys.argv[1]
    
    print(f"🔍 Auditing documentation quality...")
    results = audit_feature(feature_path)
    
    # Print report
    print_audit_report(results)
    
    # Save report
    report_path = Path(feature_path) / 'audit-report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Report saved to: {report_path}")
    
    # Exit code based on issues
    critical = sum(1 for i in results.get('issues', []) if i['severity'] == 'critical')
    errors = sum(1 for i in results.get('issues', []) if i['severity'] == 'error')
    
    if critical > 0:
        sys.exit(2)
    elif errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
