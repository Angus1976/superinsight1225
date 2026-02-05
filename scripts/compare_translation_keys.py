#!/usr/bin/env python3
"""
Compare key structures between zh and en admin translation files.
Validates Requirements 4.3: Ensure zh and en files have matching key structures.
"""

import json
import sys
from pathlib import Path
from typing import Set, List, Tuple


def get_all_keys(obj: dict, prefix: str = "") -> Set[str]:
    """Recursively extract all keys from a nested dictionary."""
    keys = set()
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
    return keys


def compare_translation_files(zh_file: Path, en_file: Path) -> Tuple[bool, List[str]]:
    """
    Compare key structures between Chinese and English translation files.
    
    Returns:
        Tuple of (is_matching, error_messages)
    """
    errors = []
    
    # Load files
    try:
        with open(zh_file, 'r', encoding='utf-8') as f:
            zh_data = json.load(f)
    except Exception as e:
        errors.append(f"❌ Failed to load {zh_file}: {e}")
        return False, errors
    
    try:
        with open(en_file, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
    except Exception as e:
        errors.append(f"❌ Failed to load {en_file}: {e}")
        return False, errors
    
    # Extract all keys
    zh_keys = get_all_keys(zh_data)
    en_keys = get_all_keys(en_data)
    
    # Find differences
    missing_in_en = zh_keys - en_keys
    missing_in_zh = en_keys - zh_keys
    
    # Report results
    print(f"\n{'='*70}")
    print(f"Translation File Structure Comparison")
    print(f"{'='*70}\n")
    
    print(f"📊 Statistics:")
    print(f"   Chinese file keys: {len(zh_keys)}")
    print(f"   English file keys: {len(en_keys)}")
    print(f"   Common keys: {len(zh_keys & en_keys)}")
    print()
    
    if missing_in_en:
        errors.append(f"❌ Keys in Chinese but missing in English ({len(missing_in_en)}):")
        for key in sorted(missing_in_en):
            errors.append(f"   - {key}")
        print("\n".join(errors[-len(missing_in_en)-1:]))
        print()
    
    if missing_in_zh:
        errors.append(f"❌ Keys in English but missing in Chinese ({len(missing_in_zh)}):")
        for key in sorted(missing_in_zh):
            errors.append(f"   - {key}")
        print("\n".join(errors[-len(missing_in_zh)-1:]))
        print()
    
    if not missing_in_en and not missing_in_zh:
        print("✅ SUCCESS: File structures match perfectly!")
        print(f"   Both files have {len(zh_keys)} keys with identical structure.")
        return True, []
    else:
        print(f"❌ FAILURE: File structures do not match")
        print(f"   Missing in English: {len(missing_in_en)}")
        print(f"   Missing in Chinese: {len(missing_in_zh)}")
        return False, errors


def main():
    """Main entry point."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define file paths
    zh_file = project_root / "frontend" / "src" / "locales" / "zh" / "admin.json"
    en_file = project_root / "frontend" / "src" / "locales" / "en" / "admin.json"
    
    # Check files exist
    if not zh_file.exists():
        print(f"❌ Chinese file not found: {zh_file}")
        sys.exit(1)
    
    if not en_file.exists():
        print(f"❌ English file not found: {en_file}")
        sys.exit(1)
    
    # Compare files
    is_matching, errors = compare_translation_files(zh_file, en_file)
    
    # Exit with appropriate code
    sys.exit(0 if is_matching else 1)


if __name__ == "__main__":
    main()
