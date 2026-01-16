#!/usr/bin/env python3
"""
Documentation Size Checker

Checks document token counts and recommends splitting if needed.
Uses approximate token counting (1 token ≈ 4 characters for English).
"""

import os
import sys
from pathlib import Path
from typing import Dict, List
import json

class DocSizeChecker:
    """Check documentation file sizes and recommend splits"""
    
    TOKEN_THRESHOLD = 10000  # Target max tokens per file
    CHARS_PER_TOKEN = 4  # Approximate
    
    def __init__(self, spec_path: str):
        self.spec_path = Path(spec_path)
        self.results = []
        
    def check_sizes(self) -> Dict:
        """Check all documentation files in spec path"""
        print(f"📏 Checking document sizes in: {self.spec_path}")
        
        # Find all markdown files
        md_files = list(self.spec_path.glob('*.md'))
        
        if not md_files:
            return {
                'success': False,
                'message': 'No markdown files found',
                'files': []
            }
        
        total_tokens = 0
        needs_split = []
        
        for md_file in md_files:
            file_info = self._analyze_file(md_file)
            self.results.append(file_info)
            total_tokens += file_info['tokens']
            
            if file_info['needs_split']:
                needs_split.append(file_info['filename'])
        
        # Generate report
        report = {
            'success': len(needs_split) == 0,
            'message': f"Checked {len(md_files)} files, {len(needs_split)} need splitting",
            'total_tokens': total_tokens,
            'files': self.results,
            'needs_split': needs_split,
            'recommendations': self._generate_recommendations(needs_split)
        }
        
        self._print_report(report)
        return report
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chars = len(content)
        tokens = chars // self.CHARS_PER_TOKEN
        lines = content.count('\n') + 1
        
        # Check if needs splitting
        needs_split = tokens > self.TOKEN_THRESHOLD
        
        # Analyze structure for split suggestions
        sections = self._extract_sections(content)
        
        return {
            'filename': file_path.name,
            'path': str(file_path),
            'chars': chars,
            'tokens': tokens,
            'lines': lines,
            'needs_split': needs_split,
            'sections': sections,
            'utilization': f"{(tokens / self.TOKEN_THRESHOLD * 100):.1f}%"
        }
    
    def _extract_sections(self, content: str) -> List[Dict]:
        """Extract H1 and H2 sections for split analysis"""
        sections = []
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('# '):
                if current_section:
                    sections.append({
                        'title': current_section,
                        'lines': len(current_content),
                        'tokens': sum(len(l) for l in current_content) // self.CHARS_PER_TOKEN
                    })
                current_section = line[2:].strip()
                current_content = []
            elif line.startswith('## '):
                if current_section:
                    sections.append({
                        'title': current_section,
                        'lines': len(current_content),
                        'tokens': sum(len(l) for l in current_content) // self.CHARS_PER_TOKEN
                    })
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add last section
        if current_section:
            sections.append({
                'title': current_section,
                'lines': len(current_content),
                'tokens': sum(len(l) for l in current_content) // self.CHARS_PER_TOKEN
            })
        
        return sections
    
    def _generate_recommendations(self, needs_split: List[str]) -> List[Dict]:
        """Generate split recommendations"""
        recommendations = []
        
        for filename in needs_split:
            file_info = next(f for f in self.results if f['filename'] == filename)
            
            # Suggest logical splits based on sections
            base_name = filename.replace('.md', '')
            suggested_splits = []
            
            # Group sections into logical chunks
            current_chunk = []
            current_tokens = 0
            chunk_num = 1
            
            for section in file_info['sections']:
                if current_tokens + section['tokens'] > self.TOKEN_THRESHOLD and current_chunk:
                    # Create new chunk
                    suggested_splits.append({
                        'filename': f"{base_name}-part{chunk_num}.md",
                        'sections': [s['title'] for s in current_chunk],
                        'tokens': current_tokens
                    })
                    current_chunk = []
                    current_tokens = 0
                    chunk_num += 1
                
                current_chunk.append(section)
                current_tokens += section['tokens']
            
            # Add last chunk
            if current_chunk:
                suggested_splits.append({
                    'filename': f"{base_name}-part{chunk_num}.md",
                    'sections': [s['title'] for s in current_chunk],
                    'tokens': current_tokens
                })
            
            recommendations.append({
                'original': filename,
                'tokens': file_info['tokens'],
                'suggested_splits': suggested_splits,
                'index_file': f"{base_name}-index.md"
            })
        
        return recommendations
    
    def _print_report(self, report: Dict):
        """Print formatted report"""
        print(f"\n📊 Document Size Report:")
        print(f"  Total Files: {len(report['files'])}")
        print(f"  Total Tokens: {report['total_tokens']:,}")
        print(f"  Files Needing Split: {len(report['needs_split'])}")
        
        print(f"\n📄 File Details:")
        for file_info in report['files']:
            status = "⚠️ " if file_info['needs_split'] else "✅"
            print(f"  {status} {file_info['filename']}")
            print(f"     Tokens: {file_info['tokens']:,} ({file_info['utilization']})")
            print(f"     Lines: {file_info['lines']:,}")
            print(f"     Sections: {len(file_info['sections'])}")
        
        if report['recommendations']:
            print(f"\n💡 Split Recommendations:")
            for rec in report['recommendations']:
                print(f"\n  📝 {rec['original']} ({rec['tokens']:,} tokens)")
                print(f"     Suggested splits:")
                for split in rec['suggested_splits']:
                    print(f"       → {split['filename']} ({split['tokens']:,} tokens)")
                    print(f"          Sections: {', '.join(split['sections'][:3])}...")
                print(f"     Create index: {rec['index_file']}")
        
        if report['success']:
            print(f"\n✅ All documents within size limits!")
        else:
            print(f"\n⚠️  Some documents exceed recommended size - consider splitting")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python check_doc_size.py <spec-path>")
        print("Example: python check_doc_size.py .kiro/specs/audit-security")
        sys.exit(1)
    
    spec_path = sys.argv[1]
    
    if not os.path.exists(spec_path):
        print(f"❌ Spec path not found: {spec_path}")
        sys.exit(1)
    
    checker = DocSizeChecker(spec_path)
    report = checker.check_sizes()
    
    # Save report
    report_path = Path(spec_path) / 'size-report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Report saved to: {report_path}")
    
    sys.exit(0 if report['success'] else 1)

if __name__ == '__main__':
    main()
