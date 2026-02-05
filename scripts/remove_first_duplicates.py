#!/usr/bin/env python3
"""
Remove first occurrence of duplicate top-level keys in JSON file.
Keeps the last occurrence of each duplicate key.
"""

import json
import re

def remove_first_duplicates(filepath, output_path):
    """Remove first occurrence of duplicate keys"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find all top-level keys and their line numbers
    key_occurrences = {}
    for i, line in enumerate(lines):
        # Match top-level keys (2 spaces indentation)
        match = re.match(r'^  "([^"]+)": \{$', line)
        if match:
            key = match.group(1)
            if key not in key_occurrences:
                key_occurrences[key] = []
            key_occurrences[key].append(i)
    
    # Find duplicates
    duplicates = {k: v for k, v in key_occurrences.items() if len(v) > 1}
    
    if not duplicates:
        print("No duplicates found!")
        return False
    
    print(f"Found {len(duplicates)} duplicate keys:")
    for key, lines_list in duplicates.items():
        print(f"  - {key}: lines {[l+1 for l in lines_list]}")
    
    # Mark lines to remove (first occurrence of each duplicate)
    lines_to_remove = set()
    
    for key, occurrences in duplicates.items():
        # Remove first occurrence
        first_line = occurrences[0]
        
        # Find the end of this section (matching closing brace)
        brace_count = 0
        for i in range(first_line, len(lines)):
            brace_count += lines[i].count('{') - lines[i].count('}')
            lines_to_remove.add(i)
            if brace_count == 0:
                break
    
    # Write output, skipping marked lines
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                f.write(line)
    
    print(f"\nRemoved {len(lines_to_remove)} lines")
    print(f"Output written to: {output_path}")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python remove_first_duplicates.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    success = remove_first_duplicates(input_file, output_file)
    sys.exit(0 if success else 1)
