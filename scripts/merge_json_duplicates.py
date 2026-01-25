#!/usr/bin/env python3
"""
Merge duplicate keys in JSON file by combining unique content from all occurrences.
The last occurrence wins for conflicting keys, but unique keys from earlier occurrences are preserved.
"""

import json
import sys
from collections import OrderedDict

def deep_merge(dict1, dict2):
    """
    Deep merge dict2 into dict1. dict2 values take precedence for conflicts.
    Returns a new dictionary.
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result:
            # If both are dicts, merge recursively
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                # dict2 value takes precedence
                result[key] = value
        else:
            # New key from dict2
            result[key] = value
    
    return result

def parse_json_with_duplicates(filepath):
    """
    Parse JSON file and track duplicate keys, merging their content.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse normally first to get structure
    data = json.loads(content)
    
    # Now parse line by line to find duplicates
    lines = content.split('\n')
    result = OrderedDict()
    current_key = None
    current_content = []
    brace_count = 0
    in_root = True
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect root-level key
        if stripped.startswith('"') and '": {' in line and line.startswith('  "'):
            # This is a root-level key
            key_name = line.split('"')[1]
            
            if current_key:
                # Save previous section
                section_json = '\n'.join(current_content)
                try:
                    section_data = json.loads('{' + section_json + '}')
                    section_value = section_data[current_key]
                    
                    if current_key in result:
                        # Merge with existing
                        result[current_key] = deep_merge(result[current_key], section_value)
                    else:
                        result[current_key] = section_value
                except:
                    pass
            
            # Start new section
            current_key = key_name
            current_content = [line.lstrip()]
            brace_count = 1
        elif current_key:
            current_content.append(line.lstrip())
            brace_count += line.count('{') - line.count('}')
            
            if brace_count == 0:
                # Section complete
                section_json = '\n'.join(current_content)
                try:
                    section_data = json.loads('{' + section_json)
                    section_value = section_data[current_key]
                    
                    if current_key in result:
                        # Merge with existing
                        result[current_key] = deep_merge(result[current_key], section_value)
                    else:
                        result[current_key] = section_value
                except Exception as e:
                    print(f"Error parsing section {current_key}: {e}", file=sys.stderr)
                
                current_key = None
                current_content = []
    
    return result

def main():
    if len(sys.argv) < 3:
        print("Usage: python merge_duplicates.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Reading {input_file}...")
    
    # Parse with duplicate handling
    merged_data = parse_json_with_duplicates(input_file)
    
    print(f"Merged {len(merged_data)} top-level keys")
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"Written to {output_file}")

if __name__ == "__main__":
    main()
