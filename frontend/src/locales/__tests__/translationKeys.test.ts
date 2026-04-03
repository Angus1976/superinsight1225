/**
 * Translation Key Consistency Tests
 * 
 * **Validates: Requirements 11.1** - 翻译文件创建
 * **Validates: Requirements 10.1.3** - 验证翻译文件
 * 
 * Tests that zh and en translation files have matching key structures.
 */

import { describe, it, expect } from 'vitest';
import zhTasks from '../zh/tasks.json';
import enTasks from '../en/tasks.json';

/**
 * Recursively extracts all keys from a nested object
 * Returns keys in dot notation (e.g., "tasks.list.refresh")
 */
function extractKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = [];
  
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    const value = obj[key];
    
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      keys.push(...extractKeys(value as Record<string, unknown>, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  
  return keys.sort();
}

/**
 * Checks if a value is a string (leaf node in translation tree)
 */
function isStringValue(obj: Record<string, unknown>, keyPath: string): boolean {
  const keys = keyPath.split('.');
  let current: unknown = obj;
  
  for (const key of keys) {
    if (current === null || typeof current !== 'object') {
      return false;
    }
    current = (current as Record<string, unknown>)[key];
  }
  
  return typeof current === 'string';
}

describe('Translation Key Consistency - tasks.json', () => {
  const zhKeys = extractKeys(zhTasks as Record<string, unknown>);
  const enKeys = extractKeys(enTasks as Record<string, unknown>);

  it('should have the same number of translation keys in zh and en', () => {
    expect(zhKeys.length).toBe(enKeys.length);
  });

  it('should have all zh keys present in en', () => {
    const missingInEn = zhKeys.filter(key => !enKeys.includes(key));
    
    if (missingInEn.length > 0) {
      console.log('Keys missing in en/tasks.json:', missingInEn);
    }
    
    expect(missingInEn).toEqual([]);
  });

  it('should have all en keys present in zh', () => {
    const missingInZh = enKeys.filter(key => !zhKeys.includes(key));
    
    if (missingInZh.length > 0) {
      console.log('Keys missing in zh/tasks.json:', missingInZh);
    }
    
    expect(missingInZh).toEqual([]);
  });

  it('should have matching key structures', () => {
    // Both should have the same keys
    expect(zhKeys).toEqual(enKeys);
  });

  it('should have string values for all leaf keys in zh', () => {
    const nonStringKeys = zhKeys.filter(
      key => !isStringValue(zhTasks as Record<string, unknown>, key)
    );
    
    expect(nonStringKeys).toEqual([]);
  });

  it('should have string values for all leaf keys in en', () => {
    const nonStringKeys = enKeys.filter(
      key => !isStringValue(enTasks as Record<string, unknown>, key)
    );
    
    expect(nonStringKeys).toEqual([]);
  });

  it('should have non-empty values for all keys in zh', () => {
    const emptyKeys: string[] = [];
    
    for (const key of zhKeys) {
      const keys = key.split('.');
      let current: unknown = zhTasks;
      
      for (const k of keys) {
        current = (current as Record<string, unknown>)[k];
      }
      
      if (typeof current === 'string' && current.trim() === '') {
        emptyKeys.push(key);
      }
    }
    
    expect(emptyKeys).toEqual([]);
  });

  it('should have non-empty values for all keys in en', () => {
    const emptyKeys: string[] = [];
    
    for (const key of enKeys) {
      const keys = key.split('.');
      let current: unknown = enTasks;
      
      for (const k of keys) {
        current = (current as Record<string, unknown>)[k];
      }
      
      if (typeof current === 'string' && current.trim() === '') {
        emptyKeys.push(key);
      }
    }
    
    expect(emptyKeys).toEqual([]);
  });

  // Verify critical translation keys exist
  describe('Critical translation keys', () => {
    const criticalKeys = [
      // `tasks.json` is a flat namespace file; keys do not include a leading `tasks.`.
      'title',
      'refresh',
      'syncAllTasks',
      'statusPending',
      'statusInProgress',
      'statusCompleted',
      'priorityLow',
      'priorityMedium',
      'priorityHigh',
      'annotateAction',
    ];

    it.each(criticalKeys)('should have key "%s" in zh', (key) => {
      expect(zhKeys).toContain(key);
    });

    it.each(criticalKeys)('should have key "%s" in en', (key) => {
      expect(enKeys).toContain(key);
    });
  });
});
